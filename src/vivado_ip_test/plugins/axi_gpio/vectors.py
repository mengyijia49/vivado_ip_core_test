from vivado_ip_test.plugins.common.axilite.spec import Action


REGISTERS = (0, 4, 8, 12, 0x11C, 0x120, 0x128)


def prepare_operations(samples, p):
    pins = {f"gpio{'2' if i == 2 else ''}_io_i": 0
            for i in range(1, p["channels"]+1) if p[f"mode{i}"] != "output"}
    operations = []
    phase, sample_index = "directed", None

    def emit(action, address=0, data=0, strobe=0):
        operations.append({"command": {"action": int(action), "address": address,
            "data": data, "strobe": strobe, **pins}, "phase": phase, "vector_index": sample_index})

    def reset():
        pins.update(dict.fromkeys(pins, 0))
        emit(Action.RESET)

    def write(address, value, strobe=15):
        emit(Action.WRITE, address, value, strobe)

    def read(address):
        emit(Action.READ, address)

    reset()
    for address in REGISTERS:
        read(address)
    for i in range(1, p["channels"]+1):
        base, mask, mode = (i-1)*8, (1 << p[f"width{i}"])-1, p[f"mode{i}"]
        pin = f"gpio{'2' if i == 2 else ''}_io_i"
        if mode == "bidirectional":
            write(base+4, 0)
            read(base+4)
        for index, value in enumerate((0, 0xFFFFFFFF, *(1 << bit for bit in range(32)),
                                       *(0xFFFFFFFF ^ (1 << bit) for bit in range(32)))):
            write(base, value, index % 16)
            read(base)
        if mode == "bidirectional":
            write(base, 0)
            write(base+4, mask)
            write(base, 0xFFFFFFFF)
            read(base)
            write(base+4, 0)
            read(base+4)
            write(base+4, mask)
        if mode != "output":
            for value in (0, mask, *(1 << bit for bit in range(p[f"width{i}"])), 0):
                pins[pin] = value
                emit(Action.DRIVE)
                read(base)
                if p["interrupt"]:
                    read(0x120)
    if p["interrupt"]:
        for gier in (0, 0x80000000, 0xFFFFFFFF, 0):
            write(0x11C, gier)
            read(0x11C)
            for enabled in range(4):
                write(0x128, enabled)
                read(0x128)
                for toggled in (0, 1, 2, 3, 3, 2, 1):
                    write(0x120, toggled)
                    read(0x120)
    phase = "unimplemented_registers"
    missing = ([] if p["channels"] == 2 else [8, 12]) + ([] if p["interrupt"] else [0x11C, 0x120, 0x128])
    for address in missing:
        for value in (0, 0xFFFFFFFF, 0xA5A5A5A5):
            write(address, value)
            for target in REGISTERS:
                read(target)
    reset()
    for sample_index, row in enumerate(samples):
        phase = "generated"
        if sample_index % 32 == 0:
            reset()
        pins.update(dict.fromkeys(pins, 0))
        emit(Action.DRIVE)
        for i in range(1, p["channels"]+1):
            if p[f"mode{i}"] == "bidirectional":
                write((i-1)*8+4, row[f"tri{i}"])
                read((i-1)*8+4)
        for i in range(1, p["channels"]+1):
            if p[f"mode{i}"] != "output":
                pins[f"gpio{'2' if i == 2 else ''}_io_i"] = row[f"pins{i}"]
        emit(Action.DRIVE)
        for i in range(1, p["channels"]+1):
            read((i-1)*8)
            write((i-1)*8, row[f"data{i}"], row["strobe"])
            read((i-1)*8)
        if p["interrupt"]:
            write(0x11C, row["global_enable"] << 31)
            write(0x128, row["irq_enable"])
            write(0x120, row["irq_toggle"])
            for address in (0x11C, 0x128, 0x120):
                read(address)
    phase, sample_index = "reset_suffix", None
    reset()
    for address in REGISTERS:
        read(address)
    emit(Action.IDLE)
    return operations
