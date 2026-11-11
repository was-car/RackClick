# MFA-L1 · revisión independiente de seguridad · 25.10.2026

Revisor: agente `mfa_l1_security_review`, distinto de Claude. Alcance: lectura de enrolamiento/login/rutas y sus pruebas. **No cerrar MFA-L1 todavía:** hay cuatro hallazgos P2 y siguen pendientes HTTP positivo, concurrencia, rollback y auditoría. Estos hallazgos no impiden preparar el host de pruebas; no requieren otra decisión de custodia de Wascar.

No se modificó producto, pruebas, configuración, VM, QA o secretos. Único archivo escrito: este informe. R0 es histórico y S1 está autorizado; se respeta el encargo actual de revisión de sólo lectura.

## Hallazgos

### MFA-L1-S01 · P2 · El enrolamiento ignora el bloqueo del factor y puede reiniciarlo

`MfaStore.Enrollment.cs:160–167` lee cifrado, versión, intervalo y estado, pero **no lee `locked_until`**. `ChallengeOpen` (`132–134`) tampoco lo comprueba. `ConfirmEnrollment:98–103` escribe un bloqueo de 15 min tras cinco fallos, pero el camino posterior no lo consulta. Además, `StartEnrollment:49–55` pone `failed_attempts=0, locked_until=NULL` al sustituir el factor pendiente.

Un desafío nuevo o todavía utilizable puede confirmar el factor pendiente durante ese bloqueo. Reiniciar enrolamiento puede borrar la protección escrita. `CompleteVerify`, en cambio, sí comprueba el bloqueo del factor (`MfaStore.cs:65–69,120`). Afecta al enrolamiento ya autorizado por contraseña/desafío; **no demuestra omitir el TOTP de un factor activo sin autorización de reenrolamiento**.

Negativos requeridos: acumular cinco fallos repartidos entre desafíos, conservar uno con intentos disponibles y presentar un TOTP correcto durante el bloqueo; exigir rechazo y cero sesiones. Probar también `StartEnrollment` con factor bloqueado: no debe limpiar el bloqueo/contador ni reemplazarlo para evitarlo. La política de un reinicio explícito debe distinguirse de un retry ordinario.

### MFA-L1-S02 · P2 · Confirm puede esperar otro bloqueo después de comprobar la caducidad

`LockChallenge:185–205` adquiere la política con `FOR SHARE` y después mide `clock_timestamp()`. Al volver, `ConfirmEnrollment:114–118` ejecuta un `UPDATE` sobre esa política. Otro lector `FOR SHARE` compatible puede dejar pasar la lectura inicial y bloquear después ese UPDATE. La sesión se inserta posteriormente (`123–128`) sin volver a comprobar la caducidad.

El escenario permite que el desafío caduque durante la espera de la actualización, tras el reloj que se anunció como posterior a todos los bloqueos. Es **análisis de código y semántica de locks, no una reproducción PostgreSQL ejecutada por este revisor**. La compatibilidad usada está documentada en [PostgreSQL 17, bloqueos de fila](https://www.postgresql.org/docs/17/explicit-locking.html#LOCKING-ROWS): los lectores compartidos pueden coexistir y bloquean las actualizaciones de otra transacción.

Negativo requerido: mantener un `FOR SHARE` externo sobre la política, comenzar confirmación válida antes del vencimiento, comprobar que espera en el UPDATE, dejar vencer y liberar. Exigir cero sesión y ninguna activación aplicada. Adquirir el bloqueo de escritura necesario antes de leer el reloj evita esa promoción posterior; cualquier otra solución debe conservar revalidación y atomicidad.

### MFA-L1-S03 · P2 · `enroll/start` no tiene el limitador declarado

En `Program.cs:196–202`, el mapeo de `/api/v1/auth/mfa/enroll/start` termina con `});`, **sin** `.RequireRateLimiting("login")`. Confirmación sí lo añade en `215`; login/verificación también. No hay política global que cubra start: el limitador configurado es una política por endpoint.

La entrega afirma que las dos rutas tienen el mismo límite; el código no lo acredita. Start puede generar/cifrar y escribir un factor repetidamente, agravando S01. Añadir un negativo HTTP con el pipeline real: tras agotar el límite de la misma partición, start debe responder429. No desactivar el limitador en la factory para hacer pasar los demás tests.

### MFA-L1-S04 · P2 · Una ruta de enrolamiento consume un desafío verify antes de validar CSRF

`LockChallenge:140–145` busca la finalidad enroll y devuelve null si el token pertenece a verify. Tanto `StartEnrollment:35–39` como `ConfirmEnrollment:72–76` llaman entonces a `Burn` y hacen commit antes de llegar al chequeo CSRF. `Burn` (`MfaStore.cs:178–181`) actualiza sólo por token_hash, sin finalidad, por lo que consume el verify existente.

Condiciones: petición al endpoint enroll con Origin correcto y cookie de desafío verify presente; el CSRF puede faltar o ser erróneo. Resultado previsto por el código:401 sin sesión, pero el verify queda inutilizable. Es mutación de una finalidad ajena/denegación del desafío, **no escalada de permisos ni omisión del segundo factor**. Se conserva la protección Origin existente; no se afirma un ataque cross-site que la eluda.

El camino inverso de `CompleteVerify:45–48` sí rechaza una finalidad ajena sin Burn. El test `VerifyAndEnrollChallengesAreNotInterchangeable:132–147` sólo comprueba error/cero sesiones, por lo que no detecta el daño al verify.

Negativo requerido: para start y confirm, presentar verify válido con CSRF ausente/incorrecto; exigir rechazo, consumed_at sin cambiar y poder completar después ese verify por su ruta correcta. No consumir un token cuya finalidad no se obtuvo en la búsqueda, o limitar explícitamente el consumo a la finalidad que corresponde.

## Lo que sí está bien encaminado

- Desafíos opacos y finalidades separadas; sin emisión de sesión durante login de enrolamiento o start. La confirmación consume el desafío y emite token/CSRF nuevos en su transacción.
- CSRF de un desafío válido se comprueba antes de los contadores de código. Cuenta activa, política y revisión se vuelven a leer con bloqueos; la intención de usar hora de PostgreSQL es correcta, con la excepción S02.
- SQL externo parametrizado en los caminos consultados. Respuesta de secreto sólo en el endpoint del titular; los logs genéricos de Program no incluyen cuerpos ni secretos.
- Middleware conserva Host/HTTPS/Origin y excepciones por rutas exactas. Sin proveedor normal se mantiene el rechazo; eso no sustituye las pruebas positivas con proveedor de fixture.

## Límites de integración que deben quedar expresos

- `enrollment_pending=true` con `mfa_required=false` también admite enrolamiento. Confirm limpia pending, pero no cambia required; un login posterior sería password-only. Puede corresponder a QA/configuración voluntaria: se debe ensayar el contrato del control que fija esas banderas antes de producción, sin inventar aquí una política adicional.
- `PostgresStore.Session:78–90` y `RequireCurrentSession:58–75` todavía no consultan política/MFA de sesión. Confirm tampoco elimina sesiones antiguas. La activación/reset de política debe demostrar revocación atómica de sesiones anteriores; no afirmar que MFA global está listo por pasar enrolamiento.
- Auditoría de enrolamiento y pruebas HTTP/concurrencia/rollback siguen pendientes, como declara Claude. Versión de clave fija1 y proveedor real/rotación pertenecen al bloque de custodia posterior. No se reabren VM ni instaladores para esta revisión.

## Pruebas realmente ejecutadas

**Nueve aserciones en Python, en memoria, PASS** sobre fuente: evaluación del predicado `ChallengeOpen` extraído para un estado pending válido; ausencia de bloqueo del factor en predicado/SELECT; reset explícito de contador/bloqueo en start; ausencia del metadato de limitador en start y presencia en confirm. Se añadieron tres comprobaciones de fuente del lookup por finalidad, las dos ramas null/Burn anteriores al CSRF y la diferencia con el rechazo inicial de verify. No son ejecuciones C#, HTTP, PostgreSQL o concurrencia. Un primer lector del predicado falló por salto de línea en `eval`; se normalizó sólo whitespace y se repitió, sin atribuir ese fallo al producto.

No ejecuté build, suites, los 9 tests de enrolamiento ni los 70 históricos declarados; tampoco consulté `.local`, credenciales o datos de VM/QA. Esos resultados pertenecen a Claude hasta la repetición que coordine Codex. Fuente primaria externa consultada únicamente para compatibilidad de locks PostgreSQL 17.

## Archivos y símbolos consultados

- `AGENTS.md`, `docs/BRIEFING-MAESTRO.md` y contexto de decisiones/contrato heredado.
- `MfaStore.Enrollment.cs`: `StartEnrollment`, `ConfirmEnrollment`, `LockedChallenge`, `ChallengeOpen`, `LockChallenge`.
- `PostgresStore.Authentication.cs`: `Authenticate`, `AuthenticateForLogin`, `AuthenticateCore`.
- `MfaStore.cs`: `CompleteVerify`, `Burn`; `PostgresStore.cs`: `Session`, `RequireCurrentSession`.
- `Program.cs`: middleware y cuatro rutas de login/verificación/enrolamiento; `database/014-mfa.sql`; `MfaEnrollmentTests.cs` (nueve casos y fixture).

SHA256 de fuentes revisadas: Program `b1107007abf9053f3c7cf782f8549c50c84418790c41d45cfb84ef985379af4f`; MfaStore `a0de3d88bafe836a21d6a8d31ac7086906e3c6ba8d396492056ea18ce2d3c1ca`; Enrollment `79b0c7e4e87ef132049fe70748b7c396539fb0d23133585e415ba92bfd189bd2`; Authentication `024df8c81eddb1de4a1a435780b17a42758b5a65c101b08057fe257ab20b0571`.
