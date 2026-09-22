from vivado_ip_test.plugins.axi_protocol_checker.reference import SCENARIOS


def prepare_operations(samples, parameters):
    id_mask = (1 << parameters["id_width"]) - 1
    address_mask = (1 << parameters["address_width"]) - 1
    data_mask = (1 << parameters["data_width"]) - 1
    alignment_mask = ~((parameters["data_width"] // 8) - 1)
    operations = []
    for index, (scenario, _) in enumerate(SCENARIOS):
        if parameters["data_width"] == 1024 and index == 3:
            scenario = "aw_fixed_too_long"
        elif parameters["data_width"] == 1024 and index == 8:
            scenario = "ar_fixed_too_long"
        operations.append({"scenario": scenario, "scenario_code": index,
            "id": index & id_mask,
            "address": (0x100 + index * 0x40) & address_mask & alignment_mask,
            "data": ((1 << min(parameters["data_width"], 32)) - 1) & data_mask})
    for index, sample in enumerate(samples):
        scenario_index = 1 + index % (len(SCENARIOS) - 1)
        scenario = SCENARIOS[scenario_index][0]
        if parameters["data_width"] == 1024 and scenario_index == 3:
            scenario = "aw_fixed_too_long"
        elif parameters["data_width"] == 1024 and scenario_index == 8:
            scenario = "ar_fixed_too_long"
        operations.append({"scenario": scenario,
            "scenario_code": scenario_index, "id": sample["sample_id"] & id_mask,
            "address": sample["sample_address"] & address_mask & alignment_mask,
            "data": sample["sample_data"] & data_mask})
    return operations
