# Revisión independiente · conciliación de I-01.03

25.10.2026. Revisor distinto del coordinador/implementador. Tanda de lectura, pruebas sintácticas y contraste de evidencia; sin cambios de producto, .NET, backend, MFA, QA/VM, W-02, paquetes o zonas de otros agentes. Git inspeccionado antes de escribir. Se conservan las instrucciones ya leídas de `AGENTS.md`, `docs/BRIEFING-MAESTRO.md`, `docs/EQUIPO-Y-SKILLS.md` y `.codex/agents/qa.toml`. Único archivo escrito por este revisor en la tanda: este informe; no fue necesaria otra fixture.

**Dictamen: apto para marcar I-01.03 como terminado técnicamente en el desarrollo identificado.** La evidencia acumulada más el ensayo READ sin EDIT cubren el texto exacto de ese subpaso para Deshacer crecimiento/reducción pura de grupos. No identifico un hueco restante propio de ese texto. Este dictamen no marca el resultado I-01 completo, no adopta candidata ni acredita MFA/instalación/QA; tampoco edita el plan o la métrica del coordinador.

## Alcance exacto y corrección de la conciliación

`docs/PLAN-CIERRE-RACKCLICK.json`, I-01.03:

> Integrar consulta/reintento/cancelación originales ante incertidumbre e invalidación tras otra revisión/permiso/cuenta/cliente.

Ese texto pertenece al resultado **Deshacer de crecimiento/reducción pura de grupos**. No exige resolver todas las capacidades de todas las APIs o escritores de inventario. `InventoryStore.Execute` selecciona DELETE sólo para tipos terminados en `.delete`; `operations.compensate` y `device.editPortGroups` seleccionan EDIT. `RequireCompensationAuthorization` vuelve a comprobar sesión, READ y EDIT; las dos inversas estructurales lo reutilizan. La consulta original requiere READ; `OperationCancellation.Cancel` exige READ y la capacidad de la intención original antes de devolver resultados previos. Para esta intención es EDIT.

Por tanto, exigir una invalidación por pérdida de `inventory.delete` a estas operaciones ampliaba indebidamente el criterio. La observación anterior «no se probó toda capacidad específica» era un límite de aquellas tandas, no un nuevo requisito contractual de I-01.03. Sus informes históricos se conservan con sus resultados y alcance originales.

I-01.05 exige congelar candidata coordinada con MFA/instalación y probar sus bytes. I-01.06 exige guiones/disponibilidad en la candidata real. I-01.07 cierra el resultado y su revisión/aceptación aplicable. Se mantienen separados: no son condiciones para impedir reconocer el cierre técnico de I-01.03, ni quedan satisfechos por él.

## Matriz contra el texto de I-01.03

| Parte del criterio | Evidencia contrastada | Evaluación |
|---|---|---|
| Consulta original ante incertidumbre | [Consulta](../c2-query-codex/CIERRE.md) y su [revisión distinta](../c2-query-codex/REVISION.md): GET committed/notRecorded/cancelled, recibo/actor/cliente originales y validación estructural; regresiones posteriores de contexto e instant. | Cubierto. notRecorded conserva intención; sólo estado terminal validado permite limpieza. |
| Reintento original | Escenarios de consulta previos; nuevo escenario READ sin EDIT: primer envío detenido antes de llegar al servidor, reintento UI bloqueado tras revocar EDIT y replay tras restituirlo con cuerpo, actor, clave y ETag iguales al registro original. | Cubierto. No se renueva silenciosamente la revisión ni se prepara otra solicitud. |
| Cancelación original | [Contexto](../c2-context-codex/CIERRE.md): cancelación confirmada con respuesta retenida/cambio de cuenta y posterior recuperación cancelled. [Instant](../c2-instant-codex/CIERRE.md): cancelación de intención no enviada libera el mismo panel. Nuevo ensayo: cancelación 403 sin EDIT no limpia el journal. | Cubierto, incluida diferencia entre cancelar incertidumbre e invertir un commit. |
| Otra revisión | [Elegibilidad](../c2-eligibility-codex/CIERRE.md); regresión sobre frontend `0df395a6…` en [REGRESION-ELEGIBILIDAD.json](../c2-instant-codex/REGRESION-ELEGIBILIDAD.json): otro actor avanza revisión; el Deshacer abierto queda bloqueado y un submit controlado no crea journal ni POST. Pruebas de revisión durante preview/put/lista. | Cubierto para el criterio; no restaura un snapshot sobre cambios ajenos. |
| Otro permiso | Nuevo [EDGE-PG.json](EDGE-PG.json), [NAVEGADOR.json](NAVEGADOR.json) y escenario revisado: READ permanece, EDIT se retira y DELETE está ausente. GET sigue autorizado; reintento/cancelación no evaden la nueva autorización. | El hueco real entre READ y EDIT queda cubierto. La revocación previa de toda la membresía por sí sola no lo acreditaba. |
| Otra cuenta | Contexto: login real de otra cuenta en el mismo perfil, recarga real y desmontaje por actor/cliente, respuestas tardías sin confirmar la vista nueva ni retirar el journal anterior. Regresión final instant reproduce el cambio real y posterior consulta del propietario. | Cubierto por navegador y por guardas/unidades independientes. |
| Otro cliente | [Revisión de contexto](../c2-context-codex/REVISION.md) y [de instant](../c2-instant-codex/REVISION.md): cambios de props/cliente, A→B→A observado, invalidación persistente y callbacks tardíos suprimidos. Inspección de la clave actor+cliente de `InventoryPanel`. | Cubierto por funciones reales extraídas, guardas y montaje inspeccionado; no se presenta como un nuevo ensayo DOM de cambio de cliente. |
| Fronteras asíncronas de las vías implicadas | Revisiones independientes de [contexto](../c2-context-codex/REVISION.md), [elegibilidad](../c2-eligibility-codex/REVISION.md) e [instant](../c2-instant-codex/REVISION.md): journal, preview, envío, limpieza, callbacks, épocas de lista, mutex e intención antes de render. P2 previos preservados con negativos originales FAIL/finales PASS. | Cubierto de forma acumulada; las salvedades históricas quedaron tratadas en las tandas posteriores pertinentes. |

La matriz no afirma todas las permutaciones de todos los escritores. Las inversas puras comparten `operations.compensate`, autorización READ+EDIT, diálogo y journal; el nuevo ensayo ejercita crecimiento. Las pruebas anteriores de ambas variantes, sus validaciones y el código común sostienen la conciliación del subpaso, sin añadir un requisito de repetir cada cruce de variante/permiso/cliente.

## Nuevo ensayo de permisos revisado

Lo ejecutó el **coordinador**, no este revisor, con Edge real, IndexedDB, HTTP y PostgreSQL 17.11 en laboratorio nuevo. Se leyeron tanto el escenario como el runner y sus resultados; se inspeccionaron las dos capturas públicas.

1. Técnico con READ+EDIT sobre el cliente sintético y sin DELETE: creación de crecimiento y apertura de Deshacer; CDP falla la petición antes del servidor y conserva la intención exacta. Se retira sólo EDIT. El submit queda bloqueado sin otra respuesta `/commands`; GET devuelve notRecorded; cancelar devuelve 403 para el requestId original, con journal y datos intactos. Al restaurar EDIT, el escenario compara cuerpo, actor, idempotency-key y ETag con el registro antes de permitir el replay.
2. Inversa confirmada con respuesta 200 retenida y perdida: al retirar EDIT pero conservar READ, un POST directo del mismo cuerpo/clave/ETag devuelve 403. GET recupera committed, cierra la recuperación y limpia su journal; el inventario permanece en el estado original. La concesión EDIT temporal queda retirada.

Resultado final del coordinador: **PASS, exit 0, 21,83 s**, Edge `156.0.4314.42`, sin excepciones JS. El runner comprueba nueve tablas de inventario exactamente restauradas, persistencia tras reiniciar el proceso servidor, entradas sin modificar y laboratorio/servidores detenidos. El listado HTTP incluye GET 200 de las dos operaciones originales, cancelación 403 y POST replay 403. No es reinicio Windows ni ensayo de servicio/VM.

Primer intento conservado: [PRIMER-ENSAYO.json](PRIMER-ENSAYO.json), FAIL/exit 1 en 16,44 s, sin excepciones JS. [OBSERVADOR.json](OBSERVADOR.json) identifica la espera: se encontró una alerta de denegación ya existente antes de que CDP registrase `Network.responseReceived` de cancelar. El coordinador cambió sólo el test para esperar la respuesta 403 de la ruta original y el fin de busy. Se contrastó la diferencia con `browser-first.mjs` preservado privado; no se atribuye ese primer fallo a producto ni se oculta como una ejecución satisfactoria.

Capturas inspeccionadas por el revisor: [READ sin EDIT e intención pendiente](read-without-edit-pending.png) muestra explicación de denegación, notRecorded y reintento deshabilitado; [recibo recuperado con sólo READ](readonly-original-committed.png) muestra el diálogo cerrado y estado Guardado por el servidor. Son capturas del laboratorio sintético, no resultados de Wascar.

## Identidad y continuidad de fuentes

Se calcularon hashes reales de los artefactos privados reutilizados y se compararon las fuentes actuales con las de la copia privada del frontend. Se contrastaron `FUENTES.json` y resultados de las tandas previas. La lectura de resultados anteriores se declara evidencia acumulada, no una ejecución nueva del revisor.

| Elemento | SHA256 |
|---|---|
| Frontend privado reutilizado `app.js` | `0df395a6a273476fea48e704ee5802a7d777727db12de85c34f0dd3d70aa1f94` |
| DLL C2 reutilizada | `5eb1abcf9d2f91d293bae8f1b01e94f0352ca254c0387aaa45de1c35b2a97585` |
| `OperationDialog.jsx`, actual y copia de build | `d6be606b7feed2af9f78c7b0f6fd4f38d52f0a14bc4b6df228a76deed3b52e2a` |
| `InventoryPanel.jsx`, actual y copia de build | `151e9de6e222a13b4e973b251e30e5b2358f7599fcf018bf03abc776468e0303` |
| `ServerApp.jsx`, actual y copia de build | `bf17b36a20a27d48c1232b1a562d01f8382e38595da2c58cb9bc6579afa67650` |
| `browser-inventory-write-permission.mjs` final | `ffa92d25dd1cce473e10f07547e231cc69387d2fa482bdb59728bb22250ce620` |
| Escenario inicial fallido, preservado privado | `f6da0e79b9c9c6ae8646a48dcb7234e028e3564f29e8af2c1694c4b54cc581e6` registrado por su runner |
| `test_inventory_operation_status_gui.py` | `2ac86688f7dab9780cb46241c069895e5a71ddd3a451bb6ce6f1fd50c590d4d6` |

No hubo build nuevo en esta tanda ni se transfieren resultados a una candidata MFA distinta. El frontend/DLL anteriores se reutilizaron identificados; el árbol backend compartido en curso no fue recompilado o declarado adoptado.

## Archivos, símbolos y ejecución del revisor

Además de los documentos/informes de la matriz se consultaron:

- `docs/PLAN-CIERRE-RACKCLICK.json`: texto, peso y límites I-01.03/05/06/07; las frases antiguas sobre capacidades específicas no modifican el texto congelado.
- `development/frontend/tests/browser-inventory-write-permission.mjs`: `grant`, `permission`, `refreshIdentity`, `grow`, `held`, `lose`, correlación de replay y dos ciclos de permiso.
- `development/frontend/tests/browser-quince-support.mjs`: `runScenario`, `CDP`, registro de respuestas/excepciones, `submit`, `saved`, `snapshot`, `normalize`; se verificó que requestSubmit es controlado y la observación HTTP es CDP.
- `development/server/tests/test_inventory_operation_status_gui.py`: selección cerrada `write-permission`, rutas privadas, laboratorio nuevo, control de nueve tablas, reinicio del proceso, hashes/entradas y cierre de procesos.
- `development/server/tests/test_inventory_movement_gui.py`: `fixture`, READ del grupo técnico en el cliente, EDIT inicial sólo en el otro cliente y concesión separada del escenario.
- `development/server/src/RackClick.Server/InventoryStore.cs`: `Execute`, selección de capacidad y autorización antes de leer replay; `InventoryCompensation.cs`: `RequireCompensationAuthorization`; `InventoryGroupGrowthCompensation.cs` y `InventoryGroupReductionCompensation.cs`: llamadas a esa autorización; `OperationCancellation.cs`: `Read`, `Cancel`, selección de capacidad original. Lectura de código, sin ejecución backend propia.
- `InventoryPanel.jsx`, `OperationDialog.jsx`, `ServerApp.jsx`, escenarios `browser-inventory-context.mjs`/`browser-inventory-eligibility.mjs`, JSON `FUENTES`, `NODE`, `EDGE-PG` y regresiones de los cuatro cierres anteriores.

Ejecutado realmente por este revisor durante esta tanda:

```powershell
& .local/node-v24.21.0-win-x64/node.exe --check development/frontend/tests/browser-inventory-write-permission.mjs
& C:/Python312/python.exe -B -c "import ast,pathlib; ast.parse(pathlib.Path('development/server/tests/test_inventory_operation_status_gui.py').read_text(encoding='utf-8')); print('AST Python: PASS')"
```

Ambas comprobaciones sintácticas finalizaron con exit 0. No son pruebas funcionales de Node ni PostgreSQL. También se realizaron lecturas, hashes y la inspección visual indicada. No se añadieron tests que duplicasen la implementación ni se repitieron las cinco pruebas anteriores por inercia.

## Hallazgos, pendientes y límites

Sin defecto nuevo P1/P2/P3 de producto reproducido en esta conciliación. El primer fallo del observador queda identificado y corregido en el escenario; el hueco real de READ conservado sin EDIT queda cubierto por el PASS final. La anterior exigencia de DELETE se descarta como ampliación de alcance para este subpaso, sin eliminar controles del producto.

**Dentro del texto de I-01.03, bajo Deshacer grupos puros, no queda un hueco identificado que impida su cierre técnico.** El coordinador puede registrar el subpaso como done con estas evidencias y esta revisión distinta. Los criterios/textos/pesos permanecen intactos; este revisor no cambia su estado ni calcula crédito en el JSON.

Siguen pendientes I-01.05, I-01.06 e I-01.07, la candidata coordinada API+GUI/MFA/instalación, su prueba sobre bytes finales, disponibilidad QA real y aceptación aplicable. Quedan fuera autenticación/reautenticación global, MFA completo, todos los escritores de inventario, Undo/Redo universal, Windows/SCM/VM y aceptación de Wascar. No se presenta una compilación o prueba de laboratorio como integración de candidata.

No ejecuté PostgreSQL/Edge, build, suites funcionales, instalador o QA en esta tanda. Las ejecuciones funcionales son del coordinador; las pruebas propias anteriores conservan su fecha, fuente y atribución en cada informe. Se avanza en la conciliación del subpaso; no se inventa un nuevo porcentaje global del producto. La métrica deberá actualizarla el coordinador mediante su generador y controles habituales si registra el cierre.
