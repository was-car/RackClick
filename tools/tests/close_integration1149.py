"""Record only verified Windows/QA13 results and retain historical records."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
ER='evidence/s1-20261018/sesenta-tandas-1090-1149'
E=ROOT/ER

def read(name):return json.loads((E/name).read_bytes())

def prepend(name,text):
    path=ROOT/name;b=path.read_bytes();first,sep,rest=b.partition(b'\n');nl=b'\r\n' if first.endswith(b'\r') else b'\n'
    assert b'Bloque1090' not in b[:1700]
    path.write_bytes(first+sep+nl+text.strip().encode().replace(b'\n',nl)+nl+nl+rest)

def main():
    out=E/'CIERRE.md';assert not out.exists()
    package=read('PACKAGES-01.json');native=read('windows/native01/result.json');copy=read('qa-copy/RESUMEN-AUTOR.json')
    own=read('revision/source-recovery849-only01/result.json');guide=read('QA-TESTS-01.json');prepared=read('REAL-QA-PREPARE-01.json')
    assert package['valid'] and native['successful'] and copy['successful'] and own['successful'] and guide['successful']
    assert read('revision/GATE-TECNICO.json')['approved'] and read('COORDINATOR-GO.json')['valid']
    assert read('REAL-QA-ACTIVATE-01.json')['state']=='committed' and read('REAL-QA-VALIDATE-01.json')['valid']
    assert guide['available']==dict(manual=8,rc9=84)
    archive=package['outputs'][0];source=read('REAL-QA-PREFLIGHT-01.json')['sourceDirectory']
    report=f'''# Bloque 1090–1149 · parejas de categorías en Windows y QA13

**QA-82 a QA-84 disponibles** con INICIAR-QA-RESTAURADO.cmd y sus credenciales privadas. En español, barra izquierda **Todos los clientes**, debajo de Infraestructura; arriba a la derecha **Paleta**, dentro **Parejas de categorías**. Guardar confirma la persistencia; recargar y entrar con otra sesión de la misma cuenta debe recuperar sus elecciones. Otra cuenta mantiene las suyas. Los colores explícitos tienen prioridad; los valores personales se aplican al crear conexiones nuevas y no repintan conexiones existentes. La guía explica las pruebas de cada caso paso a paso y admite tus observaciones.

Se cierran60 hitos internos de integración, no60 funciones ni60 suites. Global aproximado **78 % sin aumento**; pesos20/25/15/15/15/10 y aportes18/22/14/14/9/1 intactos. El incremento funcional ya estaba contabilizado en el alcance parcial; empaquetarlo y habilitarlo para QA no cierra otro punto completo. Adopción final pendiente de Wascar. Base Git60868854ce40a0eda773fd1817f48f7da41aae46.

## Candidata y distribución

Se reutiliza exactamente1089-02/esquema13:40 archivos (22 servidor+18 frontend),7.133.395 bytes, manifiesto SHA256 `c8b3df5b8e0fb6c5db148b7ddca2a8064ade6b90557713fb0835cbf69bb9710c`. Las190 fuentes del producto permanecen exactas. Cero publicaciones C# y compilaciones frontend; sin descargas, instalación global de herramientas/dependencias ni cambios de versiones fijadas. New/Restore sí instalan en raíces privadas de prueba nuevas. Git2.55.0.windows.5, SDK10.0.401, PostgreSQL17.11, Node24.21.0 y Python3.12.3 verificados en Windows11; dependencias fijadas conservadas.

Cinco fuentes del productor/operadores integran el noveno perfil cerrado1089/13 y readiness13; ocho perfiles/pines anteriores conservados. Stage/verificador distinguen22+18 archivos y SQL013 sin aceptar perfiles arbitrarios.25 operadores y cuatro manuales quedaron congelados antes de empaquetar. Dos ZIP idénticos de **{archive['bytes']} bytes**, SHA256 `{archive['sha256']}`: `{archive['path']}` y `{package['outputs'][1]['path']}`. Las33 entradas del productor no cambiaron durante ni después del empaquetado. Los ZIP son candidatos internos reproducibles, sin secretos ni datos reales y sin publicación externa.

## Ejecuciones nuevas y revisión

| Responsable | Resultado y alcance real |
|---|---|
| Autor Windows | profiles01:3/3 PASS, perfil1089/13 y negativos de pin/Stage/readiness; ocho anteriores intactos. |
| Autor Windows | native01:{native['testsRun']}/{native['testsRun']} PASS en {native['seconds']}s. New/Restore públicos desde el ZIP transportado, runtime sin SDK, HTTPS/cookies, lector sin clientes, mapas012/013 separados y por actor, prioridad/replay/no recolor, conexiones por UUID, expiración single/batch antes del commit sin auditoría ni journal fantasma,011/XLS/reinicio/backup y recuperación39tablas. Restore administrativo13 y revocación de sesiones copiadas comprobados. CRT/DLL del sistema/registro exactos; procesos propios detenidos. |
| Autor copia | {copy['testsRun']}/5 PASS:4 contratos y1 compuesto PostgreSQL. Fixture nueva de5 clústeres en cadena712→832→849→969→1089, no ejecución de los casos históricos completos. Cambios legítimos y distintos en origen12 y recuperación11, incluida paleta012 no vacía por API antes de preparar, acreditan conservación del QA posterior. Prepare→activate→retorno sin actividad→activate y compatibilidad13/12. Cuatro guardias directas con INSERT+DELETE compensado y un retorno real con actividad acumulada; no cuatro retornos independientes. Todos los clústeres propios detenidos. |
| Revisor independiente | Foco PostgreSQL propio en otra fixture: sólo actividad compensada en la recuperación original849/11. Aunque el snapshot lógico vuelve a coincidir, el watermark avanza y el retorno real se deniega; selección1089/13 conservada. Los otros tres perfiles lógicos no reciben DML del foco. El watermark es conservador por clúster, no una medición exacta por base. Resultado propio, compatibilidad de fuentes y revisión técnica registrados antes del GO. |
| Coordinador | Preflight sin PG→reconfirmación de quietud/entradas→GO con9 gates, incluida compatibilidad del pretest→prepare→activate→validate del QA real. Sin login ni DML de aplicación en origen; sólo lecturas/dumps necesarios. |
| Coordinador guía | {guide['testsRun']}/{guide['testsRun']} PASS en {guide['seconds']}s.84 casos/84 disponibles restaurado y8 original;81 guiones completos exactos, cambios sólo en feature/introducción de los tres nuevos. Pareja cerrada, roles/configuración y ausencia de mapping fallan cerrados; notas/importación de resultados exactas. |

run01 de la copia falló **antes de las pruebas** por una ruta errónea en la lista de fuentes del arnés (`pg_lab_recovery.py` estaba bajo tests, pero pertenece a tools/windows):0 casos/0 PostgreSQL. Se conserva el error. Sólo se corrigió la lista del main; run02 es la suite efectiva. El foco del revisor ya había congelado el arnés anterior: conserva `sourcesUnchanged=false` y exit1 del runner por esa comparación íntegra, aunque el caso PostgreSQL pasa. COMPATIBILIDAD-PRETEST prueba por SHA y AST que sólo cambió el metadato de main, con clases/setup/métodos y cuatro módulos runtime exactos. El gate acepta expresamente esa excepción acotada, no convierte el exit1 en exit0. No se repitió PostgreSQL por este cambio de metadatos ni se ocultó el delta.

Servir app.js exacto desde New/Restore acredita transporte, no una nueva ejecución DOM/AX/Edge/voz. Las pruebas GUI del bloque1030–1089 conservan su atribución histórica. No se afirma Office nuevo, instalación limpia en otro Windows, SCM/identidad de servicio, PKI productiva, instalación elevada de CRT ni recuperación integral del host. La prueba F12/Offline de la guía es manual y opcional, no una acción F12 ejecutada aquí. Ninguna prueba automática equivale al Pass de Wascar.

Adenda de codificación: la revisión detectó un P2 del auxiliar de guía: read_text sin encoding interpretó UTF-8 como cp1252 al regenerar su clase de pruebas. Los47 casos pasaban, pero no cubrían ese delta de constantes fuera de la clase. Se conservaron el auxiliar corrupto y el47/47 original, se restauraron prefijo/sufijo por bytes y se fijó encoding UTF-8. El foco QA-FOCO-02 pasa3/3, incluida igualdad AST fuera de la clase y bytes de constantes. Catálogo/HTML/resultados de usuario no afectados. Verificación y diff02 posteriores; sin repetir PostgreSQL ni builds.

## Nueva copia seleccionada y protección de datos

Origen `{source}` conservado con principal969/12 de37 tablas y recuperación849/11 de35 tablas; sus datos e historias se protegen por separado. Configuraciones, cuentas, sesiones, grants, credenciales privadas, preparado1029/sello y artefactos conservados. Los21 archivos estáticos de raíz y todas las entradas históricas se verifican; los7 runtime/logs originales se archivaron privadamente antes de operar y sus cambios operativos se enumeran en VERIFICACION-FINAL. No se afirma que los28 archivos originales sean byteidénticos después de arrancar PostgreSQL.

Destino seleccionado `{prepared['candidateDirectory']}`: clúster/raíz y dos bases independientes. Sólo la nueva primaria migra013:37 tablas previas exactas salvo historia y2 nuevas vacías,39 en total. Nueva recuperación969/12 con37 tablas e historia exactas. No bootstrap/recover-admin en esta copia:5 secretos PostgreSQL nuevos y cuentas/sesiones/claves/permisos de aplicación conservados. La recuperación original849/11 sigue intacta en el origen; no se confunde con la nueva969/12. Preview/readiness, quietud, selección atómica y validación final comprobados; runtimes propios detenidos.

El retorno requiere ausencia de actividad en ambas primarias y recuperaciones, incluso INSERT+DELETE compensado. Ante actividad o incertidumbre se conservan las ramas y recovery_required; no se sobrescribe ni se renuevan baselines para fingir quietud. El watermark conservador por clúster puede bloquear por actividad en otra base del mismo clúster. Restore Windows es otro recorrido: crea administrador/roles/secretos/TLS nuevos y revoca sesiones copiadas; sus diferencias se comparan explícitamente sobre39 tablas.

## Continuidad y pendientes

Las listas heredadas conservan sus parejas anteriores y añaden1089 donde antes aceptaban969; userCategoryColorsBuilds sólo acepta1089-02. Los81 casos previos se conservan completos; QA82–84 mantienen todos los pasos restantes y expected. Ambas guías se regeneraron sin leer/escribir resultados de Wascar. Usa los perfiles de navegador separados indicados en la guía para dos cuentas simultáneas.

Quedan formatos/PDF/herramientas, accesibilidad/aceptación completa EN/DE/ES, Dosen pasante/compensación general/administración visual y Windows final: servicio/identidad/PKI/DNS/renovación, instalación limpia/otro equipo/CRT elevado/licencias, recuperación integral/retención/manual y QA/adopción. El siguiente trabajo funcional debe elegirse entre esos pendientes; la integración1089/13 ya queda cerrada.

Verificación final y adenda independiente preceden al diff/SHA256SUMS nuevos y commit local. No publicación ni agentes trabajando después del cierre.
'''
    out.write_text(report,encoding='utf-8')
    path=ROOT/'docs/PLAN-SESENTA-TANDAS-1090-1149.json';plan=json.loads(path.read_bytes());assert plan['completed']==0 and len(plan['batches'])==60
    def proof(i):
        if i==1092:return 'SOURCE-FREEZE-APP.json'
        if i==1094:return 'ALCANCE-RUNTIME-FUENTE.json'
        if i==1099:return 'windows/FUENTES-CONGELADAS.json'
        if i==1104:return 'SOURCE-FREEZE-OPERATORS-01.json'
        if i<1095:return 'INICIO.json'
        if i<1100:return 'windows/profiles01/result.json'
        if i<1105:return 'MANUALES-02.json'
        if i<1107:return 'PACKAGES-01.json'
        if i<1120:return 'windows/native01/result.json'
        if i<1132:return 'qa-copy/RESUMEN-AUTOR.json'
        if i==1132:return 'revision/source-recovery849-only01/result.json'
        if i<1135:return 'revision/GATE-TECNICO.json'
        if i<1137:return 'COORDINATOR-GO.json'
        if i==1137:return 'REAL-QA-PREPARE-01.json'
        if i==1138:return 'REAL-QA-ACTIVATE-01.json'
        if i==1139:return 'REAL-QA-VALIDATE-01.json'
        if i<1143:return 'QA-MATRIX-1149.json'
        if i==1143:return 'QA-TESTS-01.json'
        return 'CIERRE.md'
    for b in plan['batches']:
        name=proof(b['id']);assert (E/name).is_file();b.update(status='verified',evidence=ER+'/'+name,independentEvidence=ER+'/revision/GATE-TECNICO.json')
    plan.update(completed=60,finalProgress=78,scope='60hitos internos de integraciónWindows/QA13; no60funciones/suites,0builds producto.')
    path.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    summary='''**Bloque1090–1149 cerrado ·18.10.2026: parejas de categorías en Windows y nueva QA13; avance global aproximado78 %, sin aumento.** Candidata1089-02 exacta,190 fuentes y40 artefactos conservados; cero compilaciones, sin instalar herramientas globales ni cambiar versiones fijadas. Nueve perfiles cerrados,25 operadores/cuatro manuales congelados y dos ZIP idénticos. New/Restore públicos en raíces privadas nuevas,39tablas, mapas012/013 por actor, defaults y expiración single/batch probados en Windows. Copia y revisión PostgreSQL independientes en fixtures nuevas; pretest fallido0casos/0PG y compatibilidad de fuentes preservados.

QA real969/12 y recuperación849/11 conservados por separado; nueva1089/13 con recuperación969/12,5 secretosPG nuevos y cuentas/sesiones/permisos/privados intactos. Preparada/seleccionada/validada tras gate independiente y GO; sin login/DML de aplicación en origen. **QA82–84 disponibles:** INICIAR-QA-RESTAURADO.cmd → Todos los clientes → Paleta → Parejas de categorías.84 casos disponibles restaurado/8 original;81 guiones y resultados anteriores conservados. Runtimes propios detenidos.

Sin nueva ejecución DOM/AX/voz/Office ni instalación en otro Windows/SCM/PKI productiva. Pendientes formatos/PDF/herramientas/accesibilidad/idiomas, Dosen/undo general/admin visual y Windows final/recuperación/manual/QA/adopción. [Contrato](INTEGRACION-PALETA-CATEGORIAS-WINDOWS-QA-S1.md), [60 hitos](PLAN-SESENTA-TANDAS-1090-1149.json), [pruebas y límites](../evidence/s1-20261018/sesenta-tandas-1090-1149/CIERRE.md). Los registros siguientes son históricos.'''
    for name in ['docs/CONTINUIDAD-CODEX.md','docs/INICIO-IMPLEMENTACION-S1.md','docs/PROGRESO-GLOBAL.md']:prepend(name,summary)
    short='''**Bloque1090–1149 vigente.** Parejas personales de categorías1089-02/esquema13 integradas en Windows y nuevaQA, con revisión independiente. New/Restore39tablas y copia12→13 probados; fuente969/12 con recuperación849/11 conservada y nueva recuperación969/12. QA82–84 disponibles:84restaurado/8original;81 guiones y resultados previos intactos.0builds producto, global78 % aproximado sin aumento; adopción pendiente. [Contrato](INTEGRACION-PALETA-CATEGORIAS-WINDOWS-QA-S1.md), [evidencias](../evidence/s1-20261018/sesenta-tandas-1090-1149/CIERRE.md). Los registros siguientes son históricos.'''
    for name in ['docs/BRIEFING-MAESTRO.md','docs/ACEPTACION.md','docs/ESTADO-ACEPTACION-S1.md','docs/MAPA-RC9-R3.md','docs/QA-COLABORACION-Y-RESTAURACION.md']:prepend(name,short)
    for name in ['development/server/README.md','development/frontend/README.md']:prepend(name,short.replace('](INTEGRACION-','](../../docs/INTEGRACION-').replace('](../evidence/','](../../evidence/'))
    prepend('CHANGELOG.md','## 18.10.2026 · Bloque1090–1149 · Windows/QA13\n\n- Candidata1089-02 exacta en noveno perfil cerrado;25 operadores/cuatro manuales congelados y dos ZIP idénticos.0builds producto.\n- New/Restore39tablas y copia12→13 probados/revisados. QA1089 seleccionada conservando969/recuperación849 y resultados.\n- QA82–84 disponibles:84+8 casos,81 guiones exactos.60 hitos internos; global78 % sin aumento. Servidor final/adopción pendientes. [Informe](evidence/s1-20261018/sesenta-tandas-1090-1149/CIERRE.md).')
    path=ROOT/'docs/MAPA-ENTREGA.json';m=json.loads(path.read_bytes());assert m['progress']==78 and [s['points'] for s in m['streams']]==[18,22,14,14,9,1]
    m.update(revision='2026-10-18-sesenta1090-1149',snapshot='1089-02/esquema13 en Windows/nuevaQA;969/12 y recuperación849/11 conservadas.84+8casos disponibles; global78 % estimado.',currentBatch=dict(count=60,completed=60,ledger='docs/PLAN-SESENTA-TANDAS-1090-1149.json',evidence=ER+'/CIERRE.md'))
    def visit(nodes):
        for n in nodes:
            if n.get('id')=='personal-category-pair-palette':n.update(status='Probado y revisado · integrado Windows/QA13',qa='QA82–84 disponibles restaurado1089',evidence=ER+'/CIERRE.md',note='28 parejas/10 colores por actor; prioridad explícita al crear conexiones, sin recolor de existentes. Windows New/Restore39 y copia QA12→13 probados/revisados;0builds producto.')
            visit(n.get('children',[]))
    visit(m['streams'])
    m['nextMilestones']=[v for v in m['nextMilestones'] if not v.startswith('Integrar candidata1089')]
    m['history'].append(dict(id='h1090-1149',name='1090–1149 · Parejas en Windows/QA13',status='Probado y revisado',note='60 hitos;84+8 casos,QA82–84disponibles.969/12+recuperación849/11 conservadas.78 % sin aumento; QA/adopción pendientes.'))
    path.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(completed=60,progress=78,qaRevision=1089,qaSchema=13,available=84)))

if __name__=='__main__':main()
