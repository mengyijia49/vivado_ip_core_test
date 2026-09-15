import random


def prepare_frames(frames, spec):
    base = {p.name: p.limit if p.name in {"tkeep", "tstrb"} else 0 for p in spec.payload}
    prefix = [dict(base)]
    for port in spec.generated_ports:
        for bit in range(port.width):
            prefix.extend(({**base, port.name: 1 << bit}, {**base, port.name: port.limit ^ (1 << bit)}))
    while len(prefix) < 8 * spec.branch_count:
        prefix.append({**base, **{p.name: len(prefix) & p.limit for p in spec.generated_ports}})
    if "tlast" in base:
        for index, frame in enumerate(prefix):
            frame["tlast"] = int(index % 7 == 6 or index == len(prefix) - 1)
    return prefix + [dict(frame) for frame in frames]


def ready_matrix(profile, branches):
    rows = []
    stall = max(8, profile.max_gap_cycles + 2) * 2
    for solo in (False, True):
        for branch in range(branches):
            value = (1 << branch) if solo else ((1 << branches) - 1) ^ (1 << branch)
            rows.extend([value] * stall + [(1 << branches) - 1] * profile.burst_length)
    rngs = [random.Random(f"broadcaster-ready:1.0:{profile.random_seed}:{i}") for i in range(branches)]
    rows.extend(sum(rng.randrange(2) << i for i, rng in enumerate(rngs)) for _ in range(512))
    rows.extend([(1 << branches) - 1] * 32)
    return [f"{value:0{branches}b}" for value in rows]
