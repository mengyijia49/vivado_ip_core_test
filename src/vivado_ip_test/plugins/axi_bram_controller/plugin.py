from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.axilite.plugin import AxiLiteIpPlugin
from vivado_ip_test.plugins.common.axilite.spec import AxiLiteSpec
from vivado_ip_test.plugins.common.cycle import Port, validate_parameters
from vivado_ip_test.plugins.axi_bram_controller.reference import AxiBramModel
from vivado_ip_test.plugins.axi_bram_controller.vectors import prepare_operations


DEPTHS = (1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144)


class AxiBramControllerPlugin(AxiLiteIpPlugin):
    ip_type = "axi_bram_controller"
    ip_name = "axi_bram_ctrl"
    version = "4.1"

    def describe(self, p):
        validate_parameters(p, {"depth": range(1024, 262145), "single_port": bool})
        if p["depth"] not in DEPTHS:
            raise PluginError("AXI BRAM Controller depth must be a supported power of two")
        address_width = (p["depth"] * 4 - 1).bit_length()
        side_inputs = (Port("s_axi_awprot", 3), Port("s_axi_arprot", 3))
        generated = (Port("sample_word", (p["depth"] - 1).bit_length(), maximum=p["depth"] - 1),
                     Port("sample_data", 32), Port("sample_strobe", 4), *side_inputs)
        settings = {"DATA_WIDTH": 32, "PROTOCOL": "AXI4LITE", "BMG_INSTANCE": "INTERNAL",
                    "MEM_DEPTH": p["depth"], "SINGLE_PORT_BRAM": int(p["single_port"]),
                    "USE_ECC": 0, "FAULT_INJECT": 0}
        models = {"C_BRAM_INST_MODE": "INTERNAL", "C_S_AXI_ADDR_WIDTH": address_width,
                  "C_S_AXI_DATA_WIDTH": 32, "C_S_AXI_PROTOCOL": "AXI4LITE",
                  "C_SINGLE_PORT_BRAM": int(p["single_port"])}
        parameters = dict(p)
        return AxiLiteSpec(address_width, side_inputs, (), generated, settings, models,
            lambda: AxiBramModel(parameters), lambda rows: prepare_operations(rows, parameters),
            minimum_ip_revision=13, settle_cycles=2, reset_cycles=20)
