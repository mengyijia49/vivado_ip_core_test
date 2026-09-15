from collections import Counter, deque

from vivado_ip_test.plugins.common.cycle import DefinedBits


class FwftFifoModel:
    def __init__(self, parameters):
        self.p = dict(parameters)
        self.capacity = self.p["depth"] + 2
        self.words = deque()
        self.cycle = -1
        self.event_counts = Counter()
        self.write_position = 0

    def _readable(self, cycle):
        return bool(self.words and self.words[0][1] + 2 <= cycle)

    def step(self, inputs):
        old_readable = self._readable(self.cycle)
        old_count = len(self.words)
        full = old_count == self.capacity
        self.cycle += 1
        overflow = bool(inputs["wr_en"] and full)
        underflow = bool(inputs["rd_en"] and not old_readable)
        read = write = False
        if inputs["srst"]:
            self.event_counts["reset"] += 1
            self.event_counts["reset_nonempty"] += int(old_count > 0)
            self.words.clear()
            self.write_position = 0
            data = self.p["dout_reset_value"]
        else:
            read = bool(inputs["rd_en"] and old_readable)
            write = bool(inputs["wr_en"] and not full)
            if read:
                self.words.popleft()
            if write:
                self.words.append((inputs["din"], self.cycle))
                self.write_position = (self.write_position + 1) % self.p["depth"]
                self.event_counts["write_wrap"] += int(self.write_position == 0)
            data = (self.words[0][0] if self._readable(self.cycle)
                    else DefinedBits(0, 0, "fwft_no_valid_output"))
        readable = self._readable(self.cycle)
        count = len(self.words)
        # PG057 tables 3-15..18: writes reach empty in two clocks,
        # almost_empty in one clock; reads update both flags immediately.
        almost_empty = count < 2 or self.words[1][1] + 1 > self.cycle
        for name, occurred in (("read", read), ("write", write), ("overflow", overflow),
                ("underflow", underflow), ("simultaneous_read_write", read and write),
                ("full_cycle", count == self.capacity), ("empty_cycle", not readable),
                ("fwft_waiting_for_first_word", count > 0 and not readable),
                ("fwft_output_hold", old_readable and not inputs["rd_en"] and not inputs["srst"]),
                ("fwft_extra_capacity", count > self.p["depth"])):
            self.event_counts[name] += int(occurred)
        low = int(self.p["active_low_flags"])
        return {"dout": data, "full": int(count == self.capacity), "empty": int(not readable),
                "almost_full": int(count >= self.capacity - 1), "almost_empty": int(almost_empty),
                "valid": int(readable) ^ low, "wr_ack": int(write) ^ low,
                "overflow": int(overflow) ^ low, "underflow": int(underflow) ^ low}


def fwft_prefix(width, depth):
    mask = (1 << width) - 1
    capacity = depth + 2
    yield {"srst": 1}
    yield {"rd_en": 1}
    for gap in range(5):
        yield {"wr_en": 1, "rd_en": 1, "din": (17 + gap) & mask}
        yield from ({} for _ in range(gap))
        yield from ({"rd_en": 1} for _ in range(5))
    for lap in range(2):
        for i in range(capacity):
            yield {"wr_en": 1, "din": ((i + 1) * 0x9E3779B1 + lap) & mask}
        yield from ({} for _ in range(5))
        yield from ({"wr_en": 1, "din": mask} for _ in range(2))
        for i in range(capacity * 2):
            yield {"wr_en": 1, "rd_en": 1, "din": (i + 7) & mask}
        yield from ({"rd_en": 1} for _ in range(capacity + 3))
    for control_sequence in range(4 ** 5):
        yield {"srst": 1}
        for position in range(5):
            control = (control_sequence >> (2 * position)) & 3
            yield {"wr_en": control & 1, "rd_en": control >> 1,
                   "din": (control_sequence * 7 + position) & mask}
        yield from ({"rd_en": 1} for _ in range(8))
    for delay in range(4):
        yield {"wr_en": 1, "din": mask}
        yield from ({} for _ in range(delay))
        yield {"srst": 1}
        yield from ({"rd_en": 1} for _ in range(4))
    yield from ({"wr_en": 1, "din": i & mask} for i in range(capacity))
    yield {"srst": 1, "wr_en": 1, "rd_en": 1}
