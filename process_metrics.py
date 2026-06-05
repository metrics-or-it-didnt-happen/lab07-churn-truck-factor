#!/usr/bin/env python3
"""Process Metrics Calculator - churn, ownership, truck factor."""

import subprocess
import sys
from argparse import ArgumentParser
from collections import Counter, defaultdict
from pathlib import Path

import altair as alt
import pandas as pd

UNIT_SEP = "\x1f"


def parse_git_numstat(repo_path: str) -> list[dict]:
    """Parse git log --numstat output into structured commit data."""
    result = subprocess.run(
        [
            "git", "log", "--numstat",
            f"--format={UNIT_SEP}%H{UNIT_SEP}%an{UNIT_SEP}%ad",
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
        if line.startswith(UNIT_SEP):
            if current:
                commits.append(current)
            parts = line.split(UNIT_SEP)
            current = {
                "hash": parts[1],
                "author": parts[2],
                "date": parts[3],
                "files": [],
            }
        elif "\t" in line and current:
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
    """Compute per-file process metrics from parsed commits."""
    file_churn: dict[str, int] = defaultdict(int)
    file_changes: dict[str, int] = defaultdict(int)
    file_author_counts: dict[str, Counter] = defaultdict(Counter)

    for commit in commits:
        author = commit["author"]
        for f in commit["files"]:
            path = f["path"]
            file_churn[path] += f["adds"] + f["deletes"]
            file_changes[path] += 1
            file_author_counts[path][author] += 1

    metrics = {}
    for path in file_churn:
        author_counts = file_author_counts[path]
        owner, owner_commits = author_counts.most_common(1)[0]
        total_commits = sum(author_counts.values())
        metrics[path] = {
            "churn": file_churn[path],
            "changes": file_changes[path],
            "authors": len(author_counts),
            "owner": owner,
            "owner_pct": owner_commits / total_commits * 100,
            "author_counts": author_counts,
        }

    return metrics


def compute_truck_factor(file_metrics: dict[str, dict]) -> tuple[int, list[str]]:
    """Compute truck factor using greedy set-cover algorithm."""
    file_owners = {path: m["owner"] for path, m in file_metrics.items()}
    total_files = len(file_owners)
    threshold = total_files / 2

    remaining = dict(file_owners)
    truck_devs = []
    covered = 0

    while covered <= threshold and remaining:
        owner_counts = Counter(remaining.values())
        top_dev, top_count = owner_counts.most_common(1)[0]
        truck_devs.append(top_dev)
        covered += top_count
        remaining = {p: o for p, o in remaining.items() if o != top_dev}

    return len(truck_devs), truck_devs


def print_report(
    file_metrics: dict[str, dict],
    truck_factor: int,
    truck_devs: list[str],
) -> None:
    """Print process metrics report to stdout."""
    print(f"\n{'=' * 80}")
    print("PROCESS METRICS REPORT")
    print(f"{'=' * 80}")

    by_churn = sorted(
        file_metrics.items(), key=lambda x: x[1]["churn"], reverse=True,
    )

    print(f"\n--- Top 20 hottest files (by churn) ---")
    print(
        f"  {'File':<50} {'Churn':>7} {'Changes':>8} "
        f"{'Authors':>8} {'Owner':<25} {'%':>5}"
    )
    print(f"  {'-' * 103}")

    for path, m in by_churn[:20]:
        short = path if len(path) < 48 else "..." + path[-45:]
        print(
            f"  {short:<50} {m['churn']:>7} {m['changes']:>8} "
            f"{m['authors']:>8} {m['owner']:<25} {m['owner_pct']:>4.0f}%"
        )

    lonely = [(p, m) for p, m in file_metrics.items() if m["authors"] == 1]
    print(f"\n--- Lonely islands (single author) ---")
    print(
        f"  {len(lonely)} of {len(file_metrics)} files "
        f"({len(lonely) / len(file_metrics) * 100:.1f}%) "
        f"have only one author"
    )

    print(f"\n--- Truck Factor ---")
    print(f"  Truck factor: {truck_factor}")
    print(f"  Key developers:")
    for dev in truck_devs:
        owned = sum(1 for m in file_metrics.values() if m["owner"] == dev)
        print(f"    {dev} (owns {owned} files)")

    print()


def build_ownership_heatmap(
    file_metrics: dict[str, dict], output_dir: str,
) -> None:
    """Build and save developer x directory ownership heatmap with Altair."""
    dir_author_commits: dict[str, Counter] = defaultdict(Counter)

    for path, m in file_metrics.items():
        directory = path.split("/")[0] if "/" in path else "."
        dir_author_commits[directory] += m["author_counts"]

    top_dirs = sorted(
        dir_author_commits, key=lambda d: sum(dir_author_commits[d].values()),
        reverse=True,
    )[:15]

    all_authors: Counter = Counter()
    for d in top_dirs:
        all_authors += dir_author_commits[d]
    top_authors = [a for a, _ in all_authors.most_common(10)]

    rows = []
    for d in top_dirs:
        total = sum(dir_author_commits[d].values())
        for author in top_authors:
            pct = dir_author_commits[d][author] / total * 100 if total else 0
            rows.append({"Directory": d, "Developer": author, "Commits (%)": round(pct, 1)})

    df = pd.DataFrame(rows)

    chart = (
        alt.Chart(df)
        .mark_rect()
        .encode(
            x=alt.X("Directory:N", sort=top_dirs, title="Directory"),
            y=alt.Y("Developer:N", sort=top_authors, title="Developer"),
            color=alt.Color(
                "Commits (%):Q",
                scale=alt.Scale(scheme="orangered"),
                title="Commits (%)",
            ),
            tooltip=["Directory", "Developer", "Commits (%)"],
        )
        .properties(
            title="Ownership Heatmap: Developer x Directory",
            width=600,
            height=350,
        )
    )

    text = (
        alt.Chart(df)
        .mark_text(fontSize=10)
        .encode(
            x=alt.X("Directory:N", sort=top_dirs),
            y=alt.Y("Developer:N", sort=top_authors),
            text=alt.Text("Commits (%):Q", format=".0f"),
            color=alt.condition(
                alt.datum["Commits (%)"] > 40,
                alt.value("white"),
                alt.value("black"),
            ),
        )
    )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (chart + text).save(str(out / "ownership_heatmap.png"), scale_factor=2)
    print(f"Heatmap saved to {out / 'ownership_heatmap.png'}")


def main() -> None:
    parser = ArgumentParser(description="Process metrics calculator")
    parser.add_argument("repo_path", help="Path to git repository")
    parser.add_argument("--output", default="output", help="Output directory")
    args = parser.parse_args()

    repo = Path(args.repo_path)
    if not (repo / ".git").exists():
        print(f"Not a git repository: {repo}")
        sys.exit(1)

    print(f"Analyzing process metrics: {repo}")
    commits = parse_git_numstat(str(repo))
    print(f"Parsed {len(commits)} commits")

    file_metrics = compute_file_metrics(commits)
    print(f"Found {len(file_metrics)} files")

    truck_factor, truck_devs = compute_truck_factor(file_metrics)
    print_report(file_metrics, truck_factor, truck_devs)

    output_dir = Path(args.output)
    build_ownership_heatmap(file_metrics, str(output_dir))


if __name__ == "__main__":
    main()
