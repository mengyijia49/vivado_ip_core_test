import unittest

from vivado_ip_test.plugins.processor_system_reset.reference import ProcessorResetModel


PARAMETERS = {
    "ext_reset_width": 4, "aux_reset_width": 4,
    "ext_active_high": True, "aux_active_high": True,
    "bus_reset_count": 2, "peripheral_reset_count": 3,
    "interconnect_aresetn_count": 2, "peripheral_aresetn_count": 3,
}
NORMAL = {"ext_reset_in": 0, "aux_reset_in": 0,
          "mb_debug_sys_rst": 0, "dcm_locked": 1}


class ProcessorResetReferenceTests(unittest.TestCase):
    def test_release_order_and_replicated_polarities(self):
        model = ProcessorResetModel(PARAMETERS)
        rows = [model.step(NORMAL) for _ in range(90)]
        defined = [row for row in rows if not hasattr(row["mb_reset"], "mask")]
        self.assertEqual(defined[-1], {"mb_reset": 0, "bus_struct_reset": 0,
                                      "peripheral_reset": 0, "interconnect_aresetn": 3,
                                      "peripheral_aresetn": 7})
        states = {(row["bus_struct_reset"], row["peripheral_reset"], row["mb_reset"])
                  for row in defined}
        self.assertIn((0, 7, 1), states)
        self.assertIn((0, 0, 1), states)

    def test_short_pulse_is_filtered_and_valid_pulse_is_latched(self):
        model = ProcessorResetModel(PARAMETERS)
        for _ in range(90):
            model.step(NORMAL)
        for _ in range(3):
            model.step({**NORMAL, "ext_reset_in": 1})
        for _ in range(20):
            last = model.step(NORMAL)
        self.assertEqual(last["mb_reset"], 0)
        for _ in range(4):
            model.step({**NORMAL, "ext_reset_in": 1})
        for _ in range(20):
            last = model.step({**NORMAL, "ext_reset_in": 1})
        self.assertEqual(last["bus_struct_reset"], 3)
        self.assertEqual(model.event_counts["qualified_ext_resets"], 1)

    def test_auxiliary_polarity_and_dcm_unlock(self):
        p = {**PARAMETERS, "aux_active_high": False, "aux_reset_width": 1}
        normal = {**NORMAL, "aux_reset_in": 1}
        model = ProcessorResetModel(p)
        for _ in range(90):
            model.step(normal)
        model.step({**normal, "aux_reset_in": 0})
        for _ in range(15):
            aux = model.step({**normal, "aux_reset_in": 0})
        self.assertEqual(aux["peripheral_reset"], 7)
        unlocked = model.step({**normal, "dcm_locked": 0})
        self.assertEqual(unlocked["mb_reset"], 1)
        self.assertEqual(model.event_counts["dcm_unlock_cycles"], 1)
