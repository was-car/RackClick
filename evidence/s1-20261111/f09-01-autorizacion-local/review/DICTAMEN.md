# Dictamen independiente · F-09.01 / paso 29

11.11.2026 · Revisor especializado de seguridad distinto del coordinador implementador. Encargo limitado a la autoridad local de entrada; sin editar producto, pruebas compartidas o metadatos de cierre.

**Favorable exclusivamente para F-09.01 técnico (+1/2).** No se identificaron hallazgos críticos, altos, medios o bajos pendientes dentro del alcance revisado. La compuerta captura el token Windows real antes del host, no acepta autoridad de aplicación y no concede una recuperación. F-09.02–.05 y los seis hitos del resultado completo F-09 deben permanecer pendientes. El ledger estaba íntegramente pendiente al contrastarlo; esta revisión no modifica estados, pesos ni porcentaje global.

## Archivos y símbolos consultados

- `AGENTS.md`, `docs/BRIEFING-MAESTRO.md`, `.codex/agents/security.toml` y `docs/EQUIPO-Y-SKILLS.md`: encargo, separación de funciones y límites S1.
- `docs/CONTINUIDAD-CODEX.md`, documentos iniciales S1/contrato/mapa/aceptación, `development/server/README.md`, `global.json` y `docs/PROGRESO-GLOBAL.md`: contexto y versión fijada. La referencia vigente anterior es 24,63/100 del cierre restante, no un porcentaje global nuevo del producto.
- `docs/D2-CONDICIONES-TECNICAS-F03-02.md` §1/§2.2, `docs/DECISION-D2-CUSTODIA-CLAVE-TOTP.md`, plan numerado pasos 29–33 y `docs/PLAN-CIERRE-RACKCLICK.json`, resultado F-09/checkpoints/hitos: autorización separada de material, transacción, revocación y ensayo operativo.
- `docs/PLAN-F0901-AUTORIZACION-EMERGENCIA.md`, `docs/PASO-029-AUTORIZACION-LOCAL-EMERGENCIA-MFA.md` y `RESULTADOS.md`, `MATRIZ-CRITERIO.md`, `FUENTES.json`, `FOCOS.json`, `MUTACION.json`, `CAMBIOS.patch` de esta evidencia: contrato, trazabilidad y atribución de ejecuciones.
- `development/server/src/RackClick.Server/Program.cs`: reconocimiento/exclusión de modos, rama `mfaEmergencyRecovery` y ubicación anterior a `WebApplication.CreateBuilder` y a `RecoveryAdministrator.Run`.
- `MfaEmergencyRecoveryCommand.cs`: `Run`, `AuthorizationFailure`, `WindowsAuthorityFailure`, `DenialForToken`, declaración nativa `GetTokenInformation` y uso de `SafeAccessTokenHandle`.
- `MfaMaintenanceCommand.RunAsync/IsElevatedAdministrator` y `MfaKeyStoreInitCommand.Run/IsElevatedAdministrator`: patrones existentes consultados; no aprobados nuevamente como operadores completos.
- Pruebas `MfaEmergencyAuthorizationTests`, `MfaEmergencyProcessTests`, `MfaEmergencyHttpTests`, `MfaRestrictedRecoveryHttpTests.RecoveryNeverAuthorizesTheApiUntilTheNewFactorIsConfirmed`; fixture `MfaAccountManagementTests.Laboratory` y `pg_support.Lab/start/close/environment/toolchain`: autoridad, HTTP y aislamiento PostgreSQL.

Se contrastaron también las fuentes oficiales enlazadas en el plan: [WindowsIdentity.GetCurrent](https://learn.microsoft.com/en-us/dotnet/api/system.security.principal.windowsidentity.getcurrent?view=net-10.0), [WindowsPrincipal.IsInRole](https://learn.microsoft.com/en-us/dotnet/api/system.security.principal.windowsprincipal.isinrole?view=net-10.0), [GetTokenInformation](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-gettokeninformation) y [TOKEN_ELEVATION](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-token_elevation). Sustentan la distinción entre identidad efectiva, suplantación y elevación; no sustituyen las ejecuciones descritas abajo.

## Hallazgos y alcance de la conformidad

1. **Sin hallazgo bloqueante de autoridad.** La CLI no consulta claims, roles web, contraseña, stdin, JSON, variables o DI para decidir permisos. Comprueba primero ausencia de suplantación; reconoce SYSTEM por SID conocido y exige pertenencia efectiva a Administradores y elevación nativa para la otra vía. Una lectura de elevación fallida o de tamaño inesperado rechaza. La política privada no es una credencial ni un permiso transferible.
2. **Sin hallazgo de entrada o efectos en este cambio.** El modo exacto y sus siete conflictos se resuelven antes del host/configuración/SQL. `Run` sólo emite rechazo/salida 1; tras autorización positiva de política conserva `mfa_emergency_transition_unavailable`, `operationsApplied=0`, `sessionGranted=false`. No hay preparación de anillo, mutación DB o sesión. `--recover-admin` conserva el recorrido de Restore.
3. **Observación temprana de prueba corregida.** La primera versión permitía varios códigos de rechazo indistintamente. La prueba final exige el código correspondiente al token padre real; mi sonda independiente también exige `mfa_emergency_not_authorized` bajo el token estándar, aunque el entorno declare SYSTEM/elevación. No queda pendiente esa observación.
4. **Límite de evidencia, sin crédito operativo.** No ejecuté un proceso SYSTEM ni administrador elevado real. Los positivos de esos perfiles son decisiones simuladas de la tabla. El token nativo observado fue no SYSTEM, sin Administradores habilitado, con `TOKEN_ELEVATION` legible y `TokenIsElevated=false`. Se ejecutó suplantación real del token propio y restauración del hilo. Este límite permanece para la aceptación operativa F-09.04/.05.

Las sondas HTTP verifican cuatro rutas concretas: anónimo 401 y administrador global autenticado 404, sin cambiar diez tablas. La lectura de fuente confirma que este cambio no registra endpoint de emergencia. Los dos casos F-08.02 repetidos mantienen API denegada hasta confirmar factor nuevo, también para el global exento. No se atribuye una exploración exhaustiva de URLs ni una recuperación de pérdida total a estos resultados.

## Ejecuciones propias

Comando: `C:/Python312/python.exe -B .local/f0901-review-independent/run_review.py`. Windows, SDK 10.0.401, Release y PostgreSQL 17.11 nuevo/aislado; esquema 46, identidad de migración separada y rol runtime de las fixtures. Ejecución `dotnet test ... --no-build --no-restore` con filtro de las cuatro clases anteriores y binlog único privado. **Sin recompilar.**

| Foco independiente | Resultado |
|---|---|
| Tabla de autoridad, combinaciones simuladas | 64/64 PASS |
| Identidad/claims y suplantación propia nativa/restauración | 2/2 PASS |
| Procesos de modo, conflictos y configuración inválida | 10/10 PASS |
| Rutas HTTP de emergencia inexistentes/snapshot | 1/1 PASS |
| Recuperación restringida, ordinario/global, hasta factor nuevo | 2/2 PASS |
| Total de xUnit | **79/79 PASS, 0 fallos, 0 omitidas** |
| Sonda propia: stdin abierto sin enviar ni cerrar entrada, `appsettings.json` malformado, SQL/origen/Enabled inválidos y autoridad ficticia por entorno | PASS: salida 1, una línea JSON, stderr vacío, rechazo exacto de autorización, 0 operaciones/sesión |
| Siete conflictos con el orden de argumentos invertido | 7/7 PASS: `cli_mode_conflict`, sin stderr |

Las ocho sondas son adicionales a los 79 casos, no ocho resultados de producto. No se cambió el token ni se elevaron privilegios. El clúster propio terminó mediante `pg_ctl stop ... -w`; `postmaster.pid` quedó ausente. Evidencia privada:

- `.local/f0901-review-independent/review-sanitized.json`, SHA256 `e93e4e24a09863ad6a0eefdb264a1260a59b059e1f0052dffd6fc5b738a71166`.
- `.local/f0901-review-independent/native-elevation.json` e `identity-before.json`: sólo indicadores de autoridad, sin nombre/SID en el dictamen.
- `.local/f0901-review-independent/logs/independent.trx`, log crudo y un binlog privado.
- `.local/f0901-review-independent/cluster-7b77cf47f58542c8957e66a4c4232e49`: clúster nuevo ya detenido; credenciales/logs permanecen privados.

Pines comprobados antes y después de mi ejecución:

| DLL | SHA256 |
|---|---|
| RackClick.Server.dll | `4283f7b871173aaf965091a25ab32a51066b21e947e571e413705eccafd4f10c` |
| RackClick.Quality.Tests.dll | `7b7b10a0bd509554ad6bba0292a48740bb0fa55311d81fc4bb94a13e6ba8bbd2` |

Las fuentes Program/helper no cambiaron durante la repetición. Contrasté las **241 entradas** de `FUENTES.json` con los archivos reales, sin discrepancias. Respecto al manifiesto previo de 227 archivos de producto: 226 se conservan, cambia únicamente Program y se añade el helper; el diff acotado incorpora sólo la compuerta y tres archivos de pruebas nuevos. No edité esos cambios.

## Evidencia del coordinador contrastada, no ejecutada por el revisor

Leí resúmenes, contadores, casos/pines y el diff: rojo inicial 0/10 por modo ausente; final 76/76; HTTP 3/3; regresión de comandos/composición 74/74; host normal 7/7. La mutación privada que permite usuario estándar produce 60/65 PASS y 5 fallos; fuente y ambas DLL restauradas a los pines anteriores. Mi repetición posterior usa esos mismos bytes. El rojo inicial corresponde a la revisión inicial del test y no a la aserción fortalecida final. Los tres fallos previos de preparación/build están declarados y sus logs conservados; no los convierto en fallos del producto ni en ejecuciones propias.

No repetí rojo, mutación, builds, regresión general, Node, Edge o suites históricas adicionales. No instalé ni operé VM, D/E, servicios o cuentas Windows. No hice commits/push ni publiqué archivos. No se ejecutó pérdida total, material/anillo nuevo, auditoría/transacción de pérdida, revocación operativa, Restore de emergencia o aceptación de candidata. La observación media de fiabilidad prueba/GUI Edge de F-08.05 sigue abierta; este dictamen no la corrige ni la acredita.

Sólo se escribieron este dictamen y archivos privados bajo `.local/f0901-review-*`. La conformidad permite acreditar únicamente F-09.01; no aumenta por contar pruebas y no declara adopción ni porcentaje global nuevo.
