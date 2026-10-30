"""Archive the tested FINAL02 profiles, then accept only the legible FINAL03 GUI."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-473-532'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    old=E/'CANDIDATA532-FINAL02.json';new=E/'CANDIDATA532-FINAL03.json';before=json.loads(old.read_text());after=json.loads(new.read_text());a,b=sha(old),sha(new)
    assert before['distributions']['server']==after['distributions']['server'],'No backend rebuild allowed for this layout fix'
    record={'oldManifest':old.name,'oldSha256':a,'newManifest':new.name,'newSha256':b,'cause':'Preview table minWidth620 inside existing horizontal scroll, for legible390px labels. No CSS/global RC9/logic/backend change. FINAL02 native/API/GUI results remain attributed to their exact artifacts.','archivedSources':{}}
    for i,relative in enumerate(['tools/windows/qa_artifact9_source532.py','tools/package_offline_bundle.py','tools/windows/RackClick.OfflineBundle.ps1','tools/tests/test_offline_bundle_builder.py']):
        path=ROOT/relative;s=path.read_text(encoding='utf-8');target=E/'integration'/('SOURCE-FINAL02-'+path.name)
        if target.exists():raise SystemExit('Archive already exists')
        target.write_bytes(path.read_bytes());record['archivedSources'][relative]={'archive':target.relative_to(E).as_posix(),'sha256':sha(target)}
        if relative.endswith('test_offline_bundle_builder.py'):assert '/CANDIDATA532-FINAL02.json' in s
        else:assert a in s;s=s.replace(a,b).replace(str(before['totalBytes']),str(after['totalBytes']))
        s=s.replace('/CANDIDATA532-FINAL02.json','/CANDIDATA532-FINAL03.json');path.write_bytes(s.replace('\n','\r\n').encode('utf-8'))
    (E/'PIN-LAYOUT-03.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps({'manifestSha256':b,'bytes':after['totalBytes'],'candidateDirectory':after['candidateDirectory'],'gui':after['distributions']['frontend']['app.js'],'dll':after['distributions']['server']['RackClick.Server.dll']}))
if __name__=='__main__':main()
