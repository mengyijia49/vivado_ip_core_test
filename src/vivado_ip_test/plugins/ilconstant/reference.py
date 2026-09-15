class InlineConstantModel:
    def __init__(self, value):
        self.value = value

    def step(self, inputs):
        if inputs:
            raise ValueError("Inline constant has no external input")
        return {"dout": self.value}
