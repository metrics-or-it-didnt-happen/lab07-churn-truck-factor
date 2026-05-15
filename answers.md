# Lab 07: Code Churn i Truck Factor - kto jest niezastąpiony?

### Ręczna eksploracja projektu `requests` przy użyciu `git log --numstat`

Łączna liczba linii dodanych w projekcie: `159 530`

Łączna liczba linii usuniętych w projekcie: `131 162`

**Kto modyfikował najwięcej plików?**

1. *Kenneth Reitz* (361)
2. *Cory Benfield* (133)
3. *Nate Prewitt* (105)
4. *Ian Cordasco* (100)
5. *Ian Stapleton Cordasco* (44)

**Pliki  z najwyższym churnem (adds + deletes):**

1. `requests/cacert.pem` (23 214)
2. `requests/packages/idna/uts46data.py` (15 268)
3. `ext/requests-logo.ai` (14 432)
4. `requests/models.py` (11 079)
5. `tests/test_requests.py` (7 684)

**1. Które 5 plików zmieniano najczęściej?**
- `requests/models.py` (717 commitów)
- `test_requests.py` (366 commitów)
- `requests/sessions.py` (335 commitów) → 11
- `HISTORY.rst` (319 commitów) → 14
- `requests/utils.py` (271 commitów)
    
**2. Czy te pliki to też te z najwyższym churnem (adds + deletes)?**
- Najczęściej zmieniany plik (`requests/models.py`) jest **czwarty** pod względem największego churnu.
- **Drugi** najczęściej zmieniany plik (`test_requests.py`) jest **szósty** pod względem największego churnu.
- Pozostałe trzy najczęściej modyfikowane pliki **są w drugiej dziesiątce** pod względem największego churnu.
- Podsumowując: *plasują się one na szczycie tabeli po posortowaniu wg churn, ale nie ma tu bezpośrednich zależności, bo inne (rzadziej modyfikowane pliki) mają również porównywalnie wysokie churn.*
    
**3. Ile unikatowych autorów dotknęło plik, który zmienia się najczęściej?** 
    
Plik `requests/models.py` modyfikowało **200 autorów**.
    

### Wnioski o truck factor na podstawie wyników skryptu **`process_metrics.py`**

`requests`

Jeden autor  — *Kenneth Reitz* — dominuje w procesie tworzenia tego projektu. Został on przypisany jako `owner` do 303 spośród 461 plików. Na podstawie `ovnership heatmap` widzimy też, że niektóre katalogi zależą też istotnie od dwóch innych autorów: Nate’a Prewitta i Braulio Valdivielso Martíneza.

`flask`

Projekt ten ma truck factor równy 2, a kluczowi autorzy to *David Lord* i *Armin Ronacher*. Są oni odpowiedzialni za — odpowiednio — 312 i 197 spośród 643 plików, w tym wszystkich zaklasyfikowanych w raporcie jako “najgorętsze” wg churn. Z `ovnership heatmap` wnioskujemy, że kompetencje tych dwóch głównych developerów dotyczyły **różnych katalogów**, ale w każdym katalogu projektu wkład któregoś z nich był bardzo istotny. 

`httpx`

Podobnie jak w pierwszym projekcie, mamy dominację jednego developera — *Toma Christie —* który jest odpowiedzialny na 248 spośród 319 plików. Jest on też przypisany jako `owner` do wszystkich top-20 plików pod względem churn. Jego wkład jest szczególnie istotny w tworzeniu folderów `http3` i `httpcore`, a nie miał on udziału jedynie w pisaniu folderzu `tools` , a który odpowiada *Florimond Manca.*

PODSUMOWANIE: 

W każdym z analizowanych projektów mamy **dominację jednego lub max. dwóch deweloperów**. Gdyby ich zabrakło w dalszych pracach, inni autorzy musieliby polegać na **dokumentacji lub wcześniej wymienionych w ramach zespołu informacjach**, aby dobrze zrozumieć i potencjalnie zmodyfikować duże fragmenty kodu, nad którymi oni głównie pracowali.