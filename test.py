import marimo

__generated_with = "0.13.15"
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
    return Game, attrs, pl


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
        .sort("date", "game_id")
        .drop("bowler")
    )
    return (bowler_frame,)


@app.cell
def _(bowler_frame, pl):
    from pinsdb.namespace.expressions import Bowling

    win_loss = (
        bowler_frame.with_columns(pl.col("throws").bowling.compute_score())
        .group_by("date", "game_id")
        .agg(
            pl.col("score").max(),
            pl.col("bowler_id").bowling.get_highest_bowler(),
            pl.col("bowler_id").bowling.get_lowest_bowler(),
        )
        .sort("date", "game_id")
    )
    wins = (
        win_loss.group_by(pl.col("winner").alias("bowler_id"))
        .agg(
            pl.len().alias("Wins"),
            pl.col("score").min().alias("Lowest Win"),
            pl.col("date").bottom_k_by(by=pl.col("score"), k=1).get(index=0).alias("Date of Lowest Win"),
            pl.col("score").max().alias("Highest Win"),
            pl.col("date").top_k_by(by=pl.col("score"), k=1).get(index=0).alias("Date of Highest Win"),
        )
        .sort("Wins", descending=True)
    )
    return (wins,)


@app.cell
def _(wins):
    wins
    return


if __name__ == "__main__":
    app.run()
