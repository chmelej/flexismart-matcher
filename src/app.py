from flask import Flask, jsonify, request
from src.models import db, BankTransaction, MatchLog
from src.flexi_client import FlexiClient
import os

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

app = create_app()

# Configuration (duplicated from sync.py for simplicity in MVP)
FLEXI_URL = os.environ.get("FLEXI_URL", "http://localhost:5000")
FLEXI_USER = os.environ.get("FLEXI_USER", "admin")
FLEXI_PASS = os.environ.get("FLEXI_PASS", "admin")
FLEXI_COMPANY = os.environ.get("FLEXI_COMPANY", "demo")

@app.route('/api/status', methods=['GET'])
def get_status():
    # Summary of matching results
    total = BankTransaction.query.count()
    matched = BankTransaction.query.filter_by(status='MATCHED').count()
    partial = BankTransaction.query.filter_by(status='PARTIAL').count()
    manual = BankTransaction.query.filter_by(status='MANUAL_REQUIRED').count()
    credit = BankTransaction.query.filter_by(status='CREDIT').count()
    pending = BankTransaction.query.filter_by(status='PENDING').count()

    return jsonify({
        "total": total,
        "matched": matched,
        "partial": partial,
        "manual_required": manual,
        "credit": credit,
        "pending": pending
    })

@app.route('/api/manual-review', methods=['GET'])
def get_manual_review():
    # List of transactions needing manual intervention
    # We should also join with MatchLog to show suggestions
    txs = BankTransaction.query.filter_by(status='MANUAL_REQUIRED').all()
    results = []
    for tx in txs:
        # Get latest log for suggestion
        log = MatchLog.query.filter_by(transaction_id=tx.id).order_by(MatchLog.id.desc()).first()
        suggestion = None
        if log:
            suggestion = {
                "invoice_id": log.invoice_id,
                "score": log.score,
                "type": log.match_type
            }

        results.append({
            "id": tx.id,
            "flexi_id": tx.flexi_id,
            "amount": float(tx.amount),
            "v_symbol": tx.v_symbol,
            "sender_name": tx.sender_name,
            "suggestion": suggestion
        })
    return jsonify(results)

@app.route('/api/confirm-match', methods=['POST'])
def confirm_match():
    # Endpoint to manually trigger a match
    data = request.json
    tx_id = data.get('transaction_id')
    invoice_id = data.get('invoice_id')

    tx = BankTransaction.query.get(tx_id)
    if not tx:
        return jsonify({"error": "Transaction not found"}), 404

    client = FlexiClient(FLEXI_URL, FLEXI_USER, FLEXI_PASS, FLEXI_COMPANY)

    try:
        client.post_pairing(tx.flexi_id, invoice_id)
        tx.status = 'MATCHED' # Or 'PARTIAL' depending on logic, simplified here
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=8000, debug=True)
