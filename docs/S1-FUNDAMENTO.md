# S1 — fundamento Windows y PostgreSQL

Inicio 28.09.2026. R0 contrastado por Wascar; desarrollo autorizado. EN CURSO, no candidata ni adopción.

## Trazabilidad

El chat de continuidad revisó el ZIP recepcion-20260928-091834. Se preservan informes y auxiliar histórico. Verificador mantenido nuevo: tools/verify_hashes.py, con pruebas negativas.

El hash 8f2027e1e485e5467d785e1b959e27c164b9983772c48fc6d2561918dc73da0a corresponde a la entrada ABRIR-DOCUMENTACION.html del ZIP RC9. Aplicación: 63a60c4b52360211e1ae90b2e38541dc76bf372007219868e7c203af9223ea96. Se verificaron bytes. Causa de alerta: identificación equivocada del HTML. Documentación es primera entrada/fila de manifiesto, pero no se conoce el comando antiguo y no se afirma que seleccionó automáticamente la primera.

Git local baseline 2edcf3e9985203d081c3b9d455c0ee0e65b0a888, sin remoto. .local/ herramientas/laboratorios/secretos excluidos. Manifiesto raíz recibido describe recepción, no fuentes S1 editadas.

## Bloques internos y criterios

1. Git/SDK exacto10.0.401/PostgreSQL17 parche fijado/Node npm oficiales; URLs, hashes/firma, versiones y scripts repetibles. No modificar locks silenciosamente.
2. Laboratorio nuevo: rutas/puerto propios, loopback, SCRAM, secretos aleatorios locales, roles inicialización/ejecución separados. Fallar ante destino existente, sin borrar instalaciones ajenas.
3. D-007: reproducir en copia baseline y unificar bootstrap/login. 1–100 escalares Unicode, trim y minúsculas invariantes existentes, sin controles/UTF-16 inválido ni NFC nueva silenciosa. Nombres de recursos distintos, sin traducción/casefold automático.
4. Build y tests Windows nuevos; PostgreSQL positivo de login/persistencia/ámbitos/grupos/sesiones/CSRF/conflictos/replay/concurrencia/rollback/auditoría. Registrar fallos y correcciones.
5. API: /api/v1/auth/login y /auth/logout; /me identidad/CSRF/permisos efectivos; OpenAPI comprobado; autorización siempre servidor.
6. RC9 login/Systemhaus/clientes: commit antes de éxito, recarga y otra sesión. Componentes/assets aprobados, sin inventario maestro localStorage. Continuar jerarquía/inventario, UUIDs, Dosen/dispositivos finales, lotes IDs+grupo/tipo.
7. Revisión independiente, luego paridad/administración/operación hasta una candidata completa Windows con manual y recuperación.

## Primera tanda y propiedad

Coordinador: documentos/Git, laboratorio/arnés PostgreSQL y HTTP. s1_windows: tools/windows y toolchain.lock.json/herramientas oficiales. s1_backend: dominio/API/auth/DTO/tests dominio. s1_hashes: tools/verify_hashes.py y tests. s1_frontend: development/frontend y prueba browser aislada. QA/seguridad posteriores separados de implementación.

## Fuentes y evidencia

Cluster nuevo según [initdb PostgreSQL17](https://www.postgresql.org/docs/17/app-initdb.html), control de instancia según [pg_ctl](https://www.postgresql.org/docs/17/app-pg-ctl.html), autenticación [SCRAM/password](https://www.postgresql.org/docs/17/auth-password.html). Binarios/URLs/hashes en development/toolchain.lock.json y evidence/s1-20260928/windows.

Evidencia nueva evidence/s1-20260928/. Históricos Linux y recepciones intactos. 25 R3 Windows de R0 no equivalen S1.

## Fundamento comprobado en Windows, 28.09.2026

Entorno: Windows 11 Pro 10.0.26200 x64, PowerShell 5.1, Git 2.55.0.windows.5, SDK **10.0.401**, PostgreSQL **17.11** EDB4, Node **24.21.0**, npm **11.19.0**, Python 3.12.3 para arneses y Edge 154.0.4258.37. Herramientas locales sin servicios ni PATH global. URLs, hashes, firmas y tres rechazos de preparación constan en `evidence/s1-20260928/windows/INFORME-HERRAMIENTAS.md`. NuGet se restauró con lock y fuente oficial explícita. Versiones recibidas SDK/Npgsql/esbuild preservadas.

| Comprobación nueva | Resultado y evidencia |
|---|---|
| Release y dominio | Compilación correcta; **48/48** casos. `backend/build-windows-native-fixes.log`, `backend/domain-tests-windows.log`. |
| HTTP de fallo sin DB | **8/8** Windows, rutas auth canónicas. `foundation/http-failclosed-windows.log`. |
| D-007 antes/después contra PostgreSQL | **4/4** verificaciones: creación con 51 y 100 caracteres suplementarios funcionaba en baseline pero login daba 401; con política común ambos login dan 200 y `/me` conserva identidad. `foundation/d007-native-verified.json`. |
| QA PostgreSQL independiente | **31/31**, 37 bases nuevas en cluster propio detenido. Persistencia, reinicio, segunda cuenta, grupos/ámbitos, sesiones, CSRF, conflictos, replay/concurrencia, rollback/auditoría, rol runtime sin DDL, OpenAPI y actor. `postgres-qa/INFORME.md`. |
| Auxiliar de hashes | **23/23** pruebas, incluidos códigos de salida negativos; referencia RC9 y ZIP interno verificados. `hashes/NOTAS-HASHES.md`. Auxiliar R0 original intacto. |
| Adaptador GUI | **16/16** pruebas finales. `frontend/build-script-windows.log` (el log inicial `adapter-tests-windows.log` contiene 12 anteriores). |
| GUI real Edge + PostgreSQL | **14 comprobaciones correctas**, dos contextos de sesión, recarga, Unicode, conflicto, pérdida de red, reautenticación, EN/DE/ES y temas. `frontend-native-run5/browser-windows.json` y capturas reales. |
| Revisión independiente | 4 negativas hashes, 12 fronteras HTTP, 9 DTO/actor/idempotencia y 3 reintentos. Alcance, fuentes y límites en `revision/INFORME-REVISION-INDEPENDIENTE.md`; no se atribuye al revisor la ejecución de las suites de otros agentes. |

Las cantidades describen suites distintas; no representan aceptación total del producto. DLL final del fundamento: `c063eb2f004c31fc6f389290ddc2428579ce349ba4c12944dd042e11489a8bd4`. Compilaciones posteriores del inventario requieren nueva evidencia.

Correcciones verificadas además de D-007: handlers GET `/me` y `/customers` producían 200 sin cuerpo por selección del delegado ASP.NET; ahora retornan `Task<IResult>` explícito. Se corrigió hosting de estáticos y respuestas JSON de rechazo 413/415. En GUI se conserva UUID/cuerpo/revisión ante incertidumbre y reautenticación, se vincula la operación a su actor original y se invoca `fetch` con receptor de navegador válido. Las primeras ejecuciones fallidas, la corrección del arnés por handles heredados Windows y la repetición satisfactoria se conservan, no se sustituyen.

Datos de laboratorio sintéticos, secretos locales bajo ACL en `.local/labs`, nunca en Git ni informes. Cada prueba crea y detiene su propia instancia y conserva sus bases. El primer uso de .NET generó un certificado de desarrollo; está registrado y no se presenta como certificado operativo. La activación posterior evita generación automática.

## Continuación autorizada

Login, Systemhaus y clientes están conectados; no equivalen a inventario RC9 completo ni a candidata Windows. Sigue implementación de `CONTRATO-INVENTARIO-S1.md`: jerarquía, entidades Dose/final en sala, grupos/puertos UUID, revisión por cliente, conexiones y Click-Click. Deben verificarse lotes por IDs y grupo/tipo, fronteras de ámbito, topología y paridad visual. Panel administrativo, revocación concurrente, recuperación durable de operaciones inciertas, importación/exportación, informes, instalación/HTTPS/servicio, backup/restore y manual completo continúan pendientes. Adopción exclusivamente por QA final de Wascar.

## Resultado26 · 04.10.2026

Tanda26,04.10.2026: identidad pública UUID independiente de token/CSRF y GET administrativo de sesiones por usuario, autorizado GLOBAL en servidor; filtrado de vencidas/inactivas, indicador de sesión actual y DTO/OpenAPI/ETag alineados. Migración004 incremental, schema4, conserva SQL001–003/cookies anteriores. Cuatro grupos finales independientes Windows/PostgreSQL y seis regresiones password22 del implementador correctos. Sin GUI ni revocación individual, sin actualizar/migrar QA. [Cierre26](../evidence/s1-20261004/admin-sesiones-consulta-26/CIERRE.md). Schema4 requiere preparación de actualización/recuperación: NO usar Upgrade-Restored-QA --no-schema-change ni rollback sólo de archivos aDLL23 sobre DB4. QA restaurado permanece schema3/DLL23/GUI24 con QA16 y original intacto. Migración3→4/repetición/rollback y bootstrap nuevo probados; no suite1→4 ni todas las carreras. Recuperación operativa de QA/schema4 pendiente de ensayo previo.
