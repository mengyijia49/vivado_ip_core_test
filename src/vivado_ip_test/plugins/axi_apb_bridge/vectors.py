from vivado_ip_test.plugins.axi_apb_bridge.reference import ERROR_OFFSET, REGION_BYTES
from vivado_ip_test.plugins.common.axilite.spec import Action


def prepare_operations(samples, parameters):
    base = parameters["base_address"]
    slaves = parameters["num_slaves"]
    operations = []
    phase, vector_index = "directed", None

    def emit(action, address=0, data=0, strobe=0, awprot=0, arprot=0):
        operations.append({"command": {"action": int(action), "address": address,
            "data": data, "strobe": strobe, "s_axi_awprot": awprot,
            "s_axi_arprot": arprot}, "phase": phase, "vector_index": vector_index})

    def address(slave, offset):
        return base + slave * REGION_BYTES + offset

    emit(Action.RESET)
    for slave in range(slaves):
        for offset in (0, 4, 0x3F8):
            emit(Action.READ, address(slave, offset), arprot=(slave + offset // 4) & 7)
        emit(Action.WRITE, address(slave, 0), 0x10203040 ^ (slave * 0x11111111), 15,
             awprot=slave & 7)
        emit(Action.READ, address(slave, 0), arprot=7-(slave & 7))
        for lane in range(4):
            emit(Action.WRITE, address(slave, 4), (0x51 + slave + lane) << (lane * 8),
                 1 << lane, awprot=(slave + lane) & 7)
            emit(Action.READ, address(slave, 4), arprot=(7-slave-lane) & 7)

    phase = "all_strobes"
    for strobe in range(16):
        emit(Action.WRITE, address(0, 8), 0x89ABCDEF ^ (strobe * 0x01010101), strobe,
             awprot=strobe & 7)
        emit(Action.READ, address(0, 8), arprot=(7-strobe) & 7)

    if parameters["error_response"]:
        phase = "slave_error"
        for slave in range(slaves):
            emit(Action.WRITE, address(slave, ERROR_OFFSET), 0xDEAD0000 | slave, 15,
                 awprot=slave & 7)
            emit(Action.READ, address(slave, ERROR_OFFSET), arprot=(slave + 3) & 7)

    phase = "generated"
    for vector_index, row in enumerate(samples):
        slave = row["sample_slave"]
        offset = row["sample_word"] * 4
        emit(Action.WRITE, address(slave, offset), row["sample_data"], row["sample_strobe"],
             awprot=row["sample_prot"])
        emit(Action.READ, address(slave, offset), arprot=row["sample_prot"] ^ 7)

    phase, vector_index = "reset_persistence", None
    emit(Action.RESET)
    for slave in range(slaves):
        emit(Action.READ, address(slave, 0), arprot=slave & 7)
    emit(Action.IDLE)
    return operations
