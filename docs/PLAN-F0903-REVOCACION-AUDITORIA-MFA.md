# F-09.03 · revocación, auditoría y último administrador tras pérdida MFA

> Ejecución del coordinador mediante planificación/TDD/verificación y revisión independiente de seguridad. Continuación del contrato aprobado D2/F09; D/E y las instalaciones se preservan. Sin commits/push/despliegue.

**Objetivo:** cerrar el checkpoint31 sobre el protocolo loss-reset existente: revocación real de credenciales anteriores, registro transaccional sin secretos y recuperación del último global sólo mediante factor nuevo.

**Arquitectura:** reutilizar SQL047 y el witness dedicado `rackclick_private.mfa_loss_operation` como auditoría Windows conforme a D2§4.1. No crear un `audit_event` con actor app inventado ni otra migración. Usar la preparación/publicación y archivo privado aprobados F0902, así como login/enrolamiento/permisos/gracia45 de F08. Mantener CLI bloqueada y fence conservado: la composición de arranque/servicio y el ensayo operativo completo son F0904.

**Tecnologías:** Windows/.NET10 SDK10.0.401, Npgsql directo, PG17.11, DPAPI/ACL/RCKEY aprobados. Sin dependencias/versiones nuevas. Pruebas contra bases/roles nuevos y privados, no contra D/E.

## Investigación previa y decisión

Inspeccionados contrato D2§2.2/§4.1, ledger/pasos29–33, fuente y sello F0902, `MfaLossResetDatabase.ApplyAsync/RequireWitness`, coordinador, SQL047, `PostgresStore.Authentication`, `MfaStore.Enrollment/Recovery`, guardas de sesiones y último administrador y sus pruebas F08. El paso30 ya revoca sesiones/desafíos/códigos y escribe el witness en la misma transacción; se reutiliza, no se contabiliza como implementación nueva.

Fuentes oficiales11.11.2026: [transacciones PostgreSQL17](https://www.postgresql.org/docs/17/tutorial-transactions.html), [bloqueos](https://www.postgresql.org/docs/17/explicit-locking.html), [funciones trigger y retornoNULL](https://www.postgresql.org/docs/17/plpgsql-trigger.html). Se comprueba un caso adicional acotado: un trigger de fixture que suprima silenciosamente una escritura podría permitir commit con conteos inferiores al plan, porque la primera aplicación sólo valida plenamente su witness en Publish. Si el negativo lo reproduce, se exigirá el testigo completo **antes del commit**. No se afirma que esos triggers existan en la instalación real.

El resultado auditado por el witness es el commit de la transición DB loss-reset, con autoridad/SID Windows, operación, instalación/DB/Systemhaus, versiones, hashes y conteos. No significa que servicio o usuario hayan recuperado acceso. El archivo cifrado de factores permanece separado de esa auditoría. No se añade proyección web ni lectura runtime del schema privado para habilitar la operación.

## Archivos y pasos

- [x] **1. Referencia:** congelar la candidata F0902 y metadata; contrastar232fuentes y sello anterior. Escribir pruebas nuevas en `development/server/tests/RackClick.Quality.Tests/MfaLossRevocationTests.cs`, reutilizando el fixture anterior sin editarlo.
- [x] **2. Rojo pertinente:** triggers sintéticos que supriman factor/sesión/desafío/código/update del witness deben hacer fallar y revertir Apply. Ejecutar antes de tocar `MfaLossResetDatabase.cs`; distinguir defectos de fixture de producto.
- [x] **3. Corrección mínima si procede:** validar `ReadWitnessAsync` recién escrito mediante `RequireWitness` en la misma transacción, sin cambiar SQL047, APIs, roles, política o comandos. Los bloqueos e identidades existentes se conservan.
- [x] **4. Verificación:** uso real de sesiones y desafíos verify/enroll/códigos antiguos rechazado; no afectados conservados. Auditoría con campos cerrados, counts, autoridad Windows y sin secretos; fallo SQL/auditoría revierte todo. Único global conserva permisos/identidad/gracia y sólo confirma TOTP nuevo para volver a administrar; guarda last_admin_required sigue vigente. Reentrada sin duplicados. Una regresión pertinente sobre binarios finales; sin navegador/VM/instalador.
- [x] **5. Revisión y conciliación:** revisor distinto repite foco propio. Actualizar evidencia/changelog/continuidad/hoja y guía conservando175casos y resultados personales; sólo F0903 podría sumar1/2 (25,63→26,13), criterios/pesos intactos. F0904/.05 y seis hitos completos permanecen pendientes; observación Edge F0805 sigue abierta.

## Límites que deben permanecer explícitos

Los positivos de material se ejecutan con confianza Windows de fixture, no elevación/SYSTEM ni SID de servicio real. El reenrolamiento completo aquí es de almacén/backend con runtime PG restringido, no servicio reanudado con HTTPS. Los errores de auditoría y supresiones son inyectados en DB nueva; no se diagnostican como configuración real. No se libera el fence ni se habilita la CLI. Ningún éxito de prueba equivale a aceptación de Wascar.


Cierre técnico11.11: [resultados](../evidence/s1-20261111/f09-03-revocacion-auditoria/RESULTADOS.md), [dictamen](../evidence/s1-20261111/f09-03-revocacion-auditoria/review/DICTAMEN.md). Backend contrastado; fence/CLI/servicio y aceptación conservan sus límites.
