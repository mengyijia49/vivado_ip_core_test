from vivado_ip_test.plugins.common.cycle import decode, reset_active


class AdderModel:
    def __init__(self, parameters):
        self.p = parameters
        self.value = 0

    def step(self, inputs):
        p = self.p
        a = decode(inputs["A"], p["a_width"], p["a_type"] == "Signed")
        b = decode(inputs["B"], p["b_width"], p["b_type"] == "Signed")
        add = p["operation"] == "Add" or (p["operation"] == "Add_Subtract" and inputs["ADD"])
        result = (a + b if add else a - b) & ((1 << p["output_width"]) - 1)
        if not p["latency"]:
            self.value = result
        elif reset_active(inputs, p["ce_overrides_reset"]):
            self.value = 0
        elif inputs.get("CE", 1):
            self.value = result
        return {"S": self.value}
