"""Coordinator evidence sealing only; no product, database or QA mutation."""
import hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/cuarenta-y-cinco-tandas-428-472'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    if (E/'SHA256SUMS').exists() or (E/'CAMBIOS.patch').exists():raise SystemExit('Existing seal/diff: preserve history; use a new revision output explicitly.')
    # The index is prepared by the coordinator. Keep historical evidence out of the source diff.
    patch=subprocess.check_output([str(ROOT/'.local/git-2.55.0.5/cmd/git.exe'),'diff','--cached','--binary','--','.',':(exclude)evidence/**'],cwd=ROOT)
    (E/'CAMBIOS.patch').write_bytes(patch)
    record={'utc':datetime.now(timezone.utc).isoformat(),'author':'coordinator','scope':'Closure and source diff; no new native test run.','progressApproximate':76,'milestonesClosed':45,'candidateSha256':digest(E/'CANDIDATA472.json'),'sourceFreezeSha256':digest(E/'SOURCE-FREEZE-01.json'),'sourceDiffSha256':digest(E/'CAMBIOS.patch'),'backendSealSha256':digest(E/'backend/SHA256SUMS'),'independentSealSha256':digest(E/'revision/SHA256SUMS'),'finalMetadata':'VERIFICACION-02.json','immutableGuards':163,'explicitMutableGuards':['development/server/src/RackClick.Server/Program.cs','docs/QA-CASOS-WASCAR.json','GUIA-QA-WASCAR.html','GUIA-QA-RESTAURADO.html'],'actualQaUpdated':False,'offline427Updated':False,'allNativeFixtureReportsStopped':True}
    (E/'CIERRE-REGISTRO.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    files=[p for p in sorted(E.rglob('*')) if p.is_file() and p!=E/'SHA256SUMS']
    (E/'SHA256SUMS').write_text(''.join(digest(p)+'  '+p.relative_to(E).as_posix()+'\n' for p in files),encoding='utf-8')
    for p in [E/'SHA256SUMS',E/'backend/SHA256SUMS',E/'revision/SHA256SUMS']:
        for line in p.read_text().splitlines():
            h,name=line.split('  ',1);assert digest(p.parent/name)==h,(p,name)
    print(json.dumps({'files':len(files),'sha256':digest(E/'SHA256SUMS'),'allThreeSealsVerified':True,'diffBytes':len(patch)}))
if __name__=='__main__':main()
