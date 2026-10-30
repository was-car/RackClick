"""Bounded relationship-navigation block; never discovers or starts real QA."""
import argparse,hashlib,json,shutil,subprocess,time,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ER='evidence/s1-20261018/sesenta-tandas-1270-1329';E=ROOT/ER
BASE='c6033fa2fec7df58b3a6b83f74f41d37f02c0c3c';GIT=ROOT/'.local/git-2.55.0.5/cmd/git.exe'
TARGET='evidence/s1-20261018/sesenta-tandas-1150-1209/CANDIDATA1209-01.json';PIN='dc79c53fe188187637972c2cad479edd1868d1942414c602de17bb4454bd153b'
MUTABLE=['development/frontend/src/AdminGroupRelations.jsx','development/frontend/src/AdminGroupCreation.jsx']
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(p.read_bytes())
def save(name,data):
 with (E/name).open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n')
def tree(p):return {f.relative_to(p).as_posix():sha(f) for f in sorted(p.rglob('*')) if f.is_file()}
def exact(values):assert values and all(sha(ROOT/p)==h for p,h in values.items())
def initial():return read(E/'INICIO.json')
def init():
 E.mkdir(parents=True,exist_ok=True);assert not (E/'INICIO.json').exists();assert subprocess.check_output([str(GIT),'rev-parse','HEAD'],text=True).strip()==BASE
 assert not subprocess.check_output([str(GIT),'diff','--name-only'],text=True);assert sha(ROOT/TARGET)==PIN
 product=read(ROOT/'evidence/s1-20261018/sesenta-tandas-1210-1269/SOURCE-FREEZE-APP.json')['sources'];assert len(product)==193;exact(product)
 pointer=ROOT/'.local/qa-rc9/current.json';directory=Path(read(pointer)['directory']);paths=[p for p in directory.iterdir() if p.is_file()]+[pointer]
 for part in ['server','frontend','versions']:paths.extend(p for p in (directory/part).rglob('*') if p.is_file())
 for folder in ['sesenta-tandas-1150-1209','sesenta-tandas-1210-1269']:paths.extend(p for p in (ROOT/'evidence/s1-20261018'/folder).rglob('*') if p.is_file())
 for rel in ['RackClick-v0.9.0-rc9-Offline.html','development/toolchain.lock.json','development/server/global.json','development/frontend/package-lock.json',TARGET]:paths.append(ROOT/rel)
 m=read(ROOT/TARGET);paths.extend(ROOT/m['candidateDirectory']/part/n for part,files in m['distributions'].items() for n in files)
 guards={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(paths))}
 save('INICIO.json',dict(utc=datetime.now(timezone.utc).isoformat(),baseCommit=BASE,sourceManifest=TARGET,sourceManifestSha256=PIN,originalProductSources=product,allowedProductChanges=MUTABLE,guards=guards,qaDirectory=directory.relative_to(ROOT).as_posix(),qaFrontend=1209,qaSchema=13,progress=78,realQaAccess=False,maximumPlannedFrontendBuilds=1,serverBuilds=0))
 print(json.dumps(dict(guards=len(guards),productSources=193,realQaAccess=False,progress=78)))
def build():
 assert not (E/'BUILD-01.json').exists();i=initial();exact(i['guards']);exact({p:h for p,h in i['originalProductSources'].items() if p not in MUTABLE});old=read(ROOT/TARGET)
 sources={p:sha(ROOT/p) for p in i['originalProductSources']};assert {p for p,h in sources.items() if h!=i['originalProductSources'][p]}==set(MUTABLE)
 save('SOURCE-FREEZE-APP.json',dict(sources=sources,sourceCount=193,changedExistingSources=MUTABLE,newSources=[],serverSourcesUnchanged=True))
 node=ROOT/'.local/node-v24.21.0-win-x64/node.exe';assert subprocess.check_output([str(node),'--version'],text=True).strip()=='v24.21.0';start=time.monotonic()
 with (E/'frontend-build01.log').open('xb') as f:r=subprocess.run([str(node),'build.mjs'],cwd=ROOT/'development/frontend',stdout=f,stderr=subprocess.STDOUT,timeout=180)
 exact(sources);save('BUILD-01.json',dict(successful=r.returncode==0,exitCode=r.returncode,seconds=round(time.monotonic()-start,3),frontendBuilds=1,serverBuilds=0,dependencyChanges=0,realQaAccess=False));assert r.returncode==0
 dest=ROOT/'.local/candidates'/('relations1329-01-'+uuid.uuid4().hex);shutil.copytree(ROOT/old['candidateDirectory']/'server',dest/'server');shutil.copytree(ROOT/'development/frontend/dist',dest/'frontend')
 distributions={part:tree(dest/part) for part in ['server','frontend']};assert distributions['server']==old['distributions']['server'];assert len(distributions['frontend'])==18 and {p for p,h in distributions['frontend'].items() if h!=old['distributions']['frontend'][p]}=={'app.js'}
 m=dict(utc=datetime.now(timezone.utc).isoformat(),baseCommit=BASE,schema=13,candidateDirectory=dest.relative_to(ROOT).as_posix(),serverDll=(dest/'server/RackClick.Server.dll').relative_to(ROOT).as_posix(),frontend=(dest/'frontend').relative_to(ROOT).as_posix(),sourceManifest=TARGET,sourceManifestSha256=PIN,distributions=distributions,fileCount=40,totalBytes=sum(p.stat().st_size for p in dest.rglob('*') if p.is_file()),selectedInRealQaAtFreeze=False,scope='Complete development distribution only; server1089 and schema13 exact, only app.js changed from1209. QA1209 and Windows1269 unchanged.')
 save('CANDIDATA1329-01.json',m);print(json.dumps(dict(successful=True,manifestSha256=sha(E/'CANDIDATA1329-01.json'),bytes=m['totalBytes'],files=40)))

def write_doc(path,value):
 p=ROOT/path;old=p.read_bytes() if p.exists() else b'';nl='\r\n' if b'\r\n' in old else '\n'
 p.write_bytes(value.replace('\r\n','\n').replace('\n',nl).encode('utf-8'))

def prepend(path,value):
 p=ROOT/path;old=p.read_text(encoding='utf-8');assert 'Bloque1270–1329' not in old[:300]
 heading,body=old.split('\n',1);write_doc(path,heading+'\n\n'+value+'\n\n'+body.lstrip('\n'))

def close():
 assert not (E/'CIERRE.md').exists()
 g=read(E/'gui02/fixture.json');assert g['result']=='PASS' and g['inputsUnchanged'] and g['labStopped'] and g['serversStopped']
 assert read(E/'revision/dom02/result.json')['successful'];assert read(E/'QA-TESTS-01.json')['testsRun']==50
 exact(initial()['guards']);exact(read(E/'SOURCE-FREEZE-APP.json')['sources'])
 save('AMBITO-Y-ENTORNO.json',dict(baseCommit=BASE,platform=g['platform'],postgresql=g['postgresql'],browser=read(E/'gui02/browser.json')['browser'],node='24.21.0',sdk='10.0.401',git='2.55.0.windows.5',python='3.12.3',sources=193,artifactFiles=40,productChanges=MUTABLE,installations=0,downloads=0,fixedVersionChanges=0,serverBuilds=0,applicationFrontendBuilds=1,componentFixtureBuilds=dict(author=1,independent=2),actualQaOperations=0,windowsBundleChanges=0,readOnlyDatabaseComparison='Eight group tables only; login/preferences may write sessions/preferences in the isolated fixture.',initialReading=['docs/CONTINUIDAD-CODEX.md','docs/INICIO-IMPLEMENTACION-S1.md','docs/CONTRATO-SERVIDOR-v0.1.md','docs/MAPA-RC9-R3.md','docs/ACEPTACION.md','docs/BRIEFING-MAESTRO.md','docs/S1-FUNDAMENTO.md','docs/EQUIPO-Y-SKILLS.md','development/server/README.md'],delegation=dict(explorer='admin_next1329: read only',implementer='group_links1329: AdminGroupRelations.jsx only',reviewer='review1089: independent evidence only',coordinator='Help strings, new tests, QA catalogue and closure'),scope='Read-only navigation by group UUID, not AD/inheritance or a change to server authorization.'))
 save('INSPECCION-VISUAL.json',dict(inspectedBy='coordinator',images=['gui02/relations-es-390.png','gui02/relations-de-390.png','gui02/relations-en-390.png'],observed=['RC9 dark layout retained.','Literal HTML-like/Unicode names, full UUID wrapping and focused persistent selector visible.'],limits=['Screenshots capture the upper portion after scrolling; link buttons below the fold are exercised by DOM/keyboard assertions, not visually shown here.','No screen-reader speech or manual Wascar acceptance.']))
 specs=[
 ('Fijar Git limpio y commit base','INICIO.json'),
 ('Consultar continuidad y alcance vigente','AMBITO-Y-ENTORNO.json'),
 ('Proteger informes históricos con531 hashes','INICIO.json'),
 ('Conservar HTML RC9 adoptado','INICIO.json'),
 ('Fijar193 fuentes originales','INICIO.json'),
 ('Proteger QA1209 y recuperación969','INICIO.json'),
 ('Conservar versiones fijadas sin instalaciones','AMBITO-Y-ENTORNO.json'),
 ('Mantener servidor y SQL001–013','SOURCE-FREEZE-APP.json'),
 ('Conservar API/DTO y autorización servidor','AMBITO-Y-ENTORNO.json'),
 ('Definir navegación por UUID de snapshot','frontend/IMPLEMENTACION.md'),
 ('Delimitar relaciones sin herencia ni AD','frontend/IMPLEMENTACION.md'),
 ('Separar implementación y revisión','AMBITO-Y-ENTORNO.json'),
 ('Enlazar concesión explícita a grupo de clientes','frontend/CAMBIO-01.diff'),
 ('Elegir destino entre homónimos por UUID','gui02/browser.json'),
 ('Excluir concesiones globales y directas','gui02/browser.json'),
 ('Volver al grupo de usuarios origen','gui02/browser.json'),
 ('Conservar múltiples padres y pertenencias','gui02/browser.json'),
 ('Usar sólo destinos del snapshot actual','revision/dom02/result.json'),
 ('Impedir fallback por nombre ante destino ausente','revision/dom02/result.json'),
 ('Enfocar selector estable tras enlace','gui02/browser.json'),
 ('Conservar nodo de estado polite/atomic','gui02/browser.json'),
 ('Limpiar selección cuando desaparecen datos','revision/dom02/result.json'),
 ('No resucitar selección al restaurar datos','revision/dom02/result.json'),
 ('Conservar borrador y usuario común','gui02/browser.json'),
 ('Mostrar nombres HTML-like y Unicode literales','gui02/browser.json'),
 ('Traducir botones EN/DE/ES','gui02/browser.json'),
 ('Corregir ayuda obsoleta de Crear grupo','AYUDA-P3-PREBUILD.json'),
 ('Resolver P3 de título real antes de compilar','AYUDA-P3-PREBUILD.json'),
 ('Ejecutar regresión de estado848 en componente','frontend/status01/result.json'),
 ('Congelar193 fuentes con sólo dos cambios','SOURCE-FREEZE-APP.json'),
 ('Compilar aplicación frontend una vez','BUILD-01.json'),
 ('Congelar candidata completa de40 archivos','CANDIDATA1329-01.json'),
 ('Conservar22 artefactos servidor exactos','CANDIDATA1329-01.json'),
 ('Limitar diferencia compilada a app.js','CANDIDATA1329-01.json'),
 ('Crear fixture PostgreSQL17 independiente','gui02/fixture.json'),
 ('Conservar fallo GUI01 original','gui01/fixture.json'),
 ('Corregir protocolo CDP sin recompilar producto','gui01/HARNESS-CORRECTION.json'),
 ('Probar recorrido completo con UUID reales','gui02/browser.json'),
 ('Probar Enter y foco en aplicación completa','gui02/browser.json'),
 ('Probar idiomas y ancho390px','gui02/browser.json'),
 ('Comprobar cero escrituras administrativas','gui02/browser.json'),
 ('Retirar ficha tras revocación y403 reales','gui02/browser.json'),
 ('Comparar ocho tablas durante navegación','gui02/fixture.json'),
 ('Reiniciar aplicación y comprobar datos/403','gui02/fixture.json'),
 ('Detener Edge, servidores y PG propios','gui02/fixture.json'),
 ('Conservar fallo independiente DOM01','revision/dom01/result.json'),
 ('Ejecutar foco independiente DOM02','revision/dom02/result.json'),
 ('Obtener revisión técnica independiente','revision/GATE-TECNICO.json'),
 ('Conservar87 guiones anteriores completos','QA-TESTS-01.json'),
 ('Añadir QA88–90 detallados como planned','QA-TESTS-01.json'),
 ('Conservar listas de builds y disponibilidad','QA-TESTS-01.json'),
 ('Conservar generador y lógica de resultados','QA-TESTS-01.json'),
 ('Ejecutar50 pruebas pertinentes de guía','QA-TESTS-01.json'),
 ('Regenerar ambas guías y verificar87+8','QA-TESTS-01.json'),
 ('Inspeccionar capturas con límites explícitos','INSPECCION-VISUAL.json'),
 ('Actualizar continuidad/mapa sin puntos extra','CIERRE.md'),
 ('Preparar comprobación final de531 guardas','CIERRE.md'),
 ('Preparar adenda de revisión del cierre','CIERRE.md'),
 ('Preparar diff y manifiesto nuevo de evidencias','CIERRE.md'),
 ('Preparar commit local y comprobación posterior','CIERRE.md')]
 assert len(specs)==60
 plan=dict(scope='60 hitos internos de un incremento de navegación y su verificación; no60 funciones ni60 ejecuciones de pruebas. Últimos hitos preparan el cierre; su ejecución final se documenta aparte.',initialProgress=78,total=60,completed=60,batches=[dict(id=1270+n,title=title,status='verified',evidence=ER+'/'+proof) for n,(title,proof) in enumerate(specs)],finalProgress=78,finalAdoption=False)
 write_doc('docs/PLAN-SESENTA-TANDAS-1270-1329.json',json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
 message='**Bloque1270–1329 cerrado ·18.10.2026: recorrido de relaciones por UUID probado en candidata de desarrollo1329; global78 % aproximado, sin aumento.** Usuarios→Relaciones de grupos: Ver grupo de clientes/Ver grupo de usuarios, foco estable, estado accesible y borradores conservados. Ayuda Crear grupo corregida en EN/DE/ES; P3 de título resuelto antes del único buildfrontend.193fuentes,40artefactos; servidor1089/SQL/CSS/dependencias exactos. Edge/PostgreSQL17.11 nativos con reinicio/403/ocho tablas y revisión DOM independiente; fallos originales de arnés preservados.\n\n**QA real sigue1209/esquema13 y ZIP1269 intactos.** Catálogo90,87restaurado/8original disponibles; QA88–90 detallados planned/NO DISPONIBLES hasta integrar Windows y seleccionar candidata revisada.87guiones/listas/generador y resultados de Wascar conservados. Sin voz acreditada, operaciónQA ni adopción. [Contrato](GUI-NAVEGACION-RELACIONES-GRUPOS-S1.md), [60hitos](PLAN-SESENTA-TANDAS-1270-1329.json), [pruebas/límites](../'+ER+'/CIERRE.md). Siguiente: integración conservadora de1329 en Windows/QA; después funcionesRC9/administración/operaciónWindows final y QA/adopción de Wascar. Registros siguientes históricos.'
 for p in ['docs/CONTINUIDAD-CODEX.md','docs/INICIO-IMPLEMENTACION-S1.md','docs/PROGRESO-GLOBAL.md']:prepend(p,message)
 short='**Bloque1270–1329 vigente.** Navegación entre fichas de grupos por UUID desarrollada/probada/revisada en candidata1329; servidor1089/esquema13 exactos. Edge/PG con reinicio/403 y foco DOM independiente; un buildfrontend. QA1209/ZIP1269 intactos:90casos,87+8disponibles,QA88–90planned;87guiones/resultados previos conservados. Global78 % aproximado; integración Windows/QA y adopción pendientes. [Contrato](GUI-NAVEGACION-RELACIONES-GRUPOS-S1.md), [pruebas/límites](../'+ER+'/CIERRE.md). Registros siguientes históricos.'
 for p in ['docs/BRIEFING-MAESTRO.md','docs/ESTADO-ACEPTACION-S1.md','docs/UX-ADMINISTRACION-ARBOL.md']:prepend(p,short)
 for p in ['development/frontend/README.md','development/server/README.md']:prepend(p,short.replace('(GUI-','(../../docs/GUI-').replace('(../evidence/','(../../evidence/'))
 prepend('CHANGELOG.md','## 18.10.2026 · Bloque1270–1329 · Recorrido de relaciones\n\n- Botones por UUID entre grupos de usuarios y clientes, foco estable y retirada de selección obsoleta; borradores y permisos intactos. Ayuda de Crear grupo alineada con editores reales EN/DE/ES.\n- Un buildfrontend; Edge/PG nativo y reinicio/403/ocho tablas, regresión de estado y revisión DOM independiente. Fallos de arnés originales preservados.\n- Candidata1329 de desarrollo; QA1209/paquete1269 conservados.90casos/87+8disponibles,QA88–90planned; guía50/50 y resultados de Wascar intactos. Global78 % sin aumento. [Informe]('+ER+'/CIERRE.md).')
 p=ROOT/'docs/MAPA-ENTREGA.json';m=read(p);assert m['progress']==78 and [s['points'] for s in m['streams']]==[18,22,14,14,9,1]
 m.update(revision='2026-10-18-sesenta1270-1329',snapshot='Relaciones por UUID en desarrollo1329 revisado; QA1209/paquete1269 intactos.90casos/87+8disponibles,88–90planned;global78 % estimado.',currentBatch=dict(count=60,completed=60,ledger='docs/PLAN-SESENTA-TANDAS-1270-1329.json',evidence=ER+'/CIERRE.md'))
 for stream in m['streams']:
  for child in stream.get('children',[]):
   if child.get('id')=='admin-tree':
    child['note']='Alta guiada integrada Windows/QA1209; navegación entre relaciones por UUID desarrollada/revisada en1329 pendiente de integración. Experiencia administrativa integral y aceptación pendientes.'
    child.setdefault('children',[]).append(dict(id='group-relationship-navigation',name='Recorrido por UUID entre grupos de usuarios y de clientes',status='Probado y revisado · sólo desarrollo1329',qa='QA88–90 planned; QA real1209 conservado',evidence=ER+'/CIERRE.md'))
 m['nextMilestones'].insert(0,'Integrar candidata1329 exacta en Windows/QA13 con revisión y preservación del laboratorio antes de habilitar QA88–90.')
 write_doc('docs/MAPA-ENTREGA.json',json.dumps(m,ensure_ascii=False,indent=2)+'\n')
 report='''# Bloque1270–1329 · cierre de desarrollo

Sesenta hitos internos de un incremento funcional: navegar entre relaciones existentes de grupos por UUID, conservando RC9. No equivalen a60funciones ni60suites. Avance global aproximado **78 %**, sin aumento de puntos; adopción final de Wascar pendiente.

Desde Usuarios→Relaciones de grupos, Ver grupo de clientes abre el destino de una concesión explícita. Ver grupo de usuarios vuelve al origen correcto entre homónimos/múltiples padres. Sólo cambia la ficha local, con foco al selector persistente y estado polite/atomic. No asigna miembros/permisos, cambia usuario común, modifica borradores/journals ni decide autorización. El servidor conserva todas las comprobaciones. No añade AD/forest/herencia. Ayuda Crear grupo actualizada en EN/DE/ES; la revisión P3 previa corrigió el título hacia el editor real Permisos de grupos de usuarios antes de compilar.

Cambios de producto: AdminGroupRelations.jsx (autor group_links1329) y sólo tres cadenas de ayuda de AdminGroupCreation.jsx (coordinador). Exploración admin_next1329; revisión independiente review1089, sin editar producto. Fuentes193, sólo dos existentes modificadas; una compilación completa frontend, ceroC#. Candidata1329-01:40archivos,7.148.383bytes,22servidor/18frontend; servidor1089, SQL001–013, CSS, dependencias, herramientas y referenciaRC9 exactos. Sólo app.js difiere de1209. Manifiesto SHA25638bbae727ffd545436506ab65d1c66525a64bf316e0a9354079cace0aa60c6b6. No instalaciones, descargas ni cambios de versiones.

Pruebas nuevas y límites:

- Autor: regresión existente del componente status848 contra la fuente nueva, cuatro observaciones PASS. Dos órdenes previas no iniciaron por PATH de Node/directorio ausente, conservadas. Un build de fixture de componente; no aplicación completa, PG ni voz.
- GUI01 nativa: FAIL29.016s antes del primer destino, cero observaciones completadas. Botón presente; Enter CDP no activó. Se preservan entradas/salidas. GUI02 añade Page.bringToFront y text=retorno de carro al teclado; no aísla cuál de ambas correcciones resolvió el timeout. Sin cambiar/recompilar producto.
- GUI02: PASS21.375s en Windows11, Edge155 y PostgreSQL17.11, base nueva/secretos locales. Un escenario compuesto/cuatro observaciones: UUID/homónimos/múltiples padres, Enter/foco/AX, EN/DE/ES390px, borrador y usuario común intactos, cero escrituras a rutas administrativas, lector separado403 y retirada tras revocación real. Revocación SQL sólo en fixture sintética. Ocho tablas de grupos exactas durante navegación; reinicio y403 conservan ocho tablas posteriores. Login/preferencias sí pueden escribir sus tablas privadas en la fixture: no se afirma igualdad de39tablas ni ausencia de toda escritura. App/Edge/PG propios detenidos, entradas exactas.
- Revisor: DOM01 FAIL por protocolo de teclado incompleto, conservado; DOM02 PASS un caso/cuatro observaciones con props sintéticas: destino ausente, sin fallback por nombre, retirada/restauración sin selección automática, foco y estado estable. Dos builds de fixture, cero builds de app/PG/API/QA real; borrador externo de prueba es un stand-in, no la aplicación real. Gate y adenda de revisión separan lectura y ejecución.
- Guía:50/50 PASS1.438s,87casos completos/listas/build gates anteriores exactos y QA88–90 nuevos planned. Generador y lógica de resultados byteexactos; sólo ajuste ASCII87→90 en una aserción de recuento antigua. Ambas guías regeneradas y comando obligatorio qa_guide.py ejecutado. Sin escribir resultados/observaciones de Wascar.
- Coordinador inspeccionó tres capturas390px: nombres literales, UUID envolvente y foco visibles; son parte superior desplazada, no acreditan apariencia visual de botones bajo el pliegue. DOM/AX no prueba voz de lector, Office, otroWindows ni aceptación manual.

Comandos reproducibles (desde C:\\RackClick_SVR):

```powershell
C:/Python312/python.exe -B tools/tests/block1329.py build
# build es de una sola ejecución; su congelación original se conserva.
$candidate = Get-Content evidence/s1-20261018/sesenta-tandas-1270-1329/CANDIDATA1329-01.json -Raw | ConvertFrom-Json
C:/Python312/python.exe -B development/server/tests/test_admin_links1329_gui.py --output <directorio-nuevo> --dll $candidate.serverDll --frontend $candidate.frontend
C:/Python312/python.exe -B tools/windows/qa_guide.py
C:/Python312/python.exe -B tools/tests/block1329.py verify
```

El auxiliar qa_links1329.py conserva y prepara el catálogo una sola vez; no debe reaplicarse sobre90casos. Sus suites y resultados están en QA-TESTS-01.log/json. La prueba independiente conserva generador, scripts de ambos intentos y comandos propios en revision/. No se presentan informes históricos como ejecuciones nuevas.

**QA actual permanece1209/esquema13**, recuperación969/esquema12, paqueteWindows1269 exacto.531guardas de raíz/configuración/puntero/artefactos/evidencias históricas se comprueban antes del cierre; no se inicia ni consulta con SQL el laboratorio real. Catálogo90,87restaurado/8original disponibles; QA88–90 **NO DISPONIBLES** hasta integración Windows y selección revisada. No hay nuevoZIP, perfilWindows ni operación de actualizaciónQA en este bloque.

La lista de60hitos documenta preparación y pruebas; los últimos preparan verificación/adenda/diff/manifiesto/commit, cuya ejecución efectiva queda en VERIFICACION.json, revision/CIERRE-REVISADO.json, DIFF-CHECK.json, CAMBIOS.diff y SHA256SUMS. El commit local no publica ni adopta. Cada manifiesto se calcula tras completar la evidencia, nunca reutilizando el anterior.

Siguiente: integrar distribución1329 exacta en Windows/QA13 con preservación y revisión antes de habilitar QA88–90. Después quedan experiencia administrativa integral, funciones RC9/formatos/PDF/herramientas, Dosen/conectores y compensación colaborativa restante, accesibilidad/idiomas, servicio/identidad/PKI/instalaciónWindows limpia/recuperación/manualfinal y QA/adopción de Wascar, según PROGRESO-GLOBAL. Pesos20/25/15/15/15/10 y aportes18/22/14/14/9/1 intactos.
'''
 write_doc(ER+'/CIERRE.md',report)
 print(json.dumps(dict(prepared=True,hitos=60,progress=78,qaRealChanged=False)))

def verify():
 i=initial();exact(i['guards']);sources=read(E/'SOURCE-FREEZE-APP.json')['sources'];exact(sources);assert len(sources)==193
 assert {p for p,h in sources.items() if h!=i['originalProductSources'][p]}==set(MUTABLE)
 m=read(E/'CANDIDATA1329-01.json');assert sha(E/'CANDIDATA1329-01.json')=='38bbae727ffd545436506ab65d1c66525a64bf316e0a9354079cace0aa60c6b6'
 for part,files in m['distributions'].items():assert tree(ROOT/m['candidateDirectory']/part)==files
 assert sum(len(v) for v in m['distributions'].values())==40 and m['totalBytes']==7148383
 g=read(E/'gui02/fixture.json');exact(g['inputSha256']);assert g['result']=='PASS' and g['inputsUnchanged'] and g['labStopped'] and g['serversStopped']
 d=read(E/'revision/dom02/result.json');assert d['successful'] and d['ownedEdgeStopped'] and d['sourcesUnchanged'] and d['artifactsUnchanged']
 gate=read(E/'revision/GATE-TECNICO.json');assert gate['approved'] and not gate['finalAdoption']
 q=read(ROOT/'docs/QA-CASOS-WASCAR.json');old=read(E/'qa-before/QA-CASOS-WASCAR.json');assert len(q['cases'])==90 and q['cases'][:87]==old['cases'] and all(c['feature']=='planned' for c in q['cases'][87:])
 assert {k:v for k,v in q.items() if k not in ['revision','cases']}=={k:v for k,v in old.items() if k not in ['revision','cases']}
 import importlib.util
 spec=importlib.util.spec_from_file_location('guide1329verify',ROOT/'tools/windows/qa_guide.py');guide=importlib.util.module_from_spec(spec);spec.loader.exec_module(guide)
 for profile,count in [('manual',8),('rc9',87)]:
  assert guide.generate(check=True,profile=profile);cs=json.loads(guide.render(q,guide.context(profile=profile)).split('const guide=',1)[1].split(';',1)[0])['cases'];assert sum(c['available'] for c in cs.values())==count
 assert (ROOT/'tools/windows/qa_guide.py').read_bytes()==subprocess.check_output([str(GIT),'show',BASE+':tools/windows/qa_guide.py'])
 progress=read(ROOT/'docs/MAPA-ENTREGA.json');assert progress['progress']==78 and [s['points'] for s in progress['streams']]==[18,22,14,14,9,1] and [s['weight'] for s in progress['streams']]==[20,25,15,15,15,10]
 plan=read(ROOT/'docs/PLAN-SESENTA-TANDAS-1270-1329.json');assert len(plan['batches'])==plan['completed']==plan['total']==60 and [b['id'] for b in plan['batches']]==list(range(1270,1330))
 assert all((ROOT/b['evidence']).is_file() for b in plan['batches'])
 checks=dict(guards=len(i['guards']),productSources=193,changedProductSources=2,artifactFiles=40,serverFilesExact=22,candidateBytes=7148383,actualQaOperations=0,actualQaFrontend=1209,actualQaSchema=13,caseCount=90,available=dict(rc9=87,manual=8),newCasesPlanned=[88,89,90],manualWascarResultsWritten=False,globalProgress=78,finalAdoption=False)
 if (E/'VERIFICACION.json').exists():assert read(E/'VERIFICACION.json')['checks']==checks
 else:save('VERIFICACION.json',dict(successful=True,utc=datetime.now(timezone.utc).isoformat(),checks=checks))
 print(json.dumps(dict(successful=True,**checks)))
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['init','build','close','verify']);a=p.parse_args();globals()[a.action]()
if __name__=='__main__':main()
