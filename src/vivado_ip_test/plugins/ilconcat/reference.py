class InlineConcatModel:
    def __init__(self, widths):
        self.widths = tuple(widths)

    def step(self, inputs):
        result = 0
        for index in reversed(range(len(self.widths))):
            result = (result << self.widths[index]) | inputs[f"In{index}"]
        return {"dout": result}
