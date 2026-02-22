# Lab 07: Code Churn i Truck Factor - kto jest niezastąpiony?

## Czy wiesz, że...

Według badań (które właśnie wymyśliłem), truck factor projektu Linux kernel wynosi 1 i ten jeden człowiek to Linus Torvalds. Gdyby wpadł pod ciężarówkę, 97% serwerów na świecie miałoby problem. Na szczęście żyje zdrowo i pisze złośliwe maile na listach dyskusyjnych.

## Kontekst

Na poprzednich labach mierzyliśmy kod - linie, złożoność, klasy. To metryki *produktowe* - opisują artefakt (kod). Dziś przechodzimy do metryk *procesowych* - opisują *jak* kod powstaje i kto za nim stoi.

Code churn mówi nam, które pliki są "gorące" - często zmieniane, z dużą rotacją linii. Wysoki churn to sygnał ryzyka: plik, który zmienia się co tydzień, prawdopodobnie jest problematyczny (bugi, niejasne wymagania, złe API).

Truck factor (znany też jako bus factor) odpowiada na pytanie: ilu developerów musi "wpaść pod ciężarówkę" (czytaj: odejść z projektu), żeby nikt nie wiedział jak działa krytyczna część kodu? Truck factor = 1 to duże ryzyko.

## Cel laboratorium

Po tym laboratorium będziesz potrafić:
- wyciągać dane o zmianach plików z `git log --numstat`,
- policzyć code churn, code ownership i truck factor,
- zidentyfikować "gorące" pliki i "samotne wyspy" w projekcie,
- ocenić ryzyko projektowe na podstawie metryk procesowych.

## Wymagania wstępne

- Python 3.9+
- `git` zainstalowany
- `matplotlib` / `seaborn` (do opcjonalnej wizualizacji)
- Sklonowany projekt open-source z co najmniej kilkuletnią historią i wieloma kontrybutorami

## Zadania

### Zadanie 1: git log --numstat (30 min)

`git log --numstat` to kopalnia danych - dla każdego commitu pokazuje ile linii dodano i usunięto w każdym pliku.

**Krok 1:** Sklonuj projekt (jeśli nie masz):

```bash
git clone https://github.com/psf/requests.git
cd requests
```

**Krok 2:** Obejrzyj format `--numstat`:

```bash
# Format: additions \t deletions \t filename
git log --numstat --format="%H|%an|%ad" --date=short | head -50
```

Zobaczysz naprzemiennie: linia z hashem|autorem|datą, potem linie z numerami (adds/deletes/plik), potem pusta linia.

**Krok 3:** Ręczna eksploracja:

```bash
# Które pliki zmieniano najczęściej?
git log --format=format: --name-only | sort | uniq -c | sort -rn | head -20

# Kto dotykał najwięcej plików?
git log --format="%an" --name-only | head -1000 | sort | uniq -c | sort -rn | head -10

# Ile linii dodano/usunięto łącznie w projekcie?
git log --numstat --format="" | awk '{adds+=$1; dels+=$2} END {print "Dodano:", adds, "Usunięto:", dels}'
```

**Krok 4:** Odpowiedz na pytania:

1. Które 5 plików zmieniano najczęściej?
2. Czy te pliki to też te z najwyższym churnem (adds + deletes)?
3. Ile unikatowych autorów dotknęło plik, który zmienia się najczęściej?

### Zadanie 2: Process Metrics Calculator (60 min)

Napiszcie skrypt `process_metrics.py`, który wyciąga metryki procesowe z historii gita.

**Co skrypt ma robić:**

1. Sparsować `git log --numstat`
2. Policzyć per plik:
   - **Total churn** = suma (additions + deletions) we wszystkich commitach
   - **Change frequency** = ile razy plik był zmieniany
   - **Distinct authors** = ilu różnych autorów zmieniało plik
   - **Code ownership** = kto ma najwięcej commitów dotykających tego pliku (i jaki %)
3. Policzyć **truck factor** projektu:
   - Dla każdego pliku określ "ownera" (autor z największą liczbą commitów)
   - Truck factor = minimalny zbiór developerów, którzy "pokrywają" > 50% plików (tzn. są ownerami > 50% plików)
4. Wygenerować raport

**Punkt startowy:**

```python
#!/usr/bin/env python3
"""Process Metrics Calculator - churn, ownership, truck factor."""

import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path


def parse_git_numstat(repo_path: str) -> list[dict]:
    """Parse git log --numstat output.

    Returns list of dicts:
        {commit_hash, author, date, files: [{path, adds, deletes}]}
    """
    result = subprocess.run(
        ["git", "log", "--numstat",
         "--format=%H|%an|%ad", "--date=short"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8",
        errors="replace",
    )

    commits = []
    current = None

    for line in result.stdout.split("\n"):
        line = line.strip()

        if "|" in line and len(line.split("|")) == 3:
            # Nowy commit
            if current:
                commits.append(current)
            parts = line.split("|")
            current = {
                "hash": parts[0],
                "author": parts[1],
                "date": parts[2],
                "files": [],
            }
        elif line and current and "\t" in line:
            # Plik ze statystykami
            parts = line.split("\t")
            if len(parts) == 3:
                adds = int(parts[0]) if parts[0] != "-" else 0
                deletes = int(parts[1]) if parts[1] != "-" else 0
                current["files"].append({
                    "path": parts[2],
                    "adds": adds,
                    "deletes": deletes,
                })

    if current:
        commits.append(current)

    return commits


def compute_file_metrics(commits: list[dict]) -> dict[str, dict]:
    """Compute per-file process metrics.

    Returns dict: filepath -> {churn, changes, authors, owner, owner_pct}
    """
    # TODO: Twój kod tutaj
    # Dla każdego pliku zbieraj:
    # - total churn (adds + deletes)
    # - change count (ile commitów dotknęło pliku)
    # - author counts (Counter autorów)
    # Potem dla każdego pliku wylicz owner i owner_pct
    pass


def compute_truck_factor(file_metrics: dict[str, dict]) -> tuple[int, list[str]]:
    """Compute truck factor - minimum developers covering >50% of files.

    Algorithm:
    1. For each file, determine the owner (most commits)
    2. Count how many files each developer owns
    3. Greedily pick developer with most owned files
    4. Remove their files from the pool
    5. Repeat until >50% files are covered
    """
    # TODO: Twój kod tutaj
    pass


def print_report(file_metrics: dict[str, dict],
                 truck_factor: int,
                 truck_devs: list[str]) -> None:
    """Print process metrics report."""
    print(f"\n{'=' * 70}")
    print(f"RAPORT METRYK PROCESOWYCH")
    print(f"{'=' * 70}")

    # Top 20 najgorętsze pliki (wg churn)
    by_churn = sorted(file_metrics.items(),
                      key=lambda x: x[1]["churn"], reverse=True)

    print(f"\n--- TOP 20 najgorętszych plików (wg churn) ---")
    print(f"{'Plik':<45} {'Churn':>7} {'Zmian':>6} "
          f"{'Autorów':>8} {'Owner':<20} {'%':>5}")
    print("-" * 95)

    for path, m in by_churn[:20]:
        short = path if len(path) < 43 else "..." + path[-40:]
        print(f"  {short:<43} {m['churn']:>7} {m['changes']:>6} "
              f"{m['authors']:>8} {m['owner']:<20} {m['owner_pct']:>4.0f}%")

    # Samotne wyspy (pliki z 1 autorem)
    lonely = [(p, m) for p, m in file_metrics.items() if m["authors"] == 1]
    print(f"\n--- Samotne wyspy (1 autor) ---")
    print(f"  {len(lonely)} z {len(file_metrics)} plików "
          f"({len(lonely)/len(file_metrics)*100:.1f}%) "
          f"ma tylko jednego autora")

    # Truck factor
    print(f"\n--- Truck Factor ---")
    print(f"  Truck factor: {truck_factor}")
    print(f"  Kluczowi developerzy:")
    for dev in truck_devs:
        owned = sum(1 for m in file_metrics.values() if m["owner"] == dev)
        print(f"    {dev} (owner {owned} plików)")


def main():
    if len(sys.argv) < 2:
        print("Użycie: python process_metrics.py <ścieżka_do_repo>")
        sys.exit(1)

    repo_path = sys.argv[1]
    print(f"Analizuję metryki procesowe: {repo_path}")

    commits = parse_git_numstat(repo_path)
    print(f"Sparsowano {len(commits)} commitów")

    file_metrics = compute_file_metrics(commits)
    print(f"Znaleziono {len(file_metrics)} plików")

    truck_factor, truck_devs = compute_truck_factor(file_metrics)
    print_report(file_metrics, truck_factor, truck_devs)


if __name__ == "__main__":
    main()
```

**Oczekiwany output (przykład):**

```
Analizuję metryki procesowe: requests/
Sparsowano 6234 commitów
Znaleziono 187 plików

======================================================================
RAPORT METRYK PROCESOWYCH
======================================================================

--- TOP 20 najgorętszych plików (wg churn) ---
Plik                                          Churn  Zmian  Autorów Owner                   %
-----------------------------------------------------------------------------------------------
  src/requests/models.py                       8234    312      34 Kenneth Reitz           41%
  src/requests/sessions.py                     5621    198      28 Kenneth Reitz           45%
  src/requests/adapters.py                     3102    156      22 Nate Prewitt            32%
  ...

--- Samotne wyspy (1 autor) ---
  23 z 187 plików (12.3%) ma tylko jednego autora

--- Truck Factor ---
  Truck factor: 2
  Kluczowi developerzy:
    Kenneth Reitz (owner 89 plików)
    Nate Prewitt (owner 42 plików)
```

### Zadanie 3: Heatmapa ownership (45 min) - dla ambitnych

Wizualizacja macierzy developer x katalog, gdzie intensywność kolorów oznacza procent ownership.

**Do zrobienia:**
- Dla każdego katalogu (top-level) policz, kto jest "ownerem" i jaki ma %
- Narysuj heatmapę (seaborn) z osiami: developer x katalog
- Wartości w macierzy: % commitów danego developera w danym katalogu

```python
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd

def build_ownership_matrix(file_metrics: dict) -> pd.DataFrame:
    """Build developer x directory ownership matrix."""
    dir_author_commits = defaultdict(Counter)

    for path, m in file_metrics.items():
        directory = path.split("/")[0] if "/" in path else "."
        # Potrzebujemy danych per-autor per-plik
        # Rozszerz compute_file_metrics o przechowywanie author_counts
        # dir_author_commits[directory] += author_counts_for_file

    # Normalizuj do procentów
    # ...

    return pd.DataFrame(...)  # developer x directory


# Rysowanie
matrix = build_ownership_matrix(file_metrics)
plt.figure(figsize=(14, 8))
sns.heatmap(matrix, annot=True, fmt=".0f", cmap="YlOrRd",
            cbar_kws={"label": "% commitów"})
plt.xlabel("Katalog")
plt.ylabel("Developer")
plt.title("Ownership heatmap: developer x katalog")
plt.tight_layout()
plt.savefig("ownership_heatmap.png", dpi=150)
```

## Co oddajecie

W swoim branchu `lab07_nazwisko1_nazwisko2`:

1. **`process_metrics.py`** - działający skrypt z zadania 2
2. **`answers.md`** - odpowiedzi na pytania z zadania 1 + wnioski o truck factor
3. *(opcjonalnie)* **`ownership_heatmap.png`** - heatmapa z zadania 3

## Kryteria oceny

- Parsowanie `git log --numstat` działa poprawnie (obsługuje pliki binarne z `-` zamiast liczb)
- Churn, change frequency i authors count są obliczane poprawnie per plik
- Code ownership identyfikuje właściwego ownera z procentem
- Truck factor jest obliczany algorytmem zachłannym (greedy covering)
- Raport zawiera top pliki, samotne wyspy i truck factor
- Odpowiedzi z zadania 1 są poparte danymi

## FAQ

**P: `git log --numstat` pokazuje `-` zamiast liczby dla niektórych plików.**
O: To pliki binarne (obrazki, PDFy). Traktuj je jako 0 adds / 0 deletes, ale wciąż licz jako zmianę (zmiana pliku binarnego to też churn).

**P: Truck factor wychodzi mi 1 dla prawie każdego projektu.**
O: To normalne dla wielu projektów OSS - jeden maintainer dominuje. Dlatego truck factor = 1 to sygnał ryzyka, nie błąd w obliczeniach.

**P: Jak obsłużyć pliki, które zostały przeniesione/zmieniono im nazwę?**
O: Na potrzeby tego laba traktuj starą i nową ścieżkę jako dwa oddzielne pliki. Pełna obsługa wymaga `git log --follow`, ale to komplikuje analizę całego projektu naraz.

**P: Mój projekt ma 50 000 commitów i parsowanie trwa wieczność.**
O: Ogranicz historię: `git log --since="2020-01-01" --numstat ...`. Albo filtruj do konkretnych ścieżek: `git log --numstat -- src/`.

**P: Czy churn powinien liczyć adds + deletes, czy same deletes?**
O: Konwencja: churn = adds + deletes. Niektóre definicje mówią, że churn to tylko "zmienione linie" (nie dodane), ale adds + deletes jest najpopularniejsze i prostsze do obliczenia.

## Przydatne linki

- [git log --numstat documentation](https://git-scm.com/docs/git-log#_generating_patch_text_with_p)
- [Truck Factor (Wikipedia)](https://en.wikipedia.org/wiki/Bus_factor)
- [Code Churn (Wikipedia)](https://en.wikipedia.org/wiki/Code_churn)
- [Assessing the Bus Factor of Git Repositories (paper)](https://doi.org/10.1109/SANER.2016.18)
- [seaborn heatmap documentation](https://seaborn.pydata.org/generated/seaborn.heatmap.html)

---
*"Jedyny niezastąpiony człowiek na cmentarzu to ten, którego tam nie ma."* - Charles de Gaulle (wersja open-source)
