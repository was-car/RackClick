# C1 · Conciliación de S-38 a S-42

23.10.2026 · Análisis de Codex en paralelo al laboratorio MFA de Claude.

**Resultado:** los mecanismos administrativos principales ya existen. No se justifica reimplementarlos a partir de esta lectura. Quedan por acreditar la ausencia de secretos en logs, los recorridos visuales aceptados por Wascar y la correspondencia entre las pruebas históricas y la candidata/instancia actual. **C1 no se declara terminado; avance global aproximado78%, sin cambios.**

## Alcance y significado de los estados

- Encargo: `docs/MENSAJE-PARA-CODEX-PARALELO-23-10-2026.md:11` y `:19`. Sólo este documento y evidencia nueva bajo `evidence/s1-20261023/c1-*/`. Sin commits, push, cambios de código, SQL, laboratorio MFA, VM, servidor QA, catálogo/guías ni documentos compartidos.
- Base Git observada: `7b4f3e8a9eb9b7278f0347b3cdd473348966e821`, rama `improvements/rev4-security-foundation`, árbol con modificaciones ajenas preexistentes. Esta es una foto de análisis, no una candidata compilada.
- **Cubierto:** hay mecanismo en código actual y pruebas relacionadas localizadas; su evidencia ejecutada se fecha aparte. No significa Pass nuevo del23 ni adopción.
- **Parcial:** una parte está demostrada, pero queda una comprobación/aceptación concreta. **Falta** se reservaría para una ausencia comprobada; no se ha clasificado un defecto nuevo de implementación como demostrado.
- Criterios literales: `docs/ACEPTACION.md:106`–`:110`. C1 exige conciliación y QA, no un forest/AD nuevo: `docs/CIERRE-RESTANTE.md:9`. Los contextos históricos incompletos de planes antiguos no se trasladan automáticamente al código actual.

Para compactar rutas: **CS/** = `development/server/src/RackClick.Server/`; **PT/** = `development/server/tests/`; **UI/** = `development/frontend/src/`; **BT/** = `development/frontend/tests/`. Cada sufijo `:n` es la línea del archivo actual con ese prefijo. Las rutas de evidencia son completas y relativas al repositorio.

## Matriz: mecanismo, diferencia restante y acción propuesta

| ID / criterio | Diferencia o condición concreta | Evidencia, código y prueba relacionada —ruta:línea— | Estado | Acción propuesta |
|---|---|---|---|---|
| C1-01 · S-38 | Retirar al usuario de un grupo debe quitar el acceso sin exigir logout. La sesión puede seguir existiendo con menos permisos. | **CS/PostgresStore.cs:24** `Can` consulta pertenencias/concesiones vigentes; **CS/AdminGroupMembers.cs:73** elimina la pertenencia. **PT/test_admin_members.py:29**, misma sesión200→404; unión con otro grupo en`:43`. Histórica: `evidence/s1-20261004/admin-miembros-13/REVISION.md:22`, con fallo inicial y revisión final separados. | **Cubierto** en autorización API. | Conservar el modelo. En la candidata seleccionada comprobar retirada con la sesión ya abierta, sin borrar la cuenta ni forzar logout como sustituto de autorización. Guion existente QA-12: `docs/QA-CASOS-WASCAR.json:174`, especialmente`:186`. |
| C1-02 · S-38 | Retirar un cliente de un grupo revoca sólo la vía retirada: otra concesión válida conserva acceso; la última retirada deniega lectura y escritura. | **CS/AdminCustomerGroupMembers.cs:83**; **CS/PostgresStore.cs:35**. **PT/test_admin_permission_races.py:88**, última retirada y denegación en`:109`–`:117`. Histórica: `evidence/s1-20261004/permisos-concurrencia-17/CIERRE.md:20`. | **Cubierto** para las operaciones/casos descritos. | Reutilizar esas pruebas en una validación futura del build objetivo. No reemplazar unión de permisos por un grupo único ni presentar el escenario como prueba de todas las intercalaciones posibles. |
| C1-03 · S-38 | Revocación en servidor y retirada inmediata de información ya dibujada en el navegador son comportamientos diferentes. Falta registrar el recorrido manual de la candidata actual. | `docs/GUI-RELACIONES-GRUPOS-S1.md:18` declara revalidación al solicitar de nuevo, sin push universal de revocación. QA-12 exige Ctrl+R sin nuevo login en `docs/QA-CASOS-WASCAR.json:186`; QA-14 está en`:211`. | **Parcial** como aceptación actual, no carencia demostrada de autorización. | Medir lectura y escritura tras retirada y el estado visual tras actualización. No inventar como requisito de S-38 el borrado remoto de cada dato ya renderizado. Las pruebas destructivas se hacen sólo con cuentas ficticias nuevas. |
| C1-04 · S-39 | Explicar procedencia de permisos del usuario, distinguiendo concesiones declaradas de capacidades efectivas. | **CS/PostgresStore.cs:161** `QueryPermissions` devuelve grupoUUID/nombre/capacidad/ámbito; **CS/AdminEffectivePermissions.cs:10** protege la consulta. **UI/AdminEffectivePermissions.jsx:33**, ayuda`:8`; **UI/admin-effective-permissions.ts:41**. **PT/test_admin_effective_permissions.py:103**, composición/origen`:136`; cambios de permisos`:151`. Histórica: `evidence/s1-20261016/admin-permisos-efectivos-35/revision/pg-4/result.json:17`. | **Cubierto** en API y vista localizada. | Mantener origen y efectivo separados. QA-18 ya pide nombre, grupo, capacidad y objetivo (`docs/QA-CASOS-WASCAR.json:288`). No añadir otro cálculo de autoridad en React ni inferir acceso a todos los clientes desde una concesión declarada. |
| C1-05 · S-39 | Grupos de personas y grupos de clientes deben ser entidades distintas, incluidas relaciones de varios padres y homónimos. | `development/server/database/001-foundation.sql:23` y`:33`; **CS/AdminGroups.cs:8** y`:35`; **UI/AdminGroupRelations.jsx:46**, ramas`:49`. **BT/browser-admin-group-relations.mjs:48**, tipo cliente`:57`, homónimos`:60` y`:65`. `docs/GUI-RELACIONES-GRUPOS-S1.md:16` delimita relaciones explícitas. | **Cubierto** en modelo/API/vista. | Conservar tablas, UUID y tipos explícitos. No convertir el árbol visual en un único padre, herencia AD, LDAP o una nueva fuente de permisos. QA-34 ya contempla ambos tipos: `docs/QA-CASOS-WASCAR.json:633`. |
| C1-06 · S-39 / UX administrativa | La legibilidad y el recorrido integral que pidió Wascar aún necesitan aceptación visual identificada, aunque ya existan origen de permisos, relaciones y altas guiadas. | Petición de usabilidad: `docs/UX-ADMINISTRACION-ARBOL.md:30`; no confundir el preview simulado de`:27` con producto. Integración posterior real y QA91–93: `docs/INTEGRACION-ALTA-GRUPOS-WINDOWS-QA-S1.md:3`,`:15`. **BT/browser-admin-effective-permissions.mjs:69**,`:95`,`:108` cubre fuentes/errores/idiomas en su alcance histórico. | **Parcial** en aceptación visual; no se ha demostrado que falte otra API. | Recorrer usuario→pertenencias→efectivos y grupo→miembros/concesiones con Wascar, registrando dónde se pierde y la versión exacta. Corregir sólo observaciones concretas autorizadas. Conservar RC9, Click-Click y EN/DE/ES; no reiniciar el diseño con otro piloto. |
| C1-07 · S-40 | Retirar pertenencia o concesión no puede eliminar al último administrador activo con `security.manage` global. | **CS/AdminGroupMembers.cs:77** y`:86`; **CS/AdminGrantWrites.cs:116** y`:127`; lock de Systemhaus en **CS/AdminGroupMembers.cs:34** / **CS/AdminGrantWrites.cs:54**. **PT/test_admin_members.py:69**, **PT/test_admin_grants.py:108**. Histórica: `evidence/s1-20261004/admin-concesiones-api-18/revision/pg-final/result.json:11`. | **Cubierto** para las acciones administrativas existentes inspeccionadas. | Conservar409 `last_admin_required`, bloqueo y rollback. Probar suplente activo/global, inactivo y ámbito cliente en laboratorio. No pedir a Wascar retirar permisos del último administrador de su servidor ni prometer protección frente a SQL externo arbitrario. |
| C1-08 · S-40 | Desactivar al último administrador debe rechazarse; con otro administrador válido puede desactivarse el propio. | **CS/AdminUserState.cs:34**,`:73`,`:78` y`:89`; commit`:111`. **PT/test_admin_user_state.py:99** compara snapshot y sustitutos. Histórica: `evidence/s1-20261004/admin-estado-api-20/revision/pg-final/result.json:11`. | **Cubierto** en implementación/caso histórico. | Mantener prueba de estado y ausencia de efectos ante rechazo. Su extensión a reset/recuperación MFA requiere coordinación con el otro desarrollador cuando M3/M4 estén preparados; hoy no se cambia su SQL ni su política. |
| C1-09 · S-41 | Reset de contraseña y desactivación deben revocar todos los tokens anteriores; reactivar no los resucita. | **CS/AdminUserPassword.cs:72**,`:89`,`:92`; **CS/AdminUserState.cs:65**,`:76`,`:80`. **PT/test_admin_user_password.py:37** y`:122`; **PT/test_admin_user_state.py:79** y`:144`, incluidas carreras con login. Histórica: `evidence/s1-20261004/admin-password-api-22/revision/pg-final/result.json:11`. | **Cubierto** en escritores y pruebas existentes. | Revalidar en el build seleccionado, con dos sesiones antiguas, login nuevo, reactivación y replay que no mate una sesión posterior válida. QA-15/16 ya existen en `docs/QA-CASOS-WASCAR.json:232` y`:250`. No agregar ahora una segunda implementación de sesiones. |
| C1-10 · S-41 | Ausencia de contraseña/hash/token en auditoría y operación durable no equivale a ausencia en todo log. | **CS/AdminUserPassword.cs:44**,`:99`,`:104`,`:110` usa intención pública y campos acotados. **PT/test_admin_user_password.py:31** `safe_durable` consulta `audit_event`/`operation`. | **Cubierto** en datos durables del alcance probado. | Conservar estos controles y su atribución. No vender `safe_durable` como comprobación de stdout/stderr, ILogger, servicios o logs de Windows. |
| C1-11 · S-41 | No se localizó una aserción que lea el log del servidor y pruebe redacción de secretos; no se ha demostrado una fuga. | **CS/Program.cs:131** registra tipo de excepción/traceId. **PT/test_http_failclosed.py:27**,`:31` captura log; prueba`:108`–`:116` busca secretos en el **body HTTP**. **PT/pg_support.py:86**–`:96` conserva logs privados. La búsqueda revisada en pruebas servidor/frontend no encontró una comprobación equivalente de su contenido. | **Parcial**: ensayo directo pendiente, no vulnerabilidad probada. | Siguiente prueba propuesta, cuando se acuerden sus archivos: marcadores sintéticos para password, token/CSRF y cadena SQL; recorrer login/reset/errorDB y leer stdout/stderr/ILogger capturados al terminar. Verificar que no aparezcan, sin consultar logs ni credenciales reales. No cambiar logging por suposición. |
| C1-12 · S-42 | Mutación, revocación de sesiones, revisión, operación idempotente y auditoría deben confirmar o revertir juntos; respuesta después de commit. | **CS/AdminUserPassword.cs:35**,`:104`,`:110`,`:113`,`:115`; **CS/AdminUserState.cs:32**,`:101`,`:107`,`:110`,`:111`. Fallo inyectado de auditoría: **PT/test_admin_user_password.py:122**, **PT/test_admin_user_state.py:144**. Fundamento: **CS/PostgresStore.cs:254**,`:342`,`:348`,`:355`; **PT/test_postgres.py:382** y`:399` cubre fallo de audit y de operation. | **Cubierto** en los escritores y caminos inspeccionados, no auditoría exhaustiva de todo el producto. | Conservar transacciones y pruebas negativas; revalidar conjuntamente con cualquier modificación MFA que cambie sesiones/auditoría. No añadir como condición oculta de S-42 enumerar todas las sesiones indirectas ni capturar login/logout: el plan los separa como mejoras opcionales (`docs/PLAN-CIERRE-AUDITORIA-ADMINISTRATIVA.md:31`,`:60`). |
| C1-13 · S-38–S-42 | Falta una atribución de ejecución/QA de estos cinco criterios al build y servidor actual. Disponibilidad de una guía local no es resultado manual ni prueba de la VM. | `docs/HANDOFF-CODEX-23-10-2026.md:8`–`:12` informa instalación, reinicio/red y10 clientes; no resultados C1 por caso. `docs/INTEGRACION-ALTA-GRUPOS-WINDOWS-QA-S1.md:11`,`:15` describe otra selección QA13. `GUIA-QA-RESTAURADO.html:344` contiene metadatos del snapshot local. Históricos reseñados abajo; no se han repetido hoy. | **Parcial** como cierre de C1. | Identificar candidata/DDL/GUI/instancia objetivo; ejecutar el conjunto focal sobre laboratorio nuevo y después guiones manuales compatibles. Registrar resultados de Wascar por versión; no trasladar Pass ni usuarios preparados del QA local a la VM por semejanza de nombres. |

## Evidencia histórica: qué respalda y qué no

Estas salidas se han **leído**, no vuelto a ejecutar. La tanda23 de04.10 no es una ejecución del23.10. Los SHA de tests password/state coinciden con los de su evidencia histórica, pero escritores C# y `Program.cs` han evolucionado: esos ensayos no certifican los bytes actuales del producto.

| Registro | Resultado histórico localizado y límite |
|---|---|
| `evidence/s1-20261004/admin-miembros-13/REVISION.md:22` y `revision/postgresql-02/result.json:1` | Revisión distinta, cinco casos finales; conserva fallo anterior de expectativa404/403. Misma sesión y unión de grupos están en el test actual. |
| `evidence/s1-20261004/permisos-concurrencia-17/CIERRE.md:20` | Tres casos independientes; dos escenarios de autorización tras espera de lock retiran permisos mediante SQL del fixture. No presentarlos como todas las carreras ni como acciones de GUI. |
| `evidence/s1-20261004/admin-concesiones-api-18/revision/pg-final/result.json:11` y `evidence/s1-20261004/admin-estado-api-20/revision/pg-final/result.json:11` | Seis casos correctos en cada registro histórico; protección del último administrador y estado. Son dos registros, no doce ejecuciones nuevas. |
| `evidence/s1-20261016/admin-permisos-efectivos-35/revision/pg-4/result.json:17` | Cuatro casos independientes históricos y fuentes de aquella corrida sin cambio. |
| `evidence/s1-20261016/admin-permisos-efectivos-gui-36/CIERRE.md:3` | Cuatro recorridos Edge antes del ajuste textual; sobre el texto final se repitió el grupo4. No anunciar otra suite completa final4/4 que no consta. |
| `evidence/s1-20261017/seis-tandas-63-68/CIERRE.md:21` | Integración/relaciones y revisión histórica; no convierte el recorrido64 en prueba nueva del23. La retirada403 de ese recorrido de relaciones fue simulada. |
| `evidence/s1-20261004/admin-password-api-22/revision/pg-final/result.json:2`,`:4`,`:11`,`:44` | Seis casos históricos de Windows11/DLL22; no DLL del23.10. |
| `evidence/s1-20261004/sesiones-contrato-23/CIERRE.md:13` | Cuatro casos independientes y regresión password de seis del04.10. No usar el número de tanda como fecha. |

## Disponibilidad de QA localizada

Se analizaron **sin ejecutar JavaScript ni abrir navegador** los metadatos `const guide` de los HTML ya generados. En `GUIA-QA-RESTAURADO.html:344`, perfil `rc9`, build `94340045725ba369379e7bde3fbde01ff2a9b6552aaada946d4c9e401e042569`, están disponibles los17 IDs comprobados: QA-12/13/14/15/16/17/18/19/22/23/25/28/34/78/85/88/91. En la guía original `manual` esos mismos17 no están disponibles. Es una comprobación de metadatos estáticos, no de ejecución, resultados de Wascar o estado vivo del servidor.

No se regeneraron guías, habilitaron casos, leyeron notas del navegador ni cambiaron snapshots. Los guiones existentes son una base para el siguiente recorrido; su disponibilidad local no demuestra que estén preparados los usuarios/grupos de prueba en la VM actual.

## Coordinación y salida de este bloque

La conciliación se hizo en tres partes pequeñas: membresías/permisos/último administrador; sesiones/auditoría; y coordinación de QA/versión. Dos exploradores de sólo lectura aportaron referencias de sus ámbitos; no se cuentan como ejecuciones nuevas ni como aprobación independiente de sus propias conclusiones. El coordinador escribe este documento. La revisión documental distinta se registra en `evidence/s1-20261023/c1-conciliacion/REVISION.md` cuando se complete; el dictamen aplica a esta conciliación, no al código nuevo de Claude ni al cierre funcional de C1.

No se solicita tocar archivos de MFA. Cualquier implementación del ensayo de logs o cambio de administración necesita antes acordar propiedad de archivos, porque el reparto actual reserva código/herramientas y documentos comunes. La revisión de las correcciones de instalación del23 sigue siendo un bloque separado, aún no realizado aquí. No se han editado `CHANGELOG.md`, continuidad ni progreso por la restricción vigente de reparto.

## Archivos leídos y SHA256

El siguiente inventario identifica los bytes consultados íntegra o parcialmente por el coordinador y los dos analistas. No significa que cada archivo haya recibido revisión exhaustiva. Las coincidencias de descubrimiento sin examen no forman parte del inventario. El SHA se obtiene del archivo completo; `SHA256SUMS` de la evidencia identifica además los documentos nuevos al cierre.

<!-- C1-FUENTES-INICIO -->

```text
d7684f27f028f04af40250916f1d4bf91a173728c9a913ba844ab746a612dac8  .codex/agents/network.toml
a4fd60451a1c6ccce04d52a8095f435c2edc88165faa5c0c2d0730fb848c817f  .codex/agents/product.toml
60fdfdb3e6dc9e61e9f8ef4f1a3f28e1aaea798a0987fe60ab961f304368fcdf  .codex/agents/qa.toml
98e0c50e45fdb144608f9c4278ece7231fef606dba8802b7411f7d4f1aef14a2  AGENTS.md
db48b662f49dda480b8f654e64e8d0c5d467e3312663a522836f495ff1fc8834  GUIA-QA-RESTAURADO.html
152a24178b184115401bc07ae0865db84db451682bb7738d4d0116edd8f58fc0  GUIA-QA-WASCAR.html
886694e442413214a710b996cb4fab97e7fa92db2761314c4e828f559141ede8  development/frontend/src/AdminCustomerGroupMembers.jsx
8eebae68b6c8d510fb0508ff353b7a95a09a67e67e3b3f7cd046d0db10af83de  development/frontend/src/AdminEffectivePermissions.jsx
92fddead51dc3819d5dbc0fdf8dee3194e86e3ebe48095f430a7f01f6c6cd9ce  development/frontend/src/AdminGrants.jsx
c31b05eca5b789710701cb972fd9320b8dbec6f4ca9960aa138287a389fe6563  development/frontend/src/AdminGroupRelations.jsx
cbde8b3b570b05ce3bdbc93e6860160d9752fcf85ab4706a5f4c867cc928d3e3  development/frontend/src/AdminUsers.jsx
805e94521f5c32f9351eca217b6e67a7aa23834a1d4b2abae80895b901d7eed2  development/frontend/src/admin-effective-permissions.ts
67df324f4e1af4eaf20f6c2e03b8edb757f3068d95e7217d5baab6a0424d5614  development/frontend/tests/browser-admin-effective-permissions.mjs
7054494a0e3492e48ebda160a465fb40d6d8f3fa5da2d7573ed4986e0ff42e0b  development/frontend/tests/browser-admin-group-relations.mjs
7dde6df0ff55b44e86bf98195bd603073767a5b9e816f182c5378bea03eba77d  development/server/database/001-foundation.sql
e8d2d19b346eddc58a02c3e2c2a3262652c89486398f153217e032e2c3e914b4  development/server/src/RackClick.Server/AdminCustomerGroupMembers.cs
6bcef407e6c863d96121d4551a14ecc9b00795d117a5934bcb38a78985df2cf9  development/server/src/RackClick.Server/AdminEffectivePermissions.cs
2d83ecb92e676c9545094a8d45001243dc230c1c9ab8c6157390d894c5e2a97b  development/server/src/RackClick.Server/AdminGrantWrites.cs
f8ea9b29b411cb24ca55f35c5e0670510a5a04680ed0e8286bb79bf067cb52c9  development/server/src/RackClick.Server/AdminGroupMembers.cs
bdf7055a3253694fd164e7da407a14b70771705f9c338e535bfdd3a9d0ee51a1  development/server/src/RackClick.Server/AdminGroups.cs
6a8d923e981d103f0852f941668ad8648aebdd19f2f872835bb8b4e2d5a4e5d9  development/server/src/RackClick.Server/AdminUserPassword.cs
38f04034a36e3c400bb9f066d7702ad01bf05f11083d6f95af4e001d0e4b06c6  development/server/src/RackClick.Server/AdminUserState.cs
68cb22d572ed8747bf9c49c04298d3c307c91c702387614f9f7d712f957bc513  development/server/src/RackClick.Server/AdminUsers.cs
4148c9388e46958ef2f6d0ae4bf053b6afd6de953a3899ef8dfbc686ffe16bfa  development/server/src/RackClick.Server/PostgresStore.cs
69e8179af02abccf6ad3f2b0475dc92e485d63b546f5703febdf7ea01f42f0f7  development/server/src/RackClick.Server/Program.cs
80c053b3a9d94108eed7867090716180f8bd25ec50c8047740999a518624a416  development/server/tests/README-WINDOWS.md
78488412678bdcc27cdd39e8a003f0a50c9e60d085a6801c50e91b9501d755c3  development/server/tests/pg_support.py
733a0dce0e976241996c2aa5772bfcaaa90d21b10b6c68307f2c03524e530680  development/server/tests/test_admin_effective_permissions.py
19ab55a0ea99b914d098f70271a69304b92148697a344ef3dd8b54e412db2589  development/server/tests/test_admin_effective_permissions_gui.py
4a877d3bfe0e178dcd103fde6b5aceea4b27050444262c48ae90efd71ada4c14  development/server/tests/test_admin_grants.py
9ee1d0cfbb18b0281ccffd7b6b12558c4bda15a706c68103dbbc7633a1a68e6d  development/server/tests/test_admin_group_relations_gui.py
b973fb16cd6b8b0383291130a10676615aea4d84859c0cd4297badfbfad53892  development/server/tests/test_admin_members.py
dad5b1e243ab09ea0aa5363302c2ecb7ca5611be177ee58bd892f1a21bbcaa52  development/server/tests/test_admin_permission_races.py
7129e9f851df42dd9cd4e874a2016e7b50cb6e870fbc6dab3776e836726b3ece  development/server/tests/test_admin_user_password.py
d32d9b28e16627da1fc721aee8c854eecce4482702224f6359245a5f40f4323a  development/server/tests/test_admin_user_state.py
397c0068e312997d30202a383457a7642012c096336c3be2639d3c0d0c8722f4  development/server/tests/test_http_failclosed.py
7d996c1dbea61f249fd2313fbeb9ebe4b76b40d19fc8ce4aed12dd0329127f3d  development/server/tests/test_postgres.py
4142aba00ced0020a3e094faacd721c0928f5e2afe30dbb2890599dec3c93d1c  development/server/tests/test_session_wait_expiry.py
c198cdc1507420152bd99654d7da6f8d46d0e1ece3a601617d97f95225c58328  docs/ACEPTACION.md
8f6a82d0cb1e1f84552d67c6c6aa15f7b6d1ccf72702494e88273294e3841e71  docs/API-ADMIN-PASSWORD-S1.md
afff88889b2e1debafae06c62a001529a06d3f12de4b2bef67ce1ed930b83610  docs/CIERRE-RESTANTE.md
994c6a73b6bb245cfc3f8134cf3fbe3d4c9d255c736a446c8780d2fb0e5e3f6e  docs/CONTINUIDAD-CODEX.md
e8d649c1c3269c222a35f9880d040b3cc02a9fb319b90d777ac53b841ebd9c8d  docs/CONTRATO-SERVIDOR-v0.1.md
9f23291505acb55a26e6e9103838e7d0559682d6cd6120de397379ac092d9a94  docs/EQUIPO-Y-SKILLS.md
e06ef3f400b45c9d7d2857ceac946a9c97d5e34ced6dae7de44c69c856a82b1c  docs/GUI-RELACIONES-GRUPOS-S1.md
15873e483338e8913262bf849e5d3ea127d6e8183c8f5b6ec6ce7a2c52b1db59  docs/HANDOFF-CODEX-23-10-2026.md
992b81726274c9221a395ea88a31cb1144a7f21a13ec77bc2a8892074d5a637d  docs/INTEGRACION-ALTA-GRUPOS-WINDOWS-QA-S1.md
6da3d817739dd4589a7851cf400893849f0e2bdd38476e63ab4033a0b84a9d44  docs/MENSAJE-PARA-CODEX-PARALELO-23-10-2026.md
2126b7d95beac2221de5c9132f1a228f6c2bedb69c5c66d6ba597599489fba3f  docs/METODOLOGIA-PARA-CLAUDE.md
c6deeb13566393dcb0045c743366b328fedacf50768d259f33687a4197c148ec  docs/PLAN-CIERRE-AUDITORIA-ADMINISTRATIVA.md
9947b6e5e13eba5026ecd79c92159e8a5e63e69a516621cb4a50b437ccda0f5e  docs/PLAN-MFA-Y-FRENTES-C1-C5.md
7523750cf225e8f9e48da130797ad906c50a0aeeab3507cdaa42dbce9140a5f4  docs/PROGRESO-GLOBAL.md
b9cdc07e7a0ad11304b20d3e3ceefb7194aad6a31a4e8270b2a1787648e89a95  docs/QA-CASOS-WASCAR.json
d6a74944c442362baa8ca5f2334afc0a15010e03b2a78947d045dd0ffc5e56a8  docs/QA-SESIONES-WASCAR.md
692759f3b855a4487771e3d51510179ad3b33b092ed614e8d456799fab016a8f  docs/REVISION-PREVIEW-ADMINISTRACION.md
f4f86131bfd0a2eb91fe5279440af808cb5aee2540243d5a098cf25a8bfa035a  docs/UX-ADMINISTRACION-ARBOL.md
f09ae952eeb71ffe14bcfb00834eaf5f4f20c26d3f8d2bb290efca20c6faff3c  evidence/s1-20261004/admin-concesiones-api-18/CIERRE.md
8e82d1f554e31a34697e0db9dcf72addfce1853c845cb24e015b343fc00ea039  evidence/s1-20261004/admin-concesiones-api-18/revision/pg-final/result.json
cc476a71812836c239cc652ee6ea36a9ef929f8a2388c08a4e2bc92f817fafd4  evidence/s1-20261004/admin-estado-api-20/CIERRE.md
6f0c516eb588c6f64b43253fcbd771eddb3ad66b22d68fd769e251b24765ecaa  evidence/s1-20261004/admin-estado-api-20/revision/pg-final/result.json
66dffd3a791105510c8f41c0144009faf970f0354f01f3aa101cfea2831d902b  evidence/s1-20261004/admin-miembros-13/REVISION.md
0c666f26fa1d9aeaf48aa613eec784c7e709d5d35c23cb307bd215a4e0609bda  evidence/s1-20261004/admin-miembros-13/revision/postgresql-02/result.json
48f5fe263031f35cf2bb9d9e637293440ed8f5dcb34b8129862b7fe3d117c0f6  evidence/s1-20261004/admin-password-api-22/CIERRE.md
510809a5989c04663a42f5b99d5b9a2e42b91ed3d134143d4ba7f57ca69ec003  evidence/s1-20261004/admin-password-api-22/revision/pg-final/result.json
577f29e970e5c69b9c2ea7fd83b18da0e8465c41c55265437fc15c3f6c12be50  evidence/s1-20261004/permisos-concurrencia-17/CIERRE.md
1e37f0bcc2abd425961f6182b57632885d0aa93b074ceec482c304e9a8202a4f  evidence/s1-20261004/sesiones-contrato-23/CIERRE.md
10d74075d58cde8ec083ce3e4b5360dbd8046b841e27114b557e95bdca0eaed8  evidence/s1-20261004/sesiones-contrato-23/implementacion/regresion-password-22/result.json
cb7b0f5c3521e1abebeb8aa6962eb0a8e4b3faab6244bca7b9df35d761e17e93  evidence/s1-20261004/sesiones-contrato-23/revision/pg-final/result.json
50be612142a9ad9ceeb69aa4180dffccb3690425f6d9d540942680571c3acf72  evidence/s1-20261016/admin-permisos-efectivos-35/CIERRE.md
9e7fea1c0855c9a731b046f4b041ca475750e43ceec0fc8d14ae38d02caab487  evidence/s1-20261016/admin-permisos-efectivos-35/revision/pg-4/result.json
5c5d1a9e7594eddc9ccf6bf4a68d273f49792401cda0fe8558eba9b5ac305269  evidence/s1-20261016/admin-permisos-efectivos-gui-36/CIERRE.md
e157ef859c21496bfe56bc45d89f44be5159596ed1e752543a9598699b7bd2cc  evidence/s1-20261017/seis-tandas-63-68/CIERRE.md
```

<!-- C1-FUENTES-FIN -->

## Lo que NO se ha comprobado

- Ninguna compilación, suite PostgreSQL/Windows/HTTP/Edge nueva ni fallo de producto reproducido el23 en este bloque. Ningún total de pruebas históricas se suma como ejecución actual.
- No se examinó ni cambió la VM, sus credenciales, cuentas, sesiones, DB, logs o servicio. No se comprobó que su código instalado equivalga al fuente actual ni a una DLL histórica.
- No hay lectura de resultados/observaciones privados de Wascar ni nuevos Pass manuales. No se verificó su aceptación visual, voz de lector de pantalla o todas las intercalaciones de concurrencia.
- No se implementó ni revisó funcionalmente MFA; tampoco se auditó la migración014 o el laboratorio del otro desarrollador. Se mantiene su propiedad.
- El límite de secretos en logs sigue siendo una comprobación pendiente; la auditoría transaccional inspeccionada no acredita por sí sola ausencia de secretos en todo archivo operativo.
- No se certificó todo S-42 para cada escritor del inventario/importaciones ni se cerraron C2–C6. La revisión documental de este bloque no sustituye esos ensayos.

## Próximo paso

Proponer el siguiente grupo acotado, después de acordar sus archivos: **(1)** añadir el ensayo de logs con marcadores sintéticos y salida privada controlada; **(2)** ejecutar una regresión focal C1 sobre un build identificado en un laboratorio nuevo, coordinando los cambios de sesiones con MFA; **(3)** recorrer con Wascar QA-12/14/15/16/18/22/28/34 y los enlaces de alta/navegación compatibles, registrando observaciones concretas de usabilidad. Las pruebas de último administrador y fallos inducidos permanecen en laboratorio, no en su cuenta real. Mantener global **~78%** hasta justificar un avance del alcance con evidencia y aceptación; esta conciliación no aumenta el indicador.

## Adenda · siguiente grupo autorizado de C1 · 23.10.2026

El reparto posterior `docs/MENSAJE-PARA-CODEX-M3-23-10-2026.md` autoriza prueba nueva de logs, regresión focal y revisión D2. La matriz anterior y sus72SHA son la **foto histórica de la conciliación**, revisada con SHA `3d5181fceb2e6e0411f8177275ae1625eca68fc5b6fce6e3ad8e302ea435fc97`; no se alteran sus fuentes ni resultados para simular otra ejecución. El manifiesto anterior corresponde a esos bytes previos a esta adenda; el manifiesto vigente de este segundo grupo está en `evidence/s1-20261023/c1-logs-d2/SHA256SUMS`.

- Nuevo `development/server/tests/test_c1_log_secrets.py`: lee stdout/stderr del ASP.NET real después de detenerlo. Comprueba password, cookie/token, CSRF, hashes sintéticos y conexión SQL en login/reset, fallo de auditoría y contraseña PostgreSQL incorrecta. Logs activos/no vacíos son precondición. El control negativo contamina únicamente el log privado del fixture y debe fallar, sin imprimir marcadores.
- Compilación/publicación aislada del commit `7b4f3e8a9eb9b7278f0347b3cdd473348966e821`, anterior a M3, sin construir sobre archivos que Claude está editando. DLL SHA `43e49045bd28d9fe62ca8afc05f49fb5ad2b96150bc02b2f76a3faca912a97ff`; SDK10.0.401 y PostgreSQL17.11, base/roles/clúster nuevos y sólo loopback. No se usa el laboratorio M1 ni el QA.
- Autor:10comprobaciones correctas (detector,3recorridos de logs y6regresiones administrativas existentes). Después se añadió al informe el SHA de la prueba y la versión PostgreSQL medida; no cambió el cuerpo de las aserciones. Control negativo sobre esa fuente final:1fallo esperado/exit1, con clúster detenido y fuentes/DLL intactos. Revisión y ejecución final de la fuente en `evidence/s1-20261023/c1-logs-d2/REVISION.md`; no sumar reproducciones como escenarios distintos.
- Esto aporta un ensayo real al hueco C1-11 **en ese baseline**, y nueva evidencia focal para C1-01/04/08/09/12. No certifica los archivos M3 en edición, schema14, custodia MFA, la VM o ausencia universal de secretos en cualquier canal. C1 completo y QA visual siguen pendientes.
- Dictamen D2 separado en `docs/REVISION-D2-CODEX.md`: no aprobado en su forma actual por ACL del servicio y recuperación administrativa aún no demostrada. README de calidad corregido para distinguir fundamento21 y dependencia de producto añadida por M2. No se cambia el documento D2 ni código del otro desarrollador. **Global78%**, sin incremento.
