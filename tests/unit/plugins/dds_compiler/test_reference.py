import unittest

from vivado_ip_test.plugins.dds_compiler.reference import DdsPhaseModel


class DdsPhaseReferenceTests(unittest.TestCase):
    def test_increment_offset_wrap_and_backpressure(self):
        model = DdsPhaseModel({"phase_width": 8, "phase_increment": 241,
                               "phase_offset": 37}, latency=2)
        reset = {"aresetn": 0, "m_axis_phase_tready": 1}
        run = {"aresetn": 1, "m_axis_phase_tready": 1}
        hold = {"aresetn": 1, "m_axis_phase_tready": 0}
        first = model.step(reset)
        self.assertEqual(first["m_axis_phase_tvalid"], 0)
        self.assertEqual(first["m_axis_phase_tdata"].mask, 0)
        self.assertEqual(model.step(run)["m_axis_phase_tvalid"], 0)
        self.assertEqual(model.step(run)["m_axis_phase_tvalid"], 0)
        first_valid = model.step(run)
        self.assertEqual(first_valid["m_axis_phase_tvalid"], 1)
        self.assertEqual(first_valid["m_axis_phase_tdata"].value, 22)
        self.assertEqual(model.step(run)["m_axis_phase_tdata"].value, 7)
        self.assertEqual(model.step(hold)["m_axis_phase_tdata"].value, 7)
        self.assertEqual(model.step(run)["m_axis_phase_tdata"].value, 248)

    def test_reset_restarts_latency_and_phase(self):
        model = DdsPhaseModel({"phase_width": 3, "phase_increment": 3,
                               "phase_offset": 2}, latency=1)
        run = {"aresetn": 1, "m_axis_phase_tready": 1}
        reset = {"aresetn": 0, "m_axis_phase_tready": 0}
        model.step(reset)
        model.step(run)
        self.assertEqual(model.step(run)["m_axis_phase_tdata"].value, 5)
        self.assertEqual(model.step(reset)["m_axis_phase_tvalid"], 1)
        self.assertEqual(model.step(reset)["m_axis_phase_tvalid"], 0)
        self.assertEqual(model.step(run)["m_axis_phase_tvalid"], 0)
        self.assertEqual(model.step(run)["m_axis_phase_tdata"].value, 5)
