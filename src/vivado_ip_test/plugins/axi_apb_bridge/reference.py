from collections import Counter

from vivado_ip_test.plugins.common.axilite.spec import Action
from vivado_ip_test.plugins.common.cycle import DefinedBits


REGION_BYTES = 4096
ERROR_OFFSET = REGION_BYTES - 4


def merge_bytes(previous, value, strobe):
    result = previous
    for lane in range(4):
        if strobe >> lane & 1:
            mask = 0xFF << (lane * 8)
            result = (result & ~mask) | (value & mask)
    return result


class AxiApbBridgeModel:
    def __init__(self, parameters):
        self.base = parameters["base_address"]
        self.slaves = parameters["num_slaves"]
        self.error_response = parameters["error_response"]
        self.memory = {}
        self.event_counts = Counter()

    def _decode(self, address):
        relative = address - self.base
        if not 0 <= relative < self.slaves * REGION_BYTES:
            raise ValueError("参考操作地址不在 APB 窗口内")
        return relative // REGION_BYTES, (relative % REGION_BYTES) // 4

    def step(self, command):
        action = Action(command["action"])
        if action not in (Action.WRITE, Action.READ):
            self.event_counts[action.name.lower()] += 1
            return {"response": DefinedBits(0, 0, "no_bus_response"),
                    "read_data": DefinedBits(0, 0, "no_read_transfer")}

        slave, word = self._decode(command["address"])
        failed = self.error_response and word * 4 == ERROR_OFFSET
        key = (slave, word)
        if action == Action.WRITE and not failed:
            updated = merge_bytes(self.memory.get(key, 0), command["data"], command["strobe"])
            if updated:
                self.memory[key] = updated
            else:
                self.memory.pop(key, None)
            self.event_counts[f"write_strobe_{command['strobe']:x}"] += 1
        self.event_counts[f"slave_{slave}_{action.name.lower()}"] += 1
        if failed:
            self.event_counts["apb_slave_error"] += 1
        return {
            "response": 2 if failed else 0,
            "read_data": self.memory.get(key, 0) if action == Action.READ
            else DefinedBits(0, 0, "no_read_transfer"),
        }
