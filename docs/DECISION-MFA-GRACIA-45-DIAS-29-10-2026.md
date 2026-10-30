# MFA · gracia de 45 días y administración global

Decisión de Wascar, 29.10.2026. Sustituye la exigencia anterior de MFA inmediato para todos.

- Usuarios ordinarios, técnicos y administradores de clientes: pueden activar MFA voluntariamente; se vuelve obligatorio a los **45 días**.
- Cuentas nuevas: plazo desde creación. Cuentas existentes: plazo desde la activación de la nueva política, sin bloquearlas retroactivamente. El servidor conserva esa fecha y reiniciar no reinicia el plazo.
- El dashboard informa de los días restantes y permite configurar el autenticador. Vencido el plazo, la contraseña sola no concede acceso normal, tampoco mediante una sesión abierta anteriormente.
- Administradores globales del Systemhaus: exentos del plazo, pueden activar o desactivar su propio MFA. La autoridad se deriva de capacidades globales `systemhaus.manage` y `security.manage`, no de un nombre de grupo ni de controles del navegador. Tener administración de un cliente no concede esta exención.
- Quitar MFA durante la gracia no cambia la fecha límite. El administrador global exento puede quitar su propio factor también después de esa fecha. Se mantienen contraseña actual, comprobación de sesión/factor cuando corresponda, auditoría y revocación.
- Administrar métodos de otro usuario requiere `security.manage`; las mutaciones sensibles mantienen la exigencia de una sesión con MFA completado, confirmada en la decisión de recuperación anterior. El administrador nunca recibe el secreto ni el QR de otra persona.
- Restablecer un autenticador exige nuevo enrolamiento. Custodia externa, recuperación local del último administrador y revisión independiente siguen vigentes.

La migración nueva no activa por sí sola la política ni inventa fechas históricas de creación. La candidata que use el proveedor real debe persistir la activación una sola vez. Esta decisión no cambia la instalación existente ni habilita casos QA por aparecer código en desarrollo.

Referencia de organización: [administración de métodos en Microsoft Entra](https://learn.microsoft.com/en-gb/entra/identity/authentication/howto-mfa-userdevicesettings). Se toma la separación entre información personal de seguridad, métodos de cada usuario y acciones administrativas; se mantiene el diseño RC9.
