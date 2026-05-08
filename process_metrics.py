#!/usr/bin/env python3
"""Process Metrics Calculator - churn, ownership, truck factor."""

import argparse
import subprocess
import sys
from collections import Counter, defaultdict


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

    commits: list[dict] = []
    current: dict | None = None

    for line in result.stdout.split("\n"):
        line = line.strip()

        if "|" in line and len(line.split("|")) == 3:
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

    Returns dict: filepath -> {churn, changes, authors, author_counts,
                               owner, owner_pct}
    """
    files: dict[str, dict] = defaultdict(
        lambda: {"churn": 0, "changes": 0, "author_counts": Counter()}
    )

    for commit in commits:
        author = commit["author"]
        for f in commit["files"]:
            entry = files[f["path"]]
            entry["churn"] += f["adds"] + f["deletes"]
            entry["changes"] += 1
            entry["author_counts"][author] += 1

    metrics: dict[str, dict] = {}
    for path, entry in files.items():
        if entry["changes"] == 0:
            continue
        owner, owner_commits = entry["author_counts"].most_common(1)[0]
        metrics[path] = {
            "churn": entry["churn"],
            "changes": entry["changes"],
            "authors": len(entry["author_counts"]),
            "author_counts": entry["author_counts"],
            "owner": owner,
            "owner_pct": owner_commits / entry["changes"] * 100,
        }
    return metrics


def compute_truck_factor(file_metrics: dict[str, dict]) -> tuple[int, list[str]]:
    """Compute truck factor - minimum developers covering >50% of files.

    Greedy set-cover: repeatedly pick the developer who owns the most
    still-uncovered files, until covered files exceed 50% of total.
    """
    owned: dict[str, set[str]] = defaultdict(set)
    for path, m in file_metrics.items():
        owned[m["owner"]].add(path)

    total = len(file_metrics)
    threshold = total / 2
    covered: set[str] = set()
    truck_devs: list[str] = []

    while len(covered) <= threshold and owned:
        dev = max(owned, key=lambda d: len(owned[d] - covered))
        gain = owned.pop(dev) - covered
        if not gain:
            break
        covered |= gain
        truck_devs.append(dev)

    return len(truck_devs), truck_devs


def print_report(file_metrics: dict[str, dict],
                 truck_factor: int,
                 truck_devs: list[str]) -> None:
    """Print process metrics report."""
    print(f"\n{'=' * 70}")
    print("RAPORT METRYK PROCESOWYCH")
    print(f"{'=' * 70}")

    by_churn = sorted(file_metrics.items(),
                      key=lambda x: x[1]["churn"], reverse=True)

    print("\n--- TOP 20 najgorętszych plików (wg churn) ---")
    print(f"{'Plik':<45} {'Churn':>7} {'Zmian':>6} "
          f"{'Autorów':>8} {'Owner':<20} {'%':>5}")
    print("-" * 95)

    for path, m in by_churn[:20]:
        short = path if len(path) < 43 else "..." + path[-40:]
        print(f"  {short:<43} {m['churn']:>7} {m['changes']:>6} "
              f"{m['authors']:>8} {m['owner']:<20} {m['owner_pct']:>4.0f}%")

    lonely = [(p, m) for p, m in file_metrics.items() if m["authors"] == 1]
    print("\n--- Samotne wyspy (1 autor) ---")
    print(f"  {len(lonely)} z {len(file_metrics)} plików "
          f"({len(lonely)/len(file_metrics)*100:.1f}%) "
          f"ma tylko jednego autora")

    print("\n--- Truck Factor ---")
    print(f"  Truck factor: {truck_factor}")
    print("  Kluczowi developerzy:")
    for dev in truck_devs:
        owned = sum(1 for m in file_metrics.values() if m["owner"] == dev)
        print(f"    {dev} (owner {owned} plików)")


def build_ownership_matrix(file_metrics: dict[str, dict],
                           top_dirs: int = 8,
                           top_devs: int = 10):
    """Build developer x directory ownership matrix (% commitów per katalog).

    Aggregates per-file author_counts by top-level directory, then
    keeps the top-N most active directories and the top-M developers
    across them. Each column normalised to 100%.
    """
    import pandas as pd

    dir_authors: dict[str, Counter] = defaultdict(Counter)
    for path, m in file_metrics.items():
        directory = path.split("/", 1)[0] if "/" in path else "."
        dir_authors[directory] += m["author_counts"]

    top_dir_names = sorted(
        dir_authors, key=lambda d: sum(dir_authors[d].values()), reverse=True
    )[:top_dirs]

    dev_totals: Counter = Counter()
    for d in top_dir_names:
        dev_totals += dir_authors[d]
    top_dev_names = [name for name, _ in dev_totals.most_common(top_devs)]

    matrix = pd.DataFrame(0.0, index=top_dev_names, columns=top_dir_names)
    for d in top_dir_names:
        total = sum(dir_authors[d].values())
        if not total:
            continue
        for dev in top_dev_names:
            matrix.at[dev, d] = dir_authors[d].get(dev, 0) / total * 100
    return matrix


def save_heatmap(matrix, path: str = "ownership_heatmap.png") -> None:
    """Save heatmap with Polish labels."""
    import matplotlib.pyplot as plt
    import seaborn as sns

    plt.figure(figsize=(14, 8))
    sns.heatmap(matrix, annot=True, fmt=".0f", cmap="RdPu",
                cbar_kws={"label": "% commitów"})
    plt.xlabel("Katalog")
    plt.ylabel("Developer")
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process metrics: churn, ownership, truck factor."
    )
    parser.add_argument("repo_path", help="ścieżka do repozytorium git")
    parser.add_argument("--heatmap", action="store_true",
                        help="zapisz ownership_heatmap.png")
    args = parser.parse_args()

    print(f"Analizuję metryki procesowe: {args.repo_path}")
    commits = parse_git_numstat(args.repo_path)
    print(f"Sparsowano {len(commits)} commitów")

    file_metrics = compute_file_metrics(commits)
    print(f"Znaleziono {len(file_metrics)} plików")

    truck_factor, truck_devs = compute_truck_factor(file_metrics)
    print_report(file_metrics, truck_factor, truck_devs)

    if args.heatmap:
        matrix = build_ownership_matrix(file_metrics)
        save_heatmap(matrix)
        print("\nZapisano ownership_heatmap.png")


if __name__ == "__main__":
    sys.exit(main())
