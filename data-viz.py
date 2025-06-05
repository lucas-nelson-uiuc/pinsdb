import marimo

__generated_with = "0.13.15"
app = marimo.App(width="full")


@app.cell
def _():
    # object handling
    import attrs

    # data handling
    import polars as pl

    # plotting
    from matplotlib import pyplot as plt
    import seaborn as sns

    # pinsdb module
    from pinsdb.models import Game
    return Game, attrs, pl


@app.cell
def _(mo):
    mo.md(
        r"""
    ### Load Games
    ---
    This will load all games from the files in `DATA_DIRECTORY` - until someone else uses this project this will be the local `.data/` folder.
    """
    )
    return


@app.cell
def _(Game, attrs, pl):
    # games stored as a Python object
    all_games = sorted(
        Game.load_games(), key=lambda g: (g.date, g.game_id, g.bowler.bowler_id)
    )

    # games stored as a Polars DataFrame
    bowler_frame = (
        pl.DataFrame([attrs.asdict(game) for game in all_games])
        .with_columns(pl.col("bowler").struct.field("bowler_id"))
        .drop("bowler")
    )
    return (all_games,)


@app.cell
def _(all_games, attrs, pl):
    scoring_columns = ["Pins", "Points", "Lowest", "Highest"]
    rates_columns = ["Per Game", "Per Frame", "Per Pin"]
    frequency_columns = ["Strikes", "Spares", "Wombats", "Gutters"]

    n_recent_games: int = 50
    col_recent_games: str = f"Recent Games ({n_recent_games:,})"


    bowler_frame = (
        pl.DataFrame([attrs.asdict(game) for game in all_games])
        .with_columns(pl.col("bowler").struct.field("bowler_id"))
        .sort("date", "game_id")
        .drop("bowler")
    )

    frames_data = (
        bowler_frame.with_columns(pl.col("throws").bowling.construct_frames())
        .explode("frames")
        .drop("throws")
        .with_columns(
            pl.col("frames").bowling.is_gutter(),
            pl.col("frames").bowling.is_strike(),
            pl.col("frames").bowling.is_spare(),
            pl.col("frames").bowling.is_wombat(),
        )
    )

    summary_detection_table = (
        frames_data.group_by("bowler_id")
        .agg(
            pl.col("frames").count().alias("Frames"),
            pl.col("is_strike").sum().alias("Strikes"),
            pl.col("is_spare").sum().alias("Spares"),
            pl.col("is_wombat").sum().alias("Wombats"),
            pl.col("is_gutter").sum().alias("Gutters"),
        )
        .sort("Strikes", "Spares", "Wombats", descending=True)
    )

    summary_statistics_table = (
        bowler_frame.with_columns(
            pl.col("throws").bowling.compute_score(),
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
            (pl.col("Points") / pl.col("Games")).round(2).alias("Per Game"),
            (pl.col("Points") / pl.col("Frames")).round(2).alias("Per Frame"),
            (pl.col("Points") / pl.col("Pins")).round(3).alias("Per Pin"),
        )
        .sort("Points", descending=True)
        .select(
            "bowler_id",
            "Games",
            "Frames",
            *scoring_columns,
            *rates_columns,
            *frequency_columns,
        )  # , col_recent_games)
    )
    return frequency_columns, rates_columns, scoring_columns, summary_table


@app.cell
def _(
    all_games,
    frequency_columns,
    rates_columns,
    scoring_columns,
    summary_table,
):
    from great_tables import GT


    scoring_palette = "GnBu"
    rates_pallete = "Purples"
    frequency_palette = "Reds"

    gt_table = (
        GT(summary_table)
        .tab_header(
            title="Bowling Statistics",
            subtitle=f"Overall scoring statistics from {all_games[0].date} to {all_games[-1].date}",
        )
        .tab_stub(rowname_col="bowler_id")
        .tab_spanner(label="Scoring", columns=scoring_columns)
        .tab_spanner(label="Rates", columns=rates_columns)
        .tab_spanner(label="Frequency", columns=frequency_columns)
        # .fmt_nanoplot(col_recent_games, reference_line=200)
        .data_color(
            columns=["Pins"],
            palette=scoring_palette,
        )
        .data_color(
            columns=["Points"],
            palette=scoring_palette,
        )
        .data_color(
            columns=["Lowest", "Highest"],
            palette=scoring_palette,
        )
        .data_color(
            columns=["Per Game"],
            palette=rates_pallete,
        )
        .data_color(
            columns=["Per Frame"],
            palette=rates_pallete,
        )
        .data_color(
            columns=["Per Pin"],
            palette=rates_pallete,
        )
        .data_color(
            columns=["Strikes", "Spares"],
            palette=frequency_palette,
        )
        .data_color(columns=["Wombats"], palette=frequency_palette)
        .data_color(
            columns=["Gutters"],
            palette=frequency_palette,
        )
    )

    gt_table = gt_table.fmt_number(
        columns=["Pins", "Points", "Frames", "Strikes", "Spares", "Wombats"], decimals=0
    )
    gt_table = gt_table.fmt_number(columns=["Per Pin"], decimals=3)
    gt_table
    return


if __name__ == "__main__":
    app.run()
