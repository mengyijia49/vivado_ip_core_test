from decimal import ROUND_FLOOR, Decimal

from vivado_ip_test.plugins.cordic.sin_cos.reference import PI, decode_signed


def _maximum_phase_code(parameters):
    scale = 1 << (parameters["input_width"] - 3)
    if parameters["phase_format"] == "Scaled_Radians":
        limit = Decimal(1) if parameters["coarse_rotation"] else Decimal("0.25")
    else:
        limit = PI if parameters["coarse_rotation"] else PI / 4
    return int((limit * scale).to_integral_value(rounding=ROUND_FLOOR))


def legal_phase_codes(parameters):
    maximum = _maximum_phase_code(parameters)
    values = {0, -maximum, maximum}
    for denominator in (2, 4, 8, 16):
        point = maximum // denominator
        values.update((-point, point))
    if parameters["phase_format"] == "Radians":
        scale = 1 << (parameters["input_width"] - 3)
        for ratio in (Decimal("0.5"), Decimal("0.25")):
            point = int((PI * ratio * scale).to_integral_value(rounding=ROUND_FLOOR))
            if point <= maximum:
                values.update((-point, point))
    expanded = set()
    for value in values:
        expanded.update((value - 1, value, value + 1))
    return sorted(value for value in expanded if -maximum <= value <= maximum)


def _encode(value, width):
    return value & ((1 << width) - 1)


def _map_to_legal(value, parameters):
    maximum = _maximum_phase_code(parameters)
    span = 2 * maximum + 1
    signed = decode_signed(value, parameters["input_width"])
    return (signed + maximum) % span - maximum


def prepare_frames(frames, spec, parameters):
    width = parameters["input_width"]
    padding = (1 << spec.payload[0].width) - (1 << width)
    patterns = (0, padding) if padding else (0,)
    result = []
    for value in legal_phase_codes(parameters):
        for pad in patterns:
            index = len(result)
            frame = {port.name: 0 for port in spec.payload}
            frame["tdata"] = _encode(value, width) | pad
            if "tlast" in frame:
                frame["tlast"] = index & 1
            if "tuser" in frame:
                frame["tuser"] = (index * 0x9E3779B1) & ((1 << parameters["user_width"]) - 1)
            result.append(frame)
    for source in frames:
        frame = dict(source)
        frame["tdata"] = _encode(_map_to_legal(frame["tdata"], parameters), width)
        result.append(frame)
    return result
