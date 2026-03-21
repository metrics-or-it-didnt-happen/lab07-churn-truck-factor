#!/usr/bin/env python3
"""Process Metrics Calculator - churn, ownership, truck factor."""

import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def _resolve_rename(path: str) -> str:
    """Resolve git rename/move notation to the resulting (new) path.

    Git --numstat encodes renames in two ways:
      1. Partial:  '{old => new}/extractor/file.py'
                   'yt_dlp/{old_dir => new_dir}/file.py'
      2. Full:     'old/path/file.py => new/path/file.py'

    In both cases we want the *new* name only, so history is attributed
    to the file at its current location.
    """
    import re

    if "=>" in path and "{" not in path:
        return path.split("=>")[1].strip()

    m = re.search(r"\{([^}]*?)=>([^}]*?)\}", path)
    if m:
        old_part, new_part = m.group(1).strip(), m.group(2).strip()
        resolved = path[: m.start()] + new_part + path[m.end() :]
        resolved = re.sub(r"/+", "/", resolved).strip("/")
        return resolved

    return path


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
                    "path": _resolve_rename(parts[2]),
                    "adds": adds,
                    "deletes": deletes,
                })

    if current:
        commits.append(current)

    return commits


def compute_file_metrics(commits: list[dict]) -> dict[str, dict]:
    """Compute per-file process metrics.

    Returns dict: filepath -> {churn, changes, authors, owner, owner_pct,
                                author_counts}
    """
    churn: dict[str, int] = defaultdict(int)
    changes: dict[str, int] = defaultdict(int)
    author_counts: dict[str, Counter] = defaultdict(Counter)

    for commit in commits:
        author = commit["author"]
        for f in commit["files"]:
            path = f["path"]
            churn[path] += f["adds"] + f["deletes"]
            changes[path] += 1
            author_counts[path][author] += 1

    file_metrics: dict[str, dict] = {}

    for path in churn:
        counts = author_counts[path]
        owner, owner_commits = counts.most_common(1)[0]
        total_commits = sum(counts.values())
        owner_pct = owner_commits / total_commits * 100

        file_metrics[path] = {
            "churn": churn[path],
            "changes": changes[path],
            "authors": len(counts),
            "owner": owner,
            "owner_pct": owner_pct,
            "author_counts": counts,
        }

    return file_metrics


def compute_truck_factor(file_metrics: dict[str, dict]) -> tuple[int, list[str]]:
    """Compute truck factor — minimum developers covering >50% of files.

    Algorithm:
    1. For each file, determine the owner (most commits)
    2. Count how many files each developer owns
    3. Greedily pick developer with most owned files
    4. Remove their files from the pool
    5. Repeat until >50% files are covered
    """
    total_files = len(file_metrics)
    if total_files == 0:
        return 0, []

    threshold = total_files * 0.5

    dev_files: dict[str, set] = defaultdict(set)
    for path, m in file_metrics.items():
        dev_files[m["owner"]].add(path)

    covered: set[str] = set()
    truck_devs: list[str] = []

    while len(covered) <= threshold:
        if not dev_files:
            break

        best_dev = max(dev_files, key=lambda d: len(dev_files[d] - covered))
        new_files = dev_files[best_dev] - covered

        if not new_files:
            break

        covered |= new_files
        truck_devs.append(best_dev)
        del dev_files[best_dev]

    return len(truck_devs), truck_devs


def build_ownership_matrix(file_metrics: dict[str, dict]) -> pd.DataFrame:
    """Build developer x directory ownership matrix.

    Cell value = % commitów danego developera w danym katalogu
    (commitów dewelopera w katalogu / wszystkich commitów w katalogu * 100).
    """
    dir_author_commits: dict[str, Counter] = defaultdict(Counter)

    for path, m in file_metrics.items():
        directory = path.split("/")[0] if "/" in path else "."
        dir_author_commits[directory] += m["author_counts"]

    all_dirs = sorted(dir_author_commits.keys())
    all_devs = sorted({
        dev
        for counts in dir_author_commits.values()
        for dev in counts
    })

    data: dict[str, dict[str, float]] = {d: {} for d in all_devs}
    for directory, counts in dir_author_commits.items():
        total = sum(counts.values())
        for dev in all_devs:
            data[dev][directory] = counts[dev] / total * 100 if total else 0.0

    df = pd.DataFrame(data, index=all_dirs).T
    df.index.name = "Developer"
    df.columns.name = "Katalog"
    return df


def plot_ownership_heatmap(matrix: pd.DataFrame,
                           output_path: str = "ownership_heatmap.png",
                           top_devs: int = 20,
                           top_dirs: int = 30) -> None:
    """Render and save ownership heatmap (developer x directory).

    Limits axes to top_devs (by total activity) and top_dirs (by total
    activity) to keep the figure within a renderable size.
    """
    if matrix.empty:
        print("Brak danych do heatmapy.")
        return

    dev_totals = matrix.sum(axis=1).nlargest(top_devs).index
    matrix = matrix.loc[dev_totals]

    dir_totals = matrix.sum(axis=0).nlargest(top_dirs).index
    matrix = matrix[dir_totals]

    cell_h, cell_w = 0.45, 1.2
    fig_h = min(max(5, int(len(matrix.index) * cell_h)), 40)
    fig_w = min(max(8, int(len(matrix.columns) * cell_w)), 50)

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    sns.heatmap(
        matrix,
        annot=True,
        fmt=".0f",
        cmap="YlOrRd",
        linewidths=0.4,
        linecolor="white",
        cbar_kws={"label": "% commitów"},
        ax=ax,
    )
    ax.set_xlabel("Katalog")
    ax.set_ylabel("Developer")
    ax.set_title(
        f"Ownership heatmap: developer × katalog"
        f"  (top {len(matrix.index)} dev, top {len(matrix.columns)} dirs)"
    )
    plt.xticks(rotation=45, ha="right")
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"Heatmapa zapisana: {output_path}")


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

    matrix = build_ownership_matrix(file_metrics)
    plot_ownership_heatmap(matrix)


if __name__ == "__main__":
    main()