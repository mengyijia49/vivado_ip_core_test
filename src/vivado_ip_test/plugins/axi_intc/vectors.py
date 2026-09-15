from vivado_ip_test.plugins.common.axilite.spec import Action
from vivado_ip_test.plugins.axi_intc.reference import ISR, IPR, IER, IAR, SIE, CIE, IVR, MER, ILR, WORD


def prepare_operations(samples, p):
    width = len(p["input_modes"])
    hardware_mask = (1 << width)-1
    total = width+p["software_interrupts"]
    mask = (1 << total)-1
    software_mask = mask ^ hardware_mask
    inactive = sum(1 << i for i, mode in enumerate(p["input_modes"]) if mode in ("falling", "low"))
    pins = inactive
    operations = []
    phase, sample_index = "reset_prefix", None
    registers = [ISR, IER, MER]
    registers += [a for a, key in ((IPR, "has_ipr"), (IVR, "has_ivr"), (ILR, "has_ilr")) if p[key]]

    def emit(action, address=0, data=0):
        operations.append({"command": {"action": int(action), "address": address,
            "data": data, "strobe": 15 if action == Action.WRITE else 0, "intr": pins},
            "phase": phase, "vector_index": sample_index})

    def write(address, data):
        emit(Action.WRITE, address, data)

    def observe():
        for address in registers:
            emit(Action.READ, address)

    def reset(hardware=False):
        nonlocal pins
        pins = inactive
        emit(Action.RESET)
        if hardware:
            write(MER, 3)
            write(IAR, WORD)

    def drive(value):
        nonlocal pins
        pins = value
        emit(Action.DRIVE)

    reset()
    observe()
    # Reset each software trigger group so a lost ISR bit cannot affect hardware tests.
    for hardware in (False, True):
        available = range(width, total) if hardware else range(total)
        for bit in available:
            phase = f"isr_preservation_hie{int(hardware)}_bit{bit}"
            reset(hardware)
            write(IER, WORD)
            write(MER, 3 if hardware else 1)
            write(ISR, 1 << bit)
            observe()
            write(ISR, 0)
            observe()
            write(ISR, 1 << ((bit+1) % total))
            observe()
            write(IAR, WORD)
            observe()
    phase = "ier_atomic_and_reserved_bits"
    reset()
    for value in (0, WORD, *(1 << bit for bit in range(32)), 0xAAAAAAAA, 0x55555555):
        write(IER, value)
        observe()
        if p["has_sie"]:
            write(SIE, (~value) & WORD)
            write(SIE, 0)
            observe()
        if p["has_cie"]:
            write(CIE, value)
            write(CIE, 0)
            observe()
    for bit in range(width):
        phase = f"hardware_capture_ack_bit{bit}"
        reset(True)
        drive(inactive ^ (1 << bit))
        observe()
        write(IER, 1 << bit)
        observe()
        write(MER, 0)
        observe()
        write(MER, WORD)
        write(IAR, 0)
        observe()
        write(IAR, 1 << bit)
        observe()
        drive(inactive)
        write(IAR, WORD)
        observe()
        drive(inactive ^ (1 << bit))
        drive(inactive)
        observe()
        write(IAR, WORD)
        observe()
    phase = "hardware_priority_and_ilr"
    reset(True)
    drive(inactive ^ hardware_mask)
    drive(inactive)
    for bit in range(width):
        write(IER, hardware_mask & ~((1 << bit)-1))
        observe()
        if p["has_ilr"]:
            for limit in (0, bit, bit+1, total, WORD):
                write(ILR, limit)
                observe()
    phase = "hie_write_once_and_read_only"
    reset(True)
    write(IER, WORD)
    write(ISR, hardware_mask)
    observe()
    for value in (0, 1, 2, WORD):
        write(MER, value)
        observe()
    for address in (IPR, IVR):
        if address in registers:
            write(address, WORD)
            observe()
    phase = "reset_pending"
    drive(inactive ^ hardware_mask)
    observe()
    reset()
    observe()
    write(IER, WORD)
    write(MER, 1)
    write(ISR, mask)
    observe()
    for sample_index, row in enumerate(samples):
        phase = "generated_hardware"
        if sample_index % 16 == 0:
            reset(True)
        drive(row["pins"])
        write(IER, row["enable_bits"])
        write(MER, row["master_enable"])
        if p["has_ilr"]:
            write(ILR, row["priority_limit"])
        observe()
        write(IAR, row["clear_bits"])
        observe()
        if p["has_sie"]:
            write(SIE, row["set_bits"])
            observe()
        if p["has_cie"]:
            write(CIE, row["clear_bits"])
            observe()
        if software_mask:
            phase = "generated_software"
            write(ISR, row["set_bits"] & software_mask)
            observe()
    phase, sample_index = "reset_suffix", None
    reset()
    observe()
    emit(Action.IDLE)
    return operations
