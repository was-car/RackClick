# Revisión independiente C2 · elegibilidad observada

25.10.2026, Windows/PowerShell, Node local 24.21.0. Revisor distinto del implementador, encargo acotado del coordinador. Se conservaron las instrucciones de `AGENTS.md`, `docs/BRIEFING-MAESTRO.md`, `docs/EQUIPO-Y-SKILLS.md` y las restricciones leídas en la revisión C2 anterior. Git comprobado antes de escribir; el árbol compartido contiene cambios ajenos. Este revisor escribió solamente este informe y `review-eligibility-negative.test.mjs`, sin editar producto, QA, MFA, backend, VM o trabajo de otros agentes.

**Dictamen: conforme para los bytes y el alcance examinados.** No se reprodujo un defecto nuevo de producto. Cinco negativos propios pasan; tres controles focales fallan contra la fuente pre-tanda como se esperaba. No se declara completa I-01.03 ni se concede crédito global o aceptación.

## Archivos y símbolos consultados

| Archivo | Foco |
|---|---|
| `development/frontend/src/OperationDialog.jsx` | `OperationDialog`, `queryContext`, `requireWrite`, `requireCurrent`, `firstDispatch`, `submit`, `queryPending`, `cancelPending`, `refreshRevision`, `writeBlocked`, `staleDraft`; JSX de explicación, recarga y envío deshabilitado. |
| `development/frontend/src/InventoryPanel.jsx` | `observedRevision`, `setObservedRevision`, callback `onObservedRevision`, `readAuthorityLost`, `canEdit`, props de `OperationDialog`, `refresh` y `refreshPending`. |
| `development/frontend/src/ClientChangeNotice.jsx` | `latest`, `tick`, `onObservedRevision(page.currentRevision)` y callback de pérdida de autoridad. Inspección de integración; sin ejecución del canal HTTP real. |
| `development/frontend/src/inventory-api.ts`, `api.ts`, `pending-journal.ts` | Imports reales `prepareCommand`, `mutationRemainsUnconfirmed`, `pendingRecord`; contrato de intención/recibo y propietario del journal, ya inspeccionados en revisión anterior. |
| `development/frontend/src/inventory-words.ts`, `inventory-operation-status-words.ts` | Imports reales utilizados por la fixture. Sin revisión visual/lingüística completa. |
| `development/frontend/tests/operation-dialog-context.test.mjs` | Lectura de las nuevas comprobaciones y del harness del implementador. Sus 17/17 comunicadas por el coordinador no se presentan como ejecución propia. |
| `.local/c2-eligibility-20261025T113806Z-454d2eb6/before/development/frontend/src/OperationDialog.jsx` e `InventoryPanel.jsx` | Comparación pre-tanda; controles nuevos ejecutados expresamente contra la primera de estas copias. |

## Comportamiento revisado

- Un borrador nuevo comprueba revisión y permiso antes de preview, tras preview, tras persistir el journal y antes del primer envío. Una revisión posterior observada no sustituye silenciosamente el snapshot cargado.
- `observedRevision` acumula el máximo recibido del canal y se combina con la revisión del snapshot y del cliente. Se inspeccionó que esas props llegan al diálogo; el montaje y la recepción de avisos en el navegador quedan para el coordinador.
- Una intención ya journalizada conserva requestId, cuerpo, actor y ETag originales. Si se detiene antes del primer envío, permanece incierta y puede consultar/cancelar o reintentar esos mismos bytes. No se genera una solicitud nueva ni se adapta automáticamente a una revisión posterior.
- `requireWrite` bloquea la escritura si se observa `writeAllowed=false` o `authorityLost=true`. Consulta y cancelación conservan sus propias guardas de contexto y la autorización real del servidor. Una denegación de estas vías conserva el journal.
- Después de enviar una operación, una pérdida posterior de elegibilidad por sí sola no oculta un recibo confirmado. Las guardas de identidad/contexto siguen aplicándose. La fixture verifica el recibo reconocido, la limpieza y el callback de commit en esa situación.
- JSX deshabilita envío/campos por permiso o borrador obsoleto y muestra una explicación cuando no existe un error más concreto. La recarga explícita sigue disponible para el borrador obsoleto con autoridad de escritura; una recarga inferior a la revisión conocida continúa bloqueada. Estas últimas comprobaciones son estáticas y de estado simulado, no una prueba DOM.

## Pruebas nuevas ejecutadas

Fixture independiente en `review-eligibility-negative.test.mjs`: extrae la función real antes de JSX, simula hooks, IndexedDB y adaptador HTTP con datos sintéticos y promesas controladas. No reutiliza el harness del implementador ni ejecuta los nueve casos de la tanda anterior. La eliminación simulada respeta el propietario original.

| Caso propio | Resultado final |
|---|---|
| Pérdida de revisión/permiso/autoridad después de dispatch no oculta el recibo ya confirmado. | PASS |
| Revisión nueva durante `journal.put` impide primer envío, conserva intención y permite replay byte a byte del original con ETag `"4"`. | PASS |
| Permiso perdido durante preview descarta su resultado; recuperar permiso exige otra preview antes de escribir. | PASS |
| GET 404 y cancelación 403 después de perder autoridad conservan exactamente el journal y no envían comando de inventario. | PASS |
| Refresh 6 frente a revisión conocida 9 conserva el bloqueo, sin journal nuevo ni envío; explicación/recarga/disabled presentes en JSX. | PASS |

Comando desde `C:\RackClick_SVR`:

```powershell
& .local/node-v24.21.0-win-x64/node.exe --test evidence/s1-20261025/c2-eligibility-codex/review-eligibility-negative.test.mjs
```

Resultado final: **5/5 PASS, 0 FAIL, 0 omitidas, exit 0, 140,3406 ms**.

Primera ejecución propia: 4 PASS/1 FAIL, exit 1, 142,5936 ms. Falló una regex del observador que exigía otra agrupación de las condiciones del botón de recarga; las aserciones de revisión y ausencia de envío ya pasaban. Se ajustó exclusivamente esa comprobación a la expresión real equivalente. No se atribuye este fallo al producto ni se borra de la relación de ejecuciones.

Control negativo nuevo contra la copia pre-tanda: variable `RACKCLICK_ELIGIBILITY_REVIEW_SOURCE` apuntando a `before/.../OperationDialog.jsx`, filtro `--test-name-pattern 'intent stopped|write loss|lower refresh'`; PowerShell propaga `$LASTEXITCODE` después de retirar la variable. Resultado: **0 PASS/3 FAIL esperados, 0 omitidas, exit 1, 163,8549 ms**. El original envía tras `put` pese a la revisión nueva, acepta preview pese al permiso perdido y carece del nuevo estado de bloqueo. Son ejecuciones realizadas en esta revisión; no logs históricos convertidos.

Node emitió `MODULE_TYPELESS_PACKAGE_JSON`; no impidió ejecutar los casos ni motivó cambios de dependencias.

## Identidad examinada

| Archivo | SHA256 |
|---|---|
| `development/frontend/src/OperationDialog.jsx` | `d6be606b7feed2af9f78c7b0f6fd4f38d52f0a14bc4b6df228a76deed3b52e2a` |
| `development/frontend/src/InventoryPanel.jsx` | `d907a92700d3259e0dabaacfe498d38a58ff8c1702ec36dff5af9039b2fd195e` |
| `review-eligibility-negative.test.mjs` | `9e988ea151c04ea790a6df8f899ccbae4db92d3265d3f7c1f37ceb1221e2e84f` |
| `before/.../OperationDialog.jsx` | `0179a1f3ff0b1d36579836f94752a87552c19808dc3572c210509ee18dd1418e` |

## Hallazgos, no ejecutado y límites

Sin hallazgos nuevos P1/P2/P3 reproducidos dentro del encargo. La conformidad se limita a los hashes anteriores y a los cinco casos descritos; la fuente no se considera congelada por este informe.

No ejecuté suites generales, los 17 casos completos del implementador, los nueve negativos anteriores, navegador/Edge, PostgreSQL, servidor HTTP, compilaciones, instalador, SQL, MFA, QA/VM ni reinicio. Los resultados de navegador que aporte el coordinador mantienen su atribución propia. No acredité IndexedDB ni notificaciones de permiso reales con estas fixtures.

La autoridad observada es la recibida por las props: `writeAllowed` deriva de `canEdit` (`inventory.edit`) y `authorityLost` del canal de lectura. Esto no verifica toda la matriz de capacidades específicas, por ejemplo `inventory.delete`, ni garantiza detección inmediata de revocaciones aún no observadas. El servidor sigue siendo responsable de autorización, revisión, idempotencia y persistencia.

Quedan fuera autenticación/reautenticación global, MFA, todas las vías heredadas y la matriz completa de cuenta/cliente/permisos/revisión requerida para I-01.03. Sin cambios de métrica: delta de crédito cero; la referencia previa de 3,57/100 es cierre del pendiente, no un porcentaje global del producto. Adopción final de Wascar pendiente.
