# Dictamen independiente F-06.02 · paso 20

09.11.2026. Revisor distinto del implementador y del coordinador de las pruebas PostgreSQL. Encargo acotado a retención/inventario MFA; D/E conservados sin operaciones. Sólo se escribe este dictamen y la salida privada de una ejecución pura. No se modifica producto, pruebas, documentación compartida, ledger ni trabajo ajeno.

## Dictamen y crédito

**Avance técnico de componentes comprobado; F-06.02 no puede marcarse `done`. Recomiendo `in_progress` con +0 puntos.** El estado del checkpoint consultado todavía es `pending`; este revisor no lo modifica.

Criterio literal de `docs/PLAN-CIERRE-RACKCLICK.json`, peso congelado **5/8**:

> Retirar una versión sólo si ningún factor ni backup retenido la necesita; incluir inventario de versiones en backup/sobre.

La guarda y el formato satisfacen partes verificables de ese criterio, pero no existe una acción operativa de retirada que los aplique. El operador nativo tampoco publica/transporta/consume el inventario lateral. No basta que una prueba construya estos metadatos y los pase a la guarda para acreditar el resultado completo. No se rebaja ni reescribe el criterio para conceder crédito.

`CandidateUnreferenced` describe exclusivamente los argumentos suministrados. No autentica la DB, un catálogo declarado completo, la vigencia del censo, su equivalencia con el dump ni los bytes de claves del anillo vivo. **No autoriza borrar ni publicar un anillo reducido.** El componente no realiza ninguna de esas acciones.

F-06.01 permanece como especificación cerrada; esta revisión no acredita F-06.03/.04 ni hitos operativos del resultado F-06. El índice documental consultado permanece **3319/168 = 19,755952…/100**, redondeado **19,76/100 del cierre restante**. No es un porcentaje global de entrega ni de aceptación; no se calcula otro porcentaje.

## Hallazgos por gravedad

1. **Alta · falta integración de retirada y del inventario en la operación nativa.** `MfaKeyRetention.EvaluateCandidate` (`MfaKeyRetention.cs:203`) no tiene llamador de producto fuera de su propio componente; la búsqueda en `development/server/src` y `tools/windows` sólo encontró las dos clases nuevas. `Read-BackupManifest` (`tools/windows/RackClick.Backup.ps1:217`, condición de archivos en 230) mantiene el contrato histórico de dos archivos. El inventario lateral probado se escribe desde una fixture, fuera de esa carpeta; no existe publicador/consumidor nativo nuevo. Es un límite expresamente documentado y bloquea cerrar el criterio entero; no se observó borrado inseguro ejecutable introducido por este lote.
2. **Alta · autoridad y actualidad del conjunto de dependencias aún externas al componente.** `ReadAsync` cuenta todas las filas visibles de `public.app_mfa_factor`, pero el GUID proporcionado sólo etiqueta el resultado. `backupCatalogComplete=true` es una declaración del llamador. Los pines externos comprueban integridad contra sus referencias, sin establecer por sí solos autenticidad, completitud, identidad de la DB o snapshot conjunto DB/dump/anillo. Falta un coordinador autorizado que vincule estos objetos, mantenga el catálogo completo y cierre la carrera con nuevos factores, backups y operaciones pendientes antes de cualquier retirada. Los comentarios de código y el contrato reconocen correctamente este límite.
3. **Media · evidencia operativa incompleta.** La evidencia aportada utiliza un laboratorio quieto y factores con ciphertext opaco sintético; no demuestra recuperación de esos factores, snapshot concurrente con dump, custodia externa real, retirada de archivos, publicación recuperable, cortes o arranque con fence. Los 10 casos PG y los 115 de regresión aportan evidencia de componentes; no sustituyen esos recorridos.
4. **Baja · trazabilidad del runner fuera del freeze.** Las cuatro fuentes/pruebas C# nuevas coinciden byte a byte entre árbol y freeze. `tools/tests/run_mfa_key_retention_inventory.py` no existe en ese freeze; se revisó y obtuvo su SHA256 en el árbol compartido. Un intento de compararlo produjo `Could not find file`; no se interpreta como diferencia del código ni fallo de la suite. La ejecución pura posterior terminó con exit 0. El runner es arnés externo, no contenido de las DLL contrastadas.

No se detectó otro defecto de producto en la revisión acotada ni un escape de ámbito o secreto nuevo en estas dos clases. Esta afirmación no equivale a una auditoría completa de MFA/autenticación ni a aprobación para operar una retirada.

## Comprobaciones de lógica y seguridad

- `FactorInventory` valida instalación no vacía, versiones 1..1000000, cupo 64, entradas únicas, negativos y overflow; copia/ordena colecciones y las expone como lectura. Pending, active y disabled conservan su dependencia. Un censo vacío es explícito.
- `InspectEnvelope` clona el ciphertext acotado para ligar hash y bytes autenticados, reutiliza `MfaKeyRecoveryEnvelope.Open` y `MfaKeyRecoveryPayload.Deserialize` y devuelve sólo metadatos. El `using` dispone las copias de claves; `finally` pone a cero el plaintext. Se inspeccionaron las rutas de limpieza y error de `Deserialize`, `MfaKeyVersionMaterial.Dispose` y `MfaKeyRecoveryContent.Dispose`. No se promete borrado universal de memoria administrada ni de la contraseña string del llamador.
- `CreateBackupInventory` y `ValidateBackup` derivan `requiredVersions` como unión exacta de versiones con factores y activa del sobre; la activa sigue requerida con cero factores. Exigen cobertura de todas las requeridas por el sobre. `envelopeVersions` conserva el inventario completo de ese sobre.
- `ParseBackupInventory` exige pin SHA256 propio más pines de manifiesto/dump/sobre y ámbito esperado, copia bytes antes de comprobarlos, limita 64 KiB/profundidad, rechaza campos extra/duplicados/omitidos y tipos/rangos/orden/cupo inválidos. Los pines han de venir de un registro privado independiente, nunca del mismo archivo recalculado. La prueba de alteración coherente demuestra por qué sustituir también el pin destruye esa garantía.
- La corrección Unicode está presente: los accesos concretos `PropertyName`/`String` traducen `InvalidOperationException` a código cerrado sin adjuntar datos o `InnerException`. La ejecución independiente incluye los tres surrogates sin pareja y los dos controles de pares suplementarios válidos.
- `EvaluateCandidate` bloquea activa, desconocida, referencias de cualquier estado, backups requeridos, catálogo incompleto, duplicación de backup ID, ámbito ajeno y dependencia ausente. Exigir completitud explícita evita que una lista vacía se interprete automáticamente como catálogo completo. No dispone de IO, writer, publicación, borrado o mutación de factores.
- `MfaFactorKeyInventoryReader.ReadAsync` valida conexión/transacción coincidentes y abiertas, aislamiento RepeatableRead/Serializable y `SHOW transaction_read_only=on`. Usa SQL constante, tabla cualificada `public.app_mfa_factor`, agregados por versión/estado y cancelación; no selecciona identidad, ciphertext, contraseña o TOTP y no filtra por cliente visible. Rechaza estados desconocidos, cuenta inválida, overflow y versiones fuera de perfil. Es una pieza interna de mantenimiento; no expone endpoint ni concede capacidades. La autorización del futuro operador y el vínculo DB/instalación siguen pendientes. Login, sesiones, CSRF, revocación y política45 no se modifican ni se revalidan integralmente en esta revisión.

## Prueba ejecutada por este revisor

Windows/PowerShell, host .NET **10.0.12**, xUnit v3 **3.2.2**, binarios Release ya compilados. Sin MSBuild, build, restore, instalación o dependencias nuevas; no aplica binlog a una invocación directa de DLL.

```powershell
& C:/RackClick_SVR/.local/dotnet-10.0.401/dotnet.exe C:/RackClick_SVR/.local/f0602-1e624af6/freeze/development/server/tests/RackClick.Quality.Tests/bin/Release/net10.0/RackClick.Quality.Tests.dll -class RackClick.Quality.Tests.MfaKeyRetentionTests
```

Resultado fresco: **51 total, 0 errors, 0 failed, 0 skipped, 0 not run; exit 0; 5,258 s**. Salida privada completa: `.local/f0602-1e624af6/review/retention-direct-dll.log`. Se aplicó la skill `verification-before-completion`; no se invocaron agentes adicionales.

Antes de ejecutarlo se contrastaron las DLL con los SHA256 aportados por el coordinador y las cuatro fuentes/pruebas C# con su copia aislada. No se repitieron mutaciones o fases rojas: sólo se leyó su registro aportado, sin atribuirlas al revisor.

## Evidencia aportada, no ejecutada por este revisor

- `POSTGRES-CENSO-BACKUP.json`: 10/10, PostgreSQL17.11, tres DB nuevas/esquema45 y roles SELECT-only; invariancia de filas, dump custom de 303255 bytes, inventario lateral separado y rechazo nativo de archivo tercero; clúster propio detenido. Se inspeccionaron ambas clases de prueba y el runner que producen ese recorrido. No se abrieron logs privados, credenciales, binlogs ni la base.
- `REGRESION-COMPONENTES.json`: 115/115 y mismo SHA de servidor, SDK10.0.401/Release, sin PG. Es ejecución del coordinador, no una segunda suite propia.
- `IMPLEMENTACION-INVENTARIO.md`: 51 casos del implementador y registro de fases rojas, mutación detectada, compilación incremental antigua y corrección Unicode. Se distinguen de la ejecución independiente actual y no se suman como casos nuevos.

No ejecutados: PostgreSQL, HTTP/GUI, DPAPI, claves reales, restauración, operación de backup nativa, D/E, VM, servicios, cuentas, instalación, fence/journal/publicación/retirada, cortes, QA o adopción de Wascar. No build/restore ni lectura de rawlogs PG/binlogs/secretos. `git status --short` mostraba un árbol con numerosos cambios previos; no se limpió, incorporó ni sobrescribió ninguno.

## Integración necesaria para volver a evaluar el criterio

Debe existir un recorrido autorizado que publique y consuma el inventario lateral y el registro de confianza, catalogue todos los backups retenidos (incluidos históricos sin inventario como bloqueo), vincule instalación/DB/dump/sobre y obtenga un censo estable bajo exclusión/fence. La acción de retirada debe volver a validar las dependencias y el material, llamar la guarda y publicar el anillo de forma recuperable sin permitir escritores durante la decisión. Debe probarse que factores de todos los estados o cualquier backup retenido bloquean la retirada, y que incertidumbre, falta de inventario y cortes conservan material recuperable. Esa integración puede reutilizar el coordinador de F-06.03; atribuirla a un paso futuro no acredita hoy el texto de F-06.02.

## Archivos y símbolos consultados

Lectura completa: `AGENTS.md`, `docs/BRIEFING-MAESTRO.md`, `docs/CONTRATO-INVENTARIO-RETENCION-MFA-v1.md`, `docs/PASO-020-INVENTARIO-RETENCION-MFA.md`, `docs/PROTOCOLO-ROTACION-MFA-v1.md`, `RESULTADOS.md`, `MATRIZ-CRITERIO.md`, `IMPLEMENTACION-INVENTARIO.md`, `POSTGRES-CENSO-BACKUP.json`, `REGRESION-COMPONENTES.json` de esta evidencia; dos fuentes y dos clases de prueba nuevas y `tools/tests/run_mfa_key_retention_inventory.py`.

Símbolos principales: tipos de inventario y decisión de `MfaKeyRetention.cs`; `FactorInventory`, `InspectEnvelope`, `CreateBackupInventory`, `SerializeBackupInventory`, `ParseBackupInventory`, `EvaluateCandidate`, `ValidateBackup`, `ValidateVersions`, `String`, `PropertyName`; `MfaFactorKeyInventoryReader.ReadAsync`; todas las pruebas y helpers de `MfaKeyRetentionTests` y `MfaFactorKeyInventoryReaderTests`; runner `main`, `environment`, `native_check`.

Lectura parcial/acotada: limpieza y `Deserialize` de `MfaKeyRecoveryPayload.cs`; condiciones de `Read-BackupManifest` en `RackClick.Backup.ps1`; checkpoint/peso de `PLAN-CIERRE-RACKCLICK.json`; encabezado vigente de `PROGRESO-GLOBAL.md` y encabezados de continuidad, inicioS1, fundamento, contrato general, mapaRC9/R3, aceptación, equipo/skills, hoja de ruta y README servidor. Se reutilizó la investigación previa del contrato; no hubo nueva búsqueda externa ni dependencia adoptada. Las afirmaciones de este dictamen proceden de código, evidencia y prueba acotada.

## Huellas SHA256 contrastadas

```text
86a53993072728f09225a5f874c97889b32a7a8b7d019ae6769287c383c6696d  MfaKeyRetention.cs (árbol=freeze)
ba1d934838914ba12f21f492ee15783402fda48af92d0c35344ae87064c5f05a  MfaFactorKeyInventoryReader.cs (árbol=freeze)
7ca1b223e29528758da149fa41df65152263f420e277860c7d71b92998ad13ec  MfaKeyRetentionTests.cs (árbol=freeze)
a7f680e358e7b4f8fc014624d1fc41834d296c4084c358bf6fa00b71a029e1c2  MfaFactorKeyInventoryReaderTests.cs (árbol=freeze)
2d56bce5d4775fa0eac3a6faead34687db331159db032af07884e61a3ee62091  run_mfa_key_retention_inventory.py (sólo árbol)
868ca47615fdf952244edf61361fc5dc1a5759ce91abd51a0975cc341e86ed5a  RackClick.Server.dll
dd34eb1b096351879f57c51d7b696a93342b85f9f25adfa3f203420b2ad0e3d0  RackClick.Quality.Tests.dll
```

Las huellas ligan esta revisión a los objetos leídos/ejecutados. No constituyen aceptación del despliegue ni autorización para retirar material.
