class VectorLogicModel:
    def __init__(self, parameters):
        self.p = parameters

    def step(self, inputs):
        a, b = inputs["Op1"], inputs.get("Op2", 0)
        operation = self.p["operation"]
        if operation == "and":
            result = a & b
        elif operation == "or":
            result = a | b
        elif operation == "xor":
            result = a ^ b
        else:
            result = ~a
        return {"Res": result & ((1 << self.p["width"]) - 1)}
