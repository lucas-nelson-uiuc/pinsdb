import pandas as pd
import polars as pl
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np

# ── Theme ────────────────────────────────────────────────────────────────────

OUTCOME_COLORS = {"Strike": "#2ecc71", "Spare": "#3498db", "Open": "#e74c3c"}


def _apply_theme():
    sns.set_theme(style="ticks", font_scale=0.95)
    plt.rcParams.update({"figure.titlesize": 16})
    plt.rcParams.update(
        {
            "figure.titlesize": 16,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.titlesize": 11,
            "axes.titleweight": "bold",
            "axes.labelsize": 10,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "grid.linestyle": "--",
            "legend.framealpha": 0.9,
            "legend.edgecolor": "#cccccc",
            "legend.fontsize": 8,
            "figure.dpi": 130,
        }
    )


_apply_theme()

# ── Helpers ──────────────────────────────────────────────────────────────────


def _subplots_grid(n: int, ncols: int = 3, subplot_size: tuple = (5, 4), **kwargs):
    nrows = -(-n // ncols)
    fig, axes = plt.subplots(
        nrows,
        ncols,
        figsize=(subplot_size[0] * ncols, subplot_size[1] * nrows),
        **kwargs,
    )
    axes = axes.flatten()
    return fig, axes


def _hide_unused(axes, n: int):
    for j in range(n, len(axes)):
        axes[j].set_visible(False)


def _fmt_pct(ax, axis="y"):
    fmt = mtick.PercentFormatter(xmax=100 if axis == "y" else 1)
    if axis == "y":
        ax.yaxis.set_major_formatter(fmt)
    else:
        ax.xaxis.set_major_formatter(fmt)


# ── 1. Strike rate vs spare conversion ───────────────────────────────────────


def plot_strike_vs_spare_conversion(frames_data: pl.DataFrame):
    rates = (
        frames_data.group_by("bowler_id").agg(
            [
                (pl.col("is_strike").mean() * 100).alias("strike_rate"),
                (
                    pl.col("is_spare").sum() / (1 - pl.col("is_strike")).sum() * 100
                ).alias("spare_conversion"),
                pl.len().alias("n_frames"),
            ]
        )
    ).to_pandas()

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.scatterplot(
        data=rates,
        x="spare_conversion",
        y="strike_rate",
        size="n_frames",
        sizes=(50, 400),
        alpha=0.8,
        legend="brief",
        ax=ax,
    )

    for _, row in rates.iterrows():
        ax.annotate(
            row["bowler_id"],
            (row["spare_conversion"], row["strike_rate"]),
            textcoords="offset points",
            xytext=(7, 3),
            fontsize=8,
        )

    ax.axvline(
        rates["spare_conversion"].mean(), color="gray", linewidth=0.8, linestyle="--"
    )
    ax.axhline(rates["strike_rate"].mean(), color="gray", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Spare conversion rate (%)")
    ax.set_ylabel("Strike rate (%)")
    ax.set_title("Strike rate vs spare conversion")
    fig.tight_layout()
    return fig


# ── 2. Outcome rates by frame position ───────────────────────────────────────


def plot_performance_per_frame(frames_data: pl.DataFrame):
    df = (
        frames_data.with_columns(
            (pl.int_range(pl.len()).over(["bowler_id", "game_id"]) % 10 + 1).alias(
                "frame_number"
            )
        )
        .group_by(["bowler_id", "frame_number"])
        .agg(
            [
                (pl.col("is_strike").mean() * 100).alias("Strike %"),
                (pl.col("is_spare").mean() * 100).alias("Spare %"),
                (pl.col("is_open").mean() * 100).alias("Open %"),
            ]
        )
        .sort(["bowler_id", "frame_number"])
    ).to_pandas()

    bowlers = sorted(df["bowler_id"].unique())
    fig, axes = _subplots_grid(len(bowlers), sharex=True, sharey=True)

    for i, bowler in enumerate(bowlers):
        ax = axes[i]
        d = df[df["bowler_id"] == bowler]
        for metric, color in [
            ("Strike %", OUTCOME_COLORS["Strike"]),
            ("Spare %", OUTCOME_COLORS["Spare"]),
            ("Open %", OUTCOME_COLORS["Open"]),
        ]:
            ax.plot(
                d["frame_number"],
                d[metric],
                marker="o",
                markersize=4,
                label=metric,
                color=color,
                linewidth=1.8,
            )
        ax.set_title(bowler)
        ax.set_xticks(range(1, 11))
        ax.set_xlabel("Frame")
        ax.set_ylabel("%")
        ax.legend(fontsize=7)

    _hide_unused(axes, len(bowlers))
    fig.suptitle(
        "Outcome rates by frame position", y=1.01, fontsize=13, fontweight="bold"
    )
    fig.tight_layout()
    return fig


# ── 3. First throw outcome breakdown ─────────────────────────────────────────


def plot_first_throw_outcomes(frames_data: pl.DataFrame):
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
            [
                (
                    pl.col("count")
                    / pl.col("count").sum().over(["bowler_id", "first_throw"])
                ).alias("prob"),
                pl.col("count").sum().over(["bowler_id", "first_throw"]).alias("total"),
            ]
        )
    ).to_pandas()

    data["first_throw"] = pd.Categorical(
        data["first_throw"], categories=range(11), ordered=True
    )
    data["outcome"] = pd.Categorical(
        data["outcome"], categories=["Strike", "Spare", "Open"], ordered=True
    )
    data = data.sort_values(["bowler_id", "first_throw", "outcome"])

    bowlers = sorted(data["bowler_id"].unique())
    fig, axes = _subplots_grid(len(bowlers), sharex=True, sharey=True)

    for i, bowler in enumerate(bowlers):
        ax = axes[i]
        d = data[data["bowler_id"] == bowler]

        pivot = d.pivot_table(
            index="first_throw", columns="outcome", values="prob", fill_value=0
        ).sort_index()
        totals = d.drop_duplicates("first_throw").set_index("first_throw")["total"]

        bottom = None
        for outcome in ["Strike", "Spare", "Open"]:
            if outcome not in pivot.columns:
                continue
            vals = pivot[outcome]
            ax.bar(
                pivot.index,
                vals,
                bottom=bottom,
                width=0.7,
                color=OUTCOME_COLORS[outcome],
                label=outcome,
                alpha=0.9,
            )
            bottom = vals if bottom is None else bottom + vals

        for ft in pivot.index:
            if ft in totals.index:
                ax.text(
                    ft,
                    1.02,
                    str(int(totals[ft])),
                    ha="center",
                    va="bottom",
                    fontsize=7,
                    color="#888888",
                )

        ax.set_xticks(range(11))
        ax.set_xticklabels(
            [str(x) if x < 10 else "★" for x in range(11)], rotation=0, fontsize=8
        )
        ax.set_title(bowler)
        ax.set_xlabel("Pins on first throw")
        ax.set_ylabel("Probability")
        ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1))
        ax.set_ylim(0, 1.12)

    _hide_unused(axes, len(bowlers))
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=OUTCOME_COLORS[o], alpha=0.9)
        for o in ["Strike", "Spare", "Open"]
    ]
    fig.legend(
        handles,
        ["Strike", "Spare", "Open"],
        title="Outcome",
        loc="lower right",
        ncol=3,
        fontsize=9,
    )
    fig.suptitle("Frame outcome by first throw", y=1.01, fontsize=13, fontweight="bold")
    fig.tight_layout()
    return fig


# ── 4. Frame outcome composition ─────────────────────────────────────────────


def plot_frame_outcome(frames_data: pl.DataFrame):
    stacked = (
        frames_data.group_by("bowler_id")
        .agg(
            [
                pl.col("is_strike").cast(pl.Int64).sum().alias("Strike"),
                pl.col("is_spare").cast(pl.Int64).sum().alias("Spare"),
                pl.col("is_open").cast(pl.Int64).sum().alias("Open"),
            ]
        )
        .sort("bowler_id")
        .to_pandas()
        .set_index("bowler_id")
    )
    stacked_pct = stacked.div(stacked.sum(axis=1), axis=0) * 100

    fig, ax = plt.subplots(figsize=(max(8, len(stacked) * 0.8), 5))
    bottom = np.zeros(len(stacked_pct))
    for col in ["Strike", "Spare", "Open"]:
        ax.bar(
            stacked_pct.index,
            stacked_pct[col],
            bottom=bottom,
            color=OUTCOME_COLORS[col],
            label=col,
            alpha=0.9,
            width=0.6,
        )
        bottom += stacked_pct[col].values

    ax.set_ylabel("% of frames")
    ax.set_xlabel("Bowler")
    ax.set_title("Frame outcome composition by bowler", fontsize=13, fontweight="bold")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_xticklabels(stacked_pct.index, rotation=45, ha="right")
    ax.legend(loc="upper right")
    fig.tight_layout()
    return fig


# ── 5. Score distribution ─────────────────────────────────────────────────────


def plot_score_distribution(bowler_frame: pl.DataFrame):
    pdf = bowler_frame.select("bowler_id", "score").to_pandas()
    pdf = pdf.sort_values("bowler_id")

    fig, ax = plt.subplots(figsize=(max(8, len(pdf["bowler_id"].unique()) * 0.8), 5))
    sns.boxplot(
        data=pdf,
        x="bowler_id",
        y="score",
        width=0.5,
        color="steelblue",
        fliersize=0,
        ax=ax,
    )
    sns.stripplot(
        data=pdf,
        x="bowler_id",
        y="score",
        color="black",
        alpha=0.25,
        jitter=True,
        size=3,
        ax=ax,
    )

    ax.set_title("Score distribution by bowler", fontsize=13, fontweight="bold")
    ax.set_xlabel("Bowler")
    ax.set_ylabel("Score")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right")
    fig.tight_layout()
    return fig


# ── 6. Personal best progression ─────────────────────────────────────────────


def plot_personal_bests(bowler_frame: pl.DataFrame, rolling_window: int = 10):
    df = (
        bowler_frame.sort(["bowler_id", "date", "game_id"])
        .with_columns(pl.col("score").cum_max().over("bowler_id").alias("cum_max"))
        .with_columns(
            (pl.col("cum_max") > pl.col("cum_max").shift(1).over("bowler_id"))
            .fill_null(True)
            .alias("new_max")
        )
        .with_columns(
            pl.col("score")
            .rolling_mean(window_size=rolling_window)
            .over("bowler_id")
            .alias("rolling_mean")
        )
    ).to_pandas()

    bowlers = sorted(df["bowler_id"].unique())
    cmap = plt.get_cmap("viridis")
    fig, axes = _subplots_grid(len(bowlers), sharex=False, sharey=True)

    for i, bowler in enumerate(bowlers):
        ax = axes[i]
        d = df[df["bowler_id"] == bowler].copy()
        pbs = d[d["new_max"]]
        rm = d["rolling_mean"]
        rm_norm = (rm - rm.min()) / (rm.max() - rm.min())

        ax.scatter(d["date"], d["score"], color="gray", alpha=0.25, s=15, zorder=1)
        ax.step(
            d["date"],
            d["cum_max"],
            where="post",
            linewidth=2,
            color="steelblue",
            zorder=2,
        )

        for j in range(len(d) - 1):
            a, b = d.iloc[j], d.iloc[j + 1]
            if pd.isna(a["rolling_mean"]) or pd.isna(b["rolling_mean"]):
                continue
            ax.plot(
                [a["date"], b["date"]],
                [a["rolling_mean"], b["rolling_mean"]],
                color=cmap((rm_norm.iloc[j] + rm_norm.iloc[j + 1]) / 2),
                linewidth=2.5,
                zorder=3,
            )

        ax.scatter(
            pbs["date"],
            pbs["cum_max"],
            s=60,
            marker="*",
            color="gold",
            edgecolors="black",
            linewidths=0.5,
            zorder=4,
        )
        for _, row in pbs.iterrows():
            ax.annotate(
                str(int(row["cum_max"])),
                (row["date"], row["cum_max"]),
                textcoords="offset points",
                xytext=(0, 8),
                ha="center",
                fontsize=8,
            )

        ax.set_title(bowler)
        ax.set_xlabel("Date")
        ax.set_ylabel("Score")
        ax.tick_params(axis="x", rotation=45)

    _hide_unused(axes, len(bowlers))

    from matplotlib.lines import Line2D

    fig.legend(
        handles=[
            Line2D([0], [0], color="steelblue", linewidth=2, label="Personal best"),
            Line2D(
                [0],
                [0],
                color="gray",
                alpha=0.4,
                linewidth=0,
                marker="o",
                markersize=4,
                label="Game score",
            ),
            Line2D(
                [0],
                [0],
                color="gold",
                linewidth=0,
                marker="*",
                markersize=8,
                markeredgecolor="black",
                label="New PB",
            ),
            Line2D(
                [0],
                [0],
                color=cmap(0.5),
                linewidth=2.5,
                label=f"{rolling_window}-game rolling mean",
            ),
        ],
        loc="lower center",
        ncol=4,
        fontsize=8,
        bbox_to_anchor=(0.5, -0.02),
    )

    fig.suptitle("Personal best progression", y=1.01, fontsize=13, fontweight="bold")
    fig.tight_layout()
    return fig


# ── 7. Top / bottom scores ────────────────────────────────────────────────────


def plot_top_bottom_scores(bowler_frame: pl.DataFrame, n: int = 5):
    df = bowler_frame.sort("score", descending=True).to_pandas()
    top = df.head(n).sort_values("score")
    bottom = df.tail(n).sort_values("score", ascending=False)

    fig, axes = plt.subplots(1, 2, figsize=(12, max(5, n * 0.5)))

    for ax, data, color, title in zip(
        axes,
        [top, bottom],
        ["#2ecc71", "#e74c3c"],
        [f"Top {n} scores", f"Bottom {n} scores"],
    ):
        ax.barh(range(n), data["score"], color=color, alpha=0.8)
        ax.set_xlabel("Score")
        ax.set_title(title, fontweight="bold")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        if n <= 20:
            labels = data.apply(
                lambda r: f"{r['bowler_id']}  {r['date'].strftime('%b %d %Y')}", axis=1
            )
            ax.set_yticks(range(n))
            ax.set_yticklabels(labels, fontsize=9)
            for j, (_, row) in enumerate(data.iterrows()):
                ax.text(
                    row["score"] + 0.5,
                    j,
                    str(int(row["score"])),
                    va="center",
                    fontsize=9,
                )
        else:
            ax.set_yticks([])
            for j, (_, row) in enumerate(data.iterrows()):
                ax.text(
                    1,
                    j,
                    f"{row['bowler_id']}  {row['date'].strftime('%b %d')}",
                    va="center",
                    fontsize=7,
                    transform=ax.get_yaxis_transform(),
                )
                ax.text(
                    row["score"] + 0.5,
                    j,
                    str(int(row["score"])),
                    va="center",
                    fontsize=7,
                )

    fig.suptitle(f"Top and bottom {n} scores all time", fontsize=13, fontweight="bold")
    fig.tight_layout()
    return fig
