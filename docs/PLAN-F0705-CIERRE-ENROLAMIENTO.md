# F-07.05 · plan de cierre del enrolamiento restringido

11.11.2026. Paso23 autorizado por Wascar. D/E se conservan sin operaciones. Trabajo del coordinador y revisión distinta acotada; sin commits, push, instalaciones o adopción.

**Objetivo:** usuario con enrolamiento exigible confirma su primer factor y recibe una única sesión nueva; desafío/enrolamiento incompleto sin acceso a /me, clientes o mutaciones, con negativos concurrentes y revisión independiente.

**Especificación vigente:** F07 en `PLAN-CIERRE-RACKCLICK.json`, decisión de gracia45/exención global29.10, revisiones L1 y GUI/dashboard existentes. No convertir el criterio histórico de primer inicio en obligación inmediata para todas las cuentas nuevas.

**Arquitectura:** conservar login, proveedor Windows y endpoints. Añadir sólo prueba integrada de las rutas/etapas no cubiertas conjuntamente, con migraciones actuales46, material DPAPI de laboratorio y rol de ejecución sin propiedad ni DDL. Reutilizar UI EN/DE/ES, cookies, locks, rollback y caídas ya probados.

## Investigación y elección

Se contrastó primero el código y las evidencias L1ronda2, GUI27.10, dashboard29.10, C10 y D11. La prueba histórica de challenge comprueba /me y logout, pero no toda la matriz de clientes/mutaciones antes y después de crear factor pending. El código de confirmación y locks se conserva; enrolamiento sólo amplió selección de clave activa respecto a L1. Se elige prueba acotada sobre fuentes actuales, frente a limitarse a contar pruebas antiguas o repetir toda la QA.

Consulta oficial11.11: [ASP.NET Core10 integración](https://learn.microsoft.com/en-us/aspnet/core/test/integration-tests?view=aspnetcore-10.0), [PostgreSQL17 locks](https://www.postgresql.org/docs/17/explicit-locking.html). Se reutilizan WebApplicationFactory y librerías fijadas; no dependencias nuevas. TestServer comprueba HTTP en memoria, no TCP/TLS/cookies de navegador. La evidencia nativa existente se cita con su alcance propio.

## Tareas y comprobaciones

- [x] **1. Matriz y referencias.** Criterio literal y F0701–04→evidencia/pines/límites. Contrastar GUI/dashboard y el núcleo actual; distinguir smoke D11 fallido por MFA personal de su prueba sintética positiva posterior.
- [x] **2. Brecha integrada.** `MfaEnrollmentClosureTests.cs` y `tools/tests/run_mfa_enrollment_closure.py`: cuentas nuevas/existentes con gracia ya vencida; contraseña inválida sin autoridad; login enroll; matriz /me, /customers, creación de cliente y preferencias con challenge normal y renombrado como Session, en estados challenge/pending/código inválido. Confirmaciones concurrentes, un solo factor activo/sesión/CSRF nuevos, replay/reintento sin segunda sesión. Cuenta runtime observada en escrituras y DDL rechazado; DPAPI/versión activa7 real con identidad de laboratorio.
- [x] **3. Verificación/revisión.** Build aislado con pines; casos nuevos y una regresión pertinente del núcleo conservado (enrolamiento, HTTP y gracia45), no toda la suite RackClick. Revisión independiente del criterio/ejecución. Si aparece defecto, reproducir y corregir por separado; no inventar fase roja de pruebas que sólo amplían cobertura.
- [x] **4. Cierre y continuidad.** Ficha23, resultados sanitizados, matriz y dictamen; conciliar sólo F0705 peso1/2 con aprobación técnica. Mantener candidata/servicio/SID/custodia real y aceptación separadas, preservar resultados QA, regenerar documentación e índices y verificar privacidad.

## Foco de revisión

- Un desafío enviado con otro nombre de cookie sigue sin ser sesión API.
- Crear factor pending o fallar un TOTP no concede autoridad ni muta inventario/preferencias.
- Dos confirmaciones concurrentes/reintentos no crean dos sesiones ni reutilizan el CSRF del desafío.
- La gracia procede de creación/activación persistida; no se fuerza la política histórica inmediata ni se altera la exención global.
- El test usa el rol restringido realmente en las escrituras HTTP; no deducirlo de la configuración ni afirmar token de servicio/TLS por TestServer.

Cierre técnico11.11: [resultados](../evidence/s1-20261111/f07-05-enrolamiento/RESULTADOS.md), [revisión](../evidence/s1-20261111/f07-05-enrolamiento/review/DICTAMEN.md). Sin cambios de producto ni despliegues; integración y aceptación pendientes.
