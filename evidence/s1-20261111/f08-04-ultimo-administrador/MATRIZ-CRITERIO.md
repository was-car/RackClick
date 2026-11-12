# F-08.04 · criterio de recuperación del único administrador

Literal: garantizar vía administrativa de recuperación con códigos válidos sin bloquear al último administrador. Las decisiones confirmadas resuelven esa condición por autorrecuperación y reenrolamiento; no exigen otro administrador ni autorizan omitir el factor nuevo.

| Condición | Fuente existente | Comprobación focal |
|---|---|---|
| Único global por capacidades | Concesiones/miembros; `MfaAccountState`, `MfaGraceDueSql` | Dos usuarios activos, sólo uno con ambas capacidades globales. El otro tiene concesiones limitadas a cliente y no cuenta como global |
| No depender de otro administrador | `AuthenticateForLogin` → `RedeemRecoveryCode` | Contraseña y código propios abren enroll; cero sesiones de ese global y ningún otro global capaz de ayudar; identidad y concesiones intactas |
| Pending prevalece sobre exención | `AuthenticateCore`, `StartEnrollment`, `ConfirmEnrollment` | Otro login durante pending sigue en enroll, no sesión. Sólo TOTP nuevo produce una sesión MFA del mismo usuario |
| Administración restaurada | `Session`, `ReadUsers`, `ReadPermissions`, `ChangeUserMfa` | Sesión nueva lee usuarios y conserva capacidades; puede habilitar MFA de otra cuenta por una escritura protegida del almacén |
| Conservación de la vía y guarda | `GenerateOwnRecoveryCodes`, `SetOrCancelUserState` | Repone expresamente diez códigos distintos; intentar desactivar al único administrador da `last_admin_required`, rollback del snapshot y cuenta activa |
| Recuperación no reactiva una cuenta revocada | `LockChallenge`, límites de cuenta/factor | Dos negativos con código válido: cuenta deshabilitada o factor bloqueado rechazan sin consumo del conjunto ni alteración de las nueve tablas comparadas; sólo puede consumirse el desafío rechazado |
| Política y permisos no se inventan | Gracia45 y exención propia confirmadas | Política global, usuario/contraseña, grupos/miembros/concesiones se comparan; estado final mantiene exención y opción propia de desactivar según contrato |

Los factores/sesiones iniciales son sintéticos; los roles SQL son separados y el fixture usa únicamente una base nueva. La comparación de autoridad cubre la fila del administrador, grupos, miembros y concesiones de su Systemhaus. El snapshot habitual cubre diez tablas; los negativos comparan nueve excluyendo el desafío que el servidor puede invalidar. No es toda la DB ni un análisis de memoria/logs.

La vía presupone host disponible, cuenta utilizable, contraseña conocida y códigos válidos previamente custodiados. No acredita pérdida de contraseña, cuenta eliminada, ausencia del almacén, emergencia F-09 ni custodia efectiva. No se introduce una obligación de conservar MFA que contradiga la exención global decidida por Wascar.


Precisión de definición: la condición global y su exención MFA requieren ambas capacidades globales. La guarda `last_admin_required` existente protege al último `security.manage` global, no una conjunción general de ambas capacidades. El fixture positivo satisface las dos condiciones; este lote no redefine las guardas generales de A-02.
