# Dictamen independiente · paso 26/F-08.03

11.11.2026. Revisor `f0803_review`, perfil security, distinto del autor de la prueba y del runner. Escritura propia limitada a este dictamen y al laboratorio privado nuevo de la repetición. No modifiqué producto, pruebas compartidas, ledger, QA ni trabajo ajeno; sin operaciones sobre D/E, VM, servicios, cuentas o bases instaladas, commits o publicación.

**Favorable exclusivamente al cierre técnico de F-08.03 con su peso existente de 1/2 punto.** El canje existente consume y revoca el estado anterior de la cuenta dentro de una transacción, entrega sólo un desafío enroll y conserva la otra cuenta. La revisión del código, los negativos existentes repetidos por el coordinador y la repetición propia cubren concurrencia observada, replay, rollback y ausencia de valores originales en las tablas inspeccionadas. No identifiqué hallazgos de producto P1/P2 pendientes en este alcance. F-08.04/.05 y los hitos operativos completos de F-08 permanecen pendientes.

## Fuentes y símbolos consultados

Se leyeron AGENTS, BRIEFING-MAESTRO, EQUIPO-Y-SKILLS, `.codex/agents/security.toml`, el plan F0803, literal del ledger y paso 026, ficha del paso 26, D2 y sus adendas, PUNTO3-FUNCIONES-PENDIENTES, planes y dictámenes F0801/.02 y entradas vigentes de continuidad/progreso. Se consultaron también las secciones iniciales del contrato, aceptación, mapa RC9/R3, inicio S1 y README del servidor. Se reutilizó la investigación oficial PostgreSQL 17 registrada por el coordinador; no se añadió una dependencia ni se hizo otra investigación web.

| Archivo bajo `development/server/` | Símbolos y comprobación |
|---|---|
| `src/RackClick.Server/MfaStore.Recovery.cs` | `RedeemRecoveryCode`, `RecoveryEnrollmentChallenge`: transacción, autoridad del desafío, consumo del conjunto completo, revocación por cuenta, respuesta sin sesión, auditoría sin valores originales |
| `src/RackClick.Server/MfaStore.Enrollment.cs` | `LockChallenge`, `LockedChallenge`, `ChallengeOpen`, `StartEnrollment`, `ConfirmEnrollment`: orden cuenta→factor→desafío→política, revisión/finalidad, reloj después de las esperas y emisión de sesión sólo al confirmar |
| `src/RackClick.Server/MfaStore.cs` | Definiciones de `Command` y `Burn`, límites de cinco intentos: parámetros y misma conexión/transacción en el consumo y la invalidación |
| `src/RackClick.Server/PostgresStore.Authentication.cs` | `AuthenticateForLogin`, `AuthenticateCore`, `LoginOutcome`: contraseña previa y pending antes de conceder sesión |
| `src/RackClick.Server/PostgresStore.cs` | `Session`, `Login`, `Logout`: consulta de sesión real y hash del token; un desafío no es un registro de sesión |
| `src/RackClick.Server/Program.cs` | Middleware de sesión/Origin/CSRF/no-store, tratamiento de errores y rutas login/verify/recover/start/confirm; recover responde202 y cambia la cookie de desafío después del commit |
| `src/RackClick.Server/MfaRecoveryCodeCodec.cs` | `Matches`, `Normalize`, `Derive`, `NewCode`, `Hash`: códigos/hash ligados a Systemhaus y usuario, sin solicitar clave TOTP |
| `database/001-foundation.sql`, `database/014-mfa.sql` | PK global de usuario, FK de sesiones, claves compuestas MFA y columnas de hash/consumo. El DELETE de sesiones por user_id queda delimitado por esa identidad global |
| `src/RackClick.Server/SchemaMigrations.cs` | `LatestVersion=46`, esquema que bootstrap aplica al fixture |
| `tests/RackClick.Quality.Tests/MfaRecoveryRedemptionTransactionTests.cs` | Prueba nueva completa, `NoKeys`, `Challenge`, `OtherAccount`, bloqueo retenido, observador de dos PID, testigo SQL y aserciones de revocación/secretos |
| `tests/RackClick.Quality.Tests/MfaRecoveryCodesTests.cs` | Siete focos existentes de canje/replay/esperas/intentos/rollback y sus helpers `Challenge`, `Recovery`, `AuditFailure`, `ThrowingKeys` |
| `tests/RackClick.Quality.Tests/MfaAccountManagementTests.cs` | `Laboratory.Create`, `Factor`, `Session`, `Policy`, `AddUser`, `Execute`, `Snapshot`, `SnapshotAll`, `DisposeAsync`: roles separados, preparación sintética y limpieza delimitada |
| `tests/RackClick.Quality.Tests/MfaRecoveryHttpTests.cs` | Contrato HTTP histórico y helpers; leído como contexto, sin ejecutarlo en esta revisión |
| `tests/pg_support.py` y driver privado `run_focus.py` | Clúster nuevo bajo .local, contraseñas privadas aleatorias, herramientas existentes, pines antes/después, filtro3 y parada del clúster propio |

Se leyeron RESULTADOS, MATRIZ-CRITERIO, FOCO, FUENTES, REUTILIZACION y CAMBIOS.patch de esta tanda, además de la revisión final del punto3 con sus dos adendas y su comparación de fuentes final.

## Identidad y revisión estática

Comprobación propia: **227/227 archivos de producto** de F0802 y del inventario previo coinciden en raíz y freeze. La nueva prueba coincide en ambas copias. Se recalcularon todas las entradas de FUENTES: 227 de producto, una prueba nueva, 29 referencias de fuentes del punto3, dos pruebas previas y 13 referencias históricas; ninguna diferencia. CAMBIOS.patch reconstruye exactamente la prueba nueva. El núcleo `MfaStore.Recovery.cs` conserva el hash revisado del punto3. No se declara identidad de todo Program con aquel punto ni identidad binaria con una candidata instalada.

Todos los comandos de `RedeemRecoveryCode`, incluidos `LockChallenge`, `Burn` y la auditoría, reciben db/tx; `Command` construye NpgsqlCommand con esa transacción y parametriza los valores. La respuesta sólo sale después de CommitAsync. Un fallo de auditoría sale antes del commit y el dispose revierte la transacción.

El canje exige desafío verify, CSRF, cuenta utilizable, factor activo/no bloqueado, política presente/exigida, ausencia de pending y misma revisión. `LockChallenge` lee clock_timestamp después de sus bloqueos; el canje vuelve a comprobar consumo/intentos/caducidad después del bloqueo adicional de códigos. Se examina el perfil acotado de diez hashes; once o más no permiten canje. El éxito consume todo el conjunto antiguo, deshabilita el factor, aumenta revisión/pending y revoca sesiones y desafíos de esa cuenta antes de insertar el desafío nuevo. El perdedor revalida el estado después de esperar y no concede otra recuperación.

La auditoría contiene únicamente enrollmentPending y contadores de revocación. El testigo SQL del fixture sólo registra relación, verbo, rol y txid; no copia NEW/OLD ni valores de filas. `NoKeys` rechaza tanto GetKey como GetActiveKey: demuestra que el canje no solicita claves TOTP, aunque LockChallenge sí puede leer el ciphertext y los metadatos del factor.

## Ejecución propia

```powershell
C:/Python312/python.exe -B .local/f0803-83799606/run_focus.py --review
```

**Salida 0; 3/3 PASS, cero fallos/omisiones.** Se inspeccionaron los tres UnitTestResult del TRX y el recibo saneado, además del agregado:

- `OverlappingRedemptionsCommitOneAccountRecoveryAndLeaveAnotherAccountUntouched(differentCodes: False)`.
- El mismo caso con `differentCodes: True`.
- `RecoveryAuditFailureRollsBackEverythingIncludingTheUsedCode`.

La nueva prueba retiene la fila app_user y exige dos PID runtime esperando antes de liberarla. En ambos escenarios hay exactamente un ganador enroll, diez códigos consumidos, dos sesiones retiradas, tres desafíos anteriores consumidos y un único desafío nuevo. Factor y política individual cambian como exige el contrato; las seis relaciones afectadas aparecen bajo el txid de la auditoría ganadora y el rol runtime. La otra cuenta conserva exactamente seis colecciones propias; la política global de gracia queda igual. Los valores originales/normalizados conocidos de códigos y las credenciales originales de los desafíos inspeccionados no aparecen en el snapshot.

El caso existente fuerza error al insertar audit y comprueba igualdad de las diez tablas del snapshot, incluido código, factor/política, sesiones y desafíos. No sustituye rollback por contar eventos o transacciones.

PostgreSQL **17.11** comprobado directamente con `postgres.exe --version`; esquema 46 por el bootstrap de la fuente fijada. Clúster propio `f0803-consumption-cb81c1cd89224361a0ff4a78804195a8` detenido, postmaster.pid ausente; un binlog privado producido. El runner comprobó los dos pines antes/después. No ejecuté restore/build, HTTP, Node, Edge u otra regresión.

| Artefacto | SHA256 |
|---|---|
| RackClick.Server.dll | `d315a00df4cd522b26030369de26fba1410a04c5a2c77667572aa6733e7c59b4` |
| RackClick.Quality.Tests.dll | `4f3d914452030f13eb877b2fb7680b18b77fbb63ef4531af2272cc73184b5120` |
| Nueva prueba | `2a6e3f99996d4563727e95e55f2641304f99bc5a0b22ceac5f3c6e92a44ffdb4` |
| run_focus.py | `d4320e54a725e86a7377de1c262ed38353ae276b95eb3bc762740793b1668be0` |
| pg_support.py | `fa5da11b657660f5335b6b5aef17387f8d0ceca5a1b0b095d2b4a09c8cdb1de5` |
| TRX propio | `8be58b5135a5c679f2c1adbebcf84f434cac31bab5eddabd484a5540dc5183e8` |
| Recibo saneado propio | `9877b0d298ea794795354699249bd688520462b95ab704a40fa6f953521307d8` |

TRX, conexiones, códigos, logs y binlogs permanecen privados. Del TRX se extrajeron sólo nombres/resultados y hashes; no se abrieron los logs privados, conexiones, pgpass o binlogs.

## Ejecuciones ajenas e históricas

Se contrastaron los nueve resultados individuales del TRX del coordinador y su recibo saneado: **9/9 PASS**, sin omisiones, mismo par de DLL. Clúster `f0803-consumption-57dc5dbdbc9f4276bee807093375919e` detenido y postmaster.pid ausente. FOCO coincide con ese TRX, hash `85bf761cf0fbf52e3aabab5483c4add1bc5457115747323b0d5477e647dab516`. Son dos casos nuevos y siete existentes, no nueve recorridos nuevos. Incluyen replay/finalidad/CSRF, caducidad/revisión cambiada, caducidad durante espera observada del lock de códigos, límite de cinco intentos y rollback de auditoría.

El coordinador comunica restore locked/build Release con salida 0 y cero errores/advertencias; RESULTADOS lo registra. No ejecuté esas etapas ni abrí sus logs privados. La evidencia HTTP y los 20 Node de F0802, así como Edge y regresión final del punto 3, se reutilizan como históricos con sus ejecutores y fechas. No son ejecuciones nuevas de esta tanda o de este revisor. La prueba concurrente histórica con Task.WhenAll se conserva sin atribuirle observación de solapamiento.

## Hallazgos, límites y conciliación

**Sin hallazgos bloqueantes, altos o medios reproducidos en el criterio inspeccionado.** No se requirió corrección de producto ni se fabrica una fase roja al añadir cobertura de comportamiento existente. La conformidad procede del contrato y de las comprobaciones descritas, no del número de tests.

El testigo acredita escrituras de seis relaciones bajo la transacción ganadora y rol runtime; no acredita un apagón, reinicio Windows o recuperación de proceso durante commit. Los factores y sesiones iniciales son sintéticos. Los roles owner/runtime se crean separados y NOSUPERUSER/NOCREATEDB/NOCREATEROLE; runtime no tiene CREATE en el esquema. El DDL y los permisos adicionales del testigo pertenecen sólo al fixture; no son migraciones ni cambios de autoridad del producto.

SnapshotAll abarca diez tablas de identidad/MFA/Systemhaus/operación/auditoría, no todo el inventario o toda la base. La comparación de otra cuenta cubre usuario, política individual, factor, códigos, sesiones y desafíos. La prueba de secretos busca los valores conocidos en esas tablas; no es una auditoría de memoria, todos los logs, dumps, dependencias o historial completo. No se revisaron de nuevo todos los ámbitos o endpoints del servidor.

No se ensayaron host HTTP en esta repetición, DPAPI, SID efectivo, SCM/servicio instalado, TLS, navegador, instalador, candidata objetivo ni QA/adopción de Wascar. NoKeys no demuestra que el host arranque sin su almacén. Custodia, último administrador F0804, emergencia local y cierre conjunto F0805 permanecen pendientes; los 175 casos QA y sus resultados están fuera de esta escritura.

Puede conciliarse únicamente F0803, +1/2, conservando los demás checkpoints e hitos de F08. Este revisor no modifica ledger, pesos o porcentajes. El índice vigente al inicio era 23,13/100 del cierre restante; no es un porcentaje global del producto ni una medición de aceptación.
