# F-08.03 · plan de conciliación del consumo transaccional

> Ejecución del coordinador con las skills de planificación, verificación y revisión independiente ya aplicadas a F-08.01/.02. Continuación autorizada por Wascar, sin commits ni operaciones en D/E.

**Objetivo:** comprobar consumo único, revocación por cuenta, replay, rollback y ausencia de secretos en lo persistido, conservando el canje del punto 3.

**Arquitectura:** `RedeemRecoveryCode` ya usa una transacción y el orden cuenta → factor → desafío → política → códigos. Reutilizar pruebas existentes y evidencia F-08.01/.02. Añadir sólo una prueba parametrizada que demuestre dos canjes realmente bloqueados simultáneamente y un testigo SQL del commit ganador, con mismo código o dos códigos del conjunto antiguo.

**Tecnologías y restricciones:** .NET 10.0.401, PostgreSQL 17.11, Npgsql y xUnit existentes; rol propietario separado de runtime sin DDL. Producto, interfaz, migraciones y dependencias intactos. Clúster nuevo bajo `.local/`; credenciales, valores, TRX y binlogs privados. No alterar VM, servicios/cuentas/bases instaladas ni QA personal.

**Especificación:** literal F-08.03 del [ledger](PLAN-CIERRE-RACKCLICK.json), paso 26 del [plan numerado](PLAN-PENDIENTES-NUMERADO.md), [D2](DECISION-D2-CUSTODIA-CLAVE-TOTP.md) y contrato ya aplicado de [punto 3](PUNTO3-FUNCIONES-PENDIENTES.md). El canje retira todo el conjunto de diez códigos del usuario, no solamente el presentado, y sólo concede enrolamiento restringido. No modifica gracia45 ni su exención global.

## Investigación previa y decisión

Se reutilizan fuente y revisión del punto 3, F-08.01 y F-08.02. Consulta oficial del 11.11.2026: [transacciones PostgreSQL 17](https://www.postgresql.org/docs/17/tutorial-transactions.html) y [bloqueos explícitos PostgreSQL 17](https://www.postgresql.org/docs/17/explicit-locking.html). Se conservan transacciones y bloqueos existentes; no se adopta una biblioteca o algoritmo nuevo. Observar `pg_locks` y un testigo de transacción no acredita por sí solo un apagón, TLS o servicio Windows instalado.

## Tareas verificables

- [x] **1. Identidad y criterio.** Conservar los 227 archivos de producto de F-08.02 y contrastar el núcleo del punto 3. Matriz código → prueba nueva/existente → límite. Revisar parámetros SQL, transacción, validaciones posteriores a esperas, revocación por usuario y auditoría sin valores originales.
- [x] **2. Concurrencia observada.** Crear únicamente `development/server/tests/RackClick.Quality.Tests/MfaRecoveryRedemptionTransactionTests.cs`: dos escenarios con el mismo código o códigos distintos del conjunto. Retener la fila de usuario hasta observar dos PID esperando; después, exactamente un desafío enroll ganador. Verificar revocaciones y que las seis relaciones afectadas por el ganador comparten txid y rol runtime. Testigos/triggers sólo en la base nueva de pruebas, sin registrar valores secretos. Comparar estado de otra cuenta sin cambios.
- [x] **3. Foco y revisión distinta.** Ejecutar dos casos nuevos y siete existentes de canje, consumo concurrente, replay/finalidad/CSRF, política/caducidad, caducidad tras bloqueo de código, límite de fallos y rollback de auditoría. Conservar resultados individuales. Revisor distinto repite los dos casos nuevos y el rollback existente en otro clúster. No repetir Node/Edge de F-08.02/punto 3 si sus fuentes se conservan; atribuirlos como históricos.
- [x] **4. Conciliación.** Ficha 26, evidencias sanitizadas, hashes, revisión, changelog y continuidad. Sólo F-08.03 (+1/2) si es conforme. Conservar F-08.04/.05 e hitos operativos de F-08 pendientes, los 175 casos QA y sus resultados. Regenerar y verificar índices y guía.

## Foco de revisión

- Un perdedor, replay o fallo de auditoría no puede producir otra recuperación/sesión ni un consumo parcial.
- Retirar todo el conjunto, sesiones y desafíos anteriores del usuario correcto; no afectar otra cuenta.
- La caducidad se mide después de todos los bloqueos, también los de filas de códigos; finalizar una espera no revive el desafío.
- El testigo SQL sólo registra relación, operación, rol y txid; no códigos, semillas, tokens o conexiones. Los snapshots se comparan sin volcar valores.
- F-08.03 técnico no equivale a custodia, último administrador, recuperación local, candidata instalada o aceptación de Wascar. Si se reproduce un defecto, corregir después del negativo; no inventar fase roja cuando el producto ya cumple.


Cierre técnico del 11.11: [resultados](../evidence/s1-20261111/f08-03-consumo/RESULTADOS.md) y [dictamen](../evidence/s1-20261111/f08-03-consumo/review/DICTAMEN.md). Sin cambios de producto o disponibilidad instalada.
