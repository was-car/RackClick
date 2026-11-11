# C2 · catálogo de jerarquía, racks, equipos y orden

**Actualización posterior del 25.10.2026:** I-04.02/03 tienen sus focos revisados en laboratorio; I04-GUI-01 también fue corregido en un bloque anterior. Véanse [nombres/destinos y variantes](C2-NOMBRES-DESTINOS-RACK-25-10-2026.md) y [permiso de borrado](C2-PERMISOS-BORRADO-25-10-2026.md). Los estados de hallazgos y pendientes que aparecen abajo describen la conciliación inicial, que se conserva como antecedente. I-04.04–07 siguen pendientes. Véase también [duplicado y reserva](C2-DUPLICADO-VARIANTES-25-10-2026.md).

25.10.2026 · I-04.01. Inventario de funciones existentes para reutilizar sus pruebas. No es una nueva ejecución de esos recorridos ni una aceptación de la candidata 14.

## Lista cerrada: 19 familias y 23 comandos

Todos usan `POST /api/v1/customers/{customerId}/commands`. E significa `inventory.read` + `inventory.edit`; D significa `inventory.read` + `inventory.delete`, sin exigir edición. El servidor comprueba sesión, cliente, revisión, permisos e identidad de la operación. El catálogo no altera estas reglas.

Los controles se encuentran en [InventoryPanel.jsx](../development/frontend/src/InventoryPanel.jsx). El despacho y la autorización están en [InventoryStore.cs](../development/server/src/RackClick.Server/InventoryStore.cs); la vista previa de impacto, en [InventoryImpact.cs](../development/server/src/RackClick.Server/InventoryImpact.cs).

| # | Control existente | Comando y permiso | Prueba reutilizable / límite |
|---|---|---|---|
| 1 | Crear/editar sede: `hierarchy('site',…)` | `site.create`, `site.update` · E | [Pruebas PostgreSQL](../development/server/tests/test_inventory_postgres.py), [alta GUI](../development/frontend/tests/browser-inventory.mjs) y [edición 59](../development/frontend/tests/browser-hierarchy-edit59.mjs). |
| 2 | Crear/editar edificio y elegir sede: `hierarchy('building',…)` | `building.create`, `building.update` · E | PostgreSQL y edición 59; reasignación por UUID, no por nombre. |
| 3 | Crear/editar sala y elegir edificio: `hierarchy('room',…)` | `room.create`, `room.update` · E | Mismas fuentes; padre obligatorio del mismo cliente. |
| 4 | Eliminar sede, edificio o sala: `removeEntity` | `site.delete`, `building.delete`, `room.delete` · D | PostgreSQL y edición 59; se rechazan ubicaciones ocupadas. No hay lote de ubicaciones. |
| 5 | Crear rack: `rackEditor()` | `rack.create` · E | PostgreSQL y alta GUI. |
| 6 | Editar nombre, sala, U y ubicación del rack: `rackEditor(r)` | `rack.update` · E | Edición 59 asigna sala. Existe validación contra ocupación; falta cerrar todas las variantes visuales de reducción U. |
| 7 | Asignación específica de sala, sólo API | `rack.assignRoom` · E | PostgreSQL. `roomId:null` desasigna. El selector GUI de la fila 6 envía `rack.update`; no inventar otro botón. |
| 8 | Duplicar rack, con opción de cables y confirmación reserved: `duplicateRack` | `rack.duplicate` · E | [GUI de duplicado](../development/frontend/tests/browser-inventory-duplicate.mjs) y PostgreSQL. El histórico 53 cubre con cables; sin cables y reserved positivo siguen en I-04.03. |
| 9 | Eliminar rack: `removeEntity('rack',r)` | `rack.delete` · D, con preview | [Impacto GUI](../development/frontend/tests/browser-impact.mjs) y PostgreSQL. Conserva equipos del extremo externo. |
| 10 | Alta manual de equipo, Dose o final: `deviceEditor`, modo manual | `device.create` · E | PostgreSQL y alta GUI. Clases cerradas: `rackEquipment`, `dose`, `endDevice`. |
| 11 | Alta desde preset RC9: `InventoryCatalogFields` | `device.createFromCatalog` · E | [API catálogo](../development/server/tests/test_inventory_catalog.py), [GUI catálogo](../development/frontend/tests/browser-inventory-catalog.mjs); 33 presets, 7 categorías, EN/DE/ES. No todas las combinaciones visuales verificadas. |
| 12 | Instanciar plantilla privada: modo private | `device.createFromPrivateTemplate` · E y plantilla propia | [GUI privada](../development/frontend/tests/browser-private-templates.mjs). Mantenimiento de plantillas pertenece a otro resultado. |
| 13 | Instanciar plantilla compartida: `sharedDeviceEditor` | `device.createFromSharedTemplate` · E; no requiere `templates.publish` | [GUI compartida](../development/frontend/tests/browser-shared-templates.mjs); existen pruebas de las tres clases de objeto. |
| 14 | Editar equipo o tarjeta de sala: `deviceEditor(value)` | `device.update` · E | PostgreSQL cubre nombre/propiedad y conservación. GUI ofrece nombre, U, presupuesto, SN, modelo, IP, firmware y notas; falta comprobar cada variante prevista en I-04.02. |
| 15 | Opciones del equipo → Mover → rack destino: `moveDevice` | `device.move` con `rackId` · E | [Movimiento GUI](../development/frontend/tests/browser-inventory-movement.mjs), PostgreSQL e histórico 52. |
| 16 | Tarjeta Dose/final → Mover → sala destino: `moveDevice` | `device.move` con `roomId` · E | [Traslado entre salas](../development/frontend/tests/browser-room-device-move.mjs), PostgreSQL e histórico 62. Conserva UUID y cables. |
| 17 | Flechas ↑/↓, arrastre y callbacks táctiles: `reorder`, `drop` | `device.reorder` · E | Movimiento GUI 52 cubre flechas/límites; [edición rápida](../development/frontend/tests/browser-inventory-instant.mjs) cubre contexto. No acredita drag ni táctil. |
| 18 | Papelera de equipo o tarjeta de sala: `removeEntity('device',d)` | `device.delete` · D, con preview | Impacto GUI y [regresión de borrado](../development/server/tests/test_inventory_delete_batch.py). También admite Dose/final. |
| 19 | Seleccionar/quitar selección y eliminar conjunto: `[data-delete-selected]` | `devices.delete` · D, con preview | [API de lote](../development/server/tests/test_inventory_delete_batch.py), [GUI de lote](../development/frontend/tests/browser-delete-batch.mjs), histórico 61: 1..64 UUID, clases mixtas y un commit/revisión. |

Los tres tipos de alta desde catálogo/plantillas se incluyen sólo como entradas de inventario. Edición y publicación de plantillas, grupos/puertos, compensación y Click-Click/cables mantienen sus tareas propias; no se retiran del alcance general.

## Reglas y límites existentes

- Rack y equipo en rack: U entero entre 1 y 1000; se comprueba la ocupación. El orden es documental, mediante la lista completa de UUID, y no expresa una posición física U. Véase [InventoryDevices.cs](../development/server/src/RackClick.Server/InventoryDevices.cs).
- Dose/final requiere sala, con `rackId` y `sizeU` nulos. El traslado no cambia su clase ni crea continuidad eléctrica o un circuito interno.
- Alta manual: hasta 32 grupos, entre 1 y 96 puertos por grupo. Describe el alta; no sustituye el contrato de editar grupos.
- Catálogo: claves cerradas; AP sólo como final en sala. Se generan UUID nuevos y ninguna conexión. Los cinco campos de notas admiten hasta 2000 escalares. Véase [InventoryCatalogDevices.cs](../development/server/src/RackClick.Server/InventoryCatalogDevices.cs).
- Duplicar remapea UUID de contenido del rack y, opcionalmente, sus cables internos; conserva los externos y no duplica objetos de sala. Véase [InventoryDuplicate.cs](../development/server/src/RackClick.Server/InventoryDuplicate.cs).
- Borrar un equipo o un conjunto incluye cables incidentes, preservando racks y equipos/puertos del otro extremo. Las ubicaciones ocupadas se rechazan. La vista previa y la confirmación no equivalen a restaurar un borrado.

## Diferencia concreta de permisos GUI

**I04-GUI-01 · pendiente de corrección y ensayo.** El servidor permite borrar con lectura+borrado, sin edición. En la GUI actual, `removeEntity` comprueba borrado, pero después llama a `open`, que exige edición. Además, varios botones individuales están dentro de `canEdit` y `OperationDialog` recibe `writeAllowed={canEdit}`. Una cuenta autorizada sólo para borrar encuentra un bloqueo adicional en la interfaz.

Se identificó por lectura de código, no mediante un ensayo nuevo de navegador. No demuestra una autorización indebida ni pérdida de datos. La corrección debe separar edición y borrado en controles, apertura y recuperación de la operación original; probar cuenta read+delete sin edit, read+edit sin delete, revocación y denegación HTTP real. Se trata en I-04.05/06, conservando permisos y pruebas existentes; no se amplía el denominador ni se da por arreglado aquí.

## Evidencia que se reutiliza y lo que falta

Los cierres [52](../evidence/s1-20261017/tres-tandas-52/CIERRE.md), [53](../evidence/s1-20261017/tres-tandas-53/CIERRE.md), [55–59](../evidence/s1-20261017/quince-tandas-55-59/CIERRE.md), [61](../evidence/s1-20261017/tres-tandas-61/CIERRE.md) y [62](../evidence/s1-20261017/tres-tandas-62/CIERRE.md) acreditan sus ejecuciones históricas, versiones y límites. Las pruebas fuente de la tabla son vías de reproducción, no pruebas ejecutadas en esta tanda ni equivalencia automática de sus bytes con la candidata 14.

I-04.01 cierra únicamente **esta lista y la reutilización de pruebas**. I-04.02–07 siguen pendientes: variantes de rack/metadatos, duplicado sin cables/reserved positivo, drag/táctil, borrado/impacto y permisos, candidata final/segunda cuenta/reinicio, revisión y QA aplicables. El catálogo y las guías QA no cambian por una conciliación documental.

[Evidencia, identidad de fuentes y revisión independiente](../evidence/s1-20261025/c2-catalogue-codex/CIERRE.md). Sin producto modificado, compilación, pruebas funcionales nuevas, commits, instalación, QA o VM.
