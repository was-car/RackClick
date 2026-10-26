"""Freeze packaged inputs once and produce two identical schema13 onboarding internal ZIPs."""
import argparse,hashlib,importlib.util,json,sys,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-1210-1269'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--attempt',choices=['01','02','03'],default='01');args=parser.parse_args()
    result=E/f'PACKAGES-{args.attempt}.json';freeze=E/f'SOURCE-FREEZE-OPERATORS-{args.attempt}.json'
    if result.exists() or freeze.exists():raise SystemExit('Preserve package evidence; use a new named attempt if correction is necessary')
    spec=importlib.util.spec_from_file_location('package_offline_bundle1269',ROOT/'tools/package_offline_bundle.py');builder=importlib.util.module_from_spec(spec);sys.modules[spec.name]=builder;spec.loader.exec_module(builder)
    manifest=ROOT/'evidence/s1-20261018/sesenta-tandas-1150-1209/CANDIDATA1209-01.json';pin='dc79c53fe188187637972c2cad479edd1868d1942414c602de17bb4454bd153b';assert sha(manifest)==pin
    assert len(builder.OPERATORS)==25 and len(builder.MANUALS)==4
    files=[ROOT/'tools/windows'/n for n in builder.OPERATORS]+[ROOT/'docs'/n for n in builder.MANUALS]+[ROOT/p for p in ['tools/package_offline_bundle.py','development/toolchain.lock.json','development/offline-bundle.sources.json','tools/tests/build_offline1269.py']]
    frozen={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(files))}
    freeze.write_bytes((json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(),sources=frozen,scope='Packaged operators/manuals and producer inputs; unbundled QA/test sources separately sealed'),indent=2)+'\n').encode())
    (E/'packaging').mkdir(exist_ok=True);outputs=[];tag=uuid.uuid4().hex
    for suffix in ['a','b']:
        target=ROOT/'.local'/f'offline1269-{tag}-{suffix}.zip';evidence=E/'packaging'/(f'build{args.attempt}-'+suffix)
        report=builder.build(manifest,pin,ROOT/'.local/downloads/dotnet-sdk-10.0.401-win-x64.zip',ROOT/'.local/downloads/postgresql-17.11-4-windows-x64-binaries.zip',ROOT/'development/offline-bundle.sources.json',target,evidence)
        assert report['valid'];outputs.append(dict(path=target.relative_to(ROOT).as_posix(),bytes=target.stat().st_size,sha256=sha(target),report=evidence.relative_to(ROOT).as_posix()+'/REPORT.json'))
    unchanged=all(sha(ROOT/p)==h for p,h in frozen.items());same=outputs[0]['sha256']==outputs[1]['sha256'] and outputs[0]['bytes']==outputs[1]['bytes']
    data=dict(utc=datetime.now(timezone.utc).isoformat(),sourceManifestSha256=pin,sourceFreezeSha256=sha(freeze),sourceCount=len(frozen),sourcesUnchanged=unchanged,byteIdentical=same,outputs=outputs,newAppBuildsDuringPackaging=0,newFrontendBuildsDuringPackaging=0,qaSelectedAtPackaging=False,valid=unchanged and same)
    result.write_bytes((json.dumps(data,indent=2)+'\n').encode());print(json.dumps(data));return 0 if data['valid'] else 1
if __name__=='__main__':raise SystemExit(main())
