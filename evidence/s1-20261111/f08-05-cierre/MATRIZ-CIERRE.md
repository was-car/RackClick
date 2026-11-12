# F-08 · matriz conjunta del criterio de cierre

11.11.2026. Criterio literal: «Cada código sirve una sola vez incluso en concurrencia; recuperación no abre API antes del estado autorizado; reenrolamiento y revocación/auditoría sin secretos probados por revisor distinto».

| Condición | Fuente existente y comprobación final | Evidencia previa reutilizada / límite |
|---|---|---|
| Generación propia, entrega inicial única | `MfaAccountRecoveryCodes.cs`, `MfaRecoveryCodeCodec.cs`; solicitud duplicada con dos PID realmente esperando, una sola respuesta con diez valores | [F0801](../f08-01-generacion/MATRIZ-CRITERIO.md): codec, replay HTTP, permisos, sal/dominio, no dependencia de clave TOTP. «Una vez» es entrega por operación, no borrado de la memoria del usuario |
| Sólo hashes con sal por usuario | Formato rck1, CSPRNG de códigos y sal, dominio/Systemhaus/usuario y comparación constante; operaciones/auditoría sin valores originales | Codec y snapshots anteriores; no examen físico de toda memoria, disco o logs |
| Contraseña y código no son sesión | `AuthenticateForLogin`, `RedeemRecoveryCode`, middleware de `Program.cs`; dos casos HTTP ordinario/global, antes/después de start y confirmación inválida | [F0802](../f08-02-recuperacion/MATRIZ-CRITERIO.md): GET/POST con desafío, cookie renombrada, sesión antigua o nada →401; diez tablas invariantes |
| Factor nuevo como transición autorizada | `ConfirmEnrollment`; nuevo TOTP activa factor, consume desafío y emite sesión/CSRF nuevos; login alternativo durante pending permanece en enroll | HTTP y navegador; rol runtime separado, proveedor sintético DI, sin SID/DPAPI/TLS nativos |
| Consumo concurrente y revocación atómica | `MfaStore.Recovery.cs`; dos casos con el mismo código o dos distintos, solicitudes realmente bloqueadas, un ganador y testigo SQL de seis relaciones con el txid ganador | [F0803](../f08-03-consumo/MATRIZ-CRITERIO.md): códigos antiguos consumidos, sesiones/desafíos revocados; otra cuenta conserva seis colecciones y política global intacta |
| Replay/finalidad/CSRF y rollback | Negativos existentes repetidos en el build final; fallo forzado del audit revierte diez tablas, incluido el código presentado | Los límites/caducidad tras espera y rate limit se reutilizan del foco previo y regresión afectada; no se declara una nueva prueba de apagón/durabilidad |
| Único administrador recuperable | `MfaLastAdministratorRecoveryTests`: único global por ambas capacidades conserva identidad, contraseña, grupos y autoridad; administra y repone códigos tras TOTP nuevo | [F0804](../f08-04-ultimo-administrador/MATRIZ-CRITERIO.md). No requiere otro administrador ni reactiva cuentas revocadas/factores bloqueados |
| Pending no se cancela con Desactivar | Guard D2 ya corregido en `MfaAccountManagement.cs`, error409 del almacén `mfa_enrollment_required`, `CanDisable=false`; dos negativos propios/globales | Rojo/verde independiente [F0804](../f08-04-ultimo-administrador/D2-ROJO-VERDE-INDEPENDIENTE.json). Exención global con factor activo no pendiente permanece; no se modifica gracia45 |
| Revisión distinta del conjunto | [Dictamen](review/DICTAMEN.md): inspección del criterio completo y repetición de seis casos en otro clúster | No suma los mismos casos como cobertura distinta ni convierte revisión técnica en adopción |

## Conciliación de alcance

- F-08.01–.04 ya tienen evidencia y revisión acotadas. Este cierre contrasta esos resultados sobre las mismas DLL corregidas del paso27, con frontend preparado en copia privada. No atribuye los resultados anteriores a ejecuciones nuevas.
- El plan numerado manda conciliar la **generación explícita posterior al enrolamiento**, no implementar de nuevo la generación automática del texto histórico D2. Se conserva el criterio/peso congelado, con el límite operativo visible. La custodia real pertenece a Wascar.
- La guarda `last_admin_required` protege `security.manage` global; la exención MFA de administrador global exige también `systemhaus.manage`. No son definiciones intercambiables.
- Definición, implementación, pruebas y revisión pueden acreditarse sólo para este resultado técnico. Integración en la candidata objetivo y aceptación manual permanecen pendientes; F-09 pérdida total no se declara resuelto.
- La omisión de navegador del paso27 y el exit1 de su driver siguen registrados en su evidencia original. La ejecución de navegador de este lote, si pasa, será un resultado nuevo con sus propios hashes, sin reescribir el anterior.
