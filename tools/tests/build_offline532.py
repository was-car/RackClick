"""Freeze package sources and build two byte-identical internal Windows ZIPs."""
import hashlib,importlib.util,json,sys,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-473-532'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    spec=importlib.util.spec_from_file_location('package_offline_bundle',ROOT/'tools/package_offline_bundle.py');builder=importlib.util.module_from_spec(spec);sys.modules[spec.name]=builder;spec.loader.exec_module(builder)
    result=E/'PACKAGES-03.json'
    if result.exists():raise SystemExit('Package result already exists; preserve it')
    manifest=E/'CANDIDATA532-FINAL03.json';assert sha(manifest)==builder.APPLICATION_CONFIG_SHA256
    files=[ROOT/'tools/windows'/n for n in builder.OPERATORS]+[ROOT/'docs'/n for n in builder.MANUALS]
    files += [ROOT/p for p in ['tools/package_offline_bundle.py','development/toolchain.lock.json','development/offline-bundle.sources.json','tools/windows/qa_artifact9_source532.py','tools/windows/qa_artifact9_update532.py','development/server/tests/test_qa_artifact9_update532.py','development/server/tests/test_offline_configuration532.py','development/server/tests/test_offline_installation.py','tools/tests/build_offline532.py']]
    frozen={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(files))};(E/'SOURCE-FREEZE-OPERATORS-03.json').write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'sources':frozen},indent=2)+'\n',encoding='utf-8')
    tag=uuid.uuid4().hex;outputs=[]
    for suffix in ['a','b']:
        target=ROOT/'.local'/f'offline532-{tag}-{suffix}.zip';evidence=E/'packaging'/f'build03-{suffix}'
        report=builder.build(manifest,sha(manifest),ROOT/'.local/downloads/dotnet-sdk-10.0.401-win-x64.zip',ROOT/'.local/downloads/postgresql-17.11-4-windows-x64-binaries.zip',ROOT/'development/offline-bundle.sources.json',target,evidence)
        assert report['valid'];outputs.append({'path':target.relative_to(ROOT).as_posix(),'bytes':target.stat().st_size,'sha256':sha(target),'report':evidence.relative_to(ROOT).as_posix()+'/REPORT.json'})
    unchanged=all(sha(ROOT/p)==h for p,h in frozen.items());same=outputs[0]['sha256']==outputs[1]['sha256'] and outputs[0]['bytes']==outputs[1]['bytes']
    record={'utc':datetime.now(timezone.utc).isoformat(),'sourceManifestSha256':sha(manifest),'sourceFreezeSha256':sha(E/'SOURCE-FREEZE-OPERATORS-03.json'),'sourceCount':len(frozen),'sourcesUnchanged':unchanged,'byteIdentical':same,'outputs':outputs,'newAppBuildsDuringPackaging':0,'newFrontendBuildsDuringPackaging':0,'qaSelectedAtPackaging':False,'valid':unchanged and same}
    result.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps(record,indent=2));return 0 if record['valid'] else 1
if __name__=='__main__':raise SystemExit(main())
