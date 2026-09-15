from vivado_ip_test.plugins.axis_subset_converter.remap import evaluate, parse_remap


def expected_transactions(frames, parameters, source, sink):
    source_widths = {p.name: p.width for p in source}
    output = {p.name: p for p in sink}
    custom = {name: parse_remap(expression, source_widths, output[name].width)
              for name, expression in parameters.get("remap", {}).items()}
    result = []
    for index, frame in enumerate(frames):
        row = {name: frame.get(name, p.limit if name in {"tkeep", "tstrb"} else 0) & p.limit
               for name, p in output.items()}
        # Qualifier extension inserts ones, unlike numeric zero extension.
        for name in ("tkeep", "tstrb"):
            if name in output:
                origin = "tkeep" if name == "tstrb" and name not in frame and "tkeep" in frame else name
                if origin in frame:
                    source_mask = (1 << source_widths[origin]) - 1
                    row[name] = (frame[origin] | ~source_mask) & output[name].limit
        mode = parameters["mapping"]
        if "tdata" in output:
            value = frame.get("tdata", 0)
            n = parameters["input_bytes"]
            if mode in {"user_to_data", "data_user_swap"}:
                value = frame["tuser"]
            elif mode == "reverse_bytes":
                value = int.from_bytes(value.to_bytes(n, "little"), "big")
            elif mode == "reverse_bits":
                value = int(f"{value:0{8 * n}b}"[::-1], 2)
            elif mode == "rotate_bytes":
                value = ((value << 8) | (value >> (8 * n - 8))) & ((1 << (8 * n)) - 1)
            elif mode == "repeat_low_byte":
                value = int.from_bytes(bytes([value & 255]) * parameters["output_bytes"], "little")
            row["tdata"] = value & output["tdata"].limit
        if mode == "data_user_swap":
            row["tuser"] = frame["tdata"] & output["tuser"].limit
        for name, parts in custom.items():
            row[name] = evaluate(parts, frame)
        period = parameters["last_period"]
        if period:
            row["tlast"] = int((index + 1) % period == 0)
        if "tkeep" in row and "tstrb" in row and row["tstrb"] & ~row["tkeep"]:
            raise ValueError("配置的映射会产生保留 TKEEP/TSTRB 组合，不能作为合法协议测试")
        result.append(row)
    return result
