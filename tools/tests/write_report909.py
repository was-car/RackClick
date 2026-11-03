"""Write the factual closure only after real selection and guide verification."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / 'evidence/s1-20261018/sesenta-tandas-850-909'


def read(name):
    return json.loads((E / name).read_bytes())


def main():
    output = E / 'CIERRE.md'
    assert not output.exists()
    package = read('PACKAGES-01.json')
    windows = read('windows/native01/result.json')
    copy = read('qa-copy/all01/result.json')
    own = read('revision/source-recovery-activity01/result.json')
    guide = read('QA-TESTS-01.json')
    prepared = read('REAL-QA-PREPARE-01.json')
    assert package['valid'] and windows['successful'] and copy['successful'] and own['successful']
    assert guide['successful'] and guide['availability'] == dict(manual=8, rc9=78)
    assert read('revision/GATE-TECNICO.json')['approved'] and read('COORDINATOR-GO.json')['valid']
    assert read('REAL-QA-ACTIVATE-01.json')['state'] == 'committed' and read('REAL-QA-VALIDATE-01.json')['valid']
    archive = package['outputs'][0]
    source = read('INICIO.json')['sourceQaDirectory']
    text = f'''# Bloque850–909 · Windows y QA de la candidata849

El ajuste accesible de grupos ya está integrado en el paquete Windows y en una copia nueva del QA. **QA-78 disponible** mediante `INICIAR-QA-RESTAURADO.cmd`; sus pasos indican dónde entrar y cómo registrar el resultado con un lector de pantalla. El laboratorio832 y su recuperación712 se conservan completos. Tus resultados y observaciones anteriores no se sobrescriben.

**60/60 hitos internos de un recorrido de integración**, no60funciones ni60suites. Avance global **78 % aproximado, sin aumento**: integra una corrección ya contabilizada; siguen pendientes alcance funcional, Windows limpio y QA/adopción final. BaseGit155e2e11fccfbc680096c22def7cb918932f16ad.

## Aplicación, paquete y manuales

Candidata849 congelada: esquema11,20servidor+18frontend,7.108.622bytes, manifiesto SHA256 `1b40f9ceffde0503c024f0dce1fb79de02c05a21bc9cb93ad3b0d6a3d359dc09`. Servidor entero, SQL001–011, dependencias y CSS idénticos a832; sólo app.js contiene la corrección848. Cero compilaciones de aplicación/frontend en este bloque. Las pruebas completas de GUI/DOM/AX/390px/teclado/403 de849 son evidencia anterior reutilizada por identidad, no nuevas ejecuciones aquí.

Tres operadores añaden únicamente el perfil cerrado849; los seis anteriores permanecen. Stage/start/recuperación ya admitían11. Cuatro manuales actualizados antes de congelar33entradas:25operadores,4manuales, productor/locks/helper. Dos ZIP nuevos idénticos de **{archive['bytes']:,}bytes**, SHA256 **`{archive['sha256']}`**. Ubicaciones: `{archive['path']}` y `{package['outputs'][1]['path']}`. Runtime.NET10.0.12/PostgreSQL17.11-4/VC++ ya fijados; sin descargas, SDK para operar, DLL del sistema copiadas ni publicación.

## Pruebas nuevas y atribución

| Responsable | Ejecución y resultado |
|---|---|
| Autor Windows | Perfiles3/3PASS: siete perfiles, sintaxis/readiness, Stage849 y negativos de pin/historia/SQL011. `windows/profiles01/`. |
| Autor Windows | Un recorrido nativo **{windows['testsRun']}/{windows['testsRun']}PASS**, {windows['seconds']}s: New y Restore públicos desde el ZIP en ROOT/clústeres nuevos, runtime sin SDK/HTTPS/cookies, dosactores/403/grant/replay/reinicio/XLS, backup35tablas y recuperación con diferencias administrativas explícitas. Dos respuestas HTTP app.js coinciden con849 y contienen un descriptor status848; eso acredita transporte, no DOM/AX/voz. CRT/inputs intactos y procesos propios detenidos. `windows/native01/`. |
| Autor de copia | **{copy['testsRun']}/{copy['testsRun']}PASS**: cuatro contratos y un escenario PostgreSQL compartido, no múltiples suites. Fuente832 preparada847 auténtica, origen con primaria y recuperación712 deliberadamente distintos, snapshots/historia protegidos por separado; copia sólo primaria a849+recuperación832.35tablas/privados/cuentas/sesiones/recibos, cinco secretosPG nuevos, locks/readiness/puntero/fallos/retorno condicionado. `qa-copy/all01/`. |
| Revisor independiente | Un focoPG propio **{own['testsRun']}/{own['testsRun']}PASS**. Tras selección849 en fixture nueva, actividad INSERT+DELETE compensada sólo en recuperación712 del origen832 no altera snapshots pero avanza watermark; retorno denegado/recovery_required, puntero849 y ramas conservados. Su informe distingue ejecución propia de pruebas observadas. No repitió suites del autor. `revision/source-recovery-activity01/`. |
| Coordinador | Preflight quieto→GO con gate e inputs reconfirmados→prepare→activate→validate del QAreal. Sin login ni DML de aplicación en fuente; dump/snapshots readonly, sin procesos ajenos detenidos. |
| Coordinador, guía | **{guide['testsRun']}/{guide['testsRun']}PASS**, {guide['seconds']}s. Catálogo78, disponibles78restaurado/8original; identidad exacta/roles/configuración/mapping ausente fallan cerrados. Sólo mapping nuevo en el generador; lógica de conservar/importar notas original. No es ejecución manual ni voz de Wascar. |

Fuentes, logs, resultados y harness están ligados a sus hashes. Los negativos inyectados no se presentan como defectos inesperados. Fallos originales de848/849 y las evidencias847 permanecen históricos; no se convierten en pruebas nuevas. Tampoco hay nuevas ejecuciones Office/Node/Edge/dominio/builds en este bloque. La prueba Office anterior conserva su límite:87valores exactos sin fórmulas, tres tablas enDevices y otras dos hojas vacías; HTML.xls sigue distinto deXLSX.

## Laboratorio y retorno

Origen conservado: `{source}`, incluidas recuperación712, configuración/artefactos y preparado/sello847. Los adaptadores nuevos `qa_relations11_*909.py` fijan832→849, ambos11. Capturan por separado los estados de las dos bases del origen: no presuponen igualdad después del QA. La operación real copia sólo la base principal actual a un clúster independiente con dos bases nuevas11. Cuentas, claves de aplicación, sesiones y permisos exactos; cinco secretosPG nuevos sólo en destino. Ningún migrate/bootstrap/recover-admin durante esa copia.

Nueva copia seleccionada: `{prepared['candidateDirectory']}`. La URLloopback se conserva. Preview/readiness y paradas confirmadas preceden al puntero atómico; validación estática posterior identifica849 y sus hashes exactos. Aplicación/PG propios detenidos al cierre. No se modifican ni se sobrescriben bases existentes. Retorno exige ausencia de actividad en fuente y ambas ramas nuevas; también bloquea actividad compensada en cualquier base protegida. Si hay actividad, conservar/recovery_required, no prometer recuperación automática de trabajo posterior.

El Restore administrativo Windows es distinto: crea administrador/roles/TLS nuevos y revoca sesiones copiadas, con diferencias explícitas verificadas sobre35tablas. La copiaQA preserva sesiones y privilegios de aplicación. No intercambiar los dos procedimientos.

## QA para Wascar

Ejecuta `INICIAR-QA-RESTAURADO.cmd` en esteWindows y abre su guía; usa el archivo privado de acceso. QA-78 indica Usuarios→Grupos y permisos→Relaciones de grupos, selectores, UUID y cambios de tipo/idioma. Necesita tu lector habitual: si no lo utilizas, anota variante no realizada y Bloqueado. Ninguna prueba automática de este bloque acredita pronunciación o número de anuncios de Narrador/NVDA/JAWS.

Primeros77casos completos exactos. EnQA-78 sólo cambian feature y primera introducción de disponibilidad; otros pasos/expected iguales. Listas heredadas añaden849 únicamente donde estaba832; todas las parejas anteriores se conservan. Nuevo gate exclusivo849 y roles/configuración antes de disponibilidad. El test848 evoluciona de faseplanned a par cerrado, con fuente anterior archivada y negativos nuevos; no se asignan Pass manuales. Observaciones permanecen en el navegador/importación y pueden exportarse como copiaJSON.

## Límites y siguiente paso

Paquete interno y revisión favorable no son adopción. Quedan formatos/PDF/herramientas/paletas/accesibilidad/aceptaciónEN-DE-ES, Dosen pasante/eléctrico/undo general/admin visual y bloque Windows final: servicio/identidad/PKI/DNS/renovación, Windows limpio/otro equipo/CRT elevado/licencias, recuperación integral/retención/manual y QA/adopción de Wascar. No servidor finalR3, SQLite, publicación o datos reales/secretos en evidencia.

Plan60 y mapa actualizados con aportes18/22/14/14/9/1 y pesos20/25/15/15/15/10 intactos. La verificación final y adenda independiente preceden al diff/SHA256SUMS nuevo y commit local. No hay agentes continuando después del cierre de la sesión.
'''
    output.write_text(text, encoding='utf-8')
    print(json.dumps(dict(report=output.relative_to(ROOT).as_posix(), progress=78, internalMilestones=60, newQaAvailable='QA-78')))


if __name__ == '__main__':
    main()
