# Operaciones pendientes de confirmación

Implementación S1 en desarrollo, 28.09.2026. Este documento describe el protocolo del bloque de inventario; su validación nativa se registra aparte y no se presupone por haber escrito código.

Un fallo de red no demuestra que el servidor haya revertido. La GUI conserva antes de enviar el UUID, actor, cliente, cuerpo y revisión originales en IndexedDB, sin cookies ni tokens. Este registro contiene comandos pendientes y puede incluir los textos que el usuario intentaba guardar; no es una copia autoritativa del inventario. Recuperar el navegador exige la identidad original y autorización vigente.

El reintento conserva exactamente esa operación. No se crea otra porque falle la recarga posterior a una respuesta ya confirmada. Un resultado confirmado y un error de refresco son estados distintos. Los datos compartidos se vuelven a leer desde PostgreSQL.

## Consulta y cancelación

`GET /api/v1/customers/{id}/operations/{requestId}` consulta una operación del actor autenticado dentro del cliente autorizado. Puede devolver `committed` y su resultado original, `cancelled` y la confirmación conservada, o `notRecorded`. Este último estado no demuestra que una petición retrasada no pueda llegar después.

`POST /api/v1/customers/{id}/operations/{requestId}/cancel` permite resolver esa incertidumbre sin deshacer datos confirmados:

- Cookie vigente, Origin, CSRF y `X-RackClick-Actor` obligatorio, igual al usuario autenticado.
- `Idempotency-Key` obligatorio e igual al UUID de la ruta. Diferencia:422 `request_id_mismatch`; ausente/inválido:422 `request_id_invalid`.
- Cuerpo `{type,payload}` original y `If-Match` con la revisión **original**. Forman parte del digest de la operación. La revisión actual puede ser posterior; cancelar no escribe inventario ni incrementa su revisión.
- `inventory.read` y la capacidad de la operación original: `inventory.delete` para `.delete`, `inventory.edit` para las demás. La lectura y la sesión se vuelven a comprobar después de esperar los locks. Sin ámbito:404; sin capacidad:403.
- Si la operación ya se confirmó, devuelve `committed` con `operation` original; no ejecuta undo.
- Si no se confirmó, guarda una marca de cancelación duradera y su auditoría en la misma transacción. Devuelve `cancelled` únicamente después del commit.
- Una llegada tardía del mismo UUID/cuerpo/revisión devuelve409 `operation_cancelled`. Reutilizarlo con otra operación devuelve409 `request_id_reused`.

Respuesta de cancelación nueva: `{state:"cancelled",customerId,requestId,revision,operationId,operation:null}`. Repetirla con la misma entrada devuelve el JSON conservado. Si ya existía commit: `{state:"committed",customerId,requestId,revision,operation:{…resultado original…}}`. Si se pierde la respuesta de cancelar, se conserva el mismo registro pendiente y se consulta/reintenta; no se adivina el resultado.

## Persistencia y revisión

`003-operation-cancellation.sql` añade `operation_cancellation`, con claves compuestas de actor/cliente/Systemhaus. Cancelación y ejecución comparten un lock transaccional por Systemhaus/actor/UUID. Triggers sobre ambas tablas impiden conservar simultáneamente los estados confirmado y cancelado, también ante inserciones SQL directas que usan ese protocolo. Esta garantía debe probarse concurrentemente contra PostgreSQL, no inferirse del texto del trigger.

La auditoría de cancelación guarda identidad, cliente, UUID, digest y tipo del comando; no guarda tokens ni contraseñas. El fallo de auditoría debe revertir también la marca de cancelación. Estas marcas no se purgan en esta versión: una política de retención futura necesita una regla de caducidad de replays antes de eliminarlas, o una petición antigua podría volver a ejecutarse.

El protocolo descrito se aplica a comandos de inventario. No se atribuye automáticamente a todas las pantallas del fundamento ni a operaciones administrativas/importaciones futuras. La revocación administrativa concurrente, la política de retención completa y la recuperación del servidor siguen requiriendo su propio bloque y evidencia.

## Evidencia GUI Windows — tanda03

[Recorrido y reproducción](../evidence/s1-20260928/lotes-recuperacion-03/CIERRE.md): registro IndexedDB original conservado después de reiniciar Edge. Respuesta perdida tras commit: retry mismo UUID/cuerpo/revisión/actor, un solo recurso/revisión, diario retirado después de confirmación. Petición que no llegó al servidor: recuperación y cancelación autorizada con marca cancelled, inventario/revisión intactos. No implica recuperación tras apagado abrupto, revocación concurrente ni reinicio Windows.
