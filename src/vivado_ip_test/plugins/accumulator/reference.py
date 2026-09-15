from vivado_ip_test.plugins.common.cycle import decode, reset_active


class AccumulatorModel:
    def __init__(self, parameters):
        self.p = parameters
        self.value = 0

    def step(self, inputs):
        p = self.p
        b = decode(inputs["B"], p["input_width"], p["input_type"] == "Signed")
        if reset_active(inputs, p["ce_overrides_reset"]):
            self.value = 0
        elif inputs.get("CE", 1):
            if inputs.get("BYPASS", 0):
                self.value = b
            elif p["operation"] == "Add" or (p["operation"] == "Add_Subtract" and inputs["ADD"]):
                self.value += b
            else:
                self.value -= b
        self.value &= (1 << p["output_width"]) - 1
        return {"Q": self.value}
