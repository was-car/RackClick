"""Bounded Windows/QA integration; private data never enters public evidence."""
import argparse,hashlib,json,shutil,subprocess,sys,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ER='evidence/s1-20261018/sesenta-tandas-1330-1389';E=ROOT/ER
BASE='4726a8a25a3b70e75267cea234c4a4416cdaa2a6';GIT=ROOT/'.local/git-2.55.0.5/cmd/git.exe'
TARGET='evidence/s1-20261018/sesenta-tandas-1270-1329/CANDIDATA1329-01.json';PIN='38bbae727ffd545436506ab65d1c66525a64bf316e0a9354079cace0aa60c6b6'
MANUALS=['MANUAL-PAQUETE-WINDOWS-S1.md','CONSTRUIR-PAQUETE-WINDOWS-S1.md','OPERAR-DESPLIEGUE-PRIVADO-WINDOWS-S1.md','RECUPERACION-DESPLIEGUE-WINDOWS-S1.md']
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(p.read_bytes())
def save(name,v):
 with (E/name).open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def exact(values):assert values and all(sha(ROOT/p)==h for p,h in values.items())
def init():
 E.mkdir(parents=True,exist_ok=True);assert not (E/'INICIO.json').exists()
 assert subprocess.check_output([str(GIT),'rev-parse','HEAD']).decode().strip()==BASE
 assert not subprocess.check_output([str(GIT),'diff','--name-only']) and not subprocess.check_output([str(GIT),'diff','--cached','--name-only'])
 assert sha(ROOT/TARGET)==PIN;m=read(ROOT/TARGET);assert m['schema']==13 and m['fileCount']==40 and m['totalBytes']==7148383
 sources=read(ROOT/'evidence/s1-20261018/sesenta-tandas-1270-1329/SOURCE-FREEZE-APP.json')['sources'];assert len(sources)==193;exact(sources)
 pointer=ROOT/'.local/qa-rc9/current.json';directory=Path(read(pointer)['directory']);cfg=read(directory/'manual-qa.json')
 assert cfg['bundleSha256']=='32c4301442c88bea9f82d03b9929cb02a6a88e2c2564d2efeea8efbc0709a53b' or cfg['bundleSha256']==read(ROOT/'evidence/s1-20261018/sesenta-tandas-1150-1209/CANDIDATA1209-01.json')['distributions']['frontend']['app.js']
 assert cfg['bundleSha256']!=m['distributions']['frontend']['app.js']
 paths=[p for p in directory.iterdir() if p.is_file()]+[pointer]
 for part in ['server','frontend','versions']:paths.extend(p for p in (directory/part).rglob('*') if p.is_file())
 original=ROOT/'.local/qa-wascar/current.json';paths.append(original);old_directory=Path(read(original)['directory']);paths.extend(p for p in old_directory.iterdir() if p.is_file())
 for block in ['sesenta-tandas-1210-1269','sesenta-tandas-1270-1329']:paths.extend(p for p in (ROOT/'evidence/s1-20261018'/block).rglob('*') if p.is_file())
 paths.extend(ROOT/p for p in sources)
 for part,files in m['distributions'].items():paths.extend(ROOT/m['candidateDirectory']/part/p for p in files)
 operators=subprocess.check_output([str(GIT),'ls-tree','-r','--name-only',BASE,'tools/windows']).decode().splitlines();paths.extend(ROOT/p for p in operators)
 paths.extend(ROOT/p for p in [TARGET,'RackClick-v0.9.0-rc9-Offline.html','tools/package_offline_bundle.py','development/toolchain.lock.json','development/offline-bundle.sources.json','GUIA-QA-WASCAR.html','GUIA-QA-RESTAURADO.html','docs/QA-CASOS-WASCAR.json']+['docs/'+n for n in MANUALS])
 guards={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(paths))}
 sys.path.insert(0,str(ROOT/'development/server/tests'));from pg_support import protect_directory
 archive=ROOT/'.local'/('source-runtime1389-'+uuid.uuid4().hex);archive.mkdir();protect_directory(archive);runtime={}
 for name in ['postgres.log','manual-control.log','manual-server.log','pg_ctl.log','preview-manual-qa.json','stop.request','server.lock']:
  p=directory/name
  if p.is_file():
   target=archive/name;shutil.copy2(p,target);assert sha(p)==sha(target);runtime[p.relative_to(ROOT).as_posix()]=dict(sha256=sha(p),bytes=p.stat().st_size,privateArchive=target.relative_to(ROOT).as_posix())
 shutil.copy2(directory/'manual-qa.json',archive/'original-manual-qa.json')
 mutable=['tools/package_offline_bundle.py','tools/windows/Test-ServerDistribution.ps1','tools/windows/RackClick.OfflineBundle.ps1','tools/windows/qa_guide.py','GUIA-QA-WASCAR.html','GUIA-QA-RESTAURADO.html','docs/QA-CASOS-WASCAR.json',directory.relative_to(ROOT).as_posix()+'/manual-qa.json']+['docs/'+n for n in MANUALS]
 save('INICIO.json',dict(utc=datetime.now(timezone.utc).isoformat(),baseCommit=BASE,guards=guards,sourceQaGuards={p.relative_to(ROOT).as_posix():sha(p) for p in directory.iterdir() if p.is_file()},authorizedMutableGuards=mutable,sourceDirectory=directory.relative_to(ROOT).as_posix(),sourceRevision=1209,sourceSchema=13,sourceRecoveryRevision=969,sourceRecoverySchema=12,targetManifest=TARGET,targetManifestSha256=PIN,originalConfigurationArchive=(archive/'original-manual-qa.json').relative_to(ROOT).as_posix(),authorizedMutableRuntimeFiles=runtime,progress=78,applicationBuilds=0,frontendBuilds=0,actualQaStartedAtInit=False))
 save('SOURCE-FREEZE-APP.json',dict(sources=sources,sourceCount=193,changedExistingSources=[],newSources=[],serverSourcesUnchanged=True));print(json.dumps(dict(guards=len(guards),productSources=193,runtimeArchived=len(runtime),targetRevision=1329,progress=78)))
def manuals():
 assert not (E/'MANUALES-01.json').exists();changes={};old_manifest='evidence/s1-20261018/sesenta-tandas-1150-1209/CANDIDATA1209-01.json';old_pin='dc79c53fe188187637972c2cad479edd1868d1942414c602de17bb4454bd153b'
 heads={
 'MANUAL-PAQUETE-WINDOWS-S1.md':'**Integración1330–1389 · candidata1329-01/esquema13.** Relaciones de grupos por UUID con Ver grupo de clientes/Ver grupo de usuarios, sin asignaciones.40archivos22+18/7.148.383bytes; servidor1089 exacto. New/Restore usan raíces nuevas; QA13 conserva datos y recuperación969/12. Instalación definitiva y adopción pendientes.',
 'CONSTRUIR-PAQUETE-WINDOWS-S1.md':'**Integración1330–1389.** Once perfiles cerrados:337/397/532 de9,592 de10,712/832/849 de11,969 de12 y1089/1209/1329 de13. Candidata1329 exacta, cero compilaciones.25operadores/cuatro manuales/productor congelados antes de dosZIP idénticos; versiones y pines anteriores intactos.',
 'OPERAR-DESPLIEGUE-PRIVADO-WINDOWS-S1.md':'**Aplicación1329/esquema13, servidor1089 exacto.** Navegación entre relaciones por UUID sin guardar ni conceder acceso. QA13 se actualiza en artefactos conservando la misma base39tablas/recuperación96912 de37tablas, cuentas, sesiones y puntero. Sólo artifactDirectory+bundleSha256; cadena1209→1329 sellada, sin migrar.',
 'RECUPERACION-DESPLIEGUE-WINDOWS-S1.md':'**Compatibilidad1329/esquema13.** Restore administrativo crea raíz/base/roles/TLS/admin nuevos, revoca sesiones copiadas y conserva propietarios originales. ActualizaciónQA1389 sólo de interfaz en misma raíz13/recuperación12; retorno dentro de la operación fallida sujeto a inputs/quietud/actividad, nunca rollback tardío. Recuperación integral y adopción pendientes.'}
 addition='''

## Relaciones por UUID1329 y operación1330–1389

Candidata1329-01: SHA25638bbae727ffd545436506ab65d1c66525a64bf316e0a9354079cace0aa60c6b6,40archivos/22+18/7.148.383bytes/esquema13. Sólo app.js difiere de1209; servidor1089/SQL001–013/CSS/dependencias exactos. Las integraciones anteriores se conservan como antecedentes, no describen la selección nueva.

Para comprobar la interfaz: ejecuta INICIAR-QA-RESTAURADO.cmd y usa la guía y credenciales privadas que abre. Elige Español arriba a la derecha y espera el guardado del idioma. En la barra izquierda pulsa Usuarios, cerca de la parte inferior. Debajo de Lista de cuentas abre Grupos y permisos. Dentro busca Relaciones de grupos · solo lectura, encima de Crear grupo; no hay un botón Relaciones de grupos en Secciones de administración.

En Tipo de grupo elige Grupos de usuarios y en Grupo seleccionado contrasta el UUID completo. Dentro de Permisos asignados, una concesión explícita sobre un grupo de clientes ofrece Ver grupo de clientes. Ese botón abre exactamente su UUID y lleva el foco al selector persistente. Desde la ficha de clientes, Ver grupo de usuarios vuelve a su origen exacto. Nombres iguales no implican identidad; pertenencias múltiples se conservan. Las concesiones globales y directas a un cliente no se convierten en grupos. Navegar no guarda, asigna miembros o permisos ni cambia el usuario común o los borradores.

La ayuda de Crear grupo dirige a editores de membresías y Permisos de grupos de usuarios, que sí requieren acciones explícitas y confirmación del servidor. Actualizar grupos retira datos obsoletos o denegados. EN/DE/ES mantienen nombres literales; usa desplazamiento en ventana estrecha. La prueba de voz requiere tu lector habitual: si no está disponible, registra Bloqueado para esa parte. Los casos QA88–90 sólo están habilitados cuando la guía confirma la distribución1329 seleccionada y sus cuentas/configuración revisadas. No cambies resultados anteriores por disponer de código nuevo.

QA1389 conserva principal13(39tablas), recuperación969/12(37), OIDs/cuentas/sesiones/grants/secretos y puntero. Se añade una versión1329, con configuración previous/preview/selected y registro/sello privados; sólo artifactDirectory y bundleSha256 cambian en manual-qa.json. El preparado1149 y overlay1209/1269 permanecen byteexactos, sin reescribir historia. La validación de la cadena excluye únicamente el descendiente identificado; una versión ajena o un sello alterado impide continuar. No copiar/migrar bases ni ejecutar bootstrap/recover-admin/login/DML de aplicación en el QA real.

Capturar baseline actual una sola vez, no la foto histórica de creación. Preview/readiness13, parada confirmada, selección atómica, GET/readiness13, parada y comparación de ambas bases/historias/permisos/actividad. Un cambio incluso compensado o una duda bloquea retorno y mantiene recovery_required; no renovar baseline ni ofrecer rollback tardío. Si existen sesiones o procesos ajenos, conservarlos y no forzar parada. Archivos runtime originales archivados privadamente; no se promete igualdad de archivos físicos PostgreSQL tras arrancar.

New/Restore de Windows se comprueban en fixtures nuevas con runtime sinSDK y secretos propios. El transporte app.js y las pruebasAPI no son una nueva ejecuciónDOM/voz/Office ni instalación limpia en otroWindows/SCM/PKI productiva. Licencias/redistribución, recuperación integral e instalación final y QA/adopción de Wascar siguen pendientes. Sin descargas ni cambios de versiones durante esta integración.
'''
 for name,heading in heads.items():
  p=ROOT/'docs'/name;raw=p.read_bytes();text=raw.decode('utf-8').replace('\r\n','\n');start=text.index('**');end=text.index('\n\n',start);text=text[:start]+heading+text[end:]
  if name.startswith('CONSTRUIR-'):
   text=text.replace('estos diez perfiles','estos once perfiles');anchor='\n\nEl productor exige el hash externo';assert anchor in text
   text=text.replace(anchor,'\n| [1329/relaciones UUID](../'+TARGET+') |13 /22+18|7.148.383|`'+PIN+'`|'+anchor,1)
   text=text.replace('--manifest '+old_manifest,'--manifest '+TARGET).replace('--expected-manifest-sha '+old_pin,'--expected-manifest-sha '+PIN).replace('--evidence evidence/s1-20261018/sesenta-tandas-1210-1269/packaging/NOMBRE-NUEVO','--evidence '+ER+'/packaging/NOMBRE-NUEVO')
  p.write_bytes((text+addition).replace('\n','\r\n' if b'\r\n' in raw else '\n').encode('utf-8'));changes['docs/'+name]=dict(before=hashlib.sha256(raw).hexdigest(),after=sha(p))
 save('MANUALES-01.json',dict(files=changes,scope='Four current manuals updated before packaging; historical reports preserved.'))
 versions={}
 for row in read(ROOT/'development/toolchain.lock.json')['components']:
  command=[str(ROOT/'.local'/row['installDirectory']/row['executable']),'--version'];r=subprocess.run(command,capture_output=True,check=True);versions[row['id']]=dict(command=command,stdout=r.stdout.decode('utf-8').strip(),exitCode=r.returncode)
 import platform
 save('ENTORNO.json',dict(utc=datetime.now(timezone.utc).isoformat(),windows=platform.platform(),python=platform.python_version(),versions=versions,downloads=0,installedDependencies=0,versionChanges=0));print(json.dumps(dict(manuals=4,versionsVerified=len(versions),builds=0)))
def package(attempt='01'):
 import importlib.util
 assert len(attempt)==2 and attempt.isdecimal() and not (E/('PACKAGES-'+attempt+'.json')).exists();spec=importlib.util.spec_from_file_location('builder1389',ROOT/'tools/package_offline_bundle.py');builder=importlib.util.module_from_spec(spec);sys.modules[spec.name]=builder;spec.loader.exec_module(builder)
 assert builder.application_schema(PIN)==13;exact(read(E/'SOURCE-FREEZE-APP.json')['sources']);assert sha(ROOT/TARGET)==PIN
 paths=[ROOT/'tools/windows'/n for n in builder.OPERATORS]+[ROOT/'docs'/n for n in MANUALS]+[ROOT/p for p in ['tools/package_offline_bundle.py','development/toolchain.lock.json','development/offline-bundle.sources.json']]
 frozen={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(paths))}
 freeze_name='SOURCE-FREEZE-PACKAGE.json' if attempt in ['01','02'] else 'SOURCE-FREEZE-PACKAGE-'+attempt+'.json'
 if (E/freeze_name).exists():assert read(E/freeze_name)['sources']==frozen
 else:save(freeze_name,dict(sources=frozen,scope='Packaged25operators/fourmanuals/producer/locks; coordinator not bundled.'))
 (E/'packaging').mkdir(exist_ok=True)
 outputs=[];tag=uuid.uuid4().hex
 for suffix in ['a','b']:
  target=ROOT/'.local'/('offline1389-'+tag+'-'+suffix+'.zip');report_dir=E/'packaging'/('build'+attempt+'-'+suffix)
  r=builder.build(ROOT/TARGET,PIN,ROOT/'.local/downloads/dotnet-sdk-10.0.401-win-x64.zip',ROOT/'.local/downloads/postgresql-17.11-4-windows-x64-binaries.zip',ROOT/'development/offline-bundle.sources.json',target,report_dir);assert r['valid'];outputs.append(dict(path=target.relative_to(ROOT).as_posix(),bytes=target.stat().st_size,sha256=sha(target),report=report_dir.relative_to(ROOT).as_posix()+'/REPORT.json'))
 exact(frozen);assert outputs[0]['bytes']==outputs[1]['bytes'] and outputs[0]['sha256']==outputs[1]['sha256'];save('PACKAGES-'+attempt+'.json',dict(valid=True,sourceManifestSha256=PIN,sourceCount=len(frozen),sourceFreeze=ER+'/'+freeze_name,sourceFreezeSha256=sha(E/freeze_name),sourcesUnchanged=True,byteIdentical=True,outputs=outputs,newAppBuildsDuringPackaging=0,newFrontendBuildsDuringPackaging=0,qaSelectedAtPackaging=False));print(json.dumps(dict(valid=True,identical=True,outputs=outputs)))
def manuals_fix():
 saved=E/'manuals-before02';saved.mkdir(exist_ok=False);changes={}
 sentence='Si una operación1389 termina en rolled_back confirmado y con sus procesos detenidos, sólo se admite reintentar el mismo --operation explícito: registro, sello, baseline, puntero y parent1209 exactos y sin actividad intermedia. No descubrir otra operación ni recapturar el baseline; cualquier interferencia bloquea la reentrada. No es un rollback tardío.'
 for name in MANUALS:
  p=ROOT/'docs'/name;raw=p.read_bytes();(saved/name).write_bytes(raw);text=raw.decode('utf-8').replace('\r\n','\n')
  if name=='MANUAL-PAQUETE-WINDOWS-S1.md':
   old='Interfaz1209-01 con servidor1089-02/esquema13 reutilizados sin compilar en1210–1269.';assert text.count(old)==1;text=text.replace(old,'Interfaz1329-01 con servidor1089-02/esquema13 reutilizados sin compilar en1330–1389.',1)
   text=text.replace('337/397/532/592/712/832/849/969/1089 y sus informes','337/397/532/592/712/832/849/969/1089/1209 y sus informes',1);old='1089 o1209 registrado';assert old in text;text=text.replace(old,'1089,1209 o1329 registrado',1)
  elif name=='OPERAR-DESPLIEGUE-PRIVADO-WINDOWS-S1.md':
   text=text.replace('1089/1209: esquema13','1089/1209/1329: esquema13',1)
   old='[candidata1209 de laboratorio](../evidence/s1-20261018/sesenta-tandas-1150-1209/CANDIDATA1209-01.json) tiene referencia `dc79c53fe188187637972c2cad479edd1868d1942414c602de17bb4454bd153b`';assert text.count(old)==1;text=text.replace(old,'[candidata1329 de laboratorio](../'+TARGET+') tiene referencia `'+PIN+'`',1)
  elif name=='RECUPERACION-DESPLIEGUE-WINDOWS-S1.md':
   for old,new in [('1089,1209 (esquema13)','1089,1209,1329 (esquema13)'),('N=13 para1089/1209','N=13 para1089/1209/1329')]:assert text.count(old)==1;text=text.replace(old,new,1)
  old='## Alta guiada1209 y operación1210–1269';assert text.count(old)==1;text=text.replace(old,'## Antecedente histórico · alta guiada1209 y operación1210–1269',1)
  assert sentence not in text;text+='\n'+sentence+'\n';p.write_bytes(text.replace('\n','\r\n' if b'\r\n' in raw else '\n').encode('utf-8'));changes['docs/'+name]=dict(before=hashlib.sha256(raw).hexdigest(),after=sha(p))
 save('MANUALES-02.json',dict(files=changes,reason='Independent P3: current paragraphs still referred to1209 or omitted1329; fixed only active references, historical section labeled, explicit same-operation reentry clarified.',packages02Retained=True,nativeOnPackage02=False,productOrOperatorChanges=False));print(json.dumps(dict(correctedManuals=4,productChanges=0,nativeExecutions=0)))
def guards():
 initial=read(E/'INICIO.json');mutable=set(initial['authorizedMutableGuards'])|set(initial['authorizedMutableRuntimeFiles']);protected={p:h for p,h in initial['guards'].items() if p not in mutable};exact(protected);exact(read(E/'SOURCE-FREEZE-APP.json')['sources'])
 for p,row in initial['authorizedMutableRuntimeFiles'].items():assert sha(ROOT/row['privateArchive'])==row['sha256'] and initial['guards'][p]==row['sha256']
 assert sha(ROOT/initial['originalConfigurationArchive'])==initial['guards'][initial['sourceDirectory']+'/manual-qa.json']
 return initial,len(protected)
def preliminary():
 sys.path.insert(0,str(ROOT/'tools/windows'));from qa_artifact13_source1269 import Source13;from qa_artifact13_update1269 import OwnedRuntime
 initial,count=guards();pointer=ROOT/'.local/qa-rc9/current.json';directory=ROOT/initial['sourceDirectory'];s=Source13(directory,pointer,real=True);OwnedRuntime(directory,s.cfg,s.operation).quiet();assert s.revision==1209
 save('REAL-QA-PRELIMINAR-01.json',dict(valid=True,utc=datetime.now(timezone.utc).isoformat(),sourceRevision=1209,directory=initial['sourceDirectory'],sourceConfigSha256=sha(directory/'manual-qa.json'),pointerSha256=sha(pointer),legacyOverlayStaticValidated=True,sourceQuiet=True,postgresqlStarted=False,applicationLogin=False,applicationDml=False,protectedFilesExact=count,manualWascarResultsWritten=False));print(json.dumps(dict(valid=True,sourceRevision=1209,sourceQuiet=True,postgresqlStarted=False)))
def inspect(attempt='02'):
 import os,time
 assert not (E/('ZIP'+attempt+'-CLI.json')).exists();package=read(E/('PACKAGES-'+attempt+'.json'));exact(read(ROOT/package.get('sourceFreeze',ER+'/SOURCE-FREEZE-PACKAGE.json'))['sources']);p=package['outputs'][0]
 assert package['byteIdentical'] and all(sha(ROOT/x['path'])==x['sha256']==p['sha256'] for x in package['outputs'])
 command=[str(Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'),'-NoLogo','-NoProfile','-NonInteractive','-File',str(ROOT/'tools/windows/Test-RackClickOfflineBundle.ps1'),'-ArchivePath',str(ROOT/p['path']),'-ExpectedArchiveSha256',p['sha256']]
 start=time.monotonic();r=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=180);report=json.loads(r.stdout);(E/('ZIP'+attempt+'-CLI.stdout')).write_bytes(r.stdout);(E/('ZIP'+attempt+'-CLI.stderr')).write_bytes(r.stderr)
 valid=r.returncode==0 and not r.stderr and report['valid'] and report['code']=='bundle_verified' and report['bundleArchiveSha256']==p['sha256'] and report['versions']['schema']==13
 save('ZIP'+attempt+'-CLI.json',dict(successful=valid,command=command,exitCode=r.returncode,seconds=round(time.monotonic()-start,3),report=report,newInstallation=False,newRestore=False));assert valid;print(json.dumps(dict(successful=True,archiveSha256=p['sha256'],schema=13,installed=False)))
def operate(action):
 sys.path.insert(0,str(ROOT/'tools/windows'));from qa_artifact13_source1389 import Source1209;from qa_artifact13_update1389 import OwnedRuntime,update_operation,validate_operation
 output='REAL-QA-'+action.upper()+'-01.json';assert not (E/output).exists();initial,count=guards();pointer=ROOT/'.local/qa-rc9/current.json';directory=ROOT/initial['sourceDirectory']
 row=dict(utc=datetime.now(timezone.utc).isoformat(),action=action,valid=False,directory=initial['sourceDirectory'],schema=13,recoverySchema=12,databaseReconstructed=False,schemaMigrationExecuted=False,applicationLogin=False,applicationDml=False,manualWascarResultsWritten=False)
 try:
  if action=='preflight':
   source=Source1209(directory,pointer,real=True);OwnedRuntime(directory,source.cfg).quiet();assert source.revision==1209
   preliminary=read(E/'REAL-QA-PRELIMINAR-01.json');assert sha(pointer)==preliminary['pointerSha256'] and sha(directory/'manual-qa.json')==preliminary['sourceConfigSha256']
   row.update(valid=True,sourceRevision=1209,sourceConfigSha256=sha(directory/'manual-qa.json'),pointerSha256=sha(pointer),sourceInputHashes=source.hashes,sourceQuiet=True,postgresqlStarted=False)
  else:
   go=read(E/'COORDINATOR-GO.json');assert go['valid'] and go['authorizedRealQaArtifactUpdate'];exact(go['gates']);pre=read(E/'REAL-QA-PREFLIGHT-01.json');assert sha(pointer)==pre['pointerSha256'];row['goSha256']=sha(E/'COORDINATOR-GO.json')
   if action=='update':
    source=Source1209(directory,pointer,real=True);OwnedRuntime(directory,source.cfg).quiet();assert source.revision==1209 and source.hashes==pre['sourceInputHashes'] and sha(directory/'manual-qa.json')==pre['sourceConfigSha256']
    result=update_operation(directory,pointer,real=True);state=read(result.journal);assert result.state=='committed'
    row.update(valid=True,state=result.state,selectedRevision=1329,serverRevision=1089,operationDirectory=result.operation.relative_to(ROOT).as_posix(),journalSha256=sha(result.journal),leftRunning=state['leftRunning'],pointerSha256=sha(pointer),idempotent=result.idempotent,databaseTestExecuted=True)
   elif action=='validate':
    source=validate_operation(directory,pointer,real=True);assert source.revision==1329;OwnedRuntime(directory,source.cfg,source.operation).quiet()
    old=read(ROOT/initial['originalConfigurationArchive']);current=read(directory/'manual-qa.json');changed=sorted(k for k in set(old)|set(current) if old.get(k)!=current.get(k));assert changed==['artifactDirectory','bundleSha256']
    states=source.record['databaseStates'];assert len(states['databases']['primary']['snapshot'])==39 and len(states['databases']['recovery969']['snapshot'])==37
    row.update(valid=True,state='static_validated',selectedRevision=1329,serverRevision=1089,databaseTestExecuted=False,operationDirectory=source.operation.relative_to(ROOT).as_posix(),currentConfigSha256=sha(directory/'manual-qa.json'),pointerSha256=sha(pointer),changedConfigFields=changed,leftRunning=False,primaryTables=39,recoveryTables=37,baselineRenewed=False)
   else:raise ValueError('unknown action')
 except Exception as error:row['errorCode']=getattr(error,'code',type(error).__name__);raise
 finally:save(output,row);print(json.dumps({k:v for k,v in row.items() if k!='sourceInputHashes'}))
def authorize(native_attempt='01'):
 assert not (E/'COORDINATOR-GO.json').exists();initial,count=guards();gate=read(E/'revision/GATE-TECNICO.json');assert gate['approved'] and not gate['finalAdoption']
 for key in ['sourceHashes','artifactHashes','reviewSourceHashes']:
  if key in gate:exact(gate[key])
 package=read(E/'PACKAGES-03.json');assert package['valid'] and package['byteIdentical'];exact(read(ROOT/package['sourceFreeze'])['sources'])
 assert len(native_attempt)==2 and native_attempt.isdecimal();native_path='windows/native'+native_attempt+'/result.json'
 native=read(E/native_path);assert native['successful'] and native['inputsUnchanged'] and native['ownedProcessesStopped'] and native['recoverySnapshotExact'] and native['systemCrtDllsAndX64RegistryUnchanged'] and native['applicationManifestSha256']==PIN and native['archiveSha256']==package['outputs'][0]['sha256'] and len(native['tableDigestsBeforeBackup'])==39
 assert read(E/'windows/profiles01/result.json')['successful'] and read(E/'ZIP03-CLI.json')['successful'] and read(E/'qa-update/RESUMEN-AUTOR.json')['successful'] and read(E/'REAL-QA-PREFLIGHT-01.json')['valid']
 sys.path.insert(0,str(ROOT/'tools/windows'));from qa_artifact13_source1389 import Source1209;from qa_artifact13_update1389 import OwnedRuntime
 pointer=ROOT/'.local/qa-rc9/current.json';directory=ROOT/initial['sourceDirectory'];pre=read(E/'REAL-QA-PREFLIGHT-01.json');source=Source1209(directory,pointer,real=True);OwnedRuntime(directory,source.cfg).quiet()
 assert source.revision==1209 and source.hashes==pre['sourceInputHashes'] and sha(pointer)==pre['pointerSha256'] and sha(directory/'manual-qa.json')==pre['sourceConfigSha256']
 paths=['revision/GATE-TECNICO.json','windows/profiles01/result.json',native_path,'PACKAGES-03.json','ZIP03-CLI.json','qa-update/RESUMEN-AUTOR.json','REAL-QA-PREFLIGHT-01.json','SOURCE-FREEZE-APP.json','SOURCE-FREEZE-PACKAGE-03.json']
 gates={ER+'/'+p:sha(E/p) for p in paths};gates[TARGET]=sha(ROOT/TARGET);gates['tools/tests/integration1389.py']=sha(Path(__file__))
 for p in ['tools/windows/qa_artifact13_source1389.py','tools/windows/qa_artifact13_update1389.py']:gates[p]=sha(ROOT/p)
 save('COORDINATOR-GO.json',dict(valid=True,utc=datetime.now(timezone.utc).isoformat(),authorizedRealQaArtifactUpdate=True,sourceRevision=1209,targetRevision=1329,schema=13,sourceRecoverySchema=12,sourceQuiet=True,protectedFilesExact=count,nativeEvidence=ER+'/'+native_path,gates=gates,applicationLogin=False,applicationDml=False,finalAdoption=False));print(json.dumps(dict(valid=True,gateCount=len(gates),targetRevision=1329,adoption=False)))
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['init','manuals','manuals_fix','package','preliminary','inspect','preflight','update','validate','authorize']);p.add_argument('--attempt',default='01');a=p.parse_args()
 if a.action in ['package','inspect']:globals()[a.action](a.attempt)
 elif a.action=='authorize':authorize(a.attempt)
 elif a.action in ['preflight','update','validate']:operate(a.action)
 else:globals()[a.action]()
if __name__=='__main__':main()
