#!/usr/bin/env python3
"""Process Metrics Calculator - churn, ownership, truck factor."""

import io
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer,
        encoding="utf-8",
        errors="replace",
        line_buffering=True,
    )


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


def _pick_owner(author_commits: Counter) -> tuple[str, int, int]:
    """Owner = autor z największą liczbą commitów przy pliku; remis alfabetycznie."""
    if not author_commits:
        return ("(brak)", 0, 0)
    total = sum(author_commits.values())
    best_author = None
    best_count = -1
    for author, cnt in author_commits.items():
        if cnt > best_count or (cnt == best_count and (best_author is None or author < best_author)):
            best_count = cnt
            best_author = author
    assert best_author is not None
    pct = (100.0 * best_count / total) if total else 0.0
    return (best_author, best_count, total)


def compute_file_metrics(commits: list[dict]) -> dict[str, dict]:
    """Compute per-file process metrics.

    Returns dict: filepath -> {churn, changes, authors, owner, owner_pct}
    """
    churn: dict[str, int] = defaultdict(int)
    author_commits_per_file: dict[str, Counter] = defaultdict(Counter)
    commits_per_file: dict[str, set[str]] = defaultdict(set)

    for commit in commits:
        h = commit["hash"]
        author = commit["author"]
        for finfo in commit["files"]:
            path = finfo["path"]
            churn[path] += finfo["adds"] + finfo["deletes"]
            author_commits_per_file[path][author] += 1
            commits_per_file[path].add(h)

    out: dict[str, dict] = {}
    for path in churn.keys():
        ac = author_commits_per_file[path]
        owner, _owner_commits, total_touch = _pick_owner(ac)
        distinct = len(ac)
        changes = len(commits_per_file[path])
        owner_pct = (100.0 * ac[owner] / total_touch) if total_touch else 0.0
        out[path] = {
            "churn": churn[path],
            "changes": changes,
            "authors": distinct,
            "owner": owner,
            "owner_pct": owner_pct,
        }
    return out


def compute_truck_factor(file_metrics: dict[str, dict]) -> tuple[int, list[str]]:
    """Compute truck factor - minimum developers covering >50% of files.

    Zachłannie: wśród jeszcze niepokrytych plików wybieramy autora,
    który jest ownerem największej liczby z nich, dodajemy go do zbioru
    i usuwamy te pliki, aż pokrycie > 50%.
    """
    all_paths = list(file_metrics.keys())
    n = len(all_paths)
    if n == 0:
        return 0, []

    uncovered = set(all_paths)
    truck_devs: list[str] = []

    def covered_count() -> int:
        return n - len(uncovered)

    # > 50% plików: pokryte * 2 > n
    while covered_count() * 2 <= n:
        counts: Counter[str] = Counter()
        for path in uncovered:
            owner = file_metrics[path]["owner"]
            if owner and owner != "(brak)":
                counts[owner] += 1
        if not counts:
            break
        best_dev = None
        best_k = -1
        for dev, k in counts.items():
            if k > best_k or (k == best_k and (best_dev is None or dev < best_dev)):
                best_k = k
                best_dev = dev
        assert best_dev is not None
        truck_devs.append(best_dev)
        to_remove = {p for p in uncovered if file_metrics[p]["owner"] == best_dev}
        uncovered -= to_remove

    return len(truck_devs), truck_devs


def print_report(
    file_metrics: dict[str, dict],
    truck_factor: int,
    truck_devs: list[str],
) -> None:
    """Print process metrics report."""
    print(f"\n{'=' * 70}")
    print("RAPORT METRYK PROCESOWYCH")
    print(f"{'=' * 70}")

    by_churn = sorted(file_metrics.items(), key=lambda x: x[1]["churn"], reverse=True)

    print("\n--- TOP 20 najgorętszych plików (wg churn) ---")
    print(
        f"{'Plik':<45} {'Churn':>7} {'Zmian':>6} "
        f"{'Autorów':>8} {'Owner':<20} {'%':>5}"
    )
    print("-" * 95)

    for path, m in by_churn[:20]:
        short = path if len(path) < 43 else "..." + path[-40:]
        print(
            f"  {short:<43} {m['churn']:>7} {m['changes']:>6} "
            f"{m['authors']:>8} {m['owner']:<20} {m['owner_pct']:>4.0f}%"
        )

    lonely = [(p, m) for p, m in file_metrics.items() if m["authors"] == 1]
    total_f = len(file_metrics)
    pct_lonely = (100.0 * len(lonely) / total_f) if total_f else 0.0
    print("\n--- Samotne wyspy (1 autor) ---")
    print(
        f"  {len(lonely)} z {total_f} plików ({pct_lonely:.1f}%) "
        "ma tylko jednego autora"
    )

    print("\n--- Truck Factor ---")
    print(f"  Truck factor: {truck_factor}")
    print("  Kluczowi developerzy:")
    for dev in truck_devs:
        owned = sum(1 for m in file_metrics.values() if m["owner"] == dev)
        print(f"    {dev} (owner {owned} plików)")


def main() -> None:
    if len(sys.argv) < 2:
        print("Użycie: python process_metrics.py <ścieżka_do_repo>")
        sys.exit(1)

    repo_path = sys.argv[1]
    p = Path(repo_path)
    if not p.is_dir():
        print(f"Nie ma takiego katalogu: {repo_path}")
        sys.exit(1)
    if not (p / ".git").exists() and not (p / ".git").is_file():
        print(f"To nie wygląda na repozytorium git: {repo_path}")
        sys.exit(1)

    print(f"Analizuję metryki procesowe: {repo_path}")

    commits = parse_git_numstat(str(p.resolve()))
    print(f"Sparsowano {len(commits)} commitów")

    file_metrics = compute_file_metrics(commits)
    print(f"Znaleziono {len(file_metrics)} plików")

    truck_factor, truck_devs = compute_truck_factor(file_metrics)
    print_report(file_metrics, truck_factor, truck_devs)


if __name__ == "__main__":
    main()
