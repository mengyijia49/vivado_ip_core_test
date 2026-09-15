from math import isqrt

from vivado_ip_test.plugins.floating_point.formats import encode_float


def normal_square_root(exponent, fraction, fmt):
    magnitude = (1 << fmt.fraction_bits) | fraction
    scale = exponent - fmt.bias - fmt.fraction_bits
    result_exponent = (magnitude.bit_length() - 1 + scale) // 2
    shift = scale + 2 * (fmt.fraction_bits - result_exponent)
    numerator = magnitude << max(0, shift)
    denominator = 1 << max(0, -shift)
    lower = isqrt(numerator // denominator)
    # Compare the exact radicand with the squared rounding midpoint.
    midpoint_squared = denominator * (2 * lower + 1) ** 2
    significand = lower + int(4 * numerator > midpoint_squared or
                             (4 * numerator == midpoint_squared and lower % 2))
    if significand == 1 << fmt.precision:
        significand >>= 1
        result_exponent += 1
    return fmt.pack(0, result_exponent + fmt.bias, significand & fmt.fraction_mask)


def square_boundaries(fmt):
    first, last = (1 - fmt.bias) // 2, fmt.bias // 2
    exponents = {first, first + 1, first + 2, last - 2, last - 1, last, -3, -2, -1, 0, 1, 2, 3}
    base = 1 << fmt.fraction_bits
    significands = {base, base + 1, base + 2, 2 * base - 2, 2 * base - 1}
    for bit in range(fmt.fraction_bits):
        significands.update(base + (1 << bit) + offset for offset in (-1, 0, 1))
    values = set()
    for exponent in sorted(exponents):
        for significand in sorted(significands):
            for midpoint in (False, True):
                m = 2 * significand + 1 if midpoint else significand
                shift = 2 * (exponent - fmt.fraction_bits - int(midpoint))
                encoded, underflow, overflow = encode_float(0, m * m, shift, fmt)
                if underflow or overflow:
                    continue
                for offset in (-2, -1, 0, 1, 2):
                    bits = encoded + offset
                    if 0 <= bits < fmt.infinity(0):
                        values.add(bits)
                        values.add(bits | (1 << (fmt.width - 1)))
    return values
