# MFA-L1 · revisión inicial y decisión HTTP · 25.10.2026

**Opción A autorizada para continuar. El lote aún no queda aceptado como terminado.** Claude puede añadir el paquete Microsoft de pruebas y el ajuste DI mínimo, dentro de los archivos ampliados en [el mensaje de continuación](MENSAJE-PARA-CLAUDE-MFA-L1-HTTP-25-10-2026.md).

## Contraste

Las cuatro fuentes de producto coinciden con los hashes entregados: Program b1107007…, MfaStore a0de3d88…, Enrollment79b0c7e4… y Authentication024df8c8…. Copias y SHA completos conservados en [la evidencia](../evidence/s1-20261025/mfa-l1-revision-codex/HASHES-REVISADOS.json).

Implementado en fuente: desafío enroll restringido, factor pending cifrado, confirmación transaccional y rutas. Proveedor normal ausente. La evidencia de Claude informa nueve tests nuevos y regresión70PASS/1omitida Docker, además de HTTP normal409/503/401 sin sesiones/desafíos/factores. **No se repitieron aquí esas ejecuciones** ni se les atribuye cobertura de HTTP positivo, concurrencia o rollback que todavía no tienen.

## Revisión independiente

El revisor de seguridad ejecutó nueve comprobaciones de fuente/predicado en memoria; no C#, HTTP o PostgreSQL. Detectó cuatro P2: bloqueo del factor ignorado/reset por Start; posible espera de actualización de política después del reloj; start sin el limitador declarado; consumo cruzado de verify desde enroll antes de CSRF. [Informe y negativos](../evidence/s1-20261025/mfa-l1-revision-codex/REVISION-SEGURIDAD.md). La caducidad durante promoción de bloqueo es análisis pendiente de reproducción, apoyado en los [bloqueos de fila de PostgreSQL17](https://www.postgresql.org/docs/17/explicit-locking.html#LOCKING-ROWS), no un ensayo ejecutado por Codex.

Son correcciones concretas dentro del flujo asignado; no bloquean preparar el host HTTP y no requieren nuevas decisiones del usuario. Auditoría y matriz HTTP/concurrencia/rollback siguen pendientes antes de cerrar el bloque.

## Dependencia y composición

[Microsoft.AspNetCore.Mvc.Testing10.0.12](https://www.nuget.org/packages/Microsoft.AspNetCore.Mvc.Testing/10.0.12) está publicado para net10.0 y se autoriza con versión exacta, sólo en pruebas/PrivateAssets=all. Ningún cambio silencioso de SDK/runtime o dependencias existentes. El [soporte Microsoft de integración](https://learn.microsoft.com/en-us/aspnet/core/test/integration-tests?view=aspnetcore-10.0) proporciona WebApplicationFactory/TestServer.

La inspección arquitectónica confirma que resolver DI antes de Build no funciona y que MfaAvailable es init-only. Hay que separar store CLI y HTTP, resolver proveedor en el contenedor final y preservar migrate/bootstrap/recover-admin sin levantar host. No crear un segundo ServiceProvider. Verificar configuración efectiva, porque la conexión y el origen se leen antes del Build actual.

La inyección sintética pertenece exclusivamente al fixture. Sin registro normal se mantiene el rechazo; ni variable de entorno, selector ni clave de prueba dentro del producto. TestServer no prueba por sí solo TCP/TLS o comportamiento de un navegador. No se anuncia MFA utilizable ni se cambia QA.

## Estado

F-07/F-12 en curso; sin crédito nuevo por esta revisión o por autorizar el paquete. Cierre del pendiente **6,21/100**, porcentaje global sin recalcular. Custodia/recuperación de Wascar continúan confirmadas. No builds/tests de producto nuevos por Codex, instalación, VM, QA, paquetes de entrega, commits o push.
