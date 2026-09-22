from vivado_ip_test.plugins.floating_point.formats import FloatFormat
from vivado_ip_test.strategies.boundaries import boundary_values


def directed_values(p):
    source = FloatFormat(p['input_exponent'], p['input_fraction'])
    target = FloatFormat(p['output_exponent'], p['output_fraction'])
    sign_bit = 1 << (source.width - 1)
    values = set(boundary_values(source.width, False))
    values.update((0, sign_bit, 1, sign_bit | 1,
        source.infinity(0), source.infinity(1), source.infinity(0) | 1,
        source.infinity(1) | 1, source.quiet_nan(), source.quiet_nan() | sign_bit))
    exponents = {1, 2, source.bias - 1, source.bias, source.bias + 1,
                 source.exponent_mask - 2, source.exponent_mask - 1}
    for unbiased in (-target.bias - 1, -target.bias, 1 - target.bias,
                     target.bias - 1, target.bias, target.bias + 1):
        exponents.update((source.bias + unbiased - 1, source.bias + unbiased,
                          source.bias + unbiased + 1))
    fractions = {0, 1, 2, source.fraction_mask - 1, source.fraction_mask,
                 1 << max(0, source.fraction_bits - 1)}
    for bit in {1, 2, source.fraction_bits // 2,
                max(1, source.fraction_bits - 2), source.fraction_bits - 1}:
        if 0 < bit < source.fraction_bits:
            fractions.update((max(0, (1 << bit) - 1), 1 << bit,
                              min(source.fraction_mask, (1 << bit) + 1)))
    for sign in (0, 1):
        values.update(source.pack(sign, exponent, fraction)
                      for exponent in exponents for fraction in fractions
                      if 0 < exponent < source.exponent_mask and
                      0 <= fraction <= source.fraction_mask)
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
