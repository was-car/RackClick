"""Write the closing account only after its observed outcomes are available."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-713-772'
def read(p):return json.loads((E/p).read_bytes())
def main():
    out=E/'CIERRE.md'
    if out.exists():raise SystemExit('Preserve report')
    native=read('windows/native02/result.json');composite=read('windows/WRAPPER-COMPOSITE.json');transition=read('qa-transition/all01/result.json');own=read('revision/source-activity01/result.json');qa=read('QA-TESTS-01.json');package=read('PACKAGES-02.json')
    assert native['successful'] and composite['valid'] and composite['compositeComplete'] and transition['successful'] and own['successful'] and qa['successful']
    assert read('REAL-QA-VALIDATE-01.json')['valid'] and read('COORDINATOR-GO.json')['valid']
    s=f'''# Cierre713–772 — integración Windows y QA11

18.10.2026. Completados60hitos internos del [plan](../../../docs/PLAN-SESENTA-TANDAS-713-772.json), no60módulos/suites. **Avance global aproximado78%, sin aumento** por integrar una capacidad ya contabilizada. Aportes18/22/14/14/9/1 y pesos20/25/15/15/15/10 intactos. No aceptación de Wascar ni porcentaje de pruebas/créditos/calendario.

La candidata712 FINAL02 con idioma/tema personales se integra en el perfil cerrado de distribución, Stage, readiness, instalación y recuperación de esquema11. Se conservan los perfiles337/397/532 de9 y592 de10. Aplicación/interfaz se reutilizan byte a byte: **cero compilaciones nuevas**; SQL001–010, dependencias fijadas, CSS, RC9 adoptada y Click-Click intactos. [Contrato](../../../docs/INTEGRACION-ESQUEMA11-WINDOWS-QA-S1.md).

## Resultado nuevo y atribución

Entorno: Windows11/PowerShell5.1, PostgreSQL17.11-4 y runtime.NET10.0.12 del content transportado. Python3.12/SDK10.0.401/Node24.21.0 siguen siendo herramientas de desarrollo locales; el operador instalado no los requiere. No se instalaron ni cambiaron versiones.

| Responsable / evidencia nueva | Resultado y alcance |
|---|---|
| Implementador Windows, [contratos profiles03](windows/profiles03/result.json) | 3/3PASS: cinco perfiles cerrados en productor/lector, SQL/readiness11, Stage real20+18 y rechazos. |
| Coordinador, [paquetes02](PACKAGES-02.json) / [fuentes33](SOURCE-FREEZE-OPERATORS-02.json) | DosZIP nuevos idénticos de{package['outputs'][0]['bytes']:,}bytes, SHA256 `{package['outputs'][0]['sha256']}`.25operadores+4manuales y entradas de productor congelados. |
| Implementador Windows, [native02](windows/native02/result.json) | {native['testsRun']}/{native['testsRun']}PASS, {native['seconds']}s. New11 desdeZIP trasladado, runtime sinSDK, HTTPS/loginUnicode, escritura/otra sesión, preferencias personales de dos actores/lector, permisos, recibos/fence, reinicio, backup, Restore inferior desdecontent y CLIrecover-admin11 REAL.35tablas comparadas con cambios administrativos explícitos; sesiones copiadas revocadas, propietario original conserva preferencias y administrador nuevo no las hereda. Origen/secretos/TLS intactos y retorno al origen probado. Backup10+Stage11 rechazado en otro parcial nuevo antes del CLI. |
| Implementador Windows, [wrapper compuesto](windows/WRAPPER-COMPOSITE.json) | Install-RackClickOfflineBundle -ModeRestore11 terminó exit0 en otro ROOT nuevo, con recibo schema2/CLI11/35tablas/HTTPS/readiness/cuentas. El escenario01 cerró FAIL por la comparación final de un DTO público con un registro interno; se conserva. Un foco RESTANTE PASS sobre ese despliegue comprueba la proyección correcta del fence y el cierre, sin reinstalar/restaurar otra vez. Atribución compuesta explícita; no se presenta01 como PASS. La cookie copiada rechazada por HTTP corresponde a native02; el wrapper comprueba sesiones revocadas antes del login. |
| Implementador copiaQA, [all01](qa-transition/all01/result.json) / [informe](qa-transition/INFORME.md) | {transition['testsRun']}/{transition['testsRun']}PASS: cuatro contratos y UNAfixtureWindows/PG compartida ({transition['cases'][-1]['elapsedSeconds']}s en el caso nativo). Candidata11/recuperación10, copia/selección/retorno, biblioteca privada+compartida/sesiones, identidad/PID/locks/puertos/autovacuum/puntero/actividad compensada. Sin QAreal. |
| Revisor independiente, [source-activity01](revision/source-activity01/result.json) | Su propia prueba1/1PASS, {own['elapsedSeconds']}s: selección quieta, actividad netacero sólo en recovery10, datos iguales pero watermark avanzado bloquea rollback, ramas/puntero conservados. Fuentes/distribuciones exactas y apps/PG detenidos. No modificó producto ni repitió suites completas. |
| Revisor independiente, [GATE técnico](revision/GATE-TECNICO.json) | Revisión estática de código/contrato/manuales, contraste de resultados anteriores OBSERVADOS y fuentes finales; ejecución propia anterior separada. Favorable sin bloqueantes antes del GO operacional. |
| Coordinador, [GO](COORDINATOR-GO.json) y REAL-QA-*.json | Copia/selección real en directorio y clúster NUEVOS, sólo tras paquete/fixtures/revisión y origen quieto. Sin login ni DML de aplicación en QAreal; migración sólo de la candidata nueva. |
| Coordinador, [guías](QA-TESTS-01.json) | {qa['testsRun']}/{qa['testsRun']}PASS, guías regeneradas:74casos disponibles en restaurado y8original. NuevosQA72–74 habilitados por snapshot compatible. Los71casos anteriores son idénticos; sólo la introducción de disponibilidad cambia en72–74. Notas/resultados de Wascar no se escriben. |

Los logs históricos no son ejecuciones de este bloque. No se volvieron a ejecutar Domain76, Node16 ni Edge funcional de653–712; sus evidencias originales permanecen como tales. Todas las nuevas fixtures son independientes y sus procesos propios quedan detenidos. El gate técnico queda inmutable tras GO; la adenda de revisión del cierre se guarda aparte.

## Correcciones y evidencia de fallos

profiles01 conserva fallos de arnés (elección del manifiesto532 provisional equivocado, normalización de código de salida de PowerShell -Command y expectativa incorrecta de rechazo). profiles02 corrigió esas expectativas; no se convierte su fallo en PASS.

**P2 real encontrado por native01:** Invoke-StageIntegrity aún aceptaba sólo18/19archivos del servidor. El ZIP01 verificaba38archivos pero la instalación se rechazó antes de crear clúster/base. Se conserva ese ZIP, su freeze y su [resultado fallido](windows/native01/result.json), con entradas exactas y procesos detenidos. Se corrigió únicamente la guarda a18/19/20, se añadió foco Stage real (profiles03), se construyeron dosZIP02 nuevos y native02 pasó en otra fixture. Ninguna recompilación de aplicación ni manipulación de la evidencia anterior.

La revisión del wrapper coordinador añadió comparación de todos los sourceInputHashes de preflight justo antes de prepare, además de cfg/puntero/quiet, para rechazar cambios privados entre GO y preparación. No cambia el motor, aplicación niZIP; sus fuentes quedan ligadas al gate.

El fallo de arnés wrapper01 comparaba el status público de cancelación (cinco campos) con el resultado interno persistido (siete, incluidos kind/operationId). Se conserva el fallo, su fuente exacta y prueba de recuperación completada antes de esa aserción. La corrección es sólo la proyección esperada; un foco restante nuevo consulta el despliegue propio recuperado y confirma el protocolo y cierre. No altera producto ni repite instalación/restore; el compuesto enlaza ambas evidencias y sus límites.

Un primer comprobador de metadatos del compuesto exigía calls vacío y no admitió el único comando Stop del foco restante. Se conserva COMPOSITE-CHECK-FAIL01.json; se corrigió sólo esa clasificación del agregador. No hubo otra ejecución nativa ni nuevos New/Restore por esa corrección.

El revisor conservó también la fuente y resumen del primer fallo de su generador del recibo técnico (ruta de un auxiliar equivocada). Corrigió sólo ese generador; no repitió pruebas funcionales ni modificó producto. El GATE final queda ligado al GO por SHA256.

Git diff --check detecta un espacio final en la línea31 del log bruto profiles01/tests.log. Se conserva su byte original como evidencia de fallo; sólo ese archivo se excluye del control de whitespace. Las fuentes y demás documentos/evidencias sí pasan ese control. CAMBIOS.patch conserva también el diff exacto y se excluye únicamente de ese control tras generarlo.

## Datos y retorno de QA

Origen592/esquema10 conservado. Candidata712/schema11 en otro clúster con dos bases:35tablas de candidata y33de recuperación10. En candidata,32tablas anteriores distintas de schema_migration idénticas; historial conserva diez filas previas y añade sólo11; dos tablas011 inicialmente vacías. Recuperación10 conserva el snapshot completo de33tablas y los binarios592. Cuatro secretosPostgreSQL nuevos y distintos; cuatro archivos privados de aplicación exactos para mantener cuentas/contraseñas/sesiones/permisos. Sin bootstrap/recover-admin ni autoconcesiones en esta copiaQA.

Watermark antes del dump y baseline después de preparación, PID/propiedad/quiet/control.lock, previewreadiness11/GUIexacta y puntero atómico con confirmación. Autovacuum normalON; no edición de postgresql.conf. Retorno sólo por puntero a origen10 intacto y ausencia demostrada de actividad en ambas ramas. Actividad compensada, identidad/puntero/secreto cambiado o incertidumbre exige recovery_required y conservar ramas. Nunca DLL10 contraDB11; después de trabajar no se promete rollback de escrituras.

QA sigue usando INICIAR-QA-RESTAURADO.cmd, misma URL/cuentas/credenciales privadas locales mediante el puntero seleccionado. Para probar idioma/tema/aislamiento/recuperación, abrir [guía restaurada](../../../GUIA-QA-RESTAURADO.html), QA72–74, con pasos de ubicación/botón/campo. No hay nuevos Pass manuales ni adopción de Wascar.

## Límites y siguiente trabajo

Ésta es una candidata interna reproducible de esquema11, ensayada en este Windows11. No acredita instalación limpia en otro equipo, servicioSCM/identidadWindowsmínima, PKIproductiva/DNS/renovación, instalación CRT elevada/reinicio3010, licencias/redistribución, recuperación integral del host o retención. Se reutilizó el CRT compatible del equipo sin modificar registro/DLLs globales. El backup restaura datos/aplicación en otro ROOT, no una imagen del host. No publicación web/GitHub.

Faltan funciones RC9/admin/Dosen/undo/formatos/herramientas/paletas y comprobaciones de accesibilidad/EN/DE/ES; los pendientes Windows/recuperación/manual final y QA/adopción. La cifra78estima alcance completo y no aumenta por repetir capacidad, contar60IDs o generarZIPs.

## Reproducir y operar

Comandos/fuentes exactos en informes de autor y SOURCE-FREEZE; usar salidas NUEVAS para no sobrescribir evidencia. Construir con `C:/Python312/python.exe -X utf8 -B tools/tests/build_offline772.py --attempt NN` sólo para un intento nuevo admitido y fuentes fijadas; no repetir01/02. El manifiesto712 FINAL02 es la entrada cerrada; no se admite un pin arbitrario.

Operación puraWindows, instalaciónNew/Restore, credenciales locales y recuperación se describen en los cuatro manuales incluidos en ZIP02, empezando por [manual del paquete](../../../docs/MANUAL-PAQUETE-WINDOWS-S1.md). El hash externo del ZIP se contrasta antes de extraer operadores; ROOT/clúster/base nuevos, nunca sobrescribir existentes. El cierre conserva diff/SHA256SUMS y revisión, sin claves/backup privado. La guía se regenera automáticamente al abrir QA; resultados/observaciones se conservan en el navegador y exportación JSON del usuario.
'''
    out.write_bytes(s.encode());print('Closing report written from observed outcomes')
if __name__=='__main__':main()
