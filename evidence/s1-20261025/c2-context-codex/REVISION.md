# Revisión independiente C2 · contexto del diálogo

25.10.2026. Revisor distinto del implementador, perfil `rackclick_qa`; encargo del coordinador limitado a `OperationDialog`, contexto de `InventoryPanel`, callbacks y journal. Windows, PowerShell, Node local 24.21.0; sin instalación, compilación, commits ni modificación de producto por este revisor. Árbol Git compartido con numerosos cambios previos constatados antes de escribir; no se revirtieron ni sobrescribieron.

**Dictamen final: conforme para el alcance revisado después de corregir R-C2-CTX-01 (P2).** Reproduje un rechazo escapado desde el `catch` de `submit`, comunicado y corregido por el coordinador. La fuente final pasa 9/9 negativos propios y 11/11 casos del implementador repetidos independientemente. Esto no cierra I-01.03 ni concede crédito global, integración, MFA o aceptación de Wascar.

## Archivos y símbolos consultados

| Archivo | Símbolos / comprobación |
|---|---|
| `AGENTS.md`, `docs/BRIEFING-MAESTRO.md` | Instrucciones, continuidad S1 y distinción entre evidencia histórica y ejecución nueva. |
| `docs/CONTINUIDAD-CODEX.md`, `docs/INICIO-IMPLEMENTACION-S1.md`, `docs/S1-FUNDAMENTO.md` | Estado/documentación de fundamento y límites; consultadas sus secciones iniciales pertinentes. |
| `docs/CONTRATO-SERVIDOR-v0.1.md`, `docs/MAPA-RC9-R3.md`, `docs/ACEPTACION.md`, `development/server/README.md` | Contexto de contrato, referencia RC9 y aceptación; no se auditaron sus capacidades completas en esta tarea. |
| `docs/EQUIPO-Y-SKILLS.md`, `.codex/agents/qa.toml` | Independencia, propiedad separada y límites del perfil detectado. Sin skills adicionales aplicables a este foco. |
| `docs/C2-CONSULTA-PENDIENTE-25-10-2026.md`, `docs/PLAN-CIERRE-RACKCLICK.md`, `docs/PROGRESO-GLOBAL.md` | I-01.03 parcial; 78 % retirado y 3,57/100 correspondiente al cierre del pendiente, no porcentaje global del producto. |
| `development/frontend/src/OperationDialog.jsx` | `OperationDialog`, `origin`, `queryContext`, `inContext`, `requireCurrent`, `submit`, `queryPending`, `cancelPending`, `refreshRevision`; `authenticate` sólo para delimitar alcance no cerrado. |
| `development/frontend/src/ServerApp.jsx` | `key={session.user.id+':'+active.id}` de `InventoryPanel`. Comparación con copia pre-tanda: cambio funcional acotado a esa clave. |
| `development/frontend/src/InventoryPanel.jsx` | `refreshPending`, `refresh`, `mounted`, `committed`, efectos y montaje de `OperationDialog`; `instant` identificado como vía heredada fuera del foco. |
| `development/frontend/src/inventory-api.ts` | `prepareCommand`, `executeCommand`, `readPendingCommand`, `cancelPendingCommand`, validación de recibos. Comparación pre-tanda sin cambio en este archivo. |
| `development/frontend/src/api.ts` | `RackClickApi.actorId`, `sendMutation`, `mutationRemainsUnconfirmed`. |
| `development/frontend/src/pending-journal.ts` | `pendingRecord`, `validPendingRecord`, `put`, `remove`; la eliminación real condiciona por propietario original. |
| `development/frontend/src/inventory-words.ts`, `development/frontend/src/inventory-operation-status-words.ts` | Imports reales de textos utilizados por las fixtures. No revisión visual/lingüística completa. |
| `development/frontend/tests/operation-dialog-context.test.mjs` | Prueba del implementador: extracción del componente real antes de JSX, hooks simulados y promesas controladas. |
| `.local/c2-context-20261025T111054Z-21ee5c0c/before/development/frontend/src/{OperationDialog.jsx,ServerApp.jsx,inventory-api.ts}` | Comparación contra estado pre-tanda. Es copia del coordinador, no una ejecución histórica adoptada. |

## Hallazgo R-C2-CTX-01 · P2 · corregido

En la primera fuente recibida, `submit.catch` esperaba `pendingJournal.remove()` y a continuación llamaba a `requireCurrent()`. Si `api.actorId` cambiaba durante esa espera mientras el diálogo seguía montado, la guarda lanzaba `{status:409,code:'actor_changed'}` **desde dentro del propio `catch`**. El rechazo del manejador asíncrono escapaba. Asimismo, un rechazo del `onPendingChange()` usado en la limpieza escapaba del mismo bloque.

Reproducción aislada: borrador nuevo → journal → primera notificación correcta → respuesta definitiva 422 del adaptador → suspender eliminación del journal → cambiar sólo `api.actorId`, sin render ni desmontaje → liberar eliminación → `submit()` rechaza. Segundo caso: 422 seguido de `onPendingChange` rechazado con `draft_storage_unavailable`. Son dos fronteras del mismo defecto. No se demostró escritura cruzada, fuga de datos ni corrupción SQL; el impacto acreditado es la falta de contención del error del evento y la recuperación del diálogo.

El coordinador sustituyó la guarda lanzadora de esa frontera por `inContext()` con retorno y añadió contención de la notificación de limpieza. El negativo exige que el manejador se resuelva, que no invoque callbacks tardíos del siguiente contexto y que conserve el error pertinente. Ambos fallan contra la copia exacta anterior y pasan contra la final. El código del producto fue cambiado por el coordinador, no por este revisor.

Fuente exacta anterior preservada por indicación expresa del coordinador: `OperationDialog.before-R-C2-CTX-01.jsx`, SHA256 `f6cac753b17b07f54a89c2195287efab928ad2f1b4e4dcb6beab186d4df90c9e`.

## Ejecuciones nuevas del revisor

No se han convertido logs anteriores en ejecuciones propias. Las siguientes se ejecutaron durante esta revisión:

| Ejecución | Resultado real |
|---|---|
| `node --test development/frontend/tests/operation-dialog-context.test.mjs`, primera fuente recibida | 11/11 PASS, 0 omitidas, exit 0, 153,3044 ms. |
| Prueba propia inicial, 8 casos | 7 PASS / 1 FAIL, exit 1, 120,5312 ms. Inicialmente incluía cambio de props y comprobación sintética de propietario; se afinó el caso para aislar sólo la mutación de `api.actorId`. No se contabiliza como corrida final. |
| Prueba propia de 8 casos, reproducción afinada | 7 PASS / 1 FAIL, exit 1, 128,687 ms: rechazo `{status:409,code:'actor_changed'}`. |
| Foco `known failure cleanup` contra fuente pre-tanda `.local/.../before` | 0 PASS / 1 FAIL: el original anterior a la tanda ejecutaba una segunda notificación `pending` después del cambio de actor. Primera llamada PowerShell ocultó exit de Node por su `finally` (shell exit 0 con FAIL visible); repetida propagando `$LASTEXITCODE`: exit 1, 113,3249 ms. No se declara PASS de esa llamada. |
| Focos `known failure cleanup\|failed pending-list` contra copia exacta F6 preservada | 0 PASS / 2 FAIL, 0 omitidas, exit 1, 128,4741 ms: `actor_changed` y `draft_storage_unavailable` escapados. |
| Prueba propia final, 9 casos | **9/9 PASS**, 0 omitidas, exit 0, 125,5898 ms. |
| Prueba del implementador repetida contra fuente final | **11/11 PASS**, 0 omitidas, exit 0, 137,5286 ms. |

Prueba propia: `review-context-negative.test.mjs`. Extrae la función real antes de JSX y utiliza fixtures sintéticas locales, hooks simulados separados por clase, eventos y promesas controladas. No importa ni reutiliza el harness del implementador. La operación y `pendingRecord` se construyen con sus funciones reales; ejecución HTTP, IndexedDB y callbacks se sustituyen por fixtures. El journal simulado conserva la condición de propietario de `remove`; no acredita IndexedDB real.

Los 9 casos finales cubren: preview tardío ante cliente/actor/API/desmontaje; refresh A→B→A sin adoptar snapshot ni formulario nuevos; cambio de API durante la notificación inicial del journal sin dispatch; ausencia de cierre al cambiar contexto dentro de un commit ya iniciado; ausencia de cierre/setState tras desmontaje dentro del refresh de cancelación; invalidación permanente al observar `api.actorId` distinto sin render; las dos variantes de R-C2-CTX-01; y separación estática de la clave por actor y cliente. La prueba de clave evalúa la expresión real: no monta React ni sustituye la comprobación de navegador.

Comandos de repetición desde `C:\RackClick_SVR`:

```powershell
& .local/node-v24.21.0-win-x64/node.exe --test evidence/s1-20261025/c2-context-codex/review-context-negative.test.mjs
& .local/node-v24.21.0-win-x64/node.exe --test development/frontend/tests/operation-dialog-context.test.mjs
```

Control negativo exacto (espera exit 1):

```powershell
$env:RACKCLICK_REVIEW_SOURCE = 'C:\RackClick_SVR\evidence\s1-20261025\c2-context-codex\OperationDialog.before-R-C2-CTX-01.jsx'
$c2ReviewExit = 99
try {
 & .local/node-v24.21.0-win-x64/node.exe --test --test-name-pattern 'known failure cleanup|failed pending-list' evidence/s1-20261025/c2-context-codex/review-context-negative.test.mjs
 $c2ReviewExit = $LASTEXITCODE
} finally {
 Remove-Item Env:\RACKCLICK_REVIEW_SOURCE
}
exit $c2ReviewExit
```

Node mostró el aviso `MODULE_TYPELESS_PACKAGE_JSON`; no se modificaron paquetes para eliminarlo. No impidió ejecutar los casos.

## Identidad final examinada

| Archivo | SHA256 |
|---|---|
| `development/frontend/src/OperationDialog.jsx` | `0179a1f3ff0b1d36579836f94752a87552c19808dc3572c210509ee18dd1418e` |
| `development/frontend/src/ServerApp.jsx` | `bf17b36a20a27d48c1232b1a562d01f8382e38595da2c58cb9bc6579afa67650` |
| `review-context-negative.test.mjs` | `ddeeaead514a2e388e9a357679f26a9f3399bd383ba316b88f8641cde3493ee5` |

## Límites y trabajo no ejecutado

- No ejecuté navegador/Edge, PostgreSQL, servidor HTTP, build, instalador, SQL, Windows limpio, VM ni reinicio. Esos resultados corresponden al coordinador si los aporta; no se acreditan aquí como propios.
- El desmontaje se comprueba invocando cleanup del hook simulado. La clave actor+cliente se inspecciona/evalúa estáticamente; su comportamiento DOM real queda para el ensayo de navegador del coordinador.
- Un callback `onCommit` o `onRefresh` ya iniciado antes del cambio de contexto puede seguir ejecutándose internamente. Las pruebas verifican que el diálogo no encadene el cierre ni otros callbacks posteriores; no afirman cancelación universal de trabajo ya iniciado.
- Las guardas observan cambios de props/API/actor; no prueban detección global de una transición que ningún render ni guarda haya observado. API mutable sin actor válido bloquea la operación, pero no equivale a revocar una sesión del servidor.
- No se audita ni modifica autenticación/reautenticación global, MFA, recuperación de cuenta, todas las vías heredadas (`instant`, otros diálogos) ni la matriz completa de revisión/permiso/cuenta/cliente. I-01.03 continúa parcial.
- No se modifican QA, sus resultados personales, W-02, paquetes, candidata 07, documentación de continuidad o métrica desde esta zona. No hay adopción de Wascar.
- Avance acreditado aquí: revisión focal y corrección del P2; **delta de crédito cero**. La referencia consultada mantiene 3,57/100 del cierre del pendiente y no aporta un nuevo porcentaje global del producto.

Archivos escritos exclusivamente por el revisor: este informe, la prueba propia y la copia exacta previa autorizada. Revisión terminada al entregar el dictamen al coordinador.
