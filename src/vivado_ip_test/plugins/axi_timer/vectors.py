from itertools import product

from vivado_ip_test.plugins.common.axilite.spec import Action
from vivado_ip_test.plugins.axi_timer.reference import ARHT, CAPT, ENALL, ENIT, ENT, GENT, LOAD, MDT, TINT, UDT


def prepare_operations(samples, p):
    pins = {f'capturetrig{i}': 1-int(p[f'trigger{i}_high']) for i in range(2)}
    operations = []
    phase, sample_index = 'reset_prefix', None
    mask = (1 << p['count_width'])-1

    def emit(action, address=0, data=0, strobe=0, cycles=0):
        operations.append({'command': {'action': int(action), 'address': address, 'data': data,
            'strobe': strobe, **pins, 'freeze': 1, 'run_cycles': cycles},
            'phase': phase, 'vector_index': sample_index})

    def write(address, value, strobe=15):
        emit(Action.WRITE, address, value, strobe)

    def read(address):
        emit(Action.READ, address)

    def window(cycles):
        emit(Action.WINDOW, cycles=cycles)

    def reset():
        for i in range(2):
            pins[f'capturetrig{i}'] = 1-int(p[f'trigger{i}_high'])
        emit(Action.RESET)

    def load(i, value, control, strobe=15):
        write(16*i, LOAD | TINT)
        write(16*i+4, value, strobe)
        read(16*i+4)
        read(16*i+8)
        write(16*i, control)

    def capture(i):
        pins[f'capturetrig{i}'] = int(p[f'trigger{i}_high'])
        emit(Action.DRIVE)
        emit(Action.IDLE)
        pins[f'capturetrig{i}'] = 1-int(p[f'trigger{i}_high'])
        emit(Action.DRIVE)

    def read_all():
        for i in range(p['channels']):
            for offset in (0, 4, 8):
                read(16*i+offset)
        read(12)
        read(28)

    reset()
    read_all()
    for i in range(p['channels']):
        base = 16*i
        phase = f'timer{i}_load_bits_strobes'
        for index, value in enumerate((0, 0xFFFFFFFF, *(1 << bit for bit in range(32)),
                                      *(0xFFFFFFFF ^ (1 << bit) for bit in range(32)))):
            load(i, value, LOAD, index % 16)
            window(3)
            read(base+8)
        phase = f'timer{i}_readonly_counter'
        load(i, mask//3, 0)
        for value in (0, 0xFFFFFFFF, *(1 << bit for bit in range(32))):
            write(base+8, value)
            read(base+8)
        phase = f'timer{i}_rollover_and_freeze'
        for down, reload, generate, irq in product((0, 1), repeat=4):
            control = ENT | down*UDT | reload*ARHT | generate*GENT | irq*ENIT
            for distance in (0, 1, 3, 7):
                value = distance if down else mask-distance
                load(i, value, control)
                for cycles in (1, 1, 1, 1, 33):
                    window(cycles)
                    read(base+8)
                    read(base)
                emit(Action.IDLE)
                read(base+8)
                write(base, control | TINT)
                read(base)
                window(2)
                read(base+8)
                write(base, control & ~ENT)
                window(5)
                read(base+8)
        phase = f'timer{i}_capture'
        for down, generate in product((0, 1), repeat=2):
            load(i, 1 if down else mask-1, MDT | ENT | down*UDT | generate*GENT)
            window(4)
            read(base+8)
            read(base)
        for overwrite, enabled, irq in product((0, 1), repeat=3):
            control = MDT | ENT | overwrite*ARHT | enabled*CAPT | irq*ENIT
            load(i, 64, control)
            read(base+4)
            capture(i)
            read(base)
            window(7)
            capture(i)
            read(base+4)
            capture(i)
            read(base+4)
            write(base, control | TINT)
            read(base)
            write(base, control & ~ENT)
            capture(i)
            read(base+4)
        write(base, 0)
    phase = 'reserved_registers'
    for address in (12, 28):
        write(address, 0xFFFFFFFF, 0)
        read_all()
    if p['channels'] == 2:
        phase = 'enable_all'
        load(0, 10, 0)
        load(1, 20, 0)
        for channel in (0, 1):
            write(channel*16, ENALL)
            read_all()
            window(7)
            read_all()
            write(channel*16, ENT)
            read_all()
    reset()
    phase = 'generated'
    for sample_index, row in enumerate(samples):
        if sample_index % 32 == 0:
            reset()
        for i in range(p['channels']):
            control = row['control']
            load(i, row['load'] ^ (i*0x55555555), control, row['strobe'])
            window(row['cycles']+1)
            read(i*16+8)
            read(i*16)
            capture(i)
            read(i*16+4)
            write(i*16, control | TINT)
            read(i*16)
            write(i*16, 0)
    phase, sample_index = 'reset_suffix', None
    reset()
    read_all()
    emit(Action.IDLE)
    return operations
