"""One final relevant Node regression on the frozen source, not historical reruns."""
import json
import argparse
from pathlib import Path
import subprocess
import time
from init_onboarding1209 import ROOT,E,sha

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--attempt',choices=['01','02'],default='01');args=parser.parse_args()
    suffix='' if args.attempt=='01' else '-'+args.attempt
    output=E/('NODE-FINAL'+suffix+'.json');log_path=E/('NODE-FINAL'+suffix+'.log');assert not output.exists() and not log_path.exists()
    freeze=json.loads((E/'frontend/FUENTES-02.json').read_bytes())['files'];assert all(sha(ROOT/p)==h for p,h in freeze.items())
    started=time.monotonic()
    with log_path.open('xb') as stream:
        result=subprocess.run([str(ROOT/'.local/node-v24.21.0-win-x64/node.exe'),'--test','--test-reporter=tap','tests/test_admin_user_onboarding.mjs'],cwd=ROOT/'development/frontend',stdout=stream,stderr=subprocess.STDOUT,timeout=60)
    log=log_path.read_text(encoding='utf-8')
    assert '# tests 15' in log and '# fail 0' in log and '# pass 15' in log
    exact=all(sha(ROOT/p)==h for p,h in freeze.items())
    record=dict(successful=result.returncode==0 and exact,exitCode=result.returncode,testsRun=15,seconds=round(time.monotonic()-started,3),sourcesUnchanged=exact,sourceHashes=freeze)
    output.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in record.items() if k!='sourceHashes'}));return result.returncode
if __name__=='__main__':raise SystemExit(main())
