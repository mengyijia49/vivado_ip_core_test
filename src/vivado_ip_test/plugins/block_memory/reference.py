from collections import Counter

from vivado_ip_test.plugins.common.cycle import DefinedBits


class BlockMemoryModel:
    def __init__(self, p):
        self.p = p
        self.limit = (1 << p["width"]) - 1
        self.memory = [(p["initial_value"], self.limit)] * p["depth"]
        self.readers = ("a",) if p["memory_type"] == "Single_Port_RAM" else (
            ("b",) if p["memory_type"] == "Simple_Dual_Port_RAM" else ("a", "b"))
        self.writers = ("a", "b") if p["memory_type"] == "True_Dual_Port_RAM" else ("a",)
        unknown = DefinedBits(0, 0, "power_up_output_unspecified")
        self.latch = {port: unknown for port in self.readers}
        self.register = dict(self.latch)
        self.event_counts = Counter()

    def write_mask(self, enable):
        if not self.p["byte_size"]:
            return self.limit if enable else 0
        size = self.p["byte_size"]
        return sum(((1 << size) - 1) << (lane * size)
                   for lane in range(self.p["width"] // size) if enable & (1 << lane))

    def step(self, inputs):
        p = self.p
        writes = {port: self.write_mask(inputs[f"we{port}"]) if inputs[f"en{port}"] else 0
                  for port in self.writers}
        old = {port: self.memory[inputs[f"addr{port}"]] for port in set(self.readers + self.writers)}
        collision = (len(self.writers) == 2 and inputs["addra"] == inputs["addrb"])
        overlap = writes["a"] & writes["b"] if collision else 0
        if collision and writes["a"] and writes["b"]:
            self.event_counts["overlapping_dual_write" if overlap else "disjoint_dual_write"] += 1
        for port, mask in writes.items():
            self.event_counts[f"{port}_write"] += int(bool(mask))
            address = inputs[f"addr{port}"]
            value, known = self.memory[address]
            self.memory[address] = ((value & ~mask) | (inputs[f"din{port}"] & mask),
                                    (known | mask) & ~overlap)
        result = {}
        for port in self.readers:
            enabled = inputs[f"en{port}"]
            reset = inputs.get(f"rst{port}", 0)
            previous_latch = self.latch[port]
            own_write = writes.get(port, 0)
            self.event_counts[f"{port}_read"] += int(bool(enabled and not own_write))
            self.event_counts[f"{port}_enable_hold"] += int(not enabled)
            mode = p[f"write_mode_{port}"]
            holding = own_write and mode == "NO_CHANGE"
            if enabled and not holding:
                value, known = old[port]
                reason = "previous_write_collision"
                if own_write and mode == "WRITE_FIRST":
                    value, known = self.memory[inputs[f"addr{port}"]]
                    if p["byte_size"]:
                        known, reason = 0, "byte_write_first_output_unspecified"
                for other, mask in writes.items():
                    if other != port and mask and inputs[f"addr{other}"] == inputs[f"addr{port}"]:
                        self.event_counts["cross_port_same_address_access"] += 1
                        if p[f"write_mode_{other}"] != "READ_FIRST":
                            known &= ~mask
                            reason = "cross_port_write_read_collision"
                        known &= ~overlap
                self.latch[port] = DefinedBits(value, known, reason)
            if enabled and reset and (not p["output_register"] or p["reset_memory_latch"]):
                self.event_counts[f"{port}_latch_reset"] += 1
                self.latch[port] = DefinedBits(p["output_reset_value"], self.limit, "output_reset")
            if p["output_register"] and inputs.get(f"regce{port}", enabled):
                self.event_counts[f"{port}_register_reset"] += int(bool(reset))
                self.register[port] = (DefinedBits(p["output_reset_value"], self.limit, "output_reset")
                                       if reset else previous_latch)
            output = self.register[port] if p["output_register"] else self.latch[port]
            result[f"dout{port}"] = output.value if output.mask == self.limit else output
        return result
