class InlineVectorLogicModel:
    def __init__(self, width, operation):
        self.mask = (1 << width) - 1
        self.operation = operation

    def step(self, inputs):
        a = inputs["Op1"]
        if self.operation == "not":
            result = self.mask ^ a
        elif self.operation == "and":
            result = a & inputs["Op2"]
        elif self.operation == "or":
            result = a | inputs["Op2"]
        elif self.operation == "xor":
            result = a ^ inputs["Op2"]
        else:
            raise ValueError("Unknown inline vector operation")
        return {"Res": result}
