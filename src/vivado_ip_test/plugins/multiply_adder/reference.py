from collections import deque

from vivado_ip_test.plugins.common.cycle import decode


class MultiplyAdderModel:
    def __init__(self, parameters, timing):
        self.p = parameters
        self.timing = timing
        # Mapping 1 swaps A/B into the same single-DSP datapath; mapping 2 uses multiple DSPs.
        self.single_dsp = timing["implementation"] in (0, 1)
        subtract_latency = (2 if parameters["pipelined"] and self.single_dsp
                            else timing["c_latency"])
        # Sampling is just after the active edge, so one stage needs no older input.
        self.delays = {"product": max(0, timing["ab_latency"] - 1),
                       "addend": max(0, timing["c_latency"] - 1),
                       "subtract": max(0, subtract_latency - 1)}
        self.clear()

    def clear(self):
        self.history = {name: deque([0] * delay) for name, delay in self.delays.items()}
        self.output = {"P": 0, "PCOUT": 0}

    def delayed(self, name, value):
        if not self.delays[name]:
            return value
        queue = self.history[name]
        queue.append(value)
        return queue.popleft()

    def step(self, inputs):
        p = self.p
        if p["pipelined"]:
            if inputs["SCLR"] and (inputs["CE"] or not p["ce_overrides_reset"]):
                self.clear()
                return dict(self.output)
            if not inputs["CE"]:
                return dict(self.output)
        a = decode(inputs["A"], p["a_width"], p["a_type"] == "Signed")
        b = decode(inputs["B"], p["b_width"], p["b_type"] == "Signed")
        addend = (decode(inputs["PCIN"], 48, True) if p["use_pcin"] else
                  decode(inputs["C"], p["c_width"], p["c_type"] == "Signed"))
        product = self.delayed("product", a * b)
        addend = self.delayed("addend", addend)
        subtract = self.delayed("subtract", inputs["SUBTRACT"])
        value = addend - product if subtract else addend + product
        width = p["output_high"] - p["output_low"] + 1
        self.output = {"P": (value >> p["output_low"]) & ((1 << width) - 1),
                       "PCOUT": value & ((1 << 48) - 1) if self.single_dsp else 0}
        return dict(self.output)
