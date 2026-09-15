from dataclasses import replace
import hashlib
import random

from vivado_ip_test.services.stimulus_schedule import build_schedule


PACKET_LENGTHS = (1, 2, 3, 7, 16, 32)


def routing_prefix_groups(spec):
    packets = 7 * spec.branch_count
    if spec.parameters["arbitrate_last"]:
        return sum(PACKET_LENGTHS[i % len(PACKET_LENGTHS)] for i in range(packets))
    return packets * max(1, spec.parameters["arbitrate_transfers"])


def prepare_frames(samples, spec):
    numeric = spec.generated_ports
    zero = {p.name: 0 for p in numeric}
    rows = [zero, {p.name: p.limit for p in numeric}]
    for p in numeric:
        for bit in range(p.width):
            rows.extend(({**zero, p.name: 1 << bit}, {**zero, p.name: p.limit ^ (1 << bit)}))
    rows.extend(dict(row) for row in samples)
    quota = max(1, spec.parameters["arbitrate_transfers"])
    # Small numerical spaces still need contention and spread traffic on every route.
    rows.extend(dict(zero) for _ in range(max(0, routing_prefix_groups(spec)-len(rows))))
    if not spec.parameters["arbitrate_last"]:
        rows.extend(dict(zero) for _ in range((-len(rows)) % quota))
    frames = [{p.name: row.get(p.name, p.limit if p.name.endswith(("_tkeep", "_tstrb")) else 0)
               for p in spec.payload} for row in rows]
    for lane in range(spec.input_lane_count):
        prefix = f"s{lane:02d}_"
        remaining, packet, destination = 0, 0, 0
        for index, frame in enumerate(frames):
            if remaining == 0:
                length = PACKET_LENGTHS[packet % len(PACKET_LENGTHS)] if spec.parameters["arbitrate_last"] else quota
                remaining = min(length, len(frames)-index)
                branch = (packet // 4) % spec.branch_count if packet < 4 * spec.branch_count else (
                    packet + lane) % spec.branch_count
                low, high = spec.routes[branch]
                destination = (low, high, (low+high)//2)[packet % 3]
                packet += 1
            if prefix + "tdest" in frame:
                frame[prefix + "tdest"] = destination
            if prefix + "tlast" in frame:
                frame[prefix + "tlast"] = int(remaining == 1)
            key = prefix + spec.tag_field
            frame[key] = (frame[key] << spec.tag_bits) | lane
            remaining -= 1
    return frames


def source_schedules(count, profile, lanes):
    schedules = []
    for lane in range(lanes):
        seed = int.from_bytes(hashlib.sha256(f"switch-input:1.0:{profile.random_seed}:{lane}".encode()).digest()[:8], "big")
        schedule = build_schedule(count, replace(profile, random_seed=seed, input_order="generated"), can_idle=True)
        schedules.append(schedule)
    return schedules


def ready_matrix(profile, branches):
    rngs = [random.Random(f"switch-ready:1.0:{profile.random_seed}:{b}") for b in range(branches)]
    full = (1 << branches)-1
    rows = [0] * max(8, profile.max_gap_cycles) + [full] * profile.burst_length
    for branch in range(branches):
        rows += [1 << branch] * 8 + [full ^ (1 << branch)] * 8 + [full] * 8
    rows += [sum(rng.randrange(2) << b for b, rng in enumerate(rngs)) for _ in range(256)]
    rows += [full] * 32
    return [f"{bits:0{branches}b}" for bits in rows]
