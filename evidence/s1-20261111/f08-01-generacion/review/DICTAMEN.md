# Revisión independiente de F-08.01

11.11.2026. Revisor: agente `f0801_review`, perfil `rackclick_security`, distinto del coordinador que añadió la prueba de concurrencia. Sólo escribí este dictamen. No modifiqué producto, pruebas compartidas, ledger, instalaciones ni datos existentes.

**Dictamen favorable para el literal técnico de F-08.01:** diez códigos propios, entrega inicial única y almacenamiento de hashes con sal independientes de la clave TOTP. No encontré hallazgos de seguridad bloqueantes en este alcance. La conformidad se limita a este checkpoint: no acredita el resto de F-08, generación automática al confirmar el enrolamiento, custodia efectiva en una candidata instalada ni aceptación de Wascar.

## Fuentes y símbolos consultados

Se leyeron AGENTS.md, BRIEFING-MAESTRO, EQUIPO-Y-SKILLS, el perfil `.codex/agents/security.toml`, continuidad y planificación vigentes, el literal de F-08.01 en el ledger, el paso 24 del plan numerado, D2 y el procedimiento público del punto 3. Se contrastaron sus resultados, revisión final, comparación de fuentes, resultados C# y Edge históricos. Para esta tanda se leyeron RESULTADOS.md, MATRIZ-CRITERIO.md, FOCO.json, FRONTEND.json, FUENTES.json y CAMBIOS.patch.

Archivos de código y símbolos principales:

| Ruta | Qué se comprobó |
|---|---|
| `development/server/src/RackClick.Server/MfaRecoveryCodeCodec.cs` | `NewCode`, `Hash`, `Matches`, `Normalize`, `Derive`: aleatoriedad, entropía por construcción, sal, formato y vínculo de cuenta |
| `development/server/src/RackClick.Server/MfaAccountRecoveryCodes.cs` | `GenerateOwnRecoveryCodes`, `ReadOwnRecoveryCodeStatus`, `ReadOwnRecoveryCodesReceipt`, `RecoveryReceipt`, `RecoveryFactorActive`: autoridad, persistencia y entrega |
| `development/server/src/RackClick.Server/MfaRecoveryCodesEndpoints.cs` | `MapMfaRecoveryCodes`: rutas propias, actor, revisión, idempotencia y limitador |
| `development/server/src/RackClick.Server/MfaAccountManagement.cs` | `RequireMfaManagementActor`, `MfaSessionVerified`: sesión actual y segundo factor comprobados en servidor |
| `development/server/src/RackClick.Server/PostgresStore.cs` | `LockOperation`, `RequireCurrentSession`: serialización y revalidación de sesión después de bloqueos |
| `development/server/src/RackClick.Server/Program.cs` | Middleware de sesión, Origin, CSRF, no-store y tratamiento de errores; diff frente a la copia compilada del punto 3 |
| `development/server/src/RackClick.Server/OpenApiMfaRecoveryCodes.cs` y `OpenApiDocument.cs` | Rutas y descripción de entrega inicial frente a recibos sin valores |
| `development/server/database/014-mfa.sql` | `app_mfa_recovery_code`: IDs, hash y estado de consumo; no columna con valores originales |
| `development/frontend/src/mfa-recovery.ts` | Generación, validación de respuestas, recibos, actor antes/después de awaits y journal con sólo IDs/revisión |
| `development/frontend/src/MfaRecoveryCodesPanel.jsx` y `MfaAccountPanel.jsx` | Generación expresa, valores en estado de memoria, descarga/ocultación y acceso desde la cuenta propia |
| `development/frontend/src/api.ts`, `mfa-recovery-words.ts`, `MfaChallengeForm.jsx` y `mfa-words.ts` | Peticiones sin caché/reintento automático, integración y textos existentes |
| `development/server/tests/RackClick.Quality.Tests/MfaRecoveryCodesTests.cs` | Codec y cuatro casos existentes de generación/autoridad/recibo/rollback |
| `development/server/tests/RackClick.Quality.Tests/MfaRecoveryHttpTests.cs` | `OwnGenerationKeepsOriginCsrfActorPasswordAndCodeFreeReplayGuards` |
| `development/server/tests/RackClick.Quality.Tests/MfaRecoveryCodeGenerationConcurrencyTests.cs` | `TheSameConcurrentGenerationDisclosesTenCodesInOnlyOneResponse`, único test añadido |
| `development/server/tests/RackClick.Quality.Tests/MfaAccountManagementTests.cs` | `Laboratory`: cuenta, sesión, factor, roles separados, snapshot y aislamiento |
| `development/frontend/tests/mfa-recovery.test.mjs` y `browser-mfa-recovery.mjs` | Cobertura Node actual y alcance real del Edge histórico |

`MfaStore.Recovery.cs`, `MfaStore.Enrollment.cs` y `MfaStore.cs` se contrastaron por identidad y como contexto de la revisión anterior; esta revisión no acredita sus recorridos de canje o reenrolamiento.

## Identidad y comprobación técnica

Comparé directamente 20 archivos MFA incluidos en la comparación final del punto 3: 19 conservan sus SHA256 y sólo Program.cs difiere. Otros cinco archivos de apoyo, incluida SQL014 y el fixture, coinciden con aquella copia de fuentes. La copia antigua de Program conserva el pin publicado `15bc5e30…`; su diff actual añade modos CLI, conexión protegida, admisión de mantenimiento, guardia de arranque y monitor. No cambia las rutas de generación ni sus controles de sesión, Origin, CSRF o caché. No se exige que un Program posterior conserve un hash histórico.

Verifiqué las 245 filas de fuentes de FUENTES.json contra sus bytes actuales, sin diferencias: 227 de producto, una prueba nueva y 17 referencias del punto 3. Comparé además las 227 filas de producto con el manifiesto de F-07.05: mismas rutas y hashes. El test nuevo coincide en raíz y freeze con SHA256 `4b290e0c5fc5695e93847add74ecb92880ad0e16bea674ffe2aeaecdde4cd513`.

La fuente toma 16 bytes de `RandomNumberGenerator` por código: 128 bits de entrada aleatoria, representados como 32 hexadecimales. Cada hash tiene otra sal aleatoria de 16 bytes y un dominio versionado con Systemhaus y usuario. SHA256 aquí protege valores aleatorios de alta entropía; no se traslada ese criterio a contraseñas humanas. La derivación no consulta la semilla ni el proveedor TOTP.

La generación comprueba sesión MFA, contraseña actual, factor activo, revisión y operación propia. Serializa solicitudes y confirma conjuntamente hashes, revisión, auditoría y recibo. Sólo tras el commit devuelve los valores en memoria; `RecoveryReceipt` fuerza `codesAvailable=false` y `codes=null`. El journal del navegador rechaza campos adicionales con contraseñas, códigos o semillas.

## Ejecución propia

Ejecuté una sola repetición independiente, sin compilar ni repetir el conjunto completo:

```powershell
C:/Python312/python.exe -B .local/f0801-ac6e2910/run_focus.py --concurrency-only
```

**1/1 PASS, 0 fallos y 0 omisiones**, Windows y PostgreSQL 17.11, esquema 46. Se inspeccionaron previamente el runner y `development/server/tests/pg_support.py`: crean un directorio/clúster nuevo, no reutilizan servicios o bases instaladas e inyectan las credenciales sólo al proceso hijo. Se comprobaron los pines antes y después:

| Binario | SHA256 |
|---|---|
| RackClick.Server.dll | `e2d3757943151bb5897871d07a95e07949f7a123a59ecb77ae82b93400f09b00` |
| RackClick.Quality.Tests.dll | `bd042f26048300263102e0b5fa15e94fa2f522765cf66cc2d40abd82bdf0dc0e` |

El caso retiene la fila Systemhaus hasta observar al menos dos PID bloqueados en la base nueva. Comprueba exactamente una respuesta con diez valores y otra sin ellos, diez hashes persistidos, una operación, una auditoría y revisión común; replay y recibo sin valores y snapshot invariable. También busca valores agrupados y normalizados en el snapshot, sin imprimirlos. La cuenta y el factor son sintéticos; generación no descifra su material TOTP.

El resultado sanitizado y el nombre/resultado del TRX propio quedaron bajo `.local/labs/f0801-generation-7add2d58dfc74b1583450c5bb96644f1`. Se confirmó `ownClusterStopped=true` y ausencia de `data/postmaster.pid`. No se consultaron credenciales, cuerpos ni logs privados.

## Ejecuciones ajenas contrastadas

FOCO.json registra la ejecución del coordinador: **15/15 PASS, 0 omitidas**, compuestos por nueve codec, cuatro almacén, un HTTP y el caso nuevo. FRONTEND.json registra **10/10 Node PASS, 0 omitidas**; conserva el aviso existente `MODULE_TYPELESS_PACKAGE_JSON`. No ejecuté esos 15 o diez casos como conjunto propio, ni su build.

Los cuatro focos existentes de almacén son `OwnGenerationStoresOnlySaltedHashesAndSafeReceiptAndOnlyShowsCodesOnce`, `GenerationNeedsMfaCurrentPasswordActiveFactorAndMatchingRevision`, `AnotherActorCannotReadAReceiptAndConsumedRequestCannotChangeItsIntent` y `GenerationAuditFailureRollsBackCodesRevisionAndReceipt`. La repetición propia del caso nuevo no añade otro caso al total de cobertura.

La ejecución histórica del punto 3 conserva sus 104 casos y su Edge identificado. Su revisión distingue el fallo OpenAPI inicial, el arreglo y la ejecución final; no se convierten intentos previos fallidos en resultados actuales. Edge y sus negativos independientes se reutilizan como evidencia histórica sobre fuentes iguales; no los repetí ahora.

## Hallazgos y límites

- **Bloqueantes de seguridad: ninguno encontrado** en el literal técnico inspeccionado.
- **Límite de conformidad documental:** D2 §3a histórico pide generar al confirmar el enrolamiento. El flujo revisado usa generación expresa posterior con contraseña y sesión MFA; el plan numerado ya indica conciliación de esa implementación. El literal técnico comprobado no acredita aquella automatización ni una nueva aceptación de su timing.
- **Límite operativo pendiente:** no se ensayaron custodia/uso en candidata instalada, último administrador, emergencia, SID efectivo del servicio, TLS, instalación o QA de Wascar. Independencia criptográfica respecto a TOTP no prueba que arranque un host cuyo almacén de claves se perdió.
- **Límite de entrega única:** el usuario puede leer o descargar varias veces los valores mientras conserva la primera respuesta visible. El servidor no vuelve a entregarlos mediante status, recibo o replay. No se afirma borrado universal de strings y copias en memoria.
- **Límite de revisión:** no se ejecutaron canje, reenrolamiento, consumo concurrente, rotación, restauración o los checkpoints F-08.02 a F-08.05. No se efectuó auditoría de todo el historial de secretos ni análisis físico de memoria.

El aviso inicial sobre un posible analizador xUnit fue cautela basada en un antecedente; el build actual no reprodujo ese error. No es un hallazgo corregido ni una fase roja inventada.

La evidencia permite reutilizar la implementación existente y conciliar F-08.01 en su criterio técnico. Los hitos operativos y la aceptación continúan pendientes; este dictamen no cambia pesos, puntos ni el porcentaje global del producto.
