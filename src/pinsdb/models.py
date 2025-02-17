import pathlib
from attrs import define, field
import datetime
from loguru import logger
import itertools
from pinsdb.bowlers import Bowler, REGISTERED_BOWLERS

from pinsdb.db import DATABASE_SOURCE
from pinsdb.constants import TOTAL_FRAME_PINS


def extract_components(
    source: str, database_source: str = DATABASE_SOURCE
) -> dict[str, str]:
    def extract_date_component(date_component: str) -> datetime.date:
        date_component = (
            f"{date_component[:4]}-{date_component[4:6]}-{date_component[6:]}"
        )
        return datetime.date.fromisoformat(date_component)

    def extract_game_component(game_component: str) -> str:
        return "".join(s for s in game_component if s.isdigit())

    if database_source:
        relative_source = pathlib.Path(source).relative_to(database_source)

    if not database_source:
        database_source = source
        relative_source = pathlib.Path(source).relative_to("pinsdb/.data")

    date_component, game_component = relative_source.parts
    return {
        "date": extract_date_component(date_component),
        "game_id": extract_game_component(game_component),
    }


@define
class Frame:
    throws: tuple[int]

    def is_strike(self):
        """Detect if frame is a strike."""
        if not self.throws:
            return False
        return self.throws[0] == TOTAL_FRAME_PINS

    def is_wombat(self):
        """Detect if frame is a wombat."""
        if not self.throws:
            return False
        return self.throws[-1] == TOTAL_FRAME_PINS

    def is_spare(self):
        """Detect if frame is a spare."""
        if not self.throws:
            return False
        return sum(self.throws) == TOTAL_FRAME_PINS

    def detect_bonus(self) -> list[int]:
        if self.is_strike():
            bonus = 2
        elif self.is_spare():
            bonus = 1
        else:
            bonus = 0
        return bonus


@define
class Game:
    """Base model representing a game of bowling."""

    game_id: str
    bowler: Bowler
    throws: list[Frame]
    date: datetime.date

    @classmethod
    def load_game(cls, source: str, *bowler_id: str) -> list["Game"]:
        """Load game from source."""
        bowlers = dict()
        try:
            with open(source, "r") as fp:
                for line in fp.readlines():
                    bowler, *throws = line.strip().split(",")
                    bowlers[bowler] = [int(throw) for throw in throws]
        except Exception as e:
            logger.error(f"Error loading data for {bowler} from: {source}")
            raise e
        if not bowler_id:
            try:
                return [
                    Game(
                        bowler=list(
                            filter(
                                lambda registered: (bowler == registered.bowler_id)
                                or (bowler in registered.nicknames),
                                REGISTERED_BOWLERS,
                            )
                        )[0],
                        throws=throws,
                        **extract_components(source),
                    )
                    for bowler, throws in bowlers.items()
                ]
            except Exception as e:
                logger.error(f"Cannot load game for {bowler}: {source}")
                raise e
        try:
            return [
                Game(
                    bowler=list(
                        filter(
                            lambda bowler: (bowler == bowler.bowler_id)
                            or (bowler in bowler.nicknames),
                            REGISTERED_BOWLERS,
                        )
                    )[0],
                    throws=throws,
                    **extract_components(source),
                )
                for bowler, throws in bowlers.items()
                if (bowler in bowler_id) or (bowler == bowler_id)
            ]
        except Exception as e:
            logger.error(f"Cannot load game for {bowler}: {source}")
            raise e

    @classmethod
    def load_games(cls, source: str | pathlib.Path = None) -> list["Game"]:
        """Load file(s) from source(s)."""
        if not source:
            source = DATABASE_SOURCE
        if not isinstance(source, pathlib.Path):
            source = pathlib.Path(source)

        all_games = [
            cls.load_game(file)
            for directory in source.iterdir()
            for file in directory.iterdir()
        ]
        all_games = list(itertools.chain(*all_games))
        logger.success(f"Loaded {len(all_games):,} games from the database")
        return all_games
