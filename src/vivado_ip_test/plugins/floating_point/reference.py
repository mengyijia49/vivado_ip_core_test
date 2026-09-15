from vivado_ip_test.plugins.floating_point.formats import FloatFormat, encode_float, round_binary, sign_extend
from vivado_ip_test.plugins.floating_point.square_root import normal_square_root


EXCEPTIONS = ("underflow", "overflow", "invalid_op")


def convert(bits, p):
    operation = p["operation"]
    source = FloatFormat(p["input_exponent"], p["input_fraction"])
    target = FloatFormat(p["output_exponent"], p["output_fraction"])
    bits &= (1 << source.width) - 1
    flags = {name: False for name in EXCEPTIONS}
    if operation == "Absolute":
        return bits & ((1 << (source.width - 1)) - 1), flags
    if operation == "Fixed_to_float":
        value = bits
        if not p["input_unsigned"] and bits & (1 << (source.width - 1)):
            value -= 1 << source.width
        result, flags["underflow"], flags["overflow"] = encode_float(
            int(value < 0), abs(value), -p["input_fraction"], target)
        return result, flags

    sign, exponent, fraction = source.unpack(bits)
    nan = exponent == source.exponent_mask and fraction != 0
    infinite = exponent == source.exponent_mask and fraction == 0
    if operation == "Square_root":
        if nan:
            return target.quiet_nan(), flags
        if exponent == 0:
            return target.pack(sign, 0, 0), flags
        if sign:
            flags["invalid_op"] = True
            return target.quiet_nan(), flags
        if infinite:
            return target.infinity(0), flags
        return normal_square_root(exponent, fraction, target), flags
    if operation == "Float_to_float":
        if nan:
            return target.quiet_nan(), flags
        if infinite:
            return target.infinity(sign), flags
        if exponent == 0:
            return target.pack(sign, 0, 0), flags
        result, flags["underflow"], flags["overflow"] = encode_float(sign,
            (1 << source.fraction_bits) | fraction, exponent - source.bias - source.fraction_bits, target)
        return result, flags

    if operation != "Float_to_fixed":
        raise ValueError(f"Unsupported floating point operation: {operation}")
    minimum, maximum = -(1 << (target.width - 1)), (1 << (target.width - 1)) - 1
    if nan:
        flags["invalid_op"] = True
        value = minimum
    elif infinite:
        flags["invalid_op"] = flags["overflow"] = True
        value = minimum if sign else maximum
    elif exponent == 0:
        value = 0
    else:
        value = round_binary((1 << source.fraction_bits) | fraction,
            exponent - source.bias - source.fraction_bits + p["output_fraction"])
        value = -value if sign else value
        flags["overflow"] = not minimum <= value <= maximum
        value = min(maximum, max(minimum, value))
    return value & ((1 << target.width) - 1), flags


def expected_transactions(frames, p):
    selected = [name for name in EXCEPTIONS if p["has_" + name]]
    width = p["output_exponent"] + p["output_fraction"]
    result = []
    for frame in frames:
        value, flags = convert(frame["tdata"], p)
        output = {"tdata": sign_extend(value, width)}
        if p["has_last"]:
            output["tlast"] = frame["tlast"]
        if p["user_width"] or selected:
            output["tuser"] = frame.get("tuser", 0) << len(selected)
            output["tuser"] |= sum(int(flags[name]) << i for i, name in enumerate(selected))
        result.append(output)
    return result
