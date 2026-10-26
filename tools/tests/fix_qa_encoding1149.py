"""Restore UTF-8 outside the authorized guide-test class; preserve failed evidence."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import time
import unittest

ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-1090-1149'
CLASS=b'class CategoryGuide1089(unittest.TestCase):'
MAIN=b"if __name__=='__main__':"

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def outside_class(data):
    tree=ast.parse(data)
    tree.body=[n for n in tree.body if not isinstance(n,ast.ClassDef) or n.name!='CategoryGuide1089']
    return ast.dump(tree,include_attributes=False)

def main():
    out=E/'QA-FOCO-02.json';assert not out.exists()
    saved=E/'qa-guide/encoding01';saved.mkdir(exist_ok=False)
    target=ROOT/'tools/tests/qa_category_colors1089.py';helper=ROOT/'tools/tests/verify_qa1149.py'
    original=(E/'qa-guide/source-before/qa_category_colors1089.py').read_bytes()
    damaged=target.read_bytes();helper_before=helper.read_bytes()
    assert outside_class(damaged)!=outside_class(original)
    (saved/target.name).write_bytes(damaged);(saved/helper.name).write_bytes(helper_before)
    prefix=original.split(CLASS,1)[0];suffix=MAIN+original.split(MAIN,1)[1]
    authorized_class=CLASS+damaged.split(CLASS,1)[1].split(MAIN,1)[0]
    corrected=prefix+authorized_class+suffix
    assert outside_class(corrected)==outside_class(original)
    ast.parse(corrected)
    needle=b'text=p.read_text();before,rest';replacement=b"text=p.read_text(encoding='utf-8');before,rest"
    assert helper_before.count(needle)==1
    helper_after=helper_before.replace(needle,replacement);ast.parse(helper_after)
    target.write_bytes(corrected);helper.write_bytes(helper_after)
    spec=importlib.util.spec_from_file_location('category1149utf8',target);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    class Encoding1149(unittest.TestCase):
        def test_all_unauthorized_source_bytes_and_unicode_constants_are_exact(self):
            current=target.read_bytes()
            self.assertEqual(current.split(CLASS,1)[0],prefix)
            self.assertEqual(MAIN+current.split(MAIN,1)[1],suffix)
            self.assertEqual(outside_class(current),outside_class(original))
            for node in ast.walk(ast.parse(helper.read_bytes())):
                if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='read_text':
                    self.assertTrue(any(k.arg=='encoding' and isinstance(k.value,ast.Constant) and k.value.value=='utf-8' for k in node.keywords))
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(module.CategoryGuide1089),
                            unittest.defaultTestLoader.loadTestsFromTestCase(Encoding1149)])
    started=time.monotonic()
    with (E/'QA-FOCO-02.log').open('x',encoding='utf-8') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    record=dict(successful=result.wasSuccessful(),testsRun=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        seconds=round(time.monotonic()-started,3),finding='P2-UTF8-GUIA',cause='read_text without encoding used Windows cp1252, then write_text UTF-8',
        original47TestRecordSha256=sha(E/'QA-TESTS-01.json'),original47RecordRetained=True,
        damagedSourceSha256=hashlib.sha256(damaged).hexdigest(),damagedSourceArchive=(saved/target.name).relative_to(ROOT).as_posix(),
        oldHelperSha256=hashlib.sha256(helper_before).hexdigest(),oldHelperArchive=(saved/helper.name).relative_to(ROOT).as_posix(),
        correctedSourceSha256=sha(target),correctedHelperSha256=sha(helper),
        outsideAuthorizedClassAstExact=True,prefixAndSuffixByteExact=True,catalogAndGuidesNotWritten=True,
        currentSourceHashes={p.relative_to(ROOT).as_posix():sha(p) for p in [target,helper]},
        postgresTestsRepeated=0,applicationBuilds=0,frontendBuilds=0,manualWascarResultsWritten=False)
    with out.open('x',encoding='utf-8') as stream:stream.write(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record));return 0 if result.wasSuccessful() else 1

if __name__=='__main__':raise SystemExit(main())
