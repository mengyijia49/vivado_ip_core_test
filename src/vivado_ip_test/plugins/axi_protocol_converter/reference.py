from collections import Counter


BURSTS = {"Fixed": 0, "Increment": 1, "Wrap": 2}
RESPONSES = {"Okay": 0, "Slave_Error": 2, "Decode_Error": 3}


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


class AxiProtocolConverterReference:
    def __init__(self, parameters):
        self.p = dict(parameters)
        self.event_counts = Counter()

    def evaluate(self, operations):
        accesses, outputs = [], []
        for operation in operations:
            addresses = burst_addresses(operation["address"], operation["beats"],
                                        operation["size"], operation["burst"],
                                        self.p["address_width"])
            if operation["kind"] == "write":
                for beat, address in enumerate(addresses):
                    response = (operation["response"]
                                if beat == operation["error_beat"] else 0)
                    accesses.append({"kind": 0, "address": address,
                        "data": beat_data(operation["data"], beat, self.p["data_width"]),
                        "strobe": operation["strobe"], "prot": operation["prot"],
                        "response": response})
                outputs.append({"kind": 0, "id": operation["id"], "data": 0,
                    "response": operation["response"] if operation["error_beat"] >= 0 else 0,
                    "last": 0})
            else:
                for beat, address in enumerate(addresses):
                    response = (operation["response"]
                                if beat == operation["error_beat"] else 0)
                    data = read_data(address, self.p["data_width"])
                    accesses.append({"kind": 1, "address": address, "data": data,
                        "strobe": 0, "prot": operation["prot"], "response": response})
                    outputs.append({"kind": 1, "id": operation["id"], "data": data,
                        "response": response, "last": int(beat == operation["beats"] - 1)})
            self.event_counts[f"{operation['kind']}_{operation['burst_name'].lower()}"] += 1
            self.event_counts[f"beats_{operation['beats']}"] += 1
            if operation["error_beat"] >= 0:
                self.event_counts[f"response_{operation['response_name'].lower()}"] += 1
            if operation["hold_cycles"]:
                self.event_counts["upstream_backpressure"] += 1
            if operation.get("w_before_aw"):
                self.event_counts["w_before_aw"] += 1
        return accesses, outputs
