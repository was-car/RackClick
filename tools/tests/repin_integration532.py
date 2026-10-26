"""Replace the provisional532 pin with reviewed-source FINAL02; keep old evidence."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-473-532'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    old=E/'CANDIDATA532.json';new=E/'CANDIDATA532-FINAL02.json';before=json.loads(old.read_text());after=json.loads(new.read_text())
    old_hash,new_hash=sha(old),sha(new);record={'previousManifest':old.name,'previousSha256':old_hash,'finalManifest':new.name,'finalSha256':new_hash,'cause':'Frontend security cleanup edited five seconds after initial build despite prior stable handshake. No PG, browser or QA selection used initial candidate. Backend bytes identical; frontend build02 coordinated with source hashes. Original manifests/candidates/freezes retained.','changedSources':[],'backendRecompiled':False}
    assert before['distributions']['server']==after['distributions']['server']
    x=json.loads((E/'SOURCE-FREEZE-APP-01.json').read_text())['sources'];y=json.loads((E/'SOURCE-FREEZE-APP-02.json').read_text())['sources'];record['changedSources']=[p for p in sorted(set(x)|set(y)) if x.get(p)!=y.get(p)]
    for relative in ['tools/windows/qa_artifact9_source532.py','tools/package_offline_bundle.py','tools/windows/RackClick.OfflineBundle.ps1']:
        path=ROOT/relative;s=path.read_text(encoding='utf-8');assert old_hash in s;s=s.replace(old_hash,new_hash)
        if relative.endswith('source532.py'):s=s.replace('/CANDIDATA532.json','/CANDIDATA532-FINAL02.json')
        else:s=s.replace(str(before['totalBytes']),str(after['totalBytes']))
        path.write_bytes(s.replace('\n','\r\n').encode('utf-8'))
    test=ROOT/'tools/tests/test_offline_bundle_builder.py';s=test.read_text(encoding='utf-8').replace('/CANDIDATA532.json','/CANDIDATA532-FINAL02.json');test.write_bytes(s.replace('\n','\r\n').encode('utf-8'))
    (E/'PIN-UPDATE-02.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps(record,indent=2))
if __name__=='__main__':main()
