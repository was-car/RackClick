"""Assemble the local Windows11 delivery from pinned, reviewed inputs; never install."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'RackClick-Windows-Completo-11/'
WRAPPER_SHA = 'e0d065416716e3a6c9e38c9a2d3c64175d5f7c83f74843150d576851d95b1f1b'
BUNDLE_SHA = '19113a00d7245b8d29fe83c6ff88ff9de2466a000a9dc08a39d078f908883e84'
APP_SHA = 'd352c04381cd4f1954aa43735e540970b295f231106560c5c9880c7ee1dc78db'
IP_SHA = 'f30e5d1592d0cc26f879e8912c1b4e31e3ba1d8bfcf2ab7bd85723b6107976ed'
DEMO_SHA = 'f89d8c7a5d796133cfe6b13812b885a124ee5fd21431a3c5271fd1a23d8a3447'
REPLAY_SHA = 'a3b44a37d8ca81f2f13d515d26905a520af8f09ffb2cfe498f97d06367bf423a'
# Canonical list of the 138 final payload files, independently pinned outside
# ENTREGA.json. A coherent self-declared manifest never authorizes another tree.
CLOSED_TREE_SHA = 'bc4ae8d0d54f930b2bfb7bbfd905e526430d4b9e2ea2940a5a6b437ac8eda15c'
STAMP = (2026, 11, 2, 0, 0, 0)

def sha(data): return hashlib.sha256(data).hexdigest()

def assert_closed_tree(entries):
    rows = [{'path':k,'size':len(v),'sha256':sha(v)} for k,v in sorted(entries.items())
            if k not in {'ENTREGA.json','SHA256SUMS.txt'}]
    raw = json.dumps(rows,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')
    if len(rows) != 138 or sha(raw) != CLOSED_TREE_SHA:
        raise ValueError('delivery_tree_not_authorized')

def checked_file(path: Path) -> bytes:
    path = Path(os.path.abspath(path))
    for component in (*reversed(path.parents), path):
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('reparse_rejected')
    if not path.is_file(): raise ValueError('input_not_file')
    return path.read_bytes()

def members(data: bytes, prefix: str) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        result = {}; seen = set(); total = 0
        for item in z.infolist():
            name = item.orig_filename; rel = name.removeprefix(prefix)
            if (item.filename != name or not name.startswith(prefix) or name == prefix or chr(92) in rel or ':' in rel
                or rel.startswith('/') or '..' in PurePosixPath(rel).parts or '.' in rel.split('/')
                or any(not part or part.endswith(('.', ' ')) for part in rel.split('/'))
                or rel.casefold() in seen or item.file_size > 350 * 1024 * 1024
                or stat.S_IFMT(item.external_attr >> 16) not in (0, stat.S_IFREG)):
                raise ValueError('zip_layout_invalid')
            total += item.file_size
            if total > 600 * 1024 * 1024: raise ValueError('zip_size_invalid')
            seen.add(rel.casefold()); result[rel] = z.read(item)
        if not result or len(result) > 3000: raise ValueError('zip_count_invalid')
        return result

def records_match(entries, manifest, excluded):
    rows = manifest['files']; names = [row['path'] for row in rows]
    if len(set(names)) != len(names) or set(names) | {excluded} != set(entries):
        raise ValueError('inventory_mismatch')
    for row in rows:
        raw = entries[row['path']]
        if row['size'] != len(raw) or row['sha256'] != sha(raw): raise ValueError('content_mismatch')

def collect(wrapper: Path, network: Path, demo: Path, replay: Path) -> dict:
    raw = checked_file(wrapper)
    if sha(raw) != WRAPPER_SHA: raise ValueError('wrapper_pin_invalid')
    wrapped = members(raw, 'RackClick-Servidor-11/')
    if set(wrapped) != {'Servidor.zip','INICIAR.ps1','00-LEEME.html','00-LIMPIAR-Y-REINSTALAR.cmd','PAQUETE.json'}:
        raise ValueError('wrapper_inventory_invalid')
    records_match(wrapped, json.loads(wrapped['PAQUETE.json']), 'PAQUETE.json')
    payload = members(wrapped['Servidor.zip'], 'RackClick-Instalador/')
    manifest = json.loads(payload['payload.json']); records_match(payload, manifest, 'payload.json')
    if manifest['bundleArchiveSha256'] != BUNDLE_SHA or sha(payload['RackClick.zip']) != BUNDLE_SHA:
        raise ValueError('bundle_pin_invalid')
    with zipfile.ZipFile(io.BytesIO(payload['RackClick.zip'])) as bundle:
        doc = json.loads(bundle.read('bundle.json'))
        if doc['versions']['schema'] != 43 or doc['applicationManifestSha256'] != APP_SHA:
            raise ValueError('application_pin_invalid')
    net = checked_file(network); data = checked_file(demo); commands = checked_file(replay)
    if sha(net) != IP_SHA or sha(data) != DEMO_SHA or sha(commands) != REPLAY_SHA:
        raise ValueError('optional_input_pin_invalid')
    entries = dict(wrapped)
    entries.update({'MANUAL-INSTALACION.html':checked_file(ROOT/'docs/INSTALADOR11-WINDOWS43.html'),
                    'MANUAL-INSTALACION.md':checked_file(ROOT/'docs/INSTALADOR11-WINDOWS43.md')})
    # Expand only known immutable archives into memory; never extract to the build host.
    entries.update({'DATOS-DEMO50/'+name:value for name,value in members(data, '').items()})
    # The IP package has its own native prefix, pinned above.
    with zipfile.ZipFile(io.BytesIO(net)) as z: prefix = z.namelist()[0].split('/')[0]+'/'
    entries.update({'MANTENIMIENTO-IP/'+name:value for name,value in members(net,prefix).items()})
    for name in ('Import-RackClickDemo50.ps1','CARGAR-50-CLIENTES.cmd','LEEME-DEMO50.txt'):
        entries['CARGAR-DEMO50/'+name] = checked_file(ROOT/'tools/windows/demo50'/name)
    entries['CARGAR-DEMO50/demo50-replay.json'] = commands
    cmd = ('@echo off\r\nsetlocal\r\n"%SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" '
           '-NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0INICIAR.ps1"\r\n'
           'set "RC_EXIT=%ERRORLEVEL%"\r\nif not "%RC_EXIT%"=="0" if not "%RC_EXIT%"=="3" pause\r\nexit /b %RC_EXIT%\r\n')
    entries['01-INSTALAR.cmd'] = cmd.encode('ascii')
    entries['02-CARGAR-50-CLIENTES.cmd'] = b'@echo off\r\ncall "%~dp0CARGAR-DEMO50\\CARGAR-50-CLIENTES.cmd"\r\nexit /b %ERRORLEVEL%\r\n'
    entries['00-ESTADO.txt'] = ('CANDIDATA LOCAL WINDOWS43 - EDICION11\r\n'
        'Abrir MANUAL-INSTALACION.html antes de instalar en una VM nueva.\r\n'
        '01-INSTALAR.cmd abre el asistente; datos50 opcionales con02-CARGAR-50-CLIENTES.cmd.\r\n'
        'No es actualizacion automatica ni adopcion. Ensayo SCM/reinicio Windows pendiente.\r\n'
        'Restore con factores MFA requiere sobre externo y sigue bloqueado.\r\n'
        'Sin usuarios/contrasenas compartidas, dumps privados ni secretos de laboratorio.\r\n'
        'Redistribucion publica de binarios no autorizada; revision de derechos abierta.\r\n').encode('ascii')
    assert_closed_tree(entries)
    doc = {'schemaVersion':1,'kind':'RackClickCompleteWindowsCandidate','edition':'11','applicationSchema':43,
           'adopted':False,'vmTested':False,'redistributionReview':'open',
           'files':[{'path':name,'size':len(value),'sha256':sha(value)} for name,value in sorted(entries.items())]}
    entries['ENTREGA.json'] = (json.dumps(doc,sort_keys=True,ensure_ascii=True,indent=2)+'\n').encode('ascii')
    entries['SHA256SUMS.txt'] = ''.join(f'{sha(value)}  {name}\n' for name,value in sorted(entries.items())).encode('ascii')
    return entries

def build(wrapper,network,demo,replay,output):
    output = Path(output)
    if output.exists() or Path(str(output)+'.sha256').exists(): raise ValueError('output_exists')
    entries = collect(wrapper,network,demo,replay)
    with output.open('xb') as stream, zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,value in sorted(entries.items()):
            info=zipfile.ZipInfo(PREFIX+name,STAMP);info.create_system=0;info.external_attr=0x20
            z.writestr(info,value,compress_type=zipfile.ZIP_STORED if name=='Servidor.zip' else zipfile.ZIP_DEFLATED,compresslevel=6)
    digest=sha(output.read_bytes())
    Path(str(output)+'.sha256').write_text(digest+'  '+output.name+'\n',encoding='ascii')
    return {'valid':True,'code':'windows_candidate_packaged','sha256':digest,'bytes':output.stat().st_size,
            'files':len(entries),'schema':43,'edition':'11','vmTested':False,'adopted':False}

def verify(path,expected):
    data=checked_file(path)
    if sha(data)!=expected: raise ValueError('archive_pin_invalid')
    entries=members(data,PREFIX);doc=json.loads(entries['ENTREGA.json'])
    body={k:v for k,v in entries.items() if k!='SHA256SUMS.txt'};records_match(body,doc,'ENTREGA.json')
    sums=''.join(f'{sha(value)}  {name}\n' for name,value in sorted(body.items())).encode('ascii')
    if sums!=entries['SHA256SUMS.txt']:raise ValueError('sums_invalid')
    if doc['edition']!='11' or doc['applicationSchema']!=43 or doc['adopted'] or doc['vmTested']:
        raise ValueError('delivery_contract_invalid')
    assert_closed_tree(entries)
    return {'valid':True,'code':'windows_candidate_verified','files':len(entries),'schema':43,'edition':'11'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='mode',required=True)
    b=sub.add_parser('build')
    for name in ['wrapper','network','demo','replay','output']:b.add_argument('--'+name,type=Path,required=True)
    v=sub.add_parser('verify');v.add_argument('--archive',type=Path,required=True);v.add_argument('--sha256',required=True)
    a=p.parse_args()
    try:
        result=build(a.wrapper,a.network,a.demo,a.replay,a.output) if a.mode=='build' else verify(a.archive,a.sha256)
        print(json.dumps(result,sort_keys=True))
    except (ValueError,OSError,KeyError,zipfile.BadZipFile):
        print(json.dumps({'valid':False,'code':'windows_package_rejected'}));raise SystemExit(1)
