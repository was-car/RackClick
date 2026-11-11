# Favoritos personales del catálogo BASE RC9 ·129–143

Contrato congelado por el coordinador el17.10.2026. Implementado y comprobado por el autor en siete focos PostgreSQL/Windows sobre la pareja143 congelada; [ejecución y límites](../evidence/s1-20261017/quince-tandas-129-143/backend/CIERRE.md). Revisión independiente, GUI y disponibilidad QA se atribuyen al cierre conjunto; esto no acredita adopción. Referencia BASE actual:33presets/7categorías, `rc9-base-v1`, SHA256 `764aa2d016057bc8232f86d4b82a5ef7c156667e906460d1b6bdef51ffcfcd92`. No incluye plantillas editables, compartidas ni publicación.

El propietario siempre procede de la sesión. El mismo usuario conserva sus favoritos entre sus clientes visibles; otro usuario tiene un agregado separado. El cliente de la ruta sólo sirve como contexto de autorización: sesión vigente y `inventory.read` actual en ese cliente para GET, escritura, replay, estado y cancelación. Un lector autorizado puede gestionar sus propios favoritos; no se exige `inventory.edit`, ni se añade capacidad o concesión automática. Revalidación antes y después de esperas y antes del commit/retorno. No se modifica inventario, revisión de cliente/Systemhaus ni canal de cambios de inventario.

## Rutas y DTO cerrados

GET `/api/v1/customers/{id}/catalog/favorites`, sin query ni cuerpo ni If-Match de inventario. Devuelve:

```json
{"kind":"catalogFavorites","customerId":"<contexto>","ownerId":"<actor>","revision":0,"catalogVersion":"rc9-base-v1","catalogSha256":"<64hex lowercase>","presetKeys":[]}
```

`presetKeys` va en orden ordinal. GET no inserta filas: agregado ausente equivale a revisión0 y lista vacía. ETag exacto `"favorites-0"`; la revisión personal es un entero0..9007199254740991, independiente de inventario. Los demás formatos ETag son inválidos.

POST a la misma ruta recibe exactamente cuatro campos, sin idioma, propietario, cliente, grupos, layout ni propiedades:

```json
{"presetKey":"pdu","catalogVersion":"rc9-base-v1","catalogSha256":"<64hex lowercase>","favorite":true}
```

`favorite` es booleano explícito, nunca toggle. Encabezados obligatorios: `If-Match: "favorites-N"` personal original, `Idempotency-Key` UUID no vacío, `X-RackClick-Actor` UUID del actor original, Origin y CSRF de la sesión. La respuesta confirmada es:

```json
{"kind":"catalogFavorites","ownerId":"<actor>","revision":1,"requestId":"<UUID>","operationId":"<UUID>","result":{"presetKey":"pdu","favorite":true,"changed":true,"catalogVersion":"rc9-base-v1","catalogSha256":"<64hex lowercase>"}}
```

No contiene customerId: recuperar la misma operación desde otro cliente accesible devuelve el mismo resultado personal. Si la pertenencia ya coincide, `changed:false`, revisión sin incremento, pero operación/auditoría se confirman una sola vez. Una intención nueva con revisión antigua sigue produciendo412 aunque el booleano coincida. La versión/hash actuales se validan sólo para intenciones nuevas, después de comprobar replay/fence; discrepancia409 `catalog_changed`, clave inexistente422 `preset_invalid`.

GET `/api/v1/customers/{id}/catalog/favorites/operations/{requestId}` y POST de esa ruta más `/cancel` devuelven:

```json
{"state":"committed","ownerId":"<actor>","revision":1,"requestId":"<UUID>","operation":{"kind":"catalogFavorites","ownerId":"<actor>","revision":1,"requestId":"<UUID>","operationId":"<UUID>","result":{"presetKey":"pdu","favorite":true,"changed":true,"catalogVersion":"rc9-base-v1","catalogSha256":"<64hex lowercase>"}}}
```

`state` también puede ser `notRecorded` o `cancelled`; en ambos casos `operation:null`. `revision` exterior es la revisión personal actual; la operación interior conserva su revisión histórica. Status sin query. Cancel exige el cuerpo original de cuatro claves, el ETag personal ORIGINAL y la misma Idempotency-Key que la ruta. Puede cerrar una intención con revisión/version/hash antiguos sin rebasarla. Nunca deshace un commit: devuelve el estado committed y su resultado original. Cancelar una intención sin registro crea un fence terminal duradero, sin cambiar favoritos ni revisión. Entrada tardía del mismo original devuelve409 `operation_cancelled`; clave con cuerpo/revisión diferentes409 `request_id_reused`.

El ETag de POST committed corresponde al resultado histórico, incluso en replay. Status/cancel usan la revisión exterior actual. El adaptador recarga GET tras confirmación para obtener el agregado/ETag actuales; nunca aplica una respuesta histórica como lista maestra. `notRecorded` no prueba que no exista una petición tardía: sólo el fence cancelado bloquea su entrada. Reautenticación del mismo actor permite recuperar, siempre con lectura vigente en el cliente usado. Cambiar actor exige mantener pendiente el intento original, sin enviarlo bajo otro propietario.

## Persistencia y atomicidad

SQL008 añade únicamente `user_catalog_favorites` (revisión por Systemhaus/usuario), `user_catalog_favorite` (pertenencia por presetKey) y `user_catalog_favorite_operation` (resultado terminal/fence por usuario/requestId). SQL001–007 permanecen idénticos. Las dos primeras tablas son la fuente maestra; ni localStorage, ni inventory.properties ni un historial de operaciones reconstruyen el estado. Versión/hash de cada intención quedan en resultado/auditoría; la identidad del favorito es la clave estable del catálogo BASE. No se descartan claves persistidas silenciosamente al actualizar la referencia.

Transacciones ReadCommitted. Orden de locks: advisory exclusivo de petición `RackClick/catalog-favorites-operation/{house:D}/{actor:D}/{request:D}` y después advisory del agregado `RackClick/catalog-favorites/{house:D}/{actor:D}`. GET/status usan lock compartido de agregado, POST/cancel exclusivo; GET no toma lock de petición. No se bloquea una fila de cliente ni se usa su revisión. Digest canónico incluye familia, House, propietario, cuatro campos originales y revisión personal esperada; excluye contexto de cliente e idioma. La clave de idempotencia pertenece exclusivamente a esta familia/propietario; no comparte journal con comandos de inventario o administración.

Pertenencia, revisión personal, auditoría `user.catalogFavorite.set` y resultado terminal se escriben en una sola transacción. Cancelación usa `user.catalogFavorite.set.cancel`. resourceId identifica al propietario; metadatos sólo personales/públicos del preset, sin cliente histórico ni secretos. Replay/cancel repetido no duplican auditoría. Un fallo revierte todas estas filas. Un único registro terminal con PK compuesta y state committed/cancelled evita dos terminales para la misma petición; fences retenidos indefinidamente en este alcance, sin purga30d inventada. Revisiones hasta máximo entero seguro de JavaScript; una mutación que lo exceda devuelve409 sin escritura.

Errores:401 sesión inválida,404 contexto ausente/no visible,403 Origin/CSRF,409 actor cambiado/catálogo cambiado/clave reutilizada/fence/revisión agotada,412 conflicto personal,422 forma/clave/booleano/UUID/ETag inválidos,428 ETag ausente. Los DTO rechazan campos extra, duplicados y tipos ambiguos. Ninguna ruta permite seleccionar otro propietario.

## Verificación prevista y límites

Siete focos PostgreSQL nuevos ejecutados: copia7→8 y constraints; GET vacío/no inserción/lector/aislamiento/ámbitos; validación/CSRF/sesión y revocación tras espera; no-ops/replay entre contextos/status/cancelación; concurrencia/misma clave/412; rollback/auditoría/inventario intacto; reinicio ASP.NET y recuperación mediante login nuevo. PG01:7/7 correctos,63.771s unittest/75.016s envolvente, SDK10.0.401/PostgreSQL17.11 en Windows; laboratorios nuevos detenidos y entradas intactas. La migración del foco01 parte de bootstrap7 nuevo, con filas de fundamento/cuentas/grants; el inventario rico se preserva en foco06 sobre DB8. Copia/restauración operacional rica7→8 corresponde al coordinador Windows. Revocaciones del arnés se provocan por SQL sintético, no se atribuyen a recorridos administrativos GUI. No acredita pérdida real de una respuesta HTTP en esta suite, reinicio de Windows, plantillas, edición compartida, retención operativa ni instalación/QA/adopción final.
