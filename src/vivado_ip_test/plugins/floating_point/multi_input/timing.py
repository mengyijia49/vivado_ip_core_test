import random


def independent_gaps(schedule, profile, lanes):
    rngs = [random.Random(f'floating-compare-inputs:1.0:{profile.random_seed}:{lane}') for lane in range(lanes)]
    rows = []
    for index, gap in enumerate(schedule.gaps):
        if profile.timing_mode == 'continuous':
            rows.append([0] * lanes)
            continue
        row = [gap + rng.randrange(profile.max_gap_cycles + 1) for rng in rngs]
        if index % 32 == 0:
            row[(index // 32) % lanes] += max(32, profile.max_gap_cycles)
        rows.append(row)
    return rows
