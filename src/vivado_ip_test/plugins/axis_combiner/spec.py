from dataclasses import dataclass

from vivado_ip_test.plugins.common.cycle import Port


CONCATENATED = frozenset({"tdata", "tstrb", "tkeep", "tuser"})


@dataclass(frozen=True)
class CombinerSpec:
    lane_payload: tuple[Port, ...]
    input_lane_count: int
    primary_lane: int
    settings: dict
    model_parameters: dict
    clock = None
    capacity = 2
    output_period_ns = 10
    source_timing_pattern = "combiner_independent_inputs:1.0"

    @property
    def payload(self):
        return tuple(Port(f"s{lane:02d}_{p.name}", p.width, p.scalar)
                     for lane in range(self.input_lane_count) for p in self.lane_payload)

    @property
    def sink_payload(self):
        return tuple(Port(p.name, p.width * (self.input_lane_count if p.name in CONCATENATED else 1), p.scalar)
                     for p in self.lane_payload)

    @property
    def inputs(self):
        return (Port("aclk", scalar=True), Port("aresetn", scalar=True),
                Port("s_axis_tvalid", self.input_lane_count), Port("m_axis_tready", scalar=True),
                *(Port(f"s_axis_{p.name}", p.width * self.input_lane_count) for p in self.lane_payload))

    @property
    def outputs(self):
        return (Port("s_axis_tready", self.input_lane_count), Port("m_axis_tvalid", scalar=True),
                *(Port(f"m_axis_{p.name}", p.width, p.scalar) for p in self.sink_payload))

    @property
    def generated_ports(self):
        return tuple(p for p in self.payload if p.name.rsplit("_", 1)[1] not in {"tkeep", "tstrb", "tlast"})

    @property
    def width(self):
        return sum(p.width for p in self.payload)
