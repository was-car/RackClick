# Pruebas Windows del fundamento

**Tanda39,16.10.2026:** `C:/Python312/python.exe -B development/server/tests/test_admin_audit_gui.py --output evidence/s1-NUEVO/audit-gui` usa tres bases nuevas y perfiles Edge headless propios; `--case 1|2|3` permite el grupo afectado. Implementador3/3,31,032s y revisión3/3,31,578s. Grupo1 igualdad SQL después de logins;2 negativos CDP explícitos;3 revocación API real/idiomas/captura. No usar QA real como fixture.32 unidades nuevas y52 regresiones de permisos correctas; [cierre39](../../../evidence/s1-20261016/admin-auditoria-gui-39/CIERRE.md).

**Tanda38,16.10.2026:** `C:/Python312/python.exe -B development/server/tests/test_admin_audit.py --evidence evidence/s1-NUEVO/admin-audit` ejecuta cuatro casos nuevos y dos regresiones `test_audit_` heredadas. `--case` repetido selecciona nombres exactos; usar destino nuevo. No selecciona laboratorios QA reales. Baseline38:6/6 correctas,38,049s; revisión distinta sólo cuatro nuevas:4/4,30,997s. [Contrato](../../../docs/API-ADMIN-AUDITORIA-S1.md), [evidencia](../../../evidence/s1-20261016/admin-auditoria-api-38/CIERRE.md). Siempre cargar Use-Toolchain antes de restore/build; no cambiar SDK/locks.

Herramientas internas, no instalador de producto. Ejecutar desde raíz tras `tools/windows/Initialize-Toolchain.ps1` y dot-source `tools/windows/Use-Toolchain.ps1`. SDK fijado global.json, PostgreSQL nativo aislado. No requiere Python para el futuro producto; estos arneses de desarrollo sí usan Python3.12.

```powershell
. ./tools/windows/Use-Toolchain.ps1
dotnet msbuild development/server/RackClick.sln -t:Restore,Build -p:Configuration=Release -p:RestoreLockedMode=true -p:RestoreSources=https://api.nuget.org/v3/index.json -m:1 -nr:false -v:minimal
dotnet development/server/tests/RackClick.Domain.Tests/bin/Release/net10.0/RackClick.Domain.Tests.dll
python -B development/server/tests/test_http_failclosed.py "$env:DOTNET_ROOT/dotnet.exe"
python -B development/server/tests/test_postgres.py
python -B development/server/tests/run_frontend_smoke.py --output evidence/s1-NUEVO/frontend
```

El frontend debe estar construido para el último comando; consultar development/frontend/README.md. Cada corrida nativa genera un cluster y bases nuevas en `.local/labs/<label>-<UUID>`, con ACL restringida al usuario/SYSTEM, puerto loopback libre, SCRAM y roles de migración/runtime independientes. No usa instalaciones existentes, no borra bases ni reutiliza directorios. Conserva datos/logs privados; para cerrar usa pg_ctl exclusivamente sobre su propio directorio y cierra procesos propios. Fixtures usan secretos generados localmente, nunca argumentos CLI ni informes.

`pg_support.py` centraliza el aislamiento. `test_postgres.py` añade metadatos/logs públicos saneados y controla finalización. Los triggers de fallo y cambios de grupos/sesiones pertenecen solo a fixtures: prueban garantías del fundamento, no APIs administrativas todavía ausentes.

`reproduce_d007.py` recibe una DLL baseline explícita y una ruta nueva de salida; compilar baseline en copia de Git2edcf3e, nunca revertir árbol compartido. Conserva evidencia antes/después PostgreSQL51/100 caracteres suplementarios. Las primeras corridas fallidas del arnés/API quedan conservadas junto con la verificada.

No compilar sobre Release mientras otros tests lo ejecutan en Windows. Coordinar cierre y repetir pruebas pertinentes cuando cambie la DLL. No transformar 29+8 Linux históricos en resultados Windows; usar archivos nuevos con entorno real.

Runner conjunto: `python -B tools/windows/Verify-Windows.py --scope foundation` desde raíz. `--scope inventory` añade las suites de inventario y su recorrido browser cuando estén implementados; `--preflight-only` comprueba únicamente versiones/entradas, no ejecuta pruebas. Cada ejecución crea una carpeta nueva bajo `evidence/`, registra comandos/retornos/entorno/hashes y falla si cambian fuentes durante la corrida. Un directorio anterior nunca se sobrescribe. No ejecutar mientras se edita o compila en paralelo. No se presenta el preflight como validación completa.

`run_frontend_smoke.py --scenario browser-inventory.mjs --output evidence/NUEVA-CARPETA` permite otro escenario dentro de frontend/tests. A partir de esta revisión guarda hashes de DLL, escenario y archivos dist antes/después, finalización del laboratorio y fallos de limpieza. No se añaden hashes retrospectivos a corridas históricas que no los capturaron.

## Permisos y espera de locks · tanda 17

`C:/Python312/python.exe -B development/server/tests/test_admin_permission_races.py --evidence evidence/NUEVA-CARPETA` ejecuta solo las tres nuevas pruebas. Con `--regression` ejecuta solo los cinco casos existentes de miembros de grupos de clientes. Requiere usuario Windows normal por ACL privadas; crea un clúster/base nuevos y no usa QA manual/restaurado. La sincronización verifica pg_blocking_pids y el lock Systemhaus; el polling no constituye evidencia temporal por sí mismo. Revocación por SQL del fixture, no API de grants. Directorios de salida nuevos, sin sobrescribir resultados anteriores.

## Concesiones por API · tanda 18

`C:/Python312/python.exe -B development/server/tests/test_admin_grants.py --evidence evidence/NUEVA-CARPETA` ejecuta los seis casos aislados. `--case test_grants_persistence_union_read_write_revocation` selecciona únicamente ese caso para reproducir un fallo afectado. Fuente/DLL capturadas antes/después en runner final; usa carpetas nuevas, usuario normal Windows y herramientas fijadas. No toca QA manual/restaurado. Evidencia de build y errores originales en evidence/s1-20261004/admin-concesiones-api-18/.

## Estado de cuentas por API · tanda20

`C:/Python312/python.exe -B development/server/tests/test_admin_user_state.py --evidence evidence/NUEVA-CARPETA` ejecuta seis casos contra PostgreSQL real en un laboratorio nuevo. `--case NOMBRE_DEL_METODO` selecciona un fallo afectado (nombres en el archivo). Requiere usuario Windows normal por ACL privadas, herramientas fijadas y DLL compilada antes de congelar fuentes. Registra hashes antes/después y detiene su laboratorio; no usa QA de Wascar. Prueba sesiones/replay/último administrador, autorización/DTO, cancelación/conflictos, rollback y concurrencia HTTP con testigo de locks PostgreSQL, además de expiración durante espera. Usar directorios nuevos sin sobrescribir evidencia. Tanda20 conserva dos errores iniciales del arnés; los seis casos finales correctos corresponden a ejecución independiente, no a sumar recorridos parciales.

## Interfaz de estado de cuentas · tanda21

`C:/Python312/python.exe -B evidence/s1-20261004/admin-estado-gui-21/implementacion/run_fixture.py --output evidence/NUEVA-CARPETA` crea un laboratorio nativo nuevo y ejecuta browser-admin-state.mjs contra DLL20. Captura hashes de entradas/salidas, detiene su laboratorio y falla si cambiaron. La cuenta state-reader del fixture posee administración para entrar al formulario; no representa lector puro. Cinco recorridos, incluidos respuesta perdida/autodesactivación/reactivación por otro administrador/login nuevo y recuperación. No altera QA de Wascar. Unidades: `.local/node-v24.21.0-win-x64/node.exe --test development/frontend/tests/admin-user-state.test.mjs`. Usar usuario normal por ACL privadas, carpeta nueva y fuente congelada, sin compilar simultáneamente.

## Reset de contraseña por API · tanda22

`C:/Python312/python.exe -B development/server/tests/test_admin_user_password.py --evidence evidence/NUEVA-CARPETA` ejecuta seis casos agrupados Windows/PostgreSQL en laboratorios nuevos, sin QA de Wascar. `--case NOMBRE_DEL_METODO` selecciona uno; puede repetirse. Fuente/DLL congelados antes/después, salida nueva sin sobrescribir y laboratorio detenido. Cuenta/hash/failed_logins/locked_until/sesiones/audit/operation/revisión, Unicode/límites, permisos/headers/DTO, recuperación/cancelación/replay actual/GET histórico, rollback y carreras reales; caducidad durante espera de target/actor observada por SQL. Secretos aleatorios locales, assertions neutras, no argv/logs públicos. SDK10.0.401/PG17.11/Python3.12.3 fijados, usuario normal con ACL privada. No compilar ni editar fuente durante corridas. Histórico pg01 seisPASS anterior al P2; seis finales correctos pertenecen al revisor, no suma de parciales. Seguimiento de helper global pendiente, no corregido por este test.

## Caducidad durante locks · tanda23

`C:/Python312/python.exe -B development/server/tests/test_session_wait_expiry.py --evidence evidence/s1-20261004/sesiones-contrato-23/revision/pg-final` (desde raíz; usar una carpeta nueva por ejecución). Cuatro casos agrupados, seis rutas de espera; alta/login Unicode y negativos incluidos. Admite `--case` para selección acotada; consultar `--help`. Requiere DLL previamente compilada, PostgreSQL real y laboratorio nuevo con secretos locales. Original22:4casos/7fallos de subtests, no7pruebas independientes. Final23:4/4 independientes; no extrapolar a todos los consumidores ni reutilizar las cuentas QA. Regresión password22:6/6 ejecutada una vez por implementador. [Cierre23](../../../evidence/s1-20261004/sesiones-contrato-23/CIERRE.md).

## GUI de contraseña · tanda24

Desde raíz: `C:/Python312/python.exe -B development/server/tests/test_admin_password_gui.py --output evidence/NUEVA-CARPETA`. Requiere DLL23 congelada d0a5c957…bd4b81 y frontend24 previamente compilado43f7a19e…89ce84; no compilar simultáneamente. Cinco grupos Edge/PostgreSQL en laboratorio nuevo, secretos locales por entorno privado, cierre/hashes de entradas verificados. Unidades: `.local/node-v24.21.0-win-x64/node.exe --test development/frontend/tests/admin-user-password.test.mjs` (21). Revisión final propia21+5; no repetir o sumar como propia gui01 parcial/gui02 del implementador. No acceso a QA de Wascar. [Resultados/límites](../../../evidence/s1-20261004/admin-password-gui-24/CIERRE.md).

## Consulta y migración de sesiones · tanda26

Desde raíz: `C:/Python312/python.exe -B development/server/tests/test_admin_user_sessions.py --evidence evidence/NUEVA-CARPETA` (cuatro grupos; `--case` selecciona caso explícito). Requiere DLL26 compilada y baseline3 privada `.local/baselines/sessions-26/server/RackClick.Server.dll` SHA d0a5c957…bd4b81; baseline creada ANTES del build, no usar DLLactualcomo baseline. Copiar salidas completas de DLL23/schema3 a destino privado NUEVO, nunca sobrescribir ni migrar QA. Cluster/bases nuevos, secretos locales, procesos detenidos/hashinputs iguales. Fuente final congelada y revisión independiente4/4; una regresión6password22 del implementador sobre mismaDLL. Suite test_migrations.py expectativa1→4 actualizada, NO ejecutada aquí: requiere baseline1 independiente y su evidencia propia. [Cierre y límites](../../../evidence/s1-20261004/admin-sesiones-consulta-26/CIERRE.md).

## Revocación individual de sesión · tanda27

Desde raíz: `C:/Python312/python.exe -B development/server/tests/test_admin_session_revoke.py --evidence evidence/NUEVA-CARPETA`. Seis grupos, `--case NOMBRE` selecciona caso explícito; usar directorio nuevo. Requiere DLL27 previamente compilada/congelada, PostgreSQL17 real y secretos locales; no recompilar durante pruebas ni usar cuentas/base QA. Concurrencia, rollback audit/operation, selectividad, expiración y retirada GLOBAL tras locks observados; sin forzar ambos órdenes login/cancel. Seis finales implementación y seis independientes correctos; única regresiónconsulta26 de cuatro del implementador requiere baseline3 privada completa indicada arriba. [Resultados y límites](../../../evidence/s1-20261004/admin-sesiones-revocacion-27/CIERRE.md). Errores previos del arnés/build y pg01 5/6 preservados; no sumarlos como suites finales.

## Backup/restore3 y4 · tanda28

Desde raíz: `C:/Python312/python.exe -B development/server/tests/test_schema_recovery.py --evidence evidence/NUEVA-CARPETA`. Tres grupos nativos, `--case NOMBRE` acota uno. Requiere DLL27 congelada5e55ba46…63cf4a y baseline3 completa DLL23 d0a5c957…bd4b81 en `.local/baselines/sessions-26/server`, PostgreSQL17.11 y Python3.12.3. No reconstruir/no usar QA. Dos suites3/3 implementación/revisión correctas, sin otras regresiones generales. Copias y logs SQL privados; candidato fallido conservado, procesos propios detenidos. [Procedimiento](../../../docs/RECUPERACION-SCHEMA4-LAB-S1.md), [resultado28](../../../evidence/s1-20261004/recuperacion-schema4-28/CIERRE.md). Interrupción/grants-fail, updater real, otra máquina/cluster y política productiva de sesiones NO probadas.

## GUI de sesiones · tanda29

Desde raíz: `C:/Python312/python.exe -B development/server/tests/test_admin_sessions_gui.py --output evidence/NUEVA-CARPETA`. Requiere DLL27 congelada5e55ba46…63cf4a y bundle29 c9072f1f…dd5ea3, Edge nativo, Node24/Python3.12/PostgreSQL17.11; NO build concurrente ni QA existente. Seis grupos finales en lab nuevo detenido. Unidades: `.local/node-v24.21.0-win-x64/node.exe --test development/frontend/tests/admin-user-sessions.test.mjs` (31). Implementador única regresión21password; revisor reproduce31+6, no esa regresión. [Cierre y límites](../../../evidence/s1-20261004/admin-sesiones-gui-29/CIERRE.md). Comparación journal hermanos estática, corrupción real ejecutada; no matrizstorage universal.

## Preparar copia de QA3→4 · tanda30

Desde raíz: `C:/Python312/python.exe -B development/server/tests/test_qa_schema_candidate.py --evidence evidence/NUEVA-CARPETA`. Tres grupos Windows/PostgreSQL reales; `--case NOMBRE` selecciona uno. Requiere baseline3 completa `.local/baselines/sessions-26/server`, frontend24 completo `.local/baselines/schema-copy-30/frontend` y DLL27/frontend29 congelados, sin recompilar. Sólo fuentes sintéticas nuevas, secretos PostgreSQL nuevos y puntero del fixture privado; nunca ambos QA reales. Comprueba invariantes de todas las tablas, bytes de cuatro archivos privados, cuentas/cookies/permisos, independencia, rechazos previos y rollback de migración fallida. Reabrir fuente compatible no demuestra switch/rollback operativo: [contrato/límites](../../../docs/ACTUALIZACION-QA-SCHEMA4-S1.md). Logs SQL y dumps bajo `.local`, evidencia pública sin contraseñas/config privada.

## Coordinador de cambio3→4 · tanda31

Desde raíz: `C:/Python312/python.exe -B development/server/tests/test_qa_schema_switch.py --evidence evidence/NUEVA-CARPETA`. Sólo tres test_switch_* (no heredados30/Foundation); `--case NOMBRE` selecciona uno. Baselines3/23/24 y candidata4/27/29 completos congelados como30, PostgreSQL17.11/SDK10.0.401, sin rebuild. Supervisores reales con Job y Qa-Local.serve, pointers privados de fixture. Revisor3/3 final correcto; implementador1/3 previos y2 afectado83,463s, NO suite conjunta nueva trasfix; ERRORteardown preservado y cleanup posterior separado. [Cierre/límites31](../../../evidence/s1-20261005/qa-schema-switch-31/CIERRE.md). Snapshot final NOhistorialDML; negativo compensado y guardia32 pendientes antesQAreal. No suitesAPI/GUI generales ni cortesWindows/disco/pg_ctl real ejecutados.

## Guardia de actividad · tanda32

Desde raíz: `C:/Python312/python.exe -B development/server/tests/test_qa_activity_guard.py --evidence evidence/NUEVA-CARPETA`. Tres test_activity_* nuevos únicamente; `--case NOMBRE` selecciona uno, no ejecutar heredados por accidente. Requiere baselines/candidata congelados como31, PostgreSQL17.11/.NET10.0.401, sin rebuild. Reproduce login/logout real con filas iguales y SQL INSERT/DELETE con COMMIT compensado; controles de sólo lectura/restart limpio y medición incierta. Todos homes/pointers/supervisores privados de fixtures nuevos, ningún QAreal. [Diseño](../../../docs/GUARDIA-ACTIVIDAD-QA-S1.md). Reproducción fallidaOLD31 debe conservarse separada; no sumarla como prueba superada.

## Permisos efectivos administrativos · tanda35

Desde raíz: `C:/Python312/python.exe -B development/server/tests/test_admin_effective_permissions.py --evidence evidence/NUEVA-CARPETA`. Sólo cuatro test_effective_* nuevos; `--case NOMBRE` selecciona uno sin heredar suites. SDK10.0.401/PostgreSQL17.11 fijados. Bases, roles y secretos NUEVOS; no QA real. Autorización GLOBAL/ámbito, composición exacta compartida con /me, cambios entre peticiones/inactivos/DTO/ETag/OpenAPI y caducidad observada durante lock real del actor. GET no cambia filas. Foreign Systemhaus sólo en fixture nuevo tras retirar índice singleton, nunca esquema de producto; texto legacy sintético sólo preservación de proyección. [Contrato y límites](../../../docs/API-ADMIN-PERMISOS-EFECTIVOS-S1.md).

Regresión acotada del cálculo extraído: `C:/Python312/python.exe -B development/server/tests/test_postgres.py --filter test_me_effective_permissions_only_readable_customers_and_own_sources --evidence evidence/OTRA-CARPETA`. No ejecutar toda la suite por herencia ni atribuir resultados históricos como nuevos. QA17 y anteriores siguen en copia congelada27/29, GUI de permisos efectivos pendiente.
