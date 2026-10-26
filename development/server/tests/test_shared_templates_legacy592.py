"""One existing private-instantiation regression on schema10 after common-helper extraction.

The historical test body is reused, not its logs or hardcoded schema9 report writer.
"""
import argparse,hashlib,json,platform,time,unittest
from datetime import datetime,timezone
from pathlib import Path
from pg_support import Lab
from test_private_device_templates import PrivateDeviceTemplatesPostgres,distribution
from test_postgres import EvidenceResult
ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class LegacyOnTen(PrivateDeviceTemplatesPostgres):
    def setUp(self):
        super().setUp()
        self.assertEqual(self.lab.sql(self.db,'SELECT max(version) FROM schema_migration'),'10')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    a.output.mkdir(parents=True,exist_ok=False);m=json.loads(a.manifest.read_bytes());assert m['schema']==10
    dll=ROOT/m['serverDll'];frontend=ROOT/m['frontend'];server_before=distribution(dll.parent);front_before=distribution(frontend)
    assert dict(server=server_before,frontend=front_before)==m['distributions']
    sources={p.relative_to(ROOT).as_posix():sha(p) for p in [Path(__file__),Path(__file__).with_name('test_private_device_templates.py'),Path(__file__).with_name('test_inventory_postgres.py'),Path(__file__).with_name('pg_support.py')]}
    lab=Lab('shared-legacy592');LegacyOnTen.lab=lab;LegacyOnTen.dll=dll;LegacyOnTen.frontend=frontend
    name='test_05_instantiate_three_kinds_new_ids_private_reset_and_change_feed';started=time.monotonic()
    with lab,(a.output/'tests.log').open('w',encoding='utf-8') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite([LegacyOnTen(name)]))
    report=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),schemaVersionObservedInSetUp=10,
        reusedTestBody=name,testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful(),seconds=round(time.monotonic()-started,3),
        sourceHashes=sources,sourcesUnchanged=all(sha(ROOT/p)==h for p,h in sources.items()),manifestSha256=sha(a.manifest),
        serverUnchanged=server_before==distribution(dll.parent),frontendUnchanged=front_before==distribution(frontend),
        labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers),
        actualQaOpened=False,historicalResultsReused=False)
    (a.output/'result.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    print(json.dumps({k:report[k] for k in ['testsRun','successful','seconds','labStopped','serversStopped']}))
    return 0 if all(report[k] for k in ['successful','sourcesUnchanged','serverUnchanged','frontendUnchanged','labStopped','serversStopped']) else 1
if __name__=='__main__':raise SystemExit(main())
