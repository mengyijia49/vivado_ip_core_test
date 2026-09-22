def prepare_frames(frames, parameters):
    length = parameters["constraint_length"]
    bits = ([0] * length + [1] + [0] * length +
            [1] * (length + 2) +
            [index & 1 for index in range(2 * length + 2)])
    prefix = [{"tdata": ((index * 0x26) & 0xFE) | bit}
              for index, bit in enumerate(bits)]
    return prefix + [dict(frame) for frame in frames]
