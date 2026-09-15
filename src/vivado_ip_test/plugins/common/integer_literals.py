import re


def parse_unsigned_literal(literal):
    if not isinstance(literal, str):
        raise ValueError("Constant value must be a literal string")
    if re.fullmatch(r"0[xX][0-9a-fA-F]+", literal):
        return int(literal[2:], 16)
    if re.fullmatch(r"b[01]+", literal):
        return int(literal[1:], 2)
    if re.fullmatch(r"0[0-7]+", literal):
        return int(literal, 8)
    if re.fullmatch(r"0|[1-9][0-9]*", literal):
        return int(literal, 10)
    raise ValueError("Expected an unsigned decimal, b-prefixed binary, leading-0 octal or 0x hexadecimal literal")
