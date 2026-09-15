def with_hex_large_integers(value):
    """Keep small JSON integers unchanged and encode wide values without decimal conversion."""
    if type(value) is int:
        return hex(value) if value.bit_length() > 13000 else value
    if isinstance(value, dict):
        return {key: with_hex_large_integers(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [with_hex_large_integers(item) for item in value]
    return value
