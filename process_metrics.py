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
    metrics = defaultdict(lambda: {
        "churn": 0,
        "changes": 0,
        "authors_count": Counter()
    })

    for commit in commits:
        author = commit["author"]
        for file_stat in commit["files"]:
            path = file_stat["path"]
            adds = file_stat["adds"]
            deletes = file_stat["deletes"]

            metrics[path]["churn"] += (adds + deletes)
            metrics[path]["changes"] += 1
            metrics[path]["authors_count"][author] += 1

    result = {}
    for path, data in metrics.items():
        if data["changes"] == 0:
            continue
        
        # Wyliczamy owner'a
        owner, owner_commits = data["authors_count"].most_common(1)[0]
        owner_pct = (owner_commits / data["changes"]) * 100

        result[path] = {
            "churn": data["churn"],
            "changes": data["changes"],
            "authors": len(data["authors_count"]),
            "owner": owner,
            "owner_pct": owner_pct,
            "author_counts": data["authors_count"] # do zadania 3
        }

    return result


def compute_truck_factor(file_metrics: dict[str, dict]) -> tuple[int, list[str]]:
    """Compute truck factor - minimum developers covering >50% of files."""
    owner_files = defaultdict(list)
    for path, data in file_metrics.items():
        owner = data["owner"]
        owner_files[owner].append(path)

    total_files = len(file_metrics)
    target_files = total_files / 2

    truck_devs = []
    covered_files_count = 0

    # Sortujemy developerow po tym ilu plikow sa ownerami malejaco
    devs_sorted = sorted(owner_files.keys(), key=lambda d: len(owner_files[d]), reverse=True)

    for dev in devs_sorted:
        if covered_files_count > target_files:
            break
        truck_devs.append(dev)
        covered_files_count += len(owner_files[dev])

    truck_factor = len(truck_devs)
    return truck_factor, truck_devs


def print_report(file_metrics: dict[str, dict],
                 truck_factor: int,
                 truck_devs: list[str]) -> None:
    """Print process metrics report."""
    print(f"\n{'=' * 70}")
    print(f"RAPORT METRYK PROCESOWYCH")
    print(f"{'=' * 70}")

    by_churn = sorted(file_metrics.items(),
                      key=lambda x: x[1]["churn"], reverse=True)

    print(f"\n--- TOP 20 najgoretszych plikow (wg churn) ---")
    print(f"{'Plik':<45} {'Churn':>7} {'Zmian':>6} "
          f"{'Autorow':>8} {'Owner':<20} {'%':>5}")
    print("-" * 95)

    for path, m in by_churn[:20]:
        short = path if len(path) < 43 else "..." + path[-40:]
        print(f"  {short:<43} {m['churn']:>7} {m['changes']:>6} "
              f"{m['authors']:>8} {m['owner']:<20} {m['owner_pct']:>4.0f}%")

    lonely = [(p, m) for p, m in file_metrics.items() if m["authors"] == 1]
    print(f"\n--- Samotne wyspy (1 autor) ---")
    print(f"  {len(lonely)} z {len(file_metrics)} plikow "
          f"({len(lonely)/len(file_metrics)*100:.1f}%) "
          f"ma tylko jednego autora")

    print(f"\n--- Truck Factor ---")
    print(f"  Truck factor: {truck_factor}")
    print(f"  Kluczowi developerzy:")
    for dev in truck_devs:
        owned = sum(1 for m in file_metrics.values() if m["owner"] == dev)
        print(f"    {dev} (owner {owned} plikow)")


def main():
    if len(sys.argv) < 2:
        print("Uzycie: python process_metrics.py <sciezka_do_repo>")
        sys.exit(1)

    repo_path = sys.argv[1]
    print(f"Analizuje metryki procesowe: {repo_path}")

    commits = parse_git_numstat(repo_path)
    print(f"Sparsowano {len(commits)} commitow")

    file_metrics = compute_file_metrics(commits)
    print(f"Znaleziono {len(file_metrics)} plikow")

    truck_factor, truck_devs = compute_truck_factor(file_metrics)
    print_report(file_metrics, truck_factor, truck_devs)


if __name__ == "__main__":
    main()
