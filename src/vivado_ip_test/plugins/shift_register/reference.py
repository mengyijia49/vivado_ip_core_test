from collections import deque


class ShiftRegisterModel:
    def __init__(self, parameters):
        self.values = deque([0] * parameters["depth"], maxlen=parameters["depth"])

    def step(self, inputs):
        if inputs.get("CE", 1):
            self.values.appendleft(inputs["D"])
        return {"Q": self.values[-1]}
