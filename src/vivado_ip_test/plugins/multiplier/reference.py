def encode_fixed_width(value: int, width: int) -> int:
    if width <= 0:
        raise ValueError("位宽必须是正整数")
    return value & ((1 << width) - 1)


def multiply(a: int, b: int) -> int:
    return a * b
