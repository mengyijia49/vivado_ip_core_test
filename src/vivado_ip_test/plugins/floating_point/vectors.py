from vivado_ip_test.plugins.floating_point.formats import FloatFormat
from vivado_ip_test.plugins.floating_point.square_root import square_boundaries
from vivado_ip_test.strategies.boundaries import boundary_values


def directed_values(p):
    width = p["input_exponent"] + p["input_fraction"]
    limit = (1 << width) - 1
    values = set(boundary_values(width, False))
    if p["operation"] == "Fixed_to_float":
        precision = p["output_fraction"]
        for discarded in range(1, width - precision + 1):
            for retained in (1 << (precision - 1), (1 << (precision - 1)) + 1, (1 << precision) - 1):
                midpoint = (retained << discarded) + (1 << (discarded - 1))
                for offset in (-1, 0, 1):
                    value = midpoint + offset
                    if 0 <= value <= limit:
                        values.add(value)
                        if value <= 1 << (width - 1):
                            values.add((-value) & limit)
    else:
        fmt = FloatFormat(p["input_exponent"], p["input_fraction"])
        exponents = {0, 1, 2, fmt.exponent_mask - 2, fmt.exponent_mask - 1, fmt.exponent_mask,
                     fmt.bias - 1, fmt.bias, fmt.bias + 1}
        fractions = {0, 1, 2, fmt.fraction_mask - 1, fmt.fraction_mask,
                     (1 << (fmt.fraction_bits - 1)) - 1, 1 << (fmt.fraction_bits - 1),
                     (1 << (fmt.fraction_bits - 1)) + 1}
        if p["operation"] == "Float_to_float":
            target = FloatFormat(p["output_exponent"], p["output_fraction"])
            exponents.update(fmt.bias + e + delta for e in (1 - target.bias, target.bias)
                             for delta in (-1, 0, 1))
            discarded = fmt.precision - target.precision
            if discarded > 0:
                for retained in (0, 1, (1 << target.fraction_bits) - 1):
                    middle = (retained << discarded) + (1 << (discarded - 1))
                    fractions.update(middle + delta for delta in (-1, 0, 1))
        elif p["operation"] == "Float_to_fixed":
            exponents.update(fmt.bias + e + delta for e in (-p["output_fraction"] - 1,
                -p["output_fraction"], p["output_exponent"] - 2, p["output_exponent"] - 1)
                for delta in (-1, 0, 1))
            for discarded in range(1, fmt.fraction_bits + 1):
                middle = 1 << (discarded - 1)
                fractions.update(middle + delta for delta in (-1, 0, 1))
                fractions.update(fmt.fraction_mask - middle + delta for delta in (0, 1, 2))
        elif p["operation"] == "Square_root":
            values.update(square_boundaries(fmt))
        for sign in (0, 1):
            values.update(fmt.pack(sign, e, f) for e in exponents for f in fractions
                          if 0 <= e <= fmt.exponent_mask and 0 <= f <= fmt.fraction_mask)
    return sorted(values)


def prepare_frames(frames, spec, parameters):
    width = parameters["input_exponent"] + parameters["input_fraction"]
    padding = (1 << spec.payload[0].width) - (1 << width)
    directed = []
    for value in directed_values(parameters):
        for pad in ((0, padding) if padding else (0,)):
            index = len(directed)
            frame = {port.name: 0 for port in spec.payload}
            frame["tdata"] = value | pad
            if "tlast" in frame:
                frame["tlast"] = index % 2
            if "tuser" in frame:
                frame["tuser"] = (index * 0x9E3779B1) & ((1 << parameters["user_width"]) - 1)
            directed.append(frame)
    return directed + [dict(frame) for frame in frames]
