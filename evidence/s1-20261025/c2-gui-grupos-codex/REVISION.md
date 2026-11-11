# Revisión independiente focal · GUI de compensación estructural

25.10.2026 · Revisor distinto del implementador. Dictamen **favorable en el alcance acotado revisado**, sin bloqueadores reproducidos. No cierra I-01, no valida una candidata distribuida ni habilita QA.

## Entradas y separación de trabajo

Se inspeccionaron los cambios respecto de `.local/c2-gui-groups-20261025-30afba8c8704/before/development/frontend/src/` en `inventory-compensation.ts`, `inventory-api.ts`, `InventoryPanel.jsx` e `inventory-words.ts`, junto con los nuevos `InventoryGroupCompensationScope.jsx`, `inventory-group-compensation-words.ts` y el test del autor. Se leyeron `api.ts`, `inventory-model.ts`, `OperationDialog.jsx` y `pending-journal.ts` para comprobar sus límites de integración.

Git tenía modificaciones previas del coordinador y de otros frentes. El revisor no editó producto, pruebas compartidas, contratos, guías, catálogo QA ni trabajo W-02. Sus únicas salidas son este informe y un directorio privado nuevo:

`.local/c2-gui-review-601424da36e8490da21afb2233fd9c1e/`

`inputs.json` conserva ocho hashes completos de fuentes copiadas. `review-result.json` acredita que esos ocho archivos seguían idénticos al terminar. Referencias principales: `inventory-compensation.ts` SHA256 `6778e215c3a14fd07cf31b69bbd0067f6e48beb7b4fb75d45e611793cd49f54a`; `inventory-api.ts` `9e3fc48cc64c602a6e240221ed32c305407e6f54866f6c62fe6fb87ad88ce06d`; `InventoryPanel.jsx` `dda11be8ac5c8c5758716270f6e3d58cf37a2e89f05559144eb8f5ca604235a4`.

## Lectura focal

- El candidato estructural requiere dos vistas adyacentes del mismo cliente y revisión, además de operación/actor/request/recurso coincidentes. Se comparan dispositivo y filas supervivientes; crecimiento y reducción tienen variantes separadas, límites y conjuntos explícitos. Sin ambas vistas no se fabrica historial estructural tras recarga.
- `committed()` conserva la vista fuente, relee y sólo registra un candidato compatible con la revisión recibida. Permanecen las invalidaciones por otra revisión, cambio de actor/cliente, permiso y operación pendiente, así como los callbacks de avisos.
- El diálogo presenta UUID de grupos/puertos/cables y distingue retirar de restaurar. La casilla requerida también se comprueba en `build`; no se añadió un preview ficticio de `operations.compensate`. El payload sigue siendo exclusivamente `{operationId}`.
- La expectativa de respuesta comprueba variante, recurso y conjuntos revisados, también al recuperar un resultado comprometido. Una respuesta estructural no se trata como `changedIds`.
- El journal continúa guardando el comando original compacto. No se guarda un snapshot anterior, evidencia inversa ni token de sesión. La expectativa adicional es efímera; tras recarga puede recuperarse la operación exacta con la validación estructural existente, pero no reaparece un candidato nuevo basado en un `before` inventado.
- El componente usa texto JSX y UUID; no introduce HTML recibido. Los textos EN/DE/ES describen el alcance y los límites de evidencia/conflicto. Esta lectura no acredita renderizado, pronunciación ni accesibilidad integral.

## Pruebas propias realmente ejecutadas

Entorno: Windows NT 10.0.26300.0, Node **v24.21.0** fijado en `.local/node-v24.21.0-win-x64/node.exe`. Se ejecutó una sola tanda de **cinco negativos propios**, con controles positivos del mismo fixture, sobre copias privadas de las fuentes indicadas:

```powershell
& C:/RackClick_SVR/.local/node-v24.21.0-win-x64/node.exe --test --test-reporter=tap C:/RackClick_SVR/.local/c2-gui-review-601424da36e8490da21afb2233fd9c1e/negatives.test.mjs
```

| Caso propio | Resultado comprobado |
|---|---|
| R1 · UUID repetido mediante distinta caja | Rechaza el candidato aunque las dos cadenas UUID difieran en mayúsculas/minúsculas. |
| R2 · Reducción elimina un cable sólo de puertos supervivientes | Rechaza describir esa desconexión ajena como reducción pura. |
| R3 · Cable superviviente reconectado a un puerto recién añadido | Rechaza el candidato mixto. |
| R4 · Respuesta estructural con UUID duplicados por distinta caja | `response_invalid`, conservando incertidumbre; no éxito confirmado. |
| R5 · Cancelación comprometida contiene operación de otro cliente | `response_invalid`, conservando incertidumbre; no recupera el resultado ajeno. |

Resultado: **5/5 PASS, 0 FAIL, 0 omitidas**, exit0, TAP duration130.4735ms. Salidas privadas `negative-tests.tap`, `negative-tests.stderr` —vacío— y `review-result.json`, terminadas a `2026-10-25T10:02:26.3644947Z`. No son pruebas PostgreSQL ni de navegador.

El revisor leyó las pruebas del autor; **no ejecutó ni se atribuye su 27/27**. No compiló frontend/servidor ni repitió suites amplias. Los intentos iniciales de localizar Node en PATH fallaron; se utilizó después su ruta fijada, sin instalar herramientas ni cambiar PATH. Los errores de consulta/diff de lectura no son fallos de producto ni ejecuciones de prueba.

## Límites y continuación

La revisión sustenta el modelo de candidato, alcance/confirmación y validación de respuesta de I-01.01/I-01.02 y el contexto parcial de I-01.04. La autoridad de evidencia completa, estado, permisos y commit sigue en el servidor.

El coordinador conserva la ejecución Edge/PostgreSQL con DLL C2 identificada y frontend privado; el revisor no la repitió ni accedió a QA/VM/servicios/bases. Quedan comprobaciones de render y recorrido real, incertidumbre/reinicio y revisión de esa combinación, integración futura en candidata completa y QA de Wascar. No se acepta con este informe la edición mixta, reservados nuevos, undo/redo general, detalle histórico estructural ni adopción del servidor.

## Adenda · corrección del observador de la regresión de atributos

25.10.2026. Se leyó el diff de `development/frontend/tests/browser-inventory-compensation.mjs` frente a `.local/c2-gui-groups-20261025-30afba8c8704/attribute-browser-before.mjs`, normalizando finales de línea únicamente para presentar la comparación. **Conforme en revisión estática:** corrige el diagnóstico del fixture, sin relajar las condiciones de éxito del producto.

El observador anterior cortaba a22hooks y suponía `candidate=values[20]`, `stale=values[21]`. La GUI actual tiene estados de plantillas antes del candidato; ese índice ya no identifica `undoCandidate`. El nuevo observador examina hasta64hooks y busca el objeto por `operationId` de texto, `portIds` array y `deviceId` de texto; usa `null` si no existe. El estado obsoleto se lee del aviso DOM. El control positivo añadido compara los `portIds` del objeto encontrado con el alcance del diálogo cuando el candidato sí está visible: por tanto, un buscador que siempre devolviera `null` no superaría el foco. Permanecen intactas las aserciones finales de candidato `null`, botón ausente, revisión y ubicación remotas cargadas, aviso retirado y una sola instancia de panel/canal/consulta. No se modificó `OperationDialog`, el comando ni la autoridad del servidor.

Se reconfirmaron por lectura los ocho hashes de producto de `inputs.json`: todos siguen idénticos a la revisión anterior. No se ejecutaron suites adicionales, Node, navegador, PostgreSQL, builds ni operaciones de QA/VM por el revisor en esta adenda. El coordinador comunica un recorrido estructural Edge/PostgreSQL nuevo conforme y conserva el fallo original del foco de atributos como fallo del observador; su repetición focal corregida y su resultado se atribuyen al coordinador, no a esta revisión.

Lectura documental adicional: el diff de `qa_guide.py` frente a `qa-guide-before.py` sólo cambia la frase del porcentaje heredado por el enlace al plan de cierre. El catálogo actual tiene113casos frente a111enHEAD: los111objetos anteriores son exactamente iguales y los dos añadidos, QA-112/113, siguen `feature: planned`, con indisponibilidad explícita y pasos de ubicación/botón/campo. Esta lectura no regenera guías, no habilita casos ni modifica resultados del navegador de Wascar. El dictamen acotado permanece; candidata distribuida, QA y cierre I-01 siguen pendientes.
