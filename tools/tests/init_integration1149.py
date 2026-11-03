"""Freeze schema13 integration inputs and privately archive source runtime files."""
from datetime import datetime,timezone
import hashlib,json,shutil,subprocess,sys,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-1090-1149'
TARGET='evidence/s1-20261018/sesenta-tandas-1030-1089/CANDIDATA1089-02.json'
PIN='c8b3df5b8e0fb6c5db148b7ddca2a8064ade6b90557713fb0835cbf69bb9710c'
MANUALS=['MANUAL-PAQUETE-WINDOWS-S1.md','CONSTRUIR-PAQUETE-WINDOWS-S1.md','OPERAR-DESPLIEGUE-PRIVADO-WINDOWS-S1.md','RECUPERACION-DESPLIEGUE-WINDOWS-S1.md']
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,v):
 with p.open('x',encoding='utf-8') as f:f.write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def main():
 E.mkdir(parents=True,exist_ok=True);assert not (E/'INICIO.json').exists();assert sha(ROOT/TARGET)==PIN
 paths=[];source_guards={};pointer=ROOT/'.local/qa-rc9/current.json';source=Path(json.loads(pointer.read_bytes())['directory'])
 for p in source.iterdir():
  if p.is_file():paths.append(p);source_guards[p.relative_to(ROOT).as_posix()]=sha(p)
 for p in [pointer,ROOT/'.local/qa-wascar/current.json']:
  paths.append(p);directory=Path(json.loads(p.read_bytes())['directory']);paths.extend(x for x in directory.iterdir() if x.is_file())
 for name in ['sesenta-tandas-970-1029','sesenta-tandas-1030-1089']:paths.extend(p for p in (ROOT/'evidence/s1-20261018'/name).rglob('*') if p.is_file())
 for name in [TARGET,'evidence/s1-20261018/sesenta-tandas-970-1029/CANDIDATA969-FIX02.json','evidence/s1-20261018/tanda-849/CANDIDATA849.json']:
  p=ROOT/name;m=json.loads(p.read_bytes());paths.append(p);paths.extend(ROOT/m['candidateDirectory']/part/n for part,files in m['distributions'].items() for n in files)
 paths.extend(p for p in (ROOT/'tools/windows').iterdir() if p.is_file())
 paths.extend(ROOT/p for p in ['tools/package_offline_bundle.py','development/toolchain.lock.json','development/offline-bundle.sources.json',
  'development/server/global.json','development/frontend/package-lock.json','GUIA-QA-WASCAR.html','GUIA-QA-RESTAURADO.html','docs/QA-CASOS-WASCAR.json'])
 paths.extend(ROOT/'docs'/p for p in MANUALS)
 guards={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(paths))}
 mutable=['tools/package_offline_bundle.py','tools/windows/Test-ServerDistribution.ps1','tools/windows/RackClick.OfflineBundle.ps1',
  'tools/windows/RackClick.Stage.ps1','tools/windows/Start-RackClickLabInstance.ps1','tools/windows/qa_guide.py','.local/qa-rc9/current.json',
  'GUIA-QA-WASCAR.html','GUIA-QA-RESTAURADO.html','docs/QA-CASOS-WASCAR.json']+['docs/'+p for p in MANUALS]
 runtime=['postgres.log','manual-control.log','manual-server.log','pg_ctl.log','preview-manual-qa.json','stop.request','server.lock']
 sys.path.insert(0,str(ROOT/'development/server/tests'));from pg_support import protect_directory
 archive=ROOT/'.local'/('source-runtime1149-'+uuid.uuid4().hex);archive.mkdir();protect_directory(archive);runtime_record={}
 for name in runtime:
  p=source/name
  if p.exists():
   dest=archive/name;shutil.copy2(p,dest);assert sha(dest)==sha(p)
   runtime_record[p.relative_to(ROOT).as_posix()]=dict(sha256=sha(p),bytes=p.stat().st_size,privateArchive=dest.relative_to(ROOT).as_posix())
 initial=dict(utc=datetime.now(timezone.utc).isoformat(),baseCommit=subprocess.check_output([str(ROOT/'.local/git-2.55.0.5/cmd/git.exe'),'rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
  guards=guards,sourceQaGuards=source_guards,authorizedMutableGuards=mutable,targetManifest=TARGET,targetManifestSha256=PIN,
  sourceDirectory=source.relative_to(ROOT).as_posix(),sourceSchema=12,sourceRecoverySchema=11,targetSchema=13,targetRecoverySchema=12,progress=78,applicationBuilds=0,frontendBuilds=0)
 write(E/'INICIO.json',initial);write(E/'ALCANCE-RUNTIME-FUENTE.json',dict(authorizedMutableRuntimeFiles=runtime_record,
  scope='Original transient runtime/log bytes archived privately before owned source operations. No exceptions for configs, credentials, artifacts, prepared seals or database data.'))
 write(E/'SOURCE-FREEZE-APP.json',json.loads((ROOT/'evidence/s1-20261018/sesenta-tandas-1030-1089/SOURCE-FREEZE-02.json').read_bytes()))
 print(json.dumps(dict(guards=len(guards),sourceRootFiles=len(source_guards),privateRuntimeArchives=len(runtime_record),target=TARGET,pin=PIN)))
if __name__=='__main__':main()
