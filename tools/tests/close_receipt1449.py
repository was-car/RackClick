"""Prepare reviewable continuity, then seal evidence; never changes actual QA."""
import argparse,json,subprocess
from pathlib import Path
from block1449 import ROOT,E,ER,BASE,GIT,MUTABLE,NEW,sha,read,save,exact,guarded
def native():
 runs=[p for p in sorted(E.glob('native*/fixture.json'))];assert runs
 for p in runs:
  r=read(p);assert r['labStopped'] and r['serversStopped'] and r['inputsUnchanged']
  if r['result']!='PASS':
   assert (p.parent/'DIAGNOSTICO.json').is_file()
   for name in ['development/frontend/tests/browser-admin-receipt1449.mjs','development/server/tests/test_admin_receipt1449_gui.py']:assert sha(p.parent/'executed-inputs'/Path(name).name)==r['inputSha256'][name]
 p=runs[-1];r=read(p);exact(r['finalInputSha256']);assert r['result']=='PASS' and r['committedCreateOperations']==4 and r['readOnlyEightGroupTablesExact'] and r['reader403BothKinds'] and r['restartAndSeparateSessionReadVerified']
 return p,r
def verify_product():
 initial=guarded();sources=read(E/'SOURCE-FREEZE-APP.json')['sources'];exact(sources);assert len(sources)==195;assert set(sources)-set(initial['originalProductSources'])==set(NEW);assert {p for p,h in initial['originalProductSources'].items() if sources[p]!=h}==set(MUTABLE)
 candidate=read(E/'CANDIDATA1449-01.json');artifacts={(ROOT/candidate['candidateDirectory']/part/p).relative_to(ROOT).as_posix():h for part,files in candidate['distributions'].items() for p,h in files.items()};exact(artifacts);assert len(artifacts)==40
 old=read(ROOT/candidate['sourceManifest']);assert candidate['distributions']['server']==old['distributions']['server'];assert {p for p,h in candidate['distributions']['frontend'].items() if h!=old['distributions']['frontend'][p]}=={'app.js'}
 qa=read(E/'QA-TESTS-01.json');assert qa['successful'] and qa['testsRun']==50 and qa['available']==dict(manual=8,rc9=90);assert len(read(ROOT/'docs/QA-CASOS-WASCAR.json')['cases'])==93
 final_qa=read(E/'QA-FOCO-ETIQUETAS-03.json');assert final_qa['successful'] and final_qa['testsRun']==3;exact(final_qa['sourceHashes'])
 prior_qa=read(E/'QA-FOCO-RUTA-02.json');assert prior_qa['successful'] and prior_qa['testsRun']==3
 for name,h in prior_qa['sourceHashes'].items():
  backup=E/'qa-02-before-label-fix'/Path(name).name;assert sha(backup if backup.exists() else ROOT/name)==h
 previous=read(E/'qa-before/QA-CASOS-WASCAR.json');now=read(ROOT/'docs/QA-CASOS-WASCAR.json');assert now['cases'][:90]==previous['cases'];assert {k:v for k,v in now.items() if k not in ['revision','cases']}=={k:v for k,v in previous.items() if k not in ['revision','cases']}
 return initial,sources,candidate,artifacts
def prepend(path,text):
 p=ROOT/path;b=p.read_bytes();assert 'Bloque1390–1449'.encode() not in b[:800];nl=b'\r\n' if b'\r\n' in b else b'\n';pos=b.index(nl)+len(nl);p.write_bytes(b[:pos]+nl+text.replace('\n','\n').encode().replace(b'\n',nl)+nl+nl+b[pos:])
def documents():
 initial,sources,candidate,artifacts=verify_product();p,n=native();gate=read(E/'revision/REVISION-FUENTE.json');assert gate['approved'] and not gate['openBlockingFindings'];exact(gate['sourceHashes'])
 report=f'''# Cierre1390–1449 · continuación del alta de grupos

Incremento completo de desarrollo: **Grupo creado → Abrir relaciones**, con nombre literal, tipo y UUID confirmados.60hitos internos de implementación/verificación/documentación, no60 funciones ni60 suites. Global **78 % aproximado**, sin cambio de ponderación. Adopción final pendiente de Wascar.

## Cambio y correcciones

- `AdminGroupCreation.jsx`, `AdminGroups.jsx`, `AdminGroupRelations.jsx`: coordinación actor/generación, snapshot vigente, recuperación y navegación de un uso, foco estable sin retarget de los tres editores.
- Nuevos `AdminGroupReceipt.jsx` y `admin-group-receipt.ts`: recibo en memoria proyectado sólo del resultado validado; nombre/tipo/UUID y Abrir relaciones EN/DE/ES. Ningún permiso se concede por navegar.
- P2 detectado antes del build: `notRecorded` posterior a cleanup fallido podía borrar evidencia de commit. El helper conserva recibo y pendiente; secuencia de recuperación añadida al foco9/9.
- Segundo borde prebuild: lectura401/403 concurrente con alta podía permitir callback tardío del mismo actor. Invalidar la generación de autoridad impide restaurarlo. El foco DOM independiente distingue dobles de persistencia real.
- Sin cambios API, C#, SQL, CSS o dependencias.195fuentes congeladas:3existentes y2nuevas; una compilación frontend, cero C#.40artefactos:22servidor1089 y18frontend; sólo app.js difiere de1329.

## Ejecuciones nuevas en Windows

- Node24.21:8/8 iniciales y9/9 finales, transporte controlado y helpers reales; sinPG/DOM. Evidencia autor/FOCO-NODE-01 y02, código/diff/freeze en autor/.
- `C:/Python312/python.exe -B tools/tests/block1449.py build`: BUILD-01 y CANDIDATA1449-01, SDK10.0.401/PG17.11 fijados sin descargas ni cambios de versión.
- `C:/Python312/python.exe -B development/server/tests/test_admin_receipt1449_gui.py --output {p.parent.relative_to(ROOT).as_posix()} --dll <serverDll de CANDIDATA1449-01> --frontend <frontend de CANDIDATA1449-01>`: **PASS**, {n['seconds']}s. Edge/PG17 nativos en clúster/base nuevos, secretos locales; cuatro commits reales (dos tipos homónimos y dos altas localizadas EN/DE). CDP pierde una respuesta después del commit HTTP y Consultar original recupera el UUID sin duplicar alta.
- Navegación/Enter/mismoUUID, borradores, EN/DE/ES390px, recarga y otro contexto de navegador; ocho tablas de grupos exactas después de las cuatro altas. Login/preferencias escriben fuera de esas ocho tablas. ReinicioASP.NET, otra sesión HTTP lee ambos UUID y Lector recibe403 en ambos tipos. No se acredita voz, otra máquina o Windows limpio. Todos los procesos propios detenidos.
- `C:/Python312/python.exe -B tools/tests/qa_receipt1449.py`: **50/50PASS** iniciales. Tras corregir únicamente la ruta de idioma de QA93, `qa_receipt1449_routes.py`: **3/3PASS** de ruta; luego foco documental `qa_receipt1449_labels.py`: **3/3PASS** finales por etiquetas exactas QA91/92. Se conservan entradas/salidas anteriores, sin repetir toda la regresión. Catálogo93; QA91–93planned/no disponibles incluso con pareja futura. Los90 casos previos/listas completos permanecen exactos; disponibles90restaurado/8original. Generador y lógica/resultados de Wascar sin cambios. Ambas guías regeneradas y comando obligatorio `C:/Python312/python.exe -B tools/windows/qa_guide.py` ejecutado.
- Revisión independiente en revision/: lectura previa al build, foco DOM con dobles declarados y adenda final. Sus pruebas no equivalen a PostgreSQL ni QA de Wascar. Native01 falló a14s por buscar idioma dentro de Administración; Native02 a19,562s por buscar UUID completo en texto de cliente donde sólo había etiqueta corta. Corregidos sólo arneses/rutaQA93; revisión P3 posterior ajustó también los botones exactos de QA92 y títulos/tipos de QA91/92; fuentes ejecutadas, diagnósticos y salidas conservados. Native03 PASS21,297s sobre la misma candidata/build. Las ejecuciones antiguas no se presentan como nuevas.

## Disponibilidad y conservación

La candidata1449 es de desarrollo; **no se ha seleccionado en el QA real**. Continúan QA1329/esquema13, ZIP1389 y recuperación969/esquema12.1021guardas protegidas exactas (1024iniciales menos3fuentes autorizadas), incluidos informes originales, distribuciónQA, archivos privados, puntero y configuración.0arranques/login/SQL/operaciones del QA real; sólo comprobación de hashes.

Siguiente: integrar conservadoramente1449 en Windows/QA antes de habilitar QA91–93; después funcionesRC9/administración/auditoría, Dosen/conectores/undo y operaciónWindows final/recuperación/manual/QA/adopción. No es servidor final ni instalador completo adoptado.

El sello SHA256SUMS de esta carpeta se genera tras la adenda/diff finales; el manifiesto raíz histórico no representa esta candidata. Commit local y comprobación posterior completan el cierre fuera de este informe congelado. No hay publicación.
'''
 (E/'CIERRE.md').write_text(report,encoding='utf-8',newline='\n')
 text='''**Bloque1390–1449 cerrado ·18.10.2026: alta de grupos con recibo confirmado y continuación por UUID; global78 % aproximado, sin aumento.** Grupo creado→Abrir relaciones conserva borradores y requiere snapshot vigente/commit; dos bordes de recuperación/denegación concurrente corregidos antes del único buildfrontend.195fuentes/40artefactos; servidor1089/SQL/CSS/dependencias intactos. Node9/9, Edge/PostgreSQL17 nativos con pérdida de respuesta real/reinicio/403 y revisión independiente; atribución y límites en informe.

**QA real1329 y ZIP1389 conservados.** Catálogo93,90restaurado/8original disponibles; QA91–93planned/no disponibles hasta integración Windows posterior.90guiones/listas/generador y resultados de Wascar intactos. No nueva selección/arranque/SQL del QA real ni adopción. [Contrato](GUI-CONTINUACION-ALTA-GRUPO-S1.md), [60hitos](PLAN-SESENTA-TANDAS-1390-1449.json), [pruebas/límites](../evidence/s1-20261018/sesenta-tandas-1390-1449/CIERRE.md). Siguiente: integrar1449 y completar funciones/operaciónWindows final/QA/adopción. Registros siguientes históricos.'''
 for path in ['docs/CONTINUIDAD-CODEX.md','docs/INICIO-IMPLEMENTACION-S1.md','docs/PROGRESO-GLOBAL.md']:prepend(path,text)
 short='''**Bloque1390–1449 vigente.** Grupo creado→Abrir relaciones desarrollado/probado/revisado en candidata1449;195fuentes, un buildfrontend, servidor1089/esquema13 exactos. Recibo UUID y guardas sin asignación automática; Node9/9/EdgePG/reinicio/403 y revisión DOM independiente. QA1329/ZIP1389 intactos:93casos,90+8disponibles,QA91–93planned;90guiones/resultados conservados. Global78 % aproximado, integraciónWindows/QA y adopción pendientes. [Contrato](GUI-CONTINUACION-ALTA-GRUPO-S1.md), [pruebas/límites](../evidence/s1-20261018/sesenta-tandas-1390-1449/CIERRE.md). Registros siguientes históricos.'''
 for path in ['docs/UX-ADMINISTRACION-ARBOL.md','docs/QA-COLABORACION-Y-RESTAURACION.md']:prepend(path,short)
 for path in ['development/frontend/README.md','development/server/README.md']:prepend(path,short.replace('](GUI-','](../../docs/GUI-').replace('](../evidence/','](../../evidence/'))
 prepend('CHANGELOG.md','''## 18.10.2026 · Bloque1390–1449 · Continuación del alta de grupos

- Tarjeta de commit con nombre/tipo/UUID y Abrir relaciones explícito, snapshot vigente, foco/idiomas y borradores conservados. Recuperación incierta y denegación concurrente corregidas antes del build; sin cambios de permisos implícitos.
- Node9/9, un buildfrontend, Edge/PG real/reinicio/403 y revisión independiente. QA1329/ZIP1389 intactos;93casos/90+8disponibles,QA91–93planned,50pruebas de guíaPASS y resultados previos conservados.
-60hitos internos; global78 % sin aumento. [Informe](evidence/s1-20261018/sesenta-tandas-1390-1449/CIERRE.md).''')
 path=ROOT/'docs/MAPA-ENTREGA.json';m=read(path);assert m['progress']==78;assert [(s['points'],s['weight']) for s in m['streams']]==[(18,20),(22,25),(14,15),(14,15),(9,15),(1,10)]
 m['revision']='2026-10-18-sesenta1390-1449';m['snapshot']='Recibo de alta de grupos1449 desarrollado/probado; QA1329/ZIP1389 intactos.93casos,90+8disponibles;QA91–93planned;global78 % estimado.'
 m['currentBatch']=dict(count=60,completed=60,ledger='docs/PLAN-SESENTA-TANDAS-1390-1449.json',evidence=ER+'/CIERRE.md');m['nextMilestones'][0]='Integrar1449 en Windows/QA antes de habilitarQA91–93; completar experiencia administrativa/auditoría restantes.'
 m['history'].append(dict(id='receipt1449',name='1390–1449 · recibo de alta de grupos y continuación UUID',status='Desarrollo probado/revisado; integración pendiente',evidence=ER+'/CIERRE.md'))
 admin=next(s for s in m['streams'] if s['id']=='admin');admin['children'].append(dict(id='group-creation-receipt1449',name='Grupo creado y Abrir relaciones por UUID',status='Desarrollo probado y revisado; integración pendiente',qa='QA91–93 · planned/no disponibles',evidence=ER+'/CIERRE.md',note='Recibo validado/actor y navegación explícita sin asignaciones; conserva borradores. No aumenta puntos.'))
 path.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(dict(documentsPrepared=True,progress=78,native=p.relative_to(ROOT).as_posix())))
def seal():
 initial,sources,candidate,artifacts=verify_product();native();review=read(E/'revision/CIERRE-REVISADO.json');assert review['approved'];gate=read(E/'revision/REVISION-FUENTE.json');exact(gate['sourceHashes'])
 observed=review.get('observedFilesSha256',{});assert observed;exact(observed)
 diff=subprocess.run([str(GIT),'diff','--check'],capture_output=True);assert diff.returncode==0,diff.stdout.decode(errors='replace')
 # Whole tracked diff is recorded; untracked new files are represented by the
 # evidence/source hashes and Git staging. No old manifest is presented current.
 (E/'CAMBIOS.diff').write_bytes(subprocess.check_output([str(GIT),'diff','--binary']))
 names=subprocess.check_output([str(GIT),'status','--porcelain','--untracked-files=all']).decode();newproduct=[line[3:] for line in names.splitlines() if line.startswith('?? development/frontend/src/')];assert set(newproduct)==set(NEW)
 save('VERIFICACION-FINAL.json',dict(valid=True,baseCommit=BASE,sourceCount=len(sources),artifactCount=len(artifacts),candidateManifestSha256=sha(E/'CANDIDATA1449-01.json'),independentReviewSha256=sha(E/'revision/CIERRE-REVISADO.json'),protectedGuards=len(initial['guards'])-3,actualQaOperations=0,available=dict(manual=8,rc9=90),catalogCases=93,progress=78,finalAdoption=False,publication=False,diffCheck=True,commitPrepared=True))
 rows=[sha(p)+'  '+p.relative_to(E).as_posix() for p in sorted(E.rglob('*')) if p.is_file() and p.name!='SHA256SUMS'];(E/'SHA256SUMS').write_text('\n'.join(rows)+'\n',encoding='ascii');print(json.dumps(dict(sealedFiles=len(rows),sha256=sha(E/'SHA256SUMS'))))
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['documents','seal']);a=p.parse_args();globals()[a.action]()
if __name__=='__main__':main()
