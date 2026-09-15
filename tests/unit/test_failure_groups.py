import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.infrastructure.output import first_output_difference, iter_output_differences
from vivado_ip_test.infrastructure.output_layout import binary_output_layout, output_field_slices
from vivado_ip_test.services.failure_analysis import analyze_outputs


class FailureGroupTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for name in ("vectors", "outputs"):
            (self.root/name).mkdir()
        self.e = self.root/'vectors/expected_output.txt'
        self.a = self.root/'outputs/actual_output.txt'
        self.m = self.root/'vectors/expected_mask.txt'

    def rows(self, expected, actual, masks=None, phases=None, fields=None):
        self.e.write_text("\n".join(expected)+"\n")
        self.a.write_text("\n".join(actual)+"\n")
        if masks is not None:
            self.m.write_text("\n".join(masks)+"\n")
        phases = phases or ["generated"]*len(expected)
        records = [{"command": {"action": 3 if index == 0 else 1, "address": index*4},
                    "phase": phase, "vector_index": index} for index, phase in enumerate(phases)]
        (self.root/'vectors/vectors.json').write_text(json.dumps(records))
        (self.root/'vectors/schedule.json').write_text(json.dumps({"mapping_kind": "register_operation",
            "timing_mode": "continuous", "transaction_vector_indices": list(range(len(expected)))}))
        if fields is not None:
            (self.root/'manifest.json').write_text(json.dumps({"output_layout": binary_output_layout(fields)}))

    def test_keeps_first_failure_and_separates_later_phase_and_field(self):
        self.rows(["000", "001", "100", "000"], ["000", "000", "000", "000"],
                  phases=["reset", "isr_preservation", "master_mask", "suffix"], fields=[("irq", 1), ("data", 2)])
        evidence = analyze_outputs(self.root)
        self.assertEqual((evidence['output_index'], evidence['operation_index']), (1, 1))
        self.assertEqual(evidence['preceding_reset_operation_index'], 0)
        summary = evidence['difference_summary']
        self.assertEqual(summary['difference_rows'], 2)
        self.assertTrue(summary['all_rows_visited'])
        self.assertEqual([(g['phase'], g['output_field']) for g in summary['groups']],
                         [('isr_preservation', 'data'), ('master_mask', 'irq')])
        self.assertEqual(summary['groups'][1]['first_context']['preceding_reset_operation_index'], 0)

    def test_one_row_can_contribute_to_multiple_fields_but_is_counted_once(self):
        self.rows(['000'], ['111'], fields=[('a', 1), ('b', 2)])
        summary = analyze_outputs(self.root)['difference_summary']
        self.assertEqual(summary['difference_rows'], 1)
        self.assertEqual(summary['retained_group_count'], 2)
        self.assertEqual(sum(g['count'] for g in summary['groups']), 2)
        self.assertEqual(summary['classification'], 'OBSERVATION_GROUPS_NOT_BUG_COUNTS')

    def test_masked_unknowns_are_not_assigned_to_wrong_field(self):
        self.rows(['000', '000'], ['X01', 'X00'], masks=['011', '011'], fields=[('a', 1), ('b', 2)])
        summary = analyze_outputs(self.root)['difference_summary']
        self.assertEqual(summary['difference_rows'], 1)
        self.assertEqual([g['output_field'] for g in summary['groups']], ['b'])
        self.a.write_text('000\n0X0\n')
        summary = analyze_outputs(self.root)['difference_summary']
        self.assertEqual(summary['groups'][0]['first_output_index'], 1)
        self.assertTrue(summary['groups'][0]['first_difference']['contains_unknown_bits'])

    def test_bad_row_does_not_hide_later_mismatch_or_short_output_tail(self):
        self.rows(['00']*5, ['bad', '11'], fields=[('word', 2)])
        differences = list(iter_output_differences(self.e, self.a))
        self.assertEqual([d['kind'] for d in differences],
                         ['invalid_actual_output', 'value_mismatch', 'missing_output', 'missing_output', 'missing_output'])
        summary = analyze_outputs(self.root)['difference_summary']
        self.assertEqual(summary['difference_rows'], 5)
        self.assertEqual(summary['difference_kind_counts']['missing_output'], 3)
        self.assertTrue(summary['all_rows_visited'])

    def test_extra_rows_and_invalid_masks_remain_visible(self):
        self.rows(['00'], ['01', '11', '00'], masks=['11'])
        summary = analyze_outputs(self.root)['difference_summary']
        self.assertEqual(summary['difference_kind_counts'], {'value_mismatch': 1, 'extra_output': 2})
        self.rows(['00', '00'], ['00', '01'], masks=['1X', '11'])
        summary = analyze_outputs(self.root)['difference_summary']
        self.assertEqual(summary['difference_kind_counts'], {'invalid_output_mask': 1, 'value_mismatch': 1})

    def test_cap_limits_examples_without_stopping_scan(self):
        phases = [f'phase{i}' for i in range(30)]+['phase0']
        self.rows(['0']*31, ['1']*31, phases=phases, fields=[('irq', 1)])
        summary = analyze_outputs(self.root, group_limit=2)['difference_summary']
        self.assertEqual(summary['difference_rows'], 31)
        self.assertEqual(summary['retained_group_count'], 2)
        self.assertEqual(summary['omitted_group_memberships'], 28)
        self.assertTrue(summary['groups_truncated'])
        self.assertEqual(summary['groups'][0]['count'], 2)
        self.assertEqual(summary['groups'][0]['last_output_index'], 30)

    def test_repeated_group_has_only_three_example_indices(self):
        self.rows(['0']*100, ['1']*100, fields=[('irq', 1)])
        group = analyze_outputs(self.root)['difference_summary']['groups'][0]
        self.assertEqual(group['count'], 100)
        self.assertEqual(group['example_output_indices'], [0, 1, 2])

    def test_group_preview_is_bounded_but_first_evidence_keeps_exact_value(self):
        self.rows(['0'*10000], ['1'*10000], fields=[('wide', 10000)])
        evidence = analyze_outputs(self.root)
        self.assertEqual(len(evidence['expected']), 10000)
        preview = evidence['difference_summary']['groups'][0]['first_difference']
        self.assertEqual(len(preview['expected']), 256)
        self.assertEqual(preview['expected_width'], 10000)
        self.assertEqual(preview['truncated_row_fields'], ['expected', 'actual'])

    def test_no_layout_or_bad_width_falls_back_without_guessing_ports(self):
        self.rows(['00'], ['11'])
        summary = analyze_outputs(self.root)['difference_summary']
        self.assertEqual(summary['groups'][0]['output_field'], 'packed_output')
        self.assertEqual(summary['layout_issue_rows'], {'layout_missing_or_invalid': 1})
        (self.root/'manifest.json').write_text(json.dumps({'output_layout': binary_output_layout([('wrong', 1)])}))
        summary = analyze_outputs(self.root)['difference_summary']
        self.assertEqual(summary['layout_issue_rows'], {'layout_width_mismatch': 1})
        self.assertEqual(summary['groups'][0]['output_field'], 'packed_output')

    def test_missing_files_and_fully_masked_rows_are_not_clean_comparisons(self):
        summary = analyze_outputs(self.root)['difference_summary']
        self.assertFalse(summary['all_rows_visited'])
        self.assertEqual(summary['artifact_issues'], 1)
        self.rows(['0'], ['X'], masks=['0'])
        evidence = analyze_outputs(self.root)
        self.assertEqual(evidence['kind'], 'no_defined_output_bits')
        self.assertEqual(evidence['difference_summary']['difference_rows'], 0)
        self.m.unlink()
        (self.root/'manifest.json').write_text(json.dumps({'artifacts': {'expected_mask': str(self.m)}}))
        evidence = analyze_outputs(self.root)
        self.assertEqual(evidence['kind'], 'missing_mask_artifact')
        self.assertFalse(evidence['difference_summary']['all_rows_visited'])

    def test_scan_uses_line_iteration_not_read_text_on_outputs(self):
        self.rows(['00']*100, ['11']*100, masks=['11']*100)
        original = Path.read_text
        def guarded(path, *args, **kwargs):
            self.assertNotIn(path, (self.e, self.a, self.m))
            return original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', guarded):
            self.assertEqual(analyze_outputs(self.root)['difference_summary']['difference_rows'], 100)

    def test_read_error_after_first_difference_preserves_first_and_marks_partial_scan(self):
        self.rows(['00', '00'], ['11', '11'])
        original = Path.open
        class Broken(io.StringIO):
            def __next__(self):
                if self.tell():
                    raise OSError('read interrupted')
                return super().__next__()
        def opened(path, *args, **kwargs):
            return Broken('11\n11\n') if path == self.a else original(path, *args, **kwargs)
        with patch.object(Path, 'open', opened):
            evidence = analyze_outputs(self.root)
        self.assertEqual(evidence['kind'], 'value_mismatch')
        summary = evidence['difference_summary']
        self.assertFalse(summary['all_rows_visited'])
        self.assertEqual(summary['difference_kind_counts']['unreadable_output_artifact'], 1)

    def test_first_difference_remains_lazy_and_closes_streams(self):
        self.rows(['0', '0'], ['1', '1'])
        original = Path.open; streams = []
        class FirstOnly(io.StringIO):
            def __next__(self):
                if self.tell():
                    raise AssertionError('first difference scanned later rows')
                return super().__next__()
        def opened(path, *args, **kwargs):
            if path in (self.e, self.a):
                stream = FirstOnly('0\n0\n' if path == self.e else '1\n1\n')
                streams.append(stream)
                return stream
            return original(path, *args, **kwargs)
        with patch.object(Path, 'open', opened):
            self.assertEqual(first_output_difference(self.e, self.a)['output_index'], 0)
        self.assertTrue(all(s.closed for s in streams))

    def test_switch_routes_do_not_collapse_into_one_stream_group(self):
        self.rows(['0', '0'], ['1', '1'], fields=[('tdata', 1)])
        (self.root/'vectors/schedule.json').write_text(json.dumps({'mapping_kind': 'accepted_transaction',
            'timing_mode': 'continuous', 'transaction_vector_indices': [0, 0],
            'output_mapping': [{'input_lane': 0, 'output_port': 0}, {'input_lane': 1, 'output_port': 0}]}))
        summary = analyze_outputs(self.root)['difference_summary']
        self.assertEqual(summary['retained_group_count'], 2)
        self.assertEqual([g['first_context']['stream_route']['input_lane'] for g in summary['groups']], [0, 1])

    def test_malformed_indices_and_phases_do_not_crash_or_use_negative_index(self):
        self.rows(['0', '0'], ['1', '1'])
        (self.root/'vectors/schedule.json').write_text(json.dumps({'transaction_vector_indices': [-1, True],
                                                                'timing_mode': 'continuous'}))
        evidence = analyze_outputs(self.root)
        self.assertFalse(evidence['input_mapping_available'])
        self.assertEqual(evidence['difference_summary']['rows_without_input_mapping'], 2)

    def test_reordered_transactions_use_input_phase_not_output_position(self):
        self.rows(['0', '0'], ['1', '1'], phases=['first_input', 'second_input'])
        (self.root/'vectors/schedule.json').write_text(json.dumps({'mapping_kind': 'accepted_transaction',
            'timing_mode': 'random_gaps', 'transaction_vector_indices': [1, 0]}))
        evidence = analyze_outputs(self.root)
        self.assertEqual(evidence['vector_index'], 1)
        self.assertEqual([g['phase'] for g in evidence['difference_summary']['groups']],
                         ['second_input', 'first_input'])

    def test_sampled_cycles_keep_history_without_claiming_causal_input(self):
        self.rows(['0', '0'], ['0', '1'])
        (self.root/'vectors/cycles.json').write_text(json.dumps([{'phase': 'reset'}, {'phase': 'hold'}]))
        (self.root/'vectors/schedule.json').write_text(json.dumps({'mapping_kind': 'sampled_cycle',
                                                                'timing_mode': 'random_gaps'}))
        evidence = analyze_outputs(self.root)
        self.assertEqual(evidence['sampled_cycle'], {'phase': 'hold'})
        self.assertEqual(evidence['preceding_cycles'], [{'phase': 'reset'}])
        self.assertTrue(evidence['causal_input_not_identified'])
        group = evidence['difference_summary']['groups'][0]
        self.assertEqual(group['phase'], 'hold')
        self.assertTrue(group['first_context']['causal_input_not_identified'])

    def test_invalid_phase_and_route_metadata_do_not_change_difference_count(self):
        self.rows(['0', '0'], ['1', '1'], phases=[None, 'valid'])
        (self.root/'vectors/schedule.json').write_text(json.dumps({'mapping_kind': 'accepted_transaction',
            'timing_mode': 'continuous', 'transaction_vector_indices': [0, 1],
            'output_mapping': [None, {'input_lane': True, 'output_port': 0}]}))
        summary = analyze_outputs(self.root)['difference_summary']
        self.assertEqual(summary['difference_rows'], 2)
        self.assertEqual(summary['rows_without_input_mapping'], 1)
        self.assertEqual([g['phase'] for g in summary['groups']], ['unmapped', 'valid'])
        self.assertFalse(summary['groups'][1]['first_context']['route_mapping_available'])

    def test_valid_equal_files_have_no_groups(self):
        self.rows(['01', '00'], ['01', '00'], fields=[('word', 2)])
        evidence = analyze_outputs(self.root)
        self.assertEqual(evidence['kind'], 'no_numeric_difference')
        self.assertEqual(evidence['difference_summary']['groups'], [])

    def test_layout_validation_rejects_ambiguous_or_invalid_fields(self):
        for fields in ([], [('a', 0)], [('a', True)], [('a', 1), ('a', 2)], [('', 1)]):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                binary_output_layout(fields)
        self.assertEqual(output_field_slices(binary_output_layout([('a', 3), ('b', 1)])),
                         (('a', 0, 3), ('b', 3, 4)))
        for limit in (0, -1, True):
            with self.assertRaises(ValueError):
                analyze_outputs(self.root, group_limit=limit)
