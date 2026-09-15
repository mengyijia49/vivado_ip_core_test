class InlineReducedLogicModel:
    def __init__(self, width, operation):
        self.mask = (1 << width) - 1
        self.operation = operation

    def step(self, inputs):
        value = inputs["Op1"]
        if self.operation == "and":
            result = int(value == self.mask)
        elif self.operation == "or":
            result = int(value != 0)
        elif self.operation == "xor":
            result = value.bit_count() & 1
        else:
            raise ValueError("Unknown inline reduction operation")
        return {"Res": result}
