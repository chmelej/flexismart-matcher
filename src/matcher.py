from thefuzz import fuzz

def calculate_match_score(transaction, invoice):
    score = 0

    # 1. Variabilní symbol (Klíčový faktor)
    if transaction.v_symbol == invoice.v_symbol:
        score += 500
    elif transaction.v_symbol and invoice.v_symbol:
        # Detekce překlepů (např. 123456 vs 123465)
        if fuzz.ratio(transaction.v_symbol, invoice.v_symbol) > 80:
            score += 100

    # 2. Částka
    if transaction.amount == invoice.amount:
        score += 300
    elif transaction.amount > invoice.amount:
        score += 50 # Potenciální přeplatek

    # 3. Identita (Číslo účtu nebo Jméno)
    if transaction.account_number == invoice.customer_account:
        score += 200
    elif fuzz.partial_ratio(transaction.sender_name, invoice.customer_name) > 85:
        score += 150

    return score
