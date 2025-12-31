import marimo

__generated_with = "0.18.4"
app = marimo.App(width="full")


@app.cell
def _():
    # marimo notebook

    import datetime

    # object handling
    import attrs

    # data handling
    import pandas as pd
    import polars as pl

    # plotting
    from matplotlib import pyplot as plt
    import seaborn as sns
    from great_tables import GT

    # pinsdb module
    from pinsdb.models import Game
    from pinsdb.namespace.expressions import Bowling  # noqa: F401

    return GT, Game, attrs, datetime, pd, pl, plt, sns


@app.cell
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
        Game.load_games(), key=lambda g: (g.date, g.game_id, g.bowler.bowler_id)
    )

    # games stored as a Polars DataFrame
    bowler_frame = (
        pl.DataFrame([attrs.asdict(game) for game in all_games])
        .with_columns(pl.col("bowler").struct.field("bowler_id"))
        .sort("date", "game_id")
        .drop("bowler")
        .filter(pl.col("bowler_id").is_in(BOWLERS))
    )
    return (bowler_frame,)


@app.cell
def _(bowler_frame, pl):
    results = (
        bowler_frame.with_columns(pl.col("throws").bowling.compute_score())
        .group_by("date", "game_id")
        .agg(
            pl.col("bowler_id").bowling.get_highest_bowler().alias("winner"),
            pl.col("bowler_id").bowling.get_lowest_bowler().alias("loser"),
        )
        .unpivot(
            index=("date", "game_id"),
            on=("winner", "loser"),
            variable_name="outcome",
            value_name="bowler_id",
        )
        .sort(by=("date", "game_id"))
        .join(bowler_frame, on=("date", "game_id", "bowler_id"), how="right")
        .with_columns(pl.col("throws").bowling.compute_score())
    )
    return (results,)


@app.cell
def _(datetime, pl, results):
    summary = (
        results.with_columns(
            [
                (pl.col("outcome") == "winner").cast(pl.Int8).alias("win"),
                (pl.col("outcome") == "loser").cast(pl.Int8).alias("loss"),
            ]
        )
        .group_by("bowler_id")
        .agg(
            [
                pl.len().alias("Games"),
                pl.sum("win").alias("Wins"),
                pl.sum("loss").alias("Losses"),
                pl.col("score").filter(pl.col("win") == 1).max().alias("Highest Win"),
                pl.col("score").filter(pl.col("win") == 1).mean().alias("Average Win"),
                pl.col("score").filter(pl.col("win") == 1).min().alias("Lowest Win"),
                pl.col("score").filter(pl.col("loss") == 1).max().alias("Highest Loss"),
                pl.col("score")
                .filter(pl.col("loss") == 1)
                .mean()
                .alias("Average Loss"),
                pl.col("score").filter(pl.col("loss") == 1).min().alias("Lowest Loss"),
                pl.col("date").filter(pl.col("win") == 1).max().alias("Last Win"),
                pl.col("date").filter(pl.col("loss") == 1).max().alias("Last Loss"),
            ]
        )
        .with_columns(
            [
                (pl.col("Wins") / pl.col("Games")).alias("Win Rate"),
                (pl.col("Losses") / pl.col("Games")).alias("Loss Rate"),
            ]
        )
        .sort("Wins", descending=True)
        .fill_null(value=datetime.datetime.today().date())
    )
    return (summary,)


@app.cell
def _(GT, results, summary):
    # Define column groups
    scoring_columns = ["Games", "Wins", "Losses"]
    maximum_columns = ["Highest Win", "Highest Loss"]
    average_columns = [
        "Average Win",
        "Average Loss",
    ]
    minimum_columns = [
        "Lowest Win",
        "Lowest Loss",
    ]
    rates_columns = ["Win Rate", "Loss Rate"]
    date_columns = ["Last Win", "Last Loss"]

    # Color palettes
    scoring_palette = "GnBu"
    minmax_palette = "Blues"
    rates_palette = "Purples"

    # Build GT table
    gt_table = (
        GT(summary)
        .tab_header(
            title="Bowling Statistics",
            subtitle=f"From {results['date'].min()} to {results['date'].max()}",
        )
        .tab_stub(rowname_col="bowler_id")
        .tab_spanner(label="Scoring", columns=scoring_columns)
        .tab_spanner(label="Maximums", columns=maximum_columns)
        .tab_spanner(label="Averages", columns=average_columns)
        .tab_spanner(label="Minimums", columns=minimum_columns)
        .tab_spanner(label="Rates", columns=rates_columns)
        .tab_spanner(label="Dates", columns=date_columns)
        .data_color(columns=scoring_columns, palette=scoring_palette)
        .data_color(
            columns=maximum_columns + average_columns + minimum_columns,
            palette=minmax_palette,
        )
        .data_color(columns=rates_columns, palette=rates_palette)
        .fmt_number(columns=scoring_columns, decimals=0)
        .fmt_number(columns=average_columns, decimals=2)
        .fmt_percent(columns=rates_columns, decimals=1)
    )

    gt_table
    return


@app.cell
def _(pd, pl, plt, results, sns):
    from statsmodels.nonparametric.smoothers_lowess import lowess

    winning_scores = (
        results.filter(pl.col("outcome") == "winner")
        .select(["date", "bowler_id", "throws"])
        .with_columns(pl.col("throws").bowling.compute_score().alias("score"))
        .sort("date")
        .to_pandas()
    )

    # Normalize dates for LOWESS
    winning_scores["date_num"] = (
        winning_scores["date"] - winning_scores["date"].min()
    ).dt.days

    # LOWESS smoothing
    smoothed = lowess(
        endog=winning_scores["score"], exog=winning_scores["date_num"], frac=0.1
    )

    plt.figure(figsize=(14, 6))
    sns.scatterplot(
        data=winning_scores,
        x="date",
        y="score",
        hue="bowler_id",
        palette="tab10",
        s=60,
    )

    plt.plot(
        winning_scores["date"].min() + pd.to_timedelta(smoothed[:, 0], unit="D"),
        smoothed[:, 1],
        color="black",
        linewidth=2.5,
        label="Smoothed Avg",
    )

    plt.xlabel("Date")
    plt.ylabel("Winning Score")
    plt.title("Winning Scores Over Time with Smoothed Average")
    plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.tight_layout()
    plt.show()
    return (lowess,)


@app.cell
def _(lowess, pd, pl, plt, results, sns):
    losing_scores = (
        results.filter(pl.col("outcome") == "loser")
        .select(["date", "bowler_id", "throws"])
        .with_columns(pl.col("throws").bowling.compute_score().alias("score"))
        .sort("date")
        .to_pandas()
    )

    # Normalize dates for LOWESS
    losing_scores["date_num"] = (
        losing_scores["date"] - losing_scores["date"].min()
    ).dt.days

    # LOWESS smoothing
    smoothed_loser = lowess(
        endog=losing_scores["score"], exog=losing_scores["date_num"], frac=0.1
    )

    plt.figure(figsize=(14, 6))
    sns.scatterplot(
        data=losing_scores,
        x="date",
        y="score",
        hue="bowler_id",
        palette="tab10",
        s=60,
    )

    plt.plot(
        losing_scores["date"].min() + pd.to_timedelta(smoothed_loser[:, 0], unit="D"),
        smoothed_loser[:, 1],
        color="black",
        linewidth=2.5,
        label="Smoothed Avg",
    )

    plt.xlabel("Date")
    plt.ylabel("Losing Score")
    plt.title("Losing Scores Over Time with Smoothed Average")
    plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.tight_layout()
    plt.show()
    return


if __name__ == "__main__":
    app.run()
