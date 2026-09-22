from vivado_ip_test.plugins.axi_timebase_wdt.reference import EWDT1, WDS, WRS
from vivado_ip_test.plugins.common.axilite.spec import Action


def prepare_operations(samples, parameters):
    operations = []
    phase, vector_index = "reset_prefix", None

    def emit(action, address=0, data=0, strobe=0, cycles=0):
        operations.append({"command": {"action": int(action), "address": address,
            "data": data, "strobe": strobe, "freeze": 1, "run_cycles": cycles},
            "phase": phase, "vector_index": vector_index})

    def write(address, data, strobe=15):
        emit(Action.WRITE, address, data, strobe)

    def read(address):
        emit(Action.READ, address)

    def window(cycles):
        emit(Action.WINDOW, cycles=cycles)

    def reset():
        emit(Action.RESET)

    def read_state():
        read(0)
        read(8)
        read(12)

    period = 1 << parameters["interval"]
    reset()
    read_state()
    phase = "configured_interval"
    for strobe in range(16):
        write(12, parameters["interval"], strobe)
        read(12)
    write(0, EWDT1)
    window(period - 16)
    read_state()
    window(32)
    read_state()

    phase = "clear_and_second_expiration"
    write(0, EWDT1 | WDS)
    read_state()
    window(period + 16)
    read_state()
    window(period + 16)
    read_state()
    reset()
    write(0, WRS)
    read_state()

    phase = "enable_behavior"
    reset()
    write(0, EWDT1)
    write(0, 0)
    write(4, 0, 15)
    window(period + 16)
    read_state()

    phase = "second_enable_and_runtime_width"
    reset()
    write(12, 8)
    read(12)
    write(4, 1)
    window(240)
    read_state()
    window(32)
    read_state()
    write(0, WDS)

    phase = "generated"
    for vector_index, row in enumerate(samples):
        reset()
        write(12, 8)
        write(0, EWDT1)
        window(row["sample_cycles"] + 1)
        read_state()

    phase, vector_index = "reset_suffix", None
    reset()
    write(0, WRS | WDS)
    read_state()
    emit(Action.IDLE)
    return operations
