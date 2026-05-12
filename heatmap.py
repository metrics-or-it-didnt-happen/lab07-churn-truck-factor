import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import sys
from  process_metrics import compute_file_metrics, parse_git_numstat

from collections import defaultdict, Counter


def build_ownership_matrix(file_metrics: dict) -> pd.DataFrame:
    """
    Build developer x directory ownership matrix.

    Rows    -> developers
    Columns -> top-level directories
    Values  -> % commitów developera w katalogu
    """

    # directory -> Counter(author -> commits)
    dir_author_commits = defaultdict(Counter)

    for path, metrics in file_metrics.items():

        # top-level directory
        directory = path.split("/")[0] if "/" in path else "."

        # author_counter musi istnieć w file_metrics
        author_counts = metrics["author_counter"]

        for author, commits in author_counts.items():
            dir_author_commits[directory][author] += commits

    # wszystkie katalogi
    directories = sorted(dir_author_commits.keys())

    # wszyscy developerzy
    developers = sorted({
        dev
        for counter in dir_author_commits.values()
        for dev in counter.keys()
    })

    # budowa macierzy
    matrix = pd.DataFrame(
        0.0,
        index=developers,
        columns=directories,
    )

    # normalizacja do %
    for directory, author_counter in dir_author_commits.items():

        total_commits = sum(author_counter.values())

        if total_commits == 0:
            continue

        for author, commits in author_counter.items():

            pct = commits / total_commits * 100

            matrix.loc[author, directory] = pct

    return matrix


def plot_ownership_heatmap(
    matrix: pd.DataFrame,
    output_file: str = "ownership_heatmap.png",
    min_pct: float = 1.0,
):
    """
    Draw ownership heatmap.

    min_pct:
        ukrywa bardzo małe wartości dla czytelności
    """

    # filtrowanie bardzo małych wartości
    filtered = matrix.copy()

    filtered[filtered < min_pct] = 0

    plt.figure(figsize=(14, 8))

    sns.heatmap(
        filtered,
        annot=True,
        fmt=".0f",
        cmap="YlOrRd",
        linewidths=0.5,
        cbar_kws={
            "label": "% commitów"
        },
    )

    plt.xlabel("Katalog")
    plt.ylabel("Developer")
    plt.title("Ownership heatmap: developer x katalog")

    plt.tight_layout()

    plt.savefig(output_file, dpi=150)

    print(f"Heatmap saved to: {output_file}")


# =========================================================
# PRZYKŁAD UŻYCIA
# =========================================================



def main():
    if len(sys.argv) < 2:
        print("Użycie: python heatmap.py <ścieżka_do_repo>")
        sys.exit(1)

    repo_path = sys.argv[1]

    print(f"Analizuję metryki procesowe: {repo_path}")

    commits = parse_git_numstat(repo_path)

    print(f"Sparsowano {len(commits)} commitów")

    file_metrics = compute_file_metrics(commits)

    matrix = build_ownership_matrix(file_metrics)

    # opcjonalnie:
    # usuń developerów z bardzo małym udziałem globalnym
    matrix = matrix.loc[matrix.sum(axis=1) > 5]

    plot_ownership_heatmap(matrix)


if __name__ == "__main__":
    main()
