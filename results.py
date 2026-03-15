import marimo

__generated_with = "0.18.4"
app = marimo.App(width="full")


@app.cell(hide_code=True)
def _():
    # marimo notebook

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

    return GT, Game, attrs, pd, pl, plt, sns


@app.cell(hide_code=True)
def _(Game, attrs, pl):
    # define bowlers to include in `bowler_frame`
    BOWLERS: tuple[str] = (
        "Cam",
        "Ryley",
        "Spencer",
        "Lucas",
        # "Alek",
        # "Jake",
        # "Munson",
        # "Tristan",
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
    ranks = (
        bowler_frame.with_columns(pl.col("throws").bowling.compute_score())
        .group_by("date", "game_id")
        .agg(
            pl.col("bowler_id").bowling.get_highest_bowler().alias("winner"),
            pl.col("bowler_id").bowling.get_lowest_bowler().alias("loser"),
            pl.col("score").rank(method="ordinal", descending=True).alias("rank"),
            pl.col("score"),
            pl.col("bowler_id"),
        )
        .explode("rank", "score", "bowler_id")
        .group_by("bowler_id")
        .agg(
            pl.len().alias("Games"),
            (pl.col("rank") == 1).sum().alias("First"),
            (pl.col("rank") == 2).sum().alias("Second"),
            (pl.col("rank") == 3).sum().alias("Third"),
            (pl.col("loser") == pl.col("bowler_id")).sum().alias("Losses"),
            pl.col("date").filter(pl.col("rank") == 1).max().alias("Last Win"),
            pl.col("date")
            .filter(pl.col("loser") == pl.col("bowler_id"))
            .max()
            .alias("Last Loss"),
            pl.col("score").filter(pl.col("rank") == 1).max().alias("Highest Win"),
            pl.col("score").filter(pl.col("rank") == 2).max().alias("Highest Second"),
            pl.col("score").filter(pl.col("rank") == 3).max().alias("Highest Third"),
            pl.col("score")
            .filter(pl.col("loser") == pl.col("bowler_id"))
            .max()
            .alias("Highest Loss"),
        )
        .with_columns(
            (pl.col("First") / pl.col("Games")).alias("Win Rate"),
            (
                (pl.col("First") + pl.col("Second") + pl.col("Third")) / pl.col("Games")
            ).alias("Podium Rate"),
            (pl.col("Losses") / pl.col("Games")).alias("Loss Rate"),
        )
        .sort("First", "Second", "Third", descending=True)
    )
    return (ranks,)


@app.cell(hide_code=True)
def _(GT, ranks, results):
    # Define column groups
    podium_columns = ["First", "Second", "Third", "Losses"]
    scoring_columns = [
        "Highest Win",
        "Highest Second",
        "Highest Third",
        "Highest Loss",
    ]
    rates_columns = ["Win Rate", "Podium Rate", "Loss Rate"]
    date_columns = ["Last Win", "Last Loss"]

    # Color palettes
    scoring_palette = "GnBu"
    rates_palette = "Purples"

    # Build GT table
    gt_table = (
        GT(ranks)
        .tab_header(
            title="Bowling Results",
            subtitle=f"From {results['date'].min().strftime('%B %d, %Y')} to {results['date'].max().strftime('%B %d, %Y')}",
        )
        .tab_stub(rowname_col="bowler_id")
        .tab_spanner(label="Podium", columns=podium_columns)
        .tab_spanner(label="Scoring", columns=scoring_columns)
        .tab_spanner(label="Rates", columns=rates_columns)
        .tab_spanner(label="Dates", columns=date_columns)
        .data_color(columns=scoring_columns, palette=scoring_palette)
        .data_color(columns="First", palette="PuBu")
        .data_color(columns="Second", palette="Blues")
        .data_color(columns="Third", palette="BuGn")
        .data_color(columns="Losses", palette="OrRd")
        .data_color(columns=rates_columns, palette=rates_palette)
        .fmt_number(columns=scoring_columns, decimals=0)
        .fmt_percent(columns=rates_columns, decimals=1)
    )

    gt_table
    return


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
