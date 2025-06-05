def is_frame(frame: list[int]) -> bool:
    """Detect if list of throws is a valid frame."""
    return (len(frame) == 2) or (sum(frame) == 10)


def construct_frames(throws: list[int]) -> list[list[int]]:
    """Construct frames from list of throws."""
    # instantiate empty collectors
    frames = []
    frame = []

    for i, throw in enumerate(throws):
        frame.append(throw)
        if is_frame(frame):
            frames.append(frame)
            frame = []
        elif (i + 1) == len(throws):  # if last throw, make complete frame
            frame.append(0)
            frames.append(frame)
        else:
            continue
    return frames
