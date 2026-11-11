# F-08.02 · plan de conciliación de la recuperación restringida

> Ejecución del coordinador con `superpowers:executing-plans`; revisión independiente acotada al terminar. Continuación autorizada por Wascar, sin otra aprobación de arranque.

**Objetivo:** comprobar que contraseña y código de recuperación sólo conceden un desafío de enrolamiento; una sesión API nueva requiere confirmar el nuevo factor.

**Arquitectura:** conservar `RedeemRecoveryCode`, rutas HTTP, middleware y GUI existentes del punto 3. Reutilizar sus pruebas y revisión; añadir únicamente cobertura HTTP de los estados intermedios y del intento de usar un desafío como sesión, para cuenta ordinaria y administrador global. Compilar en copia aislada con producto fijado, sin instalar nada en D o E.

**Tecnologías:** .NET 10.0.401, ASP.NET Core/TestServer, Npgsql directo, PostgreSQL 17.11 y xUnit existentes. Sin nuevas dependencias ni migraciones.

**Especificación:** literal F-08.02 de [ledger](PLAN-CIERRE-RACKCLICK.json), paso 25 del [plan numerado](PLAN-PENDIENTES-NUMERADO.md), [D2](DECISION-D2-CUSTODIA-CLAVE-TOTP.md) y recorrido ya decidido en [punto 3](PUNTO3-FUNCIONES-PENDIENTES.md). No cambiar gracia de 45 días ni exención global. Una cuenta global que ya activó MFA también debe completar el factor nuevo al recuperar.

## Investigación y decisión

El punto 3 ya implementa el canje sin sesión; F-07.05 ya prueba que un desafío de enrolamiento no autoriza la API. Se contrastarán hashes y diferencias de Program antes de reutilizar ambas evidencias. Consulta oficial del 11.11.2026: [pruebas de integración ASP.NET Core 10](https://learn.microsoft.com/en-us/aspnet/core/test/integration-tests?view=aspnetcore-10.0) y [cookies ASP.NET Core 10](https://learn.microsoft.com/en-us/aspnet/core/security/authentication/cookie?view=aspnetcore-10.0). Se reutiliza WebApplicationFactory ya fijado, sin adoptar Identity ni cambiar el mecanismo de sesión propio. TestServer no demuestra TLS, servicio Windows ni comportamiento de un navegador instalado.

## Restricciones

- D y E, instalaciones, cuentas y datos reales intactos; PostgreSQL nuevo con propietario y ejecución separados.
- Copia de fuentes identificada bajo `.local/`; no incorporar el árbol concurrente a un commit ni publicar.
- No confundir revocación observada como condición del canje con cierre de concurrencia/rollback F-08.03 o último administrador F-08.04.
- No secretos en evidencia pública, binlogs privados; no capturas con códigos ni resultados de Wascar alterados.
- Si se encuentra un defecto, reproducirlo antes de corregir. Una prueba nueva de comportamiento existente no implica fase roja ni arreglo de producto.

## Tareas verificables

- [x] **1. Conciliar fuentes y criterio.** Matriz literal → código → evidencia del punto 3/F-07.05 → límite. Conservar inventario de las 227 fuentes de producto de F-08.01; revisar `MfaStore.Recovery.cs`, `MfaStore.Enrollment.cs`, `Program.cs`, autenticación y GUI.
- [x] **2. Cubrir estados intermedios.** Crear sólo `development/server/tests/RackClick.Quality.Tests/MfaRestrictedRecoveryHttpTests.cs`. Reutilizar `MfaAccountManagementTests.Laboratory`; dos casos HTTP con cuenta ordinaria y global, contraseña/código, desafío nuevo sin sesión, API de lectura/escritura denegada antes/después de start y confirmación inválida, cookie renombrada denegada, login durante recuperación todavía restringido, confirmación válida como único acceso final. Comprobar rol SQL sin DDL y conservación de política. No modificar helpers aprobados.
- [x] **3. Verificación pertinente y revisión.** Compilar copia fijada con binlog privado, ejecutar el nuevo foco y los existentes de canje/restricción/Origin/CSRF, más Node del adaptador. Revisor distinto inspecciona fuente/diff y repite el nuevo foco en otro laboratorio. Reutilizar Edge histórico con atribución, sin presentarlo como ejecución nueva.
- [x] **4. Registrar cierre real.** Ficha 25, resultados, hashes y límites. Sólo F-08.02 (+1/2) si es conforme; conservar los otros checkpoints e hitos de F-08 pendientes. Actualizar continuidad, changelog e índices; preservar los 175 casos QA y reutilizar QA-163 sin habilitarlo por estas pruebas.

## Foco de revisión

1. Código sin contraseña validada/desafío previo: no conceder recuperación ni sesión.
2. Desafío de verify o enroll presentado como cookie de sesión: denegar lecturas y escrituras sin cambios persistidos.
3. Enrolamiento pendiente o confirmación inválida: no emitir sesión; repetir login con contraseña tampoco debe eludirlo, incluida cuenta global.
4. Sólo confirmación válida: sesión y CSRF nuevos, factor activo, desafío consumido; la cookie antigua no recupera autoridad.
5. Origen/CSRF, política y roles SQL: conservar controles actuales; no inferir TLS/servicio real/custodia ni cierre integral de F-08.


Cierre técnico del 11.11: [resultados](../evidence/s1-20261111/f08-02-recuperacion/RESULTADOS.md) y [dictamen](../evidence/s1-20261111/f08-02-recuperacion/review/DICTAMEN.md). No se modifica producto ni disponibilidad instalada.
