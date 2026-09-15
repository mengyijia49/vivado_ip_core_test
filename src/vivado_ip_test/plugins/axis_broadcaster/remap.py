DATA_MAPPINGS = ("replicate", "rotate_bytes", "reverse_alternate", "split", "constant_tag")
USER_MAPPINGS = ("replicate", "rotate_bits", "split", "constant_tag")


def expression(name, input_width, output_width, mode, branch):
    if not output_width:
        return "1'b0"
    if mode == "constant_tag":
        value = (int.from_bytes(bytes([branch + 1]) * (output_width // 8), "little")
                 if name == "tdata" else branch + 1)
        return f"{output_width}'b{value & ((1 << output_width) - 1):0{output_width}b}"
    indices = list(range(input_width))
    if mode == "split":
        indices = indices[branch * output_width:(branch + 1) * output_width]
    elif mode in {"rotate_bytes", "rotate_bits"}:
        shift = (branch * (8 if mode == "rotate_bytes" else 1)) % input_width
        indices = indices[shift:] + indices[:shift]
    elif mode == "reverse_alternate" and branch % 2:
        indices = [bit for byte in reversed(range(input_width // 8))
                   for bit in range(byte * 8, byte * 8 + 8)]
    indices = (indices[:output_width] + [None] * output_width)[:output_width]
    # Coalesce adjacent bits to keep wide XCI parameters readable.
    parts, offset = [], output_width - 1
    while offset >= 0:
        high = indices[offset]
        end = offset
        while end > 0 and ((high is None and indices[end - 1] is None) or
                (high is not None and indices[end - 1] == high - (offset - end + 1))):
            end -= 1
        width = offset - end + 1
        parts.append(f"{width}'b" + "0" * width if high is None else
                     f"{name}[{high}]" if width == 1 else f"{name}[{high}:{indices[end]}]")
        offset = end - 1
    return ",".join(parts)
