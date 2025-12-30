import marimo

__generated_with = "0.18.4"
app = marimo.App(width="full")


@app.cell
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

    return Game, attrs, mo, pl, plt, sns


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Load Games
    ---
    This will load all games from the files in `DATA_DIRECTORY` - until someone else uses this project this will be the local `.data/` folder.
    """)
    return


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


@app.cell
def _(bowler_frame, pl):
    scoring_columns = ["Pins", "Points", "Lowest", "Highest"]
    rates_columns = ["Per Game", "Per Frame", "Per Pin"]
    frequency_columns = ["Strikes", "Spares", "Wombats", "Gutters"]

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
    return (
        frames_data,
        frequency_columns,
        rates_columns,
        scoring_columns,
        summary_table,
    )


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
            subtitle=f"Range from {all_games[0].date.strftime('%B %d, %Y')} to {all_games[-1].date.strftime('%B %d, %Y')} | Sorted by Total Points",
        )
        .tab_stub(rowname_col="bowler_id")
        .tab_spanner(label="Scoring", columns=scoring_columns)
        .tab_spanner(label="Rates", columns=rates_columns)
        .tab_spanner(label="Frequency", columns=frequency_columns)
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
        columns=["Pins", "Points", "Frames", "Strikes", "Spares", "Wombats"],
        decimals=0,
    )
    gt_table = gt_table.fmt_number(columns=["Per Pin"], decimals=3)
    gt_table
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Plot Visuals
    ---
    """)
    return


@app.cell
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
    #### Score Dominance
    ---
    Which bowlers share different scores?
    """)
    return


@app.cell
def _(sample_data, sns):
    sns.displot(sample_data, x="score", hue="bowler_id", kind="kde", multiple="fill")
    return


@app.cell
def _(sample_data, sns):
    sns.displot(sample_data, x="score", hue="bowler_id", stat="count", kind="ecdf")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Score Variance
    ---
    How consistent is each bowler?
    """)
    return


@app.cell
def _(BOWLERS: tuple[str], sample_data, sns):
    palette = sns.color_palette("magma", n_colors=len(BOWLERS))
    sns.set_theme(style="darkgrid", palette=palette)

    sns.violinplot(
        sample_data, x="score", y="bowler_id", hue="bowler_id", palette=palette
    )
    sns.stripplot(sample_data, x="score", y="bowler_id", color=".3", jitter=0)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Pin Sequence
    ---
    How well do bowlers do on their first throw? second throw?
    """)
    return


@app.cell
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
    #### Score Progression
    ---
    How well has each bowler done over time?
    """)
    return


@app.cell
def _(bowler_frame, pl, plt, sns):
    def plot_rolling_mean(
        data: pl.DataFrame,
        bowler_ids: list[str] | None = None,
        window: int = 10,
    ) -> None:
        df = data

        if bowler_ids is not None:
            df = df.filter(pl.col("bowler_id").is_in(bowler_ids))

        rolling = (
            df.with_columns(pl.col("throws").bowling.compute_score())
            .with_columns(
                pl.col("score")
                .rolling_mean(window)
                .over("bowler_id")
                .alias("rolling_mean"),
                pl.col("score")
                .rolling_std(window)
                .over("bowler_id")
                .alias("rolling_std"),
            )
            .sort(["bowler_id", "date"])
        )

        pdf = rolling.to_pandas()

        g = sns.FacetGrid(
            pdf,
            col="bowler_id",
            col_wrap=3,
            height=3,
            aspect=1.2,
            sharex=True,
            sharey=True,
            despine=True,
        )

        # Scatter colored by score
        g.map_dataframe(
            sns.scatterplot,
            x="date",
            y="score",
            hue="score",
            palette="viridis",
            alpha=0.6,
            s=30,
            legend=False,
        )

        # Rolling mean line
        g.map_dataframe(
            sns.lineplot,
            x="date",
            y="rolling_mean",
            color="black",
            linewidth=1.8,
        )

        # Rolling std band with dashed borders
        def std_band(data, **kwargs):
            plt.fill_between(
                data["date"],
                data["rolling_mean"] - data["rolling_std"],
                data["rolling_mean"] + data["rolling_std"],
                color="black",
                alpha=0.15,
                linewidth=0,
            )
            # dashed upper/lower lines
            plt.plot(
                data["date"],
                data["rolling_mean"] + data["rolling_std"],
                color="black",
                linestyle="--",
                linewidth=1,
            )
            plt.plot(
                data["date"],
                data["rolling_mean"] - data["rolling_std"],
                color="black",
                linestyle="--",
                linewidth=1,
            )

        g.map_dataframe(std_band)

        g.set_titles("{col_name}")
        g.set_axis_labels("Date", "Score")

        # Layout control
        g.fig.set_size_inches(12, 8)
        g.fig.subplots_adjust(
            right=0.88,
            top=0.90,
            wspace=0.15,
            hspace=0.25,
        )

        # Shared colorbar
        norm = plt.Normalize(pdf["score"].min(), pdf["score"].max())
        sm = plt.cm.ScalarMappable(norm=norm, cmap="viridis")
        sm.set_array([])

        cbar = g.fig.colorbar(
            sm,
            ax=g.axes,
            fraction=0.035,
            pad=0.02,
        )
        cbar.set_label("Score")

        g.fig.suptitle(
            f"Rolling Mean ± Std (window={window})",
            fontsize=14,
        )

        # Rotate date ticks
        for ax in g.axes.flat:
            ax.tick_params(axis="x", labelrotation=30)

        plt.show()

    plot_rolling_mean(
        bowler_frame,
        bowler_ids=("Alek", "Cam", "Jake", "Lucas", "Ryley", "Spencer", "Tristan"),
        window=12,
    )
    return


if __name__ == "__main__":
    app.run()
