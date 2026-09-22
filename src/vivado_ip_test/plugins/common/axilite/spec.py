from dataclasses import dataclass
from enum import IntEnum
from typing import Callable, Mapping

from vivado_ip_test.plugins.common.cycle import Port


class Action(IntEnum):
    WRITE = 0
    READ = 1
    DRIVE = 2
    RESET = 3
    IDLE = 4
    WINDOW = 5


@dataclass(frozen=True)
class ClockWindow:
    control: str
    active: int = 0
    width: int = 12


@dataclass(frozen=True)
class PulseObservation:
    port: str
    active: int = 1

    @property
    def count_port(self):
        return Port(self.port + "_pulses", 32)


@dataclass(frozen=True)
class ObservationSpec:
    outputs: tuple[Port, ...]
    masked_outputs: bool = True


@dataclass(frozen=True)
class AxiLiteSpec:
    address_width: int
    side_inputs: tuple[Port, ...]
    side_outputs: tuple[Port, ...]
    generated_ports: tuple[Port, ...]
    settings: Mapping[str, object]
    model_parameters: Mapping[str, object]
    model_factory: Callable
    prepare_operations: Callable
    settle_cycles: int = 8
    reset_cycles: int = 20
    minimum_ip_revision: int = 0
    window: ClockWindow | None = None
    pulses: tuple[PulseObservation, ...] = ()
    loopbacks: tuple[tuple[str, str], ...] = ()
    metadata_spec: object | None = None
    extra_mappings: tuple[str, ...] = ()
    testbench_declarations: str = ""
    testbench_statements: str = ""
    clock = None
    masked_outputs = True

    def __post_init__(self):
        if self.window is not None:
            if (Port(self.window.control, scalar=True) not in self.side_inputs
                    or type(self.window.active) is not int or self.window.active not in (0, 1)
                    or type(self.window.width) is not int or not 1 <= self.window.width <= 16):
                raise ValueError("Invalid AXI-Lite clock window control")
        names = [port.name for port in self.side_outputs]
        for pulse in self.pulses:
            if (Port(pulse.port, scalar=True) not in self.side_outputs
                    or type(pulse.active) is not int or pulse.active not in (0, 1)
                    or pulse.count_port.name in names):
                raise ValueError("Invalid AXI-Lite pulse observation")
            names.append(pulse.count_port.name)
        inputs = {port.name: port for port in self.side_inputs}
        outputs = {port.name: port for port in self.side_outputs}
        looped_inputs = set()
        for input_name, output_name in self.loopbacks:
            if (input_name not in inputs or output_name not in outputs
                    or inputs[input_name].width != outputs[output_name].width
                    or input_name in looped_inputs):
                raise ValueError("Invalid AXI-Lite side-port loopback")
            looped_inputs.add(input_name)
        if (any(type(item) is not str or "=>" not in item for item in self.extra_mappings)
                or type(self.testbench_declarations) is not str
                or type(self.testbench_statements) is not str):
            raise ValueError("Invalid AXI-Lite testbench extension")

    @property
    def inputs(self):
        return (Port("s_axi_aclk", scalar=True), Port("s_axi_aresetn", scalar=True),
                Port("s_axi_awaddr", self.address_width), Port("s_axi_awvalid", scalar=True),
                Port("s_axi_wdata", 32), Port("s_axi_wstrb", 4), Port("s_axi_wvalid", scalar=True),
                Port("s_axi_bready", scalar=True), Port("s_axi_araddr", self.address_width),
                Port("s_axi_arvalid", scalar=True), Port("s_axi_rready", scalar=True), *self.side_inputs)

    @property
    def outputs(self):
        return (Port("s_axi_awready", scalar=True), Port("s_axi_wready", scalar=True),
                Port("s_axi_bresp", 2), Port("s_axi_bvalid", scalar=True),
                Port("s_axi_arready", scalar=True), Port("s_axi_rdata", 32),
                Port("s_axi_rresp", 2), Port("s_axi_rvalid", scalar=True), *self.side_outputs)

    @property
    def command_ports(self):
        looped_inputs = {input_name for input_name, _ in self.loopbacks}
        return (Port("action", 3), Port("address", self.address_width),
                Port("data", 32), Port("strobe", 4),
                *(port for port in self.side_inputs if port.name not in looped_inputs),
                *((Port("run_cycles", self.window.width),) if self.window else ()))

    @property
    def observation(self):
        return ObservationSpec((Port("response", 2), Port("read_data", 32), *self.side_outputs,
                                *(pulse.count_port for pulse in self.pulses)))

    def validate_command(self, command):
        if set(command) != {p.name for p in self.command_ports} or any(
                type(command[p.name]) is not int or not 0 <= command[p.name] <= p.limit
                for p in self.command_ports):
            raise ValueError("AXI-Lite command fields or widths are invalid")
        action = Action(command["action"])
        if action == Action.WINDOW and self.window is None:
            raise ValueError("This AXI-Lite peripheral has no clock window")
        if self.window:
            if command[self.window.control] != 1-self.window.active:
                raise ValueError("Clock window control must be inactive outside the window")
            if bool(command["run_cycles"]) != (action == Action.WINDOW):
                raise ValueError("Only clock windows need a positive run_cycles value")
        if command["address"] % 4:
            raise ValueError("Only aligned AXI-Lite accesses are generated")
        if action != Action.WRITE and (command["data"] or command["strobe"]):
            raise ValueError("Non-write commands must have zero data and strobe")
        if action not in (Action.WRITE, Action.READ) and command["address"]:
            raise ValueError("Non-bus commands must have zero address")
