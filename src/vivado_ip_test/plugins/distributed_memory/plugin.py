from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin
from vivado_ip_test.plugins.distributed_memory.reference import DistributedMemoryModel


class DistributedMemoryPlugin(CycleIpPlugin):
    ip_type = "distributed_memory"
    ip_name = "dist_mem_gen"
    version = "8.0"

    def describe(self, p):
        validate_parameters(p, {"width": range(1, 257), "depth": range(16, 4097, 16),
                                "initial_value": range(0, 1 << 256),
                                "memory_type": {"single_port_ram", "dual_port_ram"}})
        validate_parameters({"initial_value": p["initial_value"]},
                            {"initial_value": range(0, 1 << p["width"])})
        dual = p["memory_type"] == "dual_port_ram"
        address_width = (p["depth"] - 1).bit_length()
        address = Port("a", address_width, maximum=p["depth"] - 1)
        inputs = (address, Port("d", p["width"]), Port("we", scalar=True))
        outputs = (Port("spo", p["width"]),)
        if dual:
            inputs += (Port("dpra", address_width, maximum=p["depth"] - 1),)
            outputs += (Port("dpo", p["width"]),)
        prefix = []
        mask = (1 << p["width"]) - 1
        for phase in ("initial_read", "write", "read", "invert", "read"):
            for address in range(p["depth"]):
                value = (address * 0x9E3779B1) & mask
                row = {"a": address, "we": int(phase in {"write", "invert"}),
                       "d": value ^ mask if phase == "invert" else value}
                if dual:
                    row["dpra"] = address if phase == "write" else p["depth"] - address - 1
                prefix.append(row)
        return CycleSpec(
            inputs=inputs, outputs=outputs, clock="clk", prefix=tuple(prefix),
            settings={"data_width": p["width"], "depth": p["depth"], "memory_type": p["memory_type"],
                      "default_data": format(p["initial_value"], "x"), "default_data_radix": 16,
                      "coefficient_file": "no_coe_file_loaded", "input_options": "non_registered",
                      "output_options": "non_registered", "Pipeline_Stages": 0,
                      "dual_port_address": "non_registered", "input_clock_enable": False},
            model_parameters={"C_WIDTH": p["width"], "C_DEPTH": p["depth"],
                              "C_MEM_TYPE": 2 if dual else 1, "C_REG_A_D_INPUTS": 0,
                              "C_REG_DPRA_INPUT": 0, "C_PIPELINE_STAGES": 0,
                              "C_DEFAULT_DATA": format(p["initial_value"], f"0{p['width']}b")},
            model_factory=lambda: DistributedMemoryModel(p),
            model_parameter_radices={"C_DEFAULT_DATA": 2},
        )
