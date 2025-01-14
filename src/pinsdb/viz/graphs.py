from pinsdb.bowl.models import Game

import seaborn as sns

sns.set_theme(style="white", rc={"axes.facecolor": (0, 0, 0, 0)})


def convert_games(all_games: list[Game]) -> list[dict]:
    return [
        {
            "game_id": game.game_id,
            "bowler_id": game.bowler.bowler_id,
            "score": game.score_game(),
            "pins": game.score_pins(),
            "date": game.date,
        }
        for game in all_games
    ]
