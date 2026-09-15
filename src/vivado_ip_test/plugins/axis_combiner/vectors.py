import random


def prepare_frames(frames, spec):
    base = {p.name: p.limit if p.name.endswith(("_tkeep", "_tstrb")) else 0 for p in spec.payload}
    prefix = [dict(base)]
    for port in spec.generated_ports:
        for bit in range(port.width):
            prefix.extend(({**base, port.name: 1 << bit}, {**base, port.name: port.limit ^ (1 << bit)}))
    for lane in range(spec.input_lane_count):
        row = dict(base)
        for port in spec.generated_ports:
            row[port.name] = port.limit if port.name.startswith(f"s{lane:02d}_") else 0
        prefix.append(row)
    rows = prefix + [{**base, **frame} for frame in frames]
    if any(p.name == "tlast" for p in spec.lane_payload):
        for index, row in enumerate(rows):
            for lane in range(spec.input_lane_count):
                row[f"s{lane:02d}_tlast"] = int((index + lane) % (lane + 2) == lane + 1 or index == len(rows) - 1)
    return rows


def lane_gaps(schedule, profile, lanes):
    rngs = [random.Random(f"combiner-inputs:1.0:{profile.random_seed}:{lane}") for lane in range(lanes)]
    rows = []
    for index, gap in enumerate(schedule.gaps):
        if profile.timing_mode == "continuous":
            rows.append([0] * lanes)
        elif index < 2 * lanes:
            # Exercise each lane as the only early input and as the last arrival.
            selected = index % lanes
            delay = max(8, profile.max_gap_cycles)
            rows.append([gap + (delay if (lane == selected) == (index < lanes) else 0)
                         for lane in range(lanes)])
        else:
            rows.append([gap + rng.randrange(profile.max_gap_cycles + 1) for rng in rngs])
    return rows
