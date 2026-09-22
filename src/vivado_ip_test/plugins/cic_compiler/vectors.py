from vivado_ip_test.plugins.cic_compiler.reference import encode_signed, signed_value


def prepare_frames(frames, parameters):
    width = parameters["input_width"]
    low, high = -(1 << (width - 1)), (1 << (width - 1)) - 1
    values = [0, 1, 0, 0, 0, -1, 0, 0, high, high, low, low,
              1, -1, 1, -1, *([1] * (2 * parameters["rate"])),
              *([0] * (2 * parameters["rate"]))]
    prepared = [{"tdata": encode_signed(value, width)} for value in values]
    for frame in frames:
        value = signed_value(frame["tdata"], width)
        prepared.append({"tdata": encode_signed(value, width)})
    if parameters["filter_type"] == "Decimation":
        remainder = len(prepared) % parameters["rate"]
        prepared.extend({"tdata": 0} for _ in range((-remainder) % parameters["rate"]))
    return prepared


def source_timing(schedule, profile, parameters):
    spacing = parameters["rate"] - 1 if parameters["filter_type"] == "Interpolation" else 0
    return [(gap + spacing,) for gap in schedule.gaps]
