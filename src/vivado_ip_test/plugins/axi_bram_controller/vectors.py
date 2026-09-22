from vivado_ip_test.plugins.common.axilite.spec import Action


def prepare_operations(samples, parameters):
    last = parameters["depth"] * 4 - 4
    middle = (last // 8) * 4
    addresses = tuple(dict.fromkeys((0, 4, 8, middle, last - 4, last)))
    operations = []
    phase, vector_index = "directed", None
    protection = {"s_axi_awprot": 0, "s_axi_arprot": 0}

    def emit(action, address=0, data=0, strobe=0):
        operations.append({"command": {"action": int(action), "address": address,
            "data": data, "strobe": strobe, **protection},
            "phase": phase, "vector_index": vector_index})

    def write(address, data, strobe=15):
        emit(Action.WRITE, address, data, strobe)

    def read(address):
        emit(Action.READ, address)

    emit(Action.RESET)
    for address in addresses:
        read(address)

    patterns = (0, 0xFFFFFFFF, 0xAAAAAAAA, 0x55555555, 0x01234567, 0x89ABCDEF)
    for index, address in enumerate(addresses):
        for strobe in range(16):
            protection["s_axi_awprot"] = strobe & 7
            value = patterns[(index + strobe) % len(patterns)] ^ ((address * 0x9E3779B1) & 0xFFFFFFFF)
            write(address, value, strobe)
            protection["s_axi_arprot"] = 7 - (strobe & 7)
            read(address)
        for neighbor in addresses:
            read(neighbor)

    phase = "byte_lanes"
    target = addresses[len(addresses) // 2]
    write(target, 0)
    for lane in range(4):
        write(target, (0x31 + lane) << (8 * lane), 1 << lane)
        read(target)

    phase = "reset_persistence"
    write(0, 0xC35AA53C)
    write(last, 0x7E819966)
    emit(Action.RESET)
    read(0)
    read(last)

    phase = "generated"
    for vector_index, row in enumerate(samples):
        address = row["sample_word"] * 4
        protection["s_axi_awprot"] = row["s_axi_awprot"]
        protection["s_axi_arprot"] = row["s_axi_arprot"]
        write(address, row["sample_data"], row["sample_strobe"])
        read(address)
        if vector_index % 8 == 0:
            read(addresses[vector_index % len(addresses)])

    phase, vector_index = "reset_suffix", None
    emit(Action.RESET)
    for address in addresses:
        read(address)
    emit(Action.IDLE)
    return operations
