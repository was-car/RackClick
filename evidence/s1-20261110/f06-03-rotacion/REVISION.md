# Revisión independiente · F-06.03

10.11.2026. Revisor distinto de los implementadores. Encargo acotado del coordinador: lectura de producto, evidencia privada en `.local/f0603-review/` y este dictamen. Git concurrente inspeccionado; no modifiqué producto, pruebas de producto, instalaciones, dependencias, ledger ni trabajo ajeno. Sin commits o publicación.

**Dictamen favorable exclusivamente para el cierre técnico de F-06.03:** «Inyectar caída antes/después de cada publicación y commit; reinicio/Restore deben identificar estado y recuperar sin perder factores». La matriz final y los focos independientes sustentan ese criterio en laboratorio Windows/PostgreSQL, con terminación real de procesos, reapertura y Restore. Recomiendo conciliar únicamente su peso congelado **5/8**. No acredita F-06 completo, F-06.04, operación instalada, persistencia ante apagón, QA o adopción de Wascar.

## Archivos y símbolos consultados

- `AGENTS.md`, `docs/BRIEFING-MAESTRO.md`, encabezados vigentes de continuidad/progreso y `docs/EQUIPO-Y-SKILLS.md`; `docs/PROTOCOLO-ROTACION-MFA-v1.md`, `docs/PLAN-F0603-ROTACION-Y-CAIDAS.md`, criterio literal del ledger y revisión F-06.02 retirada. Las pruebas históricas se reutilizan como antecedentes, no como ejecuciones nuevas.
- `MfaRotationCoordinator.cs`: `PrepareAsync`, `ExportAsync`, `ResumeAsync`, `Exclusive`, `RequireAdmission`, `ReadPlan`, `RequireWitness`, `VerifyEnvelope`. `MfaRotationDatabase.cs`: vínculo/testigo, `ValidateBinding`, `LockAsync`, `ReadSnapshotHashAsync`, `RewrapAsync`, `ReadWitnessAsync`, `ValidateCommittedAsync`, identidades, locks y escritura del testigo. SQL046 y `SchemaMigrations.Apply/LatestVersion`.
- `WindowsMfaMaintenanceStore.Rotation.cs`: preparación, selección de versión, journals, objetos retenidos, estados derivados, publicadores de clave/anillos y finalización. `WindowsMfaMaintenanceStore.RotationGuard.cs`: `RecordRotationStartupPrior` y `PublishRotationStartupReceipt`; base del almacén: `ReadPending`, `RequireNoPending`, ACL, handles, flush e identidades. `MfaRotationStartupGuard.ValidateAsync` e integración previa al listener en `Program.cs`.
- Reutilización: `MfaMaintenanceCoordinator` — catálogo/material, autenticación de factores, identidad SQL y compatibilidad45/46—; `MfaMaintenanceAdmission`; DPAPI/`ProtectVersionMaterial` del escritor existente; proveedor y `MfaSecretCipher.Open/Seal`. Adaptación cerrada45/46 de `MfaBackupInventoryCommand.ValidateSchemaVersion`. Se contrastó la interacción con retirada, catálogo y claves retenidas.
- Pruebas `MfaRotationDatabaseTests`, `WindowsMfaRotationStoreTests`, `WindowsMfaRotationStartupReceiptTests`, `MfaRotationContractTests`, `MfaRotationProcessTests`; arnés `tools/tests/run_mfa_rotation.py`, sus comprobaciones Python y soporte PG. Evidencias finales `FUENTES.json`, `CAMBIOS.patch`, `POSTGRES-REGRESION.json`, `MATRIZ-CAIDAS.json`, `NEGATIVOS.json` y `RESULTADOS.md`.

La consulta del grafo no proporcionó cobertura: exigió identificadores de proyecto/workspace no disponibles en esta llamada. Esta revisión cita archivos actuales y sus huellas verificadas, sin atribuirles cobertura de índice.

## Hallazgos corregidos y comprobación

1. **Alta/P1, coherencia de arranque:** la guardia inicial aceptaba un factor antiguo todavía auténtico y no distinguía una DB anterior sin testigo de una instalación inicial. Lo comuniqué por lectura estática; no ejecuté aquella versión como RED. La corrección liga un recibo público al binding/testigo y exige que todos los factores usen la versión comprometida, además de autenticarlos. Mis trabajadores PG ejecutaron los negativos de factor antiguo, testigo ausente y anillo aditivo, y el rechazo de la DB origen antigua después del Restore.
2. **Media/P2, colisión/sustitución de recibo:** el primer publicador reemplazaba un marcador ajeno de bytes distintos sin fijar el estado previo. Se comunicó antes del cierre. Ahora conserva ausencia u objeto/hash previo, valida el recibo reconocido contra su testigo y fija la identidad publicada. Mis cuatro pruebas de recibo pasan: colisión conservada, mismos bytes en otro objeto rechazados y reapertura antes/después de publicar con la misma identidad. La publicación mantiene el fence hasta completar la puerta correspondiente.
3. **Media/P2, pérdida de admisión:** tras `data_verified`, una conexión perdida podía descubrirse sólo después de retirar el fence, en el commit de la transacción de verificación. La corrección revalida la admisión después de ese checkpoint y justo antes de completar. Leí los tres negativos finales del coordinador: terminación real del backend en ambas posiciones y colisión del recibo; todos conservan fence/objeto ajeno y permiten conciliación posterior. No repetí esos tres negativos por separado.
4. **Alta/P1, operación completada con DB anterior:** durante el Restore anterior al commit, el coordinador detectó que `ResumeAsync` podía volver a recifrar la DB origen antigua cuando el almacén local ya estaba `verified` y faltaba allí el testigo. Su RED real —`No exception was thrown`— está descrito y conservado por el coordinador; no lo atribuyo a mi ejecución. La corrección rechaza con `mfa_rotation_completed_witness_missing`. Mi repetición con los últimos binarios prueba Restore en otro clúster y el rechazo por guard **y coordinador** de aquella DB anterior, sin modificarla.

No quedan hallazgos bloqueantes abiertos para este criterio técnico. La transacción cambia únicamente ciphertext/versión del factor, conserva Systemhaus/usuario y metadatos funcionales, usa la nueva versión en su AAD, revoca/consume sólo la seguridad afectada e inserta el testigo en el mismo commit. Los fallos de autenticación/testigo revierten la transacción. La reanudación comprometida usa el testigo y no vuelve a cifrar. El almacén conserva las claves anteriores y bloquea colisiones, material desconocido y operaciones de retirada concurrentes.

## Ejecuciones propias y pines

Fuente de ejecución: `.local/f0603-rotation-c32a5e0b/freeze`. Todos los comandos terminaron; no quedaron agentes/pruebas trabajando por este dictamen.

| Conjunto de binarios | Servidor SHA256 | Pruebas SHA256 |
|---|---|---|
| Primera revisión ejecutada | `525ed277e23cc5a591680e4d891e59ac2583395125a79edf02489b31be52a621` | `45206f044390c94ff846071ff0a4dfe1139403cf3ef7340afc70d27e73cf9f2a` |
| Final, tras rechazo de DB anterior | `610b3841446046ae2d5a17488376e57ef5bcfbd8652ffba6ceb3eacfad7f4685` | `0f28a021bb698b87b8402258078eee89c61f024528624da1992e5c7f7499ac76` |

- `C:/Python312/python.exe -B tools/tests/run_mfa_rotation.py --source-root <freeze> --expected-server-sha256 <primer pin> --expected-tests-sha256 <primer pin> --mode database`: **12/12**,0 fallos/errores/omitidas,exit0. PostgreSQL17.11/SQL46: estados pending/active/disabled, secreto/metadatos, cuentas no afectadas, cero factores, rollback por ciphertext/testigo, locks/concurrencia, identidad, versión desconocida, colisión de versión y límites de ciphertext.
- Mismo arnés y primeros pines, `--mode crashes --only-cut after_db_commit`: terminación intencional del árbol propio,exit1 observado; **Restore1/1 y reanudación1/1 PASS**,sin omitidas,exit0. Testigo comprometido conservado, sin segundo recifrado. Dump custom y `pg_restore --single-transaction` en otro clúster; origen conservado.
- DLL de pruebas directa con `-class RackClick.Quality.Tests.WindowsMfaRotationStartupReceiptTests -noLogo`, primeros pines: **4/4**,0 errores/fallos/omitidas/no ejecutadas,exit0. Sin build, MSBuild o DB.
- Últimos pines, mismo arnés con `--mode crashes --only-cut before_db_commit`: terminación intencional,exit1; **Restore1/1 y rechazo del origen antiguo1/1 PASS**,0 omitidas,exit0. Incluye la corrección `mfa_rotation_completed_witness_missing`.

Total propio: **20 casos positivos** en varias ejecuciones y dos terminaciones intencionales; no una suite única ni veinte casos sobre una única DLL. Los18 primeros pertenecen a los pines anteriores. Entre ambos conjuntos cambiaron el gate del coordinador, la aserción del trabajador y la colección serializada de la clase DB; adaptador, SQL, criptografía y publicadores revisados permanecen idénticos. Por ello repetí el caso afectado, sin duplicar toda la regresión.

Logs propios y comprobaciones: `.local/f0603-review/` —`database-independent.private.log`, `aftercommit-independent.private.log`, `receipt-independent.private.log`, `beforecommit-final-independent.private.log`, `pins-and-proof.json`, `final-pins-and-proof.json`—. Contrasté TRX, marcador flushed, salida de taskkill del árbol propio, binlogs y ausencia de `postmaster.pid` en **cinco clústeres propios**, incluidos los dos destinos Restore. Los marcadores no se usan como PID de entrada para matar procesos.

Las20 fuentes/herramientas de `FUENTES.json` coinciden con sus archivos y las45 huellas SQL históricas coinciden con el manifiesto;0 discrepancias. Mis16 fuentes/pruebas de producto revisadas coinciden con el congelado. El runner se ejecuta desde la raíz y conserva su hash propio; no afirmo que esté dentro de ese congelado. Los pines de DLL se comprobaron antes/después de las pruebas y nuevamente al cerrar la revisión.

## Resultados del coordinador contrastados, no ejecutados por mí

Leí los recibos finales bajo `610b…/0f28…`: **360/360** de regresión pertinente,0 omitidas; **15 terminaciones de proceso con15 reaperturas correctas**, incluyendo antes/después de clave, anillo aditivo/final, commit, recibo y retirada del fence; **dos Restores** en clústeres distintos con origen invariable; **tres negativos** correctos. No se presenta esa regresión como la totalidad de RackClick.

Se preservan los intentos344/360 y355/360. El coordinador atribuye esos fallos al fixture largo y a dos clases sobre la misma DB en paralelo; revisé el acortamiento exclusivo del arnés y la colección de la clase nueva. No se relajaron aserciones históricas. El RED del gate de DB anterior se trata aparte como fallo real corregido, no como error de fixture.

## Límites y crédito

No ejecuté instalación, arranque/HTTPS/login de servicio instalado, token efectivo del servicio, reboot de Windows, apagón ni portabilidad DPAPI. Los procesos se reabren en Windows con confianza/cuenta de laboratorio; Restore conserva explícitamente la identidad nativa y material del mismo equipo. La custodia del sobre es un archivo cifrado privado fuera de la instancia, en este equipo: no demuestra custodia externa productiva. Flush/relectura más kill de proceso no certifican durabilidad ante pérdida eléctrica.

El `verified` interno acredita conciliación offline. No inició un servicio ni completó el `verified` operativo D2. No hay nueva ruta HTTP o CLI pública de rotación; instaladores45 y despliegue46 quedan fuera. El runtime del laboratorio sólo lee el testigo; no afirmo adaptación de roles de una instalación existente. No se repitió una auditoría completa de autorización por ámbitos, GUI o política45: no se modificaron en esta tanda.

D/E, VM, servicios/bases instalados, secretos/datos reales y resultados de Wascar permanecieron fuera de mis operaciones. Diagnósticos, sobres, contraseñas, dumps y binlogs siguen privados. Esta evidencia conserva únicamente fases, resultados, archivos y hashes.

Recomiendo cerrar **sólo F-06.03 técnico,5/8**, sin F-06.04, R-04, candidata integrada, QA o adopción. No edité ni recalculé ledger/métricas y no creo un porcentaje global nuevo; el coordinador concilia el crédito con el criterio vigente de `docs/PROGRESO-GLOBAL.md`.
