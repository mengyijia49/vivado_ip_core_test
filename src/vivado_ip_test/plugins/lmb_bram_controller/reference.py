from collections import Counter


WRITE_ACCESS = {"Read_Only": 0, "Word_Only": 1, "All_Writes": 2}


def address_mask(size):
    return ((1 << 64) - 1) ^ (size - 1)


def protection_allowed(mask, protection, write):
    # C_PROT_CFG is declared as std_logic_vector(0 to 7), so index 0 is the MSB.
    index = protection + (4 if write else 0)
    return bool(mask & (1 << (7 - index)))


class LmbBramControllerModel:
    def __init__(self, parameters):
        self.p = parameters
        self.mask = address_mask(parameters["address_size"])
        self.event_counts = Counter()

    def step(self, inputs):
        width = self.p["data_width"]
        lanes = width // 8
        address = inputs["LMB_ABus"]
        selected = (address & self.mask) == (self.p["base_address"] & self.mask)
        write = bool(inputs["LMB_WriteStrobe"])
        allowed = (not self.p["protection"] or
                   protection_allowed(self.p["protection_mask"], inputs.get("LMB_Prot", 0), write))
        active = bool(inputs["LMB_AddrStrobe"])
        reset = bool(inputs["LMB_Rst"])

        if active:
            self.event_counts["selected" if selected else "outside_decode"] += 1
            if self.p["protection"]:
                self.event_counts["protection_allowed" if allowed else "protection_denied"] += 1
        access = WRITE_ACCESS[self.p["write_access"]]
        if access == 2:
            write_enable = inputs["LMB_BE"]
        elif access == 1:
            write_enable = (1 << lanes) - 1
        else:
            write_enable = 0
        write_enable *= int(write and selected and allowed)

        return {
            "Sl_DBus": inputs["BRAM_Din_A"],
            "Sl_Ready": int(not reset and active and selected),
            "Sl_Wait": 0,
            "Sl_UE": int(not reset and selected and not allowed),
            "Sl_CE": 0,
            "BRAM_Rst_A": 0,
            "BRAM_Clk_A": 1,
            "BRAM_Addr_A": address & 0xFFFFFFFF,
            "BRAM_EN_A": int(active and allowed),
            "BRAM_WEN_A": write_enable,
            "BRAM_Dout_A": inputs["LMB_WriteDBus"],
        }
