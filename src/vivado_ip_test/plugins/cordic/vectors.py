from math import isqrt

from vivado_ip_test.plugins.cordic.reference import scale_ratio
from vivado_ip_test.strategies.boundaries import boundary_values


def square_root_boundaries(parameters):
    limit = (1 << parameters["input_width"]) - 1
    numerator, denominator = scale_ratio(parameters)
    top = isqrt(limit * numerator // denominator)
    roots = (range(top + 1) if top <= 256 else
             {0, 1, 2, 3, top, top - 1, top // 2,
              *(value for value in boundary_values(parameters["output_width"], False) if value <= top)})
    values = set(boundary_values(parameters["input_width"], False))
    for root in roots:
        for num, den in ((root * root * denominator, numerator),
                         ((2 * root + 1) ** 2 * denominator, 4 * numerator)):
            quotient, remainder = divmod(num, den)
            values.update((quotient - 1, quotient, quotient + 1, quotient + int(bool(remainder))))
    return sorted(value for value in values if 0 <= value <= limit)


def prepare_frames(frames, spec, parameters):
    width = parameters["input_width"]
    padding = (1 << spec.payload[0].width) - (1 << width)
    patterns = (0, padding) if padding else (0,)
    directed = []
    for value in square_root_boundaries(parameters):
        for pad in patterns:
            index = len(directed)
            frame = {port.name: 0 for port in spec.payload}
            frame["tdata"] = value | pad
            if "tlast" in frame:
                frame["tlast"] = index % 2
            if "tuser" in frame:
                frame["tuser"] = (index * 0x9E3779B1) & ((1 << parameters["user_width"]) - 1)
            directed.append(frame)
    return directed + [dict(frame) for frame in frames]
