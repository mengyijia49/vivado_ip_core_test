class SliceModel:
    def __init__(self, low_bit, output_width):
        self.divisor = 1 << low_bit
        self.modulus = 1 << output_width

    def step(self, inputs):
        return {"Dout": (inputs["Din"] // self.divisor) % self.modulus}
