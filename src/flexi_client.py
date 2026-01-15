import requests
import json

class FlexiClient:
    def __init__(self, url, user, password, company):
        self.base_url = f"{url}/c/{company}"
        self.auth = (user, password)

    def get(self, endpoint, params=None):
        url = f"{self.base_url}/{endpoint}.json"
        response = requests.get(url, auth=self.auth, params=params)
        response.raise_for_status()
        return response.json()

    def post(self, endpoint, data):
        url = f"{self.base_url}/{endpoint}.json"
        response = requests.post(url, auth=self.auth, json=data)
        response.raise_for_status()
        return response.json()

    def put(self, endpoint, data):
        url = f"{self.base_url}/{endpoint}.json"
        response = requests.put(url, auth=self.auth, json=data)
        response.raise_for_status()
        return response.json()

    def fetch_unpaid_invoices(self):
        # GET /faktura-vydana?(stavUhrK is null or stavUhrK = 'stavUhr.cast_uhrazeno')
        query = "(stavUhrK is null or stavUhrK = 'stavUhr.cast_uhrazeno')"
        return self.get("faktura-vydana", params={"detail": "full", "filter": query})

    def fetch_new_payments(self):
        # GET /banka (filtrovat nespárované)
        # Bankovní doklady filtruj na sparovano = false.
        query = "sparovano = false"
        return self.get("banka", params={"detail": "full", "filter": query})

    def post_pairing(self, payment_id, invoice_id, amount=None):
        # Endpoint: PUT /c/{firma}/banka/{id}/sparovani
        url_suffix = f"banka/{payment_id}/sparovani"
        data = {
            "winstrom": {
                "banka": {
                    "id": payment_id,
                    "vazby": [
                        {
                            "uhrazovanyDokl": invoice_id
                        }
                    ]
                }
            }
        }
        return self.put(url_suffix, data)

    def handle_overpayment(self, customer_code, amount, bank_doc_id):
        # 1. Vytvoření ZDP
        zdp_data = {
            "prijata-zaloha": [{
                "typDokl": "code:ZALOHA",
                "firma": f"code:{customer_code}",
                "sumCelkem": str(amount),
                "popis": "Přeplatek k vyúčtování",
                "bezPolozek": True
            }]
        }
        response = self.post("prijata-zaloha", zdp_data)
        # response structure depends on Flexi, usually ['winstrom']['results'][0]['ref']
        zdp_id = response['winstrom']['results'][0]['ref']

        # 2. Spárování banky s novou zálohou
        pairing_data = {
            "vazba-mezi-doklady": [{
                "a": bank_doc_id,
                "b": zdp_id,
                "typVazbyK": "typVazby.uhrada"
            }]
        }
        self.post("vazba-mezi-doklady", pairing_data)
