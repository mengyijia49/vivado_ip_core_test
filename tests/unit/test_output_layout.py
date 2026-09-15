import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.infrastructure.output_layout import binary_output_layout, output_field_slices
from vivado_ip_test.plugins.common.stream.bytes import token_ports
from vivado_ip_test.plugins.divider.metadata import DividerMetadata
from vivado_ip_test.plugins.multiplier.metadata import MultiplierMetadata
from unit.plugins.cycle_helpers import plugin_case


class OutputLayoutTests(unittest.TestCase):
    def test_all_backend_layouts_describe_comparison_rows(self):
        backends = {
            "vector_logic": "common.testbench.load_metadata",
            "axis_register_slice": "common.stream.testbench.load_metadata",
            "axi_intc": "common.axilite.testbench.load_metadata",
            "axis_dwidth_converter": "common.stream.byte_testbench.load_metadata",
            "axis_switch": "axis_switch.testbench.load_metadata",
            "divider": "divider.testbench.load_divider_metadata",
            "multiplier": "multiplier.testbench.load_multiplier_metadata",
        }
        for ip_type, loader in backends.items():
            with self.subTest(ip_type=ip_type), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                plugin, case = plugin_case(ip_type, root)
                xci = root / "fake.xci"
                xci.write_text('{"ip_inst": {"ip_revision": "37"}}')
                metadata = {}
                if ip_type == "divider":
                    metadata = DividerMetadata("div_gen_0", "xilinx.com:ip:div_gen:5.1",
                        "1", "2025.2", 16, 8, 24, 18, "Unsigned")
                    fields = (("m_axis_dout_tdata", 24),)
                elif ip_type == "multiplier":
                    metadata = MultiplierMetadata("mult_gen_0", "xilinx.com:ip:mult_gen:12.0",
                        "1", "2025.2", 8, 8, "Unsigned", "Unsigned", 15, 0, 2)
                    fields = (("P", 16),)
                else:
                    spec = plugin.describe(case.parameters)
                    if ip_type == "axis_dwidth_converter":
                        ports = token_ports(spec.sink_payload)
                    elif ip_type == "axis_switch":
                        ports = spec.lane_output
                    elif ip_type == "axi_intc":
                        ports = spec.observation.outputs
                    elif ip_type == "axis_register_slice":
                        ports = spec.sink_payload
                    else:
                        ports = spec.outputs
                    fields = tuple((port.name, port.width) for port in ports)
                with patch("vivado_ip_test.plugins." + loader, return_value=(xci, metadata)):
                    artifacts = plugin.generate_testbench(case)
                manifest = json.loads(artifacts.manifest_path.read_text())
                self.assertEqual(manifest["output_layout"], binary_output_layout(fields))
                width = output_field_slices(manifest["output_layout"])[-1][2]
                with artifacts.expected_path.open() as expected:
                    rows = list(expected)
                self.assertTrue(rows)
                self.assertTrue(all(len(row.rstrip("\n")) == width for row in rows))
                if ip_type == "axis_dwidth_converter":
                    self.assertEqual([name for name, _ in fields][:3], ["end_packet", "data_byte", "data"])
                    self.assertNotEqual(width, sum(port.width for port in spec.sink_payload))
                if ip_type == "axis_switch":
                    self.assertEqual(fields[0], ("route", 2))
                    self.assertFalse(any(name.startswith("s00_") for name, _ in fields))
