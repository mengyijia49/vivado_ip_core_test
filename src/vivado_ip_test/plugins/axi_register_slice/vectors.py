FORWARD_CHANNELS = ("aw", "w", "ar")
RESPONSE_CHANNELS = ("b", "r")


def payload(parameters, channel, variant=0):
    data_mask = (1 << parameters["data_width"]) - 1
    id_mask = (1 << parameters["id_width"]) - 1
    address_user_mask = (1 << parameters["address_user_width"]) - 1
    data_user_mask = (1 << parameters["data_user_width"]) - 1
    response_user_mask = (1 << parameters["response_user_width"]) - 1
    values = {
        "aw": {"id": id_mask ^ variant, "addr": 0x12345678 ^ variant, "len": 3,
               "size": parameters["data_width"].bit_length() - 4, "burst": 1, "lock": 0,
               "cache": 3, "prot": 5, "region": 6, "qos": 9,
               "user": address_user_mask ^ variant},
        "w": {"data": data_mask ^ (0x55 + variant),
              "strb": (1 << (parameters["data_width"] // 8)) - 1,
              "last": 1, "user": data_user_mask ^ variant},
        "b": {"id": (id_mask ^ 2 ^ variant) & id_mask, "resp": 2,
              "user": response_user_mask ^ variant},
        "ar": {"id": (id_mask ^ 1 ^ variant) & id_mask, "addr": 0x89ABCDF0 ^ variant,
               "len": 1, "size": parameters["data_width"].bit_length() - 4,
               "burst": 2, "lock": 1, "cache": 12, "prot": 2, "region": 10,
               "qos": 6, "user": address_user_mask ^ variant},
        "r": {"id": (id_mask ^ 3 ^ variant) & id_mask,
              "data": data_mask ^ (0xAA + variant), "resp": 1, "last": 1,
              "user": data_user_mask ^ variant},
    }
    return values[channel]


def directed_sequence(parameters):
    yield {"aresetn": 0}
    yield {"aresetn": 0}
    yield {"aresetn": 0}
    yield {"aresetn": 0}
    for _ in range(4):
        yield {"aresetn": 1}

    for channel in (*FORWARD_CHANNELS, *RESPONSE_CHANNELS):
        source = "s_axi" if channel in FORWARD_CHANNELS else "m_axi"
        sink = "m_axi" if channel in FORWARD_CHANNELS else "s_axi"
        values = {f"{source}_{channel}{field}": value
                  for field, value in payload(parameters, channel).items()}
        for _ in range(4):
            yield {**values, f"{source}_{channel}valid": 1,
                   f"{sink}_{channel}ready": 0}
        for _ in range(4):
            yield {**values, f"{source}_{channel}valid": 1,
                   f"{sink}_{channel}ready": 1}
        for _ in range(4):
            yield {**values, f"{source}_{channel}valid": 0,
                   f"{sink}_{channel}ready": 1}

    all_channels = {}
    for channel in (*FORWARD_CHANNELS, *RESPONSE_CHANNELS):
        source = "s_axi" if channel in FORWARD_CHANNELS else "m_axi"
        sink = "m_axi" if channel in FORWARD_CHANNELS else "s_axi"
        all_channels.update({f"{source}_{channel}{field}": value
                             for field, value in payload(parameters, channel, 1).items()})
        all_channels[f"{source}_{channel}valid"] = 1
        all_channels[f"{sink}_{channel}ready"] = 1
    for _ in range(5):
        yield all_channels

    yield {"aresetn": 0}
    yield {"aresetn": 0}
    yield {"aresetn": 0}
    for _ in range(4):
        yield {"aresetn": 1}
