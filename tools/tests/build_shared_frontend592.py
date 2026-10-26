"""Coordinated frontend build after STABLE; source identities before/after, exclusive log."""
import argparse,hashlib,json,subprocess,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-533-592'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--revision',type=int,choices=(1,2),default=1);args=parser.parse_args()
    rev=f'{args.revision:02d}';output=E/f'FRONTEND-BUILD-SOURCE-{rev}.json';log=E/f'frontend-build-{rev}.log'
    if output.exists() or log.exists():raise SystemExit('Preserve prior build evidence')
    files=[p for p in (ROOT/'development/frontend/src').rglob('*') if p.is_file()]
    files+=[ROOT/'development/frontend/build.mjs',ROOT/'development/frontend/package.json',ROOT/'development/frontend/package-lock.json']
    sources={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(files)}
    output.write_bytes((json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(),sources=sources),indent=2)+'\n').encode())
    started=time.monotonic()
    with log.open('wb') as stream:
        result=subprocess.run([str(ROOT/'.local/node-v24.21.0-win-x64/node.exe'),'build.mjs'],cwd=ROOT/'development/frontend',stdout=stream,stderr=subprocess.STDOUT,timeout=120)
    unchanged=all(sha(ROOT/p)==h for p,h in sources.items())
    print(json.dumps(dict(exitCode=result.returncode,sourcesUnchanged=unchanged,sourceCount=len(sources),seconds=round(time.monotonic()-started,3))))
    return 0 if result.returncode==0 and unchanged else 1
if __name__=='__main__':raise SystemExit(main())
