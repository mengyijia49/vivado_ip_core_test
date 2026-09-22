from collections import Counter

from vivado_ip_test.plugins.common.cycle import DefinedBits


MODE_VALUES = {"Bypass": 0, "Full": 1, "Forward": 2, "Reverse": 3, "Light": 7}


class ChannelModel:
    def __init__(self, mode, fields):
        self.mode = MODE_VALUES[mode]
        self.fields = tuple(fields)
        self.payload = {name: 0 for name in fields}
        self.skid = dict(self.payload)
        self.storage = dict(self.payload)
        self.valid = 0
        self.ready = 0
        self.has_storage = False
        self.reset_d0 = 0
        self.reset_d1 = 0

    def step(self, valid_in, payload_in, ready_down, reset_n):
        valid_in = int(bool(valid_in))
        ready_down = int(bool(ready_down))
        reset_n = int(bool(reset_n))
        if self.mode == 0:
            return valid_in, dict(payload_in), ready_down, bool(valid_in and ready_down)

        old_valid = self.valid
        old_ready = self.ready
        old_d0, old_d1 = self.reset_d0, self.reset_d1
        accepted = bool(valid_in and old_ready)

        if self.mode == 1:
            new_ready = 0 if not old_d0 else int(
                ready_down or not old_valid or (old_ready and not valid_in))
            new_valid = 0 if not old_d1 else int(
                valid_in or not old_ready or (old_valid and not ready_down))
            new_payload = dict(self.payload)
            if ready_down or not old_valid:
                new_payload = dict(payload_in if old_ready else self.skid)
            if old_ready:
                self.skid = dict(payload_in)
            self.payload = new_payload
            self.ready, self.valid = new_ready, new_valid

        elif self.mode == 2:
            pre_ready = int((ready_down or not old_valid) and old_d0)
            accepted = bool(valid_in and pre_ready)
            if accepted:
                self.payload = dict(payload_in)
            self.valid = 0 if not old_d0 else int(valid_in or (old_valid and not ready_down))

        elif self.mode == 3:
            next_storage = self.has_storage
            if valid_in and old_ready and not ready_down:
                next_storage = True
            elif self.has_storage and ready_down and (not valid_in or not old_ready):
                next_storage = False
            if accepted:
                self.storage = dict(payload_in)
            self.has_storage = False if not old_d0 else next_storage
            self.ready = 0 if not old_d0 else int(ready_down or not next_storage)

        elif self.mode == 7:
            if not old_d0:
                self.ready = 0
            elif not old_d1:
                self.ready = 1
            else:
                self.ready = int(ready_down if old_valid else not valid_in)
            self.valid = 0 if not old_d1 else int(valid_in if old_ready else not ready_down)
            if not old_valid:
                self.payload = dict(payload_in)

        if reset_n:
            self.reset_d1, self.reset_d0 = old_d0, 1
        else:
            self.reset_d0 = self.reset_d1 = 0

        if self.mode == 2:
            ready_up = int((ready_down or not self.valid) and self.reset_d0)
            return self.valid, dict(self.payload), ready_up, accepted
        if self.mode == 3:
            payload = self.storage if self.has_storage else payload_in
            valid = int((valid_in or self.has_storage) and self.reset_d1)
            return valid, dict(payload), self.ready, accepted
        return self.valid, dict(self.payload), self.ready, accepted


CHANNELS = {
    "aw": ("forward", ("id", "addr", "len", "size", "burst", "lock", "cache", "prot", "region", "qos", "user")),
    "w": ("forward", ("data", "strb", "last", "user")),
    "b": ("response", ("id", "resp", "user")),
    "ar": ("forward", ("id", "addr", "len", "size", "burst", "lock", "cache", "prot", "region", "qos", "user")),
    "r": ("response", ("id", "data", "resp", "last", "user")),
}


class AxiRegisterSliceModel:
    def __init__(self, parameters):
        self.p = dict(parameters)
        self.event_counts = Counter()
        self.channels = {
            name: ChannelModel(parameters[f"{direction}_mode"], fields)
            for name, (direction, fields) in CHANNELS.items()
        }

    def step(self, inputs):
        outputs = {}
        for name, (direction, fields) in CHANNELS.items():
            source = "s_axi" if direction == "forward" else "m_axi"
            sink = "m_axi" if direction == "forward" else "s_axi"
            payload = {field: inputs[f"{source}_{name}{field}"] for field in fields}
            valid, result, ready, accepted = self.channels[name].step(
                inputs[f"{source}_{name}valid"], payload,
                inputs[f"{sink}_{name}ready"], inputs["aresetn"])
            mode = self.p[f"{direction}_mode"]
            for field, value in result.items():
                key = f"{sink}_{name}{field}"
                outputs[key] = (DefinedBits(value, 0, f"{name} 无有效传输时负载未定义")
                                if not valid and mode != "Bypass" else value)
            outputs[f"{sink}_{name}valid"] = valid
            outputs[f"{source}_{name}ready"] = ready
            if accepted:
                self.event_counts[f"{name}_accepted"] += 1
            if valid and not inputs[f"{sink}_{name}ready"]:
                self.event_counts[f"{name}_backpressure"] += 1
        return outputs
