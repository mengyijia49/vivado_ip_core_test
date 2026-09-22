from decimal import Decimal, localcontext

from vivado_ip_test.plugins.floating_point.formats import FloatFormat, sign_extend
from vivado_ip_test.plugins.floating_point.reciprocal.reference import encode_ratio
from vivado_ip_test.plugins.floating_point.transcendental.spec import OPERATION_FLAGS


def _normal_decimal(sign, exponent, fraction, fmt, precision):
    significand = (1 << fmt.fraction_bits) | fraction
    shift = exponent - fmt.bias - fmt.fraction_bits
    with localcontext() as context:
        context.prec = precision
        value = Decimal(significand) * (Decimal(2) ** shift)
        return -value if sign else value


def _encode_decimal(value, fmt):
    sign = int(value.is_signed())
    if value.is_zero():
        return fmt.pack(sign, 0, 0), False, False
    numerator, denominator = abs(value).as_integer_ratio()
    encoded, underflow = encode_ratio(sign, numerator, denominator, 0, fmt)
    _, exponent, _ = fmt.unpack(encoded)
    return encoded, underflow, exponent == fmt.exponent_mask


def _evaluate(operation, sign, exponent, fraction, source, target, precision):
    value = _normal_decimal(sign, exponent, fraction, source, precision)
    with localcontext() as context:
        context.prec = precision
        context.Emax = 999999
        context.Emin = -999999
        if operation == 'Exponential':
            maximum = Decimal((1 << target.precision) - 1) * (
                Decimal(2) ** (target.bias - target.fraction_bits))
            minimum = Decimal(2) ** (1 - target.bias)
            maximum_log = maximum.ln()
            minimum_log = minimum.ln()
            if value > maximum_log + 2:
                return target.infinity(0), False, True
            if value < minimum_log - 2:
                return target.pack(0, 0, 0), True, False
            result = value.exp()
        else:
            result = value.ln()
    return _encode_decimal(result, target)


def calculate(bits, operation, source, target):
    bits &= (1 << source.width) - 1
    sign, exponent, fraction = source.unpack(bits)
    flags = {name: False for name in OPERATION_FLAGS[operation]}
    if exponent == source.exponent_mask:
        if fraction:
            return target.quiet_nan(), flags
        if operation == 'Exponential':
            return (target.pack(0, 0, 0) if sign else target.infinity(0)), flags
        if sign:
            flags['invalid_op'] = True
            return target.quiet_nan(), flags
        return target.infinity(0), flags
    if exponent == 0:
        if operation == 'Exponential':
            return target.pack(0, target.bias, 0), flags
        flags['divide_by_zero'] = True
        return target.infinity(1), flags
    if operation == 'Logarithm' and sign:
        flags['invalid_op'] = True
        return target.quiet_nan(), flags

    low = _evaluate(operation, sign, exponent, fraction, source, target, 180)
    high = _evaluate(operation, sign, exponent, fraction, source, target, 260)
    if low != high:
        raise ArithmeticError('Transcendental reference did not stabilize')
    value, underflow, overflow = high
    if operation == 'Exponential':
        flags['underflow'] = underflow
        flags['overflow'] = overflow
    return value, flags


def expected_transactions(frames, p):
    source = FloatFormat(p['input_exponent'], p['input_fraction'])
    target = FloatFormat(p['output_exponent'], p['output_fraction'])
    selected = [name for name in OPERATION_FLAGS[p['operation']] if p['has_' + name]]
    result = []
    for frame in frames:
        value, flags = calculate(frame['tdata'], p['operation'], source, target)
        output = {'tdata': sign_extend(value, target.width)}
        if p['has_last']:
            output['tlast'] = frame['tlast']
        if p['user_width'] or selected:
            output['tuser'] = frame.get('tuser', 0) << len(selected)
            output['tuser'] |= sum(int(flags[name]) << index
                                   for index, name in enumerate(selected))
        result.append(output)
    return result
