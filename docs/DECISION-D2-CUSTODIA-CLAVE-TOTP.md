# D2 · Custodia de la clave TOTP · versión 2

**Confirmación de Wascar · 25.10.2026:** custodia, ubicación del almacén por instancia y recuperación aprobadas expresamente. Wascar custodia el sobre cifrado fuera del servidor/backups y su contraseña en medios separados. Restablecimiento web con security.manage y MFA completado; emergencia por códigos o procedimiento local, siempre reenrolamiento antes de acceso completo. [Decisiones vigentes](DECISIONES-MFA-CONFIRMADAS-25-10-2026.md). Quedan implementación y condiciones técnicas de la revisión; no otra aprobación de arranque. La propuesta v2 que sigue se conserva como cuerpo histórico; sus menciones de decisión pendiente de Wascar quedan superadas por esta confirmación. MFA aún no disponible para usuarios.

Fecha: 23.10.2026. Estado: **propuesta v2 de Claude, corrigiendo los seis hallazgos de `docs/REVISION-D2-CODEX.md`.** Pendiente de revisión de Codex sobre esta versión y de confirmación de Wascar. No implementada. La v1 queda superada.

## 0. Cambios respecto a la v1

| Hallazgo | Corrección en esta versión |
|---|---|
| D2-01 · ACL que impide al servicio leer la clave | Almacén propio (§2), con lectura solo para el SID del servicio. `management` no cambia. |
| D2-02 · recuperación sin administrador con MFA | Códigos de recuperación independientes de la clave y restablecimiento local de emergencia (§3). |
| D2-03 · sobre sin especificar | Formato versionado con KDF, cifrado autenticado y límites (§4). |
| D2-04 · rotación e identidades | Anillo de versiones y reglas de restauración con AAD (§5). |
| D2-05 · modelo de amenaza LocalMachine | Modelo de amenaza explícito (§1). |
| D2-06 · estados de pérdida | Tabla de estados y arranque con error explícito (§6). |

## 1. Modelo de amenaza

- **Protege** frente a: lectura de la base o de sus volcados; lectura de `management` y de otras carpetas por cuentas estándar; uso de un volcado en otra máquina sin el sobre.
- **No protege** frente a: el administrador del equipo, que puede leer el almacén; ni frente al proceso del servicio comprometido, que necesita la clave en memoria para verificar códigos.
- DPAPI en ámbito `LocalMachine` es cifrado en reposo ligado al equipo. **No** es un aislamiento frente al administrador del host y no se presenta como tal.

## 2. Almacén separado de la clave

- Carpeta nueva: `C:\ProgramData\RackClick\Instances\<installationId>\mfa-keys\`. No está en `management`.
- Contenido: un archivo por versión de clave (`key-v<N>.dpapi.json`), protegido con DPAPI `LocalMachine`, y `ring.json` con las versiones y su estado. Las escrituras son atómicas: archivo temporal y reemplazo.
- ACL: SYSTEM y Administradores con control total (instalador y operador). La cuenta de servicio, con su SID real, solo tiene lectura de los archivos y de la carpeta para atravesarla. Sin escritura, sin cambios de ACL y sin acceso a `management` ni a otros secretos.
- Creación: la hace el instalador o un operador autorizado, con la ACL ya aplicada desde el primer instante. El servicio nunca genera ni rota claves.
- `Assert-SetupManagementAcl` no se relaja. El almacén tiene su propio validador de ACL.

## 3. Recuperación sin el factor

Dos vías independientes:

**a) Códigos de recuperación.** Diez códigos de un solo uso por usuario, generados al confirmar el enrolamiento y mostrados una vez. Se guardan como hash con sal, no dependen de la clave TOTP y se consumen en una transacción. Con contraseña y un código de recuperación se entra, y el usuario queda con `enrollment_pending` para volver a enrolar.

**b) Restablecimiento local de emergencia.** Si se pierden la clave y los códigos de un administrador, un operador con acceso local al servidor (SYSTEM o Administradores, fuera de la web) ejecuta un procedimiento que marca `enrollment_pending` a los usuarios afectados, invalida sus sesiones y desafíos y deja auditoría sin secretos. No hay restablecimiento web anónimo ni inicio de sesión sin factor.

Ensayo requerido antes de cerrar M6: pérdida simulada de la clave, del sobre y de los códigos de un administrador; restablecimiento local; el administrador vuelve a entrar y enrola de nuevo. Debe existir siempre al menos un administrador con códigos válidos.

## 4. Sobre de recuperación portable

- Formato `RCKEY` versión 1. Cabecera en claro: magia, versión de formato, algoritmo KDF (PBKDF2-HMAC-SHA256), iteraciones, sal de 16 bytes. Después: nonce de 12 bytes, etiqueta de 16 y texto cifrado con AES-256-GCM, que contiene el anillo completo.
- Contraseña de recuperación de 12 a 256 caracteres. Tamaño máximo de entrada de 1 MiB, validado antes de derivar la clave.
- Custodia: el sobre y su contraseña en medios distintos, y ninguno dentro del volcado de la base ni de la carpeta de copias. La contraseña la custodia Wascar; el sobre, el operador. Nunca por el chat.
- El blob DPAPI del host original **no** sustituye al sobre: está ligado a ese equipo.
- Pruebas: contraseña incorrecta, sobre alterado, sobre truncado, versión desconocida y entrada por encima del límite.

## 5. Anillo de versiones y restauración

- `ring.json` lista las versiones con su estado (`active` o `retired`) y su fecha. Cada factor guarda `key_version`.
- Rotación: se crea una versión nueva, se activa para nuevos cifrados y se reenvuelven los factores en una transacción. Una versión antigua se retira solo cuando ningún factor la usa y ningún respaldo retenido la necesita.
- Rotación interrumpida: el anillo se escribe de forma atómica; los factores siguen siendo legibles con la versión anterior.
- AAD = `systemhausId`, `userId` y `keyVersion`. En una restauración se conservan esos IDs. Si la restauración crea identidades nuevas, hace falta un proceso explícito de reenvoltura autenticada, con verificación previa de cada factor. No se cambian identidades en silencio.
- Pruebas: restauración con IDs conservados; rotación interrumpida; versión desconocida rechazada.

## 6. Estados de pérdida

| Estado | Consecuencia |
|---|---|
| Se pierde una copia del blob, pero queda el sobre y su contraseña | Se recupera desde el sobre. |
| Se pierde el sobre, pero el blob local sigue | No hay consecuencia para los factores. |
| Se pierde la contraseña de recuperación, pero el blob local sigue | Los factores siguen usables en ese host; el sobre portable deja de servir hasta regenerarlo. |
| Se pierden todas las vías útiles | Factores irrecuperables: se aplica §3b. |
| Falta un archivo del almacén en una instancia ya enrolada | Arranque con error explícito y procedimiento de recuperación. No se regenera la clave ni se borra la base. |

## 7. Lo que sigue abierto

- Responsable de custodia de la contraseña de recuperación y del sobre (Wascar y operador): pendiente.
- Ubicación del almacén (§2): acordarla con Codex antes de implementar el proveedor real.
- Parámetros KDF: PBKDF2-HMAC-SHA256 con 600 000 iteraciones como punto de partida; a revisar.
- Implementación con DPAPI y pruebas bajo el SID real del servicio: pendiente hasta confirmar esta v2.
