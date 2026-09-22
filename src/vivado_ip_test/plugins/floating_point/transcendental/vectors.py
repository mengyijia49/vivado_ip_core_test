from decimal import Decimal, localcontext

from vivado_ip_test.plugins.floating_point.formats import FloatFormat
from vivado_ip_test.plugins.floating_point.reciprocal.reference import encode_ratio
from vivado_ip_test.strategies.boundaries import boundary_values


def _encode_decimal(value, fmt):
    numerator, denominator = abs(value).as_integer_ratio()
    result, _ = encode_ratio(int(value.is_signed()), numerator, denominator, 0, fmt)
    return result


def directed_values(p):
    source = FloatFormat(p['input_exponent'], p['input_fraction'])
    sign_bit = 1 << (source.width - 1)
    values = set(boundary_values(source.width, False))
    values.update((0, sign_bit, 1, sign_bit | 1, source.infinity(0), source.infinity(1),
                   source.infinity(0) | 1, source.infinity(1) | 1,
                   source.quiet_nan(), source.quiet_nan() | sign_bit))
    exponents = {1, 2, source.bias - 2, source.bias - 1, source.bias,
                 source.bias + 1, source.bias + 2,
                 source.exponent_mask - 2, source.exponent_mask - 1}
    fractions = {0, 1, 2, source.fraction_mask // 2,
                 source.fraction_mask - 1, source.fraction_mask}
    values.update(source.pack(sign, exponent, fraction)
                  for sign in (0, 1) for exponent in exponents for fraction in fractions
                  if 0 < exponent < source.exponent_mask)
    with localcontext() as context:
        context.prec = 160
        constants = [Decimal(1), Decimal(2), Decimal('0.5'), Decimal(2).ln(),
                     -Decimal(2).ln(), Decimal(10), -Decimal(10)]
        for constant in constants:
            encoded = _encode_decimal(constant, source)
            values.update(encoded + offset for offset in (-2, -1, 0, 1, 2)
                          if 0 <= encoded + offset < (1 << source.width))
        if p['operation'] == 'Exponential':
            maximum = Decimal((1 << source.precision) - 1) * (
                Decimal(2) ** (source.bias - source.fraction_bits))
            minimum = Decimal(2) ** (1 - source.bias)
            for threshold in (maximum.ln(), minimum.ln()):
                encoded = _encode_decimal(threshold, source)
                values.update(encoded + offset for offset in (-3, -2, -1, 0, 1, 2, 3)
                              if 0 <= encoded + offset < (1 << source.width))
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
