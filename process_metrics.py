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
    # Zbieramy tymczasowe statystyki per-file
    file_stats: dict[str, dict] = {}

    for commit in commits:
        author = commit.get("author")
        for f in commit.get("files", []):
            path = f.get("path")
            adds = f.get("adds", 0)
            deletes = f.get("deletes", 0)

            if path not in file_stats:
                file_stats[path] = {
                    "churn": 0,
                    "changes": 0,
                    "author_counts": Counter(),
                }

            file_stats[path]["churn"] += adds + deletes
            file_stats[path]["changes"] += 1
            if author is not None:
                file_stats[path]["author_counts"][author] += 1

    # Zbuduj docelową strukturę zwracaną
    result: dict[str, dict] = {}
    for path, stats in file_stats.items():
        author_counts: Counter = stats["author_counts"]
        total_changes = stats["changes"]

        if author_counts:
            owner, owner_changes = author_counts.most_common(1)[0]
            owner_pct = (owner_changes / total_changes) * 100 if total_changes > 0 else 0.0
            authors = len(author_counts)
        else:
            owner = None
            owner_pct = 0.0
            authors = 0

        result[path] = {
            "churn": stats["churn"],
            "changes": total_changes,
            "authors": authors,
            "owner": owner,
            "owner_pct": owner_pct,
        }

    return result


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

    # Map owner -> set(files they own)
    owner_files: dict[str, set] = defaultdict(set)
    for path, m in file_metrics.items():
        owner = m.get("owner")
        if not owner:
            continue
        owner_files[owner].add(path)

    total_files = len([p for p in file_metrics.keys()])
    if total_files == 0:
        return 0, []

    covered: set[str] = set()
    picked: list[str] = []

    # Greedy selection: pick developer owning most uncovered files
    while len(covered) <= total_files / 2:
        best_owner = None
        best_count = 0
        for owner, files in owner_files.items():
            uncovered = len(files - covered)
            if uncovered > best_count:
                best_count = uncovered
                best_owner = owner

        if not best_owner or best_count == 0:
            break

        picked.append(best_owner)
        covered.update(owner_files[best_owner])
        # remove picked owner so we don't pick them twice
        owner_files.pop(best_owner, None)

    return len(picked), picked


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