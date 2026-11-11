"""Collect the fixed NEW18 wrapper and Demo50-03, never installs or reads secrets."""
import argparse,hashlib,io,json,zipfile
from pathlib import Path
from package_server_installer import checked_path,LOCAL,ROOT,STAMP

WRAPPER_SHA='79ad195d1307c7da4a79e5dede38ab4fae4fd34a454d5e10ad3bf7890cd27c31'
DEMO_SHA='d7ab9469d4929af703285b0cc7eddcf13e9f245f43828cfcaee95c0e2d2e9215'
PAYLOAD_SHA='9ce1f7258affda57065ab14bd3a3c2a45aea8e30e44d88bf94cddb42d60ac613'
BUNDLE_SHA='098392ebfc62f2fe5ec9f79909ea3bdbecbf3c565286747a5a9d9507fccd8d40'
APP_SHA='a7b622f917404bbe3ea2560e1fcc2dad008910395c6ab5fa8bc6875be2c88112'
PREFIX='RackClick-Windows-Completo-18/'
sha=lambda data:hashlib.sha256(data).hexdigest()
def require(ok,code):
    if not ok:raise ValueError(code)
def members(data,prefix):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names=z.namelist();require(len(set(names))==len(names),'duplicate_member')
        require(all(n.startswith(prefix) and '..' not in n.split('/') and '\\' not in n and not n.endswith('/') for n in names),'member_invalid')
        return {n[len(prefix):]:z.read(n) for n in names}
def manifest(entries,name):
    value=json.loads(entries[name]);records=value['files']
    require(len(records)==len(entries)-1,'manifest_count_invalid')
    require({v['path'] for v in records}==set(entries)-{name},'manifest_inventory_invalid')
    for item in records:
        data=entries[item['path']];require(len(data)==item['size'] and sha(data)==item['sha256'],'member_hash_invalid')
    return value
def collect(wrapper,demo):
    w=checked_path(wrapper,LOCAL).read_bytes();d=checked_path(demo,LOCAL).read_bytes()
    require(sha(w)==WRAPPER_SHA,'wrapper_pin_mismatch');require(sha(d)==DEMO_SHA,'demo_pin_mismatch')
    server=members(w,'RackClick-Servidor-18/');wm=manifest(server,'PAQUETE.json')
    require(wm['edition']=='18' and wm['payloadSha256']==PAYLOAD_SHA,'wrapper_contract_invalid')
    require(sha(server['Servidor.zip'])==PAYLOAD_SHA,'payload_pin_mismatch')
    payload=members(server['Servidor.zip'],'RackClick-Instalador/');pm=manifest(payload,'payload.json')
    require(pm['bundleArchiveSha256']==BUNDLE_SHA and len(payload)==117,'payload_contract_invalid')
    require(sha(payload['RackClick.zip'])==BUNDLE_SHA,'bundle_pin_mismatch')
    data=members(d,'RackClick-Demo50-Trilingual-03/')
    require(len(data)==64,'demo_inventory_invalid')
    entries={'Servidor/'+n:v for n,v in server.items()}
    for n,v in data.items():
        if n.startswith(('DATOS-DEMO50/','CARGAR-50-CLIENTES/')):entries[n]=v
    entries['00-LEEME.html']=(ROOT/'docs/INSTALACION18-COMPLETA.html').read_bytes()
    entries['01-INSTALAR-NUEVO.ps1']=b'''#requires -Version 5.1\r\n$ErrorActionPreference='Stop'\r\n$found=@(Get-Service -Name 'RackClick*' -ErrorAction SilentlyContinue)\r\nif($found.Count-ne0){throw 'new_server_required_existing_rackclick_preserved'}\r\n$ps=Join-Path $env:SystemRoot 'System32\\WindowsPowerShell\\v1.0\\powershell.exe'\r\n& $ps -NoProfile -STA -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'Servidor\\INICIAR.ps1')\r\nexit $LASTEXITCODE\r\n'''
    entries['01-INSTALAR.cmd']=b'''@echo off\r\nsetlocal\r\n"%SystemRoot%\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp001-INSTALAR-NUEVO.ps1"\r\nset "RC_EXIT=%ERRORLEVEL%"\r\nif not "%RC_EXIT%"=="0" pause\r\nexit /b %RC_EXIT%\r\n'''
    entries['LEEME.txt']=('RackClick Windows Completo18 / NEW48 / Demo50 trilingue03\r\n1. Verifique el SHA256 del ZIP con el registro externo antes de extraer.\r\n2. Extraiga en C:\\RackClick_Instalar18\\Extraido18 y abra 00-LEEME.html.\r\n3. En la carpeta RackClick-Windows-Completo-18 ejecute 01-INSTALAR.cmd.\r\n4. Tras instalacion y reinicio verificado, ejecute CARGAR-50-CLIENTES\\CARGAR-50-CLIENTES.cmd.\r\n5. Credenciales nuevas y MFA se introducen de forma privada. No hay contrasenas predeterminadas.\r\n6. Compruebe demo50_loaded_verified, los50 nombres y genere otro backup.\r\nNo instala sobre D/E. No habilita Restore48 ni cambio de red48. No es adopcion productiva.\r\n').encode('ascii')
    delivery=dict(schemaVersion=1,kind='RackClickCompleteWindowsCandidate',edition='18',applicationSchema=48,mode='New',demoCustomers=50,customerNameLanguages={'en':17,'de':17,'es':16},applicationManifestSha256=APP_SHA,bundleSha256=BUNDLE_SHA,wrapperSha256=WRAPPER_SHA,demoArchiveSha256=DEMO_SHA,productAdopted=False,files=[dict(path=n,size=len(v),sha256=sha(v)) for n,v in sorted(entries.items())])
    entries['ENTREGA.json']=(json.dumps(delivery,indent=2)+'\n').encode('ascii')
    entries['SHA256SUMS.txt']=(''.join(sha(v)+'  '+n+'\n' for n,v in sorted(entries.items()))).encode('ascii')
    return entries
def build(wrapper,demo,output):
    target=checked_path(output,LOCAL);require(not target.exists() and target.suffix=='.zip','new_zip_required')
    entries=collect(wrapper,demo)
    with target.open('xb') as out:
        with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_STORED) as z:
            for n,v in sorted(entries.items()):
                info=zipfile.ZipInfo(PREFIX+n,STAMP);info.create_system=3;info.external_attr=0o100644<<16;z.writestr(info,v)
    return dict(path=str(target),sha256=sha(target.read_bytes()),bytes=target.stat().st_size,files=len(entries),installed=False)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--wrapper',type=Path,required=True);p.add_argument('--demo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.wrapper,a.demo,a.output),indent=2))
