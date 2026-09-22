from dataclasses import dataclass

from vivado_ip_test.plugins.base import PluginError


@dataclass(frozen=True)
class MutexValue:
    locked: bool = False
    owner: int = 0
    interface: int = 0

    @property
    def register(self):
        return (self.owner << 1 | int(self.locked)) if self.locked else 0


class MutexModel:
    def __init__(self, num_interfaces, num_mutexes, enable_user, hardware_protection):
        self.num_interfaces = num_interfaces
        self.num_mutexes = num_mutexes
        self.enable_user = enable_user
        self.hardware_protection = hardware_protection
        self.reset()

    def reset(self):
        if self.num_mutexes == 1 or not hasattr(self, "mutexes"):
            self.mutexes = [MutexValue() for _ in range(self.num_mutexes)]
            self.users = [0 for _ in range(self.num_mutexes)]

    def write_mutex(self, interface, index, value):
        self._check(interface, index)
        current = self.mutexes[index]
        owner = (value >> 1) & 0xFF
        owner_matches = current.owner == owner
        interface_matches = not self.hardware_protection or current.interface == interface
        if not current.locked or (owner_matches and interface_matches):
            self.mutexes[index] = (MutexValue(True, owner, interface)
                                   if value & 1 else MutexValue())

    def write_user(self, interface, index, value):
        self._check(interface, index)
        if self.enable_user:
            self.users[index] = value & 0xFFFFFFFF

    def read_mutex(self, interface, index):
        self._check(interface, index)
        return self.mutexes[index].register

    def read_user(self, interface, index):
        self._check(interface, index)
        return self.users[index] if self.enable_user else 0

    def simultaneous_acquire(self, index, values):
        if len(values) != self.num_interfaces:
            raise PluginError("同时竞争输入数必须等于 AXI 接口数")
        self.write_mutex(0, index, values[0])

    def _check(self, interface, index):
        if not 0 <= interface < self.num_interfaces or not 0 <= index < self.num_mutexes:
            raise PluginError("Mutex 模型访问超出配置范围")


@dataclass(frozen=True)
class MutexPlan:
    num_interfaces: int
    num_mutexes: int
    enable_user: bool
    hardware_protection: bool

    @classmethod
    def from_parameters(cls, parameters):
        interfaces = parameters["num_interfaces"]
        mutexes = parameters["num_mutexes"]
        if type(interfaces) is not int or interfaces not in (2, 4, 8):
            raise PluginError("Mutex 当前支持 2、4 或 8 个同步 AXI 接口")
        if type(mutexes) is not int or not 1 <= mutexes <= 32:
            raise PluginError("Mutex 数量必须在 1 至 32 之间")
        for name in ("enable_user", "hardware_protection"):
            if type(parameters[name]) is not bool:
                raise PluginError(f"Mutex 参数 {name} 必须是布尔值")
        return cls(interfaces, mutexes, parameters["enable_user"],
                   parameters["hardware_protection"])

    def as_dict(self):
        return {
            "model": "mutex_shared_state:1.0",
            "num_interfaces": self.num_interfaces,
            "num_mutexes": self.num_mutexes,
            "enable_user": self.enable_user,
            "hardware_protection": self.hardware_protection,
            "clock_mode": "synchronous",
            "simultaneous_priority": "lowest_interface_index",
            "storage_reset": "cleared" if self.num_mutexes == 1 else "explicit_initialization",
        }
