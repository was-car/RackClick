# Avisos descriptivos de inventario — contrato428–472

Estado: implementación probada en Windows/PostgreSQL/Edge y revisada independientemente; candidata de desarrollo no seleccionada en QA185. Alcance interno de 45 hitos; avance global inicial 76/100. Sin cambios de schema9/SQL001–009, dependencias, GUI RC9 adoptada ni QA185.

Se conserva íntegro GET `/api/v1/customers/{id}/changes` y su DTO actual. Nuevo GET `/api/v1/customers/{id}/changes/details` con los mismos parámetros afterRevision/limit, autoridad, locks cliente→sesión, ETag/no-store, contigüidad y gaps. Cada evento conserva los8campos existentes y añade `details`. El envelope mantiene6campos. Se comprueban inventory.read y sesión vigentes antes del cursor, después de esperas y antes de responder; House/cliente/actor no se obtienen del cliente. Sin operaciones, hashes de petición, secretos, blueprint ni JSON bruto en la respuesta.

`details` cerrado: `status` captured/notAvailable, `beforeEntities` y `afterEntities`. Cada entidad contiene exactamente relation, kind, id, name, parentKind, parentId, deviceKind, rackId, roomId, sizeU, positionU, sortOrder, groupType, prefix, portCount. relation=target/source/scope; kind=site/building/room/rack/device/portGroup. name/prefix son texto histórico literal o null cuando no aplica. parentKind=customer/site/building/room/rack/device o null, unido a parentId. deviceKind=rackEquipment/dose/endDevice o null. Campos restantes son null cuando no aplican. Identidades UUIDD no vacías; números enteros válidos según dominio. Grupos porUUID/tipo explícitos, nunca porgn. Máximo512entidades por lado; si se supera, details=notAvailable con ambas listas vacías, sin recorte silencioso. Duplicados de kind/id/relation o combinaciones imposibles invalidan el detalle completo, sin invalidar un evento base válido.

Para las23acciones que hoy carecen de contexto (jerarquía, racks, equipos, grupos), se captura descripción versionada dentro de los JSON de auditoría ya existentes, en la misma transacción antes/después del comando. No se usan audit_context/object administrativos ni DDL nueva. Captura de estados persistidos reales, no intención del payload: nombres, padre inmediatoUUID, ubicación rack/sala, tamaño/posición/orden y configuración/grupo/cantidad real de puertos cuando corresponda. Duplicación registra origen antes y nuevo destino después; reordenación registra todos los equipos afectados y orden persistido; borrados incluyen objetos eliminados afectados y grupos, limitados de forma explícita. No se inventan rutas históricas completas de antecesores.

Las7acciones que ya publican puertos/conexiones/compensación mantienen ese contexto finito anterior; no se exige duplicarlo en details. El código actual acepta30acciones, corrigiendo la cifra26 de la documentación antigua. Eventos anteriores sin captura versionada y contextos corruptos/ajenos/sobredimensionados devuelven notAvailable. No se completan con tablas actuales ni se modifican auditorías históricas. Descarga/replay/rollback/cancelación no crean otro aviso ni revision; captura y auditoría fallidas revierten junto al comando.

La proyección SQL reduce valores a tipos/campos finitos y limita arrays antes de leerlos en .NET. El formato privado de captura incluye House/cliente, acción, resourceId, versión, indicador complete y entidades; estos campos internos no se publican. Sin notas, propiedades, credenciales ni etiquetas libres. Captura/proyección se limitan a las entidades afectadas por la acción; una descripción incompleta no se declara captured.

**Corrección del borrador inicial:** `Names.Validate` cuenta `EnumerateRunes()`, no unidades UTF16. Nombre y prefix admiten hasta 100 valores escalares Unicode (hasta 200 unidades UTF16/400 bytes UTF8), como el dominio existente. No se restringen silenciosamente nombres válidos de 100 emojis. No se admiten controles ni espacios exteriores; name/prefix de grupo admiten cadena vacía. Los nombres del usuario se conservan literalmente.

## Campos y límites del dominio comprobados

| Entidad | Padre inmediato | Campos específicos; los demás son null |
|---|---|---|
| site | customer solicitado | name |
| building | site | name |
| room | building | name |
| rack | room o sin padre | name, roomId igual a parentId, sizeU 1..1000 |
| device rackEquipment | rack | name, deviceKind, rackId igual a parentId, sizeU 1..1000, sortOrder |
| device dose/endDevice | room | name, deviceKind, roomId igual a parentId, sortOrder; sizeU null |
| portGroup | device incluido en el mismo lado | name/prefix, groupType, sortOrder, portCount 1..96 |

`sortOrder` es un entero 0..Int32.MaxValue. `positionU` es siempre null: schema9 guarda orden, no posición física U. No se deduce un circuito físico. El grupo usa la familia persistida (`rj45`, `sfp`, `sfp28`, `qsfp`, `mgmt`, `console`, `power`, `usb_a`, `usb_c`); `rj45_poe` es una variante de puerto, no de grupo. Referencias: InventoryDevices.AddGroup/Device, InventoryImpact.EditPortGroups, Names.Validate y SQL002.

## Selección de las 23 acciones

| Acciones | Antes | Después |
|---|---|---|
| site/building/room.create (3) | vacío | un target persistido |
| site/building/room.update (3) | un target | mismo target persistido |
| site/building/room.delete (3) | un target | vacío; las FK exigen hijos vacíos |
| rack.create | vacío | un target rack |
| rack.update/rack.assignRoom (2) | un target rack | mismo rack actualizado |
| rack.delete | rack, sus devices y grupos, todos target | vacío |
| rack.duplicate | rack de origen, sus devices y grupos, todos source | nuevo rack y descendientes, todos target |
| device.create/createFromCatalog/createFromPrivateTemplate (3) | vacío | device y sus grupos, todos target |
| device.update/device.move (2) | device y sus grupos target | mismos IDs y estado persistido actualizado |
| device.reorder | un scope rack y todos sus devices target, sin grupos | mismos IDs y orden persistido; también se captura un rack vacío |
| device.delete | device y sus grupos target | vacío |
| devices.delete | conjunto explícito de devices y sus grupos target | vacío; resourceId es identidad de lote generada por servidor |
| device.editPortGroups | un scope device y todos sus grupos target | mismo device y configuración real de grupos resultantes |

No se proyectan puertos individuales en estas selecciones: se registra su cantidad real por grupo. La captura consulta sólo los objetos afectados y sus descendientes seleccionados, con `LIMIT 513`; no crea un snapshot de todo el cliente. La captura se realiza después de autorización, replay y revisión, antes/después del comando, en la misma transacción de auditoría/operación. La lógica histórica de cálculo de impacto sigue siendo independiente.

Invariantes verificables entre lados: deviceKind no cambia; device.update no cambia ubicación ni sortOrder; device.update/move no cambian descriptores de grupos; reorder sólo cambia sortOrder; editPortGroups no cambia el descriptor scope del dispositivo; los IDs de origen/destino de duplicate son disjuntos. No se pretende una firma criptográfica de la historia ni resistir a un administrador que reescriba toda una captura coherente en PostgreSQL.

GUI: usar el nuevo endpoint y validar DTO estricto. Mantener ChangeInbox, polling/backoff, autoridad/cancelación, selección, borradores y Click-Click. Añadir Antes/Después con nombres registrados y parentUUID/ubicación/tamaño/orden/grupos claramente tipados; distinguirlos del nombre actual del actor y de etiquetas actuales cargadas de puertos. No renderizar JSON bruto ni HTML. TextosEN/DE/ES; nombres escritos por usuario sin traducir. No aplicar ni recargar proyecto automáticamente. Históricos ausentes y límites deben quedar legibles y sin éxito fingido.

Pruebas exigidas y comprobadas en el cierre (con atribución y límites): captura/proyección de las23acciones; crea→renombra→mueve→borra con UUIDestable/nombreshistóricos; duplicación y reordenación; Dose/final en sala o equipo en rack sin circuitos ficticios; grupos con tipoyIDs; SQLsintético de corrupción/redacción/límites, autorización/aislamiento/revocación/sesiones tras espera, rollback/replay/gaps y reinicio. Una regresión pertinente v1 al estabilizar. Edge con dos sesiones y borrador, aviso/lectura explícita/permisos/cambio de cliente/idiomas y layoutRC9. Prueba acotada de escala con tamaño/tiempo observados, sin declararla capacidad productiva universal. Revisión independiente, catálogoQA detallado y disponibilidad real antes del cierre. No habilitar por mera existencia de código.
