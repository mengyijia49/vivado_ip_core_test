from vivado_ip_test.plugins.common.cycle import DefinedBits


class DdsPhaseModel:
    def __init__(self, parameters, latency=4):
        self.width = parameters["phase_width"]
        self.increment = parameters["phase_increment"]
        self.offset = parameters["phase_offset"]
        self.latency = latency
        self.mask = (1 << self.width) - 1
        self.phase = 0
        self.data = 0
        self.valid = 0
        self.delay = latency - 1
        self.reset_registered = True
        self.event_counts = {"reset_cycles": 0, "held_output_cycles": 0,
                             "advanced_output_cycles": 0}

    def step(self, inputs):
        reset_now = self.reset_registered
        self.reset_registered = not inputs["aresetn"]
        if reset_now:
            self.phase = 0
            self.valid = 0
            self.delay = self.latency - 1
            self.event_counts["reset_cycles"] += 1
        elif self.valid and not inputs["m_axis_phase_tready"]:
            self.event_counts["held_output_cycles"] += 1
        elif self.delay:
            self.delay -= 1
        else:
            self.phase = (self.phase + self.increment) & self.mask
            self.data = (self.phase + self.offset) & self.mask
            self.valid = 1
            self.event_counts["advanced_output_cycles"] += 1
        data = DefinedBits(self.data, self.mask if self.valid else 0,
                           "AXI-Stream TDATA is undefined while TVALID is low")
        return {"m_axis_phase_tvalid": self.valid, "m_axis_phase_tdata": data}
