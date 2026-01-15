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

@app.route('/c/<company>/faktura-vydana.json', methods=['GET'])
def get_invoices(company):
    # Simulace filtru pro neuhrazené
    # Log filter params for debug
    print(f"DEBUG: GET /faktura-vydana params: {request.args}")
    return jsonify({"winstrom": {"faktura-vydana": invoices}})

@app.route('/c/<company>/banka.json', methods=['GET'])
def get_bank(company):
    # Log filter params for debug
    print(f"DEBUG: GET /banka params: {request.args}")
    return jsonify({"winstrom": {"banka": bank}})

@app.route('/c/<company>/banka/<id>/sparovani.json', methods=['PUT'])
def put_pairing_specific(company, id):
    # Simulace spárování konkrétního dokladu
    print(f"DEBUG: PUT /banka/{id}/sparovani payload: {request.json}")
    return jsonify({"winstrom": {"results": [{"status": "OK"}]}})

@app.route('/c/<company>/prijata-zaloha.json', methods=['POST'])
def post_zaloha(company):
    # Simulace vytvoření zálohy
    print(f"DEBUG: POST /prijata-zaloha payload: {request.json}")
    # Return a fake ID ref
    return jsonify({"winstrom": {"results": [{"ref": "code:ZDP_MOCK_1", "status": "OK"}]}})

@app.route('/c/<company>/vazba-mezi-doklady.json', methods=['POST'])
def post_vazba(company):
    # Simulace vazby
    print(f"DEBUG: POST /vazba-mezi-doklady payload: {request.json}")
    return jsonify({"winstrom": {"results": [{"status": "OK"}]}})

if __name__ == '__main__':
    app.run(port=5000)
