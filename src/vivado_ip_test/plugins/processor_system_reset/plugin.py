from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin
from vivado_ip_test.plugins.processor_system_reset.reference import ProcessorResetModel
from vivado_ip_test.plugins.processor_system_reset.vectors import directed_sequence


class ProcessorSystemResetPlugin(CycleIpPlugin):
    ip_type = "processor_system_reset"
    ip_name = "proc_sys_reset"
    version = "5.0"

    def describe(self, p):
        validate_parameters(p, {
            "ext_reset_width": range(1, 17),
            "aux_reset_width": range(1, 17),
            "ext_active_high": bool,
            "aux_active_high": bool,
            "bus_reset_count": range(1, 9),
            "peripheral_reset_count": range(1, 17),
            "interconnect_aresetn_count": range(1, 9),
            "peripheral_aresetn_count": range(1, 17),
        })
        settings = {
            "C_EXT_RST_WIDTH": p["ext_reset_width"],
            "C_AUX_RST_WIDTH": p["aux_reset_width"],
            "C_EXT_RESET_HIGH": int(p["ext_active_high"]),
            "C_AUX_RESET_HIGH": int(p["aux_active_high"]),
            "C_NUM_BUS_RST": p["bus_reset_count"],
            "C_NUM_PERP_RST": p["peripheral_reset_count"],
            "C_NUM_INTERCONNECT_ARESETN": p["interconnect_aresetn_count"],
            "C_NUM_PERP_ARESETN": p["peripheral_aresetn_count"],
        }
        inactive_ext = int(not p["ext_active_high"])
        inactive_aux = int(not p["aux_active_high"])
        return CycleSpec(
            inputs=(Port("ext_reset_in", scalar=True), Port("aux_reset_in", scalar=True),
                    Port("mb_debug_sys_rst", scalar=True), Port("dcm_locked", scalar=True)),
            outputs=(Port("mb_reset", scalar=True),
                     Port("bus_struct_reset", p["bus_reset_count"]),
                     Port("peripheral_reset", p["peripheral_reset_count"]),
                     Port("interconnect_aresetn", p["interconnect_aresetn_count"]),
                     Port("peripheral_aresetn", p["peripheral_aresetn_count"])),
            settings=settings,
            model_parameters={"C_FAMILY": "artix7", **settings},
            model_factory=lambda: ProcessorResetModel(p),
            clock="slowest_sync_clk", prefix=lambda: directed_sequence(p), flush_cycles=80,
            neutral={"ext_reset_in": inactive_ext, "aux_reset_in": inactive_aux,
                     "mb_debug_sys_rst": 0, "dcm_locked": 1},
            idle_values={"ext_reset_in": inactive_ext, "aux_reset_in": inactive_aux,
                         "mb_debug_sys_rst": 0, "dcm_locked": 1},
            masked_outputs=True,
        )
