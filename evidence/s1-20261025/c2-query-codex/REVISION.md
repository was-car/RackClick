# Revisión independiente de consulta de operación pendiente · 25.10.2026

Dictamen acotado: **conforme en fuente corregida** para la nueva consulta GET y sus fronteras de contexto. Un **P2 reproducido y corregido por el implementador** antes de este dictamen. Ocho pruebas propias finales PASS; el fixture original conserva el fallo. Esta revisión no cierra I-01.03 completo, invalidaciones generales ni integración de candidata. No concede puntos ni porcentaje global.

Revisor: agente `c2_query_review`, distinto del implementador coordinador. Explorador `dialog_async_read` apoyó sólo la lectura de ciclo de diálogo/llamantes; no editó ni ejecutó pruebas. El revisor sólo escribió este informe, su prueba propia y el fixture en esta carpeta. Estado Git compartido inspeccionado antes de escribir; cambios ajenos conservados. Sin instalaciones, producto modificado por el revisor, QA, VM, navegador, SQL, servicios, bases o paquetes.

## Hallazgo y corrección

**H1 · P2 · cerrado en fuente revisada.** En el primer `queryPending`, después de validar GET se esperaba `pendingJournal.remove` y `onPendingChange`, pero las guardas sólo miraban montaje. Cambiar actor durante esas esperas sin desmontar permitía aplicar `onCommit` del contexto previo y ejecutar `onClose`. `ServerApp` usa clave de cliente para `InventoryPanel`; `reload` puede actualizar identidad conservando cliente. El patrón también existe en vías anteriores `submit`/`cancelPending`, que quedan fuera de este cambio.

Reproducción propia sin navegador: extracción literal de la función desde `OperationDialog.jsx`, dependencias controladas y promesa de `journal.remove` retenida. El GET confirma bajo actor A; se cambia `api.actorId` a B antes de resolver el journal. La versión original invoca `committed:B` y `closed`; el negativo exige ausencia de esos efectos y falla. No demuestra una escritura cruzada ni corrupción de PostgreSQL: la consulta no escribe y el journal se elimina por actor/ID original después de recibo terminal válido.

El implementador añadió `queryContext` vivo con API, actor de sesión y cliente; `current()` verifica esos valores, `api.actorId`, aborto y montaje antes del GET y después de cada `await` antes de callbacks o efectos finales. El mismo negativo pasa sobre la fuente final. Se añadieron focos de cambio de cliente/actor/API durante `onPendingChange`, cliente/aborto durante `onCommit`, cliente durante `onRefresh` y desmontaje. El fixture anterior, hash `80823594…`, se conserva exacto; el negativo sigue fallando sobre él.

No se encontraron otros defectos concretos dentro de este alcance. Conformidades verificadas por lectura y pruebas indicadas:

- `readPendingCommand` usa GET sin cuerpo/cabeceras de mutación y conserva la solicitud original. `RackClickApi.request` mantiene credenciales mismo origen y `no-store`. Comprueba actor y aborto antes del envío y tras leer el cuerpo.
- Correlaciona cliente/solicitud exterior y recibo; reutiliza `confirmedCommand` y validación estructural. Rechaza conjuntos duplicados, fuente inversa ajena y ámbito estructural distinto del esperado.
- `notRecorded` requiere `operation:null`, conserva incertidumbre y vuelve antes de `setCompleted`/eliminación del journal; reintento y cancelación siguen disponibles por lectura del diálogo. La prueba propia verifica solicitud exacta/inmutable y ausencia de mutación; no ejecuta IndexedDB real.
- `cancelled` requiere su `operationId` UUID exterior y `operation:null`; se acepta la revisión histórica del recibo de cancelación. Para `committed`, la revisión exterior debe ser segura y mayor o igual a la del recibo. Coincide con `InventoryStore.Operation` y `OperationCancellation.Read/Cancel` consultados.
- Sólo un recibo terminal validado alcanza la eliminación del journal en la vía nueva. La eliminación usa solicitud/actor originales. Un borrado ya iniciado puede terminar después de desmontaje/cambio de contexto; el recibo ya es terminal y los callbacks posteriores están protegidos.
- Textos EN/DE/ES se renderizan como texto React, sin inserción HTML. No se añaden SQL ni cambios del servidor.

## Pruebas ejecutadas realmente

Windows local `Microsoft Windows NT 10.0.26300.0`, PowerShell, Node local `.local/node-v24.21.0-win-x64/node.exe`, TypeScript nativo. Fixtures sintéticos en memoria; sin dependencias instaladas.

Comando final desde `C:\RackClick_SVR`:

```powershell
& .local/node-v24.21.0-win-x64/node.exe --test evidence/s1-20261025/c2-query-codex/review-negatives.mjs
```

Resultado final: **exit 0; 8 tests, 8 pass, 0 fail, 0 skipped**, 141,9073 ms. Se ejecutaron seis focos de adaptador y dos focos de función de diálogo extraída literalmente. La comprobación del diálogo inyecta callbacks/ref controlados; no sustituye un montaje React/IndexedDB/Edge real.

Los seis focos iniciales pasaron antes de ampliar el arnés. La primera ampliación reprodujo H1 con **6 PASS/1 FAIL, exit 1**. No se contabiliza como una corrida satisfactoria. Tras la corrección se ejecutó de nuevo el mismo negativo contra la copia original:

```powershell
$env:RACKCLICK_REVIEW_ORIGINAL='1'
& .local/node-v24.21.0-win-x64/node.exe --test --test-name-pattern='dialog must not invoke' evidence/s1-20261025/c2-query-codex/review-negatives.mjs
Remove-Item Env:RACKCLICK_REVIEW_ORIGINAL
```

Resultado original preservado: **0 PASS/1 FAIL esperado**, `actual=['committed:12000000-0000-4000-8000-000000000099','closed']`, `expected=[]`. En la llamada agrupada el segundo comando final PASS determina el exit exterior; el fallo original se identifica por su resultado propio. Node emite aviso `MODULE_TYPELESS_PACKAGE_JSON`; no hubo instalación ni cambio de package.json para suprimirlo.

**No ejecutado por el revisor:** suites existentes `inventory-operation-status.test.mjs` o regresiones completas; `browser-inventory-operation-status.mjs`; arnés Python/Edge/PostgreSQL; compilación .NET/frontend; QA manual/VM; montaje React y journal IndexedDB real; pruebas de permisos/revocación contra DB. El coordinador comunicó sus resultados separados y el fallo inicial de observador; no se atribuyen como ejecuciones nuevas de este revisor. Un build/Edge anterior a la corrección de H1 no verifica sus bytes finales.

## Archivos y símbolos consultados

- `AGENTS.md`, `docs/BRIEFING-MAESTRO.md`, `docs/EQUIPO-Y-SKILLS.md`, `.codex/agents/qa.toml`; cabeceras/extractos vigentes de `CONTINUIDAD-CODEX`, `PROGRESO-GLOBAL`, `S1-FUNDAMENTO`, `INICIO-IMPLEMENTACION-S1`, `CONTRATO-SERVIDOR-v0.1`, `MAPA-RC9-R3`, `ACEPTACION` y `development/server/README.md`. Los registros históricos no se consideran ejecuciones de hoy.
- `development/frontend/src/inventory-api.ts`: `confirmedCommand`, `executeCommand`, `readPendingCommand`, `validateCompensationResult`, `validateCatalogResult`, `prepareCommand`, `rememberCompensation`, `cancelPendingCommand`. Diff contra `.local/c2-query-20261025T104429Z-7c240ca826/before/development/frontend/src/inventory-api.ts`.
- `development/frontend/src/OperationDialog.jsx`: `queryPending`, `queryContext`, `current`, efecto de montaje/desmontaje, `inventoryError`, render de botones/avisos; lectura comparativa de `submit`, `cancelPending`, `authenticate`. Diff contra copia `before` y contra fixture anterior a H1.
- `development/frontend/src/inventory-operation-status-words.ts`: `operationStatusWords`; `inventory-compensation.ts`: `compensationUuid`, `compensationIdsEqual`, `candidateMatches` y expectativas de candidato.
- `development/frontend/src/api.ts`: `RackClickApi.request`, `me`, `sendMutation`, `ApiError`, `mutationRemainsUnconfirmed`; `pending-journal.ts`: `validPendingRecord`, `pendingRecord`, `pendingJournal.remove/list`.
- `development/frontend/src/InventoryPanel.jsx`: `refreshPending`, `committed`, render de `OperationDialog`; `ServerApp.jsx`: `reload`, `forget`, `logout`, clave de `InventoryPanel`.
- `development/server/src/RackClick.Server/InventoryStore.cs`: `Operation`, `RequireRead`, `Revision`; `OperationCancellation.cs`: `Find`, `Read`, `Cancel`; `Program.cs`: rutas GET de operación y POST de cancelación.
- Pruebas del implementador leídas: `development/frontend/tests/inventory-operation-status.test.mjs`, `browser-inventory-operation-status.mjs` final con observación CDP, y `development/server/tests/test_inventory_operation_status_gui.py`.

## SHA256 de los bytes revisados

| Archivo | SHA256 |
|---|---|
| `src/inventory-api.ts` | `18a95180d450680bace1ec2aa92828001ae38ce2c4599e6d3b419ed5c2ca2c46` |
| `src/OperationDialog.jsx` final | `08ec90fc096d3744168921449d8eabe62f44b24829f78f73ff730ef0b30f796f` |
| `src/inventory-operation-status-words.ts` | `ae8195882a6db8c6bc49a09f54b33f49dd347712b87fa28878b12fd5e0cf914a` |
| `tests/inventory-operation-status.test.mjs` leído | `1041cfb964b7ad70134651e946be0c8bdbb0f3fdb6980fd8f462b5bf51443f06` |
| `tests/browser-inventory-operation-status.mjs` final leído | `f3170ae4bf3b74da75913be32f03759d3abddf643bf99f399bcd23151bed1248` |
| `before/src/inventory-api.ts` | `9e3fc48cc64c602a6e240221ed32c305407e6f54866f6c62fe6fb87ad88ce06d` |
| `before/src/OperationDialog.jsx` | `d7a162ee6ea249b04ecd067c26a5fc02afee22f3992d7cd6576c09bad2bfd05d` |
| `OperationDialog-before-query-fix.fixture.txt` | `808235940d5f418400744da8df7b29fc2d4f604be56aaa15d49388ab9f563dfe` |
| `review-negatives.mjs` final | `c22e3cbb8abe7076c752b697a915e2e48b7e2b3e789628883674c299e1522360` |

Rutas `src/` y `tests/` relativas a `development/frontend/`; rutas `before/` corresponden a la copia privada indicada por el coordinador. Las dos últimas rutas son de esta carpeta. No se certifica un manifiesto previo como vigente ni un binario a partir de hashes de fuente.

## Límites y continuidad

El cierre sólo cubre la consulta nueva revisada y el P2 anterior. `submit`/`cancelPending` heredados, invalidaciones generales, candidata API+GUI/MFA coordinada, integración Windows y QA/adopción final siguen fuera. El criterio vigente de `PROGRESO-GLOBAL.md` retiró el 78 % histórico: esta revisión no calcula porcentaje de entrega completa ni modifica la métrica del pendiente. No cierra I-01.03 completo ni acredita disponibilidad QA.
