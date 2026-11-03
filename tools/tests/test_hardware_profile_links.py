"""Reviewed SKU links reuse immutable profiles instead of inventing duplicates."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).absolute().parents[2]
spec = importlib.util.spec_from_file_location('profile_link_tests', ROOT/'tools/build_hardware_coverage.py')
coverage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coverage)


class ProfileLinksTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chosen = coverage.selection()
        cls.models = coverage.implemented()

    def test_seven_links_reuse_existing_revisions(self):
        links = coverage.explicit_links(self.chosen, self.models)
        self.assertEqual(len(links), 7)
        self.assertEqual(len({m['key'] for m in links.values()}), 7)
        self.assertTrue(all(m['revision'] != 'selected506a-20261101-v1' for m in links.values()))
        self.assertEqual(coverage.brand('HPE'), 'hpe')
        self.assertNotEqual(coverage.token('DS423+'), coverage.token('DS423'))

    def test_selected_name_cannot_be_replaced_under_same_id(self):
        chosen = copy.deepcopy(self.chosen)
        next(m for m in chosen['models'] if m['id'] == 'nb-0228f0e0bca0aab5')['model'] = 'different model'
        with self.assertRaisesRegex(AssertionError, 'profile_link_model_substitution'):
            coverage.explicit_links(chosen, self.models)

    def test_changed_sku_revision_or_configuration_is_not_reused(self):
        for mutate in (lambda m: m['identity'].update(sku='neighbour'),
                       lambda m: m.update(revision='latest'), lambda m: m['groups'][0].update(count=1)):
            models = copy.deepcopy(self.models)
            mutate(next(m for m in models if m['key'] == 'aruba-jl355a'))
            with self.assertRaises(AssertionError):
                coverage.explicit_links(self.chosen, models)

    def test_current_coverage_has_no_duplicate_alias_count(self):
        _, counts = coverage.outputs(self.chosen, self.models, '2026-11-01')
        self.assertEqual(counts['selectedWithProfile'], 368)
        self.assertEqual(counts['selectedPending'], 138)
        self.assertEqual(counts['commercialProfiles'], 723)
        self.assertEqual(counts['additionalCommercialProfiles'], 355)


if __name__ == '__main__':
    unittest.main()
