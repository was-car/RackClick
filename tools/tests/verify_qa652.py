"""Regenerate both real-context guides and run existing guide-only tests once."""
import importlib.util,json,sys,time,unittest
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-593-652'
def main():
    receipt=E/'QA-TESTS-01.json';log=E/'QA-TESTS-01.log'
    if receipt.exists() or log.exists():raise SystemExit('Preserve existing guide evidence')
    assert json.loads((E/'QA-MATRIX-652.json').read_bytes())['availabilityRequiresSelectedSnapshot']
    spec=importlib.util.spec_from_file_location('qa652test',ROOT/'tools/tests/test_qa_guide.py');module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    guide=module.guide
    for profile in ['manual','rc9']:assert guide.generate(profile=profile)
    start=time.monotonic()
    with log.open('x',encoding='utf-8') as f:result=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
    catalog=json.loads(guide.CATALOG.read_bytes());available={}
    for profile in ['manual','rc9']:
        assert guide.generate(check=True,profile=profile)
        data=json.loads(guide.render(catalog,guide.context(profile=profile)).split('const guide=',1)[1].split(';',1)[0])['cases']
        available[profile]=sum(x['available'] for x in data.values())
    record={'utc':datetime.now(timezone.utc).isoformat(),'testsRun':result.testsRun,'successful':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors),'seconds':round(time.monotonic()-start,3),'availability':available,'guidesRegeneratedAndExact':True,'actualQaApplicationOpened':False,'manualWascarResultsWritten':False,'scope':'Existing guide tests and real selected snapshot metadata only; no app/PG/Edge/manual QA run.'}
    receipt.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps(record));return 0 if result.wasSuccessful() and available=={'manual':8,'rc9':71} else 1
if __name__=='__main__':raise SystemExit(main())
