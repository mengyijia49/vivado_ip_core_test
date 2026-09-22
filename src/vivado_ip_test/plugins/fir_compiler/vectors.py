def prepare_frames(frames, spec, parameters):
    width = parameters["data_width"]
    low, high = -(1 << (width - 1)), (1 << (width - 1)) - 1
    values = [0, low, low, low, high, -1, 1, high, 0]
    directed = []
    for index, value in enumerate(values):
        frame = {port.name: 0 for port in spec.payload}
        frame["tdata"] = value & ((1 << width) - 1)
        if "tlast" in frame:
            frame["tlast"] = int(index % 4 == 3)
        if "tuser" in frame:
            frame["tuser"] = (index * 7) & ((1 << parameters["user_width"]) - 1)
        directed.append(frame)
    return directed + [dict(frame) for frame in frames]
