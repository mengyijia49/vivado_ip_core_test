from vivado_ip_test.plugins.floating_point.formats import FloatFormat
from vivado_ip_test.plugins.floating_point.multi_input.vectors import prefixed_frames
from vivado_ip_test.plugins.floating_point.vectors import directed_values


def midpoint_significands(precision):
    low, high = 1 << (precision - 1), 1 << precision
    divisors = {low + offset for offset in (1, 3, 5, 7)} | {high - offset for offset in (1, 3, 5, 7)}
    for bit in range(1, precision - 1):
        divisors.update((low + (1 << bit) - 1, low + (1 << bit) + 1))
    pairs = set()
    for denominator in sorted(d for d in divisors if low <= d < high and d % 2):
        for below in (False, True):
            shift = precision - 1 + int(below)
            inverse = pow(1 << shift, -1, denominator)
            for remainder in (denominator // 2, denominator // 2 + 1):
                numerator = (remainder * inverse) % denominator
                while numerator < low:
                    numerator += denominator
                if numerator < high and (numerator < denominator) == below:
                    pairs.add((numerator, denominator))
    return sorted(pairs)


def directed_pairs(p):
    fmt = FloatFormat(p['input_exponent'], p['input_fraction'])
    sign, one = 1 << (fmt.width - 1), fmt.pack(0, fmt.bias, 0)
    limit = (sign << 1) - 1
    anchors = (0, sign, 1, sign | fmt.fraction_mask, fmt.pack(0, 1, 0), fmt.pack(1, 1, 0),
               one, one | sign, fmt.infinity(0) - 1, fmt.infinity(1) - 1,
               fmt.infinity(0), fmt.infinity(1), fmt.infinity(0) | 1, fmt.infinity(1) | 1,
               fmt.quiet_nan(), fmt.quiet_nan() | sign)
    pairs = {(a, b) for a in anchors for b in anchors}
    for value in directed_values(p):
        for other in (0, sign, one, one | sign, value, value ^ sign, (value - 1) & limit, (value + 1) & limit):
            pairs.add((value, other))
            pairs.add((other, value))
    for ma, mb in midpoint_significands(fmt.precision):
        for sa in (0, 1):
            for sb in (0, 1):
                pairs.add((fmt.pack(sa, fmt.bias, ma & fmt.fraction_mask),
                           fmt.pack(sb, fmt.bias, mb & fmt.fraction_mask)))
    for ea in (1, 2, fmt.bias - 1, fmt.bias, fmt.bias + 1, fmt.exponent_mask - 2, fmt.exponent_mask - 1):
        for difference in (-fmt.bias - 1, -fmt.bias, 1 - fmt.bias, 2 - fmt.bias, fmt.bias - 1, fmt.bias, fmt.bias + 1):
            eb = ea - difference
            if not 1 <= eb < fmt.exponent_mask:
                continue
            for fa, fb in ((0, 0), (0, 1), (1, 0), (0, fmt.fraction_mask),
                           (fmt.fraction_mask, 0), (fmt.fraction_mask - 1, fmt.fraction_mask),
                           (fmt.fraction_mask, fmt.fraction_mask - 1)):
                for sa in (0, 1):
                    for sb in (0, 1):
                        pairs.add((fmt.pack(sa, ea, fa), fmt.pack(sb, eb, fb)))
    return sorted(pairs)


def prepare_frames(frames, spec, p):
    prepared = prefixed_frames(frames, spec, p, directed_pairs(p))
    for index, row in enumerate(prepared):
        for lane_index, (lane, _) in enumerate(spec.lanes):
            if f'{lane}_tlast' in row:
                row[f'{lane}_tlast'] = (index >> lane_index) & 1
    return prepared
