"""Create a portable inventory-only kit; never installs or alters host settings."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TEMPLATES=ROOT/'tools/windows/two-host-preparation'
NAMES=('01-DATOS-SERVIDOR.cmd','02-DATOS-WINDOWS11-SERVIDOR.cmd','Get-RackClickHostReadiness.ps1','Invoke-RackClickHostPreparation.ps1','LEEME-PRIMERO.html','PLAN-PENDIENTE.json')

def digest(data):return hashlib.sha256(data).hexdigest()

def inputs():
    result={name:(ROOT/'tools/windows/Get-RackClickHostReadiness.ps1' if name=='Get-RackClickHostReadiness.ps1' else TEMPLATES/name).read_bytes() for name in NAMES}
    for name,data in result.items():
        if name.endswith('.cmd'):
            result[name]=data.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
    return result

def build(output):
    output=Path(output).resolve()
    if not output.parent.is_dir() or output.exists():raise ValueError('Output must be new, with an existing parent; nothing is overwritten.')
    files=inputs()
    manifest=dict(schemaVersion=1,kind='RackClickHostPreparation',readiness='inventory_only',files={name:digest(data) for name,data in files.items()})
    files['MANIFIESTO.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    output.mkdir(exist_ok=False)
    folder=output/'Preparar-Cliente3-Servidor';folder.mkdir()
    for name,data in files.items():
        with (folder/name).open('xb') as f:f.write(data)
    archive=output/'RackClick-Preparacion-Cliente3-Servidor.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo('Preparar-Cliente3-Servidor/'+name,date_time=(2026,10,18,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
            z.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    sha=digest(archive.read_bytes());(output/'SHA256SUMS.txt').write_text(sha+'  '+archive.name+'\n',encoding='ascii')
    return dict(archive=str(archive),sha256=sha,bytes=archive.stat().st_size,files=len(files),inventoryOnly=True,productBuilds=0,installationPerformed=False)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output-directory',type=Path,required=True)
    print(json.dumps(build(parser.parse_args().output_directory),ensure_ascii=False))

if __name__=='__main__':main()
