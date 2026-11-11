# MFA-L1 · ronda 2 · revisión independiente de seguridad

25.10.2026. Revisor distinto del implementador. Alcance: lectura de las fuentes entregadas, sus pruebas y tres focos propios de fuente. Sin cambios en producto, sin compilación, sin PostgreSQL, HTTP, VM, QA, instaladores ni lectura de privados. Las ejecuciones del coordinador se registran en sus propios recibos; este informe no se las atribuye.

**Dictamen de fuente:** las cuatro causas P2 de la revisión anterior están corregidas. No he identificado un P1/P2 nuevo dentro de este alcance. La aceptación de ejecución de MFA-L1 queda pendiente del resultado independiente del coordinador. Esto no habilita MFA para usuarios ni cierra custodia, interfaz, recuperación o entrega Windows.

## Contraste de las cuatro correcciones

| Hallazgo anterior | Fuente actual y razón | Negativo de la entrega leído, no ejecutado por este revisor |
|---|---|---|
| S01, bloqueo del factor eludible mediante Start | `MfaStore.Enrollment.cs:153–155` exige `!FactorLocked`; el reloj y el bloqueo se leen al final en `:219–230`. El UPSERT `:54–60` conserva los contadores y el bloqueo de una fila existente. | `WrongCodesAccumulateAcrossChallengesAndLockAfterFive`, `NewChallengeAndStartCannotReopenALockedFactor`, `ExpiredLockAllowsRecoveryWithAValidCode` en `MfaEnrollmentTests.cs:188–249`. |
| S02, caducidad medida antes de esperar el upgrade de la política | `LockChallenge`, `MfaStore.Enrollment.cs:206–230`, adquiere `FOR UPDATE` de la política antes del reloj final. `ConfirmEnrollment` no necesita después convertir ese bloqueo para actualizarla. | `ChallengeExpiringWhileConfirmWaitsForPolicyLockIsRejected`, `MfaEnrollmentTests.cs:252–274`, conserva un lector `FOR SHARE` hasta que el desafío caduca y exige rechazo sin sesión. |
| S03, Start sin limitador | `Program.cs:199–205` termina con `RequireRateLimiting("login")`, igual que login, verify y confirm. | `StartIsRateLimitedAfterTheLoginWindowIsSpent`, `MfaHttpTests.cs:171–185`: tras login, nueve Start aceptados y el siguiente 429. |
| S04, finalidad cruzada consumía un verify | Los dos retornos nulos de `StartEnrollment` y `ConfirmEnrollment`, `MfaStore.Enrollment.cs:35–39` y `:78–82`, rechazan sin `Burn`. El SELECT inicial filtra token y finalidad. | `CrossPurposeUseDoesNotConsumeTheValidChallenge`, `MfaEnrollmentTests.cs:278–293`, y `MfaHttpTests.cs:124–142`. Verifican que un verify siga utilizable tras enviarlo a Start. |

Los tests cruzados de la entrega usan Start. La rama nula equivalente de Confirm fue revisada directamente en fuente; no se presenta como un negativo HTTP independiente ya ejecutado.

## CompleteVerify: el FOR SHARE no reproduce S02

En `MfaStore.cs:95–117` la política se bloquea `FOR SHARE` antes de leer el reloj. A diferencia del enrolamiento original, **CompleteVerify no ejecuta después un UPDATE sobre `app_mfa_user`**. Sus escrituras posteriores afectan al desafío y al factor, cuyas filas ya adquirió `FOR UPDATE` en `:66–88`, o insertan la nueva sesión (`:169–173`). Por tanto no existe allí el upgrade concreto de la fila de política que permitía pasar la caducidad en S02.

No propongo cambiar SHARE por UPDATE por analogía. Una espera genérica causada por DDL externo no demuestra esta causa. Este contraste es análisis de SQL y orden de operaciones, no una reproducción PostgreSQL propia.

## Finalidad, CSRF, transacción y composición

- **Separación de acceso:** un desafío enroll no es una sesión; login devuelve el desafío separado y la confirmación genera token y CSRF nuevos. Las excepciones de middleware son rutas exactas (`Program.cs:112–114`). No se concede acceso general por tener la cookie MFA.
- **CSRF:** Start y Confirm contrastan el hash del desafío (`MfaStore.Enrollment.cs:46–50`, `:89–93`). Un CSRF incorrecto sobre un desafío abierto se rechaza sin incrementar intentos. El middleware de Origin precede a las rutas. Los negativos HTTP de la entrega se han leído; no ejecutado aquí.
- **Revalidación y concurrencia:** cuenta, factor, desafío y política se bloquean en ese orden; la finalidad y la revisión se validan antes de la sesión (`MfaStore.Enrollment.cs:153–235`). El desafío se consume, el factor se activa, la política se actualiza y la sesión se inserta dentro de la misma transacción de Confirm (`:119–140`). Las pruebas de concurrencia y revocación de `MfaEnrollmentTests.cs:338–381` apuntan a una sola sesión o a ninguna tras revocación.
- **Auditoría:** Start y Confirm escriben `auth.mfa.enrollment_started` y `auth.mfa.enrollment_confirmed` antes del commit y con el mismo `db, tx` (`MfaStore.Enrollment.cs:61–62`, `:139–150`). El evento solo incluye identificadores, acción y `{"result":"ok"}`; no incorpora secreto, URI, código, cookie ni CSRF. `ForcedAuditFailureRollsBackTheWholeConfirmation` (`MfaEnrollmentTests.cs:314–334`) fuerza un error del INSERT y comprueba reversión de factor, política, desafío y sesión. No acredita auditoría de todo MFA ni rollback propio de Start por un fallo de su auditoría.
- **DI:** el proveedor se obtiene de `app.Services` después de `builder.Build()` (`Program.cs:86–91`); no hay registro de un proveedor sintético en el producto. El registro de `SyntheticKeys` está exclusivamente en `ConfigureTestServices` (`MfaHttpTests.cs:286–298`, `:402–405`). Sin proveedor, las rutas fallan cerradas; no se ha añadido una opción de configuración que habilite el proveedor de tests.
- **CLI y dependencia:** `--migrate` y `--bootstrap` mantienen un `cliStore` separado antes del host (`Program.cs:38–64`). `Microsoft.AspNetCore.Mvc.Testing` está fijado en `[10.0.12]` y `PrivateAssets="all"` en el proyecto de calidad (`RackClick.Quality.Tests.csproj:18`). La inspección del lock no equivale a ejecutar restore ni a revisar toda dependencia transitiva.

## Observaciones P3 de las pruebas, sin bloqueo de producto demostrado

1. **Atributos de cookies no afirmados por la entrega original.** `MfaHttpTests.cs:228–235` recorta `Set-Cookie` al par nombre/valor y las pruebas manejan las cookies manualmente. Eliminar Secure, HttpOnly, SameSite o Path del producto podría no hacer fallar esos tests. La configuración de producto sí declara esos atributos. Negativo recomendado: comprobarlos en los encabezados del login y de la sesión nueva, además de la eliminación con el Path correcto. El coordinador informó que está ejecutando un foco independiente para complementar esta cobertura; su resultado no estaba disponible al redactar este dictamen.
2. **Restauración de variables de entorno no garantizada ante fallo del fixture.** En `MfaHttpTests.cs:387–398`, una excepción de `_factory.DisposeAsync()` o de la limpieza anterior puede saltar la restauración de `ConnectionStrings__RackClick` y `PublicOrigin`. La colección serializada reduce la concurrencia, pero no cubre este fallo de limpieza. Mejora: restaurarlas en un `finally` y conservar el error de limpieza. Negativo sugerido: simular fallo de Dispose y comprobar que ambas variables recuperan sus valores anteriores. No he demostrado un fallo del producto a partir de esta observación.

## Focos propios realmente ejecutados

Python 3.12, en memoria y leyendo únicamente los archivos indicados: **3 focos, 16/16 aserciones correctas, salida 0**. Comprueban presencia y orden de los cuatro fixes, ausencia de UPDATE de política en CompleteVerify, uso de la misma transacción de auditoría y separación entre DI de producto y proveedor sintético. Son comprobaciones de fuente, no tests C#, SQL ni HTTP.

Los dos primeros intentos del pequeño arnés fallaron por supuestos del revisor: búsqueda de una firma abreviada inexistente y expectativa de `new NpgsqlCommand` donde se utiliza el helper `Command`. Se corrigió solamente el arnés en memoria, sin tocar producto. No fueron reproducciones de fallos de RackClick.

No ejecutados por este revisor: las 18 pruebas de tienda, las 9 HTTP, la regresión completa, restore, producción con la cuenta PostgreSQL restringida, TCP/TLS real, navegador ni instalación Windows. Las cifras de Claude en `docs/MFA-L1-RESULTADOS.md` se mantienen como evidencia del implementador; no se cuentan como ejecuciones independientes nuestras.

## Archivos y símbolos consultados

- `AGENTS.md`, `docs/BRIEFING-MAESTRO.md`, `docs/MENSAJE-PARA-CODEX-MFA-L1-RONDA2-25-10-2026.md`, `docs/MFA-L1-RESULTADOS.md`.
- `MfaStore.Enrollment.cs`: `StartEnrollment`, `ConfirmEnrollment`, `WriteAudit`, `ChallengeOpen`, `LockChallenge`.
- `MfaStore.cs`: `CompleteVerify`, `Burn`; `PostgresStore.Authentication.cs`: `Authenticate`, `MfaAvailable` y emisión de desafíos.
- `Program.cs`: composición de CLI/host, middleware de Origin/sesión, rutas login, verify, enroll/start y enroll/confirm.
- `MfaEnrollmentTests.cs`, `MfaHttpTests.cs`, proyecto de calidad y su lock.

## SHA256 medidos sobre esta revisión

| Archivo | SHA256 |
|---|---|
| `MfaStore.Enrollment.cs` | `ff2137a825746f5e59a89bdab3c9ea2c5289e1d4c62fce359be991ac06b5fe79` |
| `MfaStore.cs` | `a0de3d88bafe836a21d6a8d31ac7086906e3c6ba8d396492056ea18ce2d3c1ca` |
| `PostgresStore.Authentication.cs` | `024df8c81eddb1de4a1a435780b17a42758b5a65c101b08057fe257ab20b0571` |
| `Program.cs` | `a6fba2faeb1e25bf95f9680aecc9a1ac422ead2ffae4be624b0831c6e31f9185` |
| `MfaEnrollmentTests.cs` | `71b7eafcf76ebdb4b7a518ae2024910ef6b92de86581df8f75a3b99bc0828e57` |
| `MfaHttpTests.cs` | `7b5394c9b4a4e3f740c74c2b05d6f2cacd4c9c83709b426f53278b91b8a37ad4` |
| `RackClick.Quality.Tests.csproj` | `006a56f424e616e69ee139b83b0e20ca9f854c17c28bc5accdaff5b92a2b052e` |
| `packages.lock.json` | `be4935819a1d1aa3105c4f8400e2c6b2f5ee754c513c5e8359149f4dda9d9ffa` |

Revisión favorable de estas correcciones en fuente, pendiente de conciliar los resultados independientes del coordinador. No se modifica el progreso global ni se declara MFA disponible.

## Adenda · recibos independientes del coordinador conciliados

Esta adenda actualiza el estado pendiente del dictamen anterior y conserva los intentos fallidos. **Conforme al cierre técnico acotado del backend de MFA-L1**, con los límites restantes indicados aquí. La ejecución la realizó el coordinador; este revisor leyó los recibos y el foco adicional, sin ejecutar nuevos tests, compilaciones ni PostgreSQL.

- **Fuentes fijadas:** los recibos comprueban 110 fuentes de la copia congelada y la correspondencia de la entrega. La DLL del servidor es idéntica en los intentos 2 y 3: `2d067c424f0e120b6b7671871cf704a013f9e4ff1591bff16f9ff36528d653a4`. El cambio entre esos intentos afecta al observador del test independiente, no al producto.
- **Regresión, intento 2:** las 88 pruebas originales pasaron; la de Docker no se ejecutó. El resultado global del intento se conserva como FAIL porque falló el Fact añadido por Codex en su observación final de `pg_stat_activity`; no se reclasifica ese intento como verde. Según el diagnóstico del coordinador, el muestreo tardío encontró cero conexiones y no era un testigo estable de las escrituras previas. Se conserva `INTENTO2-REGRESION-Y-OBSERVADOR.json`.
- **Repetición focal, intento 3:** solo se repitió el Fact independiente corregido: 1 PASS, 0 fallos y 0 omisiones, 19,031 s, PostgreSQL 17.11. No se volvieron a sumar otras 88 ejecuciones. El recibo registra `probeOnly=true`, `runtimeRoleHttpVerified=true`, build y test con salida 0, laboratorio detenido al terminar. El coordinador registra restore con lock y compilación Release sin errores ni advertencias.
- **CLI:** los recibos registran bootstrap real, migración sobre base inicializada en 14 sin alterar usuarios/migraciones, rechazo de bootstrap repetido, modos incompatibles, migración de base vacía y recuperación de usuario inexistente antes del host. Esto no acredita migración 13→14, que figura expresamente como no probada.

### Contraste del testigo de identidad y de las cookies

Se leyó `MfaL1RuntimeReviewTests.cs`, SHA256 `d8fec5ca1812e9de6e9e931854b5f41169c806fbc420a523e6a901dae13eeaf4`.

El testigo **no inserta las identidades esperadas como parámetros del test**. Tras preparar el usuario, crea una tabla vacía y triggers `AFTER INSERT OR UPDATE` de `app_mfa_factor` y `app_session`. La función `SECURITY INVOKER` registra directamente `session_user`, `current_user`, `current_database()`, `current_setting('application_name')`, `TG_TABLE_NAME` y `TG_OP` (`:98–133`). Las consultas finales comparan esos hechos con lo esperado, tras las respuestas del flujo HTTP (`:237–265`). Las lecturas ven las transacciones confirmadas. El setup del propietario ocurre antes de los triggers; el sondeo directo de privilegios usa otro `application_name` y no escribe en estas tablas.

Así, el PASS acredita cinco escrituras del flujo real bajo la cuenta restringida: tres del factor y dos inserciones de sesión. El foco comprueba además identidad real en PostgreSQL, ausencia de privilegios administrativos/propiedad/CREATE y rechazo efectivo de DDL (`:43–70`). No se basa solo en que el test construyera una cadena de conexión con el nombre deseado.

El mismo foco comprueba hash y vigencia del desafío, ausencia de sesión previa al segundo factor, nuevos tokens/CSRF, consumo del desafío y atributos Secure, HttpOnly, SameSite, Path, Max-Age y borrado de su cookie (`:164–235`, `:294–312`). Esto complementa la carencia de cobertura original de cookies registrada como P3. Sigue siendo TestServer y encabezados: no acredita TCP, TLS ni la política efectiva de un navegador. La mejora P3 de restaurar variables mediante `finally` en el fixture original continúa abierta; el foco independiente sí utiliza `finally`.

Recibos leídos, sin credenciales:

| Recibo | SHA256 |
|---|---|
| `.local/mfa-l1-r2-codex-20261025/attempt-2/review-result.json` | `4a9aa31b250eb0db65b5e7e024f01285f05a993125f8311d7ceb96da09e3235e` |
| `.local/mfa-l1-r2-codex-20261025/attempt-3/review-result.json` | `134ebb2015b69b4ece3c13ce26a24e157080b11fd0d41aea63b6662636c32a6c` |

La evidencia respalda el backend probado de enrolamiento/verificación de L1 y su revisión independiente. **No cierra F-07 ni F-12 completos:** quedan proveedor real de custodia D2, interfaz, recuperación completa, candidata y pruebas del entorno de entrega. La propuesta de acreditar F-07.01 y F-07.03 corresponde al coordinador en el ledger; este informe no cambia porcentajes ni acredita disponibilidad de MFA en QA o producción.

## Adenda · clasificación del escaneo de este bloque

Se revisaron por lectura `clasificar_escaneo.py` y `CLASIFICACION-ESCANEO.json`, sin repetir gitleaks ni abrir credenciales privadas. El resultado conserva **17 detecciones brutas**: 15 SHA256 de fuentes y dos constantes públicas y explícitamente sintéticas de fixtures temporales. No se informa un resultado bruto de cero.

El clasificador exige la regla concreta de ese informe, contrasta los 15 valores con el manifiesto y recalcula el SHA256 del archivo correspondiente. Para las otras dos detecciones exige el literal exacto del fixture conocido y la igualdad de bytes con la copia entregada, cuyo uso en bases temporales ya se revisó en este lote. La clasificación no descansa solo en que el detector coincida con una cadena hexadecimal o con un nombre `Password`.

Conforme con esa clasificación acotada: **0 detecciones sin clasificar, sin reglas de supresión añadidas**. Es una clasificación del escaneo concreto de este bloque, no un escaneo nuevo de este revisor ni una afirmación de que todo el repositorio y su historial estén libres de secretos.
