class ConcatModel:
    def __init__(self, widths):
        self.widths = tuple(widths)

    def step(self, inputs):
        result, offset = 0, 0
        for index, width in enumerate(self.widths):
            result += inputs[f"In{index}"] * (1 << offset)
            offset += width
        return {"dout": result}
