from collections import Counter


PATTERNS = {"Zero", "Ones", "Alternating", "EdgeBits"}


def initial_value(pattern, width):
    if pattern == "Zero":
        return 0
    if pattern == "Ones":
        return (1 << width) - 1
    if pattern == "Alternating":
        return int("A5" * (width // 8), 16)
    if pattern == "EdgeBits":
        return (1 << (width - 1)) | 1
    raise ValueError(f"未知初始化图样：{pattern}")


class AxiMemoryInitReference:
    def __init__(self, parameters):
        self.p = dict(parameters)
        self.event_counts = Counter()

    @property
    def lanes(self):
        return self.p["data_width"] // 8

    @property
    def beat_count(self):
        return (1 << self.p["address_size"]) // self.lanes

    @property
    def burst_count(self):
        return self.beat_count // 16

    def burst_addresses(self):
        step = 16 * self.lanes
        addresses = [self.p["base_address"] + index * step
                     for index in range(self.burst_count)]
        self.event_counts["initialization_bursts"] += len(addresses)
        return addresses

    def output_rows(self):
        value = initial_value(self.p["init_pattern"], self.p["data_width"])
        strobe = (1 << self.lanes) - 1
        rows = [(value, strobe, int(index % 16 == 15))
                for index in range(self.beat_count)]
        post_value = value ^ ((1 << self.p["data_width"]) - 1)
        rows.append((post_value, strobe ^ 1, 1))
        self.event_counts["initialization_beats"] += self.beat_count
        self.event_counts["post_initialization_passthrough"] += 1
        return rows

