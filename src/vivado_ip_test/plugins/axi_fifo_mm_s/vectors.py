from vivado_ip_test.plugins.common.axilite.spec import Action

from vivado_ip_test.plugins.axi_fifo_mm_s.reference import (
    IER, ISR, RDFD, RDFO, RDFR, RDR, RLR, TDFD, TDFR, TDFV, TDR, TLR, RC, TC,
)


ALIGNED_PACKET_LENGTHS = (4, 8, 12, 16, 20, 32, 64)
PARTIAL_PACKET_LENGTHS = (1, 2, 3, 4, 5, 7, 8, 9, 13, 16, 31)


def packet_lengths(parameters):
    return PARTIAL_PACKET_LENGTHS if parameters["has_keep"] else ALIGNED_PACKET_LENGTHS


def _command(action, address=0, data=0, strobe=0):
    return {"action": int(action), "address": address, "data": data,
            "strobe": strobe if action == Action.WRITE else 0}


def _op(phase, action, address=0, data=0, strobe=0xF):
    return {"phase": phase, "command": _command(action, address, data, strobe)}


def prepare_operations(samples, parameters):
    lengths = packet_lengths(parameters)
    needed = sum((length + 3) // 4 for length in lengths)
    words = [sample["word"] for sample in samples]
    if len(words) < needed:
        raise ValueError("AXI-Stream FIFO needs more generated words")
    destinations = ((sample.get("destination", 0) for sample in samples)
                    if parameters["destination_width"] else iter(lambda: 0, 1))
    operations = [
        _op("reset", Action.RESET),
        _op("initial_isr", Action.READ, ISR),
        _op("initial_ier", Action.READ, IER),
        _op("initial_vacancy", Action.READ, TDFV),
        _op("initial_occupancy", Action.READ, RDFO),
        _op("clear_reset_interrupts", Action.WRITE, ISR, 0xFFFFFFFF),
        _op("enable_completion_interrupts", Action.WRITE, IER, TC | RC),
    ]
    cursor = 0
    for packet_index, length in enumerate(lengths):
        word_count = (length + 3) // 4
        destination = next(destinations) if parameters["destination_width"] else 0
        if parameters["destination_width"]:
            operations.append(_op("packet_destination", Action.WRITE, TDR, destination))
        for value in words[cursor:cursor + word_count]:
            operations.append(_op("packet_data_write", Action.WRITE, TDFD, value))
        cursor += word_count
        operations.extend((
            _op("packet_start", Action.WRITE, TLR, length),
            _op("completion_interrupt", Action.READ, ISR),
            _op("packet_occupancy", Action.READ, RDFO),
            _op("packet_length", Action.READ, RLR),
        ))
        if parameters["destination_width"]:
            operations.append(_op("packet_destination_read", Action.READ, RDR))
        operations.extend(_op("packet_data_read", Action.READ, RDFD)
                          for _ in range(word_count))
        operations.extend((
            _op("packet_drained", Action.READ, RDFO),
            _op("clear_completion_interrupts", Action.WRITE, ISR, TC | RC),
            _op("interrupt_cleared", Action.READ, ISR),
        ))
    operations.extend((
        _op("ignored_tx_reset_key", Action.WRITE, TDFR, 0x5A),
        _op("ignored_rx_reset_key", Action.WRITE, RDFR, 0x5A),
        _op("tx_reset", Action.WRITE, TDFR, 0xA5),
        _op("rx_reset", Action.WRITE, RDFR, 0xA5),
        _op("reset_interrupts", Action.READ, ISR),
        _op("final_vacancy", Action.READ, TDFV),
        _op("final_occupancy", Action.READ, RDFO),
    ))
    return operations
