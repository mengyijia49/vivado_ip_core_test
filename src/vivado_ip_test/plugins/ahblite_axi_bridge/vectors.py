import random

from vivado_ip_test.plugins.ahblite_axi_bridge.reference import read_value


def _operation(kind, address, size, hprot, response, data_width, index):
    mask = (1 << data_width) - 1
    return {"kind": kind, "address": address, "size": size, "hprot": hprot,
            "response": response, "data": ((index + 1) * 0x13579BDF2468ACE1) & mask,
            "read_data": read_value(address, data_width, index + 1)}


def prepare_operations(parameters, profile):
    lanes = parameters["data_width"] // 8
    max_size = lanes.bit_length() - 1
    operations = []
    index = 0
    for size in range(max_size + 1):
        width = 1 << size
        for offset in sorted({0, lanes - width}):
            for kind in ("write", "read"):
                address = 0x100 + size * 0x40 + offset
                operations.append(_operation(kind, address, size, index & 15, 0,
                                             parameters["data_width"], index))
                index += 1
    operations.extend((
        _operation("write", 0x400, max_size, 5, 2, parameters["data_width"], index),
        _operation("read", 0x480, max_size, 10, 3, parameters["data_width"], index + 1),
    ))
    rng = random.Random(profile.random_seed ^ 0xA4B1D6E)
    address_mask = (1 << parameters["address_width"]) - 1
    while len(operations) < profile.case_budget:
        size = rng.randrange(max_size + 1)
        width = 1 << size
        address = rng.getrandbits(parameters["address_width"]) & address_mask
        address &= ~(width - 1)
        response = 2 if len(operations) % 17 == 0 else (3 if len(operations) % 23 == 0 else 0)
        operations.append(_operation("write" if rng.randrange(2) else "read", address,
            size, rng.randrange(16), response, parameters["data_width"], len(operations)))
    return operations
