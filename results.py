import marimo

__generated_with = "0.19.9"
app = marimo.App(width="full")


@app.cell(hide_code=True)
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


@app.cell(hide_code=True)
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


@app.cell(hide_code=True)
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
                pl.col("score")
                .filter(pl.col("win") == 1)
                .max()
                .alias("Highest Win"),
                pl.col("score")
                .filter(pl.col("win") == 1)
                .mean()
                .alias("Average Win"),
                pl.col("score")
                .filter(pl.col("win") == 1)
                .min()
                .alias("Lowest Win"),
                pl.col("score")
                .filter(pl.col("loss") == 1)
                .max()
                .alias("Highest Loss"),
                pl.col("score")
                .filter(pl.col("loss") == 1)
                .mean()
                .alias("Average Loss"),
                pl.col("score")
                .filter(pl.col("loss") == 1)
                .min()
                .alias("Lowest Loss"),
                pl.col("date").filter(pl.col("win") == 1).max().alias("Last Win"),
                pl.col("date")
                .filter(pl.col("loss") == 1)
                .max()
                .alias("Last Loss"),
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


@app.cell(hide_code=True)
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
            subtitle=f"From {results['date'].min().strftime('%B %d, %Y')} to {results['date'].max().strftime('%B %d, %Y')}",
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


@app.cell(hide_code=True)
def _(pd, pl, plt, results, sns):
    from statsmodels.nonparametric.smoothers_lowess import lowess

    winning_scores = (
        results.filter(pl.col("outcome") == "winner")
        .select(["date", "bowler_id", "throws"])
        .with_columns(pl.col("throws").bowling.compute_score().alias("score"))
        .sort("date")
        .to_pandas()
    )

    winning_scores["date_num"] = (
        winning_scores["date"] - winning_scores["date"].min()
    ).dt.days

    # Build a color map keyed to bowler so scatter + lines share colors
    bowlers = winning_scores["bowler_id"].unique()
    palette = dict(zip(bowlers, sns.color_palette("tab10", len(bowlers))))

    fig, ax = plt.subplots(figsize=(14, 6))

    # Scatter (same as before)
    sns.scatterplot(
        data=winning_scores,
        x="date",
        y="score",
        hue="bowler_id",
        palette=palette,
        s=60,
        ax=ax,
    )

    # Per-bowler LOWESS — only drawn when the bowler has enough points
    min_date = winning_scores["date"].min()

    for bowler, color in palette.items():
        subset = winning_scores[winning_scores["bowler_id"] == bowler]
        if len(subset) < 5:  # skip bowlers with too few games to smooth
            continue
        smoothed_b = lowess(
            endog=subset["score"],
            exog=subset["date_num"],
            frac=0.3,  # wider frac per-bowler since subsets are smaller
            it=1,
        )
        ax.plot(
            min_date + pd.to_timedelta(smoothed_b[:, 0], unit="D"),
            smoothed_b[:, 1],
            color=color,
            linewidth=2,
            linestyle="--",
            alpha=0.7,
        )

    # Overall LOWESS on top
    smoothed_all = lowess(
        endog=winning_scores["score"],
        exog=winning_scores["date_num"],
        frac=0.1,
    )
    ax.plot(
        min_date + pd.to_timedelta(smoothed_all[:, 0], unit="D"),
        smoothed_all[:, 1],
        color="black",
        linewidth=2.5,
        label="Smoothed Avg (all)",
    )

    ax.set_xlabel("Date")
    ax.set_ylabel("Winning Score")
    ax.set_title("Winning Scores Over Time with Smoothed Averages")

    # Rebuild legend: scatter already added bowler handles; append the overall line
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles, labels, bbox_to_anchor=(1.05, 1), loc="upper left")

    plt.tight_layout()
    plt.show()
    return


@app.cell(hide_code=True)
def _(pd, pl, plt, results, sns):
    def _():
        from statsmodels.nonparametric.smoothers_lowess import lowess

        losing_scores = (
            results.filter(pl.col("outcome") == "loser")
            .select(["date", "bowler_id", "throws"])
            .with_columns(pl.col("throws").bowling.compute_score().alias("score"))
            .sort("date")
            .to_pandas()
        )

        losing_scores["date_num"] = (
            losing_scores["date"] - losing_scores["date"].min()
        ).dt.days

        bowlers = losing_scores["bowler_id"].unique()
        palette = dict(zip(bowlers, sns.color_palette("tab10", len(bowlers))))

        FRAC_B = 0.3
        FRAC_ALL = 0.1
        min_date = losing_scores["date"].min()

        fig, ax = plt.subplots(figsize=(14, 6))

        sns.scatterplot(
            data=losing_scores,
            x="date",
            y="score",
            hue="bowler_id",
            palette=palette,
            s=60,
            ax=ax,
        )

        for bowler, color in palette.items():
            subset = losing_scores[losing_scores["bowler_id"] == bowler]
            if len(subset) < 5:
                continue
            smoothed_b = lowess(
                endog=subset["score"],
                exog=subset["date_num"],
                frac=FRAC_B,
                it=1,
            )
            ax.plot(
                min_date + pd.to_timedelta(smoothed_b[:, 0], unit="D"),
                smoothed_b[:, 1],
                color=color,
                linewidth=1.5,
                linestyle="--",
                alpha=0.7,
            )

        smoothed_all = lowess(
            endog=losing_scores["score"],
            exog=losing_scores["date_num"],
            frac=FRAC_ALL,
        )
        ax.plot(
            min_date + pd.to_timedelta(smoothed_all[:, 0], unit="D"),
            smoothed_all[:, 1],
            color="black",
            linewidth=2.5,
            label="Smoothed Avg (all)",
        )

        ax.set_xlabel("Date")
        ax.set_ylabel("Losing Score")
        ax.set_title("Losing Scores Over Time with Smoothed Averages")

        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles, labels, bbox_to_anchor=(1.05, 1), loc="upper left")

        plt.tight_layout()
        return plt.show()


    _()
    return


if __name__ == "__main__":
    app.run()
