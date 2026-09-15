def expected_transactions(frames, spec):
    result = []
    for frame in frames:
        output = {}
        for port in spec.lane_payload:
            if port.name in {"tdata", "tstrb", "tkeep", "tuser"}:
                output[port.name] = sum(frame[f"s{lane:02d}_{port.name}"] << (lane * port.width)
                                        for lane in range(spec.input_lane_count))
            else:
                output[port.name] = frame[f"s{spec.primary_lane:02d}_{port.name}"]
        result.append(output)
    return result
