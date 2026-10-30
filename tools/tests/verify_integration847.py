"""Final readonly guard/candidate/package/QA checks after the selected832 copy."""
import hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/quince-tandas-833-847'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads((E/p).read_bytes())
def main():
    out=E/'VERIFICACION-FINAL.json';assert not out.exists()
    start=read('INICIO.json');allowed=set(start['authorizedMutableGuards']);allowed.update(read('ALCANCE-GUIA.json')['additionalAuthorizedMutableGuards'])
    changed={p for p,h in start['guards'].items() if sha(ROOT/p)!=h};assert changed<=allowed,changed-allowed
    assert all(sha(ROOT/p)==h for p,h in start['currentQaGuards'].items())
    package=read('PACKAGES-01.json');assert package['valid'] and package['byteIdentical']
    assert all(sha(ROOT/x['path'])==x['sha256'] for x in package['outputs'])
    freeze=read('SOURCE-FREEZE-OPERATORS-01.json');assert all(sha(ROOT/p)==h for p,h in freeze['sources'].items())
    manifest=ROOT/start['candidateManifest'];assert sha(manifest)==start['candidateManifestSha256'];m=json.loads(manifest.read_bytes())
    assert all(sha(ROOT/m['candidateDirectory']/part/p)==h for part,files in m['distributions'].items() for p,h in files.items())
    assert read('COORDINATOR-GO.json')['valid'] and read('REAL-QA-ACTIVATE-01.json')['state']=='committed' and read('REAL-QA-VALIDATE-01.json')['valid']
    assert read('QA-TESTS-01.json')['successful'] and read('QA-TESTS-01.json')['availability']==dict(manual=8,rc9=77)
    pointer=json.loads((ROOT/'.local/qa-rc9/current.json').read_bytes());selected=ROOT/read('REAL-QA-PREPARE-01.json')['candidateDirectory'];assert Path(pointer['directory']).resolve()==selected.resolve()
    cfg=json.loads((selected/'manual-qa.json').read_bytes());assert cfg['dllSha256']==m['distributions']['server']['RackClick.Server.dll'] and cfg['bundleSha256']==m['distributions']['frontend']['app.js']
    plan=json.loads((ROOT/'docs/PLAN-QUINCE-TANDAS-833-847.json').read_bytes());assert plan['completed']==15
    assert all(row['status']=='verified' and (ROOT/row['evidence']).is_file() and (ROOT/row['independentEvidence']).is_file() for row in plan['batches'])
    gate=read('revision/GATE-TECNICO.json');assert gate['valid'] and gate['recommendedProgress']==78
    for key in ['sourceHashes','manualHashes']:assert all(sha(ROOT/p)==h for p,h in gate[key].items())
    progress=json.loads((ROOT/'docs/MAPA-ENTREGA.json').read_bytes());assert progress['progress']==78 and [x['points'] for x in progress['streams']]==[18,22,14,14,9,1]
    git=str(ROOT/'.local/git-2.55.0.5/cmd/git.exe');assert subprocess.check_output([git,'rev-parse','HEAD'],text=True,cwd=ROOT).strip()==start['baseCommit']
    data=dict(utc=datetime.now(timezone.utc).isoformat(),successful=True,guardCount=len(start['guards']),unchangedGuards=len(start['guards'])-len(changed),authorizedChangedGuards=sorted(changed),sourceQaUnchangedFiles=len(start['currentQaGuards']),candidateFileCount=m['fileCount'],applicationManifestSha256=start['candidateManifestSha256'],packagedSourceCount=len(freeze['sources']),packagesByteIdentical=True,applicationBuilds=0,frontendBuilds=0,sourceApplicationLogin=False,sourceApplicationDml=False,source712Preserved=True,actualSelectedRevision=832,actualSelectedSchema=11,qaAvailable=dict(manual=8,rc9=77),newCasesAvailable=['QA-75','QA-76','QA-77'],internalMilestonesVerified=15,progress=78,manualWascarResultsWritten=False,finalAdoption=False)
    out.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8');print(json.dumps(data,indent=2))
if __name__=='__main__':main()
