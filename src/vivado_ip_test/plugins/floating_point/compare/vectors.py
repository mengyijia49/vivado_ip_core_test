from vivado_ip_test.plugins.floating_point.multi_input.vectors import prefixed_frames
from vivado_ip_test.plugins.floating_point.formats import FloatFormat
from vivado_ip_test.plugins.floating_point.compare.reference import OPERATION_CODES
from vivado_ip_test.plugins.floating_point.multi_input.timing import independent_gaps
from vivado_ip_test.strategies.boundaries import boundary_values


def directed_pairs(fmt):
    limit, sign = (1 << fmt.width) - 1, 1 << (fmt.width - 1)
    anchors = (0, sign, 1, sign | fmt.fraction_mask, fmt.pack(0, 1, 0), fmt.pack(1, 1, 0),
               fmt.pack(0, fmt.bias, 0), fmt.pack(1, fmt.bias, 0), fmt.infinity(0) - 1,
               fmt.infinity(1) - 1, fmt.infinity(0), fmt.infinity(1), fmt.infinity(0) | 1,
               fmt.infinity(1) | 1, fmt.quiet_nan(), fmt.quiet_nan() | sign)
    values = sorted(set(anchors) | set(boundary_values(fmt.width, False)))
    pairs = set((a, b) for a in anchors for b in anchors)
    for value in values:
        for other in (0, sign, value, value ^ sign, (value - 1) & limit, (value + 1) & limit):
            pairs.add((value, other))
            pairs.add((other, value))
    return sorted(pairs)


def prepare_frames(frames, spec, p):
    fmt = FloatFormat(p['input_exponent'], p['input_fraction'])
    prepared = []
    codes = tuple(OPERATION_CODES) if p['compare_operation'] == 'Programmable' else (None,)
    for frame in prefixed_frames(frames, spec, p, directed_pairs(fmt)):
        for code in codes:
            row = dict(frame)
            index = len(prepared)
            if code is not None:
                row['operation_tdata'] = code | ((index % 4) << 6)
            for lane_index, (lane, _) in enumerate(spec.lanes):
                if f'{lane}_tlast' in row:
                    row[f'{lane}_tlast'] = (index >> lane_index) & 1
            prepared.append(row)
    return prepared
