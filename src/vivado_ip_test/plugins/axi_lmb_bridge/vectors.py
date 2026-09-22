from vivado_ip_test.plugins.axi_lmb_bridge.reference import BURSTS, FAULTS


def operation(kind, ident, address, beats=1, size=2, burst="Increment", prot=0,
              data=0, strobe=15, fault="Normal", wait_cycles=0, hold_cycles=0,
              w_before_aw=False):
    return {"kind": kind, "id": ident, "address": address, "beats": beats,
            "size": size, "burst": BURSTS[burst], "burst_name": burst,
            "prot": prot, "data": data, "strobe": strobe,
            "fault": FAULTS[fault], "fault_name": fault,
            "wait_cycles": wait_cycles, "hold_cycles": hold_cycles,
            "w_before_aw": w_before_aw}


def prepare_operations(samples, parameters):
    width = parameters["data_width"]
    lanes = width // 8
    id_mask = (1 << parameters["id_width"]) - 1
    address_mask = (1 << parameters["address_width"]) - 1
    full_strobe = (1 << lanes) - 1
    operations = [
        operation("write", 1 & id_mask, 0x100, data=0x1020304050607080,
                  strobe=full_strobe),
        operation("read", 1 & id_mask, 0x100, hold_cycles=3),
        operation("write", 2 & id_mask, 0x1F0, beats=4, burst="Increment", prot=1,
                  data=(1 << width) - 1, strobe=full_strobe, wait_cycles=2),
        operation("read", 2 & id_mask, 0x1F0, beats=4, burst="Increment", prot=1,
                  wait_cycles=1, hold_cycles=2),
        operation("write", 3 & id_mask, 0x220, beats=2, size=1, burst="Fixed",
                  data=0x8877665544332211, strobe=0x3 & full_strobe),
        operation("read", 3 & id_mask, 0x220, beats=2, size=1, burst="Fixed"),
        operation("write", 4 & id_mask, 0x23C, beats=4, size=2, burst="Wrap",
                  data=0xA55A5AA5, strobe=full_strobe, w_before_aw=True),
        operation("read", 4 & id_mask, 0x23C, beats=4, size=2, burst="Wrap"),
        operation("write", 5 & id_mask, 0x280, data=0xDEADBEEF, strobe=0),
        operation("write", 6 & id_mask, 0x2A0, data=0x12345678, strobe=full_strobe,
                  fault="Address_Error"),
        operation("read", 6 & id_mask, 0x2A0, fault="Address_Error"),
        operation("write", 7 & id_mask, 0x2C0, data=0xCAFEBABE, strobe=full_strobe,
                  fault="Uncorrectable_Error"),
        operation("read", 7 & id_mask, 0x2C0, fault="Uncorrectable_Error"),
        operation("write", 1 & id_mask, 0x2D0, data=0x13579BDF, strobe=full_strobe),
        operation("read", 1 & id_mask, 0x2D0),
    ]
    for index, sample in enumerate(samples):
        address = sample["sample_address"] & address_mask & ~0x3
        ident = sample["sample_id"] & id_mask
        wait = sample["sample_wait"] & 3
        strobe = sample["sample_strobe"] & full_strobe
        operations.append(operation("write", ident, address, prot=sample["sample_prot"],
            data=sample["sample_data"], strobe=strobe, wait_cycles=wait,
            hold_cycles=index % 3, w_before_aw=bool(index & 1)))
        operations.append(operation("read", ident, address, prot=sample["sample_prot"],
            wait_cycles=(wait + 1) & 3, hold_cycles=(index + 1) % 4))
    return operations
