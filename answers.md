1. Które 5 plików zmieniano najczęściej?

5 najczesciej zmienianych plikow:

    717 requests/models.py
    366 test_requests.py
    335 requests/sessions.py
    319 HISTORY.rst
    271 requests/utils.py

2. Czy te pliki to też te z najwyższym churnem (adds + deletes)?

TOP 15 plików po churnie:

```bash
git log --numstat --format="" \
| awk '
NF==3 {
    churn[$3] += $1 + $2
}
END {
    for (f in churn)
        print churn[f], f
}' \
| sort -rn \
| head -15
```

23214 requests/cacert.pem
15268 requests/packages/idna/uts46data.py
14432 ext/requests-logo.ai
11079 requests/models.py
7279 tests/test_requests.py
6490 test_requests.py
6288 requests/packages/idna/idnadata.py
5443 Pipfile.lock
4686 requests/packages/urllib3/connectionpool.py
4266 requests/sessions.py
4041 requests/utils.py
3963 requests/packages/chardet/mbcssm.py
3793 requests/core.py
3657 HISTORY.rst
3117 docs/user/advanced.rst

Większość najczęściej modyfikowanych plików znajduje się również wśród plików o największym churnie. Liczba zmian ma korelacje z częstotliwością zmian, ale duża ilość zmian może być również u dużego plika który nigdy nie był zmieniany poza stworzeniem. Takie rzeczy mogą podnosić chunk.

3. Ile unikatowych autorów dotknęło plik, który zmienia się najczęściej?

194 Osoby zmienały plik `requests/models.py`, który jest najczęściej zmieniany w repozytorium. Ten wynik może być nie dokladny ponieważ liczy liczbę osób komity których zawirały ten plik (w tym merge itd).

```bash
top_file=$(git log --name-only --pretty=format: \
| grep -v '^$' \
| sort \
| uniq -c \
| sort -rn \
| head -1 \
| awk '{print $2}')
git log --format='%aN' -- "$top_file" \
| sort -u \
| wc -l
```


--- Truck Factor ---
  Truck factor: 1
  Kluczowi developerzy:
    Kenneth Reitz (owner 308 plików)

Wniosek 
Uzyskany wynik truck factor = 1 może sugerować silną koncentrację wiedzy projektowej wokół jednego głównego developera, jednak wynik należy interpretować ostrożnie, ponieważ Requests jest dużym projektem open-source rozwijanym przez wielu współtwórców.
# Niski truck factor oznacza wysokie ryzyko

*Jeżeli:*

tylko jedna osoba zna architekturę systemu,
tylko jeden developer utrzymuje deployment,
jeden autor rozumie krytyczny moduł,

*to projekt staje się bardzo podatny na:*

odejścia pracowników,
choroby,
urlopy,
wypalenie zawodowe,
opóźnienia.
*Typowe symptomy:*
„Tego modułu lepiej nie ruszać, tylko Kasia wie jak działa”
brak dokumentacji,
wszystkie decyzje przechodzą przez jedną osobę,
code review blokowane przez jednego eksperta.

*Wysoki truck factor zwiększa odporność projektu*

*Projekt jest stabilniejszy, gdy:*

wiedza jest rozproszona w zespole,
istnieje dobra dokumentacja,
wiele osób uczestniczy w review,
onboarding nowych osób jest prosty,
architektura jest czytelna.

*Korzyści:*

łatwiejsze skalowanie zespołu,
mniejsze ryzyko biznesowe,
szybsze utrzymanie systemu,
większa przewidywalność rozwoju.

Taki stan grozi problemami z biblioteką `Requests` w przyszłości jeżeli nic nie zmieni się i nie pojawią się inni developerzy mocno zaangażowane w ten projekt.