from vivado_ip_test.plugins.floating_point.formats import FloatFormat
from vivado_ip_test.plugins.floating_point.multi_input.vectors import user_tag


def directed_triples(p):
    fmt = FloatFormat(p['input_exponent'], p['input_fraction'])
    sign = 1 << (fmt.width - 1)
    one = fmt.pack(0, fmt.bias, 0)
    minimum = fmt.pack(0, 1, 0)
    maximum = fmt.infinity(0) - 1
    anchors = (0, sign, minimum, minimum | sign, one, one | sign, maximum, maximum | sign,
               fmt.infinity(0), fmt.infinity(1), fmt.quiet_nan(), fmt.quiet_nan() | sign)
    triples = {(a, b, c) for a in anchors for b in anchors for c in (0, one, one | sign)}
    triples.update((one, one, c) for c in anchors)
    # A*B rounds to one if evaluated separately; fused evaluation retains the residue.
    k = min(fmt.fraction_bits, max(2, (fmt.bias - 2) // 2))
    above_one = one + (1 << (fmt.fraction_bits - k))
    below_one = one - (1 << (fmt.precision - k))
    triples.update({(above_one, below_one, one | sign),
                    (above_one | sign, below_one, one),
                    (maximum, one, maximum), (minimum, minimum, minimum),
                    (fmt.infinity(0), 0, one), (0, fmt.infinity(1), one),
                    (fmt.infinity(0), one, fmt.infinity(1)),
                    (fmt.infinity(1), one, fmt.infinity(0))})
    return sorted(triples)


def prepare_frames(frames, spec, p):
    fmt = FloatFormat(p['input_exponent'], p['input_fraction'])
    padding = (1 << spec.lanes[0][1][0].width) - (1 << fmt.width)
    base = {port.name: 0 for port in spec.payload}
    prefix = []
    for index, values in enumerate(directed_triples(p)):
        opcodes = (0, 1) if index < 32 else (index & 1,)
        for opcode in opcodes:
            row = dict(base)
            data_index = 0
            for lane_index, (lane, ports) in enumerate(spec.lanes):
                if lane == 'operation':
                    row['operation_tdata'] = opcode | ((index % 4) << 6)
                else:
                    row[f'{lane}_tdata'] = values[data_index] | (
                        padding if padding and (len(prefix) >> data_index) & 1 else 0)
                    data_index += 1
                for port in ports:
                    if port.name == 'tuser':
                        row[f'{lane}_tuser'] = user_tag(len(prefix), lane_index, port.width)
                    elif port.name == 'tlast':
                        row[f'{lane}_tlast'] = (len(prefix) >> lane_index) & 1
            prefix.append(row)
    return prefix + [{**base, **frame} for frame in frames]
