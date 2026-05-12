# Odpowiedzi – lab 07 (churn, truck factor)

Analizę wykonałem na repozytorium **requests** (`psf/requests`), zgodnie z README. Klon był lokalny i pobrany z ograniczoną głębokością (`--depth`), więc liczba commitów może różnić się od pełnego repozytorium; rankingi plików i interpretacja wyników pozostają jednak czytelne.

## Zadanie 1 – eksploracja gita

### 1. Które 5 plików zmieniano najczęściej?

Wykorzystałem `git log --format=format: --name-only` i zliczyłem wystąpienia poszczególnych ścieżek. Pięć najczęściej zmienianych plików:

1. `requests/models.py`
2. `test_requests.py` (test na poziomie głównym katalogu – w historii projektu widać reorganizację struktury)
3. `requests/sessions.py`
4. `HISTORY.rst`
5. `requests/utils.py`

Są to głównie moduły rdzeniowe biblioteki oraz plik historii zmian.

### 2. Czy to są te same pliki co przy najwyższym churnie?

Nie w pełni. Churn liczyłem jako sumę dodanych i usuniętych linii z `git log --numstat`.

Na szczycie listy pod względem churnu znalazły się m.in. `requests/cacert.pem` (duże, rzadko aktualizowane bloki certyfikatów, ale o dużym wolumenie diffa), wygenerowane pliki związane z IDNA (np. `uts46data.py`) oraz `ext/requests-logo.ai` (niewiele commitów, lecz duży wpływ na sumę linii).

Plik `requests/models.py` plasuje się wysoko zarówno według częstotliwości zmian, jak i według churnu. Podobnie wygląda sprawa z testami, przy czym dokładna ścieżka w logu może różnić się między `test_requests.py` a `tests/test_requests.py` w zależności od etapu historii.

**Wniosek:** wysoka częstotliwość zmian nie musi pokrywać się z najwyższym churnem. Pojedyncza duża zmiana lub regeneracja danych może mocno podnieść churn przy stosunkowo niewielkiej liczbie commitów.

### 3. Ile unikatowych autorów dotknęło plik zmieniany najczęściej?

Najczęściej zmieniany plik to `requests/models.py`. Przy filtrowaniu `git log` do tej ścieżki uzyskuję około **200 unikalnych autorów** (dokładna wartość może zależeć od uwzględniania merge’y oraz sposobu śledzenia rename’ów w git).

Jest to zgodne z rolą tego modułu: stanowi centralną część biblioteki i bywa modyfikowany przez wiele osób w różnych kontekstach zmian.

## Wnioski o truck factor (z `process_metrics.py`)

Uruchomiłem `process_metrics.py` na tym samym klonie. Otrzymałem **truck factor równy 1**; jako owner większości plików (według liczby commitów dotykających pliku) wskazywany jest **Kenneth Reitz**.

Nie oznacza to braku wkładu innych osób, lecz że według przyjętej w laboratorium definicji jeden autor jako owner pokrywa ponad połowę plików, więc zachłanny algorytm zatrzymuje się po pierwszym wyborze.

Traktuję to jako sygnał ryzyka organizacyjnego: po odejściu głównego maintainera wiedza operacyjna bywa rozproszona, podczas gdy metryka ownership nadal może wskazywać na jedną dominującą osobę. Zgodnie z README, niski truck factor w projektach open source bywa typowy i świadczy raczej o strukturze wkładu niż o błędzie obliczeń.

W raporcie pojawia się też znaczny udział plików z jednym autorem („samotne wyspy”). Dla części z nich jest to oczekiwane (np. dokumentacja, rzadko używane narzędzia), przy wysokim odsetku warto jednak zweryfikować, czy w zespole istnieje świadoma wiedza o tych fragmentach kodu.
