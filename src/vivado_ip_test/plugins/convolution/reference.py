def convolution_codes(constraint_length, output_rate, family):
    mask = (1 << constraint_length) - 1
    if family == "ascending":
        return tuple(range(1, output_rate + 1))
    if family == "descending":
        return tuple(mask - index for index in range(output_rate))
    if family == "spread":
        offset = mask // 3
        return tuple((2 * index + offset) % mask + 1
                     for index in range(output_rate))
    raise ValueError(f"unknown convolution code family: {family}")


def encoded_symbols(bits, constraint_length, codes):
    state = 0
    state_mask = (1 << constraint_length) - 1
    symbols = []
    for bit in bits:
        state = (state >> 1) | ((bit & 1) << (constraint_length - 1))
        state &= state_mask
        symbol = sum(((state & code).bit_count() & 1) << index
                     for index, code in enumerate(codes))
        symbols.append(symbol)
    return symbols


def expected_transactions(frames, parameters):
    codes = convolution_codes(parameters["constraint_length"],
                              parameters["output_rate"],
                              parameters["code_family"])
    symbols = encoded_symbols((frame["tdata"] & 1 for frame in frames),
                              parameters["constraint_length"], codes)
    return [{"tdata": symbol} for symbol in symbols]
