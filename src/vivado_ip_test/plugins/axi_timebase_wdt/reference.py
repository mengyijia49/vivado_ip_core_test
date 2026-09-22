from collections import Counter

from vivado_ip_test.plugins.common.axilite.spec import Action
from vivado_ip_test.plugins.common.cycle import DefinedBits


EWDT1 = 1 << 1
WDS = 1 << 2
WRS = 1 << 3


class AxiTimebaseWdtModel:
    def __init__(self, parameters):
        self.p = dict(parameters)
        self.event_counts = Counter()
        self.reset_status = False
        self.reset()

    def reset(self):
        self.count = 0
        self.timer_width = self.p["interval"]
        self.ewdt1 = self.ewdt2 = False
        self.wds = False
        self.reset_asserted = False

    @property
    def enabled(self):
        return self.ewdt1 or self.ewdt2

    def write(self, address, value):
        was_enabled = self.enabled
        if address == 0:
            if value & WDS:
                self.wds = False
                self.event_counts["state_clears"] += 1
            if value & WRS:
                self.reset_status = False
                self.event_counts["reset_status_clears"] += 1
            if self.p["enable_once"]:
                self.ewdt1 |= bool(value & EWDT1)
            else:
                self.ewdt1 = bool(value & EWDT1)
        elif address == 4:
            if self.p["enable_once"]:
                self.ewdt2 |= bool(value & 1)
            else:
                self.ewdt2 = bool(value & 1)
        elif address == 12:
            self.timer_width = value & 31
        if not was_enabled and self.enabled:
            self.count = 0
            self.wds = False
            self.event_counts["enables"] += 1
        elif was_enabled and not self.enabled:
            self.event_counts["disables"] += 1

    def expire(self):
        if not self.wds:
            self.wds = True
            self.event_counts["first_expirations"] += 1
        else:
            self.reset_status = True
            self.reset_asserted = True
            self.event_counts["second_expirations"] += 1

    def advance(self, cycles):
        period = 1 << self.timer_width
        previous = self.count
        self.count = (self.count + cycles) & 0xFFFFFFFF
        if not self.enabled:
            return
        expirations = (previous % period + cycles) // period
        for _ in range(expirations):
            self.expire()

    def read(self, address):
        if address == 0:
            return ((self.count & 0xFFFFFFF0) | int(self.reset_status) * WRS |
                    int(self.wds) * WDS | int(self.ewdt1) * EWDT1 | int(self.ewdt2))
        if address == 4:
            return DefinedBits(0, 0, "write_only_twcsr1")
        if address == 8:
            return self.count
        if address == 12:
            return self.timer_width
        return 0

    def step(self, command):
        action = Action(command["action"])
        if action == Action.RESET:
            # WRS deliberately survives the AXI reset and is cleared by software.
            self.reset()
        elif action == Action.WRITE:
            if command["strobe"] == 15:
                self.write(command["address"], command["data"])
        elif action == Action.WINDOW:
            self.advance(command["run_cycles"])
        self.event_counts[action.name.lower()] += 1
        return {
            "response": (2 if action == Action.WRITE and command["strobe"] != 15 else 0)
            if action in (Action.WRITE, Action.READ)
            else DefinedBits(0, 0, "no_bus_response"),
            "read_data": self.read(command["address"]) if action == Action.READ
            else DefinedBits(0, 0, "no_read_transfer"),
            "timebase_interrupt": 0,
            "wdt_interrupt": int(self.wds),
            "wdt_reset": int(self.reset_asserted),
        }
