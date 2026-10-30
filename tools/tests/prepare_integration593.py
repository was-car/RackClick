"""Record this integration block before product/operator edits; retain all prior evidence."""
import hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-593-652'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    if (E/'INICIO.json').exists():raise SystemExit('Preserve existing initial record')
    previous=ROOT/'evidence/s1-20261018/sesenta-tandas-533-592';d=json.loads((previous/'INICIO.json').read_bytes());paths=set(d['guards'])
    paths.update(['evidence/s1-20261018/sesenta-tandas-533-592/SHA256SUMS','evidence/s1-20261018/sesenta-tandas-533-592/CANDIDATA592-FINAL02.json'])
    candidate=json.loads((previous/'CANDIDATA592-FINAL02.json').read_bytes())
    for part,files in candidate['distributions'].items():paths.update(candidate['candidateDirectory']+'/'+part+'/'+p for p in files)
    pointer=ROOT/'.local/qa-rc9/current.json';profile=Path(json.loads(pointer.read_bytes())['directory'])
    config=profile/'manual-qa.json';cfg=json.loads(config.read_bytes())
    E.mkdir(parents=True,exist_ok=True)
    row=dict(utc=datetime.now(timezone.utc).isoformat(),baseCommit=subprocess.check_output([str(ROOT/'.local/git-2.55.0.5/cmd/git.exe'),'rev-parse','HEAD'],cwd=ROOT,text=True).strip(),gitCleanAtFirstRead=True,
        initialProgress=78,scope='Schema10 native Windows packaging and recovery, plus stopped source532/schema9 to new QA10 copy/migration/guarded selection. Existing data source retained.',
        guards={p:sha(ROOT/p) for p in sorted(paths)},sourceQaConfigSha256=sha(config),sourceQaPointerSha256=sha(pointer),sourceQaFrontendSha256=cfg['bundleSha256'],sourceQaDllSha256=cfg['dllSha256'],
        sourceDatabaseApplicationDmlPlanned=False,sourceApplicationLoginPlanned=False,wascarResultsWritten=False,
        authorizedChanges='New schema10 operator/package closed profile, new schema9-to10 QA copy/selection modules and tests. QA pointer may select a NEW verified candidate only after isolated native tests, independent review and coordinator GO; source config/secrets/rows/artifacts unchanged. Catalog/guides and continuity may change; no app/GUI rebuild planned.')
    (E/'INICIO.json').write_bytes((json.dumps(row,indent=2)+'\n').encode());print(json.dumps(dict(baseCommit=row['baseCommit'],guards=len(paths),initialProgress=78,sourceDmlPlanned=False)))
if __name__=='__main__':main()
