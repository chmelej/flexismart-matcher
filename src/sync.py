import os
from flask import Flask
from src.models import db, BankTransaction, MatchLog
from src.flexi_client import FlexiClient
from src.matcher import calculate_match_score
from datetime import datetime
from decimal import Decimal

# Configuration
FLEXI_URL = os.environ.get("FLEXI_URL", "http://localhost:5000")
FLEXI_USER = os.environ.get("FLEXI_USER", "admin")
FLEXI_PASS = os.environ.get("FLEXI_PASS", "admin")
FLEXI_COMPANY = os.environ.get("FLEXI_COMPANY", "demo")

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def sync_and_match():
    app = create_app()
    client = FlexiClient(FLEXI_URL, FLEXI_USER, FLEXI_PASS, FLEXI_COMPANY)

    with app.app_context():
        print("Starting sync...")

        # 1. Fetch Data
        try:
            invoices_data = client.fetch_unpaid_invoices()
            payments_data = client.fetch_new_payments()
        except Exception as e:
            print(f"Error fetching data: {e}")
            return

        invoices = invoices_data.get('winstrom', {}).get('faktura-vydana', [])
        payments = payments_data.get('winstrom', {}).get('banka', [])

        print(f"Fetched {len(invoices)} invoices and {len(payments)} payments.")

        # Convert invoices to objects we can work with easily (or namedtuples/dicts)
        # We need efficient lookup if there are many, but for MVP iteration is fine.

        for payment in payments:
            # Check if transaction exists
            flexi_id = payment.get('id')
            tx = BankTransaction.query.filter_by(flexi_id=flexi_id).first()

            if not tx:
                print(f"Creating new transaction for {flexi_id}")
                tx = BankTransaction(
                    flexi_id=flexi_id,
                    external_id=payment.get('cisloDokl'), # Or some external ID field
                    amount=Decimal(payment.get('sumCelkem', 0)),
                    v_symbol=payment.get('varSym'),
                    account_number=payment.get('buc'),
                    sender_name=payment.get('nazev'), # Or 'nazFirmy' depending on field
                    date_received=datetime.fromisoformat(payment.get('datVyst')).date() if payment.get('datVyst') else None,
                    status='PENDING'
                )
                db.session.add(tx)
                db.session.commit()
            else:
                print(f"Transaction {flexi_id} exists with status {tx.status}")

            if tx.status != 'PENDING':
                print(f"Skipping {flexi_id} because status is {tx.status}")
                continue

            # Matching Logic
            best_match = None
            best_score = 0

            # Helper object for invoice to pass to matcher
            class InvoiceObj:
                pass

            for invoice in invoices:
                inv_obj = InvoiceObj()
                inv_obj.v_symbol = invoice.get('varSym')
                inv_obj.amount = Decimal(invoice.get('sumCelkem', 0))
                inv_obj.customer_account = invoice.get('buc')
                inv_obj.customer_name = invoice.get('nazev') # or firma.nazev
                inv_obj.id = invoice.get('id')
                inv_obj.code = invoice.get('kod')

                score = calculate_match_score(tx, inv_obj)

                if score > best_score:
                    best_score = score
                    best_match = inv_obj

            # Decision making
            if best_match:
                print(f"Match found for payment {tx.flexi_id} with invoice {best_match.id} (Score: {best_score})")

                if best_score >= 600:
                     # Automatic Match
                    if tx.amount == best_match.amount:
                        # Full match
                        try:
                            client.post_pairing(tx.flexi_id, best_match.id)
                            tx.status = 'MATCHED'
                            log_type = 'exact'
                        except Exception as e:
                            print(f"Error pairing: {e}")
                            tx.status = 'MANUAL_REQUIRED'
                            log_type = 'error'

                    elif tx.amount < best_match.amount:
                        # Partial match
                        try:
                            client.post_pairing(tx.flexi_id, best_match.id)
                            tx.status = 'PARTIAL'
                            log_type = 'partial'
                        except Exception as e:
                            print(f"Error pairing partial: {e}")
                            tx.status = 'MANUAL_REQUIRED'
                            log_type = 'error'

                    elif tx.amount > best_match.amount:
                         # Overpayment
                        diff = tx.amount - best_match.amount
                        threshold = best_match.amount * Decimal('0.10')

                        if diff > threshold:
                            # Create deposit (Zaloha)
                             try:
                                client.handle_overpayment(best_match.code, float(diff), tx.flexi_id)
                                # We also need to pair the invoice part?
                                # The instructions said: "split payment".
                                # client.post_pairing(tx.flexi_id, best_match.id) # This might be tricky if not split in Flexi
                                # For MVP, assuming handle_overpayment logic handles the rest or we just mark it.
                                # But wait, handle_overpayment in flexi_client creates a deposit for 'amount' passed.
                                # Here 'amount' passed is 'diff'.
                                # We also need to pair the original invoice amount.
                                client.post_pairing(tx.flexi_id, best_match.id)
                                tx.status = 'CREDIT'
                                log_type = 'prepayment'
                             except Exception as e:
                                print(f"Error handling overpayment: {e}")
                                tx.status = 'MANUAL_REQUIRED'
                                log_type = 'error'
                        else:
                            # Small overpayment - just pair it (Flexi handles small diffs or we leave it)
                            # Strategy: Pair it.
                            try:
                                client.post_pairing(tx.flexi_id, best_match.id)
                                tx.status = 'MATCHED'
                                log_type = 'small_overpayment'
                            except Exception as e:
                                print(e)
                                tx.status = 'MANUAL_REQUIRED'
                                log_type = 'error'

                    # Log result
                    log = MatchLog(
                        transaction_id=tx.id,
                        invoice_id=best_match.id,
                        score=best_score,
                        match_type=log_type,
                        log_details={'reason': 'Automatic match'}
                    )
                    db.session.add(log)
                    db.session.commit()

                elif best_score >= 150:
                    # Manual review needed
                    tx.status = 'MANUAL_REQUIRED'
                    log = MatchLog(
                         transaction_id=tx.id,
                         invoice_id=best_match.id,
                         score=best_score,
                         match_type='manual_suggestion',
                         log_details={'reason': 'Score between 150 and 600'}
                    )
                    db.session.add(log)
                    db.session.commit()
                else:
                    # No good match
                    pass

            else:
                 print(f"No match found for {tx.flexi_id}")

        print("Sync complete.")

if __name__ == '__main__':
    sync_and_match()
