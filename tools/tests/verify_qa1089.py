"""Run one relevant guide regression after appending only planned category cases."""
import importlib.util
import json
from pathlib import Path
import time
import unittest
ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'evidence/s1-20261018/sesenta-tandas-1030-1089'

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,ROOT/path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

def main():
 out=E/'QA-TESTS-01.json';assert not out.exists()
 base=load('guidebase1089','tools/tests/test_qa_guide.py')
 modules=[base,load('excel1089','tools/tests/test_rc9_excel_guide832.py'),load('status1089','tools/tests/test_qa_relations_status848.py'),
  load('ports1089','tools/tests/qa_port_colors969.py'),load('categories1089','tools/tests/qa_category_colors1089.py')]
 for profile in ['manual','rc9']:base.guide.generate(profile=profile)
 suite=unittest.TestSuite()
 for mod in modules:suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(mod))
 started=time.monotonic()
 with (E/'QA-TESTS-01.log').open('x',encoding='utf-8') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
 record=dict(successful=result.wasSuccessful(),testsRun=result.testsRun,failures=len(result.failures),errors=len(result.errors),seconds=round(time.monotonic()-started,3),
  caseCount=84,available=dict(manual=8,rc9=81),previous81Exact=True,newCasesPlanned=['QA-82','QA-83','QA-84'],manualWascarResultsWritten=False)
 out.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps(record));return 0 if result.wasSuccessful() else 1

if __name__=='__main__':raise SystemExit(main())
