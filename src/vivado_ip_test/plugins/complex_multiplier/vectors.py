from itertools import product

from vivado_ip_test.plugins.complex_multiplier.reference import byte_width


def pack_complex(real, imaginary, width, padding=0):
    mask = (1 << width) - 1
    field = byte_width(width)
    pad = ((1 << field) - 1) ^ mask if padding else 0
    return (real & mask) | pad | (((imaginary & mask) | pad) << field)


def directed_sequence(parameters, latency):
    p = parameters
    rounding = p["rounding"] == "Random_Rounding"
    channels = ("a", "b", "ctrl") if rounding else ("a", "b")
    enabled = {f"s_axis_{ch}_tvalid": 1 for ch in channels}

    def row(ar, ai, br, bi, index=0, carry=0, padding=0):
        values = {**enabled, "s_axis_a_tdata": pack_complex(ar, ai, p["a_width"], padding),
                  "s_axis_b_tdata": pack_complex(br, bi, p["b_width"], padding)}
        if rounding:
            values["s_axis_ctrl_tdata"] = (254 if padding else 0) | carry
        for position, ch in enumerate(channels):
            if p[f"{ch}_last"]:
                values[f"s_axis_{ch}_tlast"] = (index >> position) & 1
            width = p[f"{ch}_user_width"]
            if width:
                values[f"s_axis_{ch}_tuser"] = ((index + 1) << position) & ((1 << width) - 1)
        return values

    yield from ({} for _ in range(latency + 2))
    bounds = lambda width: (0, 1, -1, -(1 << (width - 1)), (1 << (width - 1)) - 1)
    for index, values in enumerate(product(bounds(p["a_width"]), bounds(p["a_width"]),
                                           bounds(p["b_width"]), bounds(p["b_width"]))):
        for carry in range(2 if rounding else 1):
            for padding in (0, 1):
                yield row(*values, index=index, carry=carry, padding=padding)
    # Products at, just below and just above the rounding threshold, for both signs.
    shift = p["a_width"] + p["b_width"] + 1 - p["output_width"]
    if rounding:
        exponent = shift - 1
        left = min(exponent, p["a_width"] - 1)
        right = exponent - left
        for a in (1 << left, -(1 << left)):
            for b in ((1 << right) - 1, 1 << right, (1 << right) + 1):
                for carry in (0, 1):
                    yield row(a, a, b, 0, carry=carry)
    for index, valids in enumerate(product((0, 1), repeat=len(channels))):
        values = row(3, -5, -7, 11, index=index)
        values.update({f"s_axis_{ch}_tvalid": valid for ch, valid in zip(channels, valids)})
        yield values
    for index in range(max(16, latency * 2)):
        yield row(index + 1, -index - 3, 2 * index + 1, index + 7, index=index, carry=index & 1)
    if p["clock_enable"]:
        for index in range(latency + 3):
            yield {**row(index + 31, -17, -11, 23, index=index), "aclken": 0}
    yield from ({} for _ in range(latency + 2))
