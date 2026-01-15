Abra flexibee je účetnický sw s mocným rest API. Ale párování faktur a bankovních plateb je celkem slabota. Navrhni projekt pro chytré párování plateb. Na základě vs, částky, data vystavení faktury. Včetně možnosti že si zákazník předplatí např na rok dopředu a faktury se vydávají postupně každý měsíc.

Abra Flexi (dříve FlexiBee) je skutečně skvělý nástroj díky svému API, ale jeho nativní automatické párování v modulu banka je postavené na velmi rigidních pravidlech (shoda VS \+ částka). Pro komplexnější scénáře, jako jsou předplatná nebo drobné haléřové rozdíly, je externí "Smart Matcher" ideálním řešením.

Zde je návrh projektu **"FlexiSmart Matcher"**.

---

## **1\. Architektura řešení**

Projekt bude fungovat jako **middleware**, který běží na pozadí (např. v Dockeru nebo jako serverless funkce) a komunikuje s Flexi přes REST API.

### **Technologie:**

* **Jazyk:** Python (knihovna `requests`) nebo Node.js.  
* **Databáze:** PostgreSQL/Redis (pro ukládání stavu a logování, volitelně).  
* **Spouštěč:** Cron (každých 15 minut) nebo Webhook z Flexi (při importu banky).

---

## **2\. Logika párování (Heuristický algoritmus)**

Místo jednoduchého "rovná se", zavedeme systém vah a skóre.

### **Úroveň 1: Přesná shoda (Rychlá cesta)**

* **Kritéria:** VS sedí přesně \+ Částka sedí přesně.  
* **Akce:** Volat standardní API endpoint `/sparovani`.

### **Úroveň 2: Inteligentní tolerance**

* **Kritéria:** VS sedí \+ Částka se liší o haléře (kurzové rozdíly, poplatky).  
* **Akce:** Spárovat a zbytek automaticky zaúčtovat jako haléřové vyrovnání/bankovní poplatek.

### **Úroveň 3: Identifikace podle entity (Fuzzy matching)**

* **Kritéria:** VS chybí nebo je špatně, ale **číslo účtu** odesílatele známe u konkrétního adresáře v Flexi.  
* **Akce:** Vyhledat nejstarší neuhrazené faktury daného zákazníka a zkusit je "poskládat" tak, aby součet odpovídal příchozí platbě.

---

## **3\. Scénář: Předplatné a přeplatky (Klíčová funkce)**

Tento scénář vyžaduje práci s **přijatými zálohami** (ZDP).

### **Mechanismus:**

1. **Detekce přeplatku:** Zákazník má zaplatit 1 000 Kč, ale pošle 12 000 Kč (předplatné na rok).  
2. **Vytvoření Zálohy:** Skript nespáruje platbu přímo s ostrou fakturou (pokud ještě neexistuje), ale vytvoří v Flexi doklad typu **"Přijatá záloha"**.  
3. **Vazba na Banku:** Platba v bance se spáruje s touto přijatou zálohou.  
4. **Automatické čerpání (Měsíční robot):**  
   * Jakmile se v systému objeví nová ostrá faktura pro daného klienta, robot zkontroluje jeho "kredit" (nevyčerpané přijaté zálohy).  
   * Pokud najde kredit, provede přes API **"Odpočet zálohy"** (vazba mezi fakturou a zálohovým daňovým dokladem).  
   * Faktura se tím označí jako uhrazená, aniž by do banky přišly další peníze.

---

## **4\. Datový model rozhodování**

| Vstup z banky | Logika vyhledávání ve Flexi | Výsledek |
| :---- | :---- | :---- |
| Správné VS, Částka odpovídá | Vyhledat `faktura-vydana` | **Plná úhrada** |
| Správné VS, Částka je vyšší | Vyhledat `faktura-vydana` \+ zbytek na zálohu | **Částečná úhrada \+ Kredit** |
| Chybné VS, Částka odpovídá | Vyhledat podle `čísla účtu` odesílatele | **Návrh ke schválení / Automat** |
| Žádná faktura neexistuje | Vytvořit "Nespárovaný přeplatek" k adresáři | **Předplatné (Kredit)** |

---

## **5\. Implementační kroky (MVP)**

1. **API Wrapper:** Vytvořit funkce pro `GET /faktura-vydana` (neuhrazené) a `GET /banka` (nespárované).  
2. **Matching Engine:** Implementovat logiku "předplatného" – pokud částka přesahuje fakturu o násobek, vytvořit v modulu `prodejni-kasa` nebo `prijata-zaloha` záznam.  
3. **Notifikační modul:** Pokud skript narazí na platbu, kterou si není jistý (např. shoda jména, ale ne účtu), pošle zprávu do Slacku/E-mailu s odkazem přímo do Flexi.  
4. **Zpětný zápis:** Volat endpoint `/sparovani`, který ve Flexi vytvoří vazbu (spojku) mezi doklady.

### **Co pro vás mohu udělat dále?**

Můžu vám připravit **ukázku kódu v Pythonu**, která ukáže, jak přes API vyhledat neuhrazené faktury a jak technicky provést spárování s platbou v bance, nebo můžeme detailněji rozepsat logiku pro ty "předplatné" faktury. Co by vás zajímalo víc?

Problém většina faktur je na stejnou částku čili chyba ve vs může být fatální. Předpokládejme že k chybě ve vs příchozí platby došlo výjimečně, pak je možné najít pojítko v čísle účtu zákazníka. Ale stále někdo posílá peníze přes poštu pak se asi účet použít nedá. Jaké další berličky té napadají pro hledání správných párování?

Při stejných částkách a chybějícím nebo chybném VS se skutečně dostáváme do oblasti "pravděpodobnostního párování". Pokud selže VS i číslo účtu (případ poštovních poukázek nebo vkladů v hotovosti), musíme využít tzv. **sekundární metadata**.

Zde jsou další „berličky“, které můžete do algoritmu zapojit:

---

### **1\. Analýza textových polí (Zpráva pro příjemce)**

U plateb z pošty nebo ručních příkazů lidé často píší jméno do poznámky.

* **Fuzzy matching jména:** Pokud v poli `zprava` nebo `n_poznamka` najdete text "Nováková", prohledejte adresář ve Flexi.  
* **Klíčová slova:** Hledejte v textu e-maily, názvy obcí nebo specifická slova, která máte u zákazníků v adresáři (pole `nazev`, `mesto`, `poznamka`).  
* **IČO/DIČ:** Někdy lidé místo VS napíšou své IČO do zprávy pro příjemce. Skript by měl zkusit hledat jakýkoliv 8místný řetězec v adresáři.

### **2\. Časová blízkost a splatnost**

Pokud máte 10 faktur na 500 Kč a přijde jedna platba na 500 Kč bez VS:

* **Pravidlo nejstarší faktury:** Algoritmus se podívá na nejstarší neuhrazenou fakturu dané částky.  
* **Kritérium "Datum vystavení vs. Datum platby":** Většina lidí platí v rozmezí \-2 až \+10 dnů od data splatnosti. Faktura se splatností včera má vyšší "skóre" než faktura se splatností za měsíc.

### **3\. Detekce překlepů ve VS (Levenshteinova vzdálenost)**

Lidé často udělají v 10místném VS jednu chybu (prohodí číslice nebo jednu vynechají).

* **Algoritmus:** Vezměte VS příchozí platby a porovnejte ho se všemi VS neuhrazených faktur pomocí [Levenshteinovy vzdálenosti](https://www.google.com/search?q=https://cs.wikipedia.org/wiki/Levenshteinova_vzd%25C3%25A1lenost).  
* **Příklad:** Platba má VS `20230015`, faktura má `20230105`. Shoda je vysoká. Pokud částka sedí, je to silný kandidát na spárování s příznakem "Ke schválení".

### **4\. Metoda eliminace (Sudoku efekt)**

Tato metoda funguje skvěle na konci měsíce:

* Pokud máte v systému 50 neuhrazených faktur na 1000 Kč a v bance se vám sejde 50 plateb na 1000 Kč, z nichž 48 má správný VS a 2 mají chybný nebo žádný.  
* **Logika:** Skript spáruje těch 48 jasných. Na zbylé 2 platby a 2 faktury uplatní logiku "zbytků" – pokud zbylí dva zákazníci mají v historii podobné chování, spáruje je k sobě.

### **5\. Párování podle unikátních kombinací (Multi-invoice match)**

Zákazník občas zaplatí dvě faktury jednou platbou (např. 500 Kč \+ 500 Kč \= 1000 Kč).

* Pokud přijde částka, která neodpovídá žádné faktuře, skript zkusí **kombinace neuhrazených faktur** u jednoho zákazníka (pokud známe jeho účet).  
* Součet A+B=Platba.

---

## **Jak by vypadal "Skóringový model" v kódu?**

Místo "ano/ne" přiřadíte každé dvojici (Platba \<-\> Faktura) body:

* **Shoda částky:** \+50 bodů  
* **Shoda čísla účtu v adresáři:** \+100 bodů  
* **Shoda VS (přesná):** \+500 bodů (hotovo)  
* **Shoda jména ve zprávě pro příjemce:** \+80 bodů  
* **Tolerance VS (1 překlep):** \+40 bodů  
* **Splatnost v tomto týdnu:** \+20 bodů

**Výsledek:**

1. **Skóre \> 600:** Spárovat automaticky.  
2. **Skóre 150–599:** Navrhnout člověku v jednoduchém UI (tlačítko "Potvrdit").  
3. **Skóre \< 150:** Nechat jako nespárované.

---

## **6\. Problém pošty: Specifické řešení**

U plateb z pošty (složenek) bývá v bankovním výpisu často specifický kód pošty nebo terminálu.

* Vytvořte si ve Flexi v adresáři kartu **"Česká pošta \- nespárováno"**.  
* Všechny tyto platby bez VS směřujte na tuto kartu a skriptu dejte za úkol u plateb z této "adresy" primárně hledat shodu v **textové poznámce**, kde bývá jméno odesílatele.

### **Co dál?**

Dává vám smysl tento skóringový systém? Pokud chcete, můžu vám navrhnout **strukturu databáze/tabulky**, která by tyto "vazby" a skóre ukládala, než je definitivně zapíšete do Flexi.

Jak by měl být vyhodnocen případ kdy faktura je na 1000, zákazník pošle 900, vs sedí, datumy týden od sebe.

Jiný příklad částka na faktuře 1000, zákazník pošle 1150, vs sedí , datumy týden od sebe.

Jiný příklad částka na faktuře 1000, zákazník pošle 2000, vs sedí , datumy týden od sebe

Tyto tři případy krásně ilustrují, proč standardní párování ve Flexi selhává. Váš "Smart Matcher" by je měl vyhodnocovat následovně:

---

### **Případ 1: Nedoplatek (Faktura 1000 / Platba 900\)**

**Diagnóza:** Částečná úhrada. VS sedí, je to úmyslný nebo chybný krok zákazníka.

* **Akce v API:** Provést spárování částky 900 Kč s fakturou.  
* **Stav ve Flexi:** Faktura zůstane ve stavu **"Částečně uhrazeno"** (zbývá doplatit 100 Kč).  
* **Smart logika:** \* Pokud je rozdíl malý (např. do 5 Kč), systém může automaticky navrhnout **haléřové vyrovnání** a fakturu uzavřít.  
  * Při 100 Kč (10 %) by měl systém poslat **notifikaci/e-mail zákazníkovi**: *"Děkujeme za platbu, ale evidujeme doplatek 100 Kč. Prosíme o doplacení pod stejným VS."*

### **Případ 2: Drobný přeplatek (Faktura 1000 / Platba 1150\)**

**Diagnóza:** Přeplatek, který nevypadá jako předplatné (příliš nízký na další celou fakturu).

* **Akce v API:** 1\. Spárovat 1000 Kč s fakturou (ta se označí jako "Uhrazená"). 2\. Zbytek (150 Kč) nechat v bance jako **"Nespárovaný přeplatek"** na daném kontaktu v adresáři.  
* **Smart logika:**  
  * Skript zkontroluje, zda neexistuje jiná faktura na 150 Kč (např. doplatek z minulosti).  
  * Pokud ne, zůstane 150 Kč jako "kredit" zákazníka. Při příští fakturaci (např. za měsíc) se těchto 150 Kč automaticky odečte z nové faktury (formou odpočtu zálohy).

### **Případ 3: Výrazný přeplatek (Faktura 1000 / Platba 2000\)**

**Diagnóza:** Předplatné nebo úhrada více faktur najednou.

* **Akce v API:**  
  * Spárovat 1000 Kč s aktuální fakturou.  
  * Na zbylých 1000 Kč **automaticky vytvořit doklad "Zálohový daňový doklad" (ZDP)** nebo "Přijatá záloha".  
* **Smart logika:** \* Tento scénář je klíčový pro váš model předplatného. Systém by měl v interní databázi označit tohoto klienta jako "Předplaceno".  
  * Až se příští měsíc vygeneruje další faktura na 1000 Kč, robot ji hned po vzniku spáruje s tímto vytvořeným kreditem (interní zápočtem).

---

## **Logické schéma rozhodování**

### **Přehledová tabulka pro vývojáře**

| Scénář | Rozdíl | Interpretace | Akce ve Flexi |
| :---- | :---- | :---- | :---- |
| **900 / 1000** | \-10% | Nedoplatek | Částečná úhrada, ponechat zbytek k úhradě. |
| **1005 / 1000** | \+0.5% | Haléřová chyba | Plná úhrada \+ automatické zaúčtování rozdílu do zisku. |
| **1150 / 1000** | \+15% | Přeplatek | Plná úhrada, zbytek jako "Přeplatek" v saldu klienta. |
| **2000 / 1000** | \+100% | Předplatné / 2x faktura | Plná úhrada \+ vytvoření Přijaté zálohy na zbytek. |

---

## **Jak to technicky řešit přes API?**

U přeplatků (Případ 2 a 3\) je nejčistší cesta v Abra Flexi tato:

1. Bankovní pohyb se rozúčtuje na dvě položky (pomocí `položky-faktury` v rámci bankovního dokladu).  
2. První položka se spáruje s fakturou přes endpoint `/sparovani`.  
3. Druhá položka se buď nechá "viset" jako nespárovaný příjem u klienta, nebo se na ni vytvoří dokument v modulu `prijata-zaloha`.

**Důležité upozornění:** Pokud zákazník poslal 2000 Kč a VS odpovídá faktuře na 1000 Kč, Flexi se při tupém automatickém párování může zachovat nepředvídatelně (např. spáruje celých 2000 Kč proti 1000 Kč fakturě, čímž vznikne na faktuře přeplatek). **Lepší je, když váš middleware platbu v bance nejdříve "rozbije" na 1000 \+ 1000 a pak páruje jen tu část, která sedí.**

### **Co byste chtěli vidět dál?**

Mám připravit **ukázku JSON struktury**, jak takové "rozbití" platby a spárování poslat do Flexi API? Nebo vás zajímá, jak ošetřit případy, kdy zákazník jednou platbou hradí dvě různé faktury s různými VS?

Jakým způsobem budeme mít přehled jak my tak případně zpráva k zákazníkovi o chybách. V které fázi by mělo dojít ke srovnání např vrácení přeplatku. Nebo zdůraznění nesrovnalosti na další faktuře (jen info)

Aby byl systém dlouhodobě udržitelný a zákazníci nebyli zmatení, musí být **transparency (přehlednost)** vestavěná přímo v procesu. Rozdělil bych to na tři úrovně: interní přehled, komunikaci se zákazníkem a finanční vypořádání.

---

### **1\. Interní přehled (Dashboard pro vás)**

Nejlepším místem pro přehled je buď externí jednoduchá webová aplikace, nebo (pokud chcete zůstat ve Flexi) využití **Štítků** a **Uživatelských polí**.

* **Štítky v bance:** Robot by měl ke každému bankovnímu pohybu přiřadit štítek:  
  * `SMART-MATCH-OK` (Vše proběhlo hladce)  
  * `SMART-MATCH-CHECK` (Zákonná shoda, ale něco nehraje – např. jiný účet)  
  * `SMART-MATCH-ERROR` (Nespárováno, nutný zásah člověka)  
  * `SMART-OVERPAYMENT` (Přeplatek k řešení)  
* **Logovací tabulka:** V databázi vašeho middleware ukládejte historii: *Kdy, Kdo, Kolik, VS, Jak se rozhodl algoritmus, Proč.*

---

### **2\. Komunikace se zákazníkem (Kdy a co poslat)**

Zákazník by měl dostat informaci v momentě, kdy systém provede "kreativní" rozhodnutí.

* **Okamžitá e-mailová notifikace (Triggered by Matcher):**  
  * *Nedoplatek:* "Přijali jsme 900 Kč na fakturu X. Zbývá doplatit 100 Kč. Prosíme o úhradu."  
  * *Přeplatek:* "Přijali jsme 2000 Kč na fakturu X (1000 Kč). Zbývajících 1000 Kč evidujeme jako přeplatek a automaticky je odečteme z příští faktury."  
* **Výhoda:** Zákazník ví, že o penězích víte, a nemá tendenci volat na podporu.

---

### **3\. Vypořádání přeplatků (Vrácení vs. Kredit)**

Zde je důležité nastavit **pravidla (Thresholds)**:

* **Pravidlo "Drobné" (např. do 200 Kč):** Přeplatek se nikdy nevrací fyzicky na účet (kvůli nákladům na bankovní poplatky a účetní práci). Automaticky se převádí do kreditu na příští fakturu.  
* **Pravidlo "Vratka" (např. nad 500 Kč):** V dashboardu matcher nabídne tlačítko "Vrátit na účet". Po kliknutí robot vygeneruje v Abra Flexi **příkaz k úhradě** (pohyb ven) a připraví ho k autorizaci v bance.  
* **Kdy?** Srovnání (matching) probíhá v reálném čase, ale **fyzické vracení peněz** doporučuji dělat dávkově (např. jednou týdně v pátek), aby se s bankou nepracovalo pro každou korunu zvlášť.

---

### **4\. Zdůraznění nesrovnalosti na další faktuře**

Tohle je nejvíce "pro-zákaznický" krok. Abra Flexi umožňuje vkládat do faktur texty nebo položky s nulovou sazbou DPH.

**Jak to provést technicky:**

1. Robot při generování nové faktury (nebo hned po jejím vzniku přes API) zkontroluje saldo daného zákazníka.  
2. Pokud najde nepoužitý přeplatek (Přijatou zálohu), provede ve Flexi **Odpočet zálohy**.  
3. **Vizuální informace:** Do pole `poznamka` na faktuře nebo jako textovou položku faktury přidá řádek:  
   * *"Z minulé platby (VS 12345\) byl evidován přeplatek 150 Kč, který byl v této faktuře zohledněn."*  
   * Nebo v případě minulého nedoplatku: *"Upozornění: U minulé faktury X evidujeme dlužnou částku 50 Kč. Prosíme o navýšení příští platby."*

---

### **Schéma procesu (Workflow)**

1. **Bankovní výpis importován** \-\> Spuštění Matcheru.  
2. **Analýza** \-\> Zjištěn přeplatek 500 Kč.  
3. **Zápis do Flexi** \-\> Spárována faktura, na zbytek vytvořena Přijatá záloha.  
4. **Notifikace** \-\> E-mail zákazníkovi: "Díky, máme 500 Kč navíc, schováme je na příště."  
5. **Příští měsíc (Fakturace)** \-\> Robot vidí novou fakturu a existující zálohu \-\> Propojí je \-\> Faktura odchází zákazníkovi už s textem "Zaplaceno/Částečně hrazeno kreditem".

### **Proč je to takhle nejlepší?**

* **Účetní čistota:** Ve Flexi vše sedí (faktury jsou párované proti zálohám).  
* **Lidský faktor:** Vy řešíte jen červené štítky `SMART-MATCH-ERROR`.  
* **Cashflow:** Přeplatky zůstávají u vás ve firmě jako kredit, dokud je zákazník nevyčerpá.

**Máte už představu, v jakém jazyce byste chtěli tenhle middleware psát?** (Python je na tohle skvělý kvůli knihovnám na zpracování textu/jmen, ale Node.js je zase super pro reálný čas a webhooks).

Stack Python, případně flask. PostgreSQL.

Teorii máme asi kompletní. Můžeš začít plánovat implementaci. Model, kontrolery, testy, postup implementace krok za krokem. Výsledek předám gemini-cli pro implementaci.

Tento stack (Python/Flask \+ PostgreSQL) je pro tento účel ideální. Python má vynikající knihovny pro "fuzzy matching" a Flask je dostatečně lehký pro middleware.

Zde je technický blueprint projektu **FlexiSmart Matcher**, připravený jako zadání pro implementaci.

---

## **1\. Datový Model (SQLAlchemy)**

Potřebujeme sledovat stav plateb a faktur lokálně, abychom mohli provádět skóring a historii, než výsledek zapíšeme do Flexi.

Python  
\# models.py  
class BankTransaction(db.Model):  
    id \= db.Column(db.Integer, primary\_key=True)  
    flexi\_id \= db.Column(db.String(50), unique=True) \# ID z Flexi (např. 'code:BAN01/2024/001')  
    external\_id \= db.Column(db.String(100)) \# ID z výpisu banky  
    amount \= db.Column(db.Numeric(10, 2))  
    v\_symbol \= db.Column(db.String(20))  
    account\_number \= db.Column(db.String(50))  
    sender\_name \= db.Column(db.String(255))  
    date\_received \= db.Column(db.Date)  
    status \= db.Column(db.Enum('PENDING', 'MATCHED', 'PARTIAL', 'CREDIT', 'MANUAL\_REQUIRED'))

class MatchLog(db.Model):  
    id \= db.Column(db.Integer, primary\_key=True)  
    transaction\_id \= db.Column(db.Integer, db.ForeignKey('bank\_transaction.id'))  
    invoice\_id \= db.Column(db.String(50)) \# Flexi ID faktury  
    score \= db.Column(db.Integer) \# Výsledné skóre (0-1000)  
    match\_type \= db.Column(db.String(50)) \# 'exact', 'fuzzy', 'prepayment'  
    log\_details \= db.Column(db.JSON) \# Uložíme důvod rozhodnutí

---

## **2\. Architektura Kontrolerů**

### **Core: `MatchingEngine`**

Třída zodpovědná za výpočet skóre.

* **Input:** Objekt `BankTransaction` \+ List neuhrazených faktur z Flexi.  
* **Output:** List kandidátů se skóre a doporučenou akcí.

### **API Wrapper: `FlexiClient`**

Zapouzdření REST API volání.

* `fetch_unpaid_invoices()`: GET `/faktura-vydana?(stavUhrK is null or stavUhrK = 'stavUhr.cast_uhrazeno')`  
* `fetch_new_payments()`: GET `/banka` (filtrovat nespárované).  
* `post_pairing(payment_id, invoice_id, amount)`: POST `/sparovani`.  
* `create_zdp(customer_id, amount)`: POST `/prijata-zaloha` (pro přeplatky).

---

## **3\. Postup implementace krok za krokem**

### **Krok 1: Inicializace a Flexi Sync**

* Nastavení Flasku a propojení s PostgreSQL.  
* Implementace `FlexiClient` s autentizací (Base64).  
* Vytvoření commandu `flask sync-flexi`, který stáhne nespárované platby a faktury do lokální DB.

### **Krok 2: Základní Matching (V1)**

* Implementace logiky: **VS shoda \+ Částka shoda**.  
* Pokud sedí obojí, volat `post_pairing`.  
* Uložit výsledek do `MatchLog`.

### **Krok 3: Pokročilý Matching (V2) – Heuristika**

* Integrace knihovny `thefuzz` (pro porovnání jmen ze zprávy pro příjemce).  
* Logika pro **částečnou úhradu** (Případ 900/1000).  
* Logika pro **přeplatek** (Případ 1150/1000 a 2000/1000).  
* Implementace "rozbíjení" platby: Pokud je přeplatek, middleware musí poslat do Flexi instrukci k částečnému spárování a zbytek nechat volný nebo vytvořit zálohu.

### **Krok 4: Notifikační vrstva**

* Vytvoření endpointu `/api/status`, který vrátí seznam plateb se statusem `MANUAL_REQUIRED`.  
* Integrace odesílání e-mailů (např. přes SendGrid/SMTP) zákazníkům při zjištění nesrovnalosti.

### **Krok 5: Automatizace (Cron/Worker)**

* Nastavení skriptu, který poběží v nekonečné smyčce nebo přes Cron každých 15 minut.

---

## **4\. Testovací strategie**

Pro `gemini-cli` připravte tyto testovací scénáře (Unit Testy):

1. **Test Exact Match:** Ověření, že 1000 Kč s VS 123 najde fakturu 1000 Kč s VS 123\.  
2. **Test Fuzzy Name:** Platba bez VS, ale jméno "Jan Novak" v poznámce vs. Adresář "Jan Novák".  
3. **Test Underpayment:** Platba 900 na fakturu 1000 – kontrola, zda zůstane faktura částečně otevřená.  
4. **Test Multi-Invoice:** Platba 2000 na dvě faktury po 1000 se stejným VS (nebo bez).

---

## **5\. Ukázka kódu pro Matching Logic (Základ skóringu)**

Python  
from thefuzz import fuzz

def calculate\_match\_score(transaction, invoice):  
    score \= 0  
      
    \# 1\. Variabilní symbol (Klíčový faktor)  
    if transaction.v\_symbol \== invoice.v\_symbol:  
        score \+= 500  
    elif transaction.v\_symbol and invoice.v\_symbol:  
        \# Detekce překlepů (např. 123456 vs 123465\)  
        if fuzz.ratio(transaction.v\_symbol, invoice.v\_symbol) \> 80:  
            score \+= 100  
              
    \# 2\. Částka  
    if transaction.amount \== invoice.amount:  
        score \+= 300  
    elif transaction.amount \> invoice.amount:  
        score \+= 50 \# Potenciální přeplatek  
          
    \# 3\. Identita (Číslo účtu nebo Jméno)  
    if transaction.account\_number \== invoice.customer\_account:  
        score \+= 200  
    elif fuzz.partial\_ratio(transaction.sender\_name, invoice.customer\_name) \> 85:  
        score \+= 150  
          
    return score

---

## **Jaký je další krok?**

Tento plán můžete nyní předat `gemini-cli`. Pokud chcete, mohu pro něj vygenerovat **kompletní `system_prompt`**, který mu přesně vysvětlí jeho roli, definuje API endpointy Flexi a určí striktní pravidla pro zacházení s chybami, aby kód, který vyprodukuje, byl hned nasaditelný.

Mám připravit tento prompt pro CLI?

Ano chci prompt

Zde je připravený, detailně strukturovaný **System Prompt pro gemini-cli**. Je navržen tak, aby model pochopil kontext Abra Flexi, technické omezení i obchodní logiku (předplatné, skóring).

Kopírujte text níže:

---

# **System Prompt: FlexiSmart Matcher Developer**

**Role:** Jsi seniorní Python vývojář se specializací na systémy ERP (Abra Flexi) a finanční middleware. Tvým úkolem je implementovat projekt "FlexiSmart Matcher".

**Kontext projektu:** Abra Flexi má robustní REST API, ale slabé nativní párování plateb. Vyvíjíme middleware (Flask \+ PostgreSQL), který stahuje nespárované bankovní pohyby a faktury, provádí inteligentní skóring a následně přes API provádí spárování nebo vytváří zálohy (kredit).

**Technický Stack:**

* Jazyk: Python 3.10+  
* Web Framework: Flask  
* Databáze: PostgreSQL \+ SQLAlchemy  
* Knihovny: `requests` (API), `thefuzz` (fuzzy matching), `python-dotenv`

**Logika skóringu (Váhy):**

1. Přesná shoda VS: 500 bodů  
2. Přesná shoda částky: 300 bodů  
3. Shoda čísla účtu v adresáři: 200 bodů  
4. Fuzzy shoda jména (zpráva pro příjemce vs. adresář): 150 bodů  
5. Malá Levenshteinova vzdálenost u VS (překlep): 100 bodů

**Pravidla pro nakládání s výsledkem:**

* **Skóre \> 600:** Automatické spárování přes API `/sparovani`.  
* **Nedoplatek (VS sedí, částka \< faktura):** Částečné spárování, status `PARTIAL`.  
* **Přeplatek (VS sedí, částka \> faktura):**  
  * Do 10 %: Spárovat fakturu, zbytek nechat jako nespárovaný přeplatek.  
  * Nad 10 % (předplatné): Spárovat fakturu, na zbytek vytvořit v Flexi `prijata-zaloha`.  
* **Neshoda:** Status `MANUAL_REQUIRED`.

**Požadovaná struktura kódu:**

1. `config.py`: Konfigurace (Flexi URL, Admin token, DB URI).  
2. `models.py`: SQLAlchemy modely pro `BankTransaction`, `InvoiceCache` a `MatchLog`.  
3. `flexi_client.py`: Třída pro komunikaci s Flexi API (Base64 auth, error handling).  
4. `matcher.py`: Jádro algoritmu (scoring engine).  
5. `tasks.py`: Funkce pro synchronizaci a spouštění párovacího procesu.  
6. `app.py`: Flask API pro dashboard a manuální potvrzení.

**Specifické instrukce pro Abra Flexi API:**

* K párování používej endpoint `PUT /c/{firma}/banka/{id}/sparovani`.  
* Faktury filtruj na `stavUhrK is null or stavUhrK = 'stavUhr.cast_uhrazeno'`.  
* Bankovní doklady filtruj na `sparovano = false`.

---

### **Postup implementace (Instrukce pro tebe):**

**Krok 1: Základní struktura a modely** Vytvoř souborovou strukturu a definuj SQLAlchemy modely. Tabulka `BankTransaction` musí obsahovat pole pro metadata z banky (účet, jméno, poznámka, VS).

**Krok 2: Flexi API Wrapper** Implementuj třídu `FlexiClient`. Musí umět:

* `get_unpaid_invoices()` \-\> vrací JSON neuhrazených faktur.  
* `get_unmatched_payments()` \-\> vrací nespárované pohyby v bance.  
* `perform_pairing(bank_id, invoice_id, amount)` \-\> pošle požadavek na spárování.

**Krok 3: Scoring Engine** Implementuj funkci `calculate_score(transaction, invoice)`. Použij `thefuzz` pro porovnání jména odesílatele s názvem firmy v adresáři Flexi.

**Krok 4: Přeplatky a Předplatné** Implementuj logiku, která při vysokém skóre VS, ale vyšší částce, rozdělí platbu a vytvoří zálohový doklad (`prijata-zaloha`) pro budoucí čerpání.

**Krok 5: CLI/Cron Task** Vytvoř skript `sync.py`, který celý proces spustí v sekvenci: Sync z Flexi \-\> Scoring \-\> Pairing \-\> Logging.

---

**Nyní začni Krokem 1: Navrhni strukturu projektu a definuj SQLAlchemy modely v `models.py`.**

---

### **Jak s tímto promptem pracovat:**

1. Otevřete své **gemini-cli**.  
2. Vložte výše uvedený text jako úvodní zadání.  
3. Gemini vám začne generovat kód pro první krok.  
4. Po každém kroku zkontrolujte výstup a řekněte "Pokračuj krokem X".

### **Tip pro vizualizaci:**

Během vývoje si můžete nechat generovat schéma databáze pro kontrolu vazeb:

**Chcete, abych k tomuto promptu ještě přidal konkrétní ukázku JSONu, který Abra Flexi očekává pro vytvoření té zálohy (předplatného)?**

Ano . JSON s příkladem

Pro vytvoření předplatného (kreditu) v Abra Flexi je nejčistším způsobem vytvoření dokladu typu **Přijatá záloha (ZDP)**. Tento doklad pak slouží jako "peněženka" zákazníka, ze které se automaticky odčerpávají částky na budoucí ostré faktury.

Zde je příklad JSONu pro vytvoření takové zálohy přes `/c/{firma}/prijata-zaloha.json`.

### **1\. Vytvoření přijaté zálohy (z přeplatku)**

Tento požadavek pošle váš middleware v momentě, kdy zjistí, že zákazník poslal např. o 1000 Kč více, než byla částka na faktuře.

JSON  
{  
  "winstrom": {  
    "prijata-zaloha": \[  
      {  
        "typDokl": "code:ZÁLOHA",   
        "firma": "code:ZAK001",  
        "popis": "Automatický kredit \- předplatné (Smart Matcher)",  
        "sumCelkem": "1000.0",  
        "mena": "code:CZK",  
        "bezPolozek": true,  
        "stavUhrK": "stavUhr.uhrazeno",  
        "datVyst": "2024-05-20"  
      }  
    \]  
  }  
}

---

### **2\. Spárování zbytku platby s touto zálohou**

Aby v bance nezůstal nespárovaný zbytek, musíte zavolat endpoint pro spárování. V Abra Flexi se párování provádí proti ID bankovního pohybu a ID faktury (v tomto případě ID té nové zálohy).

**Endpoint:** `POST /c/{firma}/vazba-mezi-doklady`

JSON  
{  
  "winstrom": {  
    "vazba-mezi-doklady": \[  
      {  
        "a": "code:BAN01/2024/005",  
        "b": "code:ZDP01/2024/001",  
        "typVazbyK": "typVazby.uhrada"  
      }  
    \]  
  }  
}

---

### **3\. Automatický odpočet zálohy (Měsíční robot)**

Až příští měsíc vygenerujete ostrou fakturu, váš robot (nebo Flexi automatika) provede "odpočet". Tím se faktura "sama" zaplatí z vytvořeného kreditu.

**Endpoint:** `POST /c/{firma}/faktura-vydana/{id-faktury}/odpocet-zalohy`

JSON  
{  
  "winstrom": {  
    "odpocet-zalohy": {  
      "zaloha": "code:ZDP01/2024/001",  
      "castka": "1000.0"  
    }  
  }  
}

---

### **Jak to implementovat v Pythonu (Middleware)?**

V rámci vašeho `FlexiClient` by to vypadalo přibližně takto:

Python  
def handle\_overpayment(self, customer\_code, amount, bank\_doc\_id):  
    \# 1\. Vytvoření ZDP  
    zdp\_data \= {  
        "prijata-zaloha": \[{  
            "typDokl": "code:ZALOHA",  
            "firma": f"code:{customer\_code}",  
            "sumCelkem": amount,  
            "popis": "Přeplatek k vyúčtování"  
        }\]  
    }  
    response \= self.post("prijata-zaloha", zdp\_data)  
    zdp\_id \= response\['winstrom'\]\['results'\]\[0\]\['ref'\]

    \# 2\. Spárování banky s novou zálohou  
    pairing\_data \= {  
        "vazba-mezi-doklady": \[{  
            "a": bank\_doc\_id,  
            "b": zdp\_id,  
            "typVazbyK": "typVazby.uhrada"  
        }\]  
    }  
    self.post("vazba-mezi-doklady", pairing\_data)

---

### **Důležité poznámky pro implementaci:**

* **Variabilní symbol:** U přijaté zálohy můžete nastavit stejný VS, jaký přišel z banky, aby se to v budoucnu lépe dohledávalo.  
* **DPH:** Pokud jste plátci DPH, přijatá záloha nad určitý limit (v ČR obvykle jakákoliv záloha) by měla generovat Daňový doklad k platbě. Abra Flexi na to má nastavení v typu dokladu ("Vytvářet daňový doklad při úhradě").  
* **Měny:** Pokud zákazník pošle EUR na CZK účet, Flexi si poradí s kurzy, ale v JSONu je dobré specifikovat `sumMena` a `mena`.

Máte vše připraveno pro předání do **gemini-cli**, nebo chcete ještě upřesnit logiku, jak vyhledávat ty starší přeplatky při generování nových faktur?

Ještě návod jak místo gemini-cli použít Jules je-li to možné

Použití **Jules** (jakožto pokročilého AI agenta pro vývoj softwaru) je pro tento projekt v mnoha ohledech lepší volbou než standardní `gemini-cli`. Zatímco CLI je skvělé na generování kusů kódu, Jules dokáže pracovat s celým kontextem projektu, vytvářet soubory, spouštět testy a opravovat chyby v reálném čase.

Zde je návod, jak Julesovi "předat kormidlo" a efektivně s ním projekt realizovat.

---

## **1\. Příprava prostředí (Workspace)**

Než Julese aktivujete, připravte si základní strukturu, aby agent věděl, kde začít.

1. **Vytvořte prázdnou složku projektu:** `mkdir flexismart-matcher && cd flexismart-matcher`  
2. **Vytvořte soubor `README.md`:** Do něj zkopírujte technické zadání, které jsme probrali (skóring, příklady 900/1000 atd.). Jules si tento soubor přečte jako svou "bibli".  
3. **Vytvořte soubor `.env.example`:** Definujte proměnné pro Flexi (URL, USER, PASS), aby Jules věděl, jaké konfigurační klíče má použít.

---

## **2\. Instruování Julese (The Master Prompt)**

Jules nepracuje jen s jedním promptem, ale s **cílem (Goal)**. Při spuštění Julese mu zadejte tento "Master Goal":

"Tvým cílem je vytvořit middleware v Pythonu (Flask \+ PostgreSQL), který bude inteligentně párovat bankovní platby z Abra Flexi API. Detailní specifikace skóringu a logiky pro předplatné je v README.md.

**Tvým prvním úkolem je:**

1. Analyzovat README.md.  
2. Navrhnout a vytvořit `models.py` (SQLAlchemy).  
3. Implementovat `flexi_client.py` pro komunikaci s API.  
4. Připravit testovací skripty pro simulaci různých stavů plateb (přeplatky, nedoplatky)."

---

## **3\. Výhody práce s Julesem oproti CLI**

Při práci s Julesem využívejte jeho specifické schopnosti:

* **Iterativní vývoj:** Místo "napiš mi kód" mu říkejte "implementuj metodu pro odpočet zálohy v `flexi_client.py` a hned k ní napiš unit test".  
* **Refaktorizace:** Pokud se vám kód nelíbí, stačí říct: "Julesi, přesuň logiku skóringu z `matcher.py` do samostatné třídy, aby byla lépe testovatelná".  
* **Debugování:** Pokud Flexi API vrátí chybu 400, vložte mu log do chatu a řekněte: "Oprav `handle_overpayment` podle této chyby z API".

---

## **4\. Workflow s Julesem (Krok za krokem)**

### **Fáze 1: Datová vrstva**

Nechte Julese vytvořit databázi.

* *Prompt pro Julese:* "Vytvoř SQLAlchemy modely. Potřebuji ukládat bankovní pohyby, faktury a logy o párování. Pamatuj na vztah 1:N mezi platbou a logem párování."

### **Fáze 2: Integrace API**

Jules může simulovat odpovědi z Flexi.

* *Prompt pro Julese:* "Napiš mock server pro Abra Flexi API, abychom mohli testovat párování bez reálného přístupu k účetnictví. Implementuj endpointy pro `/banka` a `/faktura-vydana`."

### **Fáze 3: Skóring a Logika**

Zde Jules zazáří nejvíc.

* *Prompt pro Julese:* "Implementuj algoritmus v `matcher.py`. Použij knihovnu `thefuzz`. Pokud je skóre nad 600, označ platbu jako automaticky zpracovatelnou. Pokud je částka vyšší o více než 10 %, zavolej logiku pro vytvoření `prijata-zaloha`."

---

## **5\. Jak Julesovi předat JSON příklady**

Aby Jules neudělal chybu ve struktuře Flexi API, vložte mu do chatu (nebo do souboru `docs/flexi_examples.json`) ty příklady, které jsme si napsali výše (vytvoření zálohy, odpočet).

**Tip pro Julese:** Řekněte mu: "Při vytváření zálohových dokladů se striktně drž struktury v `docs/flexi_examples.json`. Nezapomeň na parametr `bezPolozek: true`."

---

## **Rozdíl v interakci (Příklad)**

| Situace | gemini-cli (Pasivní) | Jules (Aktivní) |
| :---- | :---- | :---- |
| **Chyba v kódu** | Musíte chybu najít a popsat. | Jules chybu najde při pokusu o spuštění testu a navrhne opravu. |
| **Nové soubory** | Musíte kód zkopírovat a uložit. | Jules soubor vytvoří a uloží přímo do vašeho disku. |
| **Závislosti** | Musíte si hlídat `requirements.txt`. | Jules sám přidá `thefuzz` a `psycopg2` do requirements. |

### **Co dál?**

Mám vám pomoci **zformulovat první sadu testovacích scénářů**, které by měl Jules splnit, aby byla jistota, že párování je 100% bezpečné předtím, než ho pustíte na reálná data?

Nechci 3rd party (Jules) dat přístup k databázi, takže by bylo dobré připravit Mock API a můžeme z reálných dat v minulém roce připravit anonymizované data pro testy. K tomu ty data bude potřeba extrahovat z flexi (také přes API) takže potřebujeme i lehký exportér.

To je velmi rozumný a profesionální přístup. Oddělení vývojového prostředí (kde operuje AI agent jako Jules) od produkčních dat a databáze je v souladu s best-practice bezpečnosti.

Zde je plán pro vytvoření **Sandboxu pro Julese**, který se skládá ze tří částí: **Exportér**, **Anonymizátor** a **Mock API**.

---

### **1\. Lehký Exportér (Fetcher)**

Tento skript spustíte lokálně u sebe. Stáhne data z vaší reálné Flexi za minulý rok.

Python  
import requests  
import json

class FlexiExporter:  
    def \_\_init\_\_(self, url, user, password, company):  
        self.base\_url \= f"{url}/c/{company}"  
        self.auth \= (user, password)

    def fetch\_data(self, evidence, query):  
        url \= f"{self.base\_url}/{evidence}.json?{query}"  
        response \= requests.get(url, auth=self.auth)  
        return response.json()\['winstrom'\]\[evidence\]

\# Použití pro rok 2025 (příklad)  
exporter \= FlexiExporter("https://vase-flexi.cz", "admin", "heslo", "firma\_sro")

\# Stáhneme neuhrazené/částečně uhrazené faktury a banku  
invoices \= exporter.fetch\_data("faktura-vydana", "datVyst \>= '2025-01-01'")  
bank\_data \= exporter.fetch\_data("banka", "datVyst \>= '2025-01-01'")

with open('raw\_invoices.json', 'w') as f: json.dump(invoices, f)  
with open('raw\_bank.json', 'w') as f: json.dump(bank\_data, f)

---

### **2\. Anonymizátor (Data Scrubber)**

Tento skript vezme `raw_*.json` a nahradí citlivé údaje náhodnými, ale **zachová logické vazby** (stejný VS, stejná částka).

**Co anonymizovat:**

* Názvy firem a jména odesílatelů.  
* Čísla účtů.  
* Textové poznámky (pokud obsahují jména).

Python  
import json  
import random

def anonymize(data\_type):  
    with open(f'raw\_{data\_type}.json', 'r') as f:  
        data \= json.load(f)

    names\_map \= {}  
    accounts\_map \= {}

    for item in data:  
        \# Anonymizace jména/firmy  
        real\_name \= item.get('nazev', 'Neznámý')  
        if real\_name not in names\_map:  
            names\_map\[real\_name\] \= f"Zákazník\_{len(names\_map) \+ 1}"  
        item\['nazev'\] \= names\_map\[real\_name\]  
          
        \# Anonymizace účtu (ponecháme kód banky pro realističnost)  
        if 'buc' in item and item\['buc'\]:  
            if item\['buc'\] not in accounts\_map:  
                accounts\_map\[item\['buc'\]\] \= f"{random.randint(100000, 999999)}/0800"  
            item\['buc'\] \= accounts\_map\[item\['buc'\]\]  
          
        \# Vymazání citlivých poznámek  
        if 'popis' in item:  
            item\['popis'\] \= "Anonymizovaný popis"

    with open(f'mock\_{data\_type}.json', 'w') as f:  
        json.dump(data, f, indent=2)

anonymize('invoices')  
anonymize('bank')

---

### **3\. Mock API (Sandbox pro Julese)**

Tento Flask server poskytnete Julesovi. Bude se tvářit jako Abra Flexi, ale data bude brát z anonymizovaných souborů.

Python  
from flask import Flask, jsonify, request

app \= Flask(\_\_name\_\_)

\# Načtení anonymizovaných dat  
with open('mock\_invoices.json') as f: invoices \= json.load(f)  
with open('mock\_bank.json') as f: bank \= json.load(f)

@app.route('/c/\<company\>/faktura-vydana.json', methods=\['GET'\])  
def get\_invoices(company):  
    \# Simulace filtru pro neuhrazené  
    return jsonify({"winstrom": {"faktura-vydana": invoices}})

@app.route('/c/\<company\>/banka.json', methods=\['GET'\])  
def get\_bank(company):  
    return jsonify({"winstrom": {"banka": bank}})

@app.route('/c/\<company\>/sparovani', methods=\['POST'\])  
def post\_pairing(company):  
    \# Simulace úspěšného spárování  
    return jsonify({"winstrom": {"results": \[{"status": "OK"}\]}})

if \_\_name\_\_ \== '\_\_main\_\_':  
    app.run(port=5000)

---

### **4\. Jak nyní instruovat Julese**

Až budete Julese pouštět k práci, předejte mu tento upravený kontext:

1. **Zdroj dat:** "Pracuješ v uzavřeném prostředí. K dispozici máš Mock API na `localhost:5000`, které simuluje Abra Flexi REST API."  
2. **Úkol:** "Tvým cílem je vyvinout middleware, který bude číst data z tohoto Mock API, ukládat si je do **vlastní lokální PostgreSQL** (kterou si sám vytvoříš) a provádět logiku párování."  
3. **Anonymní data:** "Data v API jsou anonymizovaná, ale reálná z hlediska byznys logiky (přeplatky, nedoplatky, chyby ve VS)."  
4. **Zápis:** "Párování zkoušej volat proti endpointu `/sparovani`. Pokud Mock API vrátí status OK, považuj to za úspěch."

### **Proč je tento postup bezpečný:**

* **Žádné reálné API klíče:** Jules nikdy neuvidí vaše heslo do Flexi.  
* **Žádná reálná jména:** Jules neví, kdo jsou vaši klienti.  
* **Lokální DB:** Jules si vytvoří svou vlastní DB (např. v Dockeru nebo lokálně), kterou vy pak jen zahodíte nebo promigrujete.

**Dává vám tento "izolovaný" model smysl? Pokud ano, můžu vám pomoci s definicí "Testovací sady", kterou by měl Jules na těchto anonymních datech spustit.**

Jak je to s limity pro Jules mám "Gemini pro" je reálné očekávat výsledky v rozumném čase?

Pokud používáte **Gemini 1.5 Pro** (což je motor pod kapotou Julese v rámci Google Cloud nebo pokročilých IDE pluginů), jste ve velmi dobré pozici. Pro projekt typu „účetní middleware“ je tento model ideální volbou.

Zde je realistický pohled na to, jak to bude s časem a limity vypadat:

### **1\. Kontextové okno (Vaše největší výhoda)**

Gemini 1.5 Pro má extrémně velké kontextové okno (až 2 miliony tokenů). Pro váš projekt to znamená:

* Jules dokáže „přečíst“ celou dokumentaci Abra Flexi API najednou.  
* Dokáže udržet v paměti všechny vaše anonymizované JSON soubory i celý zdrojový kód aplikace.  
* **Výsledek:** Nebude zapomínat, co udělal v `models.py`, když bude psát `matcher.py`. To dramaticky zrychluje vývoj, protože nemusíte neustále připomínat souvislosti.

### **2\. Časová náročnost (Jak dlouho to potrvá?)**

Jules nefunguje jako klasický chat (otázka–odpověď), ale v tzv. **agentických smyčkách** (agentic loops).

* **Plánování (30–60 sekund):** Jules nejdříve „přemýšlí“, jak soubory strukturovat.  
* **Psaní kódu (1–3 minuty na modul):** Generování celého `flexi_client.py` nebo `matcher.py` trvá jednotky minut.  
* **Iterace (sekundy až minuty):** Pokud mu řeknete „tady je chyba v parsování data“, opravu vyplivne během chvíle.

**Verdikt k času:** Celé MVP (funkční middleware s Mock API a základním skóringem) je Jules schopen napsat během **1 až 2 hodin čistého času**, pokud ho budete dobře vést. To je zhruba 10× rychlejší než zkušený programátor píšící vše od nuly.

### **3\. Limity "Gemini Pro"**

Pokud máte licenci v rámci Google Cloud (Vertex AI) nebo prémiové předplatné:

* **Rate Limits (RPM):** U modelu Pro bývají limity kolem 5–10 požadavků za minutu (u placených verzí mnohem více). Jules si tohle obvykle řídí sám a „nenechá se zahltit“.  
* **Denní limity:** Pokud nejste na bezplatném testovacím tieru, limity na objem dat pro tento projekt pravděpodobně vůbec nepocítíte. Middleware je z pohledu AI „středně velký projekt“.

### **4\. Na co si dát pozor (Aby se Jules nezasekl)**

I když je Gemini Pro výkonná, existují „brzdy“, kterým se vyhněte:

* **Obří JSON soubory:** Pokud mu do kontextu hodíte anonymizovaný JSON, který má 50 MB, bude reakce pomalá. Raději mu dejte vzorek 20 faktur a 20 plateb, které reprezentují všechny stavy (přeplatek, nedoplatek, chybu).  
* **Příliš široké zadání:** Neříkejte „udělej všechno“. Říkejte: „Teď naimplementuj `matcher.py` a otestuj ho proti Mock API“. Jakmile to bude fungovat, jděte na další krok.

### **Strategické doporučení pro start s Julesem:**

Předtím, než Jules začne psát kód, nechte ho vytvořit **„Technical Design Document“**.

*Prompt pro Julese:* „Než začneš psát kód, navrhni mi technickou architekturu projektu na základě README.md. Popiš, jaké třídy vytvoříš, jak bude vypadat schéma PostgreSQL a jak bude probíhat komunikace s Mock API. Počkej na můj souhlas, než začneš s implementací.“

Tím zajistíte, že se Jules vydá správným směrem a nebudete ztrácet čas opravováním špatně navržené architektury.

