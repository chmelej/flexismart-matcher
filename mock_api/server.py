from flask import Flask, jsonify, request
import json

app = Flask(__name__)

# Načtení anonymizovaných dat
invoices = []
bank = []

try:
    with open('mock_invoices.json') as f: invoices = json.load(f)
except FileNotFoundError:
    print("Warning: mock_invoices.json not found. Serving empty list.")

try:
    with open('mock_bank.json') as f: bank = json.load(f)
except FileNotFoundError:
    print("Warning: mock_bank.json not found. Serving empty list.")

@app.route('/c/<company>/faktura-vydana/<cond>.json', methods=['GET'])
def get_invoices(company,cond):
    # Simulace filtru pro neuhrazené
    return jsonify({"winstrom": {"faktura-vydana": invoices}})

@app.route('/c/<company>/banka/<cond>.json', methods=['GET'])
def get_bank(company,cond):
    return jsonify({"winstrom": {"banka": bank}})

@app.route('/c/<company>/sparovani', methods=['POST'])
def post_pairing(company):
    # Simulace úspěšného spárování
    return jsonify({"winstrom": {"results": [{"status": "OK"}]}})

if __name__ == '__main__':
    app.run(port=5000)
