def construct_frames(throws: list[int]) -> list[list[int]]:
    """Construct frames from list of throws."""
    frames = []
    frame = []
    for throw in throws:
        frame.append(throw)
        if len(frames) < 9:
            if sum(frame) == 10 or len(frame) == 2:
                frames.append(frame)
                frame = []
        else:
            if len(frame) == 3 or (len(frame) == 2 and sum(frame) < 10):
                frame = construct_frames(frame)
                for f in frame:
                    frames.append(f)
                break
    return frames