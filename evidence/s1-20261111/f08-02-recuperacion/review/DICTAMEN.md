# Dictamen independiente · paso 25/F-08.02

11.11.2026. Revisor `f0802_review`, perfil security, distinto del implementador de la nueva prueba y del runner. Escritura propia limitada a este dictamen y a la salida privada del laboratorio nuevo. No modifiqué producto, pruebas compartidas, ledger, QA o trabajo ajeno; sin operaciones sobre D/E, VM, servicios, cuentas o bases instaladas, commits o publicación.

**Dictamen favorable exclusivamente al cierre técnico de F-08.02 con su peso existente de 1/2 punto.** Contraseña y código conceden un desafío nuevo de enrolamiento, sin sesión API hasta confirmar el factor nuevo. La implementación existente, la evidencia histórica contrastada y los dos escenarios HTTP repetidos por este revisor cubren ese literal. No se identifican hallazgos de producto P1/P2 pendientes en este alcance. F-08.03–.05 y los hitos completos de F-08 permanecen pendientes.

## Criterio, alcance y fuentes consultadas

Se leyeron AGENTS, BRIEFING-MAESTRO, perfil `.codex/agents/security.toml`, EQUIPO-Y-SKILLS, plan F0802, literal del ledger y paso025, decisión D2 con sus adendas, PUNTO3-FUNCIONES-PENDIENTES, las entradas vigentes de continuidad/progreso y el README del servidor. Se contrastaron la revisión final del punto3 con sus adendas, `COMPARACION-FUENTES-FINAL.json`, el dictamen F0705 y FUENTES de F0801. Se reutiliza la investigación oficial registrada en el plan; no se introdujo dependencia ni se hizo una investigación web adicional para este dictamen.

Archivos y símbolos de producto inspeccionados:

- `development/server/src/RackClick.Server/MfaStore.Recovery.cs`: `RecoveryEnrollmentChallenge`, `RedeemRecoveryCode`; finalidad verify, vínculo Systemhaus/usuario, CSRF, bloqueos/revalidación y respuesta sin sesión. El canje genera un desafío enroll nuevo y revoca sesiones previas antes del commit.
- `MfaStore.Enrollment.cs`: `StartEnrollment`, `ConfirmEnrollment`, `LockChallenge`, `ChallengeOpen`, `NeedsEnrollment`, `Burn` y llamadas de auditoría. Confirmar activa el factor, retira pending, cambia revisión/consume desafío e inserta una sesión nueva dentro de la transacción. Se inspeccionó el uso de `Burn`; su definición no fue objeto de una revisión nueva independiente del conjunto previo.
- `PostgresStore.Authentication.cs`: `AuthenticateCore`, `AuthenticateForLogin`, `LoginOutcome`; contraseña previa y precedencia de enrollment_pending sobre la posible exención global.
- `PostgresStore.cs`: `Session` y su consulta parametrizada; un token de desafío no es un registro de sesión. `MfaGraceEnforcement.cs`: `MfaGraceDueSql`, `MfaSessionAllowedSql`, `EnforceMfaGrace`, `EnsureMfaGracePolicy`. `MfaAccountManagement.cs`: `MfaAccountState` y capacidades globales security.manage/systemhaus.manage. No existe un archivo o símbolo literal `MfaEffectivePolicy` en este árbol: esos son los componentes efectivos consultados.
- `Program.cs`: composición, guardas de Host/HTTPS/Origin, excepciones exactas de autenticación, comprobación de sesión/CSRF y rutas login/verify/recover/start/confirm. recover devuelve202 con sólo mfaRequired/purpose/csrf, borra cookie de sesión y emite cookie de desafío; confirm emite la sesión.
- `development/frontend/src/api.ts`: `recoverMfa`, `requireChallenge`, `startMfaEnrollment`, `finishMfa`, `me`; recuperación conserva la autenticación pendiente y no instala actor/CSRF de API ni llama a /me. `MfaChallengeForm.jsx`: reemplazo por un formulario enroll y llamada onComplete sólo después de confirmar. `mfa-recovery.ts`: contrato y journal sin códigos/contraseñas. El resto de módulos de la revisión histórica se contrastó por hash, sin presentarlo como otra revisión exhaustiva de su contenido.

Se leyeron completos la prueba nueva y su diff `CAMBIOS.patch`, `MfaAccountManagementTests.Laboratory` —Create, AddUser, Session, Policy, SnapshotAll, DisposeAsync—, `MfaRecoveryHttpTests` y los focos pertinentes de `MfaRecoveryCodesTests`. Antes de ejecutar se inspeccionaron `.local/f0802-8184c4f9/run_focus.py` y `development/server/tests/pg_support.py`: clúster nuevo bajo .local/labs, credenciales aleatorias privadas, sin reutilizar un clúster, roles/bases sintéticos y parada delimitada.

## Identidad y reutilización

Comprobación propia de las 227 entradas de producto F0801: **227/227 coinciden en raíz y freeze**, sin diferencias. La prueba nueva coincide entre ambas copias y FUENTES. También se recalcularon las 227 entradas, una nueva, 29 del punto 3 y 10 referencias de `FUENTES.json`: todas corresponden a los archivos actuales.

De las 30 fuentes de `COMPARACION-FUENTES-FINAL.json`, 29 conservan su hash. Se comparó el Program histórico real, con hash `15bc5e304f16800f8e28266b853a5aba5b0880a9229b35ebc1b355dafa1ee174`, contra el actual: las diferencias añaden CLI de mantenimiento, resolución protegida de conexión y admisión/monitor de mantenimiento. Las rutas/cookies y la comprobación de sesión/Origin/CSRF inspeccionadas no cambiaron. No se declara identidad de todo Program ni identidad binaria con la candidata instalada.

El punto 3 ya implementó y revisó contraseña→verify→canje→enroll→confirmación→sesión. Su revisión final y Edge son históricos del 02.11; no los ejecuté de nuevo. El dictamen F0705 conserva sus pruebas propias de enrolamiento/confirmación y sus límites; no transfiere DPAPI real a los dos casos sintéticos de esta tanda.

## Ejecución propia

```powershell
C:/Python312/python.exe -B .local/f0802-8184c4f9/run_focus.py --new-only
```

**Salida 0; 2/2 PASS, 0 fallos/omitidas.** Se leyeron los dos UnitTestResult del TRX, globalAdministrator False y True, además del agregado. PostgreSQL 17.11 comprobado mediante el ejecutable fijado; esquema 46. Clúster propio `f0802-restricted-121e4da4e3f6421ba8a96e9b94213296` detenido, con postmaster.pid ausente. El runner verifica ambos pines antes/después. No ejecuté build, restore, Node ni otra regresión.

Los dos escenarios comprueban:

- Contraseña inválida sin desafío/sesión; código válido sin desafío previo rechazado sin consumir los diez códigos.
- Login válido verify y canje HTTP 202 sin cookie de sesión utilizable; cuerpo de tres campos, propósito enroll y token/CSRF nuevos. Cookies declaradas HttpOnly/Secure/SameSite Strict y Path correspondiente.
- Cuatro estados restringidos: después del canje, después de start, después de confirmación inválida y con otro login mientras pending. En cada uno, GET /me, GET /customers, POST /customers y POST /me/preferences devuelven 401 con cookie MFA, token renombrado Session, sesión anterior y sin cookie; cero sesiones nuevas y snapshot de diez tablas sin cambios.
- Sólo confirmación válida obtiene sesión/CSRF nuevos, /me 200, sesión anterior 401, un factor activo y una sesión MFA. La política de 45 días permanece igual; la cuenta global con pending explícito tampoco evade el factor nuevo.
- Rol runtime separado del propietario, creado NOSUPERUSER/NOCREATEDB/NOCREATEROLE por el helper; CREATE TABLE falla con 42501. El host usa su conexión runtime, sin cambiar migraciones ni permisos del producto.

| Identidad comprobada | SHA256 |
|---|---|
| RackClick.Server.dll | `504f961eaf7196c7ef81b350d9197c78c3086ba644cf762ad97410a3bd0137d9` |
| RackClick.Quality.Tests.dll | `c57e04c28f4265b2e0129be4e0d9d15fb5468aa957814f8803a23c63fe8b482a` |
| MfaRestrictedRecoveryHttpTests.cs | `51e1bcaf6a03b06560b245c1344f0aea4ab079150896f40288c4767d848b6594` |
| run_focus.py | `d01a14fe5fb1a6d101b0c9d19170a8c58acf6d3bce4c06cadd3a0a86c72024fc` |
| pg_support.py | `fa5da11b657660f5335b6b5aef17387f8d0ceca5a1b0b095d2b4a09c8cdb1de5` |
| TRX propio | `9fe2d1553cba70ccd596ae699f2055b8f323ccf867491a062d0daa5f2dc8f994` |
| result-sanitized.json propio | `546ce951ac975335a1a1e2869afa8e1c099ba9649ce4469f663a355af02267fd` |

TRX y recibo propios permanecen en la carpeta privada de ese clúster. Se extrajeron sólo nombres/resultados y hashes; no se abrieron conexiones, pgpass, códigos, secretos, logs HTTP ni binlogs.

## Ejecuciones ajenas contrastadas

Se leyeron `FOCO.json`, `FRONTEND.json`, RESULTADOS y MATRIZ de esta tanda. Además se inspeccionaron el recibo saneado y los seis resultados individuales del TRX del coordinador en `f0802-restricted-e5d358285db14308a100279fb9d77109`: **6/6 PASS, 0 omitidas**, mismo par de DLL, clúster detenido. Son dos casos nuevos y cuatro existentes de canje/enrolamiento/Origin/CSRF; no seis recorridos nuevos.

`FRONTEND.json` registra **20/20 Node, 0 fallos/omitidas**, módulos mfa-api y mfa-recovery, sin navegador nuevo y con MODULE_TYPELESS_PACKAGE_JSON preexistente. Esa ejecución pertenece al coordinador: no repetí Node ni inspeccioné su log privado. Se leyó únicamente el resumen final permitido del build privado: éxito, 0 advertencias/errores. Tampoco se presenta como build propio.

## Hallazgos y límites

**Producto: sin hallazgos P1/P2 abiertos en el criterio inspeccionado.** La conclusión depende del contrato y los estados comprobados, no de acumular un número de tests.

**Incidencias de fixture, gravedad baja y resueltas por el coordinador:** primer build con import faltante; primer foco con 4 PASS/2 FAIL porque la preparación agotaba el límite HTTP existente. Sus fallos se conservan y no constituyen una fase roja de producto. La preparación inicial del factor/sesión ahora llama a los mismos métodos de almacén; el canje y todos sus estados/final siguen por HTTP. Se leyó ese cambio sin relajar el limitador ni las aserciones de recuperación.

Los casos usan TestServer y proveedor de claves sintético por DI. No prueban TLS/TCP, aceptación real de cookies por un navegador, DPAPI, SID efectivo, SCM/servicio instalado, instalador, candidata objetivo o QA/adopción de Wascar. La negación HTTP de lecturas/escrituras se comprueba; `SnapshotAll` abarca diez tablas de identidad/MFA/Systemhaus/operación/auditoría, no toda la DB ni el inventario. No se añade aquí un testigo SQL de identidad/transacción como el de F0705.

No se acredita con esta tanda el criterio conjunto de concurrencia/replay/rollback/secretos de F0803, custodia operativa, último administrador F0804, emergencia cuando el proveedor no arranca o cierre global F0805. Tampoco se realizó una auditoría de todos los ámbitos/rutas, historial o dependencias ni un escaneo general de secretos. Los 175 casos QA y resultados de Wascar quedan fuera de esta escritura; QA-163 no se habilita por estas pruebas.

El coordinador puede conciliar sólo F0802, +1/2, conservando los demás checkpoints/hitos de F08 y su contabilidad. Este revisor no modifica ledger ni porcentajes. No hay porcentaje global nuevo: el índice vigente al inicio, 22,63/100, corresponde al cierre restante, no al avance total del producto.
