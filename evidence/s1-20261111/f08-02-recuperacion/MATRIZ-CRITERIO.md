# F-08.02 · matriz de criterio y evidencia

Literal: concretar e implementar si contraseña y código conceden sólo recuperación restringida hasta reenrolar; no emitir sesión normal antes del nuevo factor. El paso 25 ya manda conservar el canje del punto 3; no queda una decisión de producto por inventar.

| Criterio | Código existente | Comprobación de esta tanda |
|---|---|---|
| Prueba de contraseña previa | `AuthenticateForLogin`, desafío `verify`, cookie y CSRF de desafío | Login inválido sin desafío/sesión; código válido sin desafío rechazado; login válido y canje HTTP |
| Canje sólo concede recuperación | `RedeemRecoveryCode` devuelve `RecoveryEnrollmentChallenge`; ruta recover devuelve 202 sin sesión | Cuerpo con sólo `mfaRequired`, `purpose`, `csrf`; desafío y CSRF nuevos; ninguna cookie de sesión utilizable |
| API inaccesible durante recuperación | Middleware exacto de Program y tabla `app_session` | GET me/clientes y POST clientes/preferencias con cookie de desafío, cookie renombrada, sesión antigua y sin cookie: 401, sin cambios en el snapshot de diez tablas del fixture |
| Pending no es autenticación | `StartEnrollment`, `ConfirmEnrollment`, `AuthenticateCore` comprueban estado y finalidad | Repetición de las denegaciones antes/después de start y confirmación inválida; otro login sigue en `enroll`, incluso para global |
| Nuevo factor como única transición | `ConfirmEnrollment` activa factor, consume desafío e inserta sesión | Confirmación válida por HTTP; credenciales nuevas, /me 200, sesión antigua 401, exactamente una sesión MFA y factor activo |
| Política y SQL conservados | Precedencia de pending y `EnforceMfaGrace`; Npgsql parametrizado | Dos cuentas, gracia 45 y política sin cambios; rol runtime no propietario, CREATE TABLE falla con 42501 |

La preparación del factor y sesión anteriores usa el almacén existente; el flujo de recuperación objeto del criterio es HTTP. La prueba no calcula todo el control de acceso de Windows ni usa la identidad efectiva del servicio. `SnapshotAll` del helper cubre diez tablas de identidad/MFA/Systemhaus/operación/auditoría, no todo el inventario o toda la base.

Se reutilizan revisión y Edge del punto 3 con identidad de fuente comprobada. F-08.01 se conserva cerrado; no se acreditan concurrencia/rollback/custodia de F-08.03–.05, instalación o aceptación por este criterio.
