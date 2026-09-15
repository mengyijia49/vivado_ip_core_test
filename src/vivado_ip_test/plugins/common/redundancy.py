from itertools import product


def majority(a, b, c, width):
    result = 0
    for bit in range(width):
        votes = sum((value >> bit) & 1 for value in (a, b, c))
        result |= int(votes >= 2) << bit
    return result


def voted_value(p, inputs):
    if not p["triple"] or inputs.get("TMR_Disable", 0):
        return inputs["Discrete1"]
    return majority(*(inputs[f"Discrete{i}"] for i in (1, 2, 3)), p["width"])


def comparison(p, inputs, voted=None):
    if p["input_register"] and inputs.get("Rst", 0):
        return 0
    full = (1 << p["width"]) - 1
    mask = (p["include_mask"] | (full >> 64 << 64)) & full
    a, b = (inputs[f"Discrete{i}"] & mask for i in (1, 2))
    flags = int(a != b)
    if p["triple"]:
        c = inputs["Discrete3"] & mask
        flags |= int(a != c) << 1 | int(b != c) << 2
        if p["voter_check"]:
            observed = inputs["Discrete"] if voted is None else voted
            flags |= int((observed ^ voted_value(p, inputs)) & mask != 0) << 3
    return flags


def fault_sequence(p, spec, external_vote=False):
    full = (1 << p["width"]) - 1
    names = [f"Discrete{i}" for i in range(1, 4 if p["triple"] else 3)]
    disables = (0, 1) if p["disable_port"] else (0,)
    for background in (0, full):
        for bit in range(p["width"]):
            for states in product((0, 1), repeat=len(names)):
                values = {name: (background & ~(1 << bit)) | (state << bit)
                          for name, state in zip(names, states)}
                for disabled in disables:
                    frame = spec.frame(values)
                    if p["disable_port"]:
                        frame["TMR_Disable"] = disabled
                    if external_vote:
                        frame["Discrete"] = voted_value(p, frame)
                    yield frame
                    if external_vote:
                        yield {**frame, "Discrete": frame["Discrete"] ^ (1 << bit)}
    # A different faulty lane in each replica defeats whole-word selection.
    if p["triple"] and p["width"] >= 3:
        for bit in range(p["width"]):
            one_hot = [1 << ((bit + replica) % p["width"]) for replica in range(3)]
            for invert in (0, full):
                frame = spec.frame(dict(zip(names, (value ^ invert for value in one_hot))))
                if external_vote:
                    frame["Discrete"] = invert
                yield frame
    if p["triple"] and p["width"] > 1:
        patterns = (0, full, sum(1 << bit for bit in range(0, p["width"], 2)))
        for values in product(patterns, repeat=3):
            frame = spec.frame(dict(zip(names, values)))
            if external_vote:
                frame["Discrete"] = voted_value(p, frame)
            yield frame
    if any(port.name == "Rst" for port in spec.inputs):
        frame = spec.frame({"Discrete1": full, "Discrete2": 0})
        for reset in (0, 1, 1, 0, 1, 0):
            yield {**frame, "Rst": reset}
