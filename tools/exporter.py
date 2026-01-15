import requests
import json

class FlexiExporter:
    def __init__(self, url, user, password, company):
        self.base_url = f"{url}/c/{company}"
        self.auth = (user, password)

    def fetch_data(self, evidence, query):
        url = f"{self.base_url}/{evidence}.json?{query}"
        response = requests.get(url, auth=self.auth)
        return response.json()['winstrom'][evidence]

# Použití pro rok 2025 (příklad)
# exporter = FlexiExporter("https://vase-flexi.cz", "admin", "heslo", "firma_sro")

# Stáhneme neuhrazené/částečně uhrazené faktury a banku
# invoices = exporter.fetch_data("faktura-vydana", "datVyst >= '2025-01-01'")
# bank_data = exporter.fetch_data("banka", "datVyst >= '2025-01-01'")

# with open('raw_invoices.json', 'w') as f: json.dump(invoices, f)
# with open('raw_bank.json', 'w') as f: json.dump(bank_data, f)
