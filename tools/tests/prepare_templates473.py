"""Record the new block's initial identity; never overwrite historical evidence."""
import hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-473-532'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    if (E/'INICIO.json').exists():raise SystemExit('Initial record already exists')
    E.mkdir(parents=True,exist_ok=True)
    old=json.loads((ROOT/'evidence/s1-20261018/cuarenta-y-cinco-tandas-428-472/INICIO.json').read_text());paths=set(old['guards'])
    paths.update(['evidence/s1-20261018/cuarenta-y-cinco-tandas-428-472/SHA256SUMS','evidence/s1-20261018/cuarenta-y-cinco-tandas-428-472/CANDIDATA472.json'])
    guards={p:sha(ROOT/p) for p in sorted(paths)}
    start={'utc':datetime.now(timezone.utc).isoformat(),'baseCommit':subprocess.check_output([str(ROOT/'.local/git-2.55.0.5/cmd/git.exe'),'rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'gitCleanAtFirstRead':True,'initialProgress':76,'scope':'Private configuration editor creates a new immutable template; latest candidate integration in Windows package and compatible QA. No schema or pinned dependency changes.','guards':guards,'authorizedMutableGuardPolicy':'Program/new route, catalog and generated guides may change; real restored-QA manual-qa.json may change only artifactDirectory/dllSha256/bundleSha256 after isolated tests and review. Pointer, database/cuentas/keys/results/old artifact bytes remain protected. No source DB application writes or manual QA accepted on user behalf.'}
    (E/'INICIO.json').write_text(json.dumps(start,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'guards':len(guards),'initialProgress':76,'baseCommit':start['baseCommit']}))
if __name__=='__main__':main()
