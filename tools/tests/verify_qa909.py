"""After selection, evolve the historical guide test and verify all actual metadata."""
import importlib.util
import json
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / 'evidence/s1-20261018/sesenta-tandas-850-909'


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    assert not (E / 'QA-TESTS-01.json').exists()
    matrix = json.loads((E / 'QA-MATRIX-909.json').read_bytes())
    assert matrix['otherStepsAndExpectedUnchanged']
    # Keep the old test exact as evidence; only its planned-phase expectations evolve.
    path = ROOT / 'tools/tests/test_qa_relations_status848.py'
    baseline = E / 'qa-guide/source-before/test_qa_relations_status848.py'
    before = path.read_bytes()
    assert before == baseline.read_bytes()
    text = before.decode()
    start = text.index('    def test_source_only_case_is_never_available(self):')
    end = text.index('    def test_current_available_counts_and_generated_guides(self):', start)
    replacement = '''    def test_case_requires_the_closed_announcement_pair(self):
        catalog = json.loads(guide.CATALOG.read_bytes())
        case = next(c for c in catalog['cases'] if c['id'] == 'QA-78')
        self.assertEqual(case['feature'], 'adminGroupRelationsAnnouncementGui')
        manifest = json.loads((ROOT / 'evidence/s1-20261018/tanda-849/CANDIDATA849.json').read_bytes())
        pair = dict(bundle=manifest['distributions']['frontend']['app.js'], dll=manifest['distributions']['server']['RackClick.Server.dll'])
        self.assertEqual(catalog['adminGroupRelationsAnnouncementBuilds'], [pair])
        def available(ctx):
            return json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']['QA-78']['available']
        ctx = dict(configured=True, roles=True, restored=True, origin='', **pair)
        self.assertTrue(available(ctx))
        for delta in [dict(bundle='future'), dict(dll='future'), dict(roles=False), dict(configured=False)]:
            self.assertFalse(available({**ctx, **delta}))
        self.assertFalse(available(guide.context(profile='manual')))

'''
    nl = '\r\n' if b'\r\n' in before else '\n'
    text = text[:start] + replacement.replace('\n', nl) + text[end:]
    text = text.replace('Keep the source-only accessibility correction blocked in current manual QA.', 'Require the closed849 announcement pair; older QA remains blocked.')
    assert "('rc9', 77)" in text
    text = text.replace("('rc9', 77)", "('rc9', 78)")
    path.write_bytes(text.encode())
    base = module('base_guide_tests909', 'tools/tests/test_qa_guide.py')
    excel = module('excel_guide_tests909', 'tools/tests/test_rc9_excel_guide832.py')
    status = module('status_guide_tests909', 'tools/tests/test_qa_relations_status848.py')
    guide = base.guide
    catalog = json.loads(guide.CATALOG.read_bytes())
    def cases(ctx):
        return json.loads(guide.render(catalog, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']
    class Actual849(unittest.TestCase):
        def test_actual_profiles_and_negative_identity_roles_configuration(self):
            ctx = guide.context(profile='rc9')
            self.assertTrue(cases(ctx)['QA-78']['available'])
            for delta in [matrix['sourcePair'], dict(bundle='wrong'), dict(dll='wrong'), dict(roles=False), dict(configured=False)]:
                self.assertFalse(cases({**ctx, **delta})['QA-78']['available'])
            altered = json.loads(json.dumps(catalog))
            altered.pop('adminGroupRelationsAnnouncementBuilds')
            meta = json.loads(guide.render(altered, ctx).split('const guide=', 1)[1].split(';', 1)[0])['cases']
            self.assertFalse(meta['QA-78']['available'])
        def test_only_one_mapping_changed_and_notes_import_logic_is_original(self):
            old = (E / 'qa-guide/source-before/qa_guide.py').read_bytes()
            anchor = b"        'adminGroupRelationsGui': catalog.get('adminGroupRelationsBuilds', []),"
            newline = b'\r\n' if b'\r\n' in old else b'\n'
            added = newline + b"        'adminGroupRelationsAnnouncementGui': catalog.get('adminGroupRelationsAnnouncementBuilds', []),"
            self.assertEqual((ROOT / 'tools/windows/qa_guide.py').read_bytes(), old.replace(anchor, anchor + added))
            html = guide.render(catalog, guide.context(profile='rc9'))
            self.assertIn('records={...records,...accepted}', html)
            self.assertIn('conservar notas y volver a probar', html)
        def test_case_metadata_matches_the_authorized_append_and_single_case_change(self):
            self.assertEqual(matrix['unchangedCompleteCases'], 77)
            self.assertEqual(matrix['changedCases'], ['QA-78'])
            self.assertEqual(matrix['changedFields'], ['feature', 'steps[0]'])
            self.assertEqual(sum(x['available'] for x in cases(guide.context(profile='rc9')).values()), 78)
            self.assertEqual(sum(x['available'] for x in cases(guide.context(profile='manual')).values()), 8)
            self.assertTrue(all(guide.generate(check=True, profile=p) for p in ['manual', 'rc9']))
    for profile in ['manual', 'rc9']:
        assert guide.generate(profile=profile)
    suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(m) for m in [base, excel, status]])
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(Actual849))
    started = time.monotonic()
    with (E / 'QA-TESTS-01.log').open('x', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    record = dict(utc=datetime.now(timezone.utc).isoformat(), testsRun=result.testsRun,
                  successful=result.wasSuccessful(), failures=len(result.failures), errors=len(result.errors),
                  seconds=round(time.monotonic() - started, 3), caseCount=78,
                  availability=dict(manual=8, rc9=78), newCaseAvailable='QA-78',
                  actualQaApplicationOpened=False, screenReaderSpeechTested=False,
                  manualWascarResultsWritten=False,
                  scope='Metadata and guide behavior only; old848 source archived, planned expectations now closed849 pair. No manual voice or application execution.')
    (E / 'QA-TESTS-01.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(record))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
