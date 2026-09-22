from collections import Counter

from vivado_ip_test.plugins.common.axilite.spec import Action
from vivado_ip_test.plugins.common.cycle import DefinedBits


def merge_bytes(previous, value, strobe):
    result = previous
    for lane in range(4):
        if strobe >> lane & 1:
            mask = 0xFF << (8 * lane)
            result = (result & ~mask) | (value & mask)
    return result


class AxiBramModel:
    def __init__(self, parameters):
        self.depth = parameters["depth"]
        self.memory = {}
        self.event_counts = Counter()

    def read(self, address):
        return self.memory.get(address // 4, 0)

    def write(self, address, value, strobe):
        index = address // 4
        updated = merge_bytes(self.memory.get(index, 0), value, strobe)
        if updated:
            self.memory[index] = updated
        else:
            self.memory.pop(index, None)

    def step(self, command):
        action = Action(command["action"])
        if action == Action.WRITE:
            self.write(command["address"], command["data"], command["strobe"])
            self.event_counts[f"write_strobe_{command['strobe']:x}"] += 1
        elif action == Action.READ:
            self.event_counts["read"] += 1
        elif action == Action.RESET:
            # AXI reset clears controller state, not the contents of the internal BRAM.
            self.event_counts["reset"] += 1
        self.event_counts[action.name.lower() + "_operations"] += 1
        return {
            "response": 0 if action in (Action.WRITE, Action.READ)
            else DefinedBits(0, 0, "no_bus_response"),
            "read_data": self.read(command["address"]) if action == Action.READ
            else DefinedBits(0, 0, "no_read_transfer"),
        }
