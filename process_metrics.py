#!/usr/bin/env python3
"""Process Metrics Calculator - churn, ownership, truck factor."""

import subprocess
import sys
from collections import Counter, defaultdict


def parse_git_numstat(repo_path: str) -> list[dict]:
    """Parse git log --numstat output.

    Returns list of dicts:
        {commit_hash, author, date, files: [{path, adds, deletes}]}
    """
    result = subprocess.run(
        [
            "git",
            "log",
            "--numstat",
            "--format=%H|%an|%ad",
            "--date=short",
        ],
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

                current["files"].append(
                    {
                        "path": parts[2],
                        "adds": adds,
                        "deletes": deletes,
                    }
                )

    if current:
        commits.append(current)

    return commits


def compute_file_metrics(commits: list[dict]) -> dict[str, dict]:
    """Compute per-file process metrics.

    Returns dict:
        filepath -> {
            churn,
            changes,
            authors,
            owner,
            owner_pct,
            author_counter
        }
    """

    metrics = defaultdict(
        lambda: {
            "churn": 0,
            "changes": 0,
            "author_counter": Counter(),
        }
    )

    for commit in commits:
        author = commit["author"]

        for f in commit["files"]:
            path = f["path"]

            churn = f["adds"] + f["deletes"]

            metrics[path]["churn"] += churn
            metrics[path]["changes"] += 1
            metrics[path]["author_counter"][author] += 1

    # Finalizacja metryk
    result = {}

    for path, data in metrics.items():
        author_counter = data["author_counter"]

        owner, owner_commits = author_counter.most_common(1)[0]

        total_author_commits = sum(author_counter.values())

        owner_pct = (
            owner_commits / total_author_commits * 100
            if total_author_commits > 0
            else 0
        )

        result[path] = {
            "churn": data["churn"],
            "changes": data["changes"],
            "authors": len(author_counter),
            "owner": owner,
            "owner_pct": owner_pct,
            "author_counter": author_counter,
        }

    return result


def compute_truck_factor(file_metrics: dict[str, dict]) -> tuple[int, list[str]]:
    """Compute truck factor - minimum developers covering >50% of files."""

    total_files = len(file_metrics)

    if total_files == 0:
        return 0, []

    # owner -> set(files)
    ownership = defaultdict(set)

    for path, metrics in file_metrics.items():
        owner = metrics["owner"]
        ownership[owner].add(path)

    covered_files = set()
    selected_devs = []

    while len(covered_files) / total_files <= 0.5:
        best_dev = None
        best_new_files = set()

        for dev, files in ownership.items():
            new_files = files - covered_files

            if len(new_files) > len(best_new_files):
                best_dev = dev
                best_new_files = new_files

        if not best_dev:
            break

        selected_devs.append(best_dev)
        covered_files.update(best_new_files)

        # usuwamy developera aby nie wybierać go ponownie
        ownership.pop(best_dev)

    return len(selected_devs), selected_devs


def print_report(
    file_metrics: dict[str, dict],
    truck_factor: int,
    truck_devs: list[str],
) -> None:
    """Print process metrics report."""

    print(f"\n{'=' * 70}")
    print("RAPORT METRYK PROCESOWYCH")
    print(f"{'=' * 70}")

    # Top churn
    by_churn = sorted(
        file_metrics.items(),
        key=lambda x: x[1]["churn"],
        reverse=True,
    )

    print("\n--- TOP 20 najgorętszych plików (wg churn) ---")

    print(
        f"{'Plik':<45} "
        f"{'Churn':>7} "
        f"{'Zmian':>6} "
        f"{'Autorów':>8} "
        f"{'Owner':<20} "
        f"{'%':>5}"
    )

    print("-" * 95)

    for path, m in by_churn[:20]:
        short = path if len(path) < 43 else "..." + path[-40:]

        print(
            f"  {short:<43} "
            f"{m['churn']:>7} "
            f"{m['changes']:>6} "
            f"{m['authors']:>8} "
            f"{m['owner']:<20} "
            f"{m['owner_pct']:>4.0f}%"
        )

    # Samotne wyspy
    lonely = [
        (p, m)
        for p, m in file_metrics.items()
        if m["authors"] == 1
    ]

    print("\n--- Samotne wyspy (1 autor) ---")

    print(
        f"  {len(lonely)} z {len(file_metrics)} plików "
        f"({len(lonely)/len(file_metrics)*100:.1f}%) "
        f"ma tylko jednego autora"
    )

    # Truck factor
    print("\n--- Truck Factor ---")

    print(f"  Truck factor: {truck_factor}")

    print("  Kluczowi developerzy:")

    for dev in truck_devs:
        owned = sum(
            1
            for m in file_metrics.values()
            if m["owner"] == dev
        )

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

    print_report(
        file_metrics,
        truck_factor,
        truck_devs,
    )


if __name__ == "__main__":
    main()