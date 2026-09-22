from vivado_ip_test.plugins.base import PluginError


FF_TYPES = {
    "FDRE": (1, "reset", False),
    "FDCE": (2, "clear", False),
    "FDSE": (3, "set", True),
    "FDPE": (4, "preset", True),
    "LDCE": (5, "clear", False),
    "LDPE": (6, "preset", True),
}


def parse_init(text, width):
    if not isinstance(text, str) or not text.startswith("0x"):
        raise PluginError("util_ff 初值必须是以 0x 开头的十六进制字符串")
    try:
        value = int(text, 16)
    except ValueError as exc:
        raise PluginError("util_ff 初值不是合法十六进制数") from exc
    if not 0 <= value < 1 << width:
        raise PluginError("util_ff 初值超出配置位宽")
    return value


class UtilFfModel:
    def __init__(self, parameters):
        self.width = parameters["width"]
        self.mask = (1 << self.width) - 1
        self.kind = parameters["ff_type"]
        self.control = FF_TYPES[self.kind][1]
        self.control_value = self.mask if FF_TYPES[self.kind][2] else 0
        self.control_active_high = parameters["control_active_high"]
        self.data_inverted = parameters["data_inverted"]
        self.gate_active_high = parameters["gate_active_high"]
        self.value = parse_init(parameters["init_value"], self.width)

    def step(self, inputs):
        active = bool(inputs[self.control]) == self.control_active_high
        if active:
            self.value = self.control_value
        elif self.kind.startswith("FD"):
            if inputs["clk_enable"]:
                data = inputs["D"]
                self.value = (data ^ self.mask) if self.data_inverted else data
        else:
            gate = bool(inputs["G"]) == self.gate_active_high
            if gate and inputs["gate_enable"]:
                self.value = inputs["D"]
        return {"Q": self.value}
