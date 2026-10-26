"""Integration1449 coordinator; preserve actual QA data and all historical inputs."""
import argparse,hashlib,json,shutil,subprocess,sys,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ER='evidence/s1-20261018/sesenta-tandas-1450-1509';E=ROOT/ER
BASE='7d77210f4628326f1e59ffdc7debe5a969660ebf';GIT=ROOT/'.local/git-2.55.0.5/cmd/git.exe'
TARGET='evidence/s1-20261018/sesenta-tandas-1390-1449/CANDIDATA1449-01.json';PIN='55bdd496ec654494fd8e3400140e3e84241488986e24481939bad67cde7a91c6'
MANUALS=['MANUAL-PAQUETE-WINDOWS-S1.md','CONSTRUIR-PAQUETE-WINDOWS-S1.md','OPERAR-DESPLIEGUE-PRIVADO-WINDOWS-S1.md','RECUPERACION-DESPLIEGUE-WINDOWS-S1.md']
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(p.read_bytes())
def save(name,data):
 with (E/name).open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n')
def exact(values):assert values and all(sha(ROOT/p)==h for p,h in values.items())
def init():
 E.mkdir(parents=True,exist_ok=True);assert not (E/'INICIO.json').exists();assert subprocess.check_output([str(GIT),'rev-parse','HEAD']).decode().strip()==BASE
 assert not subprocess.check_output([str(GIT),'diff','--name-only']) and not subprocess.check_output([str(GIT),'diff','--cached','--name-only']);assert sha(ROOT/TARGET)==PIN
 m=read(ROOT/TARGET);assert (m['schema'],m['fileCount'],m['totalBytes'])==(13,40,7159235)
 pointer=ROOT/'.local/qa-rc9/current.json';directory=Path(read(pointer)['directory']);cfg=read(directory/'manual-qa.json');previous=read(ROOT/'evidence/s1-20261018/sesenta-tandas-1270-1329/CANDIDATA1329-01.json');assert cfg['bundleSha256']==previous['distributions']['frontend']['app.js']
 legacyPointer=ROOT/'.local/qa-wascar/current.json';legacy=Path(read(legacyPointer)['directory']);prior=read(ROOT/'evidence/s1-20261018/sesenta-tandas-1390-1449/INICIO.json');prefixes=[directory.relative_to(ROOT).as_posix()+'/',legacy.relative_to(ROOT).as_posix()+'/']
 old={p:h for p,h in prior['guards'].items() if p not in prior['allowedProductChanges'] and not any(p.startswith(prefix) for prefix in prefixes)};exact(old)
 sources=read(ROOT/'evidence/s1-20261018/sesenta-tandas-1390-1449/SOURCE-FREEZE-APP.json')['sources'];assert len(sources)==195;exact(sources)
 paths=[ROOT/p for p in old]+[ROOT/p for p in sources]+[pointer,legacyPointer]
 paths.extend(p for d in [directory,legacy] for p in d.iterdir() if p.is_file())
 paths.extend(p for part in ['server','frontend','versions'] for p in (directory/part).rglob('*') if p.is_file())
 paths.extend(p for p in (ROOT/'evidence/s1-20261018/sesenta-tandas-1390-1449').rglob('*') if p.is_file())
 paths.extend(ROOT/m['candidateDirectory']/part/p for part,files in m['distributions'].items() for p in files)
 operators=subprocess.check_output([str(GIT),'ls-tree','-r','--name-only',BASE,'tools/windows']).decode().splitlines();paths.extend(ROOT/p for p in operators)
 paths.extend(ROOT/p for p in ['tools/package_offline_bundle.py','development/toolchain.lock.json','development/offline-bundle.sources.json','GUIA-QA-WASCAR.html','GUIA-QA-RESTAURADO.html','docs/QA-CASOS-WASCAR.json']+['docs/'+n for n in MANUALS]);guards={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(paths))}
 sys.path.insert(0,str(ROOT/'development/server/tests'));from pg_support import protect_directory
 archive=ROOT/'.local'/('source-runtime1509-'+uuid.uuid4().hex);archive.mkdir();protect_directory(archive);runtime={}
 for name in ['postgres.log','manual-control.log','manual-server.log','pg_ctl.log','preview-manual-qa.json','stop.request','server.lock']:
  p=directory/name
  if p.is_file():
   target=archive/name;shutil.copy2(p,target);assert sha(p)==sha(target);runtime[p.relative_to(ROOT).as_posix()]=dict(sha256=sha(p),bytes=p.stat().st_size,privateArchive=target.relative_to(ROOT).as_posix())
 shutil.copy2(directory/'manual-qa.json',archive/'original-manual-qa.json')
 mutable=['tools/package_offline_bundle.py','tools/windows/Test-ServerDistribution.ps1','tools/windows/RackClick.OfflineBundle.ps1','tools/windows/qa_guide.py','GUIA-QA-WASCAR.html','GUIA-QA-RESTAURADO.html','docs/QA-CASOS-WASCAR.json',directory.relative_to(ROOT).as_posix()+'/manual-qa.json']+['docs/'+n for n in MANUALS]
 save('INICIO.json',dict(utc=datetime.now(timezone.utc).isoformat(),baseCommit=BASE,guards=guards,sourceQaGuards={p.relative_to(ROOT).as_posix():sha(p) for p in directory.iterdir() if p.is_file()},authorizedMutableGuards=mutable,authorizedMutableRuntimeFiles=runtime,originalConfigurationArchive=(archive/'original-manual-qa.json').relative_to(ROOT).as_posix(),sourceDirectory=directory.relative_to(ROOT).as_posix(),sourceRevision=1329,sourceSchema=13,sourceRecoveryRevision=969,sourceRecoverySchema=12,targetManifest=TARGET,targetManifestSha256=PIN,progress=78,applicationBuilds=0,frontendBuilds=0,actualQaStartedAtInit=False))
 save('SOURCE-FREEZE-APP.json',dict(sources=sources,sourceCount=195,changedExistingSources=[],newSources=[],serverSourcesUnchanged=True));print(json.dumps(dict(guards=len(guards),sources=195,runtimeArchived=len(runtime),source=1329,target=1449,progress=78)))
def guards():
 initial=read(E/'INICIO.json');mutable=set(initial['authorizedMutableGuards'])|set(initial['authorizedMutableRuntimeFiles']);protected={p:h for p,h in initial['guards'].items() if p not in mutable};exact(protected);exact(read(E/'SOURCE-FREEZE-APP.json')['sources'])
 for p,row in initial['authorizedMutableRuntimeFiles'].items():assert sha(ROOT/row['privateArchive'])==row['sha256']
 assert sha(ROOT/initial['originalConfigurationArchive'])==initial['guards'][initial['sourceDirectory']+'/manual-qa.json'];return initial,len(protected)
def manuals():
 assert not (E/'MANUALES-01.json').exists();archive=E/'manuals-before';archive.mkdir();changes={}
 heads={
 MANUALS[0]:'**Integración1450–1509 · candidata1449-01/esquema13.** Grupo creado→Abrir relaciones por UUID confirmado, sin asignaciones.40archivos22+18/7.159.235bytes; servidor1089 exacto. New/Restore en raíces nuevas; QA13 conserva datos/recuperación96912. Instalación definitiva y adopción pendientes.',
 MANUALS[1]:'**Integración1450–1509.** Doce perfiles cerrados:337/397/532 de9,592 de10,712/832/849 de11,969 de12 y1089/1209/1329/1449 de13. Candidata1449 exacta, cero compilaciones.25operadores/cuatro manuales/productor congelados antes de dosZIP idénticos; versiones y pines anteriores intactos.',
 MANUALS[2]:'**Aplicación1449/esquema13, servidor1089 exacto.** Recibo confirmado y continuación explícita por UUID sin conceder acceso. QA13 mantiene misma principal39tablas/recuperación96912 de37, cuentas/sesiones/puntero. Sólo artifactDirectory+bundleSha256; cadena1329→1449 sellada sin migrar.',
 MANUALS[3]:'**Compatibilidad1449/esquema13.** Restore administrativo crea raíz/base/roles/TLS/admin nuevos, revoca sesiones copiadas y conserva propietarios. ActualizaciónQA1509 sólo interfaz en misma raíz13/recuperación12; retorno durante fallo sujeto a entradas/quietud/actividad y misma operación explícita, nunca rollback tardío. Recuperación integral y adopción pendientes.'}
 addition='''
## Alta de grupos1449 y operación1450–1509

Candidata1449-01: SHA25655bdd496ec654494fd8e3400140e3e84241488986e24481939bad67cde7a91c6,40archivos/22+18/7.159.235bytes/esquema13.195fuentes; sólo app.js difiere de1329, servidor1089/SQL001–013/CSS/dependencias exactos. Las secciones de integraciones anteriores son antecedentes.

Interfaz: INICIAR-QA-RESTAURADO.cmd→guía y credenciales privadas. Desde Todos los clientes elige Español arriba a la derecha y espera guardado; dentro de Administración no hay selector de idioma. Barra izquierda→Usuarios→debajo de Lista de cuentas, Grupos y permisos→Crear grupo. Elige Grupo de usuarios o Grupo de clientes, escribe nombre y pulsa Crear grupo. Tras commit, Grupo creado muestra nombre literal/tipo/UUID; Abrir relaciones abre sólo la ficha exacta y enfoca Grupo seleccionado. No añade miembros ni concede permisos. Navegar conserva los tres editores; salir de Administración/recargar retira el recibo temporal, sin borrar el grupo persistido.

Si queda pendiente: Consultar resultado del grupo, Reintentar alta original o Cancelar alta de grupo pendiente conservan la intención original. No registrado no acredita cancelación ni crea recibo; un commit ya confirmado se conserva ante fallo de limpieza, bloqueando continuación hasta resolver pendiente y leer snapshot válido. Los casos QA91–93 sólo se habilitan después de selección revisada de1449. Conserva observaciones y resultados anteriores; voz requiere lector habitual, no una prueba visual.

Actualización QA1509: mismo clúster/principal13(39tablas)/recuperación96912(37), cuentas/contraseñas/sesiones/permisos/datos/puntero. Sólo artifactDirectory+bundleSha256; nueva versión1449 y registro/sello propios. Cadena1149→1209→1329 intacta, inventario exacto, nada de migrar/copiar bases/bootstrap/recover-admin/login/DML de aplicación en QA real. Baseline actual capturado una vez. Sólo la misma operación explícita puede reentrar tras rolled_back confirmado, con registro/sello/baseline/parent1329/puntero intactos y sin actividad intermedia. Interferencia o incertidumbre bloquean retorno; sin rollback tardío.

New/Restore nativos usan laboratorio nuevo, secretos/TLS propios y runtime sinSDK; no acreditan otra máquina, Windows limpio, SCM/PKI productiva o voz. Instalación definitiva, licencias/redistribución, recuperación integral y adopción de Wascar siguen pendientes.

'''
 old_manifest='evidence/s1-20261018/sesenta-tandas-1270-1329/CANDIDATA1329-01.json';old_pin='38bbae727ffd545436506ab65d1c66525a64bf316e0a9354079cace0aa60c6b6'
 for name in MANUALS:
  p=ROOT/'docs'/name;raw=p.read_bytes();(archive/name).write_bytes(raw);text=raw.decode('utf-8').replace('\r\n','\n');prefix,sep,history=text.partition('## Antecedente histórico');assert sep
  start=prefix.index('**');end=prefix.index('\n\n',start);prefix=prefix[:start]+heads[name]+prefix[end:]
  if name==MANUALS[0]:
   old='Interfaz1329-01 con servidor1089-02/esquema13 reutilizados sin compilar en1330–1389.';assert prefix.count(old)==1;prefix=prefix.replace(old,'Interfaz1449-01 con servidor1089-02/esquema13 reutilizados sin compilar en1450–1509.')
   prefix=prefix.replace('1089/1209 y sus informes','1089/1209/1329 y sus informes').replace('1089,1209 o1329 registrado','1089,1209,1329 o1449 registrado')
  elif name==MANUALS[1]:
   prefix=prefix.replace('estos once perfiles','estos doce perfiles');anchor='\n\nEl productor exige el hash externo';assert anchor in prefix;prefix=prefix.replace(anchor,'\n| [1449/alta de grupos](../'+TARGET+') |13 /22+18|7.159.235|`'+PIN+'`|'+anchor,1)
   prefix=prefix.replace('--manifest '+old_manifest,'--manifest '+TARGET).replace('--expected-manifest-sha '+old_pin,'--expected-manifest-sha '+PIN).replace('--evidence evidence/s1-20261018/sesenta-tandas-1330-1389/packaging/NOMBRE-NUEVO','--evidence '+ER+'/packaging/NOMBRE-NUEVO')
  elif name==MANUALS[2]:
   prefix=prefix.replace('1089/1209/1329: esquema13','1089/1209/1329/1449: esquema13');old='[candidata1329 de laboratorio](../'+old_manifest+') tiene referencia `'+old_pin+'`';assert prefix.count(old)==1;prefix=prefix.replace(old,'[candidata1449 de laboratorio](../'+TARGET+') tiene referencia `'+PIN+'`')
  else:prefix=prefix.replace('1089,1209,1329 (esquema13)','1089,1209,1329,1449 (esquema13)').replace('N=13 para1089/1209/1329','N=13 para1089/1209/1329/1449')
  text=prefix+addition+sep+history;text=text.replace('## Relaciones por UUID1329 y operación1330–1389','## Antecedente histórico · relaciones por UUID1329 y operación1330–1389');nl='\r\n' if b'\r\n' in raw else '\n';p.write_bytes(text.replace('\n',nl).encode('utf-8'));changes['docs/'+name]=dict(before=hashlib.sha256(raw).hexdigest(),after=sha(p))
 save('MANUALES-01.json',dict(files=changes,profile=1449,previousReportsPreserved=True,scope='Current headings/allowlists/examples updated; historical sections labeled, exact UI labels and conservative QA transition documented before ZIP.'))
 versions={}
 for row in read(ROOT/'development/toolchain.lock.json')['components']:
  command=[str(ROOT/'.local'/row['installDirectory']/row['executable']),'--version'];out=subprocess.check_output(command,cwd=ROOT/'development/server').decode().strip();assert out==row['versionOutput'];versions[row['id']]=out
 import platform
 save('ENTORNO.json',dict(windows=platform.platform(),python=platform.python_version(),versions=versions,downloads=0,dependencyChanges=0,versionChanges=0,frontendBuilds=0,serverBuilds=0));print(json.dumps(dict(manuals=4,versions=versions)))
def preliminary():
 initial,count=guards();sys.path.insert(0,str(ROOT/'tools/windows'));from qa_artifact13_update1389 import validate_operation,OwnedRuntime
 pointer=ROOT/'.local/qa-rc9/current.json';directory=ROOT/initial['sourceDirectory'];source=validate_operation(directory,pointer,real=True);assert source.revision==1329;OwnedRuntime(directory,source.cfg,source.operation).quiet()
 save('REAL-QA-PRELIMINAR-01.json',dict(valid=True,utc=datetime.now(timezone.utc).isoformat(),directory=initial['sourceDirectory'],sourceRevision=1329,sourceConfigSha256=sha(directory/'manual-qa.json'),pointerSha256=sha(pointer),sourceChainStaticValidated=True,sourceQuiet=True,postgresqlStarted=False,applicationLogin=False,applicationDml=False,protectedFilesExact=count,manualWascarResultsWritten=False));print(json.dumps(dict(valid=True,source=1329,quiet=True,postgresqlStarted=False,protected=count)))
def package(attempt='01'):
 import importlib.util
 assert len(attempt)==2 and attempt.isdecimal() and not (E/('PACKAGES-'+attempt+'.json')).exists();gate=read(E/'revision/PREPAQUETE.json');assert gate['approved'] and not gate['openBlockingFindings'];exact(gate['sourceHashes'])
 spec=importlib.util.spec_from_file_location('builder1509',ROOT/'tools/package_offline_bundle.py');builder=importlib.util.module_from_spec(spec);sys.modules[spec.name]=builder;spec.loader.exec_module(builder);assert builder.application_schema(PIN)==13;guards();assert sha(ROOT/TARGET)==PIN
 paths=[ROOT/'tools/windows'/n for n in builder.OPERATORS]+[ROOT/'docs'/n for n in MANUALS]+[ROOT/p for p in ['tools/package_offline_bundle.py','development/toolchain.lock.json','development/offline-bundle.sources.json']];frozen={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(paths))}
 freeze='SOURCE-FREEZE-PACKAGE-'+attempt+'.json';assert not (E/freeze).exists();save(freeze,dict(sources=frozen,sourceCount=len(frozen),scope='25operators/fourmanuals/producer/locks; coordinator not bundled.'))
 (E/'packaging').mkdir(exist_ok=True);outputs=[];tag=uuid.uuid4().hex
 for suffix in ['a','b']:
  target=ROOT/'.local'/('offline1509-'+tag+'-'+suffix+'.zip');report_dir=E/'packaging'/('build'+attempt+'-'+suffix)
  result=builder.build(ROOT/TARGET,PIN,ROOT/'.local/downloads/dotnet-sdk-10.0.401-win-x64.zip',ROOT/'.local/downloads/postgresql-17.11-4-windows-x64-binaries.zip',ROOT/'development/offline-bundle.sources.json',target,report_dir);assert result['valid'];outputs.append(dict(path=target.relative_to(ROOT).as_posix(),bytes=target.stat().st_size,sha256=sha(target),report=report_dir.relative_to(ROOT).as_posix()+'/REPORT.json'))
 exact(frozen);assert outputs[0]['bytes']==outputs[1]['bytes'] and outputs[0]['sha256']==outputs[1]['sha256'];save('PACKAGES-'+attempt+'.json',dict(valid=True,sourceManifestSha256=PIN,sourceFreeze=ER+'/'+freeze,sourceFreezeSha256=sha(E/freeze),sourcesUnchanged=True,byteIdentical=True,outputs=outputs,newAppBuildsDuringPackaging=0,newFrontendBuildsDuringPackaging=0,qaSelectedAtPackaging=False));print(json.dumps(dict(valid=True,identical=True,outputs=outputs)))
def inspect(attempt='01'):
 import os,time
 assert not (E/('ZIP'+attempt+'-CLI.json')).exists();package=read(E/('PACKAGES-'+attempt+'.json'));exact(read(ROOT/package['sourceFreeze'])['sources']);p=package['outputs'][0];assert package['byteIdentical'] and all(sha(ROOT/x['path'])==x['sha256']==p['sha256'] for x in package['outputs'])
 command=[str(Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'),'-NoLogo','-NoProfile','-NonInteractive','-File',str(ROOT/'tools/windows/Test-RackClickOfflineBundle.ps1'),'-ArchivePath',str(ROOT/p['path']),'-ExpectedArchiveSha256',p['sha256']];start=time.monotonic();result=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=180);report=json.loads(result.stdout)
 valid=result.returncode==0 and not result.stderr and report['valid'] and report['code']=='bundle_verified' and report['bundleArchiveSha256']==p['sha256'] and report['versions']['schema']==13
 save('ZIP'+attempt+'-CLI.json',dict(successful=valid,command=command,exitCode=result.returncode,seconds=round(time.monotonic()-start,3),report=report,stdout=result.stdout.decode('utf-8-sig'),stderr=result.stderr.decode('utf-8-sig'),newInstallation=False,newRestore=False));assert valid;print(json.dumps(dict(successful=True,archiveSha256=p['sha256'],schema=13)))
def operate(action):
 sys.path.insert(0,str(ROOT/'tools/windows'));from qa_artifact13_source1509 import Source1329;from qa_artifact13_update1509 import OwnedRuntime,update_operation,validate_operation
 output='REAL-QA-'+action.upper()+'-01.json';assert not (E/output).exists();initial,count=guards();pointer=ROOT/'.local/qa-rc9/current.json';directory=ROOT/initial['sourceDirectory']
 row=dict(utc=datetime.now(timezone.utc).isoformat(),action=action,valid=False,directory=initial['sourceDirectory'],schema=13,recoverySchema=12,databaseReconstructed=False,schemaMigrationExecuted=False,applicationLogin=False,applicationDml=False,manualWascarResultsWritten=False)
 try:
  if action=='preflight':
   source=Source1329(directory,pointer,real=True);OwnedRuntime(directory,source.cfg).quiet();assert source.revision==1329
   preliminary=read(E/'REAL-QA-PRELIMINAR-01.json');assert sha(pointer)==preliminary['pointerSha256'] and sha(directory/'manual-qa.json')==preliminary['sourceConfigSha256']
   row.update(valid=True,sourceRevision=1329,sourceConfigSha256=sha(directory/'manual-qa.json'),pointerSha256=sha(pointer),sourceInputHashes=source.hashes,sourceQuiet=True,postgresqlStarted=False)
  else:
   go=read(E/'COORDINATOR-GO.json');assert go['valid'] and go['authorizedRealQaArtifactUpdate'];exact(go['gates']);pre=read(E/'REAL-QA-PREFLIGHT-01.json');assert sha(pointer)==pre['pointerSha256'];row['goSha256']=sha(E/'COORDINATOR-GO.json')
   if action=='update':
    source=Source1329(directory,pointer,real=True);OwnedRuntime(directory,source.cfg).quiet();assert source.revision==1329 and source.hashes==pre['sourceInputHashes'] and sha(directory/'manual-qa.json')==pre['sourceConfigSha256']
    result=update_operation(directory,pointer,real=True);state=read(result.journal);assert result.state=='committed'
    row.update(valid=True,state=result.state,selectedRevision=1449,serverRevision=1089,operationDirectory=result.operation.relative_to(ROOT).as_posix(),journalSha256=sha(result.journal),leftRunning=state['leftRunning'],pointerSha256=sha(pointer),idempotent=result.idempotent,databaseTestExecuted=True)
   elif action=='validate':
    source=validate_operation(directory,pointer,real=True);assert source.revision==1449;OwnedRuntime(directory,source.cfg,source.operation).quiet()
    old=read(ROOT/initial['originalConfigurationArchive']);current=read(directory/'manual-qa.json');changed=sorted(k for k in set(old)|set(current) if old.get(k)!=current.get(k));assert changed==['artifactDirectory','bundleSha256']
    states=source.record['databaseStates'];assert len(states['databases']['primary']['snapshot'])==39 and len(states['databases']['recovery969']['snapshot'])==37
    row.update(valid=True,state='static_validated',selectedRevision=1449,serverRevision=1089,databaseTestExecuted=False,operationDirectory=source.operation.relative_to(ROOT).as_posix(),currentConfigSha256=sha(directory/'manual-qa.json'),pointerSha256=sha(pointer),changedConfigFields=changed,leftRunning=False,primaryTables=39,recoveryTables=37,baselineRenewed=False)
   else:raise ValueError('unknown action')
 except Exception as error:row['errorCode']=getattr(error,'code',type(error).__name__);raise
 finally:save(output,row);print(json.dumps({k:v for k,v in row.items() if k!='sourceInputHashes'}))

def go(native_evidence):
 initial,count=guards();gate=read(E/'revision/GATE-TECNICO.json');assert gate['approved'] and gate['valid'] and not gate['openBlockingFindings'] and gate['targetManifestSha256']==PIN
 for key in ['sourceHashes','artifactHashes','guardHashes']:
  if key in gate:exact(gate[key])
 if 'observedFilesSha256' in gate:exact(gate['observedFilesSha256'])
 pre=read(E/'REAL-QA-PREFLIGHT-01.json');pointer=ROOT/'.local/qa-rc9/current.json';directory=ROOT/initial['sourceDirectory'];assert pre['valid'] and sha(pointer)==pre['pointerSha256'] and sha(directory/'manual-qa.json')==pre['sourceConfigSha256']
 sys.path.insert(0,str(ROOT/'tools/windows'));from qa_artifact13_source1509 import Source1329;from qa_artifact13_update1509 import OwnedRuntime
 source=Source1329(directory,pointer,real=True);OwnedRuntime(directory,source.cfg).quiet();assert source.revision==1329 and source.hashes==pre['sourceInputHashes']
 n=read(ROOT/native_evidence);package=read(E/'PACKAGES-01.json');assert n['successful'] and n['inputsUnchanged'] and n['ownedProcessesStopped'] and n['recoverySnapshotExact'] and n['archiveSha256']==package['outputs'][0]['sha256'];assert read(E/'qa-update/RESUMEN-AUTOR.json')['successful'] and read(E/'ZIP01-CLI.json')['successful'];exact(read(ROOT/package['sourceFreeze'])['sources'])
 paths=[ER+'/revision/GATE-TECNICO.json',ER+'/windows/profiles01/result.json',native_evidence,ER+'/PACKAGES-01.json',ER+'/ZIP01-CLI.json',ER+'/qa-update/RESUMEN-AUTOR.json',ER+'/REAL-QA-PREFLIGHT-01.json',ER+'/SOURCE-FREEZE-APP.json',TARGET,'tools/tests/integration1509.py','tools/tests/qa_integration1509.py','tools/windows/qa_artifact13_source1509.py','tools/windows/qa_artifact13_update1509.py']
 save('COORDINATOR-GO.json',dict(valid=True,utc=datetime.now(timezone.utc).isoformat(),authorizedRealQaArtifactUpdate=True,sourceRevision=1329,targetRevision=1449,schema=13,sourceRecoverySchema=12,sourceQuiet=True,protectedFilesExact=count,nativeEvidence=native_evidence,gates={p:sha(ROOT/p) for p in paths},applicationLogin=False,applicationDml=False,finalAdoption=False));print(json.dumps(dict(valid=True,source=1329,target=1449,protected=count,gateFiles=len(paths))))


def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['init','manuals','preliminary','package','inspect','preflight','update','validate','go']);p.add_argument('--attempt',default='01');p.add_argument('--native-evidence',default=ER+'/windows/native01/result.json');a=p.parse_args()
 if a.action=='go':go(a.native_evidence)
 elif a.action in ['preflight','update','validate']:operate(a.action)
 elif a.action in ['package','inspect']:globals()[a.action](a.attempt)
 else:globals()[a.action]()
if __name__=='__main__':main()
