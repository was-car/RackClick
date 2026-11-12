"""Publishable own-only transport. Official third-party runtimes are acquired on target."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,io,json,re,sys,zipfile
ROOT=Path(__file__).resolve().parents[1]
REFERENCE_SHA='512fcaf6aa255e6ff6ae9610daa722f8b9d135972d33d5a249b9d42ad90625ed'
WRAPPER18='79ad195d1307c7da4a79e5dede38ab4fae4fd34a454d5e10ad3bf7890cd27c31'
PAYLOAD18='9ce1f7258affda57065ab14bd3a3c2a45aea8e30e44d88bf94cddb42d60ac613'
BUNDLE_SHA='098392ebfc62f2fe5ec9f79909ea3bdbecbf3c565286747a5a9d9507fccd8d40'
APP_SHA='a7b622f917404bbe3ea2560e1fcc2dad008910395c6ab5fa8bc6875be2c88112'
DEMO_SHA='d7ab9469d4929af703285b0cc7eddcf13e9f245f43828cfcaee95c0e2d2e9215'
CORE19_SHA='572215e3e99b2510f64433ba458beead7de69c761b722ef521b0abb221ca35e5'
NATIVE19_SHA='4bb169adf155cb521ace5917afce40ddf3a59ff5a4123c5ce726bcc3f28584dd'
STAMP=(2026,11,12,0,0,0)
sha=lambda data:hashlib.sha256(data).hexdigest()
def require(ok,code):
    if not ok:raise ValueError(code)
def members(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names=z.namelist();require(len(names)==len(set(n.casefold() for n in names)),'duplicate_member')
        require(all(not n.startswith('/') and '..' not in PurePosixPath(n).parts and ':' not in n and '\\' not in n and not n.endswith('/') for n in names),'unsafe_member')
        return {n:z.read(n) for n in names}
def collect(reference,demo,application):
    raw=Path(reference).read_bytes();require(sha(raw)==REFERENCE_SHA,'reference18_pin_mismatch')
    full=members(raw);wrapper=full['RackClick-Windows-Completo-18/Servidor/Servidor.zip'];require(sha(wrapper)==PAYLOAD18,'payload18_pin_invalid')
    payload={n.removeprefix('RackClick-Instalador/'):v for n,v in members(wrapper).items()}
    bundle=payload['RackClick.zip'];require(sha(bundle)==BUNDLE_SHA,'bundle_pin_invalid');inside=members(bundle)
    files={}
    for n,v in payload.items():
        if n.startswith('operators/server-install/'):files['source/tools/windows/server-install/'+n.split('operators/server-install/',1)[1]]=v
        elif n.startswith('service/') and n!='service/RackClick.WindowsService.exe':files[n]=v
    require(sum(n.startswith('service/') for n in files)==37,'service_inventory_invalid')
    require(sha(files['service/RackClick.WindowsService.dll'])=='130e9cc3959d414a0e00759a2e3323a0fc004d76113df56c250f319d38065c61','service_pin_invalid')
    for n,v in inside.items():
        if n.startswith('operators/'):files['source/tools/windows/'+n[10:]]=v
        elif n.startswith('docs/'):files['source/'+n]=v
        elif n in {'licenses/Npgsql-LICENSE','licenses/Otp.NET-LICENSE.txt'}:files['notices/'+n[9:]]=v
    app=Path(application);require(sha((app/'manifest.json').read_bytes())==APP_SHA,'application_pin_invalid')
    require(sha((app/'inventory.json').read_bytes())=='f08abc37d9d129db72bedd8d2f4bdfee7c7f76946ff717b36e216de38b789c77','application_inventory_pin_invalid')
    require(sha((app/'SHA256SUMS.txt').read_bytes())=='a62e81a358c1393eb49652b6800883c4766c736dadb9a80733dbb0b027f58573','application_sums_pin_invalid')
    app_manifest=json.loads((app/'manifest.json').read_text('utf-8'))
    total_app_bytes=0
    for group,entries in app_manifest['distributions'].items():
        for name,record in entries.items():
            data=(app/group/name).read_bytes()
            require(sha(data)==record,'application_content_invalid');total_app_bytes+=len(data)
    require(total_app_bytes==app_manifest['totalBytes'],'application_size_invalid')
    for p in app.rglob('*'):
        require(not p.is_symlink() and not p.is_junction(),'reparse_rejected')
        if p.is_file():files['application/'+p.relative_to(app).as_posix()]=p.read_bytes()
    require(sum(n.startswith('application/') for n in files)==79,'application_inventory_invalid')
    for name in ['tools/package_offline_bundle.py','tools/package_server_installer.py','tools/package_clean_server_installer.py','tools/windows/server-reset/Start-RackClickCleanInstall.ps1','development/toolchain.lock.json','development/offline-bundle14.sources.json','development/windows-service/packages.lock.json','docs/INSTALADOR19-SQL-PROTEGIDO.html','licenses/service-host-MIT.txt','licenses/service-host-THIRD-PARTY-NOTICES.txt']:
        files['source/'+name]=(ROOT/name).read_bytes()
    require(sha(files['source/tools/package_offline_bundle.py'])=='f9c094384dbb422bbb009e7852fcf6c9a4119890c9eec21cbdfe6917344a72b4','bundle_producer_pin_invalid')
    # The published clean launcher must be the reviewed18 launcher; copy from wrapper.
    outer19=full['RackClick-Windows-Completo-18/Servidor/INICIAR.ps1']
    # clean_build reads the generic template; the template source is pinned in release inputs.
    require(b'RackClick' in outer19,'entry_invalid')
    data=Path(demo).read_bytes();require(sha(data)==DEMO_SHA,'demo_pin_invalid');files['data/RackClick-Demo50-Trilingual-03.zip']=data
    files['assemble.py']=(ROOT/'tools/online-install/assemble.py').read_bytes()
    recipe=json.loads((ROOT/'development/online-installer19.sources.json').read_text('utf-8'))
    files['recipe.json']=(json.dumps(recipe,sort_keys=True,indent=2)+'\n').encode()
    require(not any(n.endswith('vc_redist.x64.exe') or 'dependencies/dotnet/' in n or 'dependencies/postgresql/' in n or n.endswith('python312.dll') or n=='service/RackClick.WindowsService.exe' for n in files),'restricted_runtime_in_transport')
    files['FILES.json']=(json.dumps([dict(path=n,bytes=len(v),sha256=sha(v)) for n,v in sorted(files.items())],sort_keys=True,indent=2)+'\n').encode()
    return files
def write_zip(files,output,prefix=''):
    target=Path(output);require(not target.exists(),'new_output_required')
    with target.open('xb') as out,zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for n,v in sorted(files.items()):
            info=zipfile.ZipInfo(prefix+n,STAMP);info.create_system=3;info.external_attr=0o100644<<16;info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,v,compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)
    return dict(path=str(target),sha256=sha(target.read_bytes()),bytes=target.stat().st_size,files=len(files))

def package(core,native,output):
    # Publication is tied to the exact reviewed transport and reconstructed native19.
    core_data=Path(core).read_bytes();require(sha(core_data)==CORE19_SHA,'core_release_pin_invalid')
    native_data=Path(native).read_bytes();require(sha(native_data)==NATIVE19_SHA,'native_release_pin_invalid')
    core_files=members(core_data);rows=json.loads(core_files['FILES.json'])
    require(set(core_files)=={r['path'] for r in rows}|{'FILES.json'},'core_release_inventory_invalid')
    for row in rows:
        data=core_files[row['path']];require(len(data)==row['bytes'] and sha(data)==row['sha256'],'core_release_content_invalid')
    recipe=json.loads(core_files['recipe.json']);require(recipe['nativeEdition']=='19' and recipe['applicationSha256']==APP_SHA and recipe['bundleSha256']==BUNDLE_SHA,'core_release_profile_invalid')
    template=(ROOT/'tools/windows/online-install/Install-RackClickOnline.ps1').read_text('utf-8')
    for token,value in {'@@CORE_SHA@@':CORE19_SHA,'@@NATIVE_SHA@@':NATIVE19_SHA,'@@PY_SHA@@':recipe['python']['digest'],'@@PY_BYTES@@':str(recipe['python']['bytes'])}.items():
        require(template.count(token)==1,'launcher_template_invalid');template=template.replace(token,value)
    require('@@' not in template,'launcher_unresolved_pin')
    files={'RackClick-Core19.zip':core_data,'Install-RackClickOnline.ps1':template.replace('\r\n','\n').replace('\n','\r\n').encode('ascii'),
        'INICIAR-RACKCLICK.cmd':(ROOT/'tools/windows/online-install/INICIAR-RACKCLICK.cmd').read_bytes(),
        '00-LEEME.html':(ROOT/'docs/INSTALADOR19-ONLINE.html').read_bytes()}
    demo=core_files['data/RackClick-Demo50-Trilingual-03.zip'];require(sha(demo)==DEMO_SHA,'demo_pin_invalid')
    for name,data in members(demo).items():
        prefix='RackClick-Demo50-Trilingual-03/'
        require(name.startswith(prefix),'demo_layout_invalid');relative=name[len(prefix):]
        if relative.startswith(('CARGAR-50-CLIENTES/','DATOS-DEMO50/')):files[relative]=data
    require(sum(n.startswith(('CARGAR-50-CLIENTES/','DATOS-DEMO50/')) for n in files)==62,'demo_release_inventory_invalid')
    receipt=dict(format='RackClickWindowsOnline19',edition='19',transportRevision=3,applicationSchema=48,coreSha256=CORE19_SHA,nativeSha256=NATIVE19_SHA,
        applicationManifestSha256=APP_SHA,bundleSha256=BUNDLE_SHA,demoSha256=DEMO_SHA,demoCustomers=50,providerDownloads=recipe['providers']+[recipe['python']],
        thirdPartyRuntimeBinariesIncluded=False,productionAdopted=False)
    files['ENTREGA.json']=(json.dumps(receipt,ensure_ascii=True,sort_keys=True,indent=2)+'\n').encode()
    files['SHA256SUMS.txt']=(''.join(sha(v)+'  '+n+'\n' for n,v in sorted(files.items()))).encode('utf-8')
    return write_zip(files,output,'RackClick-Windows-Online-19/')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--reference18',type=Path);p.add_argument('--demo',type=Path);p.add_argument('--application',type=Path);p.add_argument('--core',type=Path);p.add_argument('--native',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.core and a.native and not any([a.reference18,a.demo,a.application]):result=package(a.core,a.native,a.output)
    elif all([a.reference18,a.demo,a.application]) and not any([a.core,a.native]):result=write_zip(collect(a.reference18,a.demo,a.application),a.output)
    else:p.error('choose core inputs OR --core/--native')
    print(json.dumps(result))
