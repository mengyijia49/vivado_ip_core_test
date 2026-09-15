import os
import unittest

from .isolated_probe import run_isolated_probe


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class IsrWriteProbeTests(unittest.TestCase):
    def test_isr_zero_and_separate_bit_writes(self):
        self.run_probe(False)

    def test_isr_writes_with_fresh_source_libraries(self):
        self.run_probe(True)

    def run_probe(self, fresh_source):
        run_isolated_probe(self, name="isr_write", marker="ISR_WRITE", observation_count=14,
            fresh_source=fresh_source, parameters={"C_NUM_INTR_INPUTS": "1", "C_NUM_SW_INTR": "2",
                "C_KIND_OF_INTR": "0x00000001", "C_KIND_OF_EDGE": "0x00000001",
                "C_ASYNC_INTR": "0x00000000", "C_HAS_ILR": "0"})
