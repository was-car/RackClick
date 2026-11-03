"""Freeze packaged sources only; build two identical schema10 Windows ZIPs."""
import argparse,hashlib,importlib.util,json,sys,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-593-652'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--attempt',choices=['02','03'],default='02');args=ap.parse_args()
    spec=importlib.util.spec_from_file_location('package_offline_bundle',ROOT/'tools/package_offline_bundle.py');builder=importlib.util.module_from_spec(spec);sys.modules[spec.name]=builder;spec.loader.exec_module(builder)
    result=E/f'PACKAGES-{args.attempt}.json';freeze=E/f'SOURCE-FREEZE-OPERATORS-{args.attempt}.json'
    if result.exists() or freeze.exists():raise SystemExit('Preserve existing package evidence')
    manifest=ROOT/'evidence/s1-20261018/sesenta-tandas-533-592/CANDIDATA592-FINAL02.json'
    pin='66426b3c4fdf8c75b8c1faae4572066754934000eb2567881d93407f4ae5e9f9';assert sha(manifest)==pin
    files=[ROOT/'tools/windows'/n for n in builder.OPERATORS]+[ROOT/'docs'/n for n in builder.MANUALS]
    files += [ROOT/p for p in ['tools/package_offline_bundle.py','development/toolchain.lock.json','development/offline-bundle.sources.json','tools/tests/build_offline652.py']]
    frozen={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(files))}
    freeze.write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'sources':frozen,'scope':'Packaged operators/manuals and producer inputs; unbundled QA/test sources are sealed separately'},indent=2)+'\n',encoding='utf-8')
    (E/'packaging').mkdir(exist_ok=True)
    tag=uuid.uuid4().hex;outputs=[]
    for suffix in ['a','b']:
        target=ROOT/'.local'/f'offline652-{tag}-{suffix}.zip';evidence=E/'packaging'/f'build{args.attempt}-{suffix}'
        report=builder.build(manifest,pin,ROOT/'.local/downloads/dotnet-sdk-10.0.401-win-x64.zip',ROOT/'.local/downloads/postgresql-17.11-4-windows-x64-binaries.zip',ROOT/'development/offline-bundle.sources.json',target,evidence)
        assert report['valid'];outputs.append({'path':target.relative_to(ROOT).as_posix(),'bytes':target.stat().st_size,'sha256':sha(target),'report':evidence.relative_to(ROOT).as_posix()+'/REPORT.json'})
    unchanged=all(sha(ROOT/p)==h for p,h in frozen.items());same=outputs[0]['sha256']==outputs[1]['sha256'] and outputs[0]['bytes']==outputs[1]['bytes']
    record={'utc':datetime.now(timezone.utc).isoformat(),'sourceManifestSha256':pin,'sourceFreezeSha256':sha(freeze),'sourceCount':len(frozen),'sourcesUnchanged':unchanged,'byteIdentical':same,'outputs':outputs,'newAppBuildsDuringPackaging':0,'newFrontendBuildsDuringPackaging':0,'qaSelectedAtPackaging':False,'valid':unchanged and same}
    result.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps(record,indent=2));return 0 if record['valid'] else 1
if __name__=='__main__':raise SystemExit(main())
