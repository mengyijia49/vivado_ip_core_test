from vivado_ip_test.plugins.common.redundancy import comparison, voted_value
from vivado_ip_test.plugins.common.cycle import DefinedBits


class TmrVoterModel:
    def __init__(self, parameters):
        self.p = parameters

    def step(self, inputs):
        voted = voted_value(self.p, inputs)
        outputs = {"Discrete": voted}
        if self.p["comparator"]:
            flags = comparison(self.p, inputs, voted)
            outputs["Compare"] = flags if self.p["triple"] else DefinedBits(
                flags, 1, "lockstep_unused_compare_bits")
        return outputs
