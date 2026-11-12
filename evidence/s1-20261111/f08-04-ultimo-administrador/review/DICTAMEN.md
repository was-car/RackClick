# F-08.04 · dictamen independiente de seguridad

11.11.2026. Revisor distinto del implementador, perfil `rackclick_security` detectado en `.codex/agents/security.toml`. S1 autorizado; revisión acotada al paso 27, su prueba y la corrección surgida al contrastar D2. El revisor no editó producto, pruebas versionadas, ledger, QA ni documentación del coordinador. Sólo escribió este dictamen y sondas/evidencia privadas propias.

**Dictamen: favorable para el cierre técnico de F-08.04, tras corregir el hallazgo alto D2-RECOVERY-DISABLE.** La repetición propia final pasó **5/5, cero fallos y omisiones**; una sonda independiente confirmó el rechazo de la transición que antes permitía eludir el reenrolamiento. No quedan hallazgos bloqueantes abiertos dentro de este alcance. Esto no cierra F-08.05, emergencia F-09, custodia operativa, candidata instalada ni aceptación de Wascar.

## Archivos y símbolos contrastados

| Archivo | Símbolos o contenido consultado |
|---|---|
| `development/server/tests/RackClick.Quality.Tests/MfaLastAdministratorRecoveryTests.cs` | `TheOnlyGlobalAdministratorRecoversWithoutAnotherAdministratorAndKeepsAuthority`, `ValidCodesDoNotReactivateAnInactiveAccountOrBypassAFactorLock`, `DisableCannotCancelRecoveryPendingEvenWithAnAuthorizedMfaSession`, `ActiveGlobals`, `Authority`, `Prepare`, `NoKeys`, `Keys` |
| `development/server/src/RackClick.Server/MfaStore.Recovery.cs` | `RedeemRecoveryCode`, `RecoveryEnrollmentChallenge`: validaciones, consumo del conjunto, revocación y sólo desafío enroll |
| `development/server/src/RackClick.Server/MfaStore.Enrollment.cs` | `StartEnrollment`, `ConfirmEnrollment`, `LockChallenge`, `ChallengeOpen`: cuenta/factor/política, pending y emisión transaccional de sesión MFA |
| `development/server/src/RackClick.Server/PostgresStore.Authentication.cs` | `AuthenticateForLogin`, `AuthenticateCore`, `LoginOutcome`: contraseña, prioridad de pending y separación de desafío/sesión |
| `development/server/src/RackClick.Server/MfaAccountManagement.cs` | `ChangeMfaAccount`, `RequireMfaManagementActor`, `MfaSessionVerified`, `MfaAccountState`, `ChangeUserMfa`, `ReadOwnMfaStatus`, `ReadUserMfaStatus`: autoridad global/MFA, corrección y DTO |
| `development/server/src/RackClick.Server/MfaAccountRecoveryCodes.cs` | `GenerateOwnRecoveryCodes`: reautenticación propia, sesión MFA, generación explícita y recibo sin códigos |
| `development/server/src/RackClick.Server/PostgresStore.cs` | `Can`, `RequireCurrentSession`, `Session`, `ReadPermissions`: ámbitos y revalidación de sesión |
| `development/server/src/RackClick.Server/AdminUsers.cs`, `AdminUserState.cs` | `RequireSecurity`, `ReadUsers`, `SetOrCancelUserState`, guarda `last_admin_required` |
| `development/server/src/RackClick.Server/MfaGraceEnforcement.cs`, `Program.cs` | `MfaGraceDueSql`, `EnforceMfaGrace`, rutas login/recover/start/confirm y mapeo `ChallengePurpose ?? "verify"` |
| `development/server/tests/RackClick.Quality.Tests/MfaAccountManagementTests.cs` | `Laboratory.Create`, roles/factores/sesiones sintéticos, `Snapshot`/`SnapshotAll`, permisos limitados a cliente y desactivación permitida del global |
| `development/server/tests/RackClick.Quality.Tests/MfaRestrictedRecoveryHttpTests.cs`, `MfaDashboardHttpTests.cs` | Casos HTTP existentes y condición explícita de omisión del caso de navegador |
| `development/server/tests/pg_support.py`, drivers privados | `Lab`, `protect_directory`, `start`, `create_database`, `grant_runtime`, `close`, pines y filtros; sólo clústeres nuevos loopback |

Se leyeron `AGENTS.md`, `docs/BRIEFING-MAESTRO.md`, `docs/EQUIPO-Y-SKILLS.md`, el perfil security, `docs/PLAN-F0804-ULTIMO-ADMINISTRADOR.md`, literal F-08.04 del ledger/paso027, `docs/DECISIONES-MFA-CONFIRMADAS-25-10-2026.md`, `docs/D2-CONDICIONES-TECNICAS-F03-02.md` y `docs/DECISION-MFA-GRACIA-45-DIAS-29-10-2026.md`. También se consultaron continuidad/fundamento/inicio S1, secciones pertinentes de contrato/mapa/aceptación/README/progreso y las evidencias previas de F-08.02/.03. La lectura histórica no se presenta como ejecución nueva.

## Hallazgo alto D2-RECOVERY-DISABLE: reproducido y corregido

**Antes de corregir:** `ChangeMfaAccount` permitía `disable` de otra cuenta mientras su gracia no había vencido y ponía `mfa_required=false,enrollment_pending=false`, aun después de canjear un código válido. Contradecía D2/F-03.02 §5: una mutación administrativa no puede cancelar la recuperación y conceder acceso sin factor nuevo.

Reproducción propia sobre el servidor anterior `afd097bd7b88d1755d0744a3fde8f2a7659b7f24653bc76124859608f7e1057e`:

1. Crear clúster/base nuevos con propietario/runtime separados. Enrolar realmente, con clave sintética, a un administrador global y a un usuario ordinario dentro de gracia; obtener sus sesiones mediante `ConfirmEnrollment`.
2. Generar diez códigos propios del usuario. Validar contraseña y canjear uno mediante `RedeemRecoveryCode` con un proveedor que falla si se pide una clave TOTP. Resultado: pending=1, diez códigos consumidos y cero sesiones del usuario.
3. Ejecutar `ChangeUserMfa(admin,target,"disable",...)` con la sesión MFA del administrador: tenía éxito; pending=0, required=0, códigos=0 y un evento de desactivación.
4. Login del usuario con contraseña: devolvía una sesión normal, resoluble por `Session`, con `mfa_verified_at=NULL`; no hubo confirmación de factor nuevo tras recuperar. El único evento de confirmación pertenecía al enrolamiento inicial.

La sonda roja terminó correctamente como instrumento de diagnóstico y confirmó el defecto; no es un PASS de producto. Su clúster quedó detenido. No era un nuevo requisito ni una elección pendiente de política.

**Corrección del coordinador revisada:** exactamente dos cambios en `MfaAccountManagement.cs`: rechazar `action == "disable" && before.EnrollmentPending` con 409 `mfa_enrollment_required`, antes de las escrituras MFA; y añadir `!pending` a `CanDisable`. Mantiene reautenticación, autorización global/MFA, revisión y bloqueo de la cuenta compartido con el canje. La regla de gracia/exención para un factor activo sin pending permanece en el código.

**Verde propio:** en otro clúster y con el servidor final, la sonda con ambos enrolamientos reales obtiene `CanDisable=false`, 409/código exactos y un snapshot idéntico de diez tablas antes/después del rechazo. Conserva pending=1, required=1, diez códigos consumidos, un evento de canje y cero eventos de desactivación. El login posterior sólo entrega enroll; no existe sesión utilizable ni confirmación nueva. Clúster detenido. La regresión versionada propia también pasa para la ruta administrativa y para la defensa de la ruta propia global; esta segunda inyecta explícitamente una sesión verificada de fixture, que el login normal no emite durante pending.

## Identidad y condición de último administrador

Se comprobaron 227 archivos del manifiesto previo contra F-08.03 y la copia fijada. Tras la corrección, **226/227 permanecen idénticos y sólo cambia `MfaAccountManagement.cs`**. No se sostiene la afirmación inicial de producto completamente intacto.

- Fuente corregida: anterior `f7899de77c576c076b49e0c3a4a072b834da8adea1aafbb4a70a24dde2ce04e6`; final `0309a10a7ce310b5fd8add098f44bc679ed315f9f9cc7f05c8b8c55de9b45363`.
- Prueba nueva final: `cbf89d394abac2427cd7df5fdfb8de4950f0e67bf5ca1e32ae901d003b022c6f`, idéntica en raíz y copia fijada.
- DLL final servidor: `dd285c4f7561d8f7e678178a12d399782f0c2142712d16bff10ec87762f85d0e`.
- DLL final pruebas: `1d0332b69238239aa6b8f4214f7a8fd186c26945dc99f6e7c905998a028605c4`.

El positivo crea dos usuarios activos pero sólo uno con ambas capacidades **globales** `security.manage` y `systemhaus.manage`; las concesiones del segundo están limitadas a cliente. Recupera sin otro global, compara usuario/contraseña/grupos/miembros/concesiones, exige otro factor, repone expresamente diez códigos y realiza una escritura administrativa protegida sobre otra cuenta. La guarda de desactivación devuelve `last_admin_required` y revierte el snapshot.

Precisión: la exención MFA requiere ambas capacidades globales; la guarda existente `last_admin_required` protege al último `security.manage` global. El fixture satisface ambas condiciones, sin afirmar su equivalencia general ni redefinir A-02. Recuperar no impone conservar MFA para siempre: el global puede desactivar su factor activo cuando ya no está pending, conforme a Wascar.

## Ejecuciones propias y atribución

Windows, .NET SDK10.0.401, PostgreSQL17.11 real y esquema46. Los tres clústeres propios se crearon nuevos mediante el helper inspeccionado y quedaron detenidos; no se usaron bases, cuentas Windows, servicios o instalaciones existentes. Runtime separado del propietario; las sondas comprueban que no es propietario ni superusuario ni tiene CREATEDB/CREATEROLE. Material criptográfico exclusivamente sintético.

| Ejecución del revisor | Resultado |
|---|---|
| `C:/Python312/python.exe -B .local/f0804-review-probe-5c9e/run_probe.py` | Defecto anterior reproducido; clúster `b104e5c0fcc54de786dbac51fd5d7a4d` detenido |
| `C:/Python312/python.exe -B .local/f0804-review-green-1d7a/run_probe.py` | Contrato corregido verificado; clúster `917daa49369d4b0ab329119089dd09f8` detenido |
| `C:/Python312/python.exe -B .local/f0804-24f412cc/run_focus.py --review` | **5/5 PASS, 0 FAIL, 0 omitidos**; clúster `f91ce63484204d6da4df8dba8f1e4638` detenido |

Los cinco casos son un positivo de último global, dos negativos de cuenta inactiva/factor bloqueado y dos negativos de disable durante pending. Se contrastaron nombres/resultados del TRX y pines antes/después; existe el binlog privado de la repetición. Las dos consolas privadas se restauraron/compilaron con binlogs propios; no se recompiló el producto para la revisión. Se aplicaron las skills de binlogs y verificación; ante el hallazgo, investigación y reproducción antes de corrección.

Hashes de resultados sanitizados propios, retenidos en `.local/`:

- Rojo: `0217ec376d6d9620f0102b94866488d47f4aedaeb5283c62cb36e92d01ed12a3`.
- Verde: `9b5386f9d6605703373dae1fe7502f5e127d88812f162e75655d9d90e803ff5b`.
- Repetición 5/5: `ca692789ecec0e65cc50923d7c2b6cead921d85359564238940ecc49c8e642ba`.

**Ejecuciones ajenas:** el coordinador comunicó primer foco 6PASS/1FAIL de siete por una aserción del test sobre `ChallengePurpose`: el almacén usa null como valor predeterminado de verify y HTTP lo normaliza. Se corrigió sólo la aserción; tres casos pasaron posteriormente. La regresión D2 contra producto anterior falló 0/2 con `NoExceptionThrown`; después de corregir pasó 2/2. No son ejecuciones del revisor.

La regresión ampliada del coordinador seleccionó49: **48PASS/0FAIL/1NotExecuted** opcional de navegador; driver exit1 por su aserción de ausencia de omitidos, sin código hijo conservado como dato separado. El discovery posterior concilia los48 nombres aprobados, sin transformarlos en otra ejecución48/48. `MfaDashboardHttpTests.BrowserDashboardShowsGraceAndManagesPersonalAndSelectedUserMfa` contiene una omisión explícita cuando faltan frontend/repositorio del runner. `FRONTEND.json` registra68/68 Node; el intento previo sin módulo esbuild se conserva. Se contrastaron los registros sanitizados finales; esta revisión no repite Node o navegador ni atribuye esas ejecuciones al revisor.

## Contraste final de los archivos de cierre

Se consultaron `FOCO.json`, `FUENTES.json`, `RESULTADOS.md`, `FRONTEND.json`, `SCOPE-RECONCILIACION.json`, `D2-ROJO-VERDE-INDEPENDIENTE.json`, la matriz y la ficha `docs/PASO-027-ULTIMO-ADMINISTRADOR-MFA.md`. El diff revisado concuerda con la corrección descrita. En `FOCO.json` hay exactamente49 resultados,48 Passed y uno NotExecuted; los cinco nombres de mi repetición están incluidos como Passed. La conciliación identifica sólo discovery posterior y conserva driver1/código hijo no observado.

Se verificaron contra el árbol actual todos los hashes de las226 fuentes invariables, una modificada, una prueba nueva,29 fuentes asignadas conservadas, tres pruebas previas y un soporte histórico modificado: **cero discrepancias**. `MfaAccountManagement.cs` es ese soporte; no se resta indebidamente de las29 fuentes asignadas del punto3. Las mediciones públicas roja/verde coinciden exactamente con mis JSON privados al retirar sólo `privateLab`; sus hashes de origen también constan en el registro público.

Comparación propia de QA contra la copia previa:175 casos antes/después; sólo cambia QA-163, únicamente `steps` y `expected`; los otros174 son idénticos. Los seis pasos anteriores permanecen literalmente y en orden, con dos inserciones nuevas. Los restantes campos del caso, incluida su disponibilidad, permanecen iguales; esto no es ejecución manual. La metadata de QA conserva la estimación histórica de **78 %** sin recalcular; no corresponde a cobertura del hardware ni a un cálculo nuevo del producto. Tampoco se confunde con la métrica del cierre restante que concilia el coordinador.

## Límites y trabajo pendiente

- Los factores/sesiones del fixture versionado son sintéticos. Las sondas independientes sí recorren enrolamiento/confirmación real de aplicación, siempre con claves sintéticas; no usan proveedor nativo ni SID de servicio instalado.
- `NoKeys` acredita que el canje no pide descifrar el TOTP. No acredita que un host sin almacén pueda arrancar, ni resuelve pérdida total de claves, contraseña, cuenta eliminada o emergencia F-09.
- Los snapshots cubren diez tablas de identidad/MFA/Systemhaus/operación/auditoría; los negativos de cuenta/factor comparan nueve y permiten invalidar el desafío rechazado. La comparación de autoridad es la especificada, no toda la DB/inventario. No hay análisis de memoria, logs, dumps ni historial completo de secretos.
- Se reutilizan consumo/replay/rollback de F-08.03 y las evidencias históricas HTTP/Edge/punto3 con sus fechas y ejecutores. Esta repetición no acredita apagón, TLS, navegador actual, Windows/SID/DPAPI efectivos, instalación o QA de Wascar.
- La recuperación presupone host disponible, cuenta utilizable, contraseña conocida y códigos previamente guardados. La reposición es explícita tras recuperar; no se garantiza custodia real ni que siempre existan códigos.
- El alcance sólo hace elegible F-08.04. F-08.05 e hitos operativos conservan sus criterios propios. La revisión no modifica la métrica ni aumenta por sí misma la estimación global vigente; no equivale a aceptación/adopción.

No hubo operaciones D/E/VM, instalaciones, servicios, cambios de cuentas Windows, commits, push ni despliegue por el revisor. Conexiones, códigos, tokens, logs y binlogs permanecen privados y no se incorporan a este dictamen.
