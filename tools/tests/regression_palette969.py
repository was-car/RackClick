"""One relevant regression: existing preference protocol, domain and Node adapter."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / 'evidence/s1-20261018/sesenta-tandas-910-969'
sys.path.insert(0,str(ROOT/'development/server/tests'))
from pg_support import Lab, toolchain
from test_user_preferences import UserPreferencesPostgres
from test_inventory_movement_gui import tree


def main():
    output=E/'regression01'
    output.mkdir(exist_ok=False)
    manifest=json.loads((E/'CANDIDATA969-01.json').read_bytes())
    dll,frontend=ROOT/manifest['serverDll'],ROOT/manifest['frontend']
    before=dict(server=tree(dll.parent),frontend=tree(frontend))
    tools=toolchain()
    commands=[([str(tools['node']),'--test','tests/user-preferences.test.mjs'],ROOT/'development/frontend','node-preferences'),
              ([str(tools['dotnet']),'run','--project','tests/RackClick.Domain.Tests/RackClick.Domain.Tests.csproj','--no-restore','-c','Release'],ROOT/'development/server','domain')]
    jobs=[]
    for command,cwd,name in commands:
        started=time.monotonic()
        with (output/(name+'.log')).open('xb') as log:
            result=subprocess.run(command,cwd=cwd,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
        jobs.append(dict(command=command,exitCode=result.returncode,seconds=round(time.monotonic()-started,3)))
    c=UserPreferencesPostgres
    c.dll,c.frontend=dll,frontend
    c.lab=Lab('palette969-regression')
    names=['test_02_readonly_get_reader_no_customer_grants_and_owner_isolation','test_04_noops_replay_historical_receipt_and_durable_fences']
    started=time.monotonic()
    with c.lab,(output/'postgres-preferences.log').open('x',encoding='utf-8') as log:
        tests=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.TestSuite(c(name) for name in names))
    record=dict(successful=all(r['exitCode']==0 for r in jobs) and tests.wasSuccessful(),commands=jobs,
                existingPreferenceCases=names,postgresTestsRun=tests.testsRun,postgresSeconds=round(time.monotonic()-started,3),
                actualSchema=12,applicationBuilds=0,frontendBuilds=0,domainTestHarnessBuildOnly=True,
                artifactsUnchanged=before==dict(server=tree(dll.parent),frontend=tree(frontend)),
                labStopped=not c.lab.running,serversStopped=all(s.process.poll() is not None for s in c.lab.servers),actualQaAccessed=False)
    (output/'result.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(record))
    return 0 if record['successful'] and record['artifactsUnchanged'] and record['labStopped'] and record['serversStopped'] else 1


if __name__=='__main__':
    raise SystemExit(main())
