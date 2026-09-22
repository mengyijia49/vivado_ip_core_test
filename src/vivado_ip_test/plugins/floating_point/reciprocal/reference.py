from vivado_ip_test.plugins.floating_point.formats import FloatFormat, sign_extend


FLAGS = ('underflow', 'divide_by_zero')


def _less_than_power(numerator, denominator, shift, exponent):
    difference = exponent - shift
    if difference >= 0:
        return numerator < (denominator << difference)
    return (numerator << -difference) < denominator


def _round_scaled_ratio(numerator, denominator, shift):
    if shift >= 0:
        quotient, remainder = divmod(numerator << shift, denominator)
        divisor = denominator
    else:
        divisor = denominator << -shift
        quotient, remainder = divmod(numerator, divisor)
    return quotient + int(2 * remainder > divisor or
                          (2 * remainder == divisor and quotient % 2))


def encode_ratio(sign, numerator, denominator, shift, fmt):
    """Encode numerator / denominator * 2**shift with one nearest-even rounding."""
    exponent = numerator.bit_length() - denominator.bit_length() + shift
    if _less_than_power(numerator, denominator, shift, exponent):
        exponent -= 1
    significand = _round_scaled_ratio(
        numerator, denominator, shift + fmt.precision - 1 - exponent)
    if significand == 1 << fmt.precision:
        significand >>= 1
        exponent += 1
    if exponent < 1 - fmt.bias:
        return fmt.pack(sign, 0, 0), True
    if exponent > fmt.bias:
        return fmt.infinity(sign), False
    return fmt.pack(sign, exponent + fmt.bias, significand & fmt.fraction_mask), False


def calculate(bits, source, target):
    bits &= (1 << source.width) - 1
    sign, exponent, fraction = source.unpack(bits)
    flags = {name: False for name in FLAGS}
    if exponent == source.exponent_mask:
        if fraction:
            return target.quiet_nan(), flags
        return target.pack(sign, 0, 0), flags
    if exponent == 0:
        flags['divide_by_zero'] = True
        return target.infinity(sign), flags
    significand = (1 << source.fraction_bits) | fraction
    shift = source.fraction_bits - (exponent - source.bias)
    result, flags['underflow'] = encode_ratio(sign, 1, significand, shift, target)
    return result, flags


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
