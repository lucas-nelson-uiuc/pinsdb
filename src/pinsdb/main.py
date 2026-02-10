import re
import pathlib
import datetime
import click

from pinsdb.namespace.compute import score_pins, score_game


DATA_DIRECTORY = "/Users/lucasnelson/Desktop/open_source/pinsdb/.data"


@click.group()
def cli():
    pass


@click.command
@click.option("--date", prompt="Date of game, in format YYYY-MM-DD")
@click.option("--games", prompt="Number of games")
@click.option("--bowlers", prompt="Bowlers (comma-separated)")
def mkdir(date: str, games: str, bowlers: str) -> None:

    try:
        datetime.datetime.strptime(date, "%Y-%m-%d")
    except Exception as e:
        msg = "Expected date to be in YYYY-MM-DD format, received invalid entry."
        raise ValueError(msg) from e

    directory = pathlib.Path(DATA_DIRECTORY).joinpath(date.replace("-", ""))
    directory.mkdir(exist_ok=False)

    try:
        bowler_name_pattern = re.compile(r"[A-Z]{1,}[,[A-Z]{1,}]*")
        assert bowler_name_pattern.search(bowlers)
    except AssertionError as e:
        msg = f"Expected bowlers in format ABC,DEF,GHI,... , received {bowlers}."
        raise ValueError(msg) from e
    except Exception as e:
        raise e

    bowlers = [bowler.strip().upper() for bowler in bowlers.split(",") if bowler]

    for i in range(int(games)):
        game_file = directory.joinpath(f"G{i + 1}.txt")
        try:
            game_file.touch()
            game_file.write_text("\n".join(f"{bowler}," for bowler in bowlers))
            print(f"Created game file: {game_file}")
        except FileExistsError:
            print(f"File already exists: {game_file}")
        except Exception as e:
            raise e


@click.command
@click.option("--date", prompt="Date of game, in format YYYY-MM-DD")
def score(date: str) -> None:
    date = datetime.datetime.strptime(date, "%Y-%m-%d").strftime("%Y%m%d")
    directory = pathlib.Path(DATA_DIRECTORY) / date
    for game in sorted(directory.iterdir()):
        print(f"=== {game}")
        file = directory / game
        lines = file.read_text().split("\n")
        for line in lines:
            bowler, *throws = line.split(",")
            if len(throws) < 2:
                continue
            throws = list(map(int, throws))
            pins = score_pins(throws=throws)
            score = score_game(throws=list(map(int, throws)))
            print(f"Bowler: {bowler:>5} | Pins: {pins:>3} | Score: {score:>3}")


cli.add_command(mkdir)
cli.add_command(score)


if __name__ == "__main__":
    cli()
