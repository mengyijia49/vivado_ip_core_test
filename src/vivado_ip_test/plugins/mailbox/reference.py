from collections import deque
from dataclasses import dataclass

from vivado_ip_test.plugins.base import PluginError


class MailboxModel:
    def __init__(self, depth, enable_bus_error):
        self.depth = depth
        self.enable_bus_error = enable_bus_error
        self.reset()

    def reset(self):
        self.outgoing = [deque(), deque()]
        self.errors = [0, 0]
        self.send_threshold = [0, 0]
        self.receive_threshold = [0, 0]

    def write_data(self, port, value):
        queue = self.outgoing[port]
        if len(queue) == self.depth:
            self.errors[port] |= 2
            return 2 if self.enable_bus_error else 0
        queue.append(value & 0xFFFFFFFF)
        return 0

    def read_data(self, port):
        queue = self.outgoing[1 - port]
        if not queue:
            self.errors[port] |= 1
            return (2 if self.enable_bus_error else 0), None
        return 0, queue.popleft()

    def status(self, port):
        send = self.outgoing[port]
        receive = self.outgoing[1 - port]
        return (int(not receive) | (int(len(send) == self.depth) << 1) |
                (int(len(send) <= self.send_threshold[port]) << 2) |
                (int(len(receive) > self.receive_threshold[port]) << 3))

    def read_errors(self, port):
        value = self.errors[port]
        self.errors[port] = 0
        return value

    def clear_send(self, port):
        self.outgoing[port].clear()

    def clear_receive(self, port):
        self.outgoing[1 - port].clear()


@dataclass(frozen=True)
class MailboxPlan:
    depth: int
    memory_style: str
    enable_bus_error: bool
    registered_interrupts: bool

    @classmethod
    def from_parameters(cls, parameters):
        if parameters.get("interface_mode") != "Axi4Lite":
            raise PluginError("Mailbox AXI4-Lite 计划需要 interface_mode=Axi4Lite")
        depth = parameters["depth"]
        if type(depth) is not int or not 16 <= depth <= 8192 or depth & (depth - 1):
            raise PluginError("Mailbox 深度必须是 16 至 8192 之间的 2 的幂")
        if parameters["memory_style"] not in ("Distributed_RAM", "Block_RAM"):
            raise PluginError("Mailbox 存储类型必须是 Distributed_RAM 或 Block_RAM")
        for name in ("enable_bus_error", "registered_interrupts"):
            if type(parameters[name]) is not bool:
                raise PluginError(f"Mailbox 参数 {name} 必须是布尔值")
        return cls(depth, parameters["memory_style"], parameters["enable_bus_error"],
                   parameters["registered_interrupts"])

    def as_dict(self):
        return {
            "model": "mailbox_dual_fifo:1.0", "depth": self.depth,
            "memory_style": self.memory_style,
            "enable_bus_error": self.enable_bus_error,
            "registered_interrupts": self.registered_interrupts,
            "interface_mode": "dual_axi4lite_synchronous",
        }


@dataclass(frozen=True)
class AxisBeat:
    data: int
    last: bool


class AxisMailboxModel:
    def __init__(self, depth, data_width=32):
        self.depth = depth
        self.mask = (1 << data_width) - 1
        self.reset()

    def reset(self):
        self.queues = [deque(), deque()]

    def ready(self, source):
        return len(self.queues[source]) < self.depth

    def push(self, source, data, last=False):
        if not self.ready(source):
            return False
        self.queues[source].append(AxisBeat(data & self.mask, bool(last)))
        return True

    def pop(self, destination):
        source = 1 - destination
        return self.queues[source].popleft() if self.queues[source] else None


@dataclass(frozen=True)
class AxisMailboxPlan:
    depth: int
    memory_style: str
    async_clocks: bool
    data_width: int

    @classmethod
    def from_parameters(cls, parameters):
        if parameters.get("interface_mode") != "Axis":
            raise PluginError("Mailbox AXI4-Stream 计划需要 interface_mode=Axis")
        depth = parameters["depth"]
        if type(depth) is not int or not 16 <= depth <= 8192 or depth & (depth - 1):
            raise PluginError("Mailbox 深度必须是 16 至 8192 之间的 2 的幂")
        if parameters["memory_style"] not in ("Distributed_RAM", "Block_RAM"):
            raise PluginError("Mailbox 存储类型必须是 Distributed_RAM 或 Block_RAM")
        if type(parameters["async_clocks"]) is not bool:
            raise PluginError("Mailbox 参数 async_clocks 必须是布尔值")
        if parameters["async_clocks"]:
            raise PluginError("Mailbox AXI4-Stream 异步时钟尚未接入自检")
        if parameters["data_width"] != 32:
            raise PluginError("Mailbox AXI4-Stream 当前只支持 32 位数据")
        return cls(depth, parameters["memory_style"], False, 32)

    def input_sequences(self):
        return (
            (AxisBeat(0x00000000, False), AxisBeat(0xFFFFFFFF, False),
             AxisBeat(0x80000000, True), AxisBeat(0x13579BDF, False),
             AxisBeat(0x2468ACE0, True)),
            (AxisBeat(0xAAAAAAAA, False), AxisBeat(0x55555555, True),
             AxisBeat(0x00000001, False), AxisBeat(0x7FFFFFFF, False),
             AxisBeat(0xDEADBEEF, True)),
        )

    def expected_outputs(self):
        model = AxisMailboxModel(self.depth, self.data_width)
        for source, beats in enumerate(self.input_sequences()):
            for beat in beats:
                if not model.push(source, beat.data, beat.last):
                    raise PluginError("Mailbox AXI4-Stream 参考序列超过 FIFO 深度")
        return tuple(tuple(filter(None, (model.pop(destination) for _ in range(5))))
                     for destination in range(2))

    def as_dict(self):
        return {
            "model": "mailbox_axis_dual_fifo:1.0", "depth": self.depth,
            "memory_style": self.memory_style, "async_clocks": self.async_clocks,
            "data_width": self.data_width, "interface_mode": "dual_axis_synchronous",
            "inputs": [[{"data": beat.data, "last": beat.last} for beat in beats]
                       for beats in self.input_sequences()],
            "expected_outputs": [[{"data": beat.data, "last": beat.last} for beat in beats]
                                 for beats in self.expected_outputs()],
        }


def mailbox_plan(parameters):
    mode = parameters.get("interface_mode")
    if mode == "Axi4Lite":
        return MailboxPlan.from_parameters(parameters)
    if mode == "Axis":
        return AxisMailboxPlan.from_parameters(parameters)
    raise PluginError(f"Mailbox 接口模式不受支持：{mode!r}")
