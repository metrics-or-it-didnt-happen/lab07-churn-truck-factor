#!/usr/bin/env python3
"""Process Metrics Calculator - churn, ownership, truck factor."""

import subprocess
import sys
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
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
    file_churn = defaultdict(int)
    file_changes = defaultdict(int)
    file_authors = defaultdict(Counter)

    for commit in commits:
        author = commit["author"]
        for f in commit["files"]:
            path = f["path"]
            adds = f["adds"]
            deletes = f["deletes"]

            file_churn[path] += adds + deletes
            file_changes[path] += 1
            file_authors[path][author] += 1

    metrics = {}
    for path, total_changes in file_changes.items():
        authors_counter = file_authors[path]

        # Wyznaczanie ownera - autor z największą liczbą zmian w pliku
        owner, owner_commits = authors_counter.most_common(1)[0]
        owner_pct = (owner_commits / total_changes) * 100 if total_changes > 0 else 0

        metrics[path] = {
            "churn": file_churn[path],
            "changes": total_changes,
            "authors": len(authors_counter),
            "authors_counter": authors_counter,
            "owner": owner,
            "owner_pct": owner_pct
        }

    return metrics
    # Dla każdego pliku zbieraj:
    # - total churn (adds + deletes)
    # - change count (ile commitów dotknęło pliku)
    # - author counts (Counter autorów)
    # Potem dla każdego pliku wylicz owner i owner_pct



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

    owner_counts = Counter(m["owner"] for m in file_metrics.values())

    sorted_devs = sorted(owner_counts.items(), key=lambda x: x[1], reverse=True)

    total_files = len(file_metrics)
    target_files = total_files / 2.0
    covered_files = 0
    truck_devs = []

    for dev, count in sorted_devs:
        covered_files += count
        truck_devs.append(dev)
        if covered_files > target_files:
            break

    return len(truck_devs), truck_devs


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

def build_ownership_matrix(file_metrics: dict) -> pd.DataFrame:
        """Build developer x directory ownership matrix."""
        dir_author_commits = defaultdict(Counter)
        total_author_commits = Counter()

        # Potrzebujemy danych per-autor per-plik
        # Rozszerz compute_file_metrics o przechowywanie author_counts
        # dir_author_commits[directory] += author_counts_for_file
        for path, m in file_metrics.items():
            directory = path.split("/")[0] if "/" in path else "."
            author_counts = m["authors_counter"]

            dir_author_commits[directory].update(author_counts)
            total_author_commits.update(author_counts)

        # TOP 10 devs
        top_devs = [dev for dev, _ in total_author_commits.most_common(10)]
        directories = sorted(dir_author_commits.keys())

        # macierz udziałów
        matrix_data = defaultdict(dict)

        for directory in directories:
            # suma wszystkich commitów wszystkich autorów w danym katalogu
            dir_total_commits = sum(dir_author_commits[directory].values())

            # Normalizuj do procentów
            for dev in top_devs:
                if dir_total_commits > 0:
                    pct = (dir_author_commits[directory][dev] / dir_total_commits) * 100
                else:
                    pct = 0.0
                matrix_data[directory][dev] = pct

        # przeksztalcenie w DataFrame
        return pd.DataFrame(matrix_data).fillna(0)  # developer x directory

def plot_heatmap(file_metrics: dict) -> None:
        print("\nGenerowanie ownership heatmap...")
        matrix = build_ownership_matrix(file_metrics)
        plt.figure(figsize=(14, 8))
        sns.heatmap(matrix, annot=True, fmt=".0f", cmap="YlOrRd",
                    cbar_kws={"label": "% commitów"})
        plt.xlabel("Katalog")
        plt.ylabel("Developer")
        plt.title("Ownership heatmap: developer x katalog")
        plt.tight_layout()
        plt.savefig("ownership_heatmap.png", dpi=150)
        print(f"Heatmapa zostałą zapisana do pliku: ownership_heatmap.png")


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

    plot_heatmap(file_metrics)


if __name__ == "__main__":
    main()
