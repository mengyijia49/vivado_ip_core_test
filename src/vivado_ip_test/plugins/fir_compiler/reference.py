from math import ceil, log2


def signed_value(value, width):
    value &= (1 << width) - 1
    return value - (1 << width) if value & (1 << (width - 1)) else value


def vendor_output_width(data_width, coefficients):
    """Width reported by FIR Compiler Full Precision for fixed integer taps."""
    magnitude = sum(abs(value) for value in coefficients)
    return data_width + (ceil(log2(magnitude)) if magnitude > 1 else 0)


def mathematical_output_width(data_width, coefficients):
    low, high = -(1 << (data_width - 1)), (1 << (data_width - 1)) - 1
    minimum = sum(coefficient * (low if coefficient >= 0 else high)
                  for coefficient in coefficients)
    maximum = sum(coefficient * (high if coefficient >= 0 else low)
                  for coefficient in coefficients)
    width = 1
    while minimum < -(1 << (width - 1)) or maximum > (1 << (width - 1)) - 1:
        width += 1
    return width


def expected_transactions(frames, parameters):
    data_width = parameters["data_width"]
    coefficients = parameters["coefficients"]
    result_width = vendor_output_width(data_width, coefficients)
    padded_width = ((result_width + 7) // 8) * 8
    history = [0] * len(coefficients)
    outputs = []
    for frame in frames:
        history = [signed_value(frame["tdata"], data_width), *history[:-1]]
        value = sum(coefficient * sample for coefficient, sample in zip(coefficients, history))
        encoded = value & ((1 << padded_width) - 1)
        outputs.append({**frame, "tdata": encoded})
    return outputs
