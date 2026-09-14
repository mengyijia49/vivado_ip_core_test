"""有限宽度整数的系统边界集合，与具体 IP 运算解耦。"""


def boundary_values(width: int, signed: bool) -> tuple[int, ...]:
    if width <= 0:
        raise ValueError("width must be positive")
    mask = (1 << width) - 1
    low, high = (-(1 << (width - 1)), (1 << (width - 1)) - 1) if signed else (0, mask)
    values = {low, low + 1, high - 1, high, -1, 0, 1}
    for bit in range(width):
        for delta in (-1, 0, 1):
            values.add((1 << bit) + delta)
            if signed:
                values.add(-(1 << bit) + delta)
    patterns = [mask ^ (1 << bit) for bit in range(width)]
    alternating = sum(1 << bit for bit in range(0, width, 2))
    patterns.extend((alternating, mask ^ alternating))
    for encoded in patterns:
        values.add(encoded - (1 << width) if signed and encoded > high else encoded)
    return tuple(sorted(value for value in values if low <= value <= high))
