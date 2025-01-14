import pandas as pd

import seaborn as sns
from matplotlib.axes import Axes

from pinsdb.bowl.models import Bowler, Game


def score_dominance(data: dict) -> Axes:
    g = sns.displot(data, x="score", hue="bowler_id", kind="kde", multiple="fill")
    return g


def pins_matrix(games: list[Game], bowler: Bowler) -> Axes:
    throws_data = pd.DataFrame(
        [
            {
                "game_id": game.game_id,
                "bowler_id": game.bowler.bowler_id,
                "frames": game.construct_frames()[:9],
            }
            for game in games
            if game.bowler.bowler_id == bowler.bowler_id
        ]
    )
    throws_data = throws_data.explode("frames")
    throws_data[["first_throw", "second_throw"]] = [
        throw + [0] if throw == [10] else throw[:2]
        for throw in throws_data["frames"].to_list()
    ]

    throws_crosstab = pd.crosstab(
        throws_data["second_throw"], throws_data["first_throw"]
    )
    g = sns.heatmap(throws_crosstab)
    return g
