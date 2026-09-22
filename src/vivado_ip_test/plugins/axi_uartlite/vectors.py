from vivado_ip_test.plugins.common.axilite.spec import Action


def _command(action, address=0, data=0, strobe=0):
    return {"action": int(action), "address": address, "data": data,
            "strobe": strobe if action == Action.WRITE else 0}


def _op(phase, action, address=0, data=0, strobe=0):
    return {"phase": phase, "command": _command(action, address, data, strobe)}


def _characters(samples, width):
    mask = (1 << width) - 1
    candidates = [0, 1, mask, 1 << (width - 1), (1 << (width - 1)) - 1,
                  0x15 & mask, 0x2A & mask]
    candidates.extend(sample["character"] & mask for sample in samples)
    candidates.extend(range(mask + 1))
    result = []
    for value in candidates:
        if value not in result:
            result.append(value)
        if len(result) == 17:
            return result
    raise ValueError("UART directed character set is incomplete")


def prepare_operations(samples, parameters):
    values = _characters(samples, parameters["data_bits"])
    operations = [
        _op("reset_prefix", Action.RESET),
        _op("initial_status", Action.READ, 0x8),
        _op("write_only_reads", Action.READ, 0x4),
        _op("write_only_reads", Action.READ, 0xC),
        _op("ignored_register_writes", Action.WRITE, 0x0, 0xFFFFFFFF, 0),
        _op("ignored_register_writes", Action.WRITE, 0x8, 0xFFFFFFFF, 5),
        _op("initial_status", Action.READ, 0x8),
        _op("interrupt_enable", Action.WRITE, 0xC, 0x10, 15),
        _op("interrupt_enable", Action.READ, 0x8),
    ]
    operations.extend(_op("loopback_fill", Action.WRITE, 0x4, value, index % 16)
                      for index, value in enumerate(values[:16]))
    operations.extend((
        _op("receive_full", Action.READ, 0x8),
        _op("receive_overrun", Action.WRITE, 0x4, values[16], 0),
        _op("receive_overrun", Action.READ, 0x8),
        _op("status_error_clear", Action.READ, 0x8),
    ))
    operations.extend(_op("loopback_drain", Action.READ, 0x0) for _ in range(16))
    operations.extend((
        _op("empty_receive", Action.READ, 0x0),
        _op("empty_status", Action.READ, 0x8),
        _op("fifo_reset", Action.WRITE, 0xC, 0x3, 10),
        _op("fifo_reset", Action.READ, 0x8),
        _op("reserved_address", Action.WRITE, 0xC, 0x10, 1),
        _op("reserved_address", Action.WRITE, 0x0, 0x12, 2),
        _op("reserved_address", Action.READ, 0xC),
        _op("reset_suffix", Action.RESET),
        _op("reset_suffix", Action.READ, 0x8),
    ))
    return operations
