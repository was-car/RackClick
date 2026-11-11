# Paso 31 · revocación y auditoría tras pérdida de claves MFA

11.11.2026 · F-09.03. Cerrado técnicamente con revisión independiente favorable, limitado al componente backend bajo mantenimiento. **D y E se conservan.**

Se reutiliza la transición del paso30: revoca las sesiones, consume todos los desafíos pendientes y retira los códigos antiguos de las cuentas afectadas, en la misma transacción que archiva sus factores cifrados y exige reenrolamiento. Las cuentas no afectadas conservan sus objetos de seguridad.

El registro dedicado `rackclick_private.mfa_loss_operation` audita la autoridad Windows real, el UUID de operación, instalación/DB/Systemhaus, versiones, hashes y conteos. Su resultado significa **transición DB confirmada**, no servicio recuperado ni acceso concedido. No contiene contraseña, clave, semilla TOTP, ciphertext de factor o códigos. No se inventa un usuario RackClick para rellenar `audit_event.actor_id`.

## Corrección y verificación

La primera aplicación comprueba ahora los recuentos de archivo/reenrolamiento y la escritura del registro, y revalida su contenido completo **antes del commit**. Un resultado incompleto de SQL o auditoría provoca rollback. El caso sin factores también se comprueba; no basta esperar hasta Publish para detectar el problema.

Los ensayos ejercen las sesiones y desafíos anteriores realmente rechazados, contraseña incorrecta, códigos anteriores, aislamiento de no afectados, auditoría sin secretos y reentrada sin duplicación. El único administrador global conserva identidad, permisos y gracia; su contraseña sólo entrega un desafío `enroll`. Sólo confirmar un TOTP nuevo devuelve una sesión y acceso administrativo. La protección que impide desactivar al último administrador sigue vigente.

Se usan PostgreSQL17.11 nuevo, owner/runtime separados y material/identidad Windows de fixture. El recorrido es de componentes/backend: **no se libera el fence ni se inicia un servicio/HTTPS**. Los triggers que suprimen escrituras y los fallos de auditoría se inyectan sólo en DB nuevas; no se afirma que existan en la instalación normal.

## Continuación

[Plan e investigación](PLAN-F0903-REVOCACION-AUDITORIA-MFA.md) · [resultados](../evidence/s1-20261111/f09-03-revocacion-auditoria/RESULTADOS.md) · [matriz](../evidence/s1-20261111/f09-03-revocacion-auditoria/MATRIZ-CRITERIO.md) · [dictamen independiente](../evidence/s1-20261111/f09-03-revocacion-auditoria/review/DICTAMEN.md).

Los pasos32/33 conservan la composición operativa, guarda de arranque de pérdida, CLI, ensayo completo en host Windows y cierre. La CLI actual sigue bloqueada incluso tras autorizar al operador; no ofrece todavía recuperación de emergencia en D. No hay instalador nuevo, cambio de GUI o resultados personales de QA. Se conserva la observación Edge del paso28.


Sólo F-09.03 acredita **1/2 punto**: índice del cierre restante **25,63→26,13/100**. No es porcentaje global nuevo ni recuperación operativa instalada. Siguiente paso32/F-09.04.
