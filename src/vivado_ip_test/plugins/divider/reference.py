from dataclasses import dataclass


@dataclass(frozen=True)
class DivisionResult:
    quotient: int
    remainder: int


def truncating_division(dividend: int, divisor: int) -> DivisionResult:
    if divisor == 0:
        raise ZeroDivisionError("Divider 参考模型不接受零除数")

    magnitude = abs(dividend) // abs(divisor)
    quotient = -magnitude if (dividend < 0) != (divisor < 0) else magnitude
    remainder = dividend - quotient * divisor
    return DivisionResult(quotient=quotient, remainder=remainder)


def encode_fixed_width(value: int, width: int) -> int:
    return value & ((1 << width) - 1)


def pack_remainder_output(
    result: DivisionResult,
    quotient_width: int,
    remainder_width: int,
) -> int:
    quotient = encode_fixed_width(result.quotient, quotient_width)
    remainder = encode_fixed_width(result.remainder, remainder_width)
    return (quotient << remainder_width) | remainder
