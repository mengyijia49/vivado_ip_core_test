def directed_sequence(p):
    ext_off, ext_on = int(not p["ext_active_high"]), int(p["ext_active_high"])
    aux_off, aux_on = int(not p["aux_active_high"]), int(p["aux_active_high"])
    normal = {"ext_reset_in": ext_off, "aux_reset_in": aux_off,
              "mb_debug_sys_rst": 0, "dcm_locked": 1}
    cycles = []

    def add(count, **changes):
        cycles.extend({**normal, **changes} for _ in range(count))

    add(80)
    add(max(1, p["ext_reset_width"] - 1), ext_reset_in=ext_on)
    add(12)
    add(p["ext_reset_width"] + 12, ext_reset_in=ext_on)
    add(80)
    add(max(1, p["aux_reset_width"] - 1), aux_reset_in=aux_on)
    add(12)
    add(p["aux_reset_width"] + 12, aux_reset_in=aux_on)
    add(80)
    add(p["ext_reset_width"] + 12, mb_debug_sys_rst=1)
    add(80)
    add(8, dcm_locked=0)
    add(80)
    return tuple(cycles)
