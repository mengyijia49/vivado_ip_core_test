from collections import Counter, deque

from vivado_ip_test.plugins.common.axilite.spec import Action
from vivado_ip_test.plugins.common.cycle import DefinedBits


RX_FIFO = 0x0
TX_FIFO = 0x4
STATUS = 0x8
CONTROL = 0xC


class UartLiteModel:
    def __init__(self, parameters):
        self.p = dict(parameters)
        self.mask = (1 << self.p["data_bits"]) - 1
        self.event_counts = Counter()
        self.reset()

    def reset(self):
        self.rx_fifo = deque()
        self.interrupt_enabled = False
        self.overrun = False

    def status(self):
        return (int(bool(self.rx_fifo)) | (int(len(self.rx_fifo) == 16) << 1)
                | (1 << 2) | (int(self.interrupt_enabled) << 4)
                | (int(self.overrun) << 5))

    def write(self, address, value):
        if address == TX_FIFO:
            value &= self.mask
            if len(self.rx_fifo) < 16:
                self.rx_fifo.append(value)
                self.event_counts["looped_characters"] += 1
            else:
                self.overrun = True
                self.event_counts["receive_overruns"] += 1
        elif address == CONTROL:
            self.interrupt_enabled = bool(value & 0x10)
            if value & 0x2:
                self.rx_fifo.clear()
                self.event_counts["receive_fifo_resets"] += 1
            if value & 0x1:
                self.event_counts["transmit_fifo_resets"] += 1
        else:
            self.event_counts["ignored_writes"] += 1

    def read(self, address):
        if address == RX_FIFO:
            if not self.rx_fifo:
                return DefinedBits(0, 0, "empty_receive_fifo"), 2
            self.event_counts["received_characters_read"] += 1
            return DefinedBits(self.rx_fifo.popleft(), self.mask, "reserved_receive_bits"), 0
        if address == STATUS:
            value = self.status()
            self.overrun = False
            self.event_counts["status_reads"] += 1
            return DefinedBits(value, 0xFF, "reserved_status_bits"), 0
        if address in (TX_FIFO, CONTROL):
            return 0, 0
        return 0, 0

    def step(self, command):
        action = Action(command["action"])
        response = DefinedBits(0, 0, "no_bus_response")
        read_data = DefinedBits(0, 0, "no_read_transfer")
        if action == Action.RESET:
            self.reset()
            self.event_counts["reset"] += 1
        elif action == Action.WRITE:
            self.write(command["address"], command["data"])
            response = 0
            self.event_counts[f"write_strobe_{command['strobe']:x}"] += 1
        elif action == Action.READ:
            read_data, response = self.read(command["address"])
        interrupt = (DefinedBits(0, 0, "interrupt_event_between_checkpoints")
                     if self.interrupt_enabled else 0)
        self.event_counts[action.name.lower() + "_operations"] += 1
        return {"response": response, "read_data": read_data,
                "interrupt": interrupt, "tx": 1}
