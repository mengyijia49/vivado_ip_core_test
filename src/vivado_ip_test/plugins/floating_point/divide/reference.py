from vivado_ip_test.plugins.floating_point.formats import FloatFormat, sign_extend
from vivado_ip_test.plugins.floating_point.multi_input.sidebands import result_frame


def calculate(a, b, fmt):
    flags = {name: False for name in ('underflow', 'overflow', 'invalid_op', 'divide_by_zero')}
    sa, ea, fa = fmt.unpack(a)
    sb, eb, fb = fmt.unpack(b)
    sign = sa ^ sb
    ia, ib = ea == fmt.exponent_mask, eb == fmt.exponent_mask
    if ia and fa or ib and fb:
        return fmt.quiet_nan(), flags
    if ia and ib or ea == eb == 0:
        flags['invalid_op'] = True
        return fmt.quiet_nan(), flags
    if ia:
        return fmt.infinity(sign), flags
    if ib or ea == 0:
        return fmt.pack(sign, 0, 0), flags
    if eb == 0:
        flags['divide_by_zero'] = True
        return fmt.infinity(sign), flags
    numerator, denominator = (1 << fmt.fraction_bits) | fa, (1 << fmt.fraction_bits) | fb
    # Same-precision significands have a quotient in [0.5, 2); compare the exact remainder.
    below_one = numerator < denominator
    exponent = ea - eb - int(below_one)
    quotient, remainder = divmod(numerator << (fmt.fraction_bits + int(below_one)), denominator)
    significand = quotient + int(2 * remainder > denominator or (2 * remainder == denominator and quotient % 2))
    if significand == 1 << fmt.precision:
        significand >>= 1
        exponent += 1
    if exponent < 1 - fmt.bias:
        flags['underflow'] = True
        return fmt.pack(sign, 0, 0), flags
    if exponent > fmt.bias:
        flags['overflow'] = True
        return fmt.infinity(sign), flags
    return fmt.pack(sign, exponent + fmt.bias, significand & fmt.fraction_mask), flags


def expected_transactions(frames, p):
    fmt = FloatFormat(p['input_exponent'], p['input_fraction'])
    result = []
    for frame in frames:
        value, flags = calculate(frame['a_tdata'], frame['b_tdata'], fmt)
        result.append(result_frame(sign_extend(value, fmt.width), frame, p, flags))
    return result
