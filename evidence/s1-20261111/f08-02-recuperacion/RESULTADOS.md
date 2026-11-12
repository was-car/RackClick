# F-08.02 · contraseña y código sólo conceden reenrolamiento

11.11.2026. Cierre técnico con revisión independiente favorable. D/E sin operaciones, sin servicios, cuentas o bases instaladas, commits, push o despliegue.

## Reutilización e investigación

`MfaStore.Recovery`, autenticación, enrolamiento, rutas y GUI ya implementan el contrato del punto 3: contraseña validada → desafío verify → canje → desafío enroll → confirmación → sesión nueva. No se modifica producto ni se crea otro login. Se contrasta la identidad con el punto 3 y F-08.01 y se añade únicamente `MfaRestrictedRecoveryHttpTests.cs` para comprobar estados intermedios por HTTP, tanto en una cuenta ordinaria como global.

Fuentes oficiales consultadas el 11.11.2026: [integración ASP.NET Core 10](https://learn.microsoft.com/en-us/aspnet/core/test/integration-tests?view=aspnetcore-10.0) y [cookies ASP.NET Core 10](https://learn.microsoft.com/en-us/aspnet/core/security/authentication/cookie?view=aspnetcore-10.0). Se reutiliza WebApplicationFactory ya fijado y el sistema de sesión propio. No se incorpora Identity, código externo, dependencia o licencia nueva; siguen Npgsql directo y migraciones SQL.

## Resultado comprobado

- Canje con contraseña previamente validada, desafío verify y código propio devuelve un desafío enroll/CSRF nuevos; cuerpo de tres campos y ninguna cookie de sesión utilizable. Código sin desafío de contraseña se rechaza.
- Antes de configurar, durante pending, después de una confirmación inválida y tras otro login, la API de lectura/escritura responde 401 con desafío, cookie renombrada, sesión antigua o sin cookie. No cambian las diez tablas del snapshot del fixture; no se afirma comparación de todo el inventario.
- Sólo confirmar el nuevo TOTP devuelve sesión/CSRF nuevos; /me pasa a 200, la sesión antigua sigue en 401 y hay exactamente una sesión con MFA y un factor activo. La política de gracia no cambia. La exención global no evita un pending explícito.
- Claves sintéticas por DI y TestServer; SQL con cuenta de ejecución separada, no propietaria, CREATE TABLE rechazado con 42501. La preparación inicial del factor/sesión usa los métodos de almacén existentes para no agotar el límite HTTP en un recorrido anterior ya cubierto por F-07.05.

## Ejecuciones nuevas y errores conservados

Windows, SDK 10.0.401/runtime 10.0.12, PostgreSQL 17.11, esquema 46. Copia de fuentes `.local/f0802-8184c4f9/freeze`; binlogs, conexiones y diagnósticos privados. Producto: 227 archivos idénticos a F-08.01 en raíz/copia; una única prueba nueva. La DLL tiene un pin nuevo por recompilar en otra ruta; no se afirma identidad binaria con una candidata instalada.

| Ejecución | Resultado |
|---|---|
| Restore locked | exit 0 |
| Primer build | Falló: faltaba el import `Microsoft.AspNetCore.Hosting` en la prueba nueva; añadido sin cambiar producto |
| Build final | exit 0, cero errores y advertencias |
| Primer foco | 4 PASS / 2 FAIL de 6: el fixture gastaba diez intentos/minuto antes de su segundo login; recibió 429, el límite esperado del producto |
| Foco final | 6/6 PASS, 0 fallos y omitidas |
| Frontend actual | 20/20 Node PASS, 0 fallos y omitidas, sin navegador nuevo |

No se relajó el limitador de diez intentos/minuto ni una aserción de recuperación. Se cambió sólo la preparación previa al recorrido HTTP. El código de producto no tuvo defecto reproducido ni corrección en esta tanda. No se presenta lo anterior como fase roja de producto. Los intentos y binlogs originales quedan privados; las ejecuciones finales se identifican por sus hashes.

El foco final incluye los dos casos nuevos y cuatro existentes: `RecoveryReturnsOnlyFreshEnrollmentAndCannotReadTheTotpKey`, `NewFactorMustBeConfirmedBeforeRecoveryCreatesAnyNewSession`, `RecoveryReturnsOnlyAnEnrollmentChallengeAndRevokesTheOldSession` y `RecoveryOriginAndChallengeCsrfFailuresDoNotConsumeTheValidCode`. Node ejecuta `mfa-api.test.mjs` y `mfa-recovery.test.mjs`; conserva el aviso preexistente de tipo de módulo implícito sin cambiar la configuración.

Comandos: `dotnet build ... -c Release --no-restore -bl:<privado>/build-{}.binlog`, `dotnet test ... -c Release --no-build --no-restore --filter <foco F0802> --logger trx;LogFileName=<privado>/focus.trx -bl:<privado>/focus-{}.binlog` y Node 24.21.0 `--test` para los dos módulos anteriores. El driver privado crea/cierra su propio clúster y comprueba pines antes/después. Las pruebas y el fixture usados son fuentes del repositorio; no se entrega ni ejecuta un operador para D.

## Evidencia histórica y límites

La revisión final y Edge del punto 3 se reutilizan con fecha, ejecutor y proveedor sintético; no son ejecuciones nuevas. Program cambió después por CLI, conexión protegida y admisión/monitor de mantenimiento; se revisa su diff, sin exigir que conserve el hash histórico ni afirmar que todo el archivo es invariable. La fuente de canje/enrolamiento/GUI se contrasta en FUENTES.json.

F-08.02 acredita sólo el contrato técnico restringido. No se repiten navegador, TLS, DPAPI, servicio/SID real, candidata instalada o aceptación de Wascar. El host debe poder arrancar con su almacén; estos códigos no son una vía local de emergencia si se perdió. No se acredita el consumo concurrente/replay/rollback ni último administrador o custodia operativa por observar revocación como parte de este recorrido. F-08.03–.05 y todos los hitos completos de F-08 continúan pendientes.

Los 175 casos QA y resultados anteriores se conservan; se reutiliza QA-163 sin crear otro caso o habilitarlo por estas pruebas.


Pines finales: servidor `504f961eaf7196c7ef81b350d9197c78c3086ba644cf762ad97410a3bd0137d9`; pruebas `c57e04c28f4265b2e0129be4e0d9d15fb5468aa957814f8803a23c63fe8b482a`. FUENTES.json contrasta 29 fuentes asignadas del punto 3 con identidad exacta; Program se contrasta por diff, no por igualdad.


## Revisión y conciliación

[Dictamen independiente](review/DICTAMEN.md): el revisor repitió los dos casos nuevos en otro clúster, 2/2 PASS sin omisiones, con pines finales comprobados antes y después. Su ejecución se distingue del foco 6/6 y Node 20/20 del coordinador y del Edge histórico. Sólo F-08.02 suma 1/2: 1901/84 → 1943/84 = 23,130952…/100 del cierre restante. F-08.01 se conserva y F-08.03–.05/hitos permanecen pendientes.
