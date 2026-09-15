from dataclasses import dataclass

from vivado_ip_test.plugins.common.cycle import Port


@dataclass(frozen=True)
class BroadcasterSpec:
    payload: tuple[Port, ...]
    branch_payload: tuple[Port, ...]
    branch_count: int
    settings: dict
    model_parameters: dict
    clock = None
    capacity = 2
    output_period_ns = 10
    backpressure_pattern = "broadcaster_independent_windows:1.0"

    @property
    def inputs(self):
        return (Port("aclk", scalar=True), Port("aresetn", scalar=True),
                Port("s_axis_tvalid", scalar=True), Port("m_axis_tready", self.branch_count),
                *(Port(f"s_axis_{p.name}", p.width, p.scalar) for p in self.payload))

    @property
    def outputs(self):
        return (Port("s_axis_tready", scalar=True), Port("m_axis_tvalid", self.branch_count),
                *(Port(f"m_axis_{p.name}", p.width * self.branch_count) for p in self.branch_payload))

    @property
    def sink_payload(self):
        return tuple(Port(f"m{branch:02d}_{p.name}", p.width, p.scalar)
                     for branch in range(self.branch_count) for p in self.branch_payload)

    @property
    def generated_ports(self):
        return tuple(p for p in self.payload if p.name not in {"tkeep", "tstrb", "tlast"})

    @property
    def width(self):
        return sum(p.width for p in self.payload)
