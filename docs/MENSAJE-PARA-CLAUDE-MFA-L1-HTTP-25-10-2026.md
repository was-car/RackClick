# Para Claude · opción A autorizada y revisión MFA-L1 · 25.10.2026

**Continúa con A. No falta una decisión de Wascar.** Se autoriza añadir `Microsoft.AspNetCore.Mvc.Testing` **[10.0.12]**, sólo al proyecto de pruebas, con `PrivateAssets="all"`. Versión comprobada en [NuGet oficial](https://www.nuget.org/packages/Microsoft.AspNetCore.Mvc.Testing/10.0.12); soporta net10.0. No elegir latest ni cambiar la versión .NET SDK/global.json, runtime o versiones fijadas existentes.

## Archivos adicionales y composición

Además de tu zona MFA-L1, quedan asignados:

- `development/server/tests/RackClick.Quality.Tests/RackClick.Quality.Tests.csproj` y su `packages.lock.json`: añadir la dependencia de pruebas y sus transitivas necesarias. Conservar el resto del árbol de dependencias; justificar cualquier diferencia colateral y verificar restore con lock después. Si hace falta el selector de proyecto Microsoft.NET.Sdk.Web para el soporte oficial, el ajuste queda permitido sólo en este csproj de pruebas, conservando net10.0/xUnit y el SDK .NET10.0.401 fijado; no cambiar el proyecto de producto.
- `MfaHttpTests.cs` y fixture/factory HTTP específico dentro del mismo proyecto de pruebas.
- `Program.cs`: ajuste mínimo de composición/configuración HTTP y visibilidad del entrypoint si hace falta. Ningún proveedor sintético ni biblioteca de pruebas se registra/transporta en el producto normal.

Resolver el proveedor desde **app.Services después de builder.Build()**, sin crear un segundo ServiceProvider. Crear entonces el PostgresStore HTTP con MfaAvailable correcto. Mantener las ramas migrate/bootstrap con su store separado y retorno antes del host; recover-admin sigue independiente. Esos comandos no deben exigir origen HTTPS, levantar servidor ni proveedor MFA.

El fixture registra el proveedor exclusivamente en ConfigureTestServices. Puedes usar como marcador un tipo público del ensamblado servidor (por ejemplo PostgresStore); si eliges Program, está permitido añadir la declaración partial pública mínima. La [API de WebApplicationFactory](https://learn.microsoft.com/en-us/dotnet/api/microsoft.aspnetcore.mvc.testing.webapplicationfactory-1?view=aspnetcore-10.0) admite un tipo del ensamblado de entrada.

Conexión/origen/frontend se leen hoy antes de Build: no asumir que un callback de configuración tardío los sustituyó. Configurar antes de su uso y demostrar base/origen efectivos. Si necesitas entorno temporal, aislar esos tests del paralelismo y restaurarlo en finally. No convertirlo en un interruptor de proveedor de pruebas disponible por configuración del producto.

## Correcciones de la revisión, en el mismo lote

El informe [REVISION-SEGURIDAD.md](../evidence/s1-20261025/mfa-l1-revision-codex/REVISION-SEGURIDAD.md) identifica cuatro P2 por análisis de código; no son reproducciones PostgreSQL nuevas del revisor. Añade los negativos que los reproduzcan antes de corregir:

1. **Bloqueo del factor:** el enrolamiento no comprueba locked_until y Start restablece contadores/bloqueo. Un desafío nuevo o repetir Start no debe eludir el bloqueo ni reiniciar el presupuesto de intentos. Cubrir códigos erróneos acumulados, nuevo desafío durante bloqueo y recuperación tras expirar el bloqueo.
2. **Caducidad tras otra espera:** se toma política FOR SHARE, se lee el reloj y Confirm luego la actualiza, pudiendo esperar una promoción de bloqueo después de medir vigencia. Retener un bloqueo compartido externo, hacer caducar durante esa espera y exigir cero sesión/activación. Obtener el bloqueo necesario antes de medir o revalidar después de todas las esperas, sin bucles de espera artificiales.
3. **Limitador de start:** la ruta enroll/start termina sin RequireRateLimiting, aunque la entrega lo declara. Aplicar el control y probar 429 sin desactivar el limitador para hacer pasar el resto de tests.
4. **Finalidad y CSRF:** enviar un verify a enroll hace que el lookup devuelva null y Burn lo consume antes de CSRF. Rechazar el uso cruzado sin consumir el desafío válido ajeno; probar ambas rutas y que el verify original siga utilizable. Es mutación cruzada/denegación, no una sesión ni escalada demostrada.

La auditoría de enrolamiento está declarada pendiente: añade eventos mínimos sin secretos para las transiciones que cierren el lote, con la confirmación dentro de la misma transacción. El rollback forzado al escribir auditoría debe dejar factor, política, desafío y sesiones exactamente como antes. No guardar secreto, ciphertext, URI otpauth, códigos, cookie o CSRF en auditoría/evidencia pública.

## Cobertura y entrega

Completar positivo HTTP enrolar→confirmar→API y siguiente login verify; negativos de Origin/CSRF/cookies/finalidad/replay, falta de proveedor, doble consumo y revocación/concurrencia/rollback con PostgreSQL17 real. El modo normal sin proveedor conserva MfaAvailable=false y rechazo explícito sin emitir desafíos o sesiones cuando MFA se exige. Mantener los tests históricos y añadir regresión CLI de las ramas afectadas.

WebApplicationFactory/TestServer ejecuta el pipeline real, pero su HTTP en memoria **no acredita TCP/TLS ni cookies de navegador**. Etiquetar resultados correctamente y conservar el contraste Kestrel de modo normal. La [documentación Microsoft](https://learn.microsoft.com/en-us/aspnet/core/test/integration-tests?view=aspnetcore-10.0) explica esa infraestructura; no sustituir PostgreSQL por una base en memoria.

Prueba primero los negativos nuevos, corrige y ejecuta una regresión pertinente al estabilizar. Builds/binlogs y logs completos privados en `.local/`; publicar sólo resultados sanitizados y hashes. No afirmar que los70tests informados fueron repetidos por Codex: no los repetí en esta revisión.

No hace falta otra aprobación para estos ajustes técnicos. Conservar evidencia anterior; guardar nuevos hashes/comandos/resultados y límites en la entrega. Sin tocar C2/InventoryPanel/OperationDialog, frontend, SQL014, instaladores, VM/QA o ledger; sin commits/push. No cerrar MFA-L1 hasta completar lo anterior. Proveedor real, recuperación completa, UI y candidata final siguen pendientes; no anunciar MFA disponible para usuarios.
