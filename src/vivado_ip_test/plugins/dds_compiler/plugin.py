from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin
from vivado_ip_test.plugins.dds_compiler.reference import DdsPhaseModel
from vivado_ip_test.plugins.dds_compiler.vectors import directed_sequence


LATENCY = 4


class DdsCompilerPlugin(CycleIpPlugin):
    ip_type = "dds_compiler"
    ip_name = "dds_compiler"
    version = "6.0"

    def describe(self, p):
        validate_parameters(p, {
            "phase_width": range(3, 49),
            "phase_increment": range(1 << 48),
            "phase_offset": range(1 << 48),
        })
        limit = 1 << p["phase_width"]
        if p["phase_increment"] >= limit or p["phase_offset"] >= limit:
            raise PluginError("DDS phase increment and offset must fit phase_width")
        bits = lambda value: format(value, f"0{p['phase_width']}b")
        settings = {
            "PartsPresent": "Phase_Generator_only",
            "Parameter_Entry": "Hardware_Parameters",
            "Phase_Width": p["phase_width"],
            "Phase_Increment": "Fixed",
            "PINC1": bits(p["phase_increment"]),
            "Phase_offset": "Fixed" if p["phase_offset"] else "None",
            "Has_Phase_Out": True,
            "Has_TREADY": True,
            "Has_ARESETn": True,
            "Resync": False,
            "Latency_Configuration": "Configurable",
            "Latency": LATENCY,
        }
        if p["phase_offset"]:
            settings["POFF1"] = bits(p["phase_offset"])
        return CycleSpec(
            inputs=(Port("aresetn", scalar=True), Port("m_axis_phase_tready", scalar=True)),
            outputs=(Port("m_axis_phase_tvalid", scalar=True),
                     Port("m_axis_phase_tdata", p["phase_width"])),
            settings=settings,
            model_parameters={"C_ACCUMULATOR_WIDTH": p["phase_width"], "C_HAS_PHASEGEN": 1,
                              "C_HAS_SINCOS": 0, "C_LATENCY": LATENCY,
                              "C_HAS_TREADY": 1, "C_HAS_ARESETN": 1,
                              "C_M_PHASE_TDATA_WIDTH": p["phase_width"]},
            model_factory=lambda: DdsPhaseModel(p, LATENCY),
            clock="aclk", prefix=directed_sequence(LATENCY), flush_cycles=16,
            neutral={"aresetn": 1, "m_axis_phase_tready": 1},
            idle_values={"aresetn": 1, "m_axis_phase_tready": 1},
            masked_outputs=True,
        )
