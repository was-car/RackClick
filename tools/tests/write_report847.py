"""Write the factual report only once all implementation and actual-selection gates passed."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/quince-tandas-833-847'
def read(p):return json.loads((E/p).read_bytes())
def main():
    out=E/'CIERRE.md';assert not out.exists()
    start=read('INICIO.json');package=read('PACKAGES-01.json');native=read('windows/native01/result.json');copy=read('qa-copy/all01/result.json');own=read('revision/recovery-activity01/result.json');guide=read('QA-TESTS-01.json');prepared=read('REAL-QA-PREPARE-01.json');selected=read('REAL-QA-VALIDATE-01.json')
    assert native['successful'] and copy['successful'] and own['successful'] and guide['successful'] and selected['valid']
    assert read('revision/GATE-TECNICO.json')['valid'] and read('COORDINATOR-GO.json')['valid']
    ziprow=package['outputs'][0]
    text=f'''# Cierre833–847 · Windows y QA del XLS RC9

18.10.2026, S1 autorizado, Windows11. BaseGit `{start['baseCommit']}`. **15/15 hitos internos**; no15módulos/sprints/suites. Avance global **78/100 estimado, sin aumento**: se integra un formato ya contado, no completa la paridad/instalación/adopción pendientes. Pesos20/25/15/15/15/10 y aportes18/22/14/14/9/1 intactos.

## Resultado

Candidata832-02 integrada en perfilWindows cerrado832, ZIPnuevo reproducible y **nuevaQA restaurada832/schema11 seleccionada**. Aplicación/GUI832 congeladas de773–832 reutilizadas sin recompilar; SQL001–011, dependencias, CSS, RC9 y Click-Click intactos. Los perfiles337/397/532/592/712 y sus ZIP/manifiestos/evidencias se conservan; no publicación/GitHub ni adopción automática.

Nuevo perfil en tres archivos: `tools/package_offline_bundle.py`, `tools/windows/Test-ServerDistribution.ps1`, `tools/windows/RackClick.OfflineBundle.ps1`. Cantidades20servidor+18frontend/7.108.267bytes, pin832-02 exacto `511c097bafd5baf7590da15287a0dbd53bb5eb8e2fde33931c940b2885e7dfc5`. Stage, start y recuperación ya admitían11 y no necesitaron cambios. Sin pin/esquema arbitrarios ni ampliar límites por arrastre de otra versión.

Cuatro manuales de operación/construcción/paquete/recuperación actualizados y congelados con25operadores/productor/locks/buildhelper:33fuentes. Dos ZIP nuevos idénticos, **{ziprow['bytes']:,}bytes**, SHA256 **`{ziprow['sha256']}`**. Ubicaciones privadas: `{package['outputs'][0]['path']}` y `{package['outputs'][1]['path']}`. `SOURCE-FREEZE-OPERATORS-01.json` y `PACKAGES-01.json` ligan inputs, inventarios y resultados. Dependencias oficiales ya fijadas:runtime.NET10.0.12, PostgreSQL17.11, VC++ compatible reutilizado, sinSDK/Node/Python/Git para operar. No nuevas descargas/instalaciones de herramientas en este bloque.

## Pruebas nuevas y atribución

| Responsable / foco | Ejecución y resultado |
|---|---|
| Autor Windows `windows847` | Perfiles3/3PASS,14.172s: productor/lector/sintaxis/readiness,38hashes y Stage832, perfiles anteriores, negativos de pin/historia/SQL011. `windows/profiles01/`. |
| Autor Windows, recorrido nativo único | **{native['testsRun']}/{native['testsRun']}PASS**,{native['seconds']}s total. `test_offline_rc9_excel847.py --archive <ZIP847> --archive-sha <SHA> --evidence .../windows/native01`. Entradas públicas **Install-RackClickOfflineBundle.ps1 -Mode New y -Mode Restore** extraídas del ZIP, en dosROOT/clústeres nuevos. HTTPS/SecureCookie, rechazoTLSsinconfianza, doscuentas/lectura/exportación explícita,403antesgrant,412/replayoriginal, descargaAPI delXLS auténtico conUUID/grupo/tipo yDosen/finales, reinicio y35tablas/backup/Restore/recibos/fecha/bytes exactos. Sesiones copiadas revocadas y administrador nuevo sólo enRestore administrativo; permisos originales persistidos yotrosactores aislados. CRTDLLs/registrox64sin cambios; procesos propios detenidos/cleanupErrorsvacío. |
| Autor del motor `qa_copy847` | **{copy['testsRun']}/{copy['testsRun']}PASS**:4contratos cerrados y1recorrido nativo compartido con6focos, no seis suites. `test_qa_xls11_update847.py --group all --evidence .../qa-copy/all01`. Source712→832/11→11,35tablas/historia/privados/sesiones/recibos/preferencias exactos,5secretosPG nuevos(4DB+inicializador), selección/retorno/readiness/locks/PID y fallos inyectados/actividadcompensada. Fixture sintética se inicializó antes de copiar; el adaptador no ejecuta migrate/bootstrap/recover-admin. Fuente/harness congelados enSOURCE-FREEZE.json; auxiliares históricos y Qa-Local.py intactos. |
| Revisor independiente | **1/1PASS**,{own['elapsedSeconds']}s según su metadata. Único foco propio `revision/recovery-activity01/`: INSERT+DELETE comprometidos sólo en recuperación712 mantienen ambas35tablas iguales pero avanzanwatermark. Retorno→recovery_required, puntero832 yramas conservados; fuente original exacta, app/PG detenidos. No ejecutó por sí mismo las pruebas Windows/copia del autor ni casosGUI/Office previos. |
| Coordinador | Preflight quieto del QAreal, GO operacional tras paquete+native+fixture+revisión favorable, prepare→activate→validate de nueva copia real. Sin login ni DML de aplicación en origen, sin detener procesos ajenos, sin notas de Wascar leídas/escritas. |
| Coordinador, guía | **{guide['testsRun']}/{guide['testsRun']}PASS**,{guide['seconds']}s. Ambasguías exactas,77disponibles restaurado/8original, gates de parejacompleta/roles/configuración fallan cerrados; importación/notas conservadas por el código existente. Es metadata/guion, no ejecución manual de Wascar. |

Las pruebas reutilizan helpers de lifecycle/snapshot/parsers, sin ejecutar métodos históricos por herencia. No hubo una nueva compilación de aplicación/frontend, suite de dominio/Node/Edge/Office en847. Las validaciones773–832 permanecen históricas y atribuidas: Excel16.0build20430 conservó87valores exactos sin fórmulas; creó tres pestañas pero las tres tablas están enDevices y otrasdos vacías. No prometer tres hojas pobladas, todas las versiones de Office/LibreOffice ni ausencia de aviso HTML.xls. Formato HTML.xls distinto del XLSXtabular.

## Copia y selección del QAreal

Motor nuevo `qa_xls11_source847.py`, `qa_xls11_candidate847.py`, `qa_xls11_switch847.py`, `qa_xls11_update847.py`; motores772 y anteriores intactos. Origen712 completo `{start['sourceQaDirectory']}` conservado, incluida su recuperación histórica; la operación toma sólo su base principal11. Dump/restore privado a clúster y dosbases nuevos11, una para832 y otra recuperación712 separada. Los35conjuntos lógicos/historia11 exactos en ambasnuevasbases; nuevasidentidades/contraseñasPG distintas entre sí y del origen. Cuatroprivados de aplicación y cuentas/sesiones/contraseñas/permisos exactos; ninguna concesión nueva.

Nueva copia seleccionada: `{prepared['candidateDirectory']}`. URLde QA restaurado conservada (loopback del mismoWindows). Puntero atómico a832 traspreview/readiness11 yconfirmación; aplicación/PG propios detenidos al cierre. Validación estática posterior distingue selectedRevision832 de schema11compartido por ambasversiones. Arranque normal mantieneautovacuumON; inicios operativos usan opción temporaloff y no editanpostgresql.conf. Retorno condicionado a ausencia de actividad en todaslasramas, incluida compensada; si hay actividad/inconsistencia, conservar/recovery_required, no prometer rollback de trabajo de Wascar.

`REAL-QA-PREFLIGHT-01.json`, `COORDINATOR-GO.json`, `REAL-QA-PREPARE-01.json`, `REAL-QA-ACTIVATE-01.json`, `REAL-QA-VALIDATE-01.json` dan las referencias y flags reales. Los52archivos protegidos del origen siguen idénticos y los manifiestos/ZIPanteriores se conservan. No contiene dump/secretos/datos de usuarios en el paquete ni en estaevidencia pública; todo secreto se genera/guarda sólo local privado.

## QA que puede realizar Wascar

**QA75–77 disponibles ahora**. Ejecutar `INICIAR-QA-RESTAURADO.cmd` en esteWindows; usar `GUIA-QA-RESTAURADO.html` y su archivo privado de acceso. La guía explica ubicación exacta de Consultar inventario→XLS(HTMLRC9), selector/UUID visible, generar/confirmar/descargar, texto Unicode y extremos de sala, roles/segundasesión/recuperación/borradores. Elegir Pass/NotPass/Bloqueado y guardar copia de resultados. No hace falta repetir todo ni probar la candidata de desarrollo por separado.

`QA-MATRIX-847.json`:77casos, nuevasparejas heredadas justificadas por fuentes conservadas y prueba nativa. Sólo cambiaron seisintros de disponibilidad:75–77 dejan su aviso temporal712,60–62 corrigen texto obsoletoQA185. Pasosrestantes/expected de esosseis y otras71definiciones completos iguales. El test normaliza explícitamente esas3introslegadas antes delhashhistórico; fuenteanterior archivada. Resultados/notas de Wascar no se sobrescriben: permanecen en el navegador/importación, con aviso de guion actualizado cuando cambiósu hash. No nuevosPass automáticos ni aceptación manual atribuida.

## Límites y siguiente paso

Global78/100 sin aumento: integración de un formato ya contado, no puntos por15IDs/ZIP/suites/documentos. No se instalaSCM/identidadWindows/PKIproductiva, no Windowslimpio/otroequipo/CRT elevado ni aprobación de redistribución/licencias. No se acredita recuperaciónintegral delhost/retención ni manualfinal del producto completo. Adopción final sóloWascar.

Continuar formatos/PDF/herramientas/paletas/accesibilidad/EN-DE-ES, Dosenpasante ycombinaciones eléctricas, undo general/admin visual y bloque final Windows/recuperación/manual/QAadopción. La fuente y recuperación se conservan, sin borrar bases/servicios/carpetas ajenos. Pruebas fallidas históricas no se convierten en nuevasPASS; fallos inyectados de este recorrido son negativos esperados con journal conservado. Nuevos SHA256SUMS ydiff se sellan con revisión ymetadatos independientes antes de commitlocal; nada publicado.
'''
    out.write_bytes(text.encode());print(json.dumps(dict(report=out.relative_to(ROOT).as_posix(),progress=78,selectedRevision=832,availableRestoredCases=77)))
if __name__=='__main__':main()
