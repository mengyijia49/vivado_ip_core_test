from collections import Counter

from vivado_ip_test.plugins.common.axilite.spec import Action
from vivado_ip_test.plugins.common.cycle import DefinedBits


ISR, IPR, IER, IAR, SIE, CIE, IVR, MER, ILR = 0, 4, 8, 12, 16, 20, 24, 28, 36
WORD = 0xFFFFFFFF


class IntcModel:
    """PG099 register semantics after stable inputs, not a cycle/CDC model."""

    def __init__(self, parameters):
        self.p = dict(parameters)
        self.modes = tuple(parameters["input_modes"])
        self.hardware_mask = (1 << len(self.modes))-1
        self.mask = (1 << (len(self.modes)+parameters["software_interrupts"]))-1
        self.inactive = sum(1 << i for i, mode in enumerate(self.modes) if mode in ("low", "falling"))
        self.event_counts = Counter()
        self.reset()

    def reset(self):
        self.isr = self.ier = self.mer = 0
        self.ilr = WORD
        self.pins = self.inactive

    def drive(self, pins):
        if not self.mer & 2 and pins != self.inactive:
            raise ValueError("INTC pre-HIE external activity is outside the stable-input oracle")
        if self.mer & 2:
            for i, mode in enumerate(self.modes):
                active = ((pins >> i) & 1) == int(mode in ("rising", "high"))
                changed = bool((pins ^ self.pins) & (1 << i))
                if active and (mode in ("high", "low") or changed):
                    if changed or not self.isr & (1 << i):
                        self.event_counts[mode+"_capture"] += 1
                    self.isr |= 1 << i
        self.pins = pins

    def write(self, address, value):
        if address == ISR:
            writable = self.mask ^ (self.hardware_mask if self.mer & 2 else 0)
            self.isr |= value & writable
            self.event_counts["isr_write_zero" if value == 0 else "isr_write_set"] += 1
        elif address == IER:
            self.ier = value & self.mask
        elif address == IAR:
            self.isr &= ~(value & self.mask)
            self.event_counts["acknowledge"] += 1
        elif address == SIE and self.p["has_sie"]:
            self.ier |= value & self.mask
        elif address == CIE and self.p["has_cie"]:
            self.ier &= ~(value & self.mask)
        elif address == MER:
            if value & 2 and not self.mer & 2 and self.isr & self.hardware_mask:
                raise ValueError("Clear test-mode hardware ISR bits before enabling HIE")
            self.mer = (self.mer & 2) | (value & 3)
        elif address == ILR and self.p["has_ilr"]:
            if value > self.mask.bit_length() and value != WORD:
                raise ValueError("INTC ILR oracle accepts interrupt ordinals and the all-ones sentinel")
            self.ilr = value & WORD
        self.drive(self.pins)

    def read(self, address):
        registers = {ISR: self.isr, IER: self.ier, MER: self.mer}
        if self.p["has_ipr"]:
            registers[IPR] = self.isr & self.ier
        if self.p["has_ivr"]:
            pending = self.isr & self.ier
            registers[IVR] = (pending & -pending).bit_length()-1 if pending else WORD
        if self.p["has_ilr"]:
            registers[ILR] = self.ilr
        if address not in registers:
            raise ValueError("INTC write-only or absent register read has no strict oracle")
        return registers[address]

    def step(self, command):
        action = Action(command["action"])
        if action == Action.WRITE and command["strobe"] != 15:
            raise ValueError("INTC partial-write side effects are not specified by this oracle")
        if action == Action.RESET:
            self.reset()
        self.drive(command["intr"])
        if action == Action.WRITE:
            self.write(command["address"], command["data"])
        pending = self.isr & self.ier
        priority = (pending & -pending).bit_length()-1 if pending else WORD
        asserted = bool(self.mer & 1 and pending and (not self.p["has_ilr"] or priority < self.ilr))
        self.event_counts[action.name.lower()+"_operations"] += 1
        self.event_counts["irq_asserted_observations"] += int(asserted)
        return {"response": 0 if action in (Action.READ, Action.WRITE) else
                DefinedBits(0, 0, "no_bus_response"),
                "read_data": self.read(command["address"]) if action == Action.READ else
                DefinedBits(0, 0, "no_read_transfer"),
                "irq": int(asserted == self.p["irq_active_high"])}
