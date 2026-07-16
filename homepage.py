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

MEDALS = ("🥇", "🥈", "🥉")


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
    """Wins/games/win-rate per bowler, used for 'current leader' + standings."""
    ranked = (
        frame.group_by("date", "game_id")
        .agg(
            pl.col("bowler_id").bowling.get_highest_bowler().alias("winner"),
            pl.col("bowler_id"),
        )
        .explode("bowler_id")
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


def compute_frame_awards(frame: pl.DataFrame) -> pl.DataFrame:
    """Per-bowler wombat/gutter/strike counts, used for Fun Awards."""
    frames_data = (
        frame.with_columns(pl.col("throws").bowling.construct_frames())
        .explode("frames")
        .with_columns(
            pl.col("frames").bowling.is_gutter(),
            pl.col("frames").bowling.is_strike(),
            pl.col("frames").bowling.is_wombat(),
        )
    )
    return frames_data.group_by("bowler_id").agg(
        pl.col("is_wombat").sum().alias("wombats"),
        pl.col("is_gutter").sum().alias("gutters"),
        pl.col("is_strike").sum().alias("strikes"),
    )


def compute_current_streaks(frame: pl.DataFrame) -> dict[str, int]:
    """Current consecutive-win streak per bowler, counted back from their last game."""
    per_game_winner = (
        frame.group_by("date", "game_id")
        .agg(
            pl.col("bowler_id").bowling.get_highest_bowler().alias("winner"),
            pl.col("bowler_id"),
        )
        .explode("bowler_id")
        .with_columns((pl.col("bowler_id") == pl.col("winner")).alias("won"))
        .sort("date", "game_id")
    )

    streaks: dict[str, int] = {}
    for bowler in BOWLERS:
        results = (
            per_game_winner.filter(pl.col("bowler_id") == bowler)
            .sort("date", "game_id")["won"]
            .to_list()
        )
        streak = 0
        for won in reversed(results):
            if not won:
                break
            streak += 1
        streaks[bowler] = streak
    return streaks


def compute_trivia(frame: pl.DataFrame) -> dict:
    n_sessions = frame["date"].n_unique()

    blowout = (
        frame.group_by("date", "game_id")
        .agg(
            (pl.col("score").max() - pl.col("score").min()).alias("margin"),
            pl.col("bowler_id").bowling.get_highest_bowler(),
        )
        .sort("margin", descending=True)
        .row(0, named=True)
    )

    busiest_day = (
        frame.group_by("date")
        .agg(pl.len().alias("games"))
        .sort("games", descending=True)
        .row(0, named=True)
    )

    perfect_games = frame.filter(pl.col("score") == 300).height

    return {
        "n_sessions": n_sessions,
        "blowout": blowout,
        "busiest_day": busiest_day,
        "perfect_games": perfect_games,
    }


def build_markdown(frame: pl.DataFrame) -> str:
    total_games = frame.height
    total_pins = frame["throws"].list.sum().sum()
    date_min = frame["date"].min()
    date_max = frame["date"].max()
    n_bowlers = frame["bowler_id"].n_unique()

    best_row = frame.sort("score", descending=True).row(0, named=True)
    leaderboard = compute_leaderboard(frame)
    leader = leaderboard.row(0, named=True)
    awards = compute_frame_awards(frame)
    streaks = compute_current_streaks(frame)
    trivia = compute_trivia(frame)

    recent_date = date_max
    recent_games = frame.filter(pl.col("date") == recent_date).sort(
        "game_id", "score", descending=[False, True]
    )

    wombat_king = awards.sort("wombats", descending=True).row(0, named=True)
    gutter_champ = awards.sort("gutters", descending=True).row(0, named=True)
    on_fire_bowler, on_fire_streak = max(streaks.items(), key=lambda kv: kv[1])

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
    lines.append(f"| Sessions | {trivia['n_sessions']:,} |")
    lines.append(f"| Bowlers tracked | {n_bowlers} |")
    lines.append(f"| Total pins knocked down | {total_pins:,} |")
    lines.append(
        f"| Date range | {date_min.strftime('%b %d, %Y')} – {date_max.strftime('%b %d, %Y')} |"
    )
    lines.append("")

    lines.append("## Standings\n")
    lines.append("| | Bowler | Wins | Games | Win Rate |")
    lines.append("|---|---|---|---|---|")
    for i, row in enumerate(leaderboard.head(3).iter_rows(named=True)):
        lines.append(
            f"| {MEDALS[i]} | **{row['bowler_id']}** | {row['wins']} | "
            f"{row['games']} | {row['win_rate']:.0%} |"
        )
    lines.append("")

    lines.append("## Highlights\n")

    lines.append('=== "Current Leader"')
    lines.append("")
    lines.append(
        f"    **{leader['bowler_id']}** leads the pack with **{leader['wins']}** wins "
        f"out of {leader['games']} games ({leader['win_rate']:.0%} win rate)."
    )
    lines.append("")

    lines.append('=== "All-Time High Score"')
    lines.append("")
    lines.append(
        f"    **{best_row['bowler_id']}** holds the top score with a **{best_row['score']}**, "
        f"bowled on {best_row['date'].strftime('%B %d, %Y')}."
    )
    lines.append("")

    lines.append('=== "Most Recent Session"')
    lines.append("")
    lines.append(f"    {recent_date.strftime('%B %d, %Y')}")
    lines.append("")
    lines.append("    | Game | Bowler | Score |")
    lines.append("    |---|---|---|")
    for row in recent_games.iter_rows(named=True):
        lines.append(f"    | {row['game_id']} | {row['bowler_id']} | {row['score']} |")
    lines.append("")

    lines.append("## Fun Awards\n")

    lines.append('=== "🌵 Wombat King"')
    lines.append("")
    lines.append(
        f"    **{wombat_king['bowler_id']}** has the most wombats on record, with "
        f"**{wombat_king['wombats']}** career wombats."
    )
    lines.append("")

    lines.append('=== "🕳️ Gutter Champ"')
    lines.append("")
    lines.append(
        f"    **{gutter_champ['bowler_id']}** has thrown the most gutter frames, with "
        f"**{gutter_champ['gutters']}** and counting. A dubious honor."
    )
    lines.append("")

    lines.append('=== "🔥 On Fire"')
    lines.append("")
    if on_fire_streak > 0:
        lines.append(
            f"    **{on_fire_bowler}** is riding a **{on_fire_streak}**-game win streak "
            f"heading into the next session."
        )
    else:
        lines.append("    Nobody's on a win streak right now -- anyone's game.")
    lines.append("")

    lines.append("## Fun Facts\n")
    lines.append('!!! tip "Biggest Blowout"')
    lines.append(
        f"    **{trivia['blowout']['winner']}** won by **{trivia['blowout']['margin']}** "
        f"points on {trivia['blowout']['date'].strftime('%B %d, %Y')} -- the largest "
        f"margin of victory in a single game on record."
    )
    lines.append("")
    lines.append('!!! note "Busiest Session"')
    lines.append(
        f"    {trivia['busiest_day']['date'].strftime('%B %d, %Y')} saw "
        f"**{trivia['busiest_day']['games']}** games bowled in a single day -- "
        f"the most of any session so far."
    )
    lines.append("")
    lines.append('!!! info "Perfect Game Watch"')
    if trivia["perfect_games"] > 0:
        lines.append(
            f"    **{trivia['perfect_games']}** perfect game(s) bowled so far. 🎳"
        )
    else:
        lines.append(
            "    Nobody's bowled a 300 yet. The all-time high is "
            f"**{best_row['score']}**, set by **{best_row['bowler_id']}**."
        )
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
