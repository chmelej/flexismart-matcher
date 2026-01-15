import sys
import unicodedata

def remove_diacritics(text):
    # 1. KROK: Interpretace \uXXXX sekvencí
    # Trik spočívá v zakódování do latin-1 a dekódování přes unicode_escape
    try:
        # Tento krok převede doslovný řetězec '\u00e1' na skutečné 'á'
        text = text.encode('utf-8').decode('unicode_escape')
    except Exception:
        # Pokud by text obsahoval nevalidní escape sekvence, necháme ho v původním stavu
        pass

    # 2. KROK: Odstranění diakritiky
    normalized = unicodedata.normalize('NFD', text)
    # Ponechá pouze znaky, které nejsou "kombinační značky" (diakritika)
    return "".join(c for c in normalized if unicodedata.category(c) != 'Mn')

if __name__ == "__main__":
    # Čtení ze souboru nebo stdin
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            input_data = f.read()
    else:
        input_data = sys.stdin.read()

    # Výpis na standardní výstup (stdout)
    sys.stdout.write(remove_diacritics(input_data))
