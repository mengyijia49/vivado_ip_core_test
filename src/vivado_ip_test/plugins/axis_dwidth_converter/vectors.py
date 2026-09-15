from math import gcd


def prepare_frames(generated, p, spec):
    n = p["input_bytes"]
    full = (1 << n) - 1
    group = p["output_bytes"] // gcd(n, p["output_bytes"])
    user_mask = (1 << p["user_bits_per_byte"]) - 1
    widths = {port.name: port.limit for port in spec.payload}
    frames = []

    def frame(index, keep=full, *, last=0, position=False, packet=0):
        row = {name: 0 for name in widths}
        row["tdata"] = sum(((index * 17 + lane * 29) & 255) << (8 * lane) for lane in range(n))
        if "tuser" in row:
            row["tuser"] = sum(((index + 3 * lane) & user_mask) << (p["user_bits_per_byte"] * lane)
                               for lane in range(n))
        for name in ("tid", "tdest"):
            if name in row:
                row[name] = packet & widths[name]
        if "tkeep" in row:
            row["tkeep"] = keep
        if "tstrb" in row:
            row["tstrb"] = 0 if position else keep
        if "tlast" in row:
            row["tlast"] = last
        return row

    lengths = dict.fromkeys((1, max(1, group - 1), group, group + 1, 2 * group - 1, 2 * group + 1))
    for packet, length in enumerate(lengths):
        for index in range(length):
            frames.append(frame(len(frames), last=int(index == length - 1), packet=packet))
    if p["has_last"]:
        for lane in range(n):
            keep = 1 << lane if p["has_keep"] else full
            for position in ((False, True) if p["has_strb"] else (False,)):
                frames.append(frame(len(frames), keep, last=1, position=position))
        if p["has_keep"]:
            frames += [frame(len(frames), 0, last=last) for last in (0, 1, 1)]
    patterns = (full, 0, 1, 1 << (n - 1), sum(1 << i for i in range(0, n, 2)))
    for index, raw in enumerate(generated):
        keep = patterns[index % len(patterns)] if p["has_keep"] and p["has_last"] else full
        row = frame(index, keep, last=int(index % (group + 1) == group))
        row.update(raw)
        if "tstrb" in row and p["has_last"]:
            row["tstrb"] = keep & patterns[(index // len(patterns)) % len(patterns)]
        frames.append(row)
    if p["has_last"]:
        frames[-1]["tlast"] = 1
    else:
        # With no end-of-packet signal, finish the last same-ID group explicitly.
        names = [name for name in ("tid", "tdest") if name in widths]
        last_id = tuple(frames[-1][name] for name in names)
        count = 0
        for row in reversed(frames):
            if tuple(row[name] for name in names) != last_id:
                break
            count += 1
        for _ in range((-count) % group):
            row = frame(len(frames))
            row.update(dict(zip(names, last_id)))
            frames.append(row)
    return frames
