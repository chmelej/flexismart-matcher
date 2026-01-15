import requests
import json
import urllib3
import os
from dotenv import load_dotenv

load_dotenv()  # Načte soubor .env do systémových proměnných

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class FlexiExporter:
    def __init__(self, url, user, password, company):
        self.base_url = f"{url}/c/{company}"
        self.auth = (user, password)

    def fetch_data(self, evidence, query):
        # Sestavení URL podle konvence FlexiBee: evidence/(podminka).json
        if query:
            url = f"{self.base_url}/{evidence}/({query}).json?limit=100"
        else:
            url = f"{self.base_url}/{evidence}.json"
        print(f"DEBUG: Volám URL: {url}") # Pro kontrolu v konzoli

        response = requests.get(url, auth=self.auth, verify=False)
        try:
            data = response.json()

            # Kontrola, zda v odpovědi skutečně je to, co čekáme
            if 'winstrom' in data and evidence in data['winstrom']:
                return data['winstrom'][evidence]
            else:
                # Pokud to není v datech, vypíšeme, co server poslal
                print(f"\n--- CHYBA: Evidence '{evidence}' nenalezena v odpovědi ---")
                print(f"URL: {url}")
                print(f"Status: {response.status_code}")
                print("Odpověď serveru:")
                print(json.dumps(data, indent=4, ensure_ascii=False))
                return None

        except json.JSONDecodeError:
            print(f"\n--- CHYBA: Server nevrátil validní JSON ---")
            print(f"Status: {response.status_code}")
            print(f"Raw body: {response.text}")
            return None

# Použití pro rok 2025 (příklad)
exporter = FlexiExporter( url=os.getenv("FLEXI_URL"), user=os.getenv("FLEXI_USER"), password=os.getenv("FLEXI_PASSWORD"), company=os.getenv("FLEXI_COMPANY"))

# Stáhneme neuhrazené/částečně uhrazené faktury a banku
invoices = exporter.fetch_data("faktura-vydana", "datVyst gt '2025-12-01'")
bank_data = exporter.fetch_data("banka", "datVyst eq '2025-12-01'")

with open('raw_invoices.json', 'w') as f: json.dump(invoices, f)
with open('raw_bank.json', 'w') as f: json.dump(bank_data, f)
