"""Reviewed integration1449 closure; readonly verification never starts PostgreSQL."""
import argparse,json,subprocess
from pathlib import Path
from integration1509 import ROOT,E,ER,BASE,GIT,TARGET,PIN,MANUALS,sha,save,read,exact,guards

def write(path,text):
 p=ROOT/path;raw=p.read_bytes() if p.exists() else b'';nl='\r\n' if b'\r\n' in raw else '\n';p.write_bytes(text.replace('\r\n','\n').replace('\n',nl).encode('utf-8'))


def prepend(path,text):
 p=ROOT/path;old=p.read_text(encoding='utf-8');assert 'Bloque1450–1509' not in old[:400];heading,body=old.split('\n',1);write(path,heading+'\n\n'+text+'\n\n'+body.lstrip('\n'))


def verify():
 initial,count=guards();m=read(ROOT/TARGET);assert sha(ROOT/TARGET)==PIN
 for part,files in m['distributions'].items():assert {p.relative_to(ROOT/m['candidateDirectory']/part).as_posix():sha(p) for p in (ROOT/m['candidateDirectory']/part).rglob('*') if p.is_file()}==files
 go=read(E/'COORDINATOR-GO.json');assert go['valid'];exact(go['gates']);native=read(ROOT/go['nativeEvidence']);assert native['successful'] and native['inputsUnchanged'] and native['ownedProcessesStopped'] and native['recoverySnapshotExact'] and native['systemCrtDllsAndX64RegistryUnchanged'] and len(native['tableDigestsBeforeBackup'])==39
 package=read(E/'PACKAGES-01.json');exact(read(ROOT/package['sourceFreeze'])['sources']);assert package['byteIdentical'] and native['archiveSha256']==package['outputs'][0]['sha256'];assert all(sha(ROOT/p['path'])==p['sha256']==native['archiveSha256'] for p in package['outputs'])
 update=read(E/'REAL-QA-UPDATE-01.json');validated=read(E/'REAL-QA-VALIDATE-01.json');assert update['valid'] and update['state']=='committed' and validated['valid'] and validated['selectedRevision']==1449 and validated['changedConfigFields']==['artifactDirectory','bundleSha256']
 pointer=ROOT/'.local/qa-rc9/current.json';assert sha(pointer)==initial['guards'][pointer.relative_to(ROOT).as_posix()];directory=ROOT/initial['sourceDirectory'];cfg=read(directory/'manual-qa.json');old=read(ROOT/initial['originalConfigurationArchive']);assert sorted(k for k in set(old)|set(cfg) if old.get(k)!=cfg.get(k))==['artifactDirectory','bundleSha256']
 assert cfg['bundleSha256']==m['distributions']['frontend']['app.js'] and cfg['dllSha256']==m['distributions']['server']['RackClick.Server.dll']
 for part,files in m['distributions'].items():assert {p.relative_to(Path(cfg['artifactDirectory'])/part).as_posix():sha(p) for p in (Path(cfg['artifactDirectory'])/part).rglob('*') if p.is_file()}==files
 import sys
 sys.path.insert(0,str(ROOT/'tools/windows'));from qa_artifact13_update1509 import validate_operation,OwnedRuntime
 source=validate_operation(directory,pointer,real=True);OwnedRuntime(directory,source.cfg,source.operation).quiet();assert source.revision==1449 and len(source.record['databaseStates']['databases']['primary']['snapshot'])==39 and len(source.record['databaseStates']['databases']['recovery969']['snapshot'])==37
 from qa_integration1509 import load
 guide=load('guide1509verify','tools/windows/qa_guide.py');catalog=read(ROOT/'docs/QA-CASOS-WASCAR.json');before=read(E/'qa-guide/source-before/QA-CASOS-WASCAR.json');assert len(catalog['cases'])==93 and catalog['cases'][:90]==before['cases'][:90]
 counts={}
 for profile,n in [('manual',8),('rc9',93)]:
  assert guide.generate(check=True,profile=profile);cs=json.loads(guide.render(catalog,guide.context(profile=profile)).split('const guide=',1)[1].split(';',1)[0])['cases'];assert sum(c['available'] for c in cs.values())==n;counts[profile]=n
 plan=read(ROOT/'docs/PLAN-SESENTA-TANDAS-1450-1509.json');assert len(plan['batches'])==plan['completed']==plan['total']==60 and [b['id'] for b in plan['batches']]==list(range(1450,1510)) and all((ROOT/b['evidence']).is_file() for b in plan['batches'])
 progress=read(ROOT/'docs/MAPA-ENTREGA.json');assert progress['progress']==78 and [s['points'] for s in progress['streams']]==[18,22,14,14,9,1] and [s['weight'] for s in progress['streams']]==[20,25,15,15,15,10]
 changes={p:('absent' if not (ROOT/p).exists() else sha(ROOT/p)) for p,row in initial['authorizedMutableRuntimeFiles'].items() if not (ROOT/p).exists() or sha(ROOT/p)!=row['sha256']}
 result=dict(successful=True,protectedFilesExact=count,immutableQaRootFilesExact=len(initial['sourceQaGuards'])-8,originalRuntimeFilesPrivatelyArchived=7,allowedRuntimeChanges=changes,productSourcesExact=195,candidateFilesExact=40,selectedQaFrontendRevision=1449,selectedServerRevision=1089,selectedQaSchema=13,recoveryRevision=969,recoverySchema=12,realQaPrimaryTables=39,realQaRecoveryTables=37,pointerUnchanged=True,configChangedFields=['artifactDirectory','bundleSha256'],available=counts,previous90CasesExact=True,manualWascarResultsWritten=False,newApplicationPublications=0,newFrontendBuilds=0,processesQuiet=True,independentGateApproved=True,verificationStartedPostgresql=False,finalAdoption=False,progress=78)
 if (E/'VERIFICACION.json').exists():assert read(E/'VERIFICACION.json')==result
 else:save('VERIFICACION.json',result)
 print(json.dumps(result))

def close():
 assert not (E/'CIERRE.md').exists();go=read(E/'COORDINATOR-GO.json');native=read(ROOT/go['nativeEvidence']);package=read(E/'PACKAGES-01.json');actual=read(E/'REAL-QA-UPDATE-01.json');q=read(E/'QA-TESTS-01.json');author=read(E/'qa-update/RESUMEN-AUTOR.json');assert native['successful'] and actual['valid'] and q['successful'] and author['successful'] and read(E/'revision/GATE-TECNICO.json')['approved']
 native_path=go['nativeEvidence'][len(ER)+1:];groups=[
 ('INICIO.json','Registrar Git limpio y commit7d77210|Proteger informes1390–1449 y anteriores|Congelar195fuentes originales|Fijar1158guardas iniciales|Archivar7runtime y configuración privados|ConservarRC9offlineadoptado sin modificar'),
 ('MANUALES-01.json','Actualizar cuatro manuales vigentes|Conservar secciones y reportes históricos|Precisar ubicación y botones QA91–93'),
 ('ENTORNO.json','Verificar herramientas fijadas sin descargas/builds'),
 ('SOURCE-FREEZE-APP.json','Conservar servidorSQLCSSdependencias sin recompilar'),
 ('windows/profiles01/result.json','Conservar once perfiles anteriores|Registrar duodécimo perfil1449 por pin exacto|Verificar sintaxisPowerShell5.1 y rechazo de pines ajenos'),
 ('SOURCE-FREEZE-PACKAGE-01.json','Congelar25operadores/cuatro manuales/productor/locks'),
 ('revision/PREPAQUETE.json','Revisar manuales/productores antes de empaquetar'),
 ('revision/REVISION-ARNES-WINDOWS.json','Revisar escenario nativo antes de su ejecución'),
 ('PACKAGES-01.json','Construir dosZIP byteidénticos'),
 ('ZIP01-CLI.json','Ejecutar lector público delZIP final'),
 (native_path,'InstalarNew en raíz/base nueva|ArrancarHTTPS con runtime sinSDK|Servir app.js1449 exacto|Comprobar cuatro recibos/UUID en ambos tipos|Conservar Unicode/nombres homónimos|Consultar/repetir operación original sin duplicar grupo|No asignar miembros/permisos por crear grupo|Denegar alLector lectura/estado/alta|Comparar ocho tablas durante lecturas/replays|Respaldar39tablas por operadores públicos|Restaurar con admin/roles/TLS/secretos nuevos|Revocar sesiones copiadas y preservar propietarios|Reiniciar y comparar recuperación administrativa|Detener procesos propios/preservarCRT y entradas'),
 ('REAL-QA-PRELIMINAR-01.json','Validar pasivamente fuente1329 quieta'),
 ('REAL-QA-PREFLIGHT-01.json','Revalidar nueva claseSource1329 sin arrancarPG'),
 ('qa-update/RESUMEN-AUTOR.json','Cerrar transición1329→1449|Validar cadena genuina1149→1209→1329|Preservar sellos/baselines de ancestros|Rechazar entradas/carpetas descendientes ajenos|Vincular puntero y configuración exacta de dos campos|Capturar baseline actual de39+37tablas una vez|Probar retorno durante fallo quieto|Reentrar misma operación explícita sin recapturar baseline|Probar commit e idempotencia sin rollback tardío|Detectar actividad compensada y preservar selección'),
 ('revision/fault01/result.json','Ejecutar foco propio de revisión con procedencia declarada'),
 ('revision/GATE-TECNICO.json','Cerrar revisión técnica antes de operación real'),
 ('COORDINATOR-GO.json','Revalidar quietud vigente y emitirGO por hashes'),
 ('REAL-QA-UPDATE-01.json','Seleccionar interfaz1449 en mismo laboratorioQA'),
 ('REAL-QA-VALIDATE-01.json','Validar dos campos y conservar principal/recuperación/puntero'),
 ('QA-MATRIX-1509.json','Habilitar únicamenteQA91–93 tras selección|Conservar90casos y pasos restantes de los3nuevos|Heredar parejas revisadas sin retirar anteriores|Preservar lógica y resultados de Wascar'),
 ('QA-TESTS-01.json','Ejecutar una regresión pertinente de guía|Regenerar ambas guías y comprobar93restaurado/8original'),
 ('CIERRE.md','Actualizar continuidad/CHANGELOG/mapa con resultado real|Conservar78puntos y pesos sin incremento por hitos|Documentar pruebas nuevas y límites históricos|Preparar diffJSON/sello/commit local sin publicación')]
 rows=[]
 for proof,titles in groups:
  if not titles:continue
  start=1450+len(rows);rows.extend([dict(id=start+i,title=t,status='verified',evidence=ER+'/'+proof) for i,t in enumerate(titles.split('|'))])
 assert len(rows)==60,len(rows)
 report=f'''# Bloque1450–1509 · alta de grupos integrada en Windows y QA

**QA91–93 disponibles** en INICIAR-QA-RESTAURADO.cmd, con guía y cuentas privadas existentes. Desde Todos los clientes elige Español arriba a la derecha y espera guardado. Barra izquierda→Usuarios→debajo de Lista de cuentas, Grupos y permisos→Crear grupo. Elige Grupo de usuarios/Grupo de clientes, escribe nombre y pulsa Crear grupo. La tarjeta Grupo creado muestra nombre/tipo/UUID confirmado; Abrir relaciones abre su ficha exacta sin conceder acceso. Los botones de recuperación son Consultar resultado del grupo, Reintentar alta original y Cancelar alta de grupo pendiente. Salir de Administración/recargar retira sólo el recibo temporal. Guía:93restaurado/8original;90guiones completos y resultados de Wascar intactos. Voz sin lector habitual queda Bloqueada.

Sesenta hitos internos de una integración completa, no60funciones/suites. Avance global aproximado **78 %**, sin incremento por repetir pruebas o empaquetar. Los pesos20/25/15/15/15/10 y puntos18/22/14/14/9/1 no cambian. Adopción final de Wascar pendiente.

## Artefactos y Windows

Candidata1449-01 exacta:195fuentes,40artefactos22+18/7.159.235bytes/esquema13, SHA256{PIN}. Servidor1089/SQL001–013/CSS/dependencias y referenciaRC9 intactos; cero compilaciones/descargas/cambios de versiones. Duodécimo perfil cerrado, once anteriores conservados.

25operadores/cuatro manuales/productor/locks congelados32entradas. DosZIP01 idénticos{package['outputs'][0]['bytes']}bytes, SHA256{package['outputs'][0]['sha256']}; ruta{package['outputs'][0]['path']} y copia-b. Lector públicoZIP01 comprobado; gate previo sobre productores/manuales y arnés antes de nativo.

Autor Windows: perfiles3/3PASS34,531s. Prueba nueva compuesta en {go['nativeEvidence']}, **{native['testsRun']}/1PASS{native['seconds']}s**: New/HTTPS/backup/Restore13 públicos en raíces/clústeres nuevos, runtime sinSDK y secretos propios; recibosAPI por UUID y ambos tipos/Unicode/homónimos/consulta/replay, Lector403, reinicio y comparación39tablas con excepciones administrativas declaradas. Admin/roles/secretos/TLS nuevos en Restore, sesiones copiadas revocadas y propietarios originales preservados. Ocho tablas exactas en etapa de lecturas/replay; CRT/registro del sistema e inputs intactos, procesos propios detenidos. Helpers de lifecycle reutilizados; casos históricos no se reejecutan como nuevos. Transporte app.js/API no acreditan otraGUI/AX/voz/Office, otroWindows, SCM oPKI productiva.

## TransiciónQA y revisión

Nuevos source/update1509 preservan validadores1269/1389, registros y baselines. Cadena genuina1149→1209→1329, nueva etapa1449 identificada/sellada e inventario exacto; ni configuración temporal, glob permisivo o monkeypatch de procedencia en camino real. Baseline actual39+37tablas/historias/OIDs/roles/settings/permisos/watermark capturado una vez. Reentrada sólo operación explícita original tras rolled_back confirmado y quietud/entradas sin interferencia. Actividad incluso compensada o incertidumbre bloquean retorno; sin rollback tardío.

Pruebas nuevas del autor en qa-update/RESUMEN-AUTOR.json: **{author['testsRun']}/5PASS**,4contratos y1PostgreSQL compuesto, suite{author['suiteDurationSeconds']}s/nativo{author['finalNativeDurationSeconds']}s, una ejecución sin fallos de ejecución. Atribución separada: contratos sintéticos declarados; setup histórico genuino reutilizado una vez en5clústeres nuevos, sin ejecutar cuerpos de pruebas anteriores. Fallo after_config inyectado deliberadamente confirma retorno quieto1329 y reanudación de la misma operación hasta1449. Dos guardias directas de actividad compensada; recuperación se prueba acumulativamente después de principal, sin atribuir la marca global a una base ni afirmar rollback nativo independiente por base. Cinco clústeres detenidos y51hashes exactos. Revisión propia:1/1PASS5,578s, validate_parents real acepta cadena sintética1209→1329 y rechaza directorio vacío tardío en1209 con archivos/puntero/config/records/sellos/journals intactos. CeroPG/constructorSource1329/procedencia1149/rollback del revisor. Ver revision/fault01 y gate; la revisión contrasta por lectura los ensayosPG de los autores.

P3 de atribución corregido antes delGO: éste comprobaba hashes del preflight y declaraba quietud; ahora vuelve a construir Source1329 y comprobar OwnedRuntime.quiet/hash actual sin arrancarPG, antes de emitirlo. La actualización vuelve a verificarlo y respeta procesos/sesiones ajenos.

Coordinador: preflight pasivo, gate independiente yGO por hashes antes de operar QA real. Actualización committed→validación estática; misma raíz/clúster/principal13/recuperación96912/cuentas/sesiones/permisos/secretos/puntero, sólo artifactDirectory+bundleSha256. Sin migración/bootstrap/recover-admin/login/DML de aplicación ni copia/borrado de bases existentes. Comparaciones durante operación; no se sellan por hash archivos físicosPG.7runtime anteriores archivados privadamente,1139guardas protegidas intactas y procesos propios detenidos.

## Guía, reproducción y pendientes

Guía **{q['testsRun']}PASS{q['seconds']}s**: sólo feature/primerpaso91–93 cambian;90casos completos y demás pasos/expected exactos. Parejas antiguas conservadas y1449 heredada; generador añade sólo unmapeoASCII, lógica de resultados exacta.3helpers cambian recuento de disponibilidad y expectativa de ese mapeo; versiones anteriores conservadas. Ambas guías regeneradas y comando obligatorio qa_guide.py ejecutado, sin escribir Pass/observaciones de Wascar.

Reproducir paquete en intento libre: C:/Python312/python.exe -B tools/tests/integration1509.py package --attempt NN, seguido de inspect --attempt NN; no sobrescribir01. Nativo exige ZIP/pin/evidencia nueva explícitos. Pruebas de cadena y límites se describen en qa-update/RESUMEN-AUTOR.json y fuentes. C:/Python312/python.exe -B tools/tests/close_integration1509.py verify comprueba hashes/selección/quietud sin iniciarPG. Acciones enable/update/cierre crean registros exclusivos y no deben reaplicarse como otra operación a una selección comprometida; reentrada sólo según el contrato sellado.

Continuidad/plan60/mapa/VERIFICACION/revisión final, diffJSON ySHA256SUMS separan preparación de ejecución del cierre/commit. No publicar ni adoptar. Siguen pendientes inventario/undo/Dosen según contrato, formatos/herramientas/transferencia/accesibilidad/idiomas y cierre administrativo, servicio/identidad/certificadosWindows, Windows limpio/otro equipo, recuperación integral/manualfinal yQA/adopción. El contador de hitos no estima tiempo restante. [Cierre restante por seis frentes](../../../docs/CIERRE-RESTANTE.md) ordena criterios existentes sin añadir alcance ni afirmar otra auditoría. Próximo entregable: servicio/identidadWindows según C4, sin esperar otra autorización de arranque.
'''
 write(ER+'/CIERRE.md',report);write('docs/PLAN-SESENTA-TANDAS-1450-1509.json',json.dumps(dict(scope='60hitos internos de una integración, no60funciones/suites. Últimos hitos preparan cierre/sello/commit, cuya ejecución se comprueba aparte.',initialProgress=78,total=60,completed=60,batches=rows,finalProgress=78,finalAdoption=False),ensure_ascii=False,indent=2)+'\n')
 summary='''**Bloque1450–1509 cerrado ·18.10.2026: alta de grupos1449 integrada en Windows y el mismoQA13; global78 % aproximado sin aumento.** Duodécimo perfil,195fuentes/40artefactos exactos,0builds/descargas/cambios de versiones. DosZIP01 idénticos, New/Restore y cadena1329→1449 probados/revisados. GO revalida quietud antes de seleccionar; preserva raíz/principal13/recuperación96912/cuentas/sesiones/permisos/puntero, sólo2camposconfig.

**QA91–93 disponibles:** INICIAR-QA-RESTAURADO.cmd→Todos los clientes (idioma)→Usuarios→Grupos y permisos→Crear grupo→Grupo creado→Abrir relaciones.93restaurado/8original,90guiones y resultados anteriores intactos. No nuevaGUI/voz/SCM/otroWindows ni adopción. [Contrato](INTEGRACION-ALTA-GRUPOS-WINDOWS-QA-S1.md), [60hitos](PLAN-SESENTA-TANDAS-1450-1509.json), [pruebas/límites](../'''+ER+'''/CIERRE.md). Próximo entregable: servicio/identidadWindows; [seis frentes de cierre](CIERRE-RESTANTE.md) distinguen trabajo y aceptación pendientes. Registros siguientes históricos.'''
 for path in ['docs/CONTINUIDAD-CODEX.md','docs/INICIO-IMPLEMENTACION-S1.md','docs/PROGRESO-GLOBAL.md']:prepend(path,summary)
 short='**Bloque1450–1509 vigente.** Alta de grupos1449 integrada Windows/QA13, servidor1089 exacto; QA91–93disponibles,93restaurado/8original,90guiones/resultados previos intactos. DosZIP01 reproducibles, New/Restore y cadena1329→1449 con revisión independiente. Misma base/recuperación12/cuentas/puntero, sólo2camposconfig;0builds, global78 % estimado, adopción pendiente. [Contrato](INTEGRACION-ALTA-GRUPOS-WINDOWS-QA-S1.md), [pruebas/límites](../'+ER+'/CIERRE.md). Registros siguientes históricos.'
 for path in ['docs/BRIEFING-MAESTRO.md','docs/ACEPTACION.md','docs/ESTADO-ACEPTACION-S1.md','docs/MAPA-RC9-R3.md','docs/UX-ADMINISTRACION-ARBOL.md','docs/QA-COLABORACION-Y-RESTAURACION.md']:prepend(path,short)
 for path in ['development/frontend/README.md','development/server/README.md']:prepend(path,short.replace('(INTEGRACION-','(../../docs/INTEGRACION-').replace('(../evidence/','(../../evidence/'))
 prepend('CHANGELOG.md','## 18.10.2026 · Bloque1450–1509 · Alta de grupos Windows/QA\n\n- Perfil1449 cerrado, dosZIP01 idénticos; New/Restore nativos sobre paquete final,0builds.\n- Transición1329→1449 conserva cadena/baselines y datos; revisión independiente/GO antes de operar. Sólo2camposconfig, misma base/recuperación/puntero/cuentas.\n- QA91–93disponibles:93+8casos,90guiones/resultados conservados.60hitos internos/global78 % sin aumento. [Informe]('+ER+'/CIERRE.md).')
 m=read(ROOT/'docs/MAPA-ENTREGA.json');assert m['progress']==78 and [s['points'] for s in m['streams']]==[18,22,14,14,9,1];m.update(revision='2026-10-18-sesenta1450-1509',snapshot='Alta de grupos1449 integrada Windows/QA13;93casos/93+8disponibles; misma base/recuperación/cuentas/puntero. Global78 % estimado.',currentBatch=dict(count=60,completed=60,ledger='docs/PLAN-SESENTA-TANDAS-1450-1509.json',evidence=ER+'/CIERRE.md'))
 leaf=next(c for s in m['streams'] if s['id']=='admin' for c in s['children'] if c['id']=='group-creation-receipt1449');leaf.update(status='Probado y revisado · integrado Windows/QA13',qa='QA91–93 disponibles restaurado1449',evidence=ER+'/CIERRE.md');m['nextMilestones'][0]='C4 de docs/CIERRE-RESTANTE.md: servicio/identidadWindows e instalador revisable; conciliación acotada de pendientesC1–C3 antes de nuevas funciones.';m['history'].append(dict(id='h1450-1509',name='1450–1509 · Alta de grupos Windows/QA13',status='Probado y revisado',note='60hitos internos,0builds;93+8casos disponibles. Misma principal13/recuperación12/cuentas/puntero;78 % sin aumento.'));write('docs/MAPA-ENTREGA.json',json.dumps(m,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(completed=60,progress=78,available=93)))

def seal():
 verify();review=read(E/'revision/CIERRE-REVISADO.json');assert review['approved'] and not review.get('openBlockingFindings',[]);exact(review['observedFilesSha256'])
 result=subprocess.run([str(GIT),'diff',BASE,'--check'],capture_output=True);assert result.returncode==0,(result.stdout+result.stderr).decode(errors='replace');diff=subprocess.check_output([str(GIT),'diff',BASE,'--binary','--','.',':(exclude)evidence']);save('CAMBIOS.json',dict(baseCommit=BASE,scope='Base-to-current source and documentation diff, including staged new files; evidence is covered separately by this block SHA256SUMS.',sha256=__import__('hashlib').sha256(diff).hexdigest(),bytes=len(diff),utf8=diff.decode('utf-8')))
 rows=[sha(p)+'  '+p.relative_to(E).as_posix() for p in sorted(E.rglob('*')) if p.is_file() and p.name!='SHA256SUMS'];p=E/'SHA256SUMS';assert not p.exists();p.write_text('\n'.join(rows)+'\n',encoding='ascii');print(json.dumps(dict(sealedFiles=len(rows),sha256=sha(p))))
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['close','verify','seal']);a=p.parse_args();globals()[a.action]()
if __name__=='__main__':main()
