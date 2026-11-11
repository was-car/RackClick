# Catálogo base RC9 y creación atómica ·114–128

Contrato implementado y comprobado por el autor en siete focos PostgreSQL/Windows sobre la pareja128congelada; [salida y límites](../evidence/s1-20261017/quince-tandas-114-128/backend/CIERRE.md). Revisión independiente, GUI y disponibilidad reales se registran en el cierre conjunto. Esquema7, SQL001–007 y capacidades existentes. No añade favoritos, preferencias, plantillas privadas/compartidas ni catálogo editable.

La referencia inmutable del producto se genera de `evidence/integrated-source.jsx` de la RC9 adoptada, comprobando su SHA256 contra el manifiesto del ZIP. `tools/catalog/generate_rc9_catalog.mjs` materializa33presets,7categorías y EN/DE/ES en `development/catalog/rc9-catalog.json` y `InventoryRc9CatalogData.g.cs`. Se ejecutan los patches de catálogo y las funciones originales `mkP`/`irTemplatePorts` en el extractor aislado; no se toma sólo la primera declaración PRESETS. La GUI obtiene esta referencia del servidor, sin inventario maestro local.

## Lectura

GET `/api/v1/customers/{id}/catalog?language=en|de|es`. Requiere sesión vigente, `inventory.read` en ese cliente y `If-Match: "<revision>"`. Query cerrada: exactamente una clave `language` con un solo valor; sin valor predeterminado. El servidor usa ReadCommitted, bloquea cliente FOR SHARE y revalida sesión/permisos tras esperas y antes del commit de lectura. Devuelve ETag con la misma revisión. No modifica datos, revisiones ni auditoría.

Respuesta cerrada: `customerId`, `revision`, `language`, `catalogVersion` (`rc9-base-v1`), `catalogSha256` (SHA256 lowercase de todos los bytes UTF-8 del JSON canónico, incluidos LF final e idiomas), `categories`, `presets`.

- Categoría: `key`, `label`, `presetKeys`. Key conserva la categoría original; label corresponde al idioma de la petición.
- Preset: `key`, `categoryKey`, `label`, `icon`, `color`, `sizeU`, `poeBudget`, `portGroups`.
- Grupo: `key` (`g1`...), `type` (familia), `name`, `prefix`, `sortOrder`, `ports`.
- Puerto: `gn`, `sortOrder`, `type`, `label`, `status`, `poe`, `watts`, `color`, `face`, `powerRole`, `properties` (vacío en esta referencia).

El catálogo no contiene UUIDs de inventario. `gn` sólo numera dentro del grupo; puede repetirse entre grupos. `rj45_poe` conserva su tipo de puerto y pertenece a grupo familia `rj45`.

## Creación

POST `/api/v1/customers/{id}/commands`, con type `device.createFromCatalog`. Usa los mismos If-Match/Idempotency-Key/actor/CSRF y recuperación/cancelación de la familia de comandos de inventario. Requiere `inventory.read` y `inventory.edit` actuales; no existe una capacidad nueva `inventory.create`.

Payload cerrado, exactamente once claves obligatorias:

```json
{
  "presetKey": "pdu",
  "catalogVersion": "rc9-base-v1",
  "catalogSha256": "<SHA256 de la respuesta>",
  "language": "es",
  "kind": "rackEquipment",
  "rackId": "<UUID>",
  "roomId": null,
  "name": "Nombre literal del técnico",
  "color": "#6b7280",
  "poeBudget": null,
  "notes": {"sn":"", "model":"", "ip":"", "firmware":"", "text":""}
}
```

`kind` sólo acepta `rackEquipment`, `dose`, `endDevice`. RackEquipment requiere rackId propio y roomId null, usa U canónica y comprueba capacidad. Dose/endDevice requieren roomId propio y rackId null, con size_u físico NULL. AP conserva la adaptación existente a endDevice/sala: la U1 del catálogo es referencia documental, no U física. Otros presets no infieren ubicación ni circuito. Ambos campos de ubicación deben estar presentes, incluso cuando son null.

Nombre utiliza la validación S1: trim exterior,1..100escalares Unicode, sin controles, sin traducción/casefold. Color obligatorio `#RRGGBB`, override del equipo; no cambia los colores de puertos. PoeBudget null o0..999999; cero no se convierte a desconocido. Notes contiene exactamente cinco strings, cada uno hasta2000escalares mediante FreeText; conjunto de propiedades persistidas hasta8192bytes UTF-8. El cliente no envía sizeU, grupos, puertos, UUIDs, layout, conexiones ni propiedades arbitrarias. Los objetos ajenos/no visibles producen404.

El motor comprueba sesión/ámbito/capacidad, fence y replay antes de resolver la versión actual del catálogo. Digest liga actor/cliente/clave/tipo/payload/revisión originales. Replay exacto devuelve resultado original incluso tras otra revisión del cliente; misma clave con otra carga devuelve409request_id_reused. Version/hash distintos en una petición nueva producen409catalog_changed, sin escritura; recargar catálogo y revisar el borrador antes de preparar otra operación. Se mantienen401/403/404/409/412/422/428actuales.

Se generan UUIDs nuevos para equipo/grupos/puertos, conservando asociación y orden explícitos. Se insertan todos los atributos canónicos en una única transacción; una revisión y auditoría `inventory.device.createFromCatalog`, con resourceId del equipo y createdIds exactos. Resultado estándar `customerId/revision/requestId/operationId/result`. Sólo se confirma después del commit y de la revalidación final de sesión/read/edit. Fallo intermedio revierte equipo, grupos, puertos, revisión, resultado y auditoría. La creación manual `device.create` y edición de grupos existentes mantienen su contrato.

## Paridad y límites

PDU incorpora9puertos power: rear,1inlet+8outlet. UPS incorpora5power,1mgmt y1USB-A: power rear,1inlet+4outlet. Otros power efectivamente presentes reciben rear/inlet y etiqueta PSU. Las etiquetas iniciales de alimentación se materializan en el idioma de creación y después son datos persistidos, sin traducirse al cambiar idioma. Los8presets añadidos por Object.assign después del patchpower no reciben puertos eléctricos inventados. Puertos no-power permanecen auto/unspecified; sólo rj45_poe inicia PoE true; status free,wattsnull,colornull según referencia. Equipos sin puertos son válidos.

No se crean cables, endpoints, pasantes internos de Dose, circuitos ni cálculos eléctricos. La acción aparece en el canal de cambios con contexto notAvailable, igual que la creación manual; no se declara una nueva captura histórica tipada. Favoritos/plantillas persistentes necesitan tablas dedicadas futuras.

`test_inventory_catalog.py` define siete focos PostgreSQL: catálogo99definiciones/lectura sin cambios y muestras ricas, validación/límites/AP, ámbitos/CSRF/revocación tras espera, replay/concurrencia/412, fallo de inserción parcial/auditoría/feed, compatibilidad manual/grupos/catalog_changed/cancelación y reinicio ASP.NET/otro usuario. Requiere DLL/frontend congelados y laboratorios nuevos; no utiliza QA real. La preparación de estas pruebas no equivale a haberlas ejecutado.
