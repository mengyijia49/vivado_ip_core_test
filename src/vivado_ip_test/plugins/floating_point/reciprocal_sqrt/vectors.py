from vivado_ip_test.plugins.floating_point.formats import FloatFormat
from vivado_ip_test.plugins.floating_point.reciprocal.reference import encode_ratio
from vivado_ip_test.strategies.boundaries import boundary_values


def rounding_boundaries(source, target):
    values = set()
    output_exponents = {1, 2, target.bias - 1, target.bias, target.bias + 1,
                        target.exponent_mask - 2, target.exponent_mask - 1}
    base = 1 << target.fraction_bits
    significands = {base, base + 1, base + 2, 2 * base - 2, 2 * base - 1}
    for bit in {1, 2, target.fraction_bits // 2,
                max(1, target.fraction_bits - 2), target.fraction_bits - 1}:
        if 0 < bit < target.fraction_bits:
            significands.update((max(base, base + (1 << bit) - 1),
                                 base + (1 << bit),
                                 min(2 * base - 1, base + (1 << bit) + 1)))
    for encoded_exponent in output_exponents:
        if not 0 < encoded_exponent < target.exponent_mask:
            continue
        exponent = encoded_exponent - target.bias
        for significand in significands:
            midpoint = 2 * significand + 1
            shift = 2 * (target.fraction_bits + 1 - exponent)
            encoded, _ = encode_ratio(0, 1, midpoint * midpoint, shift, source)
            for offset in (-2, -1, 0, 1, 2):
                bits = encoded + offset
                _, source_exponent, _ = source.unpack(bits)
                if 0 < source_exponent < source.exponent_mask:
                    values.add(bits)
    return values


def directed_values(p):
    source = FloatFormat(p['input_exponent'], p['input_fraction'])
    target = FloatFormat(p['output_exponent'], p['output_fraction'])
    sign_bit = 1 << (source.width - 1)
    values = set(boundary_values(source.width, False))
    values.update((0, sign_bit, 1, sign_bit | 1,
        source.infinity(0), source.infinity(1), source.infinity(0) | 1,
        source.infinity(1) | 1, source.quiet_nan(), source.quiet_nan() | sign_bit))
    exponents = {1, 2, source.bias - 2, source.bias - 1, source.bias,
                 source.bias + 1, source.bias + 2,
                 source.exponent_mask - 2, source.exponent_mask - 1}
    fractions = {0, 1, 2, source.fraction_mask // 2,
                 source.fraction_mask - 1, source.fraction_mask}
    values.update(source.pack(sign, exponent, fraction)
                  for sign in (0, 1) for exponent in exponents for fraction in fractions
                  if 0 < exponent < source.exponent_mask)
    values.update(rounding_boundaries(source, target))
    return sorted(values)


def prepare_frames(frames, spec, p):
    source_width = p['input_exponent'] + p['input_fraction']
    padding = (1 << spec.payload[0].width) - (1 << source_width)
    directed = []
    for value in directed_values(p):
        for pad in ((0, padding) if padding else (0,)):
            index = len(directed)
            row = {port.name: 0 for port in spec.payload}
            row['tdata'] = value | pad
            if 'tlast' in row:
                row['tlast'] = index & 1
            if 'tuser' in row:
                row['tuser'] = (index * 0x9E3779B1) & ((1 << p['user_width']) - 1)
            directed.append(row)
    return directed + [dict(frame) for frame in frames]
