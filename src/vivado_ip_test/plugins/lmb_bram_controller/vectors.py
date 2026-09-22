def directed_sequence(parameters, spec):
    width = parameters["data_width"]
    lanes = width // 8
    full_data = (1 << width) - 1
    full_be = (1 << lanes) - 1
    base = parameters["base_address"]
    last = base + parameters["address_size"] - lanes

    yield spec.frame({"LMB_Rst": 1})
    yield spec.frame()

    for address in dict.fromkeys((base, base + lanes, base + parameters["address_size"] // 2, last)):
        yield spec.frame({"LMB_ABus": address, "LMB_AddrStrobe": 1,
                          "LMB_ReadStrobe": 1, "BRAM_Din_A": address ^ full_data})
        for byte_enable in range(full_be + 1):
            yield spec.frame({"LMB_ABus": address, "LMB_WriteDBus": address ^ 0xA5A55A5A,
                              "LMB_AddrStrobe": 1, "LMB_WriteStrobe": 1,
                              "LMB_BE": byte_enable})

    outside = []
    if base:
        outside.append(base - lanes)
    if last + lanes <= (1 << parameters["address_width"]) - 1:
        outside.append(last + lanes)
    outside.append((base ^ (1 << (parameters["address_width"] - 1))) &
                   ((1 << parameters["address_width"]) - 1))
    for address in dict.fromkeys(outside):
        yield spec.frame({"LMB_ABus": address, "LMB_AddrStrobe": 1,
                          "LMB_ReadStrobe": 1, "BRAM_Din_A": full_data})

    if parameters["protection"]:
        for protection in range(4):
            for write in (0, 1):
                yield spec.frame({"LMB_ABus": base, "LMB_Prot": protection,
                                  "LMB_WriteDBus": full_data, "LMB_AddrStrobe": 1,
                                  "LMB_ReadStrobe": 1 - write, "LMB_WriteStrobe": write,
                                  "LMB_BE": full_be, "BRAM_Din_A": 0x12345678})

    yield spec.frame({"LMB_ABus": base, "LMB_AddrStrobe": 1,
                      "LMB_ReadStrobe": 1, "LMB_WriteStrobe": 1,
                      "LMB_BE": full_be, "LMB_WriteDBus": full_data})
    yield spec.frame({"LMB_Rst": 1, "LMB_ABus": base, "LMB_AddrStrobe": 1,
                      "LMB_ReadStrobe": 1})
    yield spec.frame()
