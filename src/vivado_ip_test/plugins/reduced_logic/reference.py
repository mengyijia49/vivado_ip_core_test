class ReducedLogicModel:
    def __init__(self, parameters):
        self.p = parameters

    def step(self, inputs):
        value = inputs["Op1"]
        if self.p["operation"] == "and":
            result = int(value == (1 << self.p["width"]) - 1)
        elif self.p["operation"] == "or":
            result = int(value != 0)
        else:
            result = value.bit_count() % 2
        return {"Res": result}
