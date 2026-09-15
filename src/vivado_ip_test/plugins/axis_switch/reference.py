def route_for_destination(destination, routes):
    matches = [branch for branch, (low, high) in enumerate(routes) if low <= destination <= high]
    if len(matches) != 1:
        raise ValueError("目的地址必须恰好匹配一个输出")
    return matches[0]


def expected_transactions(frames, spec):
    results = []
    for frame in frames:
        result = {}
        for lane in range(spec.input_lane_count):
            prefix = f"s{lane:02d}_"
            result[prefix + "route"] = route_for_destination(frame.get(prefix + "tdest", 0), spec.routes)
            result.update({prefix + p.name: frame[prefix + p.name] for p in spec.lane_payload})
        results.append(result)
    return results
