from vivado_ip_test.plugins.floating_point.multi_input.vectors import prefixed_frames
from vivado_ip_test.plugins.floating_point.formats import FloatFormat
from vivado_ip_test.plugins.floating_point.vectors import directed_values


def directed_pairs(p):
    fmt = FloatFormat(p['input_exponent'], p['input_fraction'])
    sign = 1 << (fmt.width - 1)
    limit = (sign << 1) - 1
    one = fmt.pack(0, fmt.bias, 0)
    anchors = (0, sign, 1, sign | fmt.fraction_mask, fmt.pack(0, 1, 0), fmt.pack(1, 1, 0),
               one, one | sign, fmt.infinity(0) - 1, fmt.infinity(1) - 1,
               fmt.infinity(0), fmt.infinity(1), fmt.infinity(0) | 1, fmt.infinity(1) | 1,
               fmt.quiet_nan(), fmt.quiet_nan() | sign)
    pairs = {(a, b) for a in anchors for b in anchors}
    for value in directed_values(p):
        for other in (0, sign, one, one | sign, value, value ^ sign, (value - 1) & limit, (value + 1) & limit):
            pairs.add((value, other))
            pairs.add((other, value))
    for exponent in (1, 2, fmt.bias - 1, fmt.bias, fmt.bias + 1, fmt.exponent_mask - 2, fmt.exponent_mask - 1):
        for fraction in (0, 1, fmt.fraction_mask - 1, fmt.fraction_mask):
            a = fmt.pack(0, exponent, fraction)
            for gap in (fmt.precision - 1, fmt.precision, fmt.precision + 1):
                if exponent - gap > 0:
                    center = fmt.pack(0, exponent - gap, 0)
                    for offset in (-1, 0, 1):
                        for sa in (0, sign):
                            for sb in (0, sign):
                                pairs.add((a | sa, (center + offset) | sb))
    # (1 + ulp) * 1.5 is a product rounding midpoint; adjacent B values test either side.
    for offset in (-1, 0, 1):
        b = fmt.pack(0, fmt.bias, 1 << (fmt.fraction_bits - 1)) + offset
        for a in (one + 1, one + 3):
            for sa in (0, sign):
                for sb in (0, sign):
                    pairs.add((a | sa, b | sb))
    for exponent in (1, 2, fmt.bias - 1, fmt.bias, fmt.bias + 1, fmt.exponent_mask - 2, fmt.exponent_mask - 1):
        for result_exponent in (-fmt.bias, 1 - fmt.bias, 2 - fmt.bias, fmt.bias - 1, fmt.bias, fmt.bias + 1):
            other_exponent = 2 * fmt.bias + result_exponent - exponent
            if not 1 <= other_exponent < fmt.exponent_mask:
                continue
            for fa, fb in ((0, 0), (0, fmt.fraction_mask), (1, fmt.fraction_mask),
                           (fmt.fraction_mask, 1), (fmt.fraction_mask, fmt.fraction_mask)):
                for sa in (0, 1):
                    for sb in (0, 1):
                        pairs.add((fmt.pack(sa, exponent, fa), fmt.pack(sb, other_exponent, fb)))
    for sa in (0, sign):
        for sb in (0, sign):
            pairs.add((fmt.pack(0, 1, 0) | sa, (one - 1) | sb))
    return sorted(pairs)


def prepare_frames(frames, spec, p):
    codes = (0, 1) if p.get('add_sub_value') == 'Both' else (None,)
    prepared = []
    for frame in prefixed_frames(frames, spec, p, directed_pairs(p)):
        padding_code = (len(prepared) // len(codes)) % 4
        for code in codes:
            row = dict(frame)
            if code is not None:
                row['operation_tdata'] = code | (padding_code << 6)
            for lane_index, (lane, _) in enumerate(spec.lanes):
                if f'{lane}_tlast' in row:
                    row[f'{lane}_tlast'] = (len(prepared) >> lane_index) & 1
            prepared.append(row)
    return prepared
