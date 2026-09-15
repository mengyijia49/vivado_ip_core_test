from vivado_ip_test.plugins.common.cycle import reset_active


class CounterModel:
    def __init__(self, parameters):
        self.p = parameters
        self.value = 0

    def step(self, inputs):
        p = self.p
        if reset_active(inputs, p["ce_overrides_reset"]):
            self.value = 0
        elif inputs.get("CE", 1):
            if inputs["LOAD"]:
                self.value = inputs["L"]
            else:
                up = p["direction"] == "UP" or (p["direction"] == "UPDOWN" and inputs["UP"])
                self.value += p["increment"] if up else -p["increment"]
        self.value &= (1 << p["width"]) - 1
        return {"Q": self.value}
