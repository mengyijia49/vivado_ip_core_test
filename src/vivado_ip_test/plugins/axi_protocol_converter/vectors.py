from vivado_ip_test.plugins.axi_protocol_converter.reference import BURSTS, RESPONSES


def operation(kind, ident, address, beats=1, size=2, burst="Increment", prot=0,
              data=0, strobe=15, response="Okay", error_beat=-1,
              hold_cycles=0, w_before_aw=False):
    return {"kind": kind, "id": ident, "address": address, "beats": beats,
            "size": size, "burst": BURSTS[burst], "burst_name": burst,
            "prot": prot, "data": data, "strobe": strobe,
            "response": RESPONSES[response], "response_name": response,
            "error_beat": error_beat, "hold_cycles": hold_cycles,
            "w_before_aw": w_before_aw}


def prepare_operations(samples, parameters):
    width = parameters["data_width"]
    lanes = width // 8
    size = lanes.bit_length() - 1
    ident_mask = (1 << parameters["id_width"]) - 1
    address_mask = (1 << parameters["address_width"]) - 1
    full_strobe = (1 << lanes) - 1
    beats = parameters["burst_length"]
    wrap_beats = beats if beats in {2, 4, 8, 16} else 2
    operations = [
        operation("write", 1 & ident_mask, 0x100, beats=beats, size=size,
                  data=(1 << width) - 1, strobe=full_strobe, hold_cycles=3),
        operation("read", 1 & ident_mask, 0x100, beats=beats, size=size,
                  hold_cycles=2),
        operation("write", 2 & ident_mask, 0x240, beats=min(beats, 4), size=1,
                  burst="Fixed", prot=5, data=0x8877665544332211,
                  strobe=0x3 & full_strobe, response="Slave_Error", error_beat=0,
                  w_before_aw=beats == 1),
        operation("read", 2 & ident_mask, 0x240, beats=min(beats, 4), size=1,
                  burst="Fixed", prot=5, response="Decode_Error", error_beat=0),
        operation("write", 3 & ident_mask, 0x27C, beats=wrap_beats, size=2,
                  burst="Wrap", prot=2, data=0xA55A5AA5, strobe=full_strobe),
        operation("read", 3 & ident_mask, 0x27C, beats=wrap_beats, size=2,
                  burst="Wrap", prot=2),
    ]
    for index, sample in enumerate(samples):
        address = sample["sample_address"] & address_mask & ~(lanes - 1)
        ident = sample["sample_id"] & ident_mask
        operations.append(operation("write", ident, address, size=size,
            prot=sample["sample_prot"], data=sample["sample_data"],
            strobe=sample["sample_strobe"] & full_strobe,
            hold_cycles=index % 3, w_before_aw=bool(index & 1)))
        operations.append(operation("read", ident, address, size=size,
            prot=sample["sample_prot"], hold_cycles=(index + 1) % 3))
    return operations
