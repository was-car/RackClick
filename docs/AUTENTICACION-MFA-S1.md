# MFA sobre la autenticación existente

**Estado vigente · 29.10.2026, después del ensayo10:** MFA disponible en la nueva VM C de laboratorio con proveedor Windows DPAPI real bajo servicio estándar, HTTPS y esquema15. Enrolamiento, confirmación y siguiente login comprobados por API antes y después del reinicio; TLS validado normalmente. Política45 y exención global comprobadas. La cuenta Wascar conserva acceso y su factor queda para su propio QA visual. La QA anterior permanece intacta y la producción no está adoptada. Recuperación portable, último administrador y negativos completos de otros tokens siguen pendientes. [Resultado y límites](../evidence/s1-20261029/installer10-vm-codex/RESULTADOS.md), [pasos de Wascar](QA-MFA10-WASCAR.md). Los estados siguientes son históricos.

**Estado vigente · 29.10.2026:** dashboard de seguridad propia/administrativa, avisos y enforcement de **45 días** implementados y probados en laboratorio de esquema15. Wascar cambia la política: existentes desde activación, nuevas desde creación; sólo administrador global Systemhaus exento y con desactivación propia permitida. Sustituye la exigencia inmediata anterior para todos. Rutas con autorización del servidor, revocación/auditoría/idempotencia y gestión sin secretos ajenos. Quality378PASS/0fallos/1Dockeromitida y Browser8etapasPASS con proveedor sintético de prueba. No activado/instalado en QA; candidata15, custodia real integrada y recuperación pendientes. [Decisión](DECISION-MFA-GRACIA-45-DIAS-29-10-2026.md), [resultado](MFA-DASHBOARD-GRACIA-45-29-10-2026.md). Entradas siguientes históricas.

**Estado vigente · 27.10.2026:** el enrolamiento y la verificación tienen GUI EN/DE/ES, QR local y clave manual, comprobados en Edge/Kestrel/PostgreSQL 17.11 con cuenta DML sin DDL y proveedor sintético sólo de pruebas. 38 pruebas Node y una integración real PASS; revisión independiente favorable. Se acredita F-07.02, sin habilitar MFA en la QA instalada. La composición Windows explícita ya existe en desarrollo; falta su validación con la cuenta efectiva del servicio y la entrega de una candidata integrada. Recuperación y aceptación final siguen pendientes. [Resultado y límites](MFA-GUI-PRIMER-FLUJO-27-10-2026.md). Los estados fechados anteriores se conservan como historia.

**Entrega parcial y revisión · 25.10.2026:** Claude entregó enrolamiento backend y rutas; informó nueve pruebas PG y70PASS/1omitida en calidad. Codex no las repitió. Cuatro P2 de revisión y positivo/negativos HTTP/concurrencia/rollback/auditoría pendientes: [dictamen](REVISION-MFA-L1-CODEX-25-10-2026.md). Autorizado paquete Microsoft.AspNetCore.Mvc.Testing10.0.12 sólo en pruebas y DI del fixture, sin proveedor normal ni activación QA. [Siguiente trabajo Claude](MENSAJE-PARA-CLAUDE-MFA-L1-HTTP-25-10-2026.md). MFA no está disponible para usuarios; decisiones de custodia/recuperación ya confirmadas.

**Estado actualizado · 25.10.2026:** implementación parcial sin disponibilidad para usuarios: cifrado/store/verificación existen, pero proveedor normal ausente y enrolamiento/UI pendientes. SQL014 ya está activa en el runner y presente en bundle14-08; las referencias a esquema13 del contrato fechado21 son históricas. Wascar confirmó custodia/ubicación y recuperación: [decisiones](DECISIONES-MFA-CONFIRMADAS-25-10-2026.md). Claude tiene asignado [MFA-L1](MENSAJE-PARA-CLAUDE-MFA-L1-25-10-2026.md), con revisión independiente posterior. No se ha activado en QA ni cambiado el servidor.

21.10.2026. Contrato de implementación pendiente; **MFA no está disponible**. Wascar confirma que será obligatorio para **todos los usuarios antes de producción**, incluidos lectores y administradores. No se modificaron cuentas, sesiones ni claves del servidor.

## Base comprobada

`PostgresStore.Login` normaliza usuario igual que bootstrap, verifica contraseña, limita fallos por cuenta y crea sesión/CSRF nuevos con expiración de ocho horas. El middleware exige Origin exacto y CSRF en mutaciones. Desactivar/resetear un usuario revoca sesiones; se protege el último administrador. Administrador significa capacidad global `security.manage`, no un nombre de grupo fijo.

El esquema actual es13. La siguiente migración deberá ser aditiva14; no modificar SQL anteriores. Readiness, recuperación administrativa y operadores/backup que fijan versión13 deben actualizarse y probarse juntos en una candidata nueva.

## Estados y API previstos

- Password verificada no equivale a login completado si MFA aplica. Login devuelve202 y desafío opaco de corta vida; no crea `app_session`, actor con permisos ni cookie `RackClick.Session` utilizable.
- Desafíos de enrolamiento/verificación separados, finalidad fija, token aleatorio persistido como hash, duración máxima cinco minutos, contador de intentos y consumo único. La sesión anterior no se promueve a MFA por presentar un desafío.
- Cookie de desafío HttpOnly/Secure/Strict, alcance mínimo y token CSRF propio. Sólo excepciones exactas a los endpoints MFA en middleware; se mantienen HTTPS, Host, Origin, límites de cuerpo y rate limiter. Un prefijo público amplio sería incorrecto.
- Verificar TOTP y emitir sesión/CSRF nuevos en la misma transacción que consume el desafío. Validar de nuevo cuenta activa, política, caducidad y permisos tras adquirir bloqueos; usar reloj del servidor PostgreSQL para decisiones transaccionales.
- TOTP de seis dígitos/30 segundos, ventana pequeña documentada y último intervalo consumido para impedir repetición. No confiar en hora del navegador. Revisar y fijar Otp.NET oficial antes de introducirlo; no añadir EF Core ni reemplazar toda la autenticación por Identity.
- Enrolamiento confirmado por un primer código válido; mostrar secreto/QR sólo a ese usuario durante el proceso y no registrarlo en logs, URL, historial ni auditoría. No marcar factor activo sólo porque se generó un QR.
- Recuperación con códigos de un uso guardados como hashes y consumo transaccional. Restablecer MFA requiere capacidad administrativa autorizada, auditoría y revocar sesiones/desafíos; conservar al menos una vía administrativa de recuperación comprobada.
- Revocar sesiones password-only al entrar en vigor la política. Una concesión nueva de privilegios no debe elevar una sesión que aún no cumple MFA.

## Custodia y restauración

El secreto TOTP debe poder recuperarse para verificar códigos; un hash del secreto no sirve. Requiere cifrado autenticado con versión de clave e identificador de instancia/usuario, clave fuera de PostgreSQL, acceso mínimo y esquema de backup/recuperación portable. No usar clave efímera de arranque ni guardar la clave junto al dump en texto plano. DPAPI ligado al equipo sin exportación/recuperación no basta para Restore en otra VM.

Antes de desplegar se concretará el responsable de custodiar la clave y el procedimiento de emergencia. La pérdida de un dispositivo MFA no debe exigir borrar la DB ni crear un administrador por una ruta web sin autenticación. La recuperación operativa no puede reactivar sesiones antiguas ni omitir la política silenciosamente.

## Integración de interfaz obligatoria

`api.login` actualmente devuelve sesión después de `/me`. No cambiar ese contrato a medias: el coordinador de autenticación deberá completar también desafío/enrolamiento y conservar la identidad esperada.

Usan reautenticación los formularios de operaciones inciertas, administración de usuarios/contraseñas/estado/sesiones, favoritos, plantillas, preferencias y paletas. Todos deben continuar sólo al completar MFA para el mismo actor; no perder borradores ni reenviar una escritura bajo otro usuario. Login aislado funcionando no basta.

Mantener RC9 y EN/DE/ES. Añadir guiones QA precisos de activar factor, segundo login, código erróneo/caducado/repetido, recuperación, revocación, otra sesión y reautenticación de borrador; dejarlos no disponibles hasta integrar y verificar la candidata seleccionada. No reescribir resultados de Wascar.

## Pruebas de aceptación necesarias

1. Login antes/después con Unicode y límites; sin cookie de sesión privilegiada durante desafío. Rutas `/me`, clientes y mutaciones rechazan el desafío como sesión.
2. PostgreSQL real: desafío expirado, bloqueado, consumido concurrentemente y TOTP repetido; sólo un commit puede emitir sesión. Contraseña/código incorrectos no producen éxito ni registros duplicados.
3. Origin/CSRF/rate limit en enrolamiento y verificación; sesión/CSRF diferentes tras completar; revocación concurrente gana frente a petición que esperó un bloqueo.
4. Cambio de política, reset/desactivación/grupos y protección del último administrador. Códigos de recuperación de un uso, dos peticiones simultáneas y auditoría sin secretos.
5. Backup cifrado y restauración en otra instancia Windows con clave recuperada; sin clave, error explícito antes de ofrecer un login inseguro. Esquema14 y recuperación CLI compatibles y verificados.
6. Navegador real: login y todos los formularios de reauth, pérdida de respuesta, misma identidad, borradores, recarga y segunda sesión. Revisión independiente antes de empaquetar o habilitar.

No hay migración14, librería TOTP añadida, endpoints ni interfaz MFA en este cierre de fundamento. Este archivo registra el alcance necesario para que el desarrollo posterior no se reduzca a un campo adicional en login.
