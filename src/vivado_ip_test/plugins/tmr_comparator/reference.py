from vivado_ip_test.plugins.common.redundancy import comparison


class TmrComparatorModel:
    def __init__(self, parameters):
        self.p = parameters

    def step(self, inputs):
        return {"Compare": comparison(self.p, inputs)}
