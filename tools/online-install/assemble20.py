"""Verified local assembly from an own-only core and official downloads. No installation."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,importlib,json,os,re,shutil,sys,traceback,urllib.parse,zipfile
sys.dont_write_bytecode=True
HOSTS={'builds.dotnet.microsoft.com','dotnetcli.blob.core.windows.net','dotnetcli.azureedge.net','get.enterprisedb.com','download.visualstudio.microsoft.com','www.python.org'}
BUNDLE_SHA='c69a82210a4f221058c088d01e5b70a13c4ec1855386692c44774cc6ee28efea'
APP_SHA='f7b971f31dd5f424dbce35c9c18a4c6c75c8968f31d10c5df8bbfe215e5b8a53'
RECIPE_SHA='7b47bf9d6bda91bbbfb6ec1aa177a2c8f2cae14b0db86374fb4008d0c1ea226e'
DEMO_SHA='d7ab9469d4929af703285b0cc7eddcf13e9f245f43828cfcaee95c0e2d2e9215'
_owned_work=None
def require(ok,code):
    if not ok:raise ValueError(code)
def safe_name(name):
    require(isinstance(name,str) and name and '\\' not in name and ':' not in name and not name.startswith('/') and not name.endswith('/') and not any(ord(c)<32 for c in name),'unsafe_member')
    parts=PurePosixPath(name).parts
    require(all(p not in {'.','..'} and p==p.rstrip(' .') and p.split('.')[0].casefold() not in {'con','prn','aux','nul',*(f'com{i}' for i in range(1,10)),*(f'lpt{i}' for i in range(1,10))} for p in parts),'unsafe_member')
    require('/'.join(parts)==name,'unsafe_member');return name
def no_reparse(path):
    for p in (Path(path).absolute(),*Path(path).absolute().parents):
        require(not p.is_symlink() and not p.is_junction(),'reparse_rejected')
    return Path(path).absolute()
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def unique(pairs):
    d={}
    for k,v in pairs:require(k not in d,'duplicate_json_key');d[k]=v
    return d
def read_json(path):return json.loads(Path(path).read_text('utf-8'),object_pairs_hook=unique)
def verify_core(root):
    root=no_reparse(root);rows=read_json(root/'FILES.json');seen=set()
    require(isinstance(rows,list),'core_inventory_invalid')
    for row in rows:
        require(set(row)=={'path','bytes','sha256'},'core_inventory_invalid');name=safe_name(row['path'])
        require(name.casefold() not in seen and name!='FILES.json','core_inventory_invalid');seen.add(name.casefold())
        p=no_reparse(root/name);require(p.is_file() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],'core_content_invalid')
    files=set()
    for p in root.rglob('*'):
        no_reparse(p)
        if p.is_file():files.add(p.relative_to(root).as_posix().casefold())
    require(files==seen|{'files.json'},'core_inventory_invalid');return rows
def check_url(url):
    u=urllib.parse.urlsplit(url)
    require(u.scheme=='https' and u.hostname in HOSTS and not u.username and not u.password and u.port in {None,443} and not u.fragment,'provider_url_invalid')
def verify_provider(path,item):
    require(path.is_file() and path.stat().st_size==item['bytes'],'provider_content_invalid')
    require(item['algorithm'] in {'sha256','sha512'},'provider_profile_invalid')
    h=hashlib.new(item['algorithm'])
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    require(h.hexdigest()==item['digest'],'provider_content_invalid')
def acquire(item,target,cache=None):
    # All network traffic belongs to the Windows SChannel transport. Python only
    # consumes the exact complete cache; it never falls back to urllib/OpenSSL.
    require(cache is not None,'provider_cache_required')
    check_url(item['url']);target=no_reparse(target);require(not target.exists(),'provider_target_exists')
    candidate=no_reparse(Path(cache)/safe_name(item['fileName']))
    require(candidate.is_file(),'provider_cache_incomplete');verify_provider(candidate,item)
    target.parent.mkdir(parents=True,exist_ok=True)
    with candidate.open('rb') as src,target.open('xb') as out:shutil.copyfileobj(src,out)
    verify_provider(target,item)
def require_new_work(work):
    no_reparse(work);require(not Path(work).exists(),'new_assembly_root_required')
def extract_new(archive,target):
    require(not target.exists(),'extract_target_exists');target.mkdir()
    with zipfile.ZipFile(archive) as z:
        seen=set();total=0
        for info in z.infolist():
            name=safe_name(info.filename);require(name.casefold() not in seen,'duplicate_member');seen.add(name.casefold())
            require(not info.is_dir() and (info.external_attr>>16)&0o170000 not in {0o120000},'member_type_invalid')
            total+=info.file_size;require(total<=512*1024*1024,'extract_size_invalid')
            p=target/name;p.parent.mkdir(parents=True,exist_ok=True)
            with z.open(info) as src,p.open('xb') as out:shutil.copyfileobj(src,out)
def assemble(core,work,cache=None):
    global _owned_work
    _owned_work=None
    rows=verify_core(core);core=Path(core).absolute();work=Path(work).absolute();require_new_work(work)
    require(cache is not None,'provider_cache_required')
    require(sha(core/'recipe.json')==RECIPE_SHA,'recipe_pin_invalid')
    recipe=read_json(core/'recipe.json');require(recipe['format']=='RackClickOnline20' and recipe['bundleSha256']==BUNDLE_SHA and recipe['applicationSha256']==APP_SHA,'recipe_invalid')
    work.mkdir();_owned_work=work.resolve();(work/'.local').mkdir()
    for row in rows:
        name=row['path'];dest=None
        if name.startswith('source/'):dest=work/name[7:]
        elif name.startswith('application/'):dest=work/'.local/distribution48/admin-data-01'/name[12:]
        elif name.startswith('service/'):dest=work/'.local/service'/name[8:]
        if dest:
            dest.parent.mkdir(parents=True,exist_ok=True)
            with (core/name).open('rb') as src,dest.open('xb') as out:shutil.copyfileobj(src,out)
    providers=recipe['providers'];require({v['id'] for v in providers}=={'sdk','postgresql','crt'} and len(providers)==3,'provider_inventory_invalid')
    acquired={}
    for item in providers:
        relative=safe_name(item['target']);require(relative.startswith('.local/downloads/'),'provider_target_invalid')
        dest=work/relative;acquire(item,dest,cache);acquired[item['id']]=dest
    lock=read_json(work/'development/offline-bundle14.sources.json')
    notice_names={'Npgsql-LICENSE':'notices/Npgsql-LICENSE','Otp.NET-LICENSE':'notices/Otp.NET-LICENSE.txt'}
    for row in lock['sources']:
        if row['name']=='vc_redist.x64.exe':require((work/safe_name(row['path']))==acquired['crt'],'crt_target_invalid');continue
        require(row['name'] in notice_names,'source_notice_invalid');dest=work/safe_name(row['path']);dest.parent.mkdir(parents=True,exist_ok=True)
        with (core/notice_names[row['name']]).open('rb') as src,dest.open('xb') as out:shutil.copyfileobj(src,out)
    require(sha(work/'.local/distribution48/admin-data-01/manifest.json')==APP_SHA,'application_pin_invalid')
    sys.path.insert(0,str(work/'tools'))
    bundle=importlib.import_module('package_offline_bundle')
    bundle_file=work/'.local/RackClick-Bundle-48-20.zip'
    bundle.build(work/'.local/distribution48/admin-data-01/manifest.json',APP_SHA,acquired['sdk'],acquired['postgresql'],work/'development/offline-bundle14.sources.json',bundle_file,work/'.local/bundle-evidence20')
    require(sha(bundle_file)==BUNDLE_SHA,'reconstructed_bundle_mismatch')
    wrapper=work/'.local/RackClick-Servidor-20.zip';clean=importlib.import_module('package_clean_server_installer')
    clean.clean_build(bundle_file,work/'.local/service',wrapper,work/'.local/RackClick-Payload-20.zip',bundle_sha256=BUNDLE_SHA,edition='20',stamp=(2026,11,12,0,0,0))
    extract_new(wrapper,work/'native20')
    # Demo50 is embedded in the application. Keep the exact source ZIP for audit;
    # do not stage the legacy application-pinned CMD/PowerShell loader as runnable tools.
    demo=core/'data/RackClick-Demo50-Trilingual-03.zip';require(sha(demo)==DEMO_SHA,'demo_pin_invalid')
    result=dict(success=True,code='online_assembled',applicationSchema=48,bundleSha256=BUNDLE_SHA,wrapperSha256=sha(wrapper),installed=False,providersVerified=3,demoCustomers=50)
    (work/'assembly-report.json').write_text(json.dumps(result,indent=2)+'\n','utf-8');return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--core-root',type=Path,required=True);p.add_argument('--work-root',type=Path,required=True);p.add_argument('--cache',type=Path);args=p.parse_args()
    try:result=assemble(args.core_root,args.work_root,args.cache)
    except Exception as exc:
        if _owned_work==args.work_root.resolve() and args.work_root.is_dir():
            try:(args.work_root/'assembly-error.private.txt').write_text(traceback.format_exc(),'utf-8')
            except OSError:pass
        code=str(exc) if isinstance(exc,ValueError) and re.fullmatch('[a-z0-9_]{1,90}',str(exc)) else 'online_assembly_failed'
        result=dict(success=False,code=code,installed=False,errorType=type(exc).__name__)
    print(json.dumps(result));sys.exit(0 if result['success'] else 1)
