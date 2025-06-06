import pathlib
from attrs import define, field
import datetime
from loguru import logger
import itertools
from pinsdb.bowlers import Bowler, registered_bowlers


TOTAL_FRAME_PINS: int = 10
TOTAL_GAME_PINS: int = 120
TOTAL_GAME_SCORE: int = 300
DATABASE_SOURCE: str = "/Users/lucasnelson/Desktop/open_source/pinsdb/.data"


def extract_components(source: str, database_source: str = DATABASE_SOURCE) -> dict[str, str]:
    def extract_date_component(date_component: str) -> datetime.date:
        return datetime.date.fromisoformat(date_component)
    
    def extract_game_component(game_component: str) -> str:
        return ''.join(s for s in game_component if s.isdigit())
    
    relative_source = pathlib.Path(source).relative_to(database_source)
    date_component, game_component = relative_source.parts
    return {"date": extract_date_component(date_component), "game_id": extract_game_component(game_component)}


@define
class Frame:
    throws: tuple[int] = field()

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
                    bowler, *throws = line.strip().split(',')
                    bowlers[bowler] = [int(throw) for throw in throws]
        except Exception as e:
            logger.error(f"Error loading data for {bowler} from: {source}")
            raise e
        if not bowler_id:
            try:
                return [
                    Game(
                        bowler=list(filter(lambda registered: (bowler == registered.bowler_id) or (bowler in registered.nicknames), registered_bowlers))[0],
                        throws=throws,
                        **extract_components(source)
                    )
                    for bowler, throws in bowlers.items()
                ]
            except Exception as e:
                print(f"Cannot load game for {bowler}: {source}")
                raise e
        try:
            return [
                Game(
                    bowler=list(filter(lambda bowler: (bowler == bowler.bowler_id) or (bowler in bowler.nicknames), registered_bowlers))[0],
                    throws=throws,
                    **extract_components(source)
                )
                for bowler, throws in bowlers.items()
                if (bowler in bowler_id) or (bowler == bowler_id)
            ]
        except Exception as e:
            print(f"Cannot load game for {bowler}: {source}")
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
        print(f"Loaded {len(all_games):,} games from the database")
        return all_games

    def construct_frames(self) -> list[list[int]]:
        """Construct frames from list of throws."""
        frames = []
        frame = []
        for throw in self.throws:
            frame.append(throw)
            if len(frames) < 9:  # For the first 9 frames
                if sum(frame) == 10 or len(frame) == 2:  # Strike or complete frame
                    frames.append(frame)
                    frame = []
            else:  # 10th frame
                if len(frame) == 3 or (len(frame) == 2 and sum(frame) < 10):
                    frames.append(frame)
                    break  # End after processing the 10th frame
        return frames

    def score_pins(self) -> int:
        """Return score not following bowling scoring conventions."""
        if not self.throws:
            return 0
        return sum(self.throws)
    
    def score_game(self) -> int:
        """
        Return score following bowling scoring conventions.
        
        Notes
        -----
        Link: https://www.bowlinggenius.com/#
        """
        if not self.throws:
            return 0
        
        frames = self.construct_frames()
        bonus = [Frame(frame).detect_bonus() for frame in frames]
        
        current_index = 0
        current_sum = 0
        for i, (frame, bonus) in enumerate(zip(frames, bonus)):
            frame = Frame(frame)
            if i > 8:
                bonus = None
            if bonus:
                if frame.is_spare():
                    bonus_frames = self.throws[current_index: current_index + bonus + 2]
                if frame.is_strike():
                    bonus_frames = self.throws[current_index : current_index + bonus + 1]
                current_sum += sum(bonus_frames)
            else:
                bonus_frames = []
                current_sum += sum(frame.throws)

            current_index += len(frame.throws)
        
        return current_sum
