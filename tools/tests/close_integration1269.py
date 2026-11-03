"""Record verified integration outcomes, without rewriting historical reports."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ER='evidence/s1-20261018/sesenta-tandas-1210-1269';E=ROOT/ER
def read(n):return json.loads((E/n).read_bytes())
def prepend(name,text):
 p=ROOT/name;b=p.read_bytes();first,sep,rest=b.partition(b'\n');nl=b'\r\n' if first.endswith(b'\r') else b'\n';assert b'Bloque1210' not in b[:2000];p.write_bytes(first+sep+nl+text.strip().encode('utf-8').replace(b'\n',nl)+nl+nl+rest)
def main():
 out=E/'CIERRE.md';assert not out.exists();p=read('PACKAGES-02.json');n=read('windows/native01/result.json');a=read('qa-update/run03/result.json');q=read('QA-TESTS-01.json');own=read('revision/fault02/result.json');actual=read('REAL-QA-UPDATE-01.json')
 assert p['valid'] and n['successful'] and a['successful'] and q['successful'] and own['successful'] and actual['state']=='committed' and read('REAL-QA-VALIDATE-01.json')['valid'] and read('revision/GATE-TECNICO.json')['approved'];assert q['available']==dict(manual=8,rc9=87)
 package=p['outputs'][0]
 report=f'''# Bloque1210–1269 · alta guiada integrada en Windows y QA

**QA85–87 disponibles**: ejecuta INICIAR-QA-RESTAURADO.cmd, usa su guía y credenciales privadas. En la barra izquierda pulsa **Usuarios**, cerca de la parte inferior; en **Secciones de administración** pulsa **Crear cuenta**. Tras **Crear usuario**, la tarjeta **Cuenta creada** muestra nombre y UUID y ofrece **Continuar a membresías** y **Revisar permisos efectivos**. Cada asignación requiere guardar y consultar al servidor. La guía describe ubicación/campo/botón/expected y permite tus observaciones sin sustituirlas. Si el panel de grupos ya estaba abierto, usa **Actualizar grupos**.

Sesenta hitos internos de una integración; no sesenta funciones/suites. **Global78 % aproximado, sin aumento**; pesos20/25/15/15/15/10 y puntos18/22/14/14/9/1 intactos. El alcance funcional parcial ya estaba contado; empaquetar/habilitar no cierra otro punto completo. Base Git7e86fbea9e5fa7dc188b52c6027729dc89fedbdd. Adopción final pendiente de Wascar.

## Resultado concreto

Candidata1209-01/esquema13 exacta:40 archivos,22servidor+18frontend,7.146.303bytes, manifiestoSHA256 dc79c53fe188187637972c2cad479edd1868d1942414c602de17bb4454bd153b.193fuentes exactas; cero publicacionesC#/buildsfrontend. Sóloapp.js difiere de1089; servidor/SQL/CSS/dependencias intactos. Git2.55.0.windows.5,SDK10.0.401,PostgreSQL17.11,Node24.21.0,Python3.12.3 verificados. Sin descargas/instalaciones globales/cambios de versiones fijadas.

Décimo perfil cerrado1209 en tres fuentes de productor/operadores; nueve perfiles anteriores y pines exactos. Stage/Start13 conservados.25operadores/cuatro manuales/33entradas congelados para dos ZIP finales02 idénticos de{package['bytes']}bytes, SHA256 `{package['sha256']}`. Rutas `{package['path']}` y `{p['outputs'][1]['path']}`. Son candidatos internos; no publicación ni redistribución/adopción. Avisos/licencias conservados; derechos de redistribución pendientes.

## Pruebas nuevas y atribución

| Responsable | Resultado real |
|---|---|
| Autor Windows | profiles02:3/3PASS tras restaurar CRLF original. profiles01 también3PASS, no seis casos distintos. Tres fuentes/dos arneses congelados; nueve perfiles previos exactos. |
| Autor Windows | native01:{n['testsRun']}/1PASS,{n['seconds']}s sobre **ZIP01**. New/Restore públicos desde transporte, runtime sinSDK,HTTPS/cookies/app.js1209 exacto. Alta real, UUID de recibo, sin acceso inicial, grant sin membresía insuficiente, grupoUUID entre homónimos, otra sesión lee membresía/permisos, sólo cliente concedido y403administración/escritura. Reinicio/backup/Restore13 compara39tablas con excepciones administrativas explícitas; nuevosroles/base/secretos/TLS/admin, sesiones copiadas revocadas y credenciales/propietarios originales conservados. CRT/DLLsistema/registro exactos y procesos propios detenidos. |
| Coordinador paquete | ZIP02-CLI PASS e inventario completo. COMPATIBILIDAD-DOCUMENTAL-02 demuestra40app/25ops/runtime/PG/licencias byteidénticos aZIP01; sólo cuatro manuales y bundle.json generado cambian. **No nueva ejecución New/Restore02**. |
| Autor actualizador | 5contratosPASS de run02 (esa corrida completa sigueFAIL en setupPG); clase de contratosAST exacta a03, sin repetirlos. run03:{a['testsRun']}/1PASS del único caso compuestoPG en fixture genuina1149 de5clústeres nuevos. Setup histórico reutilizado, casos históricos no ejecutados de nuevo. Datos legítimos posteriores y distintos en principal13/recuperación12 aceptados; baseline actual39+37/OIDs/historias/grants/privados y settingsPG no vacíos exactos. Lock/PGajeno rechazan; fallo quiet after_config retorna dentro de la operación; éxito→reentrada idempotente sin versión/baseline nuevos. Arranque13 y recuperación12; sesión/recibo13 sembrados antes de la operación conservados. INSERT+DELETE principal primero bloquea reentrada; recuperación después es acumulativa. Watermark global, sin atribución porDB ni afirmar dos retornos independientes. |
| Revisor independiente | fault02:1contrato PASS,{own['seconds']}s,**ceroPG/procesos**. Funciones reales de retorno/validación con runtime/metadatos/I/O controlados: marca primaria900, estados lógicos iguales y última lectura recuperación901 deniegan rewind. Configuración/selección/baseline sintéticos exactos. No ejecuta la operación completa ni valida Source13 real en ese foco; lectura/revisión y gate distinguen ese límite. |
| Coordinador QAreal | Preflight sólo metadatos,0PG; gate independiente→reconfirmación→GO→update→validate. Misma raíz/base13/recuperación12/puntero, dos campos de configuración. GET/readiness/preview y parada con comparación de datos/actividad; sin login/DML de aplicación ni migraciones/creaciónDB/roles/grants/secretos. |
| Coordinador guía | {q['testsRun']}/{q['testsRun']}PASS,{q['seconds']}s.87casos disponibles restaurado/8original;84casos completos exactos, sólo feature/introducción de85–87. Todas las parejas anteriores conservadas, nueva pareja cerrada y denegación por roles/configuración/hash incorrectos. Código de notas/importación/resultados byteexacto; sin leer/escribir resultados de Wascar. |

## Correcciones y evidencia conservada

Revisión P3: manuales01 omitían1209 en listas y una indicación de navegación era imprecisa. MANUALES-02 corrige referencia operativa, perfiles y botones reales después de terminar native01. Ambos ZIP01 se conservan; ZIP02 sólo cambia esos cuatro manuales y su inventario/id. La compatibilidad es estática y el CLI02 sí se ejecutó, sin relabelar New/Restore01 como otra ejecución. No corrección de producto ni rebuild.

PG run01 conserva4contratosPASS+1FAIL a283.165s: Source13 intentaba leer rolconfig de pg_authid, columna inexistente enPG17. Falló antes de publicar baseline/sello, preview o selección; cinco clústeres detenidos y configuración original exacta. Se corrigió la consulta: roles/membresías y settings de pg_db_role_setting se comparan privadamente. P2 independiente: el overlay ahora vincula bytes exactos del puntero a su SHA sellado, con negativo de mismoJSON/formato distinto.

run02 conserva5contratosPASS y1FAIL de setupPG a247.364s: el arnés comparaba OIDJSON con0 entero, sin alcanzar update ni baseline. Diagnóstico READONLY posterior en esa fixture confirma tipos y función real Source13.database_states antes del único Native03 nuevo; sin app/DML ni publicar baseline. Se normalizaron sólo tres aserciones de OID; la clase de los cinco contratos permanece AST idéntica. run03 es nueva ejecución del casoPG afectado con settings rol/base no vacíos; no transforma01/02 enPASS. Lifecycles de setups fallidos documentados aparte.

Se escribió un borrador para reutilizar la fixture01, con receipt sólo privado; quedó archivado **sin ejecutar**, al elegir el caso existente para evitar mantener/revisar otro arnés y reconstruir secretos. No restauró cookies ni operóPG; las cinco raíces01 se conservan. Los errores de comparaciónZIP01/02 eran expectativas del helper (docs/, y40artefactos másmanifest=41entradasapplication); fuentes/fallos preservados, comparación final corregida sin cambiar ZIP/producto.

fault01 del revisor fue ERROR de arnés: stub sin pointer_bytes/pointerSha256. Se conservan fuente/log/resultado; fault02 corrige sólo el foco. No fallo del producto ni ejecuciónPG. Su foco usa las funciones de retorno/comparadores sin cambios; la compatibilidad de fuentes distingue Source13/test del autor no ejecutados por él. La primera instantánea INICIO incluía accidentalmente archivos físicos PG; INICIO-02/GUARDAS-ALCANCE-02 retiran esa comparación antes de operar. El intento amplio permanece. Las bases se comparan por datos lógicos/historias/identidades/grants/actividad, no por hashes físicos que necesariamente cambian al arrancar. Finales de línea de operadores y ambos perfiles01/02 quedan documentados.

## QA conservado

Raíz `{actual['directory']}` intacta como identidad. Interfaz seleccionada1209, servidor1089/esquema13, principal39tablas y recuperación969/esquema12 de37tablas. Cuentas, contraseñas, sesiones, grants, secretos, OIDs y puntero conservados. Nueva versión `{actual['operationDirectory']}`; sólo artifactDirectory y bundleSha256 cambian en manual-qa.json. Se retienen los artefactos1089 de raíz, recuperación969, preparado1149 y sello exactos.20archivos estáticos de raíz exactos; siete runtime/logs archivados privadamente antes de operar y sus cambios permitidos se enumeran en verificación final. Configuración original guardada privadamente y comparada campo a campo.

Sin cambio de esquema ni nueva copia/base. Baseline actual de ambasDB capturado una sola vez. Hook qa.control sólo en worker privado para arrancarPG con autovacuum=off temporal, sin parchear validadores/procedencia/configuración permanente. Retorno privado sólo dentro de la operación fallida y con inputs/quietud/actividad conocidos; actividad compensada o incertidumbre conserva selección y recovery_required. Sin CLI de rollback posterior ni renovación de baseline al reentrar. Todos los procesos propios detenidos.

Servir app.js exacto no es nueva pruebaDOM/AX/voz. Las pruebas Edge/PG y revisiónDOM de1150–1209 conservan su atribución histórica. Sin nueva ejecuciónOffice, otroWindows/instalaciónlimpia,SCM/identidadservicio/PKIproductiva/CRT elevado/licencias aprobadas ni recuperación integralhost. Pruebas automáticas no sustituyen Pass de Wascar.

## Pendientes

Experiencia administrativa integral/relaciones/auditoría restante; compensación colaborativa más allá de ports.update; Dosen pasante/conectores/presupuestos eléctricos; herramientasRC9/PDF nativo/transferencia/accesibilidad y aceptaciónEN/DE/ES. Windows final: servicio/identidad/PKI/DNS/renovación, instalación limpia/otro equipo/CRT elevado/licencias, recuperación integral/retención/manual. QA/adopción final de Wascar. La integración1209 ya queda resuelta; no proponer repetirla como siguiente bloque.

Verificación final, adenda independiente, diff/SHA256SUMS y commit local cierran este bloque. No publicación ni agentes trabajando después de finalizar la sesión.
'''
 out.write_text(report,encoding='utf-8')
 planpath=ROOT/'docs/PLAN-SESENTA-TANDAS-1210-1269.json';plan=json.loads(planpath.read_bytes());assert plan['completed']==0
 def proof(i):
  if i==1212:return 'SOURCE-FREEZE-APP.json'
  if i==1214:return 'ALCANCE-RUNTIME-FUENTE.json'
  if i<1215:return 'INICIO-02.json'
  if i==1219:return 'windows/FUENTES-CONGELADAS.json'
  if i<1220:return 'windows/profiles02/result.json'
  if i==1224:return 'SOURCE-FREEZE-OPERATORS-02.json'
  if i<1225:return 'MANUALES-02.json'
  if i<1227:return 'PACKAGES-02.json'
  if i<1240:return 'windows/native01/result.json'
  if i<1252:return 'qa-update/RESUMEN-AUTOR.json'
  if i==1252:return 'revision/fault02/result.json'
  if i<1255:return 'revision/GATE-TECNICO.json'
  if i==1255:return 'REAL-QA-PREFLIGHT-01.json'
  if i==1256:return 'COORDINATOR-GO.json'
  if i<1259:return 'REAL-QA-UPDATE-01.json'
  if i==1259:return 'REAL-QA-VALIDATE-01.json'
  if i<1263:return 'QA-MATRIX-1269.json'
  if i==1263:return 'QA-TESTS-01.json'
  return 'CIERRE.md'
 for b in plan['batches']:
  name=proof(b['id']);assert (E/name).is_file();b.update(status='verified',evidence=ER+'/'+name,independentEvidence=ER+'/revision/GATE-TECNICO.json')
 plan.update(completed=60,finalProgress=78);planpath.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 summary=f'''**Bloque1210–1269 cerrado ·18.10.2026: alta guiada integrada en Windows y el mismo QA13; global78 % aproximado sin aumento.** Candidata1209 exacta,193fuentes/40artefactos;0builds/descargas/cambios de versiones. Décimo perfil cerrado,25operadores/cuatro manuales y dos ZIP02 idénticos. New/Restore01 nativos y compatibilidad documental02 distinguidos; cinco contratos y un compuestoPG final tras corregir SQL/P2, revisión adversarial propia sinPG/gate antes del GO. Fallos/intentos originales conservados.

**QA85–87 disponibles:** INICIAR-QA-RESTAURADO.cmd→Usuarios→Crear cuenta; Cuenta creada→Continuar a membresías/Revisar permisos efectivos.87restaurado/8original disponibles,84guiones/resultados anteriores conservados. Misma raíz/base13/recuperación96912/OIDs/cuentas/sesiones/grants/secretos/puntero; sólo artifactDirectory+bundleSha256. Preparado1149/sello/artifacts exactos, sin migración/login/DML de aplicación en QA. Runtimes propios detenidos. No nuevaGUI/voz/Office/otroWindows/SCM/PKI productiva ni adopción. [Contrato](INTEGRACION-ALTA-GUIADA-WINDOWS-QA-S1.md), [60hitos](PLAN-SESENTA-TANDAS-1210-1269.json), [pruebas y límites](../{ER}/CIERRE.md). Continúan funciones/operaciónWindows final/QA/adopción de Wascar. Registros siguientes históricos.'''
 for name in ['docs/CONTINUIDAD-CODEX.md','docs/INICIO-IMPLEMENTACION-S1.md','docs/PROGRESO-GLOBAL.md']:prepend(name,summary)
 short=f'''**Bloque1210–1269 vigente.** Alta guiada1209 integrada en décimo perfil Windows y el mismoQA13, servidor1089 exacto. QA85–87 disponibles:87restaurado/8original,84guiones/resultados previos intactos. New/Restore01+compatibilidad documental02 y actualizadorPG/revisión independiente registrados; misma base/recuperación12/puntero/cuentas.0builds, global78 % aproximado; adopción pendiente. [Contrato](INTEGRACION-ALTA-GUIADA-WINDOWS-QA-S1.md), [evidencias](../{ER}/CIERRE.md). Registros siguientes históricos.'''
 for name in ['docs/BRIEFING-MAESTRO.md','docs/ACEPTACION.md','docs/ESTADO-ACEPTACION-S1.md','docs/MAPA-RC9-R3.md','docs/UX-ADMINISTRACION-ARBOL.md','docs/QA-COLABORACION-Y-RESTAURACION.md','docs/GUI-CONTINUACION-ALTA-USUARIO-S1.md']:prepend(name,short)
 for name in ['development/server/README.md','development/frontend/README.md']:prepend(name,short.replace('](INTEGRACION-','](../../docs/INTEGRACION-').replace('](../evidence/','](../../evidence/'))
 prepend('CHANGELOG.md',f'## 18.10.2026 · Bloque1210–1269 · Alta guiada Windows/QA\n\n- Décimo perfil1209, dos ZIP02 reproducibles, cero builds. New/Restore01 y compatibilidad documental02 explícitos.\n- Actualizador13 conserva raíz/base/OIDs/grants/cuentas/sesiones/puntero; cambia sólo dos campos de artefactos, sin migraciones. SQL de rolesPG17/puntero exacto corregidos;5contratos+1PG final y revisión independiente, GO previo a operaciónreal.\n- QA85–87 disponibles:87+8casos;84guiones y resultados conservados.60hitos internos/global78 % sin aumento. [Informe]({ER}/CIERRE.md).')
 path=ROOT/'docs/MAPA-ENTREGA.json';m=json.loads(path.read_bytes());assert m['progress']==78 and [s['points'] for s in m['streams']]==[18,22,14,14,9,1]
 m.update(revision='2026-10-18-sesenta1210-1269',snapshot='Alta guiada1209 integrada Windows/QA13 sobre mismo servidor1089/datos/puntero.87casos/87+8disponibles;global78 % estimado.',currentBatch=dict(count=60,completed=60,ledger='docs/PLAN-SESENTA-TANDAS-1210-1269.json',evidence=ER+'/CIERRE.md'))
 tree=next(n for s in m['streams'] if s['id']=='admin' for n in s['children'] if n['id']=='admin-tree');tree['note']='Continuación Cuenta creada→Membresías→Permisos integrada Windows/QA1209;QA85–87disponibles. Experiencia administrativa integral/relaciones/aceptación pendientes.'
 leaf=next(n for n in tree['children'] if n['id']=='guided-user-creation');leaf.update(status='Probado y revisado · integrado Windows/QA13',qa='QA85–87 disponibles restaurado1209',evidence=ER+'/CIERRE.md')
 m['nextMilestones']=[v for v in m['nextMilestones'] if not v.startswith('Integrar candidata1209')];m['history'].append(dict(id='h1210-1269',name='1210–1269 · Alta guiada Windows/QA13',status='Probado y revisado',note='60hitos internos,0builds.87+8casos,QA85–87disponibles. MismoQA13/recuperación12/datos/puntero;78 % sin aumento.'))
 path.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(completed=60,progress=78,qaFrontendRevision=1209,serverRevision=1089,available=87)))
if __name__=='__main__':main()
