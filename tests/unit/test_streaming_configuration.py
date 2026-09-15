from contextlib import closing
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import weakref
from unittest.mock import patch

from vivado_ip_test.application.selection import select_cases
from vivado_ip_test.configuration import ConfigError, iter_test_cases, load_test_cases
from vivado_ip_test.configuration.uniqueness import UniqueKeys
from unit.test_configuration import valid_config
from unit.test_pipeline import make_case


class UniqueKeysTests(unittest.TestCase):
    def test_small_sets_do_not_create_a_database(self):
        with patch('vivado_ip_test.configuration.uniqueness.TemporaryDirectory') as directory:
            with UniqueKeys(memory_limit=2) as keys:
                self.assertTrue(keys.add('first'))
                self.assertTrue(keys.add('second'))
                self.assertFalse(keys.add('first'))
                directory.assert_not_called()

    def test_spill_preserves_exact_keys_and_removes_temporary_files(self):
        with UniqueKeys(memory_limit=2) as keys:
            for value in ('A', 'a', 'a\0b', 'a\0c', '', 'x' * 100000):
                self.assertTrue(keys.add(value))
                self.assertFalse(keys.add(value))
            self.assertFalse(keys.add('A'))
            self.assertEqual(keys._keys, set())
            directory = Path(keys._directory.name)
            self.assertTrue((directory / 'keys.sqlite').is_file())
            self.assertEqual(keys._database.execute('PRAGMA journal_mode').fetchone(), ('memory',))
            self.assertEqual(keys._database.execute('PRAGMA integrity_check').fetchone(), ('ok',))
        self.assertFalse(directory.exists())

    def test_full_database_raises_and_removes_the_incomplete_index(self):
        with self.assertRaisesRegex(sqlite3.OperationalError, 'full'):
            with UniqueKeys(memory_limit=0) as keys:
                keys.add('first')
                directory = Path(keys._directory.name)
                pages = keys._database.execute('PRAGMA page_count').fetchone()[0]
                keys._database.execute(f'PRAGMA max_page_count={pages}')
                keys.add('x' * 100000)
        self.assertFalse(directory.exists())

    def test_cleanup_on_consumer_error_and_database_creation_error(self):
        with self.assertRaisesRegex(RuntimeError, 'consumer'):
            with UniqueKeys(memory_limit=0) as keys:
                keys.add('key')
                directory = Path(keys._directory.name)
                raise RuntimeError('consumer')
        self.assertFalse(directory.exists())
        with UniqueKeys(memory_limit=0) as keys, patch(
                'vivado_ip_test.configuration.uniqueness.sqlite3.connect',
                side_effect=sqlite3.OperationalError('no space')):
            with self.assertRaises(sqlite3.OperationalError):
                keys.add('key')
            self.assertIsNone(keys._directory)
            self.assertIsNone(keys._database)

    def test_rejects_invalid_key_and_memory_limits(self):
        for limit in (-1, True, 2.0):
            with self.assertRaises(ValueError):
                UniqueKeys(limit)
        with UniqueKeys() as keys, self.assertRaises(TypeError):
            keys.add(1)


class StreamingConfigurationTests(unittest.TestCase):
    def write(self, root, name, value):
        path = root / name
        path.write_text(json.dumps(value))
        return path

    def sweep(self, prefix='scan', values=(8, 16, 32)):
        template = deepcopy(valid_config()['cases'][0])
        template.pop('case_id')
        return {'schema_version': 2, 'sweeps': [{'case_prefix': prefix,
                'template': template, 'axes': {'dividend_width': list(values)}}]}

    def test_list_and_iterator_preserve_include_sweep_and_exploration_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, 'first.json', valid_config())
            self.write(root, 'second.json', self.sweep())
            path = self.write(root, 'all.json', {'schema_version': 2,
                'includes': ['first.json', 'second.json'],
                'exploration': {'seeds': [12, 4], 'timing_modes': ['bursts', 'continuous']}})
            cases = list(iter_test_cases(path))
            self.assertEqual(cases, load_test_cases(path))
            expected = [(name, seed, mode) for name in ('arbitrary_case_name',
                'scan__dividend_width_8', 'scan__dividend_width_16', 'scan__dividend_width_32')
                for seed in (12, 4) for mode in ('bursts', 'continuous')]
            self.assertEqual([c.case_id for c in cases], [f'{name}__seed{seed}__{mode}' for name, seed, mode in expected])
            self.assertEqual([(c.verification.random_seed, c.verification.timing_mode) for c in cases],
                             [(seed, mode) for _, seed, mode in expected])

    def test_cases_are_produced_lazily_and_parameters_are_independent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write(Path(directory), 'matrix.json', self.sweep())
            with closing(iter_test_cases(path)) as stream:
                first = next(stream)
                first.parameters['divisor_width'] = 999
                second = next(stream)
                self.assertEqual(second.parameters['divisor_width'], 8)
            self.assertEqual(len(load_test_cases(path)), 3)

    def test_late_duplicate_and_malformed_sweep_are_not_hidden(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, 'first.json', self.sweep())
            duplicate = {'schema_version': 2, 'includes': ['first.json', 'first.json']}
            path = self.write(root, 'all.json', duplicate)
            with self.assertRaisesRegex(ConfigError, '唯一'):
                list(iter_test_cases(path))
            invalid = self.sweep('second')
            invalid['sweeps'].append({'case_prefix': 'bad'})
            path = self.write(root, 'invalid.json', invalid)
            with self.assertRaises(ConfigError):
                list(iter_test_cases(path))

    def test_iterator_close_releases_spilled_id_index(self):
        created = []
        def index():
            value = UniqueKeys(memory_limit=1)
            created.append(value)
            return value
        with tempfile.TemporaryDirectory() as directory, patch(
                'vivado_ip_test.configuration.loader.UniqueKeys', side_effect=index):
            path = self.write(Path(directory), 'matrix.json', self.sweep())
            with closing(iter_test_cases(path)) as stream:
                next(stream)
                next(stream)
                scratch = Path(created[0]._directory.name)
                self.assertTrue(scratch.is_dir())
            self.assertFalse(scratch.exists())

    def test_index_error_is_a_configuration_error(self):
        with tempfile.TemporaryDirectory() as directory, patch(
                'vivado_ip_test.configuration.loader.UniqueKeys.add',
                side_effect=sqlite3.OperationalError('no space')):
            path = self.write(Path(directory), 'matrix.json', valid_config())
            with self.assertRaisesRegex(ConfigError, '临时索引'):
                list(iter_test_cases(path))


class SelectionTests(unittest.TestCase):
    def test_unselected_cases_are_released_during_iteration(self):
        references = []
        def candidates():
            for i in range(10000):
                case = replace(make_case(), case_id=str(i))
                references.append(weakref.ref(case))
                if i % 100 == 99:
                    self.assertLessEqual(sum(r() is not None for r in references), 3)
                    references.clear()
                yield case
        chosen, _ = select_cases(candidates(), validate=lambda values: None, limit=1)
        self.assertEqual([c.case_id for c in chosen], ['0'])

    def test_limit_keeps_one_case_but_validates_all_matching_cases(self):
        validated = []
        cases = (replace(make_case(), case_id=str(i)) for i in range(10000))
        selected, skipped = select_cases(cases, validate=lambda values: validated.extend(c.case_id for c in values), limit=1)
        self.assertEqual([c.case_id for c in selected], ['0'])
        self.assertEqual(len(validated), 10000)
        self.assertEqual(skipped, 0)

    def test_errors_after_limit_and_in_excluded_files_are_still_raised(self):
        def malformed():
            yield make_case()
            raise ConfigError('late invalid file')
        with self.assertRaisesRegex(ConfigError, 'late invalid'):
            select_cases(malformed(), validate=lambda values: None, limit=1)
        def reject(values):
            if next(iter(values)).case_id == 'bad':
                raise ConfigError('late invalid parameter')
        with self.assertRaisesRegex(ConfigError, 'late invalid parameter'):
            select_cases([make_case(), replace(make_case(), case_id='bad')], validate=reject, limit=1)

    def test_resume_requires_complete_equality_and_limit_follows_skips(self):
        first = make_case()
        changed = replace(first, verification=replace(first.verification, random_seed=999))
        next_case = replace(first, case_id='next')
        chosen, skipped = select_cases([changed, next_case], validate=lambda values: None,
                                      completed={first.case_id: [first]}, limit=1)
        self.assertEqual(chosen, [changed])
        self.assertEqual(skipped, 0)
        chosen, skipped = select_cases([first, next_case], validate=lambda values: None,
                                      completed={first.case_id: [first]}, limit=1)
        self.assertEqual(chosen, [next_case])
        self.assertEqual(skipped, 1)

    def test_ip_and_case_filters_and_overrides_match_previous_order(self):
        first = make_case()
        second = replace(first, ip_type='counter', case_id='second')
        third = replace(second, case_id='third')
        validated = []
        selected, _ = select_cases([first, second, third], validate=validated.extend,
            ip_types=['counter'], case_ids=['second'], seed=7, budget=20)
        self.assertEqual(selected, validated)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].verification.random_seed, 7)
        self.assertEqual(selected[0].verification.case_budget, 20)
        self.assertEqual(first, make_case())

    def test_unknown_selections_and_seed_override_of_exploration_fail(self):
        for changes in ({'ip_types': ['missing']}, {'case_ids': ['missing']},
                        {'ip_types': ['counter'], 'case_ids': [make_case().case_id]}):
            with self.assertRaises(ConfigError):
                select_cases([make_case(), replace(make_case(), ip_type='counter', case_id='other')],
                             validate=lambda values: None, **changes)
        with self.assertRaisesRegex(ConfigError, 'exploration.seeds'):
            select_cases([replace(make_case(), case_id='case__seed0__continuous')],
                         validate=lambda values: None, seed=5, case_ids=['missing'])
