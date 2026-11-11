# Revisión independiente de I-04.01

25.10.2026. Revisor distinto del autor; revisión documental acotada, con Git inspeccionado y cambios ajenos conservados. Única escritura propia: este informe. La consulta previa del explorador no se presenta como esta revisión.

**Dictamen: apto para marcar sólo I-04.01 como done.** El catálogo responde al texto fijo «Cerrar lista de controles/comandos existentes y reutilizar prueba; no rehacer lotes ni CRUD por tabla51». Identifica funciones y pruebas reutilizables sin convertirlas en ejecuciones nuevas ni declarar cerradas sus variantes. I-04.02–07 permanecen pendientes. No encontré un defecto documental material que impida cerrar la lista.

Documento revisado: [C2-CATALOGO-JERARQUIA-25-10-2026.md](../../../docs/C2-CATALOGO-JERARQUIA-25-10-2026.md), SHA256 `ee2746c802eae2440411592ab8d8e7d240bc090cef79327f80204d163b0067ad`.

## Focos reales de lectura

| Foco | Contraste efectuado |
|---|---|
| Cantidades y comandos | Conteo propio mediante Python en memoria: 19 filas, 24 menciones y **23 comandos distintos**; `device.move` aparece para rack y sala. Todos los tipos figuran en `InventoryStore.Apply`. No se incluyen grupos/puertos/cables como nuevas familias de este catálogo. |
| API frente a GUI | `rack.assignRoom` existe en `Apply/Hierarchy`, acepta `roomId:null`; `InventoryPanel.rackEditor` envía `rack.update`. La fila 7 lo declara sólo API y no inventa un botón. |
| Permisos | `InventoryStore.Execute` y `InventoryImpact.PreviewImpact`: READ+EDIT para escritura ordinaria, READ+DELETE para `.delete`, sin exigir EDIT en servidor. `open`, `removeEntity`, controles y props del diálogo confirman la restricción adicional de GUI documentada. |
| Presets y plantillas | `InventoryCatalogDevices.CreateFromCatalog`, `InventoryRc9Catalog.Load` y pruebas fuente respaldan 33 presets/7 categorías/EN-DE-ES y AP como final en sala. `CreateFromPrivateTemplate/PrivateDeviceTemplates.ForCreation` comprueban propietario; `CreateFromSharedTemplate/SharedDeviceTemplates.ForCreation` permiten instanciar sin `templates.publish`. La administración/publicación de plantillas queda separada. |
| Movimiento y orden | `InventoryPanel.moveDevice/reorder/drop` y `InventoryDevices.Device/Capacity`: rack frente a sala, identidad estable y lista completa de UUID para orden documental. La existencia de callbacks drag/táctiles no se presenta como prueba ejecutada de esos gestos. |
| Duplicado y borrado | `InventoryDuplicate.DuplicateRack` remapea contenido y sólo duplica cables internos opcionales. `InventoryImpact.ImpactFor/DeleteInventory` recoge incidentes y el lote 1..64. `Hierarchy` y las FK de `database/002-inventory.sql` respaldan el rechazo de ubicaciones ocupadas. No se afirma restauración de borrado. |

Se leyeron además los focos pertinentes de `test_inventory_postgres.py`, `test_inventory_catalog.py`, `browser-shared-templates.mjs` y las referencias históricas 52, 53, 55–59 y 62. Confirman vías de reproducción y límites; no se auditó toda su implementación ni se ejecutaron sus recorridos.

## Enlaces, hallazgos y límites

Comprobación propia de rutas: **27 referencias locales a 26 destinos únicos**. El único destino ausente en el primer control era el cierre de esta tanda; se comprobó su existencia después de crearlo el coordinador. Los otros destinos existían. No se hizo un barrido recursivo de todos los enlaces de los documentos históricos.

**I04-GUI-01 — diferencia funcional existente, prioridad P2, evidencia estática:** una cuenta READ+DELETE sin EDIT encuentra bloqueos adicionales en apertura, botones o `writeAllowed`. Está descrita fielmente como pendiente, sin afirmar reproducción DOM ni corrección. Corresponde tratarla en los focos de borrado/integración I-04.05/06; no impide finalizar el inventario documental I-04.01. Sin otros hallazgos nuevos bloqueantes del catálogo.

**Pruebas funcionales ejecutadas: ninguna. Builds: ninguno.** Sólo lectura, conteo/comparación de literales, resolución de rutas y hashes; sin nuevas fixtures ni suites. No PostgreSQL, navegador, QA/VM, MFA, W-02, instalaciones o commits. No se modificaron producto, plan, métrica, guías ni resultados de Wascar. Este dictamen reconoce la lista; no certifica candidata 14, aceptación o porcentaje global del producto.
