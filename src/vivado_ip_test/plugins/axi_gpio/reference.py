from collections import Counter

from vivado_ip_test.plugins.common.axilite.spec import Action
from vivado_ip_test.plugins.common.cycle import DefinedBits


class GpioModel:
    def __init__(self, parameters):
        self.p = dict(parameters)
        self.event_counts = Counter()
        self.reset()

    def reset(self):
        self.data = [self.p[f"default_data{i}"] for i in range(1, self.p["channels"]+1)]
        self.tri = [(1 << self.p[f"width{i}"])-1 if self.p[f"mode{i}"] == "input" else
                    self.p[f"default_tri{i}"] for i in range(1, self.p["channels"]+1)]
        self.tri_register = [self.p[f"default_tri{i}"] if self.p[f"mode{i}"] == "bidirectional"
                             else 0xFFFFFFFF for i in range(1, self.p["channels"]+1)]
        self.pins = [0] * self.p["channels"]
        self.ier = self.isr = self.gier = 0

    def drive(self, command):
        for index in range(self.p["channels"]):
            name = f"gpio{'2' if index else ''}_io_i"
            value = command.get(name, 0)
            if (value ^ self.pins[index]) & self.tri[index] and self.p["interrupt"]:
                self.isr |= 1 << index
                self.event_counts[f"channel{index+1}_input_change"] += 1
            self.pins[index] = value

    def write(self, address, value):
        for index in range(self.p["channels"]):
            mode = self.p[f"mode{index+1}"]
            mask = (1 << self.p[f"width{index+1}"])-1
            if address == index * 8 and mode != "input":
                enabled = mask ^ self.tri[index]
                self.data[index] = (self.data[index] & ~enabled) | (value & enabled)
                self.event_counts["data_write"] += 1
            if address == index * 8 + 4 and mode == "bidirectional":
                self.tri[index] = value & mask
                self.tri_register[index] = value & mask
                self.event_counts["direction_write"] += 1
        if self.p["interrupt"]:
            if address == 0x11C:
                self.gier = (value >> 31) & 1
            elif address == 0x128:
                self.ier = value & ((1 << self.p["channels"])-1)
            elif address == 0x120:
                self.isr ^= value & ((1 << self.p["channels"])-1)
                self.event_counts["interrupt_toggle"] += 1

    def read(self, address):
        for index in range(self.p["channels"]):
            if address == index * 8:
                return (self.pins[index] & self.tri[index]) | (self.data[index] & ~self.tri[index])
            if address == index * 8 + 4:
                return self.tri_register[index]
        if self.p["interrupt"]:
            return {0x11C: self.gier << 31, 0x128: self.ier, 0x120: self.isr}.get(address, 0)
        return 0

    def step(self, command):
        action = Action(command["action"])
        if action == Action.RESET:
            self.reset()
            self.event_counts["reset"] += 1
        self.drive(command)
        if action == Action.WRITE:
            self.write(command["address"], command["data"])
            self.event_counts[f"write_strobe_{command['strobe']:x}"] += 1
        result = {"response": 0 if action in (Action.WRITE, Action.READ) else
                  DefinedBits(0, 0, "no_bus_response"),
                  "read_data": self.read(command["address"]) if action == Action.READ else
                  DefinedBits(0, 0, "no_read_transfer")}
        if action == Action.READ and command["address"] in (0, 4, 8, 12):
            channel = command["address"] // 8 + 1
            if channel <= self.p["channels"]:
                result["read_data"] = DefinedBits(result["read_data"],
                    (1 << self.p[f"width{channel}"])-1, "outside_gpio_register_field")
        for index in range(self.p["channels"]):
            mode = self.p[f"mode{index+1}"]
            stem = f"gpio{'2' if index else ''}_io_"
            if mode != "input":
                mask = ((1 << self.p[f"width{index+1}"])-1) ^ self.tri[index]
                result[stem+"o"] = DefinedBits(self.data[index], mask, "pin_configured_as_input")
            if mode == "bidirectional":
                result[stem+"t"] = self.tri[index]
        if self.p["interrupt"]:
            result["ip2intc_irpt"] = int(bool(self.gier and self.ier & self.isr))
        self.event_counts[action.name.lower()+"_operations"] += 1
        return result
