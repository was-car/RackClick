"""Publish the single reviewed RecoveryAdministrator schema correction; reuse the GUI."""
import argparse,hashlib,json,shutil,subprocess,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-970-1029'

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--attempt',default='02');a=p.parse_args();assert a.attempt.isdecimal()
    record_path=E/('PUBLISH-FIX'+a.attempt+'.json');assert not record_path.exists()
    original=ROOT/'evidence/s1-20261018/sesenta-tandas-910-969/CANDIDATA969-01.json';old=json.loads(original.read_bytes())
    base=json.loads((original.parent/'SOURCE-FREEZE-01.json').read_bytes())['sources']
    changed=[p for p,h in base.items() if sha(ROOT/p)!=h]
    assert changed==['development/server/src/RackClick.Server/RecoveryAdministrator.cs'],changed
    rec=dict(reason='P1 Restore12 rejected by stale recovery schema11; align explicit reviewed version12. No frontend build or migration edit.',
        changedProductSources=changed,sourceHashes={p:sha(ROOT/p) for p in base},successful=False)
    target=ROOT/'.local/candidates'/('palette969-fix'+a.attempt+'-'+uuid.uuid4().hex);target.mkdir()
    rec['candidateDirectory']=target.relative_to(ROOT).as_posix()
    cmd=[str(ROOT/'.local/dotnet-10.0.401/dotnet.exe'),'publish','src/RackClick.Server/RackClick.Server.csproj','-c','Release','--no-restore','-o',str(target/'server'),'-p:UseAppHost=false']
    start=time.monotonic()
    try:
        with (E/('PUBLISH-FIX'+a.attempt+'.log')).open('xb') as log:r=subprocess.run(cmd,cwd=ROOT/'development/server',stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
        rec.update(command=cmd,exitCode=r.returncode,seconds=round(time.monotonic()-start,3));assert r.returncode==0
        shutil.copytree(ROOT/old['frontend'],target/'frontend')
        trees={part:{p.relative_to(target/part).as_posix():sha(p) for p in sorted((target/part).rglob('*')) if p.is_file()} for part in ['server','frontend']}
        assert trees['frontend']==old['distributions']['frontend']
        delta=[p for p,h in old['distributions']['server'].items() if trees['server'][p]!=h]
        assert set(delta)<={'RackClick.Server.dll','RackClick.Server.pdb'} and 'RackClick.Server.dll' in delta,delta
        m=dict(schema=12,candidateDirectory=target.relative_to(ROOT).as_posix(),serverDll=(target/'server/RackClick.Server.dll').relative_to(ROOT).as_posix(),
            frontend=(target/'frontend').relative_to(ROOT).as_posix(),distributions=trees,fileCount=sum(map(len,trees.values())),
            totalBytes=sum(p.stat().st_size for part in ['server','frontend'] for p in (target/part).rglob('*') if p.is_file()),
            sourceManifest=original.relative_to(ROOT).as_posix(),sourceManifestSha256=sha(original),reason=rec['reason'],selectedInRealQaAtFreeze=False)
        mp=E/('CANDIDATA969-FIX'+a.attempt+'.json')
        with mp.open('x',encoding='utf-8') as f:json.dump(m,f,indent=2);f.write('\n')
        rec.update(successful=True,manifest=mp.relative_to(ROOT).as_posix(),manifestSha256=sha(mp),serverChangedArtifacts=delta,frontendExact=True,sql001To012Exact=True,frontendBuilds=0,totalBytes=m['totalBytes'],fileCount=m['fileCount'])
    finally:
        with record_path.open('x',encoding='utf-8') as f:json.dump(rec,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in rec.items() if k not in ['sourceHashes','command']}))

if __name__=='__main__':main()
