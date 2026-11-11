# MFA · lote M3 · resultados (tramo 2: gate del login y verificación)

Fecha: 23.10.2026. Responsable: Claude. Estado: **en desarrollo; no desplegable todavía**. MFA no está activo en QA ni en el producto: no hay interruptor de usuario (M4), no hay enrolamiento (M3, siguiente tramo) y no hay proveedor de clave de producción (D2).

## Qué cambia en el código

- `development/server/src/RackClick.Server/PostgresStore.cs`: `Login` pasa a ser un envoltorio de `Authenticate`. Un usuario con MFA exigido no puede entrar por esa vía (`mfa_required`).
- `development/server/src/RackClick.Server/PostgresStore.Authentication.cs` (nuevo): `Authenticate` mantiene las mismas comprobaciones de contraseña, bloqueo y fallos. Tras validar la contraseña consulta `app_mfa_user` y `app_mfa_factor` en la misma transacción:
  - Sin política o sin exigencia: sesión como antes.
  - Exigido y factor activo, con proveedor: desafío de cinco minutos, sin sesión.
  - Exigido sin factor activo: `409 mfa_enrollment_required` (el enrolamiento es el siguiente tramo).
  - Exigido sin proveedor: `503 mfa_unavailable`. No se emite ningún desafío.
- `development/server/src/RackClick.Server/Program.cs`:
  - Login usa `Authenticate`. Con desafío responde `202 {"mfaRequired": true}` y establece la cookie `RackClick.MfaChallenge` (HttpOnly, Secure, SameSite=Strict, ruta `/api/v1/auth/mfa`, cinco minutos). No establece la cookie de sesión.
  - Nuevo `POST /api/v1/auth/mfa/verify` con `{code}`, limitado por la política `login`. Sin proveedor responde 503. Con proveedor consume el desafío y crea sesión nueva con CSRF nuevo.
  - La excepción del middleware es exacta: solo `/api/v1/auth/login` y `/api/v1/auth/mfa/verify` no exigen sesión.
  - El proveedor de clave del producto es `null` (D2 pendiente).
- `MfaStore.cs`, `MfaTotp.cs`, `MfaSecretCipher.cs`: tramo 1, sin cambios funcionales desde su revisión anterior.

## Pruebas

| Conjunto | Resultado |
|---|---|
| `FullyQualifiedName~Mfa` sin laboratorio | 26 OK, 13 omitidas (integración) |
| Integración contra PostgreSQL 17.11 del laboratorio | **13 de 13 OK** |
| Sin Docker (`!~PostgresContainer`) | 36 OK, 13 omitidas |

Integración nueva del tramo 2: login sin MFA emite sesión; login con MFA devuelve desafío y no crea sesión; exigido sin factor da 409; exigido sin proveedor da 503; el login antiguo rechaza al usuario con MFA; un desafío del login se completa con el código y crea sesión con `mfa_verified_at`.

Las pruebas de integración usan `RACKCLICK_TEST_PG_ADMIN` apuntando al laboratorio privado de M1. Sin esa variable se omiten. El laboratorio se arrancó para la prueba y se paró después.

## Bloqueo antes de desplegar

**La consulta de política se ejecuta en cada login.** La migración `014` no está en la lista del producto (`SchemaMigrations.cs`), así que una base con esquema 13 daría error en `app_mfa_user` y el login se rompería para todos. Antes de cualquier despliegue hay que:

1. Añadir `014-mfa-borrador.sql` a la lista de migraciones y pasar el esquema a 14.
2. Actualizar readiness, instalador, recuperación y operadores que fijan la versión 13.
3. Probar esa candidata completa en un laboratorio nuevo.

No se ha esquivado este bloqueo con una comprobación de existencia de tabla: esa ruta dejaría pasar a un usuario marcado sin su segundo factor.

## Pendiente de M3

- Enrolamiento en el primer inicio: secreto mostrado una sola vez, confirmación con un primer código y generación de códigos de recuperación (D2 §3a).
- Activar 014 en el producto (bloqueo anterior).
- Proveedor de clave de producción (D2), solo después de la revisión de Codex sobre la v2 y de la confirmación de Wascar.
- Revisión independiente de los tramos 1 y 2 antes de cerrar M3.

## Hashes de coordinación (versión inestable, no candidata)

| Archivo | SHA256 (16 primeros) |
|---|---|
| `PostgresStore.cs` | 8e3a01945f0c1e6e |
| `PostgresStore.Authentication.cs` | 9d1d00d313ad5578 |
| `Program.cs` | 05c2a77fba0e73ca |
| `MfaStore.cs` | 7754e47d946b8418 |
| `MfaTotp.cs` | 0bf5d3e3198bb197 |
| `MfaSecretCipher.cs` | 9c1cdc76b3d189c9 |

Estos hashes identifican una versión de trabajo. No son una candidata ni una regresión conjunta; cualquier cambio posterior invalida la coordinación.
