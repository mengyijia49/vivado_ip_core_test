class InlineSliceModel:
    def __init__(self, low, high):
        self.low = low
        self.mask = (1 << (high - low + 1)) - 1

    def step(self, inputs):
        return {"Dout": (inputs["Din"] >> self.low) & self.mask}
