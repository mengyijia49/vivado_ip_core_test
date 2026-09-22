import random


DIRECTED_VALUES = (0, 1, -1, "minimum", "maximum", "alternating_a", "alternating_5", 3)
AES_CHANNEL_STATUS = int("0123456789ABCDEFAABBCCDDEEFF00112233445566778899", 16)


def _directed_value(kind, width, frame, channel):
    mask = (1 << width) - 1
    if kind == "minimum":
        value = 1 << (width - 1)
    elif kind == "maximum":
        value = (1 << (width - 1)) - 1
    elif kind == "alternating_a":
        value = int("10" * (width // 2), 2)
    elif kind == "alternating_5":
        value = int("01" * (width // 2), 2)
    else:
        value = int(kind) & mask
    return (value ^ ((channel * 0x31 + frame * 0x07) & mask)) & mask


def prepare_audio(parameters, verification):
    width = parameters["sample_width"]
    channels = parameters["channels"]
    frames = max(194, verification.case_budget,
                 (parameters["fifo_depth"] + channels - 1) // channels)
    rng = random.Random(verification.random_seed)
    samples = []
    for frame in range(frames):
        for channel in range(channels):
            pattern_frame = frame % 192
            if pattern_frame == 0:
                sample = 0
            elif pattern_frame == 1:
                sample = (1 << width) - 1
            elif pattern_frame - 2 < len(DIRECTED_VALUES):
                sample = _directed_value(DIRECTED_VALUES[pattern_frame - 2], width,
                                         pattern_frame, channel)
            else:
                sample = rng.randrange(1 << width)
            block_frame = pattern_frame
            preamble = 1 if block_frame == 0 and channel % 2 == 0 else (2 if channel % 2 == 0 else 3)
            shift = 4 + (24 - width)
            channel_status = (AES_CHANNEL_STATUS >> block_frame) & 1
            samples.append({"frame": frame, "channel": channel, "sample": sample,
                            "tdata": (channel_status << 30) | (sample << shift) | preamble,
                            "tid": channel})
    return samples


def serialized_samples(samples, channels):
    by_position = {(row["frame"], row["channel"]): row["sample"] for row in samples}
    frames = len(samples) // channels
    lanes = channels // 2
    return [by_position[(frame, lane * 2 + side)]
            for frame in range(1, frames) for side in range(2) for lane in range(lanes)]
