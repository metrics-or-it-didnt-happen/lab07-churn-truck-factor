#!/usr/bin/env python3
"""Process Metrics Calculator - churn, ownership, truck factor."""

import subprocess
import sys
from collections import Counter, defaultdict
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")
import pandas as pd

# dla złożonych nazw plików wynikających z refaktoryzacji
# bierzemy pod uwagę plik docelowy
def normalize_git_filename(name: str) -> str:
    if " => " not in name: return name

    if "{" not in name:
        return name.split(" => ")[1]

    prefix, rest = name.split("{", 1)
    old_new, suffix = rest.split("}", 1)
    _, new = old_new.split(" => ")
    return prefix + new + suffix


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
                    "path": normalize_git_filename(parts[2]),
                    "adds": adds,
                    "deletes": deletes,
                })

    if current:
        commits.append(current)

    return commits


def compute_file_metrics(commits: list[dict]) -> dict[str, dict]:
    """Compute per-file process metrics.

    Returns dict: filepath -> 
        {churn, changes, authors_counter, authors, owner, owner_pct}
    """

    file_metrics = defaultdict(lambda: {
        "churn": 0,
        "changes": 0,
        "authors_counter": Counter(),
        "authors" : 0,
        "owner": None,
        "owner_pct": None,
    })

    # zliczenie podstawowych statystyk (total churn, change count)
    # i przypisanie ingerencji autorów do poszczególnych plików
    for commit in commits:
        author = commit['author']
        for file in commit['files']:
            file_name = file['path']

            metrics = file_metrics[file_name]
            metrics['churn'] += file['adds'] + file['deletes']
            metrics['changes'] +=1
            metrics['authors_counter'][author] += 1

            file_metrics[file_name] = metrics

    # dla każdego pliku: kto ma najwięcej commitów (i jaki procent)
    # zamiana "authors" z Countera na liczbę różnych autorów
    for metrics in file_metrics.values():
        authors = metrics["authors_counter"]
        owner, owner_commits = authors.most_common(1)[0]
        total_commits = sum(authors.values())

        metrics["owner"] = owner
        metrics["owner_pct"] = owner_commits/total_commits*100
        metrics["authors"] = len(authors)

    return file_metrics


def compute_truck_factor(file_metrics: dict[str, dict]) -> tuple[int, list[str]]:
    """Compute truck factor - minimum developers covering >50% of files.

    Algorithm:
    1. For each file, determine the owner (most commits)
    2. Count how many files each developer owns
    3. Greedily pick developer with most owned files
    4. Remove their files from the pool
    5. Repeat until >50% files are covered
    """

    developer_files = Counter()
    for metrics in file_metrics.values():
        developer_files[metrics["owner"]] += 1

    truck_factor = 0
    truck_list = []
    total_files = len(file_metrics)
    covered_files = 0

    for developer, owned_files in developer_files.most_common():
        covered_files += owned_files
        truck_factor += 1
        truck_list.append(developer)

        if covered_files > 0.5*total_files:
            break

    return (truck_factor, truck_list)


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

# z ograniczeniem do 10-top autorów dla czytelności
def build_ownership_matrix(file_metrics: dict) -> pd.DataFrame:
    """Build developer x directory ownership matrix."""
    dir_author_commits = defaultdict(Counter)
    total_author_counts = Counter()

    for path, metrics in file_metrics.items():
        directory = path.split("/")[0] if "/" in path else "."
        author_counts = metrics['authors_counter']
        total_author_counts.update(author_counts)
        for author, count in author_counts.items():
            dir_author_commits[directory][author] += count

    dirs = sorted(dir_author_commits.keys())
    developers = sorted([dev for dev, _ in total_author_counts.most_common(10)])

    data = defaultdict(dict)
    for dir in dirs:
        dir_counter = dir_author_commits[dir]
        total = sum(dir_counter.values())

        for author in developers:
            contribution = dir_counter[author]/total*100 if total>0 else 0
            data[dir][author] = contribution

    return pd.DataFrame(data).fillna(0)  # developer x directory
    

def plot_ownership_matrix(file_metrics: dict[str, dict]):
    matrix = build_ownership_matrix(file_metrics)
    plt.figure(figsize=(14, 8))
    sns.heatmap(matrix, annot=True, fmt=".0f", cmap="YlOrRd",
                cbar_kws={"label": "% commitów"})
    plt.xlabel("Katalog")
    plt.ylabel("Developer")
    plt.title("Ownership heatmap: developer x katalog")
    plt.tight_layout()
    plt.savefig("ownership_heatmap.png", dpi=150)

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

    plot_ownership_matrix(file_metrics)
    print("\nHeatmapa ownership zapisana do pliku: ownership_heatmap.png")


if __name__ == "__main__":
    main()