def signed_value(value, width):
    value &= (1 << width) - 1
    return value - (1 << width) if value & (1 << (width - 1)) else value


def full_precision_width(filter_type, input_width, stages, differential_delay, rate):
    gain = (rate * differential_delay) ** stages
    if filter_type == "Interpolation":
        gain //= rate
    return input_width + (gain - 1).bit_length()


def physical_width(width):
    return ((width + 7) // 8) * 8


def encode_signed(value, logical_width):
    padded = physical_width(logical_width)
    raw = value & ((1 << logical_width) - 1)
    if raw & (1 << (logical_width - 1)):
        raw |= ((1 << padded) - 1) ^ ((1 << logical_width) - 1)
    return raw


def _comb(value, delays):
    for history in delays:
        previous = history.pop(0)
        history.append(value)
        value -= previous
    return value


def _integrate(value, states):
    for index in range(len(states)):
        states[index] += value
        value = states[index]
    return value


def cic_values(values, parameters):
    stages = parameters["stages"]
    delay = parameters["differential_delay"]
    rate = parameters["rate"]
    histories = [[0] * delay for _ in range(stages)]
    integrators = [0] * stages
    outputs = []
    if parameters["filter_type"] == "Decimation":
        for index, sample in enumerate(values):
            integrated = _integrate(sample, integrators)
            if index % rate == 0:
                outputs.append(_comb(integrated, histories))
    else:
        for sample in values:
            differentiated = _comb(sample, histories)
            for value in (differentiated, *([0] * (rate - 1))):
                outputs.append(_integrate(value, integrators))
    return outputs


def expected_transactions(frames, parameters):
    width = parameters["input_width"]
    values = [signed_value(frame["tdata"], width) for frame in frames]
    output_width = full_precision_width(parameters["filter_type"], width,
                                        parameters["stages"],
                                        parameters["differential_delay"],
                                        parameters["rate"])
    return [{"tdata": encode_signed(value, output_width)}
            for value in cic_values(values, parameters)]


def causal_input_counts(frames, expected, parameters):
    rate = parameters["rate"]
    if parameters["filter_type"] == "Decimation":
        return [rate * index + 1 for index in range(len(expected))]
    return [index // rate + 1 for index in range(len(expected))]
