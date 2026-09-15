from collections import Counter, deque

from vivado_ip_test.plugins.common.cycle import DefinedBits


class FifoModel:
    def __init__(self, p):
        self.p = p
        self.words = deque()
        self.event_counts = Counter()
        self.write_position = 0

    def step(self, inputs):
        p = self.p
        old_count = len(self.words)
        full, empty = old_count == p["depth"], old_count == 0
        # PG057 synchronous-reset notes keep these flags dependent on the requests.
        overflow = bool(inputs["wr_en"] and full)
        underflow = bool(inputs["rd_en"] and empty)
        if inputs["srst"]:
            self.event_counts["reset"] += 1
            self.event_counts["reset_nonempty"] += int(old_count > 0)
            self.words.clear()
            self.write_position = 0
            data = p["dout_reset_value"]
            read = write = False
        else:
            read = bool(inputs["rd_en"] and not empty)
            write = bool(inputs["wr_en"] and not full)
            data = self.words.popleft() if read else DefinedBits(0, 0, "no_valid_read")
            if write:
                self.words.append(inputs["din"])
                self.write_position = (self.write_position + 1) % p["depth"]
                self.event_counts["write_wrap"] += int(self.write_position == 0)
        for name, occurred in (("read", read), ("write", write), ("overflow", overflow),
            ("underflow", underflow), ("simultaneous_read_write", read and write)):
            self.event_counts[name] += int(occurred)
        count = len(self.words)
        self.event_counts["full_cycle"] += int(count == p["depth"])
        self.event_counts["empty_cycle"] += int(count == 0)
        low = int(p["active_low_flags"])
        return {"dout": data, "full": int(count == p["depth"]), "empty": int(count == 0),
                "almost_full": int(count >= p["depth"] - 1), "almost_empty": int(count <= 1),
                "valid": int(read) ^ low, "wr_ack": int(write) ^ low,
                "overflow": int(overflow) ^ low, "underflow": int(underflow) ^ low}
