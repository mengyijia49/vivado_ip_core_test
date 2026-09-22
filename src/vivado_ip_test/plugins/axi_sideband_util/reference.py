from collections import Counter


ADDRESS_FIELDS = (
    "id", "addr", "len", "size", "burst", "lock", "cache", "prot", "qos",
)


class AxiSidebandUtilModel:
    def __init__(self, parameters):
        self.p = dict(parameters)
        self.event_counts = Counter()

    def _user(self, value):
        mode = self.p["smid_mode"]
        width = self.p["smid_width"]
        if mode == "Insert":
            return (value << width) | self.p["smid_value"]
        if mode == "Remove":
            return value >> width
        return value

    def step(self, inputs):
        outputs = {}
        for channel in ("aw", "ar"):
            for field in ADDRESS_FIELDS:
                outputs[f"m_axi_{channel}{field}"] = inputs[f"s_axi_{channel}{field}"]
            outputs[f"m_axi_{channel}user"] = self._user(inputs[f"s_axi_{channel}user"])
            outputs[f"m_axi_{channel}valid"] = inputs[f"s_axi_{channel}valid"]
            outputs[f"s_axi_{channel}ready"] = inputs[f"m_axi_{channel}ready"]

        for field in ("data", "strb", "last", "valid"):
            outputs[f"m_axi_w{field}"] = inputs[f"s_axi_w{field}"]
        outputs["s_axi_wready"] = inputs["m_axi_wready"]

        for field in ("id", "resp", "valid"):
            outputs[f"s_axi_b{field}"] = inputs[f"m_axi_b{field}"]
        outputs["m_axi_bready"] = inputs["s_axi_bready"]

        for field in ("id", "data", "resp", "last", "valid"):
            outputs[f"s_axi_r{field}"] = inputs[f"m_axi_r{field}"]
        outputs["m_axi_rready"] = inputs["s_axi_rready"]
        outputs["w_parity_error"] = 0
        outputs["r_parity_error"] = 0

        for channel in ("aw", "w", "b", "ar", "r"):
            valid = inputs[f"s_axi_{channel}valid"] if channel in ("aw", "w", "ar") \
                else inputs[f"m_axi_{channel}valid"]
            ready = inputs[f"m_axi_{channel}ready"] if channel in ("aw", "w", "ar") \
                else inputs[f"s_axi_{channel}ready"]
            if valid and ready:
                self.event_counts[f"{channel}_handshake"] += 1
            elif valid:
                self.event_counts[f"{channel}_backpressure"] += 1
        return outputs
