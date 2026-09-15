from vivado_ip_test.plugins.floating_point.formats import FloatFormat, encode_float, sign_extend
from vivado_ip_test.plugins.floating_point.multi_input.sidebands import result_frame


def calculate(a, b, fmt, operation, opcode=0):
    if operation not in {'Add', 'Subtract', 'Both', 'Multiply'}:
        raise ValueError('Unsupported floating point arithmetic operation')
    if operation == 'Both':
        if opcode & 63 not in (0, 1):
            raise ValueError('Reserved add/subtract opcode')
        operation = 'Subtract' if opcode & 1 else 'Add'
    flags = {'underflow': False, 'overflow': False, 'invalid_op': False}
    sa, ea, fa = fmt.unpack(a)
    sb, eb, fb = fmt.unpack(b)
    if ea == fmt.exponent_mask and fa or eb == fmt.exponent_mask and fb:
        return fmt.quiet_nan(), flags
    sb ^= int(operation == 'Subtract')
    ia, ib = ea == fmt.exponent_mask, eb == fmt.exponent_mask
    if operation == 'Multiply':
        sign = sa ^ sb
        if ia and eb == 0 or ib and ea == 0:
            flags['invalid_op'] = True
            return fmt.quiet_nan(), flags
        if ia or ib:
            return fmt.infinity(sign), flags
        if ea == 0 or eb == 0:
            return fmt.pack(sign, 0, 0), flags
        magnitude = ((1 << fmt.fraction_bits) | fa) * ((1 << fmt.fraction_bits) | fb)
        shift = ea + eb - 2 * (fmt.bias + fmt.fraction_bits)
    else:
        if ia and ib and sa != sb:
            flags['invalid_op'] = True
            return fmt.quiet_nan(), flags
        if ia or ib:
            return fmt.infinity(sa if ia else sb), flags
        ma, mb = ((1 << fmt.fraction_bits) | fa) if ea else 0, ((1 << fmt.fraction_bits) | fb) if eb else 0
        xa, xb = (ea - fmt.bias - fmt.fraction_bits) if ea else 0, (eb - fmt.bias - fmt.fraction_bits) if eb else 0
        # Align exact integers first; no intermediate floating point rounding.
        shift = min(xa, xb)
        total = (-1 if sa else 1) * (ma << (xa - shift)) + (-1 if sb else 1) * (mb << (xb - shift))
        sign, magnitude = int(total < 0), abs(total)
        if not magnitude:
            return fmt.pack(sa & sb, 0, 0), flags
    value, flags['underflow'], flags['overflow'] = encode_float(sign, magnitude, shift, fmt)
    return value, flags


def expected_transactions(frames, p):
    fmt = FloatFormat(p['input_exponent'], p['input_fraction'])
    operation = p['add_sub_value'] if p['operation'] == 'Add_Subtract' else 'Multiply'
    result = []
    for frame in frames:
        value, flags = calculate(frame['a_tdata'], frame['b_tdata'], fmt, operation, frame.get('operation_tdata', 0))
        result.append(result_frame(sign_extend(value, fmt.width), frame, p, flags))
    return result
