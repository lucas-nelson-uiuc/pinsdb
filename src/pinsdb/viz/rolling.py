import polars as pl
import seaborn as sns
import matplotlib.pyplot as plt


def plot_rolling_mean(
    data,
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


def plot_rolling_statistic(
    data,
    statistic: str,
    bowler_ids: list[str] | None = None,
    window: int = 10,
) -> None:
    df = data

    if bowler_ids is not None:
        df = df.filter(pl.col("bowler_id").is_in(bowler_ids))

    rolling = (
        df
        .with_columns(
            pl.col(f"is_{statistic}")
            .rolling_mean(window)
            .over("bowler_id")
            .alias("rolling_mean"),
            pl.col(f"is_{statistic}")
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
        y=f"is_{statistic}",
        hue=f"is_{statistic}",
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

    # g.map_dataframe(std_band)

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
    norm = plt.Normalize(pdf[f"is_{statistic}"].min(), pdf[f"is_{statistic}"].max())
    sm = plt.cm.ScalarMappable(norm=norm, cmap="viridis")
    sm.set_array([])

    cbar = g.fig.colorbar(
        sm,
        ax=g.axes,
        fraction=0.035,
        pad=0.02,
    )
    cbar.set_label(statistic.title())

    g.fig.suptitle(
        f"{statistic.title()}: Rolling Mean ± Std (window={window})",
        fontsize=14,
    )

    # Rotate date ticks
    for ax in g.axes.flat:
        ax.tick_params(axis="x", labelrotation=30)

    plt.show()
