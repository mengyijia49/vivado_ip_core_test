from collections import Counter


CR = 0x00
AIR = 0x04
IIR = 0x08


def address_mask(size):
    return ((1 << 64) - 1) ^ (size - 1)


def protection_allowed(mask, protection, write):
    index = protection + (4 if write else 0)
    return bool(mask & (1 << (7 - index)))


class TmrInjectModel:
    def __init__(self, parameters):
        self.p = dict(parameters)
        self.mask = address_mask(parameters["address_size"])
        self.event_counts = Counter()
        self.reset()

    def reset(self):
        self.address = 0
        self.instruction = 0
        self.enabled = False
        self.injecting = False
        self.pending = None

    def _selected(self, address):
        return (address & self.mask) == (self.p["base_address"] & self.mask)

    def _apply_pending(self):
        if self.pending is None:
            return False
        address, data, allowed = self.pending
        offset = address - self.p["base_address"]
        if not allowed:
            self.event_counts["protected_writes_rejected"] += 1
        elif offset == CR:
            valid = ((data & 0xFF) == self.p["magic"] and
                     ((data >> 8) & 3) == self.p["cpu_id"] and
                     bool(data & (1 << 10)))
            if valid:
                self.enabled = True
                self.event_counts["injection_armed"] += 1
            else:
                self.event_counts["invalid_arm_writes"] += 1
            return True
        elif offset == AIR:
            self.address = data & 0xFFFFFFFF
            self.event_counts["address_writes"] += 1
        elif offset == IIR:
            self.instruction = data & 0xFFFFFFFF
            self.event_counts["instruction_writes"] += 1
        return False

    def step(self, inputs):
        if inputs["Rst"]:
            self.reset()
        else:
            old_injecting = self.injecting
            old_enabled = self.enabled
            enable_write = self._apply_pending()
            if old_injecting and not enable_write:
                self.enabled = False

            address_match = ((inputs["MB_LMB_ABus"] >> 2) == (self.address >> 2))
            if inputs["MB_LMB_AddrStrobe"] and old_enabled and address_match:
                self.injecting = True
                self.event_counts["faults_injected"] += 1
            elif inputs["BRAM_Sl_Ready"]:
                self.injecting = False

            control_write = (inputs["LMB_AddrStrobe"] and inputs["LMB_WriteStrobe"] and
                             self._selected(inputs["LMB_ABus"]))
            if control_write:
                allowed = (not self.p["protection"] or protection_allowed(
                    self.p["protection_mask"], inputs.get("LMB_Prot", 0), True))
                self.pending = (inputs["LMB_ABus"], inputs["LMB_WriteDBus"], allowed)
            else:
                self.pending = None

        selected = self._selected(inputs["LMB_ABus"])
        active = bool(inputs["LMB_AddrStrobe"])
        allowed = (not self.p["protection"] or protection_allowed(
            self.p["protection_mask"], inputs.get("LMB_Prot", 0),
            bool(inputs["LMB_WriteStrobe"])))
        if active:
            self.event_counts["control_selected" if selected else "control_outside"] += 1
        if self.injecting:
            read_data = self.instruction
        else:
            read_data = inputs["BRAM_Sl_DBus"]

        outputs = {
            "Sl_DBus": 0,
            "Sl_Ready": int(not inputs["Rst"] and selected and active),
            "Sl_Wait": 0,
            "Sl_UE": int(not inputs["Rst"] and selected and active and not allowed),
            "Sl_CE": 0,
            "MB_Sl_DBus": read_data,
            "MB_Sl_Ready": inputs["BRAM_Sl_Ready"],
            "MB_Sl_Wait": inputs["BRAM_Sl_Wait"],
            "MB_Sl_UE": inputs["BRAM_Sl_UE"],
            "MB_Sl_CE": inputs["BRAM_Sl_CE"],
            "BRAM_LMB_ABus": inputs["MB_LMB_ABus"],
            "BRAM_LMB_WriteDBus": inputs["MB_LMB_WriteDBus"],
            "BRAM_LMB_AddrStrobe": inputs["MB_LMB_AddrStrobe"],
            "BRAM_LMB_ReadStrobe": inputs["MB_LMB_ReadStrobe"],
            "BRAM_LMB_WriteStrobe": inputs["MB_LMB_WriteStrobe"],
            "BRAM_LMB_BE": inputs["MB_LMB_BE"],
        }
        if self.p["protection"]:
            outputs["BRAM_LMB_Prot"] = inputs["MB_LMB_Prot"]
        return outputs
