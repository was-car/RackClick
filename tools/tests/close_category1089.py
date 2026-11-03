"""Close the reviewed category-palette development block; never select or start real QA."""
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2];ER='evidence/s1-20261018/sesenta-tandas-1030-1089';E=ROOT/ER
PIN='c8b3df5b8e0fb6c5db148b7ddca2a8064ade6b90557713fb0835cbf69bb9710c'
BASE='eb97a85dc439c03718fa2af7db3f531567c0dccc';GIT=ROOT/'.local/git-2.55.0.5/cmd/git.exe'

def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads((E/p).read_bytes())
def write(p,v):
 with p.open('x',encoding='utf-8') as f:f.write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def prepend(path,text):
 p=ROOT/path;b=p.read_bytes();assert b'Bloque1030' not in b[:1400]
 head,sep,tail=b.partition(b'\n');nl=b'\r\n' if head.endswith(b'\r') else b'\n'
 p.write_bytes(head+sep+nl+text.strip().encode().replace(b'\n',nl)+nl+nl+tail)

def guards():
 start=read('INICIO.json');assert start['baseCommit']==BASE
 assert all(sha(ROOT/p)==h for p,h in start['guards'].items())
 sources=read('SOURCE-FREEZE-02.json')['sources'];assert len(sources)==190
 assert all(sha(ROOT/p)==h for p,h in sources.items())
 manifest=read('CANDIDATA1089-02.json');assert sha(E/'CANDIDATA1089-02.json')==PIN
 artifacts=[(ROOT/manifest['candidateDirectory']/part/p,h) for part,files in manifest['distributions'].items() for p,h in files.items()]
 assert len(artifacts)==40 and all(sha(p)==h for p,h in artifacts)
 assert sum(p.stat().st_size for p,h in artifacts)==7133395
 original=read('CANDIDATA1089-01.json');assert sha(E/'CANDIDATA1089-01.json')=='39d7e3f2835b86c8ded2e44c7ee04d95a849101518f90d37501d44378f56f162'
 assert all(sha(ROOT/original['candidateDirectory']/part/p)==h for part,files in original['distributions'].items() for p,h in files.items())
 assert manifest['distributions']['frontend']==original['distributions']['frontend']
 for p,h in manifest['distributions']['server'].items():
  if p not in ['RackClick.Server.dll','RackClick.Server.pdb']:assert original['distributions']['server'][p]==h,p
 return start,sources

def results():
 assert read('BUILD-01.json')['successful'] and read('BUILD-02.json')['successful']
 assert 'RESULT: 76 domain tests passed' in (E/'build-01-domain.log').read_text()
 assert read('frontend/NODE-FINAL.json')['tests']==41 and read('frontend/NODE-FINAL.json')['result']=='PASS'
 pg1=read('backend/pg01/result.json');pg2=read('backend/pg02/result.json')
 assert not pg1['successful'] and pg1['testsRun']==4
 assert sorted(c['status'] for c in pg1['cases'])==['error','passed','passed','passed']
 assert pg2['successful'] and pg2['testsRun']==2
 for r in [pg1,pg2]:
  assert all(r[k] for k in ['labStopped','serversStopped','sourcesUnchanged','serverUnchanged','frontendUnchanged','baselineUnchanged'])
 gui=read('gui/03/result.json');assert gui['result']=='PASS'
 assert all(gui[k] for k in ['labStopped','serversStopped','artifactsUnchanged','sourcesUnchanged','serverRestartPersistence','originalCableExact','portPalette12Untouched'])
 assert gui['guiConnectionCount']==5 and gui['guiCreateCommands']==3
 assert read('gui/01/result.json')['result']=='FAIL' and read('gui/02/result.json')['result']=='FAIL'
 own=read('revision/own-waits01/result.json');assert own['successful'] and own['testsRun']==1
 assert all(own[k] for k in ['labStopped','serversStopped','sourceHashesUnchanged','artifactsUnchanged'])
 qa=read('QA-TESTS-01.json');assert qa['successful'] and qa['caseCount']==84 and qa['available']==dict(manual=8,rc9=81)
 focal=read('QA-FOCAL-02.json');assert focal['successful'] and focal['testsRun']==2 and focal['previous81Exact']
 gate=read('revision/GATE-TECNICO.json');assert gate['valid'] and gate['approved'] and not gate['openBlockingFindings']
 return pg1,pg2,gui,own,qa

def close():
 guards();pg1,pg2,gui,own,qa=results();assert not (E/'CIERRE.md').exists()
 report=f'''# Bloque 1030–1089 · paleta personal por parejas de categorías

**60 hitos internos completados. Avance global aproximado:78 %, sin aumento.** Nueva función desarrollada y probada; QA/adopción final de Wascar pendiente. No equivale a60 funciones ni60 suites.

## Resultado y disponibilidad

Se conservan las28 parejas simétricas de siete categorías y las diez muestras de RC9, incluidas parejas consigo mismas. Nueva sección **Paleta→Parejas de categorías**, con borrador, toggle/×, Restablecer todo y Guardar confirmado por commit+GET. Cambiar entre Tipos de puerto y Parejas conserva borradores; cerrar los descarta. Se mantienen RC9/CSS/Click-Click, EN/DE/ES y nombres literales.

La preferencia pertenece a la cuenta autenticada, incluido Lector/sin clientes. No concede edición de inventario ni comparte el mapa privado. El servidor lee una paleta confirmada por comando al crear conexiones por UUID: color manual válido→pareja→null. La clasificación usa catalog.presetKey, no etiquetas traducidas; fallback legacy exacto y Other para desconocidos. El color queda en el cable compartido. Los cables anteriores, update/reconnect/duplicación y puertos no se recolorean. Se conservan límites128, reservas/ocupación/PoE/ámbitos y atomicidad.

El QA real sigue en969/esquema12 y conserva ZIP1029, cuentas y datos. **QA-82 a QA-84 están detallados pero NO DISPONIBLES**, pendientes de integración Windows/selección revisada13. Catálogo84, disponibles81 restaurado/8 original. Los81 casos previos, listas de parejas, generador y resultados/observaciones de Wascar se conservan; no se asignan Pass manuales.

## Candidatas y correcciones

SQL013 añade dos tablas personales:39 en total; SQL001–012, dominio, dependencias, versiones y referencia adoptada exactos. Migrador y recuperación administrativa alineados a13. API cerrada /api/v1/me/category-colors con28 claves/10 muestras, ETag personal, CSRF, actor de sesión, revisión, recibos/replay/noop/conflictos/fences y auditoría atómicos.

La revisión detectó P2 heredado: InventoryStore.Execute no releía la caducidad natural de sesión antes del commit. FIX02 añade exactamente una revalidación final. Single y batch que caducan durante una espera real devuelven401 y conservan39 tablas/revisión sin recibo ni auditoría. No se relaja una protección para hacer pasar pruebas.

Dos publicaciones C# y una compilación frontend en este bloque. Dominio76 se ejecutó en la primera y se reutiliza por identidad de sus fuentes/artefactos. El primer freeze observó41 archivos porque el SDK generó un AppHost.exe opcional: fallo del auxiliar conservado en FREEZE-01-FAIL.json, publicación y primera copia retenidas. La distribución dotnet/DLL excluye sólo ese ejecutable, sin otra compilación. FIX02 reutiliza frontend01 exacto. Candidata final **1089-02**,40 archivos (22+18),7.133.395 bytes, SHA256`{PIN}`.

## Pruebas nuevas y atribución exacta

| Responsable | Ejecución y resultado |
|---|---|
| Coordinador | Publish01, dominio76PASS y frontend; Publish02 únicamente C# por P2. Ambos con190 fuentes estables durante compilación. |
| Autor frontend | Node41/41PASS:22 focos nuevos+19 de paleta de tipos969. Primer fallo de arnés por ruta Git conservado. |
| Autor backend, candidata01 | Cuatro focos PostgreSQL en{pg1['elapsedSeconds']}s:01/03/04PASS y02ERROR por rawJSON con ↔ enviado como Latin-1 antes de HTTP. No es4/4Pass. Matriz28×2, claves frente a etiquetas, cliente/Systemhaus, prioridad/coherencia/replay/no recolor/atomicidad, sesiones/concurrencia y migración12→13 dos veces, reinicio, pg_dump/pg_restore39 tablas y CLI13. |
| Autor backend, FIX02 | Sólo dos focos02+05:2/2PASS en{pg2['elapsedSeconds']}s. RawJSON corregido a UTF8 en el arnés; contrato/CSRF/límites/corrupción/rollback y expiración final single+batch con39 tablas exactas,401,0recibo/0auditoría. No se presentan los tres éxitos anteriores como ejecución de FIX02. |
| Autor GUI, candidata01 | Edge/PostgreSQL:PASS,{gui['seconds']}s; siete observaciones, guardado/relectura/otra sesión/otro actor,503 y recuperación, teclado/390px/EN/DE/ES, owner forjado, Click-Click y lote entre racks. Cinco conexiones/tres comandos GUI; siete tablas de inventario sin conexión y cable original exactos,8 journals/8 auditorías, paleta012 intacta y reinicio. No compara39 tablas. |
| Revisor independiente, candidata01 | Un foco PostgreSQL propioPASS: creación esperando cliente mientras el mismo actor guarda otra paleta, materialización del color confirmado/replay original y revocación de sesión durante espera personal→401 sin recibo/auditoría. Fuentes/artefactos exactos; no repite suites de autores. |
| Revisor, FIX02 | Compatibilidad estática de fuentes/IL, fuentes/rutas no modificadas y frontend idéntico; lectura de focos finales y capturas. El foco propio y GUI de01 conservan su pin/atribución; no son nueva ejecución runtime con DLL02. |
| Coordinador de guía | {qa['testsRun']}/{qa['testsRun']}PASS,{qa['seconds']}s, más foco final2/2 tras corregir ubicación del botón Todos los clientes (Infraestructura es un título, no el botón). Sólo cambian instrucciones nuevas82–84.84 casos/81+8 disponibles, nuevos82–84planned,81 previos/listas/resultados intactos. |

Los fallos GUI01 (click sobre SVG) yGUI02 (captura fetch después de construir el cliente) son fallos del arnés: se conservan completos y sóloGUI03 esPASS. El segundo se corrige capturando peticiones CDP reales; se comprueba que el almacenamiento local legacy no impone colores automáticos en el payload. Ninguno requirió cambiar producto ni recompilar frontend.

## Límites y siguiente paso

Todas estas ejecuciones usan Windows11, .NET10.0.401/Node24.21.0/PostgreSQL17.11 fijados, laboratorios nuevos y secretos locales. Sin descargas, instalaciones, cambios de versión ni publicación. Procesos propios detenidos. Las pruebas HTTP usan loopback de desarrollo; no acreditan TLS ni instalación/servicio Windows13. Inspección PNG/DOM no acredita voz de lector de pantalla. No nueva ejecución Office/PDF ni adopción de Wascar.

Siguiente bloque: integrar candidata1089-02/esquema13 en perfiles/operadores/paquete reproducible Windows y copiar conservadoramente QA969/12 con su recuperación849/11 a otra instancia antes de habilitar QA82–84. Después continúan formatos/PDF/herramientas/accesibilidad, Dosen/undo/administración visual y Windows final/recuperación/manual/QA/adopción. Se mantienen pesos20/25/15/15/15/10 y aportes18/22/14/14/9/1: no puntos por IDs, pruebas ni esta función parcial.

Verificación y adenda final preceden al diff/SHA256SUMS nuevo y commit local. No quedan agentes trabajando después del cierre.
'''
 (E/'CIERRE.md').write_text(report,encoding='utf-8')
 plan_path=ROOT/'docs/PLAN-SESENTA-TANDAS-1030-1089.json';plan=json.loads(plan_path.read_bytes());assert plan['completed']==0 and len(plan['batches'])==60
 for b in plan['batches']:
  i=b['id']
  proof='INICIO.json' if i<1040 else 'revision/GATE-TECNICO.json' if i<1056 else 'frontend/NODE-FINAL.json' if i<1066 else 'BUILD-01.json' if i<1068 else 'CANDIDATA1089-02.json' if i==1068 else 'backend/pg01/result.json' if i<1076 else 'gui/03/result.json' if i<1080 else 'revision/own-waits01/result.json' if i==1080 else 'backend/pg02/result.json' if i==1081 else 'QA-TESTS-01.json' if i<1084 else 'CIERRE.md'
  assert (E/proof).is_file();b.update(status='verified',evidence=ER+'/'+proof,independentEvidence=ER+'/revision/GATE-TECNICO.json')
 plan.update(completed=60,finalProgress=78);plan_path.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 summary='''**Bloque1030–1089 cerrado ·18.10.2026: paleta personal por parejas de categorías desarrollada/probada en candidata13; global78 % aproximado, sin aumento.** Veintiocho parejas y diez muestras RC9; sección Paleta→Parejas de categorías, borrador/Guardar confirmado y preferencia por cuenta. El servidor aplica una paleta confirmada al crear por UUID, con prioridad manual→pareja→null y categoría por clave estable, sin recolorear existentes.

SQL013 aditiva,39 tablas, migrador/CLI13 alineados. P2 heredado de caducidad antes de commit de inventario corregido con una revalidación final y prueba single/batch→401/rollback completo. Dos publicaciones C#, un frontend; dominio76/Node41, PG inicial3PASS+1ERROR de arnés, focos finales2PASS, Edge/PG siete observaciones y revisión independiente. Los resultados de candidata01 se distinguen de FIX02 mediante compatibilidad estática; fallos/artefactos originales conservados.

**QA real conserva969/esquema12 y ZIP1029.** Catálogo84, disponibles81 restaurado/8 original; QA82–84 detallados siguen pendientes de integrar y seleccionar Windows13 en otra copia. Los81 casos previos, listas, generador y resultados de Wascar permanecen. Siguiente: integración Windows13/QA conservadora; después restantes funciones/Windows final/QA/adopción. [Contrato](API-PALETA-CATEGORIAS-PERSONAL-S1.md), [plan60](PLAN-SESENTA-TANDAS-1030-1089.json), [pruebas, fallos y límites](../evidence/s1-20261018/sesenta-tandas-1030-1089/CIERRE.md). Los registros siguientes son históricos.'''
 for p in ['docs/CONTINUIDAD-CODEX.md','docs/INICIO-IMPLEMENTACION-S1.md','docs/PROGRESO-GLOBAL.md']:prepend(p,summary)
 short='''**Bloque1030–1089 vigente.** Paleta personal28 parejas RC9 y default autoritativo de creación probados/revisados en candidata1089-02/esquema13. P2 de expiración antes del commit corregido. QA969/12 y ZIP1029 conservados;84 casos,81+8 disponibles,QA82–84 pendientes de integrar Windows13/seleccionar copia. Global78 % aproximado y adopción pendiente. [Contrato](API-PALETA-CATEGORIAS-PERSONAL-S1.md), [evidencias/límites](../evidence/s1-20261018/sesenta-tandas-1030-1089/CIERRE.md). Registros siguientes históricos.'''
 for p in ['docs/BRIEFING-MAESTRO.md','docs/ACEPTACION.md','docs/ESTADO-ACEPTACION-S1.md','docs/MAPA-RC9-R3.md','docs/QA-COLABORACION-Y-RESTAURACION.md']:prepend(p,short)
 for p in ['development/server/README.md','development/frontend/README.md']:prepend(p,short.replace('](API-','](../../docs/API-').replace('](../evidence/','](../../evidence/'))
 prepend('CHANGELOG.md','## 18.10.2026 ·1030–1089 · Paleta por categorías y expiración de inventario\n\n- Preferencia personal28×10, API/journal/SQL013 y GUI RC9; default de conexión decidido por servidor al crear.\n- P2 de expiración antes de commit corregido y probado; Node41/dominio76/PG/Edge/revisión. Fallos de arnés originales conservados.\n- Candidata13 de40 archivos; QA969/ZIP1029 conservados,QA82–84 pendientes.60 hitos internos/global78 % sin aumento. [Informe](evidence/s1-20261018/sesenta-tandas-1030-1089/CIERRE.md).')
 p=ROOT/'docs/MAPA-ENTREGA.json';m=json.loads(p.read_bytes());assert m['progress']==78 and [s['points'] for s in m['streams']]==[18,22,14,14,9,1]
 m.update(revision='2026-10-18-sesenta1030-1089',snapshot='Paleta personal por28 parejas probada/revisada en13;QA969/12 conservado,84casos/81+8disponibles,global78 % estimado.',currentBatch=dict(count=60,completed=60,ledger='docs/PLAN-SESENTA-TANDAS-1030-1089.json',evidence=ER+'/CIERRE.md'))
 for s in m['streams']:
  if any(n.get('id')=='personal-port-type-palette' for n in s.get('children',[])):
   s['children'].append(dict(id='personal-category-pair-palette',name='Paleta personal RC9 por parejas de categorías y color inicial de conexiones',status='Probado y revisado · desarrollo13',qa='QA82–84 pendientes de Windows/selección13',evidence=ER+'/CIERRE.md'))
   for n in s['children']:
    if n.get('id')=='personal-port-type-palette':n['note']='Tipos integrados en QA969. Paleta por parejas implementada/probada en13, aún pendiente de integración Windows/QA.'
 m['nextMilestones'].insert(0,'Integrar candidata1089-02/esquema13 en Windows y nueva copia QA antes de habilitar QA82–84.')
 m['history'].append(dict(id='h1030-1089',name='1030–1089 · Paleta por parejas y expiración final',status='Probado y revisado',note='Candidata13/40archivos;QA969conservado,QA82–84pendientes;78 % sin aumento.'))
 p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(dict(completed=60,progress=78,candidateSchema=13,selectedQaSchema=12,available=81)))

def verify():
 assert not (E/'VERIFICACION-FINAL.json').exists();start,sources=guards();results()
 git=lambda *a:subprocess.check_output([str(GIT),*a],cwd=ROOT)
 assert git('rev-parse','HEAD').decode().strip()==BASE
 old=json.loads(git('show',BASE+':docs/QA-CASOS-WASCAR.json'));current=json.loads((ROOT/'docs/QA-CASOS-WASCAR.json').read_bytes())
 assert current['cases'][:81]==old['cases'] and len(current['cases'])==84 and all(c['feature']=='planned' for c in current['cases'][81:])
 assert all(current[k]==v for k,v in old.items() if k not in ['revision','cases'])
 spec=importlib.util.spec_from_file_location('g1089verify',ROOT/'tools/windows/qa_guide.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
 assert all(g.generate(check=True,profile=p) for p in ['manual','rc9'])
 assert (ROOT/'tools/windows/qa_guide.py').read_bytes()==git('show',BASE+':tools/windows/qa_guide.py')
 plan=json.loads((ROOT/'docs/PLAN-SESENTA-TANDAS-1030-1089.json').read_bytes());assert plan['completed']==60 and all(b['status']=='verified' and (ROOT/b['evidence']).is_file() for b in plan['batches'])
 progress=json.loads((ROOT/'docs/MAPA-ENTREGA.json').read_bytes());assert progress['progress']==78 and [s['points'] for s in progress['streams']]==[18,22,14,14,9,1]
 write(E/'VERIFICACION-FINAL.json',dict(successful=True,utc=datetime.now(timezone.utc).isoformat(),protectedFilesExact=len(start['guards']),productSourcesExact=len(sources),candidateFilesExact=40,
  selectedQaUnchanged=True,selectedQaRevision=969,selectedQaSchema=12,windowsPackage1029Unchanged=True,caseCount=84,available=dict(manual=8,rc9=81),previous81Exact=True,
  newCasesPlanned=['QA-82','QA-83','QA-84'],manualWascarResultsWritten=False,applicationPublications=2,frontendBuilds=1,domainTests=76,nodeTests=41,finalAdoption=False,progress=78))
 print('Verificación final: PASS; QA969 conservado; global78 %')

if __name__=='__main__':
 if sys.argv[1:] == ['verify']:verify()
 else:close()
