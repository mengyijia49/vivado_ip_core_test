from dataclasses import dataclass


@dataclass(frozen=True)
class FloatFormat:
    exponent: int
    precision: int

    @property
    def width(self):
        return self.exponent + self.precision

    @property
    def fraction_bits(self):
        return self.precision - 1

    @property
    def bias(self):
        return (1 << (self.exponent - 1)) - 1

    @property
    def exponent_mask(self):
        return (1 << self.exponent) - 1

    @property
    def fraction_mask(self):
        return (1 << self.fraction_bits) - 1

    def pack(self, sign, exponent, fraction):
        return (sign << (self.width - 1)) | (exponent << self.fraction_bits) | fraction

    def unpack(self, bits):
        return (bits >> (self.width - 1)) & 1, (bits >> self.fraction_bits) & self.exponent_mask, bits & self.fraction_mask

    def infinity(self, sign):
        return self.pack(sign, self.exponent_mask, 0)

    def quiet_nan(self):
        return self.pack(0, self.exponent_mask, 1 << (self.fraction_bits - 1))


def round_binary(magnitude, shift):
    """Round magnitude * 2**shift to the nearest integer, ties to even."""
    if shift >= 0:
        return magnitude << shift
    divisor = 1 << -shift
    quotient, remainder = divmod(magnitude, divisor)
    return quotient + int(2 * remainder > divisor or (2 * remainder == divisor and quotient % 2))


def encode_float(sign, magnitude, shift, fmt):
    if not magnitude:
        return fmt.pack(sign, 0, 0), False, False
    exponent = magnitude.bit_length() - 1 + shift
    significand = round_binary(magnitude, fmt.precision - magnitude.bit_length())
    if significand == 1 << fmt.precision:
        significand >>= 1
        exponent += 1
    # PG060's main UNDERFLOW rule detects tininess after significand rounding.
    if exponent < 1 - fmt.bias:
        return fmt.pack(sign, 0, 0), True, False
    if exponent > fmt.bias:
        return fmt.infinity(sign), False, True
    return fmt.pack(sign, exponent + fmt.bias, significand & fmt.fraction_mask), False, False


def sign_extend(value, width):
    wire_width = ((width + 7) // 8) * 8
    return value | ((1 << wire_width) - (1 << width)) if value & (1 << (width - 1)) else value
