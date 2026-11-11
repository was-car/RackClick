# Revisión independiente · F-03.02 · condiciones técnicas D2

03.11.2026. Revisor: `f0302_review`, perfil de seguridad, distinto del autor de la especificación. No edita el documento que aprueba ni el producto o el ledger.

## Dictamen final

**Favorable al cierre documental de F-03.02, paso9.** La versión corregida concreta las tres condiciones técnicas de la revisión D2: recuperación restringida sin depender de la clave perdida, perfil KDF/cabecera autenticada y publicación conciliable entre archivos y PostgreSQL. El hallazgo documental de esta revisión quedó corregido antes de este dictamen. No quedan bloqueantes concretos en el ámbito examinado.

Documento revisado: `docs/D2-CONDICIONES-TECNICAS-F03-02.md`, SHA256 **`b8a601686d9a7c03518f5c3f4084ccd348fcecf393ee41d46fb8c1caec7c0dd3`**. Este dictamen sólo vale para esa fuente; cambios posteriores requieren contraste acotado.

La conclusión no acredita la implementación del journal, fence, registro de mantenimiento, rotación, emergencia o Restore portable. No cierra F-03.03 ni F-04 a F-09, R-03 o R-04; no representa una prueba de la instalación D, una aceptación de Wascar o una nueva puntuación ponderada.

## Hallazgo corregido

**F0302-REV-01 · P2 documental · pérdida irreversible incompatible con la tabla general.** La primera versión remitía la pérdida total a un protocolo que exigía conservar legibles todas las claves anteriores y un sobre que las contuviese. Era imposible satisfacerlo precisamente cuando no quedaban esas claves ni un sobre útil. Se comunicó al coordinador antes de aprobar; el revisor no cambió el documento.

La corrección fija de antemano los modos `rotate`, `portable-restore` y `loss-reset`. Los dos primeros se detienen si falta material requerido. El tercero necesita autorización y alcance expresos, conserva el material anterior opaco, identifica factores/usuarios/backups afectados, prepara sólo material útil nuevo y retira los factores ilegibles en la transacción que fuerza reenrolamiento. La cobertura se calcula contra el conjunto vivo posterior y los backups recuperables declarados; una pérdida/dependencia desconocida impide continuar. No convierte el nuevo sobre en recuperación de claves históricas perdidas. Las filas `material_ready` y `ring_published` distinguen esos modos. **Hallazgo resuelto por inspección del contrato**, no por ensayo de la futura implementación.

## Contraste de condiciones

| Condición | Contraste independiente |
|---|---|
| Recuperación restringida | El documento diferencia código de recuperación con host disponible de pérdida total con host cerrado. Reutiliza el login y el canje existentes; exige password, desafío/CSRF, revocación y nuevo factor antes de una sesión. La autorización local es independiente del factor perdido, con autoridad Windows explícita y sin elevar el servicio. |
| Gracia y exención global | Se conserva la decisión45días. `enrollment_pending` tiene prioridad real en `AuthenticateCore`; la exención no limpia ese estado. El contrato añade negativos de `disable`/`reset`/activación de política para que esa prioridad no se confunda con integración completa de todas las mutaciones. No se otorga acceso por un nombre de rol. |
| Uso de herramientas existentes | `--recover-admin` se identifica correctamente como recuperación de administrador de Restore: no es el operador MFA de pérdida total. `Recover` adapta sólo identidad/DPAPI del anillo; no cambia por sí solo los IDs/AAD de factores DB. El instalador actual rechaza factores sin importador de sobre. |
| Límites del codec | Offsets, algoritmos, mínimo60/máximo1048576bytes, 600000 iteraciones exactas, sal16/nonce12/tag16, salida32, AAD0..42 y UTF-8 estricto12..256puntos de código coinciden con fuente. Cabecera y límites se validan antes del KDF. El límite adicional de entrada del futuro operador se declara normativo, no una garantía nueva del codec actual. |
| AAD y errores | Se diferencia rechazo previo de formato/parámetros de `AuthenticationFailed` con formato válido. La prueba histórica independiente sin AAD no se atribuye al autor original ni a esta sesión. No se promete borrado universal de strings/memoria ni duración universal de la derivación. |
| Orden disco/DB | Material válido antes de que DB dependa de él; fence y exclusión duraderos; marcador único DB en la misma transacción que datos y auditoría; commit incierto se consulta, no se infiere. Publicación final y conciliación conservan material requerido. No se anuncia atomicidad conjunta por rename o una transacción SQL. |
| Arranque y recuperación | Se distingue comprobación offline `data_verified`, retirada del fence para arranque controlado, `service_resumed` y cierre de operación. El reenrolamiento puede realizarse con el host disponible sin conceder sesión API antes de confirmar. Fallo de arranque devuelve el servicio a mantenimiento, sin rollback ciego del commit. |
| Versiones/retención | No reutilización silenciosa de versión con otra clave; límites actuales1..1000000 y64entradas; agotamiento/historia no fiable detienen. `retired` sigue legible, no elegida para nuevos cifrados. Dependencias de backups también impiden retirar material; pérdida explícita no cuenta como cobertura criptográfica. |
| Autoría local y permisos | El registro de mantenimiento dedicado es futuro, con autoridad Windows y runtime sólo SELECT; no se finge un usuario autenticado para satisfacer `audit_event.actor_id`. No amplía `management` ni derechos Windows/DB del servicio. |

La precisión final de tres filas de la tabla4.2 también fue contrastada: `portable-restore` conserva claves/versiones/activa con reprotección DPAPI, no exige rotación ni recifrado TOTP si la AAD se conserva, y revoca las sesiones/desafíos restaurados antes de servir. Es consistente con la adaptación limitada del componente `Recover`; sigue sin afirmar que el instalador actual integre ese recorrido.

## Fuentes y símbolos consultados

- `AGENTS.md`, `docs/BRIEFING-MAESTRO.md`, criterio de F-03.02 y especificación revisada.
- `docs/REVISION-D2-CODEX.md`, condiciones1–3; `docs/DECISIONES-MFA-CONFIRMADAS-25-10-2026.md`; `docs/DECISION-MFA-GRACIA-45-DIAS-29-10-2026.md`. El texto histórico de exigencia inmediata queda subordinado a la decisión posterior.
- `MfaKeyRecoveryEnvelope.cs`: `Seal`, `Open`, `RequireHeader`, `PasswordBytes`, `Derive`; `MfaKeyRecoveryPayload.cs`: `Serialize`, `Deserialize` y forma binaria; `MfaKeyRing.cs`: límites, `Parse`, `RequireEntry`, `EntropyFor`.
- `MfaStore.Recovery.cs`: `RedeemRecoveryCode`; `PostgresStore.Authentication.cs`: `AuthenticateCore`; `MfaGraceEnforcement.cs`: `MfaGraceDueSql`, `EnforceMfaGrace`; `MfaSecretCipher.cs`: AAD.
- `WindowsMfaKeyRecovery.cs`: `Export`, `Recover`; `WindowsMfaKeyStoreWriter.cs`: `CreateInitialStore`, `CreateStoreFromMaterial`; `WindowsMfaKeyProvider.cs`: `GetKey`, `GetActiveKey`; `MfaWindowsHostComposition.cs`: `Validate`.
- `RecoveryAdministrator.cs`: `Run`/`Recover`; `tools/windows/New-RackClickRecoveredInstance.ps1`: `Assert-RecoveryMfaMaterial`; `001-foundation.sql`: `audit_event` y su actor no nulo.
- Revisiones y manifiestos de fuentes de L2d, L2f y L2g corregido. Los componentes centrales reutilizados mantienen los hashes contrastados en `CONTRASTE-REUSO.json`.

## Qué ejecutó realmente este revisor

Lectura de instrucciones, decisiones, código y evidencia; comprobación de offsets/límites y flujo por inspección; cálculo SHA256; contraste de cinco hashes actuales con los manifiestos históricos de fuentes; revisión de las correcciones del autor. Sólo se crean este dictamen y su medición JSON sanitizada en la carpeta asignada.

Las cifras34 de L2d,93 de L2f y59 de L2g son **ejecuciones históricas reutilizadas**, con solapamientos; no son pruebas nuevas de este revisor ni un total acumulable de casos únicos. El hash del codec y los del recorrido de recuperación/escritor/archivos coinciden con aquellas fuentes.

**No ejecutado:** compilación, dotnet/test, KDF o DPAPI nuevos, PostgreSQL, HTTP/login, criptografía de referencia nueva, concurrencia/cortes, operador local, custodia externa, SID efectivo, VM D/E, GitHub, commits/push o cambios del ledger. No se abren secretos ni `.local`. Las fuentes oficiales enlazadas por el autor no se consultaron de nuevo por este revisor; se contrastan aquí sus requisitos con código y revisiones locales ya conservadas.

## Límites

El protocolo futuro necesita implementación y ensayos de sus fases, exclusión, durabilidad, registro DB y guard de arranque. El doble read de `ring.json` no acredita snapshot global ni evita ABA. Las piezas de laboratorio no prueban Restore entre equipos ni ausencia universal de copias en memoria. Los límites de amenaza DPAPI/administrador/proceso comprometido mantienen su paso F-03.03. D permanece fuera de las operaciones de esta revisión.
