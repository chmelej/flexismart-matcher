import json
import random

def anonymize(data_type):
    try:
        with open(f'raw_{data_type}.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"File raw_{data_type}.json not found.")
        return

    names_map = {}
    accounts_map = {}

    for item in data:
        # Anonymizace jména/firmy
        real_name = item.get('nazev', 'Neznamy')
        if real_name not in names_map:
            names_map[real_name] = f"Zákazník_{len(names_map) + 1}"
        item['nazev'] = names_map[real_name]

        # Anonymizace účtu (ponecháme kód banky pro realističnost)
        if 'buc' in item and item['buc']:
            if item['buc'] not in accounts_map:
                accounts_map[item['buc']] = f"{random.randint(100000, 999999)}/0800"
            item['buc'] = accounts_map[item['buc']]

        # Vymazání citlivých poznámek
        if 'popis' in item:
            item['popis'] = "Anonymizovany popis"

    with open(f'mock_{data_type}.json', 'w') as f:
        json.dump(data, f, indent=2)

anonymize('invoices')
anonymize('bank')
