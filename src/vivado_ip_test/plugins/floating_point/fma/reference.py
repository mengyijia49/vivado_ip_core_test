from vivado_ip_test.plugins.floating_point.formats import FloatFormat, encode_float, sign_extend
from vivado_ip_test.plugins.floating_point.multi_input.sidebands import result_frame


def _finite(bits, fmt):
    sign, exponent, fraction = fmt.unpack(bits)
    if exponent == 0:
        return sign, 0, 0
    return sign, (1 << fmt.fraction_bits) | fraction, exponent - fmt.bias - fmt.fraction_bits


def calculate(a, b, c, fmt, opcode=0):
    if opcode & 63 not in (0, 1):
        raise ValueError('Reserved FMA opcode')
    flags = {'underflow': False, 'overflow': False, 'invalid_op': False}
    sa, ea, fa = fmt.unpack(a)
    sb, eb, fb = fmt.unpack(b)
    sc, ec, fc = fmt.unpack(c)
    sc ^= opcode & 1
    if ((ea == fmt.exponent_mask and fa) or (eb == fmt.exponent_mask and fb)
            or (ec == fmt.exponent_mask and fc)):
        return fmt.quiet_nan(), flags
    zero_a, zero_b = ea == 0, eb == 0
    inf_a, inf_b, inf_c = ea == fmt.exponent_mask, eb == fmt.exponent_mask, ec == fmt.exponent_mask
    product_sign = sa ^ sb
    if (inf_a and zero_b) or (inf_b and zero_a):
        flags['invalid_op'] = True
        return fmt.quiet_nan(), flags
    if inf_a or inf_b:
        if inf_c and sc != product_sign:
            flags['invalid_op'] = True
            return fmt.quiet_nan(), flags
        return fmt.infinity(product_sign), flags
    if inf_c:
        return fmt.infinity(sc), flags

    _, ma, xa = _finite(a, fmt)
    _, mb, xb = _finite(b, fmt)
    _, mc, xc = _finite(c, fmt)
    product = ma * mb
    if product and mc:
        product_shift = xa + xb
        shift = min(product_shift, xc)
        total = ((-1 if product_sign else 1) * (product << (product_shift - shift))
                 + (-1 if sc else 1) * (mc << (xc - shift)))
    elif product:
        shift = xa + xb
        total = (-1 if product_sign else 1) * product
    elif mc:
        shift = xc
        total = (-1 if sc else 1) * mc
    else:
        return fmt.pack(product_sign & sc, 0, 0), flags
    if not total:
        return fmt.pack(product_sign & sc, 0, 0), flags
    value, flags['underflow'], flags['overflow'] = encode_float(int(total < 0), abs(total), shift, fmt)
    return value, flags


def expected_transactions(frames, p):
    fmt = FloatFormat(p['input_exponent'], p['input_fraction'])
    result = []
    for frame in frames:
        value, flags = calculate(frame['a_tdata'], frame['b_tdata'], frame['c_tdata'], fmt,
                                 frame['operation_tdata'])
        result.append(result_frame(sign_extend(value, fmt.width), frame, p, flags))
    return result
