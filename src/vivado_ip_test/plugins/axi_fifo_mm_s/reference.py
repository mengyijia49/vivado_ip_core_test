from collections import Counter, deque
from dataclasses import dataclass

from vivado_ip_test.plugins.common.axilite.spec import Action
from vivado_ip_test.plugins.common.cycle import DefinedBits


ISR = 0x00
IER = 0x04
TDFR = 0x08
TDFV = 0x0C
TDFD = 0x10
TLR = 0x14
RDFR = 0x18
RDFO = 0x1C
RDFD = 0x20
RLR = 0x24
TDR = 0x2C
RDR = 0x30

RRC = 1 << 23
TRC = 1 << 24
TSE = 1 << 25
RC = 1 << 26
TC = 1 << 27
RPUE = 1 << 29
RPURE = 1 << 31
SCORED_ISR_BITS = RRC | TRC | TSE | RC | TC | RPUE | RPURE


@dataclass
class Packet:
    words: list[int]
    length: int
    destination: int
    index: int = 0


class AxiFifoModel:
    def __init__(self, parameters):
        self.p = dict(parameters)
        self.event_counts = Counter()
        self.reset()

    def reset(self):
        self.isr = RRC | TRC
        self.ier = 0
        self.tx_words = []
        self.tx_destination = 0
        self.rx_packets = deque()

    def _interrupt(self):
        return int(bool(self.isr & self.ier & SCORED_ISR_BITS))

    def _outputs(self, response, read_data):
        return {"response": response, "read_data": read_data,
                "interrupt": self._interrupt(), "mm2s_prmry_reset_out_n": 1,
                "s2mm_prmry_reset_out_n": 1}

    def write(self, address, value):
        if address == ISR:
            self.isr &= ~value
        elif address == IER:
            self.ier = value & SCORED_ISR_BITS
        elif address == TDFR and value == 0xA5:
            self.tx_words.clear()
            self.isr |= TRC
            self.event_counts["transmit_resets"] += 1
        elif address == RDFR and value == 0xA5:
            self.rx_packets.clear()
            self.isr |= RRC
            self.event_counts["receive_resets"] += 1
        elif address == TDFD:
            self.tx_words.append(value & 0xFFFFFFFF)
            self.event_counts["transmit_words"] += 1
        elif address == TDR and self.p["destination_width"]:
            self.tx_destination = value & ((1 << self.p["destination_width"]) - 1)
        elif address == TLR:
            length = value & 0x7FFFFF
            words = (length + 3) // 4
            if not length or words != len(self.tx_words):
                self.isr |= TSE
                self.event_counts["size_errors"] += 1
            else:
                self.rx_packets.append(Packet(list(self.tx_words), length, self.tx_destination))
                self.isr |= TC | RC
                self.event_counts["packets_looped"] += 1
            self.tx_words.clear()
        else:
            self.event_counts["ignored_writes"] += 1

    def read(self, address):
        if address == ISR:
            return DefinedBits(self.isr, SCORED_ISR_BITS, "threshold_and_ecc_interrupt_bits")
        if address == IER:
            return self.ier
        if address == TDFV:
            return self.p["tx_depth"] - 4 - len(self.tx_words)
        if address == RDFO:
            return len(self.rx_packets[0].words) if self.rx_packets else 0
        if address == RLR:
            if not self.rx_packets:
                self.isr |= RPURE
                return DefinedBits(0, 0, "empty_receive_length")
            return self.rx_packets[0].length
        if address == RDR:
            if not self.rx_packets or not self.p["destination_width"]:
                return 0
            return self.rx_packets[0].destination
        if address == RDFD:
            if not self.rx_packets:
                self.isr |= RPUE
                return DefinedBits(0, 0, "empty_receive_data")
            packet = self.rx_packets[0]
            value = packet.words[packet.index]
            valid_bytes = min(4, packet.length - packet.index * 4)
            mask = (1 << (valid_bytes * 8)) - 1
            packet.index += 1
            if packet.index == len(packet.words):
                self.rx_packets.popleft()
            self.event_counts["receive_words"] += 1
            return DefinedBits(value, mask, "unused_final_word_bytes")
        return 0

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
        elif action == Action.READ:
            read_data = self.read(command["address"])
            response = 0
        self.event_counts[action.name.lower() + "_operations"] += 1
        return self._outputs(response, read_data)
