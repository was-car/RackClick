# F-08.05 · dictamen independiente del cierre técnico

11.11.2026. Revisor `f0805_review`, distinto del coordinador, perfil `rackclick_security` comprobado en `.codex/agents/security.toml`. S1 autorizado. Sólo escribí este dictamen y auxiliares privados propios; no edité producto, pruebas compartidas, guiones de navegador, ledger, QA ni metadatos del coordinador.

**Dictamen favorable al criterio técnico completo F-08 y a F-08.05, con una observación media abierta de fiabilidad del recorrido de navegador, cuya causa no está acreditada.** La repetición propia dio **6/6 PASS, cero fallos y omisiones**. El foco PG/HTTP del coordinador dio **12/12 PASS** y sus resultados se contrastaron contra el TRX privado. La evidencia no permite anunciar una batería de navegador íntegramente verde ni una GUI estable: conserva tres fallos y cuatro positivos del caso de recuperación, con atribución separada. No encontré un incumplimiento reproducido de los invariantes de seguridad de F-08 que impida esta acreditación técnica. Integración de candidata y aceptación/custodia de Wascar permanecen pendientes.

## Criterio y decisión de acreditación

Se contrastó el literal del ledger: «Cada código sirve una sola vez incluso en concurrencia; recuperación no abre API antes del estado autorizado; reenrolamiento y revocación/auditoría sin secretos probados por revisor distinto», junto con sus cinco checkpoints, los pasos 24–28, D2 y gracia45/exención global.

| Checkpoint | Juicio técnico y evidencia |
|---|---|
| F-08.01 | Acreditado y conservado: generación propia expresa de diez valores, hashes con sal ligados a cuenta, una única respuesta con valores por operación. Repetí el caso con dos solicitudes realmente solapadas; recibo y replay no vuelven a revelarlos. |
| F-08.02 | Acreditado y conservado: contraseña/código sólo conceden un desafío enroll nuevo. Inspeccioné fuente y caso HTTP ordinario/global; el foco final del coordinador repite ambos. Sólo la confirmación del factor nuevo crea sesión/CSRF. |
| F-08.03 | Acreditado y conservado: consumo del conjunto antiguo, revocación, auditoría y desafío nuevo en una transacción. Repetí los dos canjes solapados y el rollback de auditoría; otra cuenta y la política global se conservan. |
| F-08.04 | Acreditado y conservado: el único global recupera su misma identidad/autoridad tras confirmar otro factor y repone expresamente códigos. Se conserva la guarda del último administrador. Repetí los dos negativos disable/pending sobre la corrección D2 ya revisada. |
| F-08.05 | Elegible como `done`, con su peso existente de 1/2: criterio conjunto contrastado, repetición independiente y límites registrados aquí. No concede crédito adicional por repetir casos ni por observar la incidencia de navegador. |

Son elegibles `definition_confirmed`, `implementation_complete`, `technical_tests_same_scope` e `independent_review_same_scope` **para este resultado técnico**, con la observación abierta siguiente expresamente asociada a sus pruebas. `integrated_current_candidate` y `target_acceptance` deben seguir `pending`. Esto no cierra toda la GUI MFA, la operación Windows, F-09 o la entrega completa.

La generación implementada es una acción expresa posterior al enrolamiento, con contraseña y sesión MFA. Se conserva la conciliación documentada del plan numerado y del procedimiento del punto3; no se atribuye generación automática al confirmar el enrolamiento ni se garantiza que alguien haya guardado los códigos. No se reabre la decisión de custodia ni se sustituye gracia45 por la exigencia histórica inmediata.

## Fuentes y símbolos consultados

Se leyeron AGENTS, BRIEFING-MAESTRO, EQUIPO-Y-SKILLS, el perfil security y el plan F0805; las secciones pertinentes de continuidad, fundamento/inicio S1, contrato, aceptación, mapa RC9/R3, README y progreso; ledger F-08 completo, pasos24–28, D2, gracia45 y PUNTO3-FUNCIONES-PENDIENTES. Se consultaron las cuatro revisiones F0801–.04 y sus fuentes/resultados, incluida la reproducción roja/verde D2 de la revisión final F0804. Son evidencias previas de otros ejecutores, no ejecuciones propias nuevas.

| Archivo o grupo | Símbolos o contenido inspeccionado |
|---|---|
| `development/server/src/RackClick.Server/MfaRecoveryCodeCodec.cs` | `NewCode`, `Hash`, `Matches`, `Normalize`, `Derive`: CSPRNG, sal/dominio, vínculo Systemhaus/usuario y comparación de hashes. |
| `MfaAccountRecoveryCodes.cs` | `GenerateOwnRecoveryCodes`, `ReadOwnRecoveryCodeStatus`, `ReadOwnRecoveryCodesReceipt`, `RecoveryReceipt`, `RecoveryFactorActive`: autoridad, serialización, commit y entrega. |
| `MfaRecoveryCodesEndpoints.cs`, `Program.cs` | `MapMfaRecoveryCodes`; middleware de sesión/Origin/CSRF/no-store y rutas login/recover/start/confirm, cookies y normalización de purpose verify. |
| `MfaStore.Recovery.cs` | `RedeemRecoveryCode`, `RecoveryEnrollmentChallenge`: validación, bloqueos, revocaciones, auditoría y respuesta sin sesión. |
| `MfaStore.Enrollment.cs` | `StartEnrollment`, `ConfirmEnrollment`, `LockChallenge`, `ChallengeOpen`, `NeedsEnrollment`, `WriteAudit`: factor nuevo y sesión transaccional. |
| `PostgresStore.Authentication.cs`, `PostgresStore.cs` | `AuthenticateForLogin`, `AuthenticateCore`, `LoginOutcome`, `Session`, `RequireCurrentSession`, `Command`, `Can`, `LockOperation`: contraseña, pending prioritario, ámbito y sesión real. |
| `MfaAccountManagement.cs`, `MfaGraceEnforcement.cs` | `ChangeMfaAccount`, `RequireMfaManagementActor`, `MfaSessionVerified`, `MfaAccountState`, `MfaGraceDueSql`, `EnforceMfaGrace`: guard D2, reset/enable y conservación de pending/fechas/exención. |
| `AdminUsers.cs`, `AdminUserState.cs`, `database/014-mfa.sql` | `RequireSecurity`, `ReadUsers`, `SetOrCancelUserState`/`last_admin_required`; identidad compuesta y columnas de hash/consumo de MFA. |
| Cuatro pruebas F0801–.04 | `MfaRecoveryCodeGenerationConcurrencyTests`, `MfaRestrictedRecoveryHttpTests`, `MfaRecoveryRedemptionTransactionTests`, `MfaLastAdministratorRecoveryTests`: positivos, negativos, testigos y snapshots. |
| `MfaRecoveryCodesTests.cs`, `MfaAccountManagementTests.cs` | Rollback/replay y helpers `AuditFailure`, `Laboratory.Policy`, `SnapshotAll`, `DisposeAsync`; roles y preparación sintéticos. |
| `MfaRecoveryHttpTests.cs`, `MfaDashboardHttpTests.cs` | Casos opcionales de navegador, requisitos de entorno, host Kestrel/DI y comprobaciones finales. |
| `development/frontend/src/MfaRecoveryCodesPanel.jsx` | `perform`, `hide`, `download`, ámbito de cuenta y valores en estado de memoria. |
| `development/frontend/tests/browser-mfa-recovery.mjs` y copia diagnóstica privada | `enroll`, etapas de generación/lectura/unicidad/formato/storage/ocultación/canje; categorías de salida sin valores. |
| `development/server/tests/pg_support.py`, drivers privados | `Lab.start`, `environment`, `close`, aislamiento, pines/filtros, parada propia y preparación privada del frontend. |

Las rutas cortas C# de la tabla pertenecen a `development/server/src/RackClick.Server/`; los tests pertenecen a `development/server/tests/RackClick.Quality.Tests/`. Se reutilizó la investigación oficial .NET10/PostgreSQL17 registrada en RESULTADOS de F0801 y F0803, sin consulta web nueva, dependencia o versión nueva. Se aplicaron las skills de binlogs y verificación.

## Inspección de seguridad e identidad

La generación exige sesión actual con MFA, contraseña, factor activo, revisión y operación propia. El bloqueo de operación y Systemhaus serializa la solicitud duplicada; la transacción guarda sólo hashes/metadatos. Los valores salen después del commit y `RecoveryReceipt` fuerza `CodesAvailable=false,Codes=null`.

El canje exige desafío verify y CSRF, cuenta utilizable, factor activo/no bloqueado, política/revisión vigentes y ausencia de pending. Revalida caducidad después de esperar los bloqueos de códigos; no solicita claves TOTP. Consume el conjunto antiguo completo, deshabilita el factor, fija required/pending, revoca sesiones/desafíos de esa cuenta e inserta sólo enroll. Los comandos reciben db/tx y valores parametrizados; la auditoría precede al commit. La confirmación posterior activa un factor nuevo y emite sesión/CSRF nuevos dentro de su transacción. El middleware exige un registro de sesión para la API, no acepta un token de desafío como autoridad.

La corrección D2 rechaza disable durante pending antes de sus escrituras y deja `CanDisable=false`. Reset fija pending=true; enable lo conserva si ya existía; la aplicación de gracia usa OR y no lo cancela. La exención por ambas capacidades globales no elimina una recuperación pendiente. El global puede desactivar su factor activo no pendiente conforme a Wascar. La guarda `last_admin_required` protege al último `security.manage` global; la exención MFA requiere además `systemhaus.manage` global. No se confunden esas definiciones ni se otorga autoridad por nombre de rol.

Comprobación propia: **227/227 fuentes coinciden en raíz y freeze con F0804**, y las cuatro fuentes de pruebas añadidas son idénticas. Frente a F0801 sólo difiere `MfaAccountManagement.cs`, el guard ya corregido en F0804. Las 29 referencias de fuentes del punto3 conservan sus hashes en raíz/freeze. Los sellos previos verifican 9/9/9/12 archivos, sin discrepancias. Se recalcularon además las 250 filas con ruta/hash de FUENTES F0805 y los 18 artefactos del frontend privado, todos coincidentes. No se afirma identidad binaria con D/E.

## Ejecución propia y contraste de resultados ajenos

```powershell
C:/Python312/python.exe -X utf8 -B .local/f0805-53a7f4b2/run_focus.py --review
```

**Salida0, 6/6 PASS, cero fallos/omitidos**, Windows, PostgreSQL17.11 comprobado con el ejecutable fijado, esquema46. Sin restore/build .NET. El clúster propio `f0805-review-88a249ffd28044dd9effe3d4a2cd25f0` quedó detenido, con `postmaster.pid` ausente y un binlog privado existente. Los pines coinciden antes/después.

| Casos propios | Resultado y comprobación relevante |
|---|---|
| `TheSameConcurrentGenerationDisclosesTenCodesInOnlyOneResponse` (1) | Dos PID bloqueados observados; una entrega de diez valores, otra sin ellos; operación/auditoría únicas, recibo/replay sin valores. |
| `OverlappingRedemptionsCommitOneAccountRecoveryAndLeaveAnotherAccountUntouched` (2) | Mismo código o dos distintos; dos PID esperando, un ganador enroll; seis relaciones bajo el txid/rol runtime ganador, otra cuenta y gracia intactas. |
| `DisableCannotCancelRecoveryPendingEvenWithAnAuthorizedMfaSession` (2) | Ruta administrativa y propia global: error409/código exacto, CanDisable=false, snapshot invariable y login sólo enroll. La defensa propia usa una sesión verificada inyectada de fixture, que el login normal no emite durante pending. |
| `RecoveryAuditFailureRollsBackEverythingIncludingTheUsedCode` (1) | Fallo forzado de audit; igualdad del snapshot de diez tablas, incluido el código presentado. |

| Artefacto propio o binario fijado | SHA256 |
|---|---|
| DLL servidor | `dd285c4f7561d8f7e678178a12d399782f0c2142712d16bff10ec87762f85d0e` |
| DLL pruebas | `1d0332b69238239aa6b8f4214f7a8fd186c26945dc99f6e7c905998a028605c4` |
| TRX propio | `f77ba10dfd548627f3404fadc28f891518c8a41239517c053862362aa4f952a5` |
| Recibo saneado propio | `d3087f7e52e10f13c98ee99d10391d926f2db1139b1a0236628bb413439bd488` |

Mi lector propio comparó nombres/resultados/counters del TRX, recibo, pines, ausencia de pid y presencia de binlog. Otro lector propio contrastó **el TRX de los12 del coordinador y los siete lanzamientos Edge**, sus resultados JSON y hashes con FOCO/NAVEGADOR-INTENTOS; todos corresponden, incluidos los fallos. Los ocho clústeres del coordinador tienen parada registrada y pid ausente. No abrí sus logs, pgpass, cuerpos HTTP o binlogs. Esas ejecuciones pertenecen al coordinador; no las repetí ni las sumé a mis seis.

Los 68 Node y los 49 seleccionados del paso27 son históricos reutilizados: 48PASS/0FAIL/1NotExecuted, driver1 y discovery posterior. No se convierten en49/49 ni en una ejecución nueva. Tampoco esta revisión vuelve a ejecutar el rojo/verde histórico D2.

## Hallazgos y observaciones

**Alta, histórica y cerrada:** D2-RECOVERY-DISABLE permitía cancelar pending mediante disable y volver a contraseña sola. F0804 conserva su reproducción roja, corrección y verde independiente. Esta revisión inspeccionó el guard y repitió sus dos negativos corregidos; no halló reapertura del defecto.

**Media, abierta: intermitencia de prueba/GUI, origen no acreditado.** El primer lanzamiento Edge fue dashboardPASS/recuperaciónFAIL, exit1. La recuperación original pasó después sin cambio de producto/guion compartido. Las cinco invocaciones instrumentadas dieron FAIL/PASS/FAIL/PASS/PASS: en total, recuperación **4PASS/3FAIL**, no siete casos distintos ni una batería completamente verde. Los fallos quedaron en la etapa amplia generate_codes, sin excepción de runtime observada; una medición fallida vio GET200/POST200. Esa etapa también contiene aserciones de unicidad, formato, storage y ocultación. El botón habilitado medido descarta la explicación inicial de botón deshabilitado. La ocultación inmediatamente comprobada sin espera es una posibilidad estática adicional, **no una causa demostrada**. Las etapas más finas no capturaron otro fallo.

No se ha demostrado pérdida de confidencialidad, doble entrega/canje, sesión prematura o rollback incorrecto mediante esos fallos. Tampoco se ha demostrado que sean exclusivamente un defecto del guion. Por eso no bloqueo el literal técnico de seguridad acreditado por fuente y PG/HTTP, pero dejo abierta la incidencia y excluyo expresamente estabilidad de GUI/compuerta automatizada de entrega. Debe diagnosticarse por etapas sin volcar valores y resolverse antes de usar ese guion como compuerta de candidata; repetir hasta obtener verde no la resuelve. Los guiones privados instrumentados no se fijaron por hash al inicio de cada invocación y no se acreditan como regresión certificada de un cambio.

**Baja, documental y resuelta durante la revisión:** la matriz atribuía inicialmente «HTTP409» a los dos negativos de pending. El coordinador lo precisó como error409 del almacén; esas repeticiones no se presentan como dos ensayos HTTP propios.

## Límites que permanecen

- Factores/sesiones iniciales de varios fixtures son sintéticos; host de pruebas con claves por DI. Edge usa Kestrel HTTP loopback y perfil nuevo, no HTTPS nativo, SID efectivo, DPAPI ni servicio instalado. La independencia del hash/canje respecto a TOTP no prueba que un host sin almacén pueda arrancar.
- Esta vía presupone host disponible, cuenta utilizable, contraseña y códigos válidos previamente custodiados. Pérdida total, sobre/rotación, mantenimiento local y emergencia F-09 no quedan resueltos por F-08.
- Los snapshots de secretos conocidos cubren diez tablas de identidad/MFA/Systemhaus/operación/auditoría; la otra cuenta se compara en seis colecciones. No son una auditoría física de memoria, todo el disco/logs, historial, dependencias, inventario o todos los ámbitos/endpoints.
- El testigo SQL prueba la transacción/rol de las seis relaciones del caso; no prueba apagón, reinicio durante commit o durabilidad universal. Sus triggers/DDL pertenecen sólo al fixture propietario, no al runtime del producto.
- Se contrastaron ficha28, plan, matriz, RESULTADOS, FUENTES, FOCO, FRONTEND, NAVEGADOR-INTENTOS y OBSERVACION-NAVEGADOR. La conciliación posterior de ledger/índices y su verificación corresponden al coordinador. No modifiqué los175 casos QA, notas/resultados de Wascar, pesos ni porcentajes. La estimación global histórica del78% no se recalcula por esta revisión; el índice del cierre restante conserva su contabilidad separada.

No hubo operaciones sobre D/E/VM, servicios instalados, cuentas Windows, instalaciones, commits, push o despliegue por el revisor. Conexiones, códigos, cookies, semillas, logs, TRX y binlogs permanecen privados. El único archivo público escrito por este revisor es este dictamen.
