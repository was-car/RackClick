# Plantillas compartidas por cliente · contrato533–592

Estado: implementado y probado/revisado en laboratorios Windows/PostgreSQL/Edge, candidata592/schema10; avance78/100 estimado. Base532 conservada; QA real y ZIP532 permanecen intactos en este bloque. Los 60 hitos internos cubren contrato, servidor, interfaz, migración y pruebas; no son60módulos o60suites. Adopción final de Wascar pendiente.

## Alcance y autoridad

Se publica una copia NUEVA e inmutable de una plantilla privada propia activa en la colección de UN cliente. La privada no cambia ni se vuelve visible para otros actores. La publicación conserva propietario/autor original y su configuración exacta; retirar una copia no cambia originales ni equipos ya creados. No publicación externa en web/GitHub ni catálogo global entre clientes.

`templates.publish` es una capacidad específica concedida mediante los grupos y ámbitos existentes (Systemhaus, cliente o grupo de clientes). Leer exige `inventory.read`; publicar/retirar exige además `templates.publish`, sin exigir `inventory.edit`. Instanciar exige lectura+edición, sin exigir publicación. Se permite a un publicador vigente retirar cualquier publicación del cliente; no le da acceso a privadas ajenas. Se revalidan sesión/permisos después de las esperas y antes del commit/replay/cancelación/lectura. No basta ocultar botones.

Bootstrap NUEVO incorpora la capacidad al grupo administrativo inicial. La migración NO la concede a grupos/usuarios existentes. Un administrador autorizado puede concederla explícitamente mediante Concesiones. Actualizar los validadores cerrados de capacidades del adaptador administrativo/auditoría para admitir la décima capacidad, con nombres EN/DE/ES.

## Rutas y DTO cerrados

P=`/api/v1/customers/{id}/catalog/shared-templates`.

- GET P → `{kind:'sharedTemplates',customerId,revision,templates:[metadata]}`.
- GET P/{templateId} → `{kind:'sharedTemplates',customerId,revision,template:detail}`.
- POST P, publicar → `{type:'publish',privateTemplateId,definitionVersion:1,definitionSha256,name}`.
- POST P, retirar → `{type:'deactivate',templateId}`.
- GET P/operations/{requestId} → estado propio del actor.
- POST P/operations/{requestId}/cancel → misma intención cerrada que el POST original. Fence sin requerir fuente actual/existencia ni revisión vigente.

Metadata reutiliza los campos privados `id,name,active,definitionVersion,definitionSha256,kind,sizeU,groupCount,portCount` y añade `publishedById,publishedByName`. Detail añade `definitionByteLength,definitionBase64`, sin otra copiaJSON. No sourceTemplateId privado en respuestas compartidas, auditoría pública ni recibos. La entrada privada sólo pertenece a la intención propia del publicador y al compromiso hash del servidor.

Resultado: `{kind:'sharedTemplates',customerId,actorId,revision,requestId,operationId,result:{type,templateId,name,active,changed,definitionVersion,definitionSha256}}`. Estado: `{state,customerId,actorId,revision,requestId,operation}`; estados committed/cancelled/notRecorded. Se conserva el resultado terminal exacto incluso tras retirar fuente/publicación.

ETag separado `"shared-templates-N"`, If-Match, Idempotency-Key, actor, CSRF y Origin. Revisión por colección de cliente0..9007199254740991; máximo128activas. Nombre1..100escalares Unicode. Publicar siempre UUID nuevo. Retirar ya retirada es noop confirmado sin incrementar revisión ni generar otro evento de cambio; el recibo de la petición nueva sí debe quedar terminal según el patrón existente. Replay no vuelve a consultar la fuente ni altera bytes.

Instanciación mediante comando `device.createFromSharedTemplate` del motor de inventario existente; mismo payload de privateTemplate con UUID compartido/version/hash y destino/nombre/atributos explícitos. Sólo activa del mismo cliente/Systemhaus. UUID nuevos de equipo/grupos/puertos, estados free, watts null, properties limpias y cero cables heredados. Tipo/PoE independientes y GN por grupo conservados. Revisión/conflicto/idempotencia/auditoría/rollback del inventario intactos.

## Datos y compatibilidad

SQL010 aditiva separa revisión/definición/operaciones compartidas. Foreign keys de House/cliente/autor, límites, estados y unicidad por contexto. SQL001–009 no cambian. No autoconcesiones, reinterpretación, actualización o reserialización de datos históricos privados. Copiar los bytesUTF8 y hash privados verificados; validar V1 sin convertir la serialización original.

Orden de locks: operación propia → cliente SHARE → sesión/autoridad → biblioteca compartida exclusiva → biblioteca privada propia SHARE. Instanciar: cliente UPDATE → sesión → compartida SHARE; nunca toma privada. No ruta privado→compartido/cliente. Fallo de auditoría revierte definición/revisión/operación; fence no necesita fuente. No blueprint en journal del navegador, recibos o auditoría de publicaciones. No se altera revisión de inventario/House por publicar/retirar; instanciar sí genera su cambio normal de inventario.

## Interfaz y pruebas

Acceso desde barra del inventario RC9 a Plantillas compartidas. Consultar/preview/crear equipo conservando ubicación y Click-Click; publicación explícita desde privada propia con nombre público y advertencia de etiquetas. Retirar con confirmación. Lector sólo consulta; técnico con edit usa pero no publica sin permiso; publicador sin edit puede publicar/retirar pero no crear equipo. TextoEN/DE/ES, teclado y ventana390px. No redefinir la GUI aprobada.

Diario compacto nuevo por actor/cliente/intención y revisión. Respuesta perdida permite retry exacto/consulta/cancelación; reautenticación misma cuenta, abort/generaciones, no éxito antes del commit ni reenvío automático nuevo. No tocar digest/journals privados anteriores. No abrir un borrador compartido pisando otro editor/selección Click-Click.

Pruebas nativas Windows/PostgreSQL: nueva base10 y migración de base9 poblada NUEVA, filas previas exactas, permisos por unión de grupos/grupos de clientes, revocación/caducidad durante espera, ámbitos ajenos/CSRF/actor, Unicode/límites, copia byteexacta/retirada/replay/fence, instanciación de tres tipos/reinicio/segunda sesión, rollback/auditoría/concurrencia. Node/adaptador/diario y Edge multiactor con datos sintéticos. Revisión independiente acotada, una compilación estable por componente y regresión pertinente; conservar fallos originales.

Los operadores/paquete/actualizador vigentes son esquema9 cerrado: no introducirles esquema10 sin adaptación y pruebas específicas posteriores. QA69+ se documenta con pasos exactos pero NO DISPONIBLE en QA532. Guías se regeneran desde snapshot real y conservan resultados. Este bloque no modifica cuentas, datos o procesos del laboratorio de Wascar.

## Resultado del bloque

[Informe completo](../evidence/s1-20261018/sesenta-tandas-533-592/CIERRE.md): ocho focosPG de backend, dos propios del revisor, Edge multiactor y foco de avisosFINAL02, backup/restore de datos aislado33tablas. QA69–71 detallados pero no disponibles enQA532. No operadores/paquete/recuperación de aplicación10 ni QA manual/adopción.
