def count_for_report(value: int) -> int | str:
    """保留精确数量；超大计数用十六进制，不关闭 Python 的转换保护。"""
    if type(value) is not int or value < 0:
        raise ValueError("计数必须是非负整数")
    return value if value.bit_length() <= 13000 else hex(value)
