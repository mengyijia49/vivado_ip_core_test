def prepare_frames(frames, spec, period):
    base = {p.name: p.limit if p.name in {"tkeep", "tstrb"} else 0 for p in spec.payload}
    prefix = [dict(base)]
    for port in spec.generated_ports:
        for bit in range(port.width):
            prefix.append({**base, port.name: 1 << bit})
            prefix.append({**base, port.name: port.limit ^ (1 << bit)})
    if "tlast" in base:
        for index, row in enumerate(prefix):
            row["tlast"] = int(index % 7 == 6)
    if period:
        # Exercise at least two counter wraps even for a one-byte input space.
        for index in range(max(0, 2 * period + 3 - len(prefix) - len(frames))):
            prefix.append({**base, **{p.name: index & p.limit for p in spec.generated_ports}})
    return prefix + frames
