# Revisión independiente · API de copias de inventario

12.11.2026. Encargo backend acotado, distinto del implementador. Base `98ad43582dcf08b3227f16873175625048dc09bd`; worktree separado `C:\RackClick_SVR\.local\github-installable-20261112\worktree`. Se revisó el diff recibido y se ejecutaron tres sondas propias contra el snapshot Release fijado. Sin cambios de producto, fixtures del autor, dependencias, VM, commits/push, instalaciones o subagentes; no se recompiló.NET ni se usaron outputs compartidos.

## Dictamen

**Especificación y calidad: requiere corregir dos P2 de validación antes del cierre.** Se reproducen con PostgreSQL17.11 y HTTP/Kestrel reales: una previsualización acepta un booleano nulo que luego causa503, y una importación acepta una revisión que vuelve ilegible la lista de clientes para el contrato existente del adaptador. No se observó en estas sondas pérdida parcial de datos, modificación de seguridad o un P0/P1 de filtración/autorización.

Los controles principales de autoridad global, aislamiento, SQL parametrizado, transacción, replay y fence de cancelación están presentes por lectura. No se convierten en ejecución propia las11pruebas/Quality del implementador. El frontend ya revisado queda cerrado: sólo se consultó su adaptador público sin modificarlo para medir la compatibilidad de la respuesta nueva del backend.

## Hallazgos reproducibles

### B01 · P2 · `poe:null` supera la vista previa y produce un error de servicio al restaurar

Fuentes: `development/server/src/RackClick.Server/InventoryDataAdministrationArchive.cs:185` y `:187`; helper existente `InventoryJson.cs:79` (`Boolean`); inserción en `InventoryDataAdministration.cs:191` y `:209`; columna `development/server/database/002-inventory.sql:48`.

El esquema exige que la propiedad `poe` esté presente, pero `Boolean(port,"poe")` devuelve el fallback `false` cuando su valor es JSONnull. La previsualización, por tanto, la acepta. La inserción conserva el valor original del archivo, y `jsonb_populate_recordset` lo convierte en NULL para una columna booleana NOTNULL. No es un fallo transitorio de infraestructura.

Reproducción B01, laboratorio nuevo y rol runtime sin DDL:

1. Generar un archivo cerrado válido con un cliente, rack, equipo manual, grupo RJ45 y puerto; el único tipo incorrecto es `ports[0].poe=null`.
2. POST `/api/v1/admin/inventory-data/preview` con sesión, Origin, CSRF y actor correctos devuelve **200**.
3. POST `/restore`, con revisión vigente, clave propia, hash correcto y confirmación, devuelve **503 `service_unavailable`**.
4. Consultar por el mismo UUID devuelve **`notRecorded`**; la base conserva **0clientes**. La comparación de tablas de usuarios/sesiones/miembros/concesiones/factores no cambió.

Efecto: la persona confirma un archivo que la vista previa presentó como válido y recibe un fallo de servicio; la UI conserva una intención incierta que requiere conciliación/cancelación. La atomicidad evita datos parciales, pero el rechazo debería ser un error de archivo antes de cualquier inserción. Debe exigirse un booleano real sin reinterpretar null como false. No basta con traducir posteriormente la violación NOTNULL a otro error HTTP.

### B02 · P2 · Revisión importada fuera del rango seguro deja de poder leerse en la GUI existente

Fuentes: `InventoryDataAdministrationArchive.cs:32` y `:67` (`DataRevision`); `InventoryDataAdministration.cs:197`. Contrato consumidor existente: `development/frontend/src/api.ts:14` (`resource`) y `:141` (`RackClickApi.customers`), consultado sólo como dependencia de la respuesta backend.

`DataRevision` admite enteros positivos `long` hasta `long.MaxValue-1`. Una copia externa puede así introducir una revisión superior al rango entero seguro que exige el contrato JSON de la aplicación. La creación normal de clientes no produce ese valor; la nueva restauración sí lo permite directamente.

Reproducción B02, otra base nueva:

1. Archivo cerrado mínimo con un cliente y ocho colecciones vacías; `revision=9007199254740992` (`2^53`).
2. Preview devuelve **200**; restore devuelve **200/commit**.
3. GET `/api/v1/customers` devuelve **200** y la revisión importada.
4. La **respuesta HTTP real**, guardada en privado y consumida por `RackClickApi.customers` sin cambiar ese código, es rechazada con **`response_invalid`**, porque `Number.isSafeInteger` es falso. No se inventó un mock de esa respuesta.

Efecto: una importación confirmada deja la lista completa fuera del contrato de lectura de la GUI. El inventario ya está poblado y no puede corregirse repitiendo restore sobre vacío desde el panel. La revisión entrante debe acotarse al contrato numérico que los consumidores pueden leer y usar para continuar trabajando; añadir prueba de frontera. No se propone alterar el frontend aprobado para aceptar valores imprecisos.

## Tres sondas ejecutadas por el revisor

Script privado `C:\RackClick_SVR\.local\admin-data-20261112\review-backend\backend-probes.py`, ejecutado con `C:\Python312\python.exe -B` desde el worktree. Reutiliza `pg_support.Lab`, sobreescribe sólo en memoria `toolchain` a los binarios oficiales ya existentes de la raíz y `DEFAULT_DLL` al snapshot fijado.

| Sonda | Resultado |
| --- | --- |
| B01 · booleano nulo | **REPRODUCED:** preview200, restore503,0clientes, `notRecorded`, seguridad comparada intacta |
| B02 · revisión2^53 | **REPRODUCED:** preview200/restore200, lista200 y rechazo `response_invalid` del adaptador existente sobre esa respuesta |
| B03 · frontera de clientes | **PASS:** preview acepta500clientes, rechaza501 con422;0mutaciones de inventario |

Un solo clúster NUEVO PostgreSQL17.11 y tres bases nuevas, con propietarios/runtime distintos y claves aleatorias sólo en entorno/archivos privados. DACL restrictiva aplicada antes de credenciales. `MfaKeyStore__Enabled=false` exclusivamente en el laboratorio: no es una conclusión sobre MFA de producción. Se confirmó en SQL runtime NOSUPERUSER/NOCREATEDB/NOCREATEROLE, sin CREATE/TEMPORARY de base, sin CREATE de esquema ni INSERT/UPDATE/DELETE del catálogo físico. Servidores propios y clúster **detenidos al finalizar**, sin borrar ni reutilizar recursos ajenos.

Las comparaciones de seguridad de B01/B02 cubren valores de `app_user`, `app_session`, `user_group_member`, `permission_grant` y `app_mfa_factor` antes/después. No había factor criptográfico activo ni sentinel MFA propio; no se acredita recuperación/cifrado MFA por estas comparaciones.

Salidas nuevas privadas: `backend-probes.json`, `probe-execution.log`, `input-hashes.json`, `unsafe-revision-customer-list.json`, `unsafe-revision-adapter.log`. El resumen contiene estados/recuentos/tipos, sin claves, cookies, tokens, conexiones o contraseñas. DLL y nueve fuentes/pruebas **idénticas antes/después**. El proceso terminó exit0, lo cual indica que reprodujo los resultados esperados de auditoría; no significa que los dos fallos sean verdes del producto.

`git diff --check` sobre las cuatro integraciones modificadas: sin errores. No se ejecutó la batería del autor ni Quality.

## Contraste de controles y archivos/símbolos consultados

- **Autoridad/sesión/ámbitos:** `InventoryDataAdministration.cs` (`DataAuthority`, `DataHouseRevision`, `DataCustomers`, `ReadInventoryDataAdministration`, `PreviewInventoryData`, `ExecuteInventoryData`, `InventoryDataOperation`). Se exigen las dos capacidades globales; lectura/exportación para backup y creación/edición para preview/importación. `PostgresStore.Can` con cliente null no acepta concesiones por cliente/grupo de clientes. `RequireCurrentSession` reevalúa reloj/MFA después de esperar y conserva locks de sesión/usuario. Se repite autoridad antes de commit. Las escrituras administrativas de grupos usan el mismo bloqueo Systemhaus; se consultó `AdminGroupWrites`.
- **Pipeline:** `InventoryDataAdministrationEndpoints.cs` (`MapInventoryDataAdministration`, `Actor`, `IsLargeInventoryDataRequest`) y `Program.cs` (Origin, host, sesión, CSRF, límites, rate limiter, errores). Las mutaciones necesitan actor coincidente, CSRF y Origin; las dos rutas de archivo tienen cuerpo45MiB, las restantes16KiB y la excepción anterior de plantillas se conserva. Concurrencia de tareas de archivo limitada a2 por actor después del middleware de autenticación. Estas negativas HTTP no se repitieron por el revisor.
- **Archivo:** `InventoryDataAdministrationArchive.cs` (`DataKeys`, `DataRevision`, `DecodeInventoryData`, `ParseInventoryData`, `ValidateInventoryDataCustomer`, `InventoryDataProfile`, `LoadDemoInventoryData`); `InventoryJson.Object/Validate/Id/Properties/Boolean`, `Names`, `FreeText`. Archivo32MiB, base64 acotado antes de decodificar, JSON estricto/duplicados anidados, esquema/campos cerrados, UTC,500clientes/100000filas e IDs globales y referencias dentro del cliente. Preview añade conversión real a jsonb y comprobación del catálogo. B01/B02 son las diferencias de validación reproducidas; B03 contrasta la frontera500/501.
- **Modelos/montajes/cables:** `InventoryHardwareMounting` (`CreateHardware`, `UpdateHardware`), `InventoryFamilyLMounting` (`CreateFamilyHardware`), `InventoryDevices` (`Capacity`, `AddGroup`, `UpdatePorts`), `InventoryConnections` (`Pair`, `PowerSystem`, `ValidateExistingPower`), `InventoryRules.RequireConnectorPair/RequireCapacity` y `FamilyLRules.PowerPair/Feature/IsRoom`. Se contrastaron los contratos reales de bandeja/desktop, sharedU, vertical0U y sala, metadatos de perfil/grupo/puerto, capacidad, pertenencia y ocupación. Se conserva la política histórica de conectores manuales y no se aplica el bloqueo de creación a cables ya documentados en puertos faulty/disabled. No se exige que estados dinámicos legítimos coincidan con valores iniciales de catálogo. No se ejecutó un ensayo físico independiente adicional.
- **Consistencia y atomicidad:** `InventoryStore.Snapshot/ReadAuthorizedSnapshot/Execute`; `ExecuteInventoryData` bloquea Systemhaus y clientes antes del snapshot; el restore usa inserción parametrizada explícita de nueve entidades, padres antes de hijos y extremos al final, en la misma transacción que auditoría/recibo. Mapeo SQL de tablas/columnas exclusivamente interno. Se confirma después del commit; B01 verificó rollback real. Importación sólo sobre vacío bajo lock y replay antes de revisar el destino poblado/revisión obsoleta. Las pruebas de carreras/rollback de auditoría del autor se leyeron, no se ejecutaron nuevamente.
- **Replay/cancelación/filtración:** `InventoryDataAdministrationCancellation.cs` (`DataDigest`, `StoredDataFence`, `CancelInventoryData`), `PostgresStore.LockOperation/RejectReportOperation`, `OperationCancellation.EnsureNotCanceled`, `InventoryJsonExport` (`StoredInventoryJsonExport`, rutas propias). UUID ligado a actor/Systemhaus y digest de acción/revisión/archivo; advisory compartido con cancelación; fence terminal en `operation` sin cliente ficticio. Cancelar devuelve el commit existente y no lo deshace. `kind:inventoryData` queda rechazado por recuperación genérica; decodificadores de otras rutas validan su kind. Recibos y copias sólo con autoridad actual propia. Auditoría de esta función sólo contiene metadatos, no archivo/credenciales.
- **Seguridad excluida del archivo:** `InsertInventoryData` no mapea cuentas, grupos de seguridad, sesiones, factores/códigos MFA, preferencias o plantillas. No hay DDL nuevo. `RackClick.Server.csproj` sólo añade los50 JSON/manifest embebidos, sin dependencias/versiones nuevas. `LoadDemoInventoryData` verifica pin del manifest, hashes/longitudes individuales y recuentos. No se volvió a cargar Demo50 en estas tres sondas.

Pruebas del autor leídas: los11 métodos de `InventoryDataAdministrationTests`, con fixtures HTTP/MFA, round-trip de nueve colecciones, seguridad sentinel, negativos y concurrencia; `PhysicalMediaRulesTests`. Documentos leídos: contrato del lote, `RESULTADOS-BACKEND`, briefing/AGENTS/contexto de la revisión previa y manifiestos. Skills de reproducción/verificación ya aplicados a la revisión; no se implementó un arreglo propio que luego aprobar.

## Evidencia atribuida, identidad y límites

El informe final del implementador declara `regression02`:868PASS/107SKIP/0FAIL de975casos, con8casos `MfaPortableDatabaseRestoreTests` excluidos por filtro. Se registra como evidencia suya y se distinguen skips/exclusiones de aprobados. Este revisor no ejecutó esa suite ni las11nuevas. El caso histórico PhysicalMedia45→48 se comprobó por `git show HEAD`: HEAD ya tenía `SchemaMigrations.LatestVersion=48` y el test esperaba45; el diff cambia únicamente esa aserción a48. No es una migración ni un fallo introducido de esquema.

**SHA256 DLL ensayada:** `a80ac3819f626a1ddd4b1c23b357a18da5454510cc38524887b4eda9ce452bb0`.

**SHA256 del diff recibido:** `322be1ce094f5919bb27ae6e1d71b5bf79b43ca0e02abce36b311edf5d389a6f`.

**SHA256 del conjunto de nueve archivos producto/pruebas revisado:** `1e013276c0889a1d489a9abd671ffcd96995fa3e1f64030f4c27858cd0252563`.

Método: SHA256 UTF-8 de las líneas `ruta_relativa + TAB + hash_bytes + LF` en el orden de `review-backend/input-hashes.json`. Incluye cuatro archivos nuevos de servidor, PostgresStore/Program/csproj, test nuevo y aserción PhysicalMedia. No incluye binlogs, secretos o archivos concurrentes ajenos. Cambios posteriores necesitan nuevo contraste/hash; este informe corresponde exactamente al snapshot indicado.

Límites: no prueba propia de todos los32MiB/100000filas, chunked, matrices físicas completas, pérdidas de red/locks/carreras, permiso revocado, recuperación genérica negativa, GUI, Windows20, backup/restore SQL o Windows, MFA criptográfico, VM/reinicio ni QA/adopción de Wascar. No se exige Restore48 como condición de este lote de inventario. Las capacidades restantes se valoran por lectura y evidencia atribuida, no por ejecuciones inventadas.

No se modifica progreso:26,63/100 del cierre restante como referencia, sin porcentaje global nuevo. Próximo paso: corregir B01/B02 en producto, conservar estos rojos y repetir únicamente sus focos más la regresión pertinente que determine el coordinador.
