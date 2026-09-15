from math import isqrt


ROUND_MODES = {"Truncate": 0, "Round_Pos_Inf": 1, "Round_Pos_Neg_Inf": 2, "Nearest_Even": 3}


def scale_ratio(parameters):
    if parameters["data_format"] == "UnsignedInteger":
        return 1, 1
    shift = 2 * (parameters["output_width"] - 1) - (parameters["input_width"] - 1)
    return (1 << shift, 1) if shift >= 0 else (1, 1 << -shift)


def quantized_root(value, numerator, denominator, rounding):
    scaled = value * numerator
    lower = isqrt(scaled // denominator)
    if rounding == "Truncate":
        return lower
    # Compare with the exact squared midpoint; no floating-point rounding is involved.
    difference = 4 * scaled - denominator * (2 * lower + 1) ** 2
    increment = difference > 0 or difference == 0 and (rounding != "Nearest_Even" or lower % 2)
    return lower + int(increment)


def expected_transactions(frames, parameters):
    numerator, denominator = scale_ratio(parameters)
    mask = (1 << parameters["input_width"]) - 1
    width = parameters["output_width"]
    padded_width = ((width + 7) // 8) * 8
    result = []
    for frame in frames:
        value = quantized_root(frame["tdata"] & mask, numerator, denominator, parameters["rounding"])
        # PG105 TDATA packing sign-extends the result field, including unsigned square root.
        if value & (1 << (width - 1)):
            value |= (1 << padded_width) - (1 << width)
        result.append({**frame, "tdata": value})
    return result
