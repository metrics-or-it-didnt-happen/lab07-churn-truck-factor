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
    # Tymczasowe struktury do zbierania danych per plik
    file_churn = defaultdict(int)
    file_changes = defaultdict(int)
    file_authors = defaultdict(Counter)

    for commit in commits:
        author = commit["author"]
        for f in commit["files"]:
            path = f["path"]
            
            # Sumujemy churn (dodane + usunięte)
            file_churn[path] += f["adds"] + f["deletes"]
            # Zwiększamy licznik modyfikacji pliku
            file_changes[path] += 1
            # Zliczamy commity tego autora dla danego pliku
            file_authors[path][author] += 1

    metrics = {}
    for path in file_changes:
        authors_counter = file_authors[path]
        total_changes = file_changes[path]
        
        # Wyznaczamy właściciela (najwięcej commitów dla tego pliku)
        owner, owner_commits = authors_counter.most_common(1)[0]
        owner_pct = (owner_commits / total_changes) * 100 if total_changes > 0 else 0.0

        metrics[path] = {
            "churn": file_churn[path],
            "changes": total_changes,
            "authors": len(authors_counter),  
            "owner": owner,
            "owner_pct": owner_pct
        }

    return metrics


def compute_truck_factor(file_metrics: dict[str, dict]) -> tuple[int, list[str]]:
    """Compute truck factor - minimum developers covering >50% of files.

    Algorithm:
    1. For each file, determine the owner (most commits)
    2. Count how many files each developer owns
    3. Greedily pick developer with most owned files
    4. Remove their files from the pool
    5. Repeat until >50% files are covered
    """
    if not file_metrics:
        return 0, []

    total_files_count = len(file_metrics)
    target_to_cover = total_files_count / 2  # Musimy pokryć ściśle WIĘCEJ niż 50%
    
    # Budujemy mapę: kto posiada jakie pliki (owner -> set of filepaths)
    dev_ownership = defaultdict(set)
    for path, m in file_metrics.items():
        dev_ownership[m["owner"]].add(path)

    covered_files = set()
    truck_devs = []

    while len(covered_files) <= target_to_cover and dev_ownership:
        # Szukamy dewelopera, którego pliki (jeszcze niepokryte) dają największy zysk
        best_dev = None
        best_new_files = set()

        for dev, owned_files in dev_ownership.items():
            # Sprawdzamy tylko te pliki, których jeszcze nie mamy w puli pokrytych
            uncovered_by_this_dev = owned_files - covered_files
            if len(uncovered_by_this_dev) > len(best_new_files):
                best_dev = dev
                best_new_files = uncovered_by_this_dev

        # Jeśli żaden deweloper nie wnosi już nowych plików, kończymy pętlę
        if not best_dev or len(best_new_files) == 0:
            break

        # Dodajemy wybranego dewelopera do ekipy ratunkowej
        truck_devs.append(best_dev)
        covered_files.update(best_new_files)
        
        # Usuwamy go z puli do rozpatrzenia w kolejnej iteracji
        del dev_ownership[best_dev]

    truck_factor = len(truck_devs)
    return truck_factor, truck_devs


def print_report(file_metrics: dict[str, dict],
                 truck_factor: int,
                 truck_devs: list[str]) -> None:
    """Print process metrics report."""
    print(f"\n{'=' * 70}")
    print(f"RAPORT METRYK PROCESOWYCH")
    print(f"{'=' * 70}")

    # Top 20 pliki (wg churn)
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
    if file_metrics:
        print(f"  {len(lonely)} z {len(file_metrics)} plików "
              f"({len(lonely)/len(file_metrics)*100:.1f}%) "
              f"ma tylko jednego autora")
    else:
        print("  Brak plików do analizy.")

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

    try:
        commits = parse_git_numstat(repo_path)
        print(f"Sparsowano {len(commits)} commitów")
    except Exception as e:
        print(f"Błąd podczas uruchamiania git log: {e}")
        sys.exit(1)

    file_metrics = compute_file_metrics(commits)
    print(f"Znaleziono {len(file_metrics)} plików")

    truck_factor, truck_devs = compute_truck_factor(file_metrics)
    print_report(file_metrics, truck_factor, truck_devs)


if __name__ == "__main__":
    main()
