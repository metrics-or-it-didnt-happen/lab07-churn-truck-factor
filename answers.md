1. Które 5 plików zmieniano najczęściej?
Pretty:
    1. Ilość zmian: 717  Plik: requests/models.py
    2. Ilość zmian: 366 Plik: test_requests.py
    3. Ilość zmian: 335 Plik: requests/sessions.py
    4. Ilość zmian: 319 Plik: HISTORY.rst
    5. Ilość zmian: 271 Plik: requests/utils.py
Raw:
 git log --pretty=format: --name-only | grep -v '^$' | sort | uniq -c | sort -rn | head -5
    717 requests/models.py
    366 test_requests.py
    335 requests/sessions.py
    319 HISTORY.rst
    271 requests/utils.py

2. Czy te pliki to też te z najwyższym churnem (adds + deletes)?

Pretty:
    1. requests/models.py - 4 miejsce 11079 zmian
    2. test_requests.py- 7 miejsce 6900 zmian
    3. requests/sessions.py - 11 miejsce 4266 zmian
    4. HISTORY.rst - 15 miejsce 3657 zmian
    5. requests/utils.py - 12 miejsce 4041 zmian

    Pliki najczęściej zmieniane to nie te same co te zawierające najwięcej zmienianych linii, jednak dalej są dosyć wysoko w tej drugiej metryce.

Raw:
git log --numstat --pretty=format: | awk '{sum[$3]+=($1+$2)} END {for (file in sum) print sum[file], file}' | sort -rn | head -20
23214 requests/cacert.pem
15268 requests/packages/idna/uts46data.py
14432 ext/requests-logo.ai
11079 requests/models.py
8808 requests/packages/{charade
7274 tests/test_requests.py
6900 test_requests.py
6288 requests/packages/idna/idnadata.py
5443 Pipfile.lock
4686 requests/packages/urllib3/connectionpool.py
4266 requests/sessions.py
4041 requests/utils.py
3963 requests/packages/chardet/mbcssm.py
3793 requests/core.py
3657 HISTORY.rst
3116 docs/user/advanced.rst
2777 requests/packages/chardet/big5freq.py
2478 tests/test_utils.py
2389 requests/packages/chardet/langcyrillicmodel.py
2144 HISTORY.md

3. Ile unikatowych autorów dotknęło plik, który zmienia się najczęściej?

Pretty : 193

Raw: 
git log --pretty=format:'%aN' --no-merges -- requests/models.py | sort -u | wc -l
193