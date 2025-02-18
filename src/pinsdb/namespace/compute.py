from pinsdb.models import Frame
from pinsdb.namespace.construct import construct_frames


def score_pins(throws: list[int]) -> int:
    """Return score not following bowling scoring conventions."""
    return sum(throws)


def score_game(throws: list[int] = None) -> int:
    """
    Return score following bowling scoring conventions.

    Notes
    -----
    Link: https://www.bowlinggenius.com/#
    """
    if throws is None:
        return 0

    frames = construct_frames(throws=throws)
    bonus = [Frame(frame).detect_bonus() for frame in frames]

    current_index = 0
    current_sum = 0
    for i, (frame, bonus) in enumerate(zip(frames, bonus)):
        frame = Frame(frame)
        if i > 8:
            bonus = None
        if bonus:
            if frame.is_spare():
                bonus_frames = throws[
                    current_index : current_index + bonus + 2
                ]
            if frame.is_strike():
                bonus_frames = throws[
                    current_index : current_index + bonus + 1
                ]
            current_sum += sum(bonus_frames)
        else:
            bonus_frames = []
            current_sum += sum(frame.throws)

        current_index += len(frame.throws)

    return current_sum
