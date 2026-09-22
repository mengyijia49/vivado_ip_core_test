from vivado_ip_test.plugins.xfft.reference import pack_complex, unpack_complex


def _frame(samples, width):
    last = len(samples) - 1
    return [{"tdata": pack_complex(real, imag, width), "tlast": int(index == last)}
            for index, (real, imag) in enumerate(samples)]


def prepare_frames(seed_frames, parameters):
    length = parameters["transform_length"]
    width = parameters["input_width"]
    high = (1 << (width - 1)) - 1
    amplitude = max(1, high // 3)
    zero = [(0, 0)] * length
    patterns = [zero]

    for value in ((high, 0), (0, -high)):
        impulse = [(0, 0)] * length
        impulse[0] = value
        patterns.append(impulse)
    patterns.append([(amplitude, 0)] * length)
    patterns.append([(0, -amplitude)] * length)
    patterns.append([(amplitude if index % 2 == 0 else -amplitude, 0)
                     for index in range(length)])
    quarter = ((amplitude, 0), (0, amplitude), (-amplitude, 0), (0, -amplitude))
    patterns.append([quarter[index % 4] for index in range(length)])
    shifted = [(0, 0)] * length
    shifted[length // 4] = (-amplitude, amplitude)
    patterns.append(shifted)

    frames = [beat for pattern in patterns for beat in _frame(pattern, width)]
    for seed in seed_frames:
        impulse = [(0, 0)] * length
        impulse[0] = unpack_complex(seed["tdata"], width)
        frames.extend(_frame(impulse, width))
    return frames
