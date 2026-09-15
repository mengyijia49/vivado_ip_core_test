from vivado_ip_test.plugins.common.integer_literals import parse_unsigned_literal as parse_literal


class ConstantModel:
    def __init__(self, value):
        self.value = value

    def step(self, inputs):
        if inputs:
            raise ValueError("A constant IP has no input ports")
        return {"dout": self.value}
