def mapped_value(value, input_width, output_width, mode, branch, *, data):
    if mode == "split":
        value >>= branch * output_width
    elif mode == "rotate_bytes":
        raw = value.to_bytes(input_width // 8, "little")
        shift = branch % len(raw)
        value = int.from_bytes(raw[shift:] + raw[:shift], "little")
    elif mode == "rotate_bits":
        shift = branch % input_width
        value = ((value >> shift) | (value << (input_width - shift))) & ((1 << input_width) - 1)
    elif mode == "reverse_alternate" and branch % 2:
        value = int.from_bytes(value.to_bytes(input_width // 8, "little"), "big")
    elif mode == "constant_tag":
        value = sum((branch + 1) << bit for bit in range(0, output_width, 8)) if data else branch + 1
    return value & ((1 << output_width) - 1)


def expected_transactions(frames, parameters, spec):
    result = []
    for frame in frames:
        combined = {}
        for branch in range(spec.branch_count):
            for port in spec.branch_payload:
                value = frame[port.name]
                if port.name in {"tdata", "tuser"}:
                    data = port.name == "tdata"
                    width = parameters["input_bytes"] * 8 if data else parameters["input_user_width"]
                    mode = parameters["data_mapping" if data else "user_mapping"]
                    value = mapped_value(value, width, port.width, mode, branch, data=data)
                combined[f"m{branch:02d}_{port.name}"] = value
        result.append(combined)
    return result
