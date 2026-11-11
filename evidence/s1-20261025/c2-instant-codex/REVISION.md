# Revisión independiente C2 · instant

25.10.2026. Encargo acotado del coordinador, revisor distinto del implementador, Windows/PowerShell y Node local 24.21.0. Se conservan las instrucciones ya leídas de `AGENTS.md`, `docs/BRIEFING-MAESTRO.md`, `docs/EQUIPO-Y-SKILLS.md` y el perfil `.codex/agents/qa.toml`. Git comprobado antes de escribir: árbol compartido con cambios ajenos, sin revertirlos. Propiedad del revisor limitada a este informe y `review-instant-negative.test.mjs`.

**Dictamen: conforme para los cinco focos y el hash revisados.** 5/5 pruebas propias PASS. No encontré un defecto nuevo en ese alcance. Reproduje con controles negativos los problemas de contexto anteriores y el defecto intermedio de segunda acción detectado por el coordinador; ambos quedan bloqueados en la fuente final examinada. No se cierra I-01.03, ni MFA, ni adopción o métrica global.

## Archivos y símbolos consultados

| Archivo | Símbolos / comprobación |
|---|---|
| `development/frontend/src/InventoryPanel.jsx` | `panelOrigin`, `panelContext`, `panelInContext`, `requirePanelWrite`, `instantInFlight`, `instantIntent`, `pendingEpoch`, `refreshPending`, `refresh`, `committed`, `instant`; inspección del guard posterior de reconexión en `choosePort`. |
| `development/frontend/src/revision-gate.ts` | `RevisionGate.begin`, `confirm`, `accept`; import real utilizado por la fixture. |
| `development/frontend/src/inventory-api.ts`, `pending-journal.ts` | `prepareCommand`, `pendingRecord`, contrato del journal y eliminación condicionada por propietario; imports reales, inspección del contrato ya realizada en las revisiones C2 anteriores. |
| `development/frontend/tests/inventory-instant-context.test.mjs` | Lectura de las diez pruebas del implementador y su harness. No se presentan como ejecución propia sus diez PASS ni las 1 PASS/8 FAIL previas comunicadas. |
| `.local/c2-instant-20261025T122334Z-da4af7d2/before/development/frontend/src/InventoryPanel.jsx` | Fuente pre-tanda comparada y ejecutada en controles nuevos. |
| `.local/c2-instant-20261025T122334Z-da4af7d2/InventoryPanel.before-pending-guard.jsx` | Intermedia preservada por el coordinador, antes de `instantIntent`; controles nuevos de la segunda acción. |

## Cinco focos ejecutados

Fixture propia: extrae del archivo real las funciones de guardas, `refreshPending`, `refresh`, `committed` e `instant`, más la asignación real del contexto. Cada render crea closures independientes; las referencias sobreviven y `useCallback` conserva el callback según sus dependencias. Las escrituras de estado se registran y, cuando el caso lo requiere, provocan otro render simulado. No reutiliza el harness del implementador ni los nueve/cinco tests de tandas anteriores.

`prepareCommand`, `pendingRecord` y `RevisionGate` son reales. HTTP, IndexedDB y las funciones de construcción/publicación del candidato se sustituyen por fixtures sintéticas y promesas controladas. La eliminación del journal simulado comprueba actor. Las llamadas a `candidate`/`remember` son sondas de callback, no una acreditación de la lógica real de compensación.

| Foco | Resultado final |
|---|---|
| Una lista antigua vacía termina después de otra más reciente con la intención incierta. No publica estado, no borra el bloqueo de intención y no permite segundo despacho antes de render. | PASS |
| `committed` espera una lectura de revisión 5; el cliente cambia A→B→A. Al terminar no publica snapshot/revisión/candidato/listas y la invalidación persiste. | PASS |
| Respuesta incierta seguida de fallo de lectura del journal: conserva exactamente la intención, evita segundo despacho y libera el mutex. Tras simular resolución del journal y leerlo correctamente, otra acción puede continuar. | PASS |
| Se renderizan el busy y el pending de la propia acción durante la primera lectura del journal. Ese estado propio permite completar el despacho iniciado y retirar su registro confirmado. | PASS |
| Commit confirmado y journal retirado, pero lista final fallida: mantiene confirmado el resultado, libera el mutex y conserva un bloqueo prudente hasta releer correctamente. Después acepta otra acción sin bloqueo permanente. | PASS |

La resolución del tercer caso se simula retirando el registro de la fixture y realizando una lectura posterior; no se ejecutó la consulta/cancelación real ni se alteró un journal del usuario.

## Hallazgos y controles negativos

Sin hallazgos nuevos reproducidos en el alcance final. **P2 previo del coordinador, confirmado por el revisor y corregido:** la intermedia sin `instantIntent` admitía otro `instant` después de una respuesta incierta antes de que el pending llegase al render. El control propio registra dos despachos en esa fixture; no demuestra dos commits SQL ni corrupción real. La fuente final conserva la referencia de intención hasta que una lectura actual comprueba que el registro ya no está.

La misma intermedia permite comenzar otra acción cuando el commit anterior retiró su journal pero falló la lectura final; el control final exige recuperación explícita de la lista. Se verifica la liberación del mutex de ejecución por separado de esa referencia persistente de intención.

En la fuente pre-tanda, la lectura posterior a A→B→A todavía publica `setSnapshot`, `onRevision`, `candidate`, `remember` y la lista. El control final verifica ausencia de esas llamadas. No se vuelve a presentar el defecto antiguo como un hallazgo nuevo de esta revisión.

## Relación de ejecuciones reales

| Ejecución nueva del revisor | Resultado |
|---|---|
| Primera corrida propia de cinco focos | 5 PASS, 0 FAIL, 0 omitidas, exit 0, 118,7114 ms. |
| Dos focos contra pre-tanda `d907…` | 0 PASS / 2 FAIL esperados, exit 1, 159,7744 ms: callbacks tardíos y segundo despacho tras incertidumbre. |
| Dos focos contra intermedia `00d6…` | 0 PASS / 2 FAIL esperados, exit 1, 145,7816 ms: segundo despacho incierto y segunda acción tras terminal/lista fallida. |
| Ajuste de fixture, no de producto | El foco `committed` se precisó con operación `ports.update` y lectura de revisión 5, elegible para `RevisionGate`; así el control comprueba también la publicación tardía de snapshot/revisión. |
| Corrida final propia tras ese ajuste | **5/5 PASS**, 0 FAIL, 0 omitidas, exit 0, 158,1736 ms. |
| Foco `committed read` fortalecido contra pre-tanda | 0 PASS / 1 FAIL esperado, exit 1, 128,8693 ms; `setSnapshot/onRevision/candidate/list` tardíos visibles. |

No se transforman logs históricos en estas ejecuciones. Node mostró `MODULE_TYPELESS_PACKAGE_JSON`, sin impedir los casos ni motivar cambios de paquetes.

Comando desde `C:\RackClick_SVR`:

```powershell
& .local/node-v24.21.0-win-x64/node.exe --test evidence/s1-20261025/c2-instant-codex/review-instant-negative.test.mjs
```

Controles: establecer `RACKCLICK_INSTANT_REVIEW_SOURCE` en una de las dos copias anteriores y usar, respectivamente, `--test-name-pattern 'committed read|uncertainty plus'` o `--test-name-pattern 'obsolete empty list|terminal cleanup'`. Las llamadas ejecutadas retiraron esa variable en `finally` y propagaron `$LASTEXITCODE`; los FAIL esperados devolvieron exit 1. Para el control fortalecido se usó el filtro `committed read`.

## Identidad examinada

| Archivo | SHA256 |
|---|---|
| `development/frontend/src/InventoryPanel.jsx` | `151e9de6e222a13b4e973b251e30e5b2358f7599fcf018bf03abc776468e0303` |
| `review-instant-negative.test.mjs` | `dea8396ddd0f59e91fab42c0575430d8bc2211bfee093220e82972968c4da191` |
| Pre-tanda `before/.../InventoryPanel.jsx` | `d907a92700d3259e0dabaacfe498d38a58ff8c1702ec36dff5af9039b2fd195e` |
| Intermedia `InventoryPanel.before-pending-guard.jsx` | `00d6f6ab91bae4a1e8bbd1de1edfe1bdc7a7cd8261bf8c2be2c8b5b1ef17cf36` |

## No ejecutado y límites

- No ejecuté navegador/DOM, IndexedDB real, HTTP/PostgreSQL, servidor .NET, SQL, compilaciones, instalador, VM/QA, MFA, W-02 ni reinicio. Los ensayos que aporte el coordinador mantienen su autoría propia.
- No repetí las diez pruebas del implementador, las nueve/cinco de tandas anteriores ni suites generales. El callback de reconexión se inspeccionó, sin prueba DOM propia.
- La fixture acredita callbacks y serialización local del panel. No es un lock entre pestañas o procesos ni demuestra exclusión de todas las demás vías de edición.
- `refreshSharedPending`, `refreshConfigurationPending`, autenticación global, recuperación de cuentas y matriz completa de permisos/revisión/cuenta/cliente no se cierran aquí. Las guardas de este bloque no sustituyen autorización, idempotencia ni transacciones del servidor.
- No se acreditan candidato de compensación real, paridad visual, persistencia, aceptación ni I-01.03 completa por comprobar las sondas del harness.
- Sin cambios de métrica: delta de crédito cero y ningún porcentaje global nuevo. La última referencia consultada de 3,57/100 corresponde al cierre del pendiente, no al producto completo. QA y adopción final de Wascar pendientes.

Sólo se escribieron los dos archivos asignados de evidencia; no hubo modificaciones de producto por el revisor.
