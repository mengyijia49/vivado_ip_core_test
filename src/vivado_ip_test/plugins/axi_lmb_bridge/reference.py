from collections import Counter


FAULTS = {"Normal": 0, "Address_Error": 1, "Uncorrectable_Error": 2}
BURSTS = {"Fixed": 0, "Increment": 1, "Wrap": 2}


def beat_data(base, beat, width):
    return (base ^ (beat * 0x101)) & ((1 << width) - 1)


def read_data(address, width):
    value = 0
    for lane in range(width // 8):
        value |= ((address + lane * 49) & 0xFF) << (lane * 8)
    return value


def burst_addresses(address, beats, size, burst, address_width):
    increment = 1 << size
    mask = (1 << address_width) - 1
    if burst == BURSTS["Fixed"]:
        return [address & mask] * beats
    if burst == BURSTS["Wrap"]:
        boundary = beats * increment
        base = address & ~(boundary - 1)
        return [base | ((address + beat * increment) & (boundary - 1))
                for beat in range(beats)]
    return [(address + beat * increment) & mask for beat in range(beats)]


class AxiLmbBridgeReference:
    def __init__(self, parameters):
        self.p = dict(parameters)
        self.event_counts = Counter()

    def evaluate(self, operations):
        accesses, outputs = [], []
        for operation in operations:
            addresses = burst_addresses(
                operation["address"], operation["beats"], operation["size"],
                operation["burst"], self.p["address_width"])
            response = 0 if operation["fault"] == FAULTS["Normal"] else 2
            protection_bit = operation["prot"] & 1
            protection = (protection_bit << 1) | (1 - protection_bit)
            if operation["kind"] == "write":
                for beat, address in enumerate(addresses):
                    strobe = operation["strobe"]
                    if strobe:
                        accesses.append({"address": address, "read": 0, "write": 1,
                            "data": beat_data(operation["data"], beat, self.p["data_width"]),
                            "be": strobe, "prot": protection})
                outputs.append({"kind": 0, "id": operation["id"], "data": 0,
                                "resp": response, "last": 0})
                self.event_counts[f"write_{operation['fault_name'].lower()}"] += 1
                if not operation["strobe"]:
                    self.event_counts["suppressed_zero_strobe"] += operation["beats"]
            else:
                for beat, address in enumerate(addresses):
                    accesses.append({"address": address, "read": 1, "write": 0,
                                     "data": 0, "be": 0, "prot": protection})
                    outputs.append({"kind": 1, "id": operation["id"],
                        "data": read_data(address, self.p["data_width"]),
                        "resp": response, "last": int(beat == operation["beats"] - 1)})
                self.event_counts[f"read_{operation['fault_name'].lower()}"] += 1
            self.event_counts[f"burst_{operation['burst_name'].lower()}"] += 1
            self.event_counts[f"beats_{operation['beats']}"] += 1
            if operation["wait_cycles"]:
                self.event_counts["waited_transactions"] += 1
            if operation["hold_cycles"]:
                self.event_counts["backpressured_responses"] += 1
            if operation.get("w_before_aw"):
                self.event_counts["w_before_aw"] += 1
        return accesses, outputs
