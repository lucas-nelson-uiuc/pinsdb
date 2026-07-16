"""Generate docs/index.md from the current bowling database.

Unlike results.py / statistic.py (marimo notebooks exported to HTML), this is a
plain script that writes Markdown directly. Zensical builds Markdown natively,
so there's no notebook export step -- just run this and commit the result.

Usage:
    uv run homepage.py
    # or
    python homepage.py
"""

import datetime
import pathlib

import attrs
import polars as pl

from pinsdb.models import Game
from pinsdb.namespace.expressions import Bowling  # noqa: F401

DOCS_INDEX = pathlib.Path("docs/index.md")

# Same bowler set used on the Statistics page -- keep these in sync.
BOWLERS: tuple[str, ...] = (
    "Alek",
    "Cam",
    "Jake",
    "Lucas",
    "Munson",
    "Ryley",
    "Spencer",
    "Tristan",
    "Stuart",
)

FRONTMATTER = """---
icon: lucide/rocket
---
"""


def load_frame() -> pl.DataFrame:
    all_games = sorted(
        Game.load_games(verbose=False),
        key=lambda g: (g.date, g.game_id, g.bowler.bowler_id),
    )
    return (
        pl.DataFrame([attrs.asdict(g) for g in all_games])
        .with_columns(
            pl.col("bowler").struct.field("bowler_id"),
            pl.col("throws").bowling.compute_score(),
        )
        .sort("date", "game_id")
        .drop("bowler")
        .filter(pl.col("bowler_id").is_in(BOWLERS))
    )


def compute_leaderboard(frame: pl.DataFrame) -> pl.DataFrame:
    """Wins/games/win-rate per bowler, used for 'current leader'."""
    ranked = (
        frame.group_by("date", "game_id")
        .agg(
            pl.col("bowler_id").bowling.get_highest_bowler().alias("winner"),
            pl.col("bowler_id"),
        )
        .explode("bowler_id", empty_as_null=True)
        .with_columns((pl.col("bowler_id") == pl.col("winner")).alias("won"))
        .group_by("bowler_id")
        .agg(
            pl.len().alias("games"),
            pl.col("won").sum().alias("wins"),
        )
        .with_columns((pl.col("wins") / pl.col("games")).alias("win_rate"))
        .sort("wins", "win_rate", descending=True)
    )
    return ranked


def build_markdown(frame: pl.DataFrame) -> str:
    total_games = frame.height
    total_pins = frame["throws"].list.sum().sum()
    date_min = frame["date"].min()
    date_max = frame["date"].max()
    n_bowlers = frame["bowler_id"].n_unique()

    best_row = frame.sort("score", descending=True).row(0, named=True)
    leaderboard = compute_leaderboard(frame)
    leader = leaderboard.row(0, named=True)

    recent_date = date_max
    recent_games = frame.filter(pl.col("date") == recent_date).sort(
        "game_id", "score", descending=[False, True]
    )

    today = datetime.date.today().strftime("%B %d, %Y")

    lines: list[str] = []
    lines.append(FRONTMATTER)
    lines.append("# PinsDB\n")
    lines.append(
        "A running record of every frame my friends and I have bowled -- "
        "who's winning, who's streaking, and who owes who a beer.\n"
    )

    lines.append("## At a Glance\n")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Games logged | {total_games:,} |")
    lines.append(f"| Bowlers tracked | {n_bowlers} |")
    lines.append(f"| Total pins knocked down | {total_pins:,} |")
    lines.append(
        f"| Date range | {date_min.strftime('%b %d, %Y')} – {date_max.strftime('%b %d, %Y')} |"
    )
    lines.append("")

    lines.append("## Current Leader\n")
    lines.append(
        f"**{leader['bowler_id']}** leads the pack with **{leader['wins']}** wins "
        f"out of {leader['games']} games ({leader['win_rate']:.0%} win rate).\n"
    )

    lines.append("## All-Time High Score\n")
    lines.append(
        f"**{best_row['bowler_id']}** holds the top score with a **{best_row['score']}**, "
        f"bowled on {best_row['date'].strftime('%B %d, %Y')}.\n"
    )

    lines.append(f"## Most Recent Session -- {recent_date.strftime('%B %d, %Y')}\n")
    lines.append("| Game | Bowler | Score |")
    lines.append("|---|---|---|")
    for row in recent_games.iter_rows(named=True):
        lines.append(f"| {row['game_id']} | {row['bowler_id']} | {row['score']} |")
    lines.append("")

    lines.append("---\n")
    lines.append(
        "Want the full picture? Check out [Statistics](statistic.html) for "
        "strikes, spares, and scoring trends, or browse every [Result](results.html) "
        "game by game.\n"
    )
    lines.append(f"*Last updated {today}.*")

    return "\n".join(lines) + "\n"


def main() -> None:
    frame = load_frame()
    markdown = build_markdown(frame)
    DOCS_INDEX.parent.mkdir(parents=True, exist_ok=True)
    DOCS_INDEX.write_text(markdown)
    print(f"Wrote {DOCS_INDEX} ({len(markdown):,} chars)")


if __name__ == "__main__":
    main()
