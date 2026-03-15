import marimo

__generated_with = "0.18.4"
app = marimo.App(width="full")


@app.cell(hide_code=True)
def _():
    # marimo notebook
    import marimo as mo

    # object handling
    import attrs

    # data handling
    import polars as pl

    # plotting
    import seaborn as sns

    # pinsdb module
    from pinsdb.models import Game
    from pinsdb.namespace.expressions import Bowling  # noqa: F401

    return Game, attrs, mo, pl, sns


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## **Load Games**
    ---
    """)
    return


@app.cell(hide_code=True)
def _(Game, attrs, pl):
    # define bowlers to include in `bowler_frame`
    BOWLERS: tuple[str] = (
        "Alek",
        "Cam",
        "Jake",
        "Lucas",
        "Munson",
        "Ryley",
        "Spencer",
        "Tristan",
    )

    # games stored as a Python object
    all_games = sorted(
        Game.load_games(verbose=False),
        key=lambda g: (g.date, g.game_id, g.bowler.bowler_id),
    )

    # games stored as a Polars DataFrame
    bowler_frame = (
        pl.DataFrame([attrs.asdict(game) for game in all_games])
        .with_columns(
            pl.col("bowler").struct.field("bowler_id"),
            pl.col("throws").bowling.compute_score(),
        )
        .sort("date", "game_id")
        .drop("bowler")
        .filter(pl.col("bowler_id").is_in(BOWLERS))
    )
    return BOWLERS, all_games, bowler_frame


@app.cell(hide_code=True)
def _(bowler_frame, pl):
    import polars.selectors as cs

    n_recent_games: int = 50
    col_recent_games: str = f"Recent Games ({n_recent_games:,})"

    frames_data = (
        bowler_frame.with_columns(pl.col("throws").bowling.construct_frames())
        .explode("frames")
        .drop("throws")
        .with_columns(
            pl.col("frames").bowling.is_gutter(),
            pl.col("frames").bowling.is_strike(),
            pl.col("frames").bowling.is_spare(),
            pl.col("frames").bowling.is_wombat(),
            pl.col("frames").bowling.is_open(),
        )
    )

    summary_detection_table = (
        frames_data.group_by("bowler_id")
        .agg(
            pl.col("frames").count().alias("Frames"),
            pl.col("is_strike").sum().alias("Strikes"),
            pl.col("is_spare").sum().alias("Spares"),
            pl.col("is_open").sum().alias("Open"),
            pl.col("is_wombat").sum().alias("Wombats"),
            pl.col("is_gutter").sum().alias("Gutters"),
        )
        .sort("Strikes", "Spares", "Wombats", descending=True)
    )

    summary_statistics_table = (
        bowler_frame.with_columns(
            pl.col("throws").list.sum().alias("pins"),
        )
        .group_by("bowler_id")
        .agg(
            pl.col("pins").count().alias("Games"),
            pl.col("pins").sum().alias("Pins"),
            pl.col("score").sum().alias("Points"),
            pl.col("score").min().alias("Lowest"),
            pl.col("score").max().alias("Highest"),
            pl.col("score").tail(n_recent_games).alias(col_recent_games),
        )
    )

    summary_table = (
        summary_statistics_table.join(summary_detection_table, on="bowler_id")
        .with_columns(
            (pl.col("Points") / pl.col("Games")).round(2).alias("Points Per Game"),
            (pl.col("Strikes") / pl.col("Games")).round(2).alias("Strikes Per Game"),
            (pl.col("Spares") / pl.col("Games")).round(2).alias("Spares Per Game"),
            (pl.col("Wombats") / pl.col("Games")).round(2).alias("Wombats Per Game"),
            (pl.col("Gutters") / pl.col("Games")).round(2).alias("Gutters Per Game"),
        )
        .sort("Points", descending=True)
        .select(
            "bowler_id",
            "Games",
            "Frames",
            "Pins",
            cs.starts_with("Point"),
            cs.starts_with("Strike"),
            cs.starts_with("Spare"),
            cs.starts_with("Wombat"),
            cs.starts_with("Gutter"),
        )
    )
    return cs, frames_data, summary_table


@app.cell(hide_code=True)
def _(all_games, cs, summary_table):
    from great_tables import GT

    DATETIME_FORMAT = "%b %d, %Y"
    RANGE_START = all_games[0].date.strftime(DATETIME_FORMAT)
    RANGE_END = all_games[-1].date.strftime(DATETIME_FORMAT)

    class Palette:
        PINS = "Greens"
        POINTS = "GnBu"
        STRIKES = "PuBu"
        SPARES = "Purples"
        WOMBATS = "Oranges"
        GUTTERS = "Reds"

    gt_table = (
        GT(summary_table)
        .tab_header(
            title="Bowling Statistics",
            subtitle=f"{RANGE_START} to {RANGE_END} | Sorted by Total Points",
        )
        .tab_stub(rowname_col="bowler_id")
        .tab_spanner(
            label="Scoring",
            columns=cs.starts_with("Pins") | cs.starts_with("Point"),
        )
        .tab_spanner(label="Strikes", columns=cs.starts_with("Strike"))
        .tab_spanner(label="Spares", columns=cs.starts_with("Spare"))
        .tab_spanner(label="Wombats", columns=cs.starts_with("Wombat"))
        .tab_spanner(label="Gutters", columns=cs.starts_with("Gutter"))
        .data_color(
            columns=cs.starts_with("Pins"),
            palette=Palette.PINS,
        )
        .data_color(
            columns=cs.starts_with("Point"),
            palette=Palette.POINTS,
        )
        .data_color(
            columns=cs.starts_with("Strike"),
            palette=Palette.STRIKES,
        )
        .data_color(
            columns=cs.starts_with("Spare"),
            palette=Palette.SPARES,
        )
        .data_color(
            columns=cs.starts_with("Wombat"),
            palette=Palette.WOMBATS,
        )
        .data_color(
            columns=cs.starts_with("Gutter"),
            palette=Palette.GUTTERS,
        )
        .fmt_number(
            columns=["Pins", "Points", "Frames", "Strikes", "Spares", "Wombats"],
            decimals=0,
        )
    )

    gt_table
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## **Scoring Leaderboards**
    ---
    """)
    return


@app.cell
def _(mo):
    N_SCORES = mo.ui.slider(
        start=1, stop=30, value=10, show_value=True, label="Number of Scores"
    ).form()
    N_SCORES
    return (N_SCORES,)


@app.cell
def _(N_SCORES, bowler_frame):
    from pinsdb.plot import plot_top_bottom_scores

    plot_top_bottom_scores(bowler_frame=bowler_frame, n=N_SCORES.value or 10)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## **Scoring Distributions**
    """)
    return


@app.cell(hide_code=True)
def _(bowler_frame):
    from pinsdb.plot import plot_score_distribution

    plot_score_distribution(bowler_frame=bowler_frame)
    return


@app.cell
def _(frames_data):
    from pinsdb.plot import plot_frame_outcome

    plot_frame_outcome(frames_data=frames_data)
    return


@app.cell
def _(frames_data):
    from pinsdb.plot import plot_strike_vs_spare_conversion

    plot_strike_vs_spare_conversion(frames_data=frames_data)
    return


@app.cell
def _(frames_data):
    from pinsdb.plot import plot_performance_per_frame

    plot_performance_per_frame(frames_data=frames_data)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## **Scoring Progressions**
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## **Pin Sequence**
    ---
    """)
    return


@app.cell(hide_code=True)
def _(frames_data):
    from pinsdb.plot import plot_first_throw_outcomes

    plot_first_throw_outcomes(frames_data=frames_data)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## **Score Progression**
    ---
    """)
    return


@app.cell
def _(mo):
    WINDOW_SIZE = mo.ui.slider(
        start=1, stop=30, step=1, value=15, show_value=True, label="Window Size"
    ).form()
    WINDOW_SIZE
    return (WINDOW_SIZE,)


@app.cell(hide_code=True)
def _(WINDOW_SIZE, bowler_frame):
    from pinsdb.plot import plot_personal_bests

    plot_personal_bests(
        bowler_frame=bowler_frame, rolling_window=WINDOW_SIZE.value or 10
    )
    return


if __name__ == "__main__":
    app.run()
