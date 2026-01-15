import pytest
from src.matcher import calculate_match_score
from collections import namedtuple

# Mocks
Transaction = namedtuple('Transaction', ['v_symbol', 'amount', 'account_number', 'sender_name'])
Invoice = namedtuple('Invoice', ['v_symbol', 'amount', 'customer_account', 'customer_name'])

def test_exact_match():
    # 1. Test Exact Match: Ověření, že 1000 Kč s VS 123 najde fakturu 1000 Kč s VS 123.
    # Score should be high (500 VS + 300 Amount = 800)
    tx = Transaction(v_symbol="123", amount=1000, account_number="111", sender_name="User")
    inv = Invoice(v_symbol="123", amount=1000, customer_account="222", customer_name="User")

    score = calculate_match_score(tx, inv)
    assert score >= 600

def test_fuzzy_name():
    # 2. Test Fuzzy Name: Platba bez VS, ale jméno "Jan Novak" v poznámce vs. Adresář "Jan Novák".
    # Score: VS=0, Amount=300 (assuming amount matches), Name match.
    # Name match > 85 partial ratio => +150
    # Total = 300 + 150 = 450. (This falls into manual review 150-599)

    tx = Transaction(v_symbol=None, amount=1000, account_number="111", sender_name="Jan Novak")
    inv = Invoice(v_symbol="999", amount=1000, customer_account="222", customer_name="Jan Novák")

    score = calculate_match_score(tx, inv)
    assert score >= 150
    assert score < 600

def test_underpayment():
    # 3. Test Underpayment: Platba 900 na fakturu 1000
    # VS match = 500
    # Amount match = 0
    # Identity match (Name "User" vs "User") = 150
    # Total = 650. (Manual review / Partial)

    tx = Transaction(v_symbol="123", amount=900, account_number="111", sender_name="User")
    inv = Invoice(v_symbol="123", amount=1000, customer_account="222", customer_name="User")

    score = calculate_match_score(tx, inv)
    assert score == 650

def test_overpayment():
    # Helper for overpayment scenarios
    # VS match = 500
    # Amount > Invoice => +50
    # Identity match (Name "User" vs "User") = 150
    # Total = 700.

    tx = Transaction(v_symbol="123", amount=1150, account_number="111", sender_name="User")
    inv = Invoice(v_symbol="123", amount=1000, customer_account="222", customer_name="User")

    score = calculate_match_score(tx, inv)
    assert score == 700

def test_multi_invoice():
    # 4. Test Multi-Invoice: Platba 2000 na dvě faktury po 1000 se stejným VS.
    # If 1 TX (2000) vs Invoice A (1000)
    # VS match = 500
    # Amount > Invoice => +50
    # Identity match = 150
    # Total 700.

    tx = Transaction(v_symbol="123", amount=2000, account_number="111", sender_name="User")
    inv1 = Invoice(v_symbol="123", amount=1000, customer_account="222", customer_name="User")

    score = calculate_match_score(tx, inv1)
    assert score == 700
