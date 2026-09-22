from vivado_ip_test.plugins.tmr_inject.reference import AIR, CR, IIR, protection_allowed


def _allowed_write_protection(parameters):
    if not parameters["protection"]:
        return 0
    return next(value for value in range(4)
                if protection_allowed(parameters["protection_mask"], value, True))


def _denied_write_protection(parameters):
    if not parameters["protection"]:
        return None
    return next((value for value in range(4)
                 if not protection_allowed(parameters["protection_mask"], value, True)), None)


def directed_sequence(parameters, spec):
    base = parameters["base_address"]
    target = 0x12345678
    instruction = 0xDEADC0DE
    bram_data = 0x89ABCDEF
    write_prot = _allowed_write_protection(parameters)

    def control_write(offset, data, protection=write_prot, byte_enable=15):
        values = {"LMB_ABus": base + offset, "LMB_WriteDBus": data,
                  "LMB_AddrStrobe": 1, "LMB_WriteStrobe": 1, "LMB_BE": byte_enable}
        if parameters["protection"]:
            values["LMB_Prot"] = protection
        return spec.frame(values)

    def fetch(address, data=bram_data, ready=1, **extra):
        values = {"MB_LMB_ABus": address, "MB_LMB_AddrStrobe": 1,
                  "MB_LMB_ReadStrobe": 1, "MB_LMB_BE": 15,
                  "BRAM_Sl_DBus": data, "BRAM_Sl_Ready": ready, **extra}
        if parameters["protection"]:
            values["MB_LMB_Prot"] = 2
        return spec.frame(values)

    enable = parameters["magic"] | (parameters["cpu_id"] << 8) | (1 << 10)
    yield spec.frame({"Rst": 1})
    yield spec.frame()

    yield fetch(0x40, data=0x01020304, ready=0, BRAM_Sl_Wait=1,
                BRAM_Sl_UE=1, BRAM_Sl_CE=1)
    yield spec.frame({"MB_LMB_ABus": 0x44, "MB_LMB_WriteDBus": 0x55667788,
                      "MB_LMB_AddrStrobe": 1, "MB_LMB_WriteStrobe": 1,
                      "MB_LMB_BE": 5, "BRAM_Sl_Ready": 1})
    yield spec.frame({"LMB_ABus": base, "LMB_AddrStrobe": 1,
                      "LMB_ReadStrobe": 1})
    yield spec.frame({"LMB_ABus": base + parameters["address_size"],
                      "LMB_AddrStrobe": 1, "LMB_ReadStrobe": 1})

    yield control_write(AIR, target)
    yield spec.frame()
    yield control_write(IIR, instruction)
    yield spec.frame()
    yield control_write(CR, enable ^ 1)
    yield spec.frame()
    yield fetch(target)
    yield spec.frame()
    yield control_write(CR, enable ^ (1 << 8))
    yield spec.frame()
    yield fetch(target)
    yield spec.frame()

    denied = _denied_write_protection(parameters)
    if denied is not None:
        yield control_write(IIR, 0xBAD0BAD0, protection=denied)
        yield spec.frame()

    yield control_write(CR, enable, byte_enable=1)
    yield spec.frame()
    yield fetch(target ^ 0x100)
    yield fetch(target + 3)
    yield spec.frame({"BRAM_Sl_Ready": 1})
    yield fetch(target)
    yield spec.frame()

    yield control_write(CR, enable)
    yield spec.frame()
    yield fetch(target, data=0x11223344, ready=0)
    yield spec.frame({"BRAM_Sl_DBus": 0xA5A55A5A, "BRAM_Sl_Ready": 1})
    yield fetch(target)

    if parameters["protection"]:
        for protection in range(4):
            yield spec.frame({"LMB_ABus": base, "LMB_Prot": protection,
                              "LMB_AddrStrobe": 1, "LMB_WriteStrobe": 1,
                              "LMB_WriteDBus": 0, "LMB_BE": 15})

    yield spec.frame({"Rst": 1, "MB_LMB_ABus": target,
                      "MB_LMB_AddrStrobe": 1, "BRAM_Sl_DBus": bram_data})
    yield spec.frame()
