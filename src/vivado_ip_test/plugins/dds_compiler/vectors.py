def directed_sequence(latency=4):
    cycles = []

    def add(count, resetn, ready):
        cycles.extend({"aresetn": resetn, "m_axis_phase_tready": ready}
                      for _ in range(count))

    add(2, 0, 0)
    add(2, 0, 1)
    add(latency + 12, 1, 1)
    add(7, 1, 0)
    add(12, 1, 1)
    add(2, 0, 0)
    add(latency + 3, 1, 0)
    add(8, 1, 1)
    return tuple(cycles)
