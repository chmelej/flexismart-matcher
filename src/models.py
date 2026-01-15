from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class BankTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    flexi_id = db.Column(db.String(50), unique=True) # ID z Flexi (např. 'code:BAN01/2024/001')
    external_id = db.Column(db.String(100)) # ID z výpisu banky
    amount = db.Column(db.Numeric(10, 2))
    v_symbol = db.Column(db.String(20))
    account_number = db.Column(db.String(50))
    sender_name = db.Column(db.String(255))
    date_received = db.Column(db.Date)
    status = db.Column(db.Enum('PENDING', 'MATCHED', 'PARTIAL', 'CREDIT', 'MANUAL_REQUIRED', name='transaction_status_enum'))

class MatchLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('bank_transaction.id'))
    invoice_id = db.Column(db.String(50)) # Flexi ID faktury
    score = db.Column(db.Integer) # Výsledné skóre (0-1000)
    match_type = db.Column(db.String(50)) # 'exact', 'fuzzy', 'prepayment'
    log_details = db.Column(db.JSON) # Uložíme důvod rozhodnutí
