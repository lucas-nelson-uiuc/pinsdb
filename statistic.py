import marimo

__generated_with = "0.19.9"
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
    from matplotlib import pyplot as plt
    import seaborn as sns

    # pinsdb module
    from pinsdb.models import Game
    from pinsdb.namespace.expressions import Bowling  # noqa: F401

    return Game, attrs, mo, pl, plt, sns


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
        .with_columns(pl.col("bowler").struct.field("bowler_id"))
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
            (pl.col("Points") / pl.col("Games")).round(2).alias("Points Per Game"),
            (pl.col("Points") / pl.col("Frames"))
            .round(2)
            .alias("Points Per Frame"),
            (pl.col("Points") / pl.col("Pins")).round(3).alias("Points Per Pin"),
            (pl.col("Strikes") / pl.col("Games"))
            .round(2)
            .alias("Strikes Per Game"),
            (pl.col("Spares") / pl.col("Games")).round(2).alias("Spares Per Game"),
            (pl.col("Wombats") / pl.col("Games"))
            .round(2)
            .alias("Wombats Per Game"),
            (pl.col("Gutters") / pl.col("Games"))
            .round(2)
            .alias("Gutters Per Game"),
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
        .fmt_number(columns=["Points Per Pin"], decimals=3)
    )

    gt_table
    return (GT,)


@app.cell(hide_code=True)
def _(BOWLERS: tuple[str], all_games, pl, sns):
    from pinsdb.namespace.compute import score_game, score_pins

    sns.set_theme(style="white", rc={"axes.facecolor": (0, 0, 0, 0)})

    sample_data = pl.DataFrame(
        [
            {
                "game_id": game.game_id,
                "bowler_id": game.bowler.bowler_id,
                "score": score_game(game.throws),
                "pins": score_pins(game.throws),
                "date": game.date,
            }
            for game in all_games
            if game.bowler.bowler_id in BOWLERS
        ]
    )
    return (sample_data,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## **Score Dominance**
    ---
    """)
    return


@app.cell(hide_code=True)
def _(sample_data, sns):
    sns.displot(
        sample_data, x="score", hue="bowler_id", kind="hist", multiple="fill"
    )
    return


@app.cell(hide_code=True)
def _(sample_data, sns):
    sns.displot(sample_data, x="score", hue="bowler_id", stat="count", kind="ecdf")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## **Score Variance**
    ---
    How consistent is each bowler?
    """)
    return


@app.cell(hide_code=True)
def _(GT, pl, sample_data):
    N_SCORES: int = 10

    (
        GT(
            sample_data.select(
                pl.col("date").alias("Date"),
                pl.col("bowler_id").alias("Bowler"),
                pl.col("pins").alias("Pins"),
                pl.col("score").alias("Score"),
            )
            .top_k(by="Score", k=N_SCORES)
            .with_columns(
                pl.col("Score").rank(method="max", descending=True).alias("Rank")
            )
            .select("Rank", "Date", "Bowler", "Pins", "Score")
            .sort(by=("Rank", "Date"), descending=(False, True))
        )
        .data_color(columns="Rank", palette="Greys")
        .data_color(columns=["Pins", "Score"], palette="Purples")
    )
    return (N_SCORES,)


@app.cell(hide_code=True)
def _(GT, N_SCORES: int, pl, sample_data):
    (
        GT(
            sample_data.select(
                pl.col("date").alias("Date"),
                pl.col("bowler_id").alias("Bowler"),
                pl.col("pins").alias("Pins"),
                pl.col("score").alias("Score"),
            )
            .bottom_k(by="Score", k=N_SCORES)
            .with_columns(
                pl.col("Score").rank(method="max", descending=True).alias("Rank")
            )
            .select("Rank", "Date", "Bowler", "Pins", "Score")
            .sort(by=("Rank", "Date"), descending=True)
        )
        .data_color(columns="Rank", palette="Greys")
        .data_color(columns=["Pins", "Score"], palette="Purples")
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## **Pin Sequence**
    ---
    """)
    return


@app.cell(hide_code=True)
def _(frames_data, pl, plt, sns):
    import pandas as pd

    # -------------------------------
    # Build categorized transition data
    # -------------------------------
    data = (
        frames_data.select("bowler_id", "frames", "is_strike", "is_spare")
        .with_columns(
            pl.col("frames").list.first().alias("first_throw"),
            pl.when(pl.col("is_strike"))
            .then(pl.lit("Strike"))
            .when(pl.col("is_spare"))
            .then(pl.lit("Spare"))
            .otherwise(pl.lit("Open"))
            .alias("outcome"),
        )
        .group_by("bowler_id", "first_throw", "outcome")
        .len()
        .rename({"len": "count"})
        .with_columns(
            (
                pl.col("count")
                / pl.col("count").sum().over(["bowler_id", "first_throw"])
            ).alias("prob")
        )
    )

    pdf = data.to_pandas()

    # Order axes explicitly
    pdf["first_throw"] = pd.Categorical(
        pdf["first_throw"], categories=range(11), ordered=True
    )
    pdf["outcome"] = pd.Categorical(
        pdf["outcome"], categories=["Strike", "Spare", "Open"], ordered=True
    )

    # -------------------------------
    # Faceted stacked bar chart (readable version)
    # -------------------------------
    g = sns.FacetGrid(
        pdf,
        col="bowler_id",
        col_wrap=3,
        height=3.5,
        aspect=1.2,
        sharey=True,
    )


    def stacked_bar(data, **kwargs):
        pivot = data.pivot_table(
            index="first_throw",
            columns="outcome",
            values="prob",
            fill_value=0,
        ).sort_index()

        bottom = None
        for outcome in pivot.columns:
            plt.bar(
                pivot.index,
                pivot[outcome],
                bottom=bottom,
                width=0.8,
                label=outcome,
            )
            bottom = pivot[outcome] if bottom is None else bottom + pivot[outcome]

        plt.ylim(0, 1)
        plt.xlabel("Pins on First Throw")
        plt.ylabel("Probability")


    g.map_dataframe(stacked_bar)
    g.set_titles("{col_name}")

    # Shared legend
    handles, labels = plt.gca().get_legend_handles_labels()
    g.fig.legend(
        handles,
        labels,
        title="Frame Outcome",
        bbox_to_anchor=(1.02, 0.5),
        loc="center left",
    )

    plt.tight_layout()
    plt.show()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## **Score Progression**
    ---
    """)
    return


@app.cell(hide_code=True)
def _(bowler_frame):
    from pinsdb.viz import plot_rolling_mean, plot_rolling_statistic


    plot_rolling_mean(
        bowler_frame,
        bowler_ids=("Alek", "Cam", "Jake", "Lucas", "Ryley", "Spencer", "Tristan"),
        window=12,
    )
    return (plot_rolling_statistic,)


@app.cell(hide_code=True)
def _(frames_data, plot_rolling_statistic):
    plot_rolling_statistic(
        frames_data,
        bowler_ids=("Alek", "Cam", "Jake", "Lucas", "Ryley", "Spencer", "Tristan"),
        window=20,
        statistic="strike",
    )
    return


@app.cell(hide_code=True)
def _(frames_data, plot_rolling_statistic):
    plot_rolling_statistic(
        frames_data,
        bowler_ids=("Alek", "Cam", "Jake", "Lucas", "Ryley", "Spencer", "Tristan"),
        window=20,
        statistic="spare",
    )
    return


@app.cell(hide_code=True)
def _(bowler_frame, pl, plt):
    df = (
        bowler_frame.with_columns(pl.col("throws").bowling.compute_score())
        .sort(by=("date", "game_id"))
        .with_columns(
            [
                pl.col("score").cum_max().alias("cum_max"),
                pl.col("score").cum_min().alias("cum_min"),
            ]
        )
        .with_columns(
            [
                (pl.col("cum_max") > pl.col("cum_max").shift(1))
                .fill_null(True)
                .alias("new_max"),
                (pl.col("cum_min") < pl.col("cum_min").shift(1))
                .fill_null(True)
                .alias("new_min"),
            ]
        )
    )

    scores_over_time = df.to_pandas()

    # -----------------------------
    # Plot cumulative max + min together
    # -----------------------------
    plt.figure(figsize=(11, 6))

    plt.plot(scores_over_time["date"], scores_over_time["cum_max"], linewidth=2)
    plt.plot(scores_over_time["date"], scores_over_time["cum_min"], linewidth=2)

    # high-contrast palette
    bowlers = scores_over_time["bowler_id"].unique()
    pltt = plt.get_cmap("tab20").colors
    color_map = {bowler: pltt[i % len(pltt)] for i, bowler in enumerate(bowlers)}

    # -----------------------------
    # Max record points + annotations
    # -----------------------------
    max_breaks = scores_over_time[scores_over_time["new_max"]]

    for bowler, bowler_records in max_breaks.groupby("bowler_id"):
        plt.scatter(
            bowler_records["date"],
            bowler_records["cum_max"],
            s=70,
            marker="^",
            color=color_map[bowler],
            label=bowler,
            zorder=3,
        )

        for i, (_, row) in enumerate(bowler_records.iterrows()):
            plt.annotate(
                f"{bowler} ({row['cum_max']})",
                (row["date"], row["cum_max"]),
                xytext=(6 * (i % 3 - 1), 10 + 4 * (i % 2)),
                textcoords="offset points",
                ha="center",
                fontsize=9,
            )

    # -----------------------------
    # Min record points + annotations
    # -----------------------------
    min_breaks = scores_over_time[scores_over_time["new_min"]]

    for bowler, bowler_records in min_breaks.groupby("bowler_id"):
        plt.scatter(
            bowler_records["date"],
            bowler_records["cum_min"],
            s=70,
            marker="v",
            color=color_map[bowler],
            zorder=3,
        )

        for i, (_, row) in enumerate(bowler_records.iterrows()):
            plt.annotate(
                f"{bowler} ({row['cum_min']})",
                (row["date"], row["cum_min"]),
                xytext=(6 * (i % 3 - 1), -14 - 4 * (i % 2)),
                textcoords="offset points",
                ha="center",
                fontsize=9,
            )

    plt.xlabel("Date")
    plt.ylabel("Score")
    plt.title("Cumulative Maximum and Minimum Scores Over Time")
    plt.legend(title="Bowler")
    plt.tight_layout()
    plt.savefig("figures/cumulative_scores.png")
    plt.show()
    return


if __name__ == "__main__":
    app.run()
