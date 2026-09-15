import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import Port
from vivado_ip_test.plugins.common.metadata import load_metadata


class ChunkedXciParameterTests(unittest.TestCase):
    def check_value(self, value, succeeds):
        expression = ",".join(f"tdata[{bit}]" for bit in range(4096))
        spec = SimpleNamespace(settings={"TDATA_REMAP": expression}, model_parameters={"WIDTH": 8},
            inputs=(Port("Din", 8),), outputs=(Port("Dout", 8),), clock=None)
        instance = {"component_reference": "xilinx.com:ip:axis_subset_converter:1.1",
            "parameters": {"component_parameters": {"TDATA_REMAP": [{"value": value(expression)}]},
                           "model_parameters": {"WIDTH": [{"value": "8"}]}},
            "boundary": {"ports": {
                "Din": [{"direction": "in", "size_left": "7", "size_right": "0"}],
                "Dout": [{"direction": "out", "size_left": "7", "size_right": "0"}]}}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "proj/ip_test.srcs/sources_1/ip/dut_0/dut_0.xci"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"ip_inst": instance}))
            before = path.read_bytes()
            if succeeds:
                self.assertEqual(load_metadata(root, spec, "axis_subset_converter", "1.1")[0], path)
            else:
                with self.assertRaises(PluginError):
                    load_metadata(root, spec, "axis_subset_converter", "1.1")
            self.assertEqual(path.read_bytes(), before)

    def test_scalar_and_chunked_strings_have_identical_meaning(self):
        self.check_value(lambda text: text, True)
        self.check_value(lambda text: [text[i:i + 999] for i in range(0, len(text), 999)], True)

    def test_changed_missing_or_reordered_chunks_still_fail(self):
        for make in (lambda text: [text[:999], text[1000:]],
                     lambda text: [text[999:], text[:999]],
                     lambda text: [text[:999], "X" + text[1000:]]):
            with self.subTest(make=make):
                self.check_value(make, False)

    def test_malformed_chunk_arrays_are_not_coerced(self):
        for value in ([], [None], [True], [1], [["text"]], [{"text": "value"}]):
            with self.subTest(value=value):
                self.check_value(lambda text: value, False)
