from math import isqrt

from vivado_ip_test.plugins.floating_point.formats import FloatFormat, sign_extend


FLAGS = ('invalid_op', 'divide_by_zero')


def normal_reciprocal_sqrt(exponent, fraction, source, target):
    magnitude = (1 << source.fraction_bits) | fraction
    scale = exponent - source.bias - source.fraction_bits
    input_exponent = exponent - source.bias
    result_exponent = -(input_exponent // 2) - 1
    if fraction == 0 and input_exponent % 2 == 0:
        result_exponent += 1

    if result_exponent < 1 - target.bias:
        return target.pack(0, 0, 0)
    if result_exponent > target.bias:
        return target.infinity(0)

    shift = 2 * (target.fraction_bits - result_exponent) - scale
    numerator = 1 << max(0, shift)
    denominator = magnitude << max(0, -shift)
    lower = isqrt(numerator // denominator)
    midpoint_squared = denominator * (2 * lower + 1) ** 2
    significand = lower + int(4 * numerator > midpoint_squared or
                              (4 * numerator == midpoint_squared and lower % 2))
    if significand == 1 << target.precision:
        significand >>= 1
        result_exponent += 1
    if result_exponent < 1 - target.bias:
        return target.pack(0, 0, 0)
    if result_exponent > target.bias:
        return target.infinity(0)
    return target.pack(0, result_exponent + target.bias,
                       significand & target.fraction_mask)


def calculate(bits, source, target):
    bits &= (1 << source.width) - 1
    sign, exponent, fraction = source.unpack(bits)
    flags = {name: False for name in FLAGS}
    if exponent == source.exponent_mask:
        if fraction:
            return target.quiet_nan(), flags
        if sign:
            flags['invalid_op'] = True
            return target.quiet_nan(), flags
        return target.pack(0, 0, 0), flags
    if exponent == 0:
        flags['divide_by_zero'] = True
        return target.infinity(sign), flags
    if sign:
        flags['invalid_op'] = True
        return target.quiet_nan(), flags
    return normal_reciprocal_sqrt(exponent, fraction, source, target), flags


def expected_transactions(frames, p):
    source = FloatFormat(p['input_exponent'], p['input_fraction'])
    target = FloatFormat(p['output_exponent'], p['output_fraction'])
    selected = [name for name in FLAGS if p['has_' + name]]
    result = []
    for frame in frames:
        value, flags = calculate(frame['tdata'], source, target)
        output = {'tdata': sign_extend(value, target.width)}
        if p['has_last']:
            output['tlast'] = frame['tlast']
        if p['user_width'] or selected:
            output['tuser'] = frame.get('tuser', 0) << len(selected)
            output['tuser'] |= sum(int(flags[name]) << index
                                   for index, name in enumerate(selected))
        result.append(output)
    return result
