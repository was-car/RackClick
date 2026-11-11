# F-06.03 · rotación y caídas controladas

10.11.2026 · Continuación autorizada del paso21. Especificación: [protocolo aprobado](PROTOCOLO-ROTACION-MFA-v1.md); componentes y revisión [F-06.02](PASO-020-INVENTARIO-RETENCION-MFA.md). No se vuelve a diseñar custodia, política o cifrado.

**Objetivo:** implementar y ensayar la recuperación de una rotación interrumpida antes/después de cada publicación y del commit, preservando los secretos y metadatos de los factores.

**Arquitectura:** ampliar el almacén privado del coordinador, añadir un testigo PostgreSQL transaccional y coordinar ambas piezas mediante el fence existente. Una caída posterior al commit continúa hacia delante por el testigo; su ausencia requiere comprobar el estado inicial. Las copias retenidas conservan sus claves.

**Tecnologías:** .NET10/SDK10.0.401, PostgreSQL17.11/Npgsql directo, DPAPI y AES-GCM/RCKEY existentes. Migración046 aditiva para el testigo;001–045 intactas. Sin dependencias nuevas.

## Restricciones y decisiones

- D/E, VM, servicios y datos instalados sin operaciones; laboratorios nuevos y fuentes congeladas bajo `.local`.
- Sin commits, push, instaladores o despliegues. El árbol concurrente se conserva.
- No exponer rotación pública ni habilitarla en el servidor instalado por haber superado un ensayo de procesos. SID efectivo, persistencia ante pérdida eléctrica, custodia externa y candidata completa requieren su evidencia operativa.
- Material, contraseñas, sobres y logs/binlogs sólo privados. Evidencia versionable sin secretos.
- El catálogo cubre todas las raíces declaradas, sin inferir medios desconectados. Unknown bloquea. Se conserva todo el material anterior.
- Se reutilizan escritor de almacenes nuevos, proveedor, codecs, admisión, SCM y catálogo; no se copian bibliotecas ni cambian versiones.

## Investigación previa

Fuentes existentes: protocolo F-06.01 y dictamen F-06.02; implementación actual de `WindowsMfaMaintenanceStore`, `MfaMaintenanceAdmission`, `MfaSecretCipher` y `WindowsMfaKeyRecovery`.

Consulta oficial10.11.2026: [bloqueos PostgreSQL17](https://www.postgresql.org/docs/17/explicit-locking.html), [COMMIT](https://www.postgresql.org/docs/17/sql-commit.html) y [FileStream.Flush](https://learn.microsoft.com/en-us/dotnet/api/system.io.filestream.flush?view=net-10.0). Decisión: reutilizar/adaptar las primitivas actuales; PostgreSQL no publica archivos como parte de su transacción. Flush y relectura no acreditan por sí solos pérdida eléctrica.

## Tareas y propiedad

- [x] Almacén: `WindowsMfaMaintenanceStore.Rotation.cs`, ampliación mínima del almacén y pruebas nuevas. Preparar/publicar clave, anillo aditivo/final, identidades, journal/fence y reanudación idempotente.
- [x] Base: `046-mfa-key-rotation.sql`, `MfaRotationDatabase.cs` y pruebas. Bloquear, autenticar/recifrar todos los estados, revocar sesiones/desafíos afectados e insertar el testigo en una transacción. Fallo de auditoría/testigo deshace todo.
- [x] Coordinación: `MfaRotationCoordinator.cs`, guard de arranque, adaptación explícita de esquema y arnés privado. Preparación, sobre verificado antes del commit, conciliación y verificación final. API interna; no ruta web nueva.
- [x] Verificación: negativos de material/catálogo/UUID/estado, proceso terminado antes/después de publicaciones/commit, reapertura y Restore a otra DB de laboratorio. Regresión afectada, revisión por persona distinta, evidencia y continuidad. Acreditar sólo lo demostrado.

## Foco de revisión

No reutilizar versiones; factores pending/active/disabled; cero factores; no alterar antirreplay/gracia/roles; material o journal sustituido; commit incierto; copia DB anterior o sin testigo; pérdida de admisión; interrupción tras liberar fence; incompatibilidad de esquema/candidata; secretos en diagnósticos.

Cada prueba se ejecutará con pines de fuente/binarios y salidas privadas. Se registrarán intentos fallidos y límites, sin presentar excepciones inyectadas como apagones físicos. El índice permanece20,38/100 hasta la revisión y conciliación; este plan no concede crédito.


Cierre técnico10.11.2026: [resultado y límites](../evidence/s1-20261110/f06-03-rotacion/RESULTADOS.md), revisión independiente favorable. Ensayos de proceso/DB, no apagón ni servicio instalado. Crédito sólo F-06.03; lo operativo y F-06.04 siguen pendientes.
