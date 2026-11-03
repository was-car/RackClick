"""Close continuity only after corrected Windows/QA12 and guide gates pass."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ER='evidence/s1-20261018/sesenta-tandas-970-1029';E=ROOT/ER

def read(name):return json.loads((E/name).read_bytes())
def prepend(name,text):
    path=ROOT/name;b=path.read_bytes();first,sep,rest=b.partition(b'\n');nl=b'\r\n' if first.endswith(b'\r') else b'\n'
    assert b'Bloque970' not in b[:1400]
    path.write_bytes(first+sep+nl+text.strip().encode().replace(b'\n',nl)+nl+nl+rest)

def main():
    out=E/'CIERRE.md';assert not out.exists()
    package=read('PACKAGES-02.json');native=read('windows/native02/result.json');copy=read('qa-copy/RESUMEN-AUTOR.json')
    own=read('revision/target-palette-activity01/result.json');guide=read('QA-TESTS-01.json');prepared=read('REAL-QA-PREPARE-01.json')
    assert package['valid'] and native['successful'] and copy['successful'] and own['successful'] and guide['successful']
    assert read('revision/GATE-TECNICO.json')['approved'] and read('COORDINATOR-GO.json')['valid']
    assert read('REAL-QA-ACTIVATE-01.json')['state']=='committed' and read('REAL-QA-VALIDATE-01.json')['valid']
    assert guide['availability']==dict(manual=8,rc9=81)
    archive=package['outputs'][0];source=read('REAL-QA-PREFLIGHT-01.json')['sourceDirectory']
    report=f'''# Bloque 970–1029 · paleta personal en Windows y QA12

**QA-79 a QA-81 disponibles** con INICIAR-QA-RESTAURADO.cmd y sus credenciales privadas. En Infraestructura/Clientes, arriba a la derecha junto a idioma/tema, pulsa **Paleta**. Elige colores y **Guardar**; ↺/Restablecer todo requieren Guardar. Otra sesión de la misma cuenta recupera la paleta; otra cuenta conserva la suya. Los colores explícitos de puerto/cable y estados mantienen prioridad. Tu laboratorio849, recuperación832 y resultados anteriores se conservan.

Se cierran 60 hitos internos de esta integración. No equivalen a 60 funciones ni a 60 suites. Avance global aproximado: **78 %**, sin aumento; aportes 18/22/14/14/9/1 y pesos 20/25/15/15/15/10 intactos. QA y adopción final de Wascar pendientes. Base Git:962948f48543429d22cc806d5951ea94e2c90dc2.

## Correcciones y candidata final

El plan inicial era reutilizar969 sin compilar. Las pruebas nuevas encontraron P2 de readiness (Start sólo admitía 9–11) y P1 real de recuperación administrativa: RecoveryAdministrator.RequiredSchemaVersion seguía en11 frente a LatestVersion12. New, paletas, reinicio y backup de 37 tablas pasaron en native01, pero Restore falló; esa ejecución de 203,344 segundos no se presenta como Pass. profiles01 y native01 se conservan con fuentes, logs y parada de procesos confirmada. También se corrigió el CLI del adaptador: no puede informar esquema11 al seleccionar969/12.

FIX02 cambia una sola línea C# de11 a12, con una publicación del servidor y cero compilaciones del frontend. Candidata969-FIX02: 39 archivos (21+18), 7.037.914 bytes, pin `b589609154fed1567106ef0865972155258f0f5474128c73076f4697d43b8bda`. Las otras 180 fuentes, frontend, SQL001–012 y dependencias son exactas. Cambian cuatro DLL/PDB por la corrección y los metadatos de procedencia Git. La lectura PE independiente confirma que los 177 métodos del dominio y sus firmas/referencias son iguales. El primer auxiliar rechazó ese delta inesperado después de compilar con exit0; se conserva su evidencia. La finalización no volvió a compilar.

Se actualizaron cinco fuentes del productor y operadores. Stage/Start corregidos se conservan en FIX02 sin otros cambios. Ocho perfiles cerrados: siete anteriores y969-FIX02; el pin969 inicial fallido deja de aceptarse como perfil final. Se congelaron 25 operadores y cuatro manuales antes de cada intento. ZIP02a/b idénticos: **{archive['bytes']} bytes**, SHA256 `{archive['sha256']}`. Archivos `{archive['path']}` y `{package['outputs'][1]['path']}`. ZIP01 y manifiestos969 previos son históricos. Runtime/SDK/PostgreSQL/Node/VC++ fijados siguen iguales. No hubo descargas, instalaciones, copias de DLL del sistema ni publicación externa.

## Pruebas nuevas y atribución

| Responsable | Evidencia y resultado real |
|---|---|
| Autor Windows | profiles03: 3/3 PASS, nuevo pin, Stage21, esquema12, readiness y negativos; profiles01 FAIL y02 PASS anteriores preservados. |
| Autor Windows | native02: {native['testsRun']}/{native['testsRun']} PASS en {native['seconds']} s. New/Restore públicos desde ZIP02, runtime sin SDK, HTTPS/cookies, paletas de lector sin clientes y de dos actores, GET/replay/noop/reset/conflictos/fences, 011/XLS/reinicio/37 tablas, permisos y recuperación administrativa12 con sesiones revocadas. CRT y entradas exactos; procesos propios detenidos. |
| Autor copia | Resultado final propio: {copy['testsRun']}/5 PASS: cuatro contratos y un foco PostgreSQL con fixture nuevo sobre FIX02. El foco comprueba prepare→activate→rollback y los negativos pendientes. Las ramas anteriores conservan su ejecución y atribución original. run01 falló por un hook sintético que confundía el listener web del destino con propiedad del origen. run02 quedó ERROR en el retorno explícito: se confirmó la parada y el fallo cerrado. El log PostgreSQL muestra error487 al reservar memoria de un proceso hijo, posible contribuyente cuya relación causal con la excepción final no puede demostrarse; hubo comprobaciones posteriores y el journal no preservó la clase/mensaje original. No se conoce la lectura exacta que falló. El compuesto original no se presenta como Pass ni como repetido íntegramente. Módulos, política y baselines se mantienen; sólo cambia el arnés y su diagnóstico privado. |
| Revisor independiente | own01: {own['testsRun']} comprobaciones (1 PostgreSQL+1 CLI); ejecución PostgreSQL sobre la candidata inicial, claramente histórica. INSERT+DELETE en una tabla nueva no cambia los 37 digests, pero avanza el watermark y bloquea el retorno. La comparación AST/fuentes/IL acota su aplicabilidad a las guardias sin cambios en FIX02; no se atribuye esa corrida a los nuevos bytes. El gate exige además Windows02 y la copia final realmente ejecutados sobre FIX02. |
| Coordinador | Preflight sin actividad→GO con gates/entradas reconfirmados→prepare→activate→validate del QA real, sin login/DML de aplicación en origen. Sólo dump/snapshots de lectura de la fuente; SQL012 únicamente en la nueva primaria. |
| Coordinador de guía | {guide['testsRun']}/{guide['testsRun']} PASS en {guide['seconds']} s; catálogo81, disponibles81 restaurado/8 original. Par exacto, roles/configuración y ausencia de mapping fallan cerrados; lógica de notas/importación exacta. |

La revisión estática adicional SERVER-IL-FIX02 compara 4.933 métodos: sólo cambia el operando 11→12 del inicializador de RecoveryAdministrator; los otros 4.932 mantienen IL, firmas, variables locales y control de excepciones. Esta lectura de ensamblados no es una nueva ejecución del servidor.

Servir app.js exacto desde New/Restore acredita transporte y la ruta de paleta; no nueva ejecución DOM/AX/Edge/voz. La GUI/EN/DE/ES/390px/Tab de910–969 se reutiliza como evidencia histórica por identidad del frontend. No Office nuevo ni interoperabilidad universal. El guion F12 Offline es una instrucción manual, no una operación F12 ejecutada por estas pruebas. Los informes y fallos anteriores no se convierten en ejecuciones nuevas.

## Copia real, archivos y retorno

Origen conservado `{source}`: principal849/11 y recuperación832/11, preparado/sello909, cuentas/sesiones/permisos/privados/artefactos. Se protege por separado el snapshot y la historia de cada base; no se supone igualdad después del QA. Los originales de siete archivos transitorios de runtime/logs se archivaron privadamente antes de la actividad operativa. Configuraciones, credenciales, preparado y artefactos no reciben excepción.

Destino seleccionado `{prepared['candidateDirectory']}`: raíz/clúster y dos bases nuevas. Sólo la nueva primaria migra012: 35 tablas previas exactas salvo historia, más dos tablas personales vacías; 37 en total. La recuperación849/11 mantiene sus 35 tablas e historia exactas. No se ejecuta bootstrap/recover-admin en esta copia. Cinco secretos PostgreSQL nuevos; claves de aplicación y privilegios conservados. Preview/readiness, parada confirmada y selección atómica verificados; aplicación y PostgreSQL propios quedan detenidos.

El retorno requiere ausencia de actividad en fuente/destino/recuperaciones, incluida actividad compensada. Si hay actividad o resultado incierto, se conservan las ramas con recovery_required, sin sobrescribir ni fingir reconciliación. Nunca ejecutar binarios11 sobre12. Restore Windows es otro recorrido: crea administrador/roles/TLS nuevos y revoca sesiones copiadas; sus diferencias administrativas se comparan explícitamente sobre 37 tablas.

## QA y pendientes

Los primeros 78 guiones completos son exactos. En QA-79 a QA-81 sólo cambian feature e introducción de disponibilidad; los pasos restantes y el resultado esperado son iguales. Las listas heredadas añaden la pareja FIX02 únicamente donde estaba849 y conservan las anteriores. Nuevo gate exclusivo FIX02 y roles/configuración. Los tests de fase969/848 evolucionan a este estado con los originales archivados. No se leen ni escriben resultados de Wascar ni se asignan Pass manuales.

El paquete interno y la revisión favorable no son servidor final ni adopción. Quedan paleta por parejas de categorías, formatos/PDF/herramientas/accesibilidad/aceptación EN/DE/ES, Dosen pasante/undo general/administración visual y Windows final: servicio/identidad/PKI/DNS/renovación, instalación limpia/otro equipo/CRT elevado/licencias, recuperación integral/retención/manual y QA/adopción. El siguiente bloque debe abordar uno de esos pendientes funcionales u operativos.

La verificación final y la adenda preceden al diff, SHA256SUMS nuevo y commit local. No hay publicación ni agentes continuando después de cerrar sesión.
'''
    out.write_text(report,encoding='utf-8')
    plan_path=ROOT/'docs/PLAN-SESENTA-TANDAS-970-1029.json';plan=json.loads(plan_path.read_bytes());assert plan['completed']==0 and len(plan['batches'])==60
    def proof(i):
        if i<975:return 'INICIO.json'
        if i<980:return 'windows/profiles03/result.json'
        if i<984:return 'MANUALES-02.json'
        if i==984:return 'SOURCE-FREEZE-OPERATORS-02.json'
        if i<987:return 'PACKAGES-02.json'
        if i<1003:return 'windows/native02/result.json'
        if i<1014:return 'qa-copy/RESUMEN-AUTOR.json'
        if i==1014:return 'revision/target-palette-activity01/result.json'
        if i==1015:return 'revision/GATE-TECNICO.json'
        if i==1016:return 'COORDINATOR-GO.json'
        if i==1017:return 'REAL-QA-PREPARE-01.json'
        if i==1018:return 'REAL-QA-ACTIVATE-01.json'
        if i==1019:return 'REAL-QA-VALIDATE-01.json'
        if i<1024:return 'QA-MATRIX-1029.json'
        if i==1024:return 'QA-TESTS-01.json'
        return 'CIERRE.md'
    for b in plan['batches']:
        name=proof(b['id']);assert (E/name).is_file();b.update(status='verified',evidence=ER+'/'+name,independentEvidence=ER+'/revision/GATE-TECNICO.json')
    plan.update(completed=60,finalProgress=78,scope='60hitos internos de integraciónWindows/QA12; P1corregido conFIX02, no60funciones/suites.')
    plan_path.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    summary='''**Bloque970–1029 cerrado ·18.10.2026: paleta personal integrada en Windows y nueva QA12; avance global aproximado: 78 %, sin aumento.** Se corrigió el P1 real de Restore12 alineando el literal de recuperación. Una publicación C#, cero compilaciones del frontend. FIX02 mantiene interfaz/SQL/dependencias y las otras 180 fuentes. Cinco fuentes del productor y operadores actualizadas, ocho perfiles, 25 operadores y cuatro manuales congelados, y dos ZIP02 idénticos. Fallos originales y compatibilidad de procedencia/guardias registrados.

New/Restore públicos, HTTPS/paletas por actor/011/XLS/reinicio/37 tablas y copia11→12 probados. Fuente849 y recuperación832 protegidas por separado; nueva969/12 con recuperación849/11, cinco secretos PostgreSQL nuevos y cuentas/sesiones/privados conservados. La revisión independiente distingue su prueba PostgreSQL histórica y la compatibilidad FIX02 de las ejecuciones finales del autor. El coordinador prepara/selecciona/valida después del GO; origen sin login/DML de aplicación. Sin nueva ejecución GUI/AX/voz/Office.

**QA-79 a QA-81 disponibles** en INICIAR-QA-RESTAURADO.cmd con guía y credenciales privadas. Catálogo81, disponibles81 restaurado/8 original. Se conservan los 78 guiones previos, los pasos restantes y los resultados de Wascar. Siguiente: paleta de grupos/formatos/herramientas/Dosen/undo/administración y Windows final/recuperación/manual/QA/adopción. [Contrato](INTEGRACION-PALETA-TIPOS-WINDOWS-QA-S1.md), [plan de60 hitos](PLAN-SESENTA-TANDAS-970-1029.json), [pruebas, fallos y límites](../evidence/s1-20261018/sesenta-tandas-970-1029/CIERRE.md). Los registros siguientes son históricos.'''
    for path in ['docs/CONTINUIDAD-CODEX.md','docs/INICIO-IMPLEMENTACION-S1.md','docs/PROGRESO-GLOBAL.md']:prepend(path,summary)
    short='''**Bloque970–1029 vigente.** Paleta personal969-FIX02/esquema12 en ZIP Windows y nueva QA. P1 de Restore12 y límites de readiness corregidos, probados y revisados. Fuente849 y recuperación832 conservadas; nueva recuperación849/11. Hay81 casos disponibles en restaurado/8 en original, incluidos QA-79 a QA-81; resultados previos intactos. Avance global aproximado: 78 %; adopción pendiente. [Contrato](INTEGRACION-PALETA-TIPOS-WINDOWS-QA-S1.md), [evidencias y límites](../evidence/s1-20261018/sesenta-tandas-970-1029/CIERRE.md). Los registros siguientes son históricos.'''
    for path in ['docs/BRIEFING-MAESTRO.md','docs/ACEPTACION.md','docs/ESTADO-ACEPTACION-S1.md','docs/MAPA-RC9-R3.md','docs/QA-COLABORACION-Y-RESTAURACION.md','docs/API-PALETA-TIPOS-PERSONAL-S1.md']:prepend(path,short)
    for path in ['development/server/README.md','development/frontend/README.md']:prepend(path,short.replace('](INTEGRACION-','](../../docs/INTEGRACION-').replace('](../evidence/','](../../evidence/'))
    prepend('CHANGELOG.md','## 18.10.2026 · Bloque970–1029 · Windows/QA12 y corrección Restore\n\n- P1 de recuperación12 y P2 de readiness/CLI corregidos; FIX02, una publicación C# y frontend exacto. Fallos y ZIP01 conservados.\n- ZIP02 New/Restore de37 tablas/paletas/011/XLS y copia11→12 probados y revisados. QA969 seleccionada con849/recuperación832 preservados.\n- QA-79 a QA-81 disponibles:81+8 casos;78 guiones previos y resultados intactos.60 hitos internos; global78 % sin aumento. Servidor final/adopción pendientes. [Informe](evidence/s1-20261018/sesenta-tandas-970-1029/CIERRE.md).')
    path=ROOT/'docs/MAPA-ENTREGA.json';m=json.loads(path.read_bytes());assert m['progress']==78 and [s['points'] for s in m['streams']]==[18,22,14,14,9,1]
    m.update(revision='2026-10-18-sesenta970-1029',snapshot='969-FIX02/esquema12 en Windows y nueva QA. P1 de Restore corregido;849/recuperación832 preservadas.81+8 casos disponibles; global78 % estimado.',currentBatch=dict(count=60,completed=60,ledger='docs/PLAN-SESENTA-TANDAS-970-1029.json',evidence=ER+'/CIERRE.md'))
    def visit(nodes):
        for n in nodes:
            if n.get('id')=='personal-port-type-palette':n.update(status='Probado y revisado · integrado Windows/QA12',qa='QA79–81 disponibles restaurado969',evidence=ER+'/CIERRE.md')
            visit(n.get('children',[]))
    visit(m['streams'])
    m['nextMilestones']=[v for v in m['nextMilestones'] if not v.startswith('Integrar candidata969/esquema12')]
    m['history'].append(dict(id='h970-1029',name='970–1029 · Paleta en Windows/QA12 y Restore FIX02',status='Probado y revisado',note='60 hitos y81+8 casos; fuente849 y recuperación832 conservadas.78 % sin aumento; QA/adopción pendiente.'))
    path.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(completed=60,progress=78,qaRevision=969,qaSchema=12,available=81)))

if __name__=='__main__':main()
