## Które 5 plików zmieniano najczęściej?

~~~bash
git log --format=format: --name-only | sort | uniq -c | sort -rn | head -20
   6466 
    717 requests/models.py
    366 test_requests.py
    335 requests/sessions.py
    319 HISTORY.rst
    271 requests/utils.py
~~~

## Czy te pliki to też te z najwyższym churnem (adds + deletes)?

~~~bash
git log --numstat --format= | awk 'NF==3 {adds[$3]+=$1; dels[$3]+=$2} END {for (f in adds) print adds[f]+dels[f], f}' | sort -rn | head -10
23214 requests/cacert.pem
15268 requests/packages/idna/uts46data.py
14432 ext/requests-logo.ai
11079 requests/models.py
7294 tests/test_requests.py
6490 test_requests.py
6288 requests/packages/idna/idnadata.py
5443 Pipfile.lock
4686 requests/packages/urllib3/connectionpool.py
4266 requests/sessions.py
~~~

3 z 5 najczęściej zmienianych plików znajduje się również w TOP 10 plików z najwyższym churnem. Liczba zmian może korelować z najwyższym churnem, ale nie musi. Możemy mieć sytuacje, gdy raz stworzymy wielki plik, którego nigdy nie będziemy już zmieniać. Wtedy churn będzie duży, ale liczba zmian niska.

## Ile unikatowych autorów dotknęło plik, który zmienia się najczęściej?

Plik zmieniający się najczęściej: ```requests/models.py```

~~~bash
git log --format="%an" -- requests/models.py | sort | uniq | wc -l
194
~~~

## Wnioski o truck factor

Analizując ```requests``` truck factor wynosi 1 i głównym autorem jest Kenneth Reitz (samotny autor w 49.1% plików).
Nasuwa się od razu wniosek, ze gdyby Kenneth Reitz nagle zniknął rozwój i utrzymanie projektu mogłoby ulec gwałtownemu spowolnieniu. Jest też szansa, że wiedza o konkretnych komponentach repozytorium mogła by razem z nim zniknąć.
Natomiast ```requests``` jest dużym projektem open-source, więc duży wpływ jednego autora na repozytorium jest też spodziewany. Może on pełnić rolę zarządcy tzw. "blessed repository".
Nie zmienia to faktu, że projekt na pewno byłby stabilniejszy, gdyby było mniej tych samotnych wysp i więcej osób byłoby równie zaangażowanych w projekt.
Skutkowało by to lepszą możliwością skalowania ```requests``` w przyszłości.