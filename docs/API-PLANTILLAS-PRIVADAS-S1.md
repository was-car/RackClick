# Plantillas privadas de equipos — contrato159–173

17.10.2026. S1 autorizado; este documento define el bloque en desarrollo, no declara pruebas ejecutadas ni adopción. Colecciones compartidas, publicación y editor libre de una plantilla siguen pendientes de S-26.

Una plantilla es una configuración separada del inventario, propiedad del usuario de la sesión dentro de su Systemhaus. La captura queda inmutable; se puede desactivar y capturar otra. No hay propietario enviado por el navegador, concesiones nuevas, localStorage maestro, SQLite ni escritura en el catálogo BASE. SQL009 añade sólo `user_device_templates`, `user_device_template` y `user_device_template_operation`; SQL001–008 intactas. La revisión personal comienza en0, máximo9007199254740991. GET no crea filas. Lista de activas: máximo128, ordenUUID; al superar el límite se rechaza la captura, sin truncar ni retirar otras plantillas.

## API y autorización

Prefijo `P=/api/v1/customers/{id}/catalog/private-templates`. Todas las consultas están cerradas/vacías. Los UUID deben ser no vacíos. Las rutas exigen sesión vigente e `inventory.read` actual en el cliente contexto. Captura, desactivación, consulta de operación y cancelación exigen además `inventory.edit` actual; el lector sólo consulta sus propias plantillas, no recibe permisos de editar inventario. Existencia/propietario/ámbito no visible:404; lectura visible sin edición:403. No se consultan colecciones de otros usuarios, aunque el solicitante sea administrador. La colección propia se puede consultar y utilizar desde otro cliente al que el mismo actor tenga acceso; la captura no conserva vínculo operativo con su origen.

| Ruta | Respuesta200 |
|---|---|
| GET P | `{kind:"privateTemplates",customerId,ownerId,revision,templates:[metadata]}`; sólo activas |
| GET P/{templateId} | `{kind:"privateTemplates",customerId,ownerId,revision,template:{...metadata,definitionByteLength,definitionBase64}}`; incluye inactiva propia |
| POST P | recibo confirmado `{kind:"privateTemplates",customerId,ownerId,revision,requestId,operationId,result:{type,templateId,name,active,changed,definitionVersion,definitionSha256}}` |
| GET P/operations/{requestId} | `{state,customerId,ownerId,revision,requestId,operation:null\|recibo}` |
| POST P/operations/{requestId}/cancel | mismo estado; intención, revisión y clave originales |

`metadata={id,name,active,definitionVersion:1,definitionSha256,kind,sizeU,groupCount,portCount}`. No contiene equipo/cliente/rack/sala originales ni definición completa. El detalle entrega bytes de la definición, no un segundo objeto maestro reserializado.

POST P acepta exactamente una de estas formas, sin campos adicionales o duplicados:

```json
{"type":"capture","deviceId":"UUID","name":"Nombre literal","sourceRevision":1}
```

```json
{"type":"deactivate","templateId":"UUID"}
```

Cabeceras de mutación: Origin/CSRF, `X-RackClick-Actor` obligatorio, Idempotency-KeyUUID y `If-Match: "templates-N"` personal original, también para reintento/cancelación. Falta de revisión428; formato, leadingzeroes, rango o tipos422. El nombre usa la política Unicode de Names: trim,1..100 escalares, sin controles, sin traducción/NFC. El sourceRevision de captura es entero1..9007199254740991.

**Dos conflictos412 distintos:** `revision_conflict` indica colección personal obsoleta; `source_revision_conflict` indica inventario fuente obsoleto. Mantener el borrador y recargar sólo la referencia correspondiente. Una desactivación nueva de una plantilla ya inactiva devuelve changed=false, conserva revisión y registra una única operación/auditoría. El tombstone no reactiva ni borra la definición. Un cambio real incrementa una vez la revisión personal. Capturar/desactivar/cancelar nunca cambia inventario, revisiones cliente/Systemhaus ni avisos multiusuario del inventario.

## ConfiguraciónV1 y privacidad

La definición JSON cerrada contiene exactamente:

```text
kind, sizeU, poeBudget, icon, color, visualFamily, portGroups[
  {key:"g1" (ordinal),type,name,prefix,sortOrder,ports[
    {gn,sortOrder,type,label,poe,color,face,powerRole}
  ]}
]
```

Se captura bajo bloqueo del cliente que impide cambios simultáneos y se valida cada familia/tipo/PoE/rol/cara. Los campos tipo y PoEboolean se conservan de forma independiente dentro de la familiaRJ45: `rj45+true` y `rj45_poe+false` son combinaciones válidas del esquema recibido y de irPoeEnabled. PoEtrue en familias ajenas se rechaza; no se normaliza el tipo al capturar/instanciar. Orden fuente por sort_order,UUID se normaliza a ordinales consecutivos; key g1..g32 identifica el grupo de plantilla, gn no sustituye su identidad. Máximo32grupos y96puertos/grupo; grupo no vacío; exceso o configuración inválida se rechaza explícitamente. Kind original `rackEquipment|dose|endDevice`; sizeU1..1000 sólo para equipo de rack y NULL para sala. PresupuestoPoE null o decimal0..999999; icono texto≤100escalares, color#RRGGBB; nombres/prefijos de grupos≤100 y etiquetas≤500escalares, literales. Estos nombres/etiquetas forman parte de la configuración reutilizable y el preview lo advierte.

No se capturan nombre del equipo, ubicación, clientes, rack/sala, UUIDs del inventario, serial/IP/modelo/firmware/notas, sesiones/tokens, propiedades genéricas del equipo/puerto, catálogo de origen, estado de ejecución, watts ni conexiones/cables. `properties` no existe en el formatoV1. Icono y color se extraen por whitelist; sin propiedad, valores documentados `▦` y `#64748b`.

**Caras AUTO y decoración:** visualFamily es enum `storage|ups|blank|switch|panel`, derivado exclusivamente del properties.preset técnico existente con la precedencia real de RC9 irLayout: `server|srv|nas|storage|san`→storage; `ups`→ups; `blank|spacer|cable|shelf|bl[12]u|sp[12]u|cbl`→blank; `switch|^sw`→switch; resto→panel. No se conserva el preset literal ni se deduce de un nombre nuevo. Al crear se escribe únicamente ese enum como properties.preset, reconocido por los componentes RC9 y el SVG. FaceAUTO permaneceAUTO y conserva cara efectiva (storage/ups y power detrás), incluso si una NAS se renombra PDU. No se infieren circuitos o pasos físicos de Dosen.

**Hash y bytes:** el servidor ordena claves ordinalmente y serializa a JSONUTF8; la definición se guarda como TEXTJSON validado, máximo1048576bytes y SHA256minúscula. No se reconstruyen sus bytes desde JSONB ni JavaScript. GETdetalle envía base64 de esos bytes exactos y definitionByteLength; el adaptador verifica longitud, SHA256 de bytes decodificados, UTF8 y formato cerrado, después JSONparse. Esto conserva decimales1.0 y escapes Unicode sin exigir que JSON.stringify produzca los mismos bytes. DefinitionVersion/hash son inmutables, incluso tras desactivar/reiniciar. Definición completa nunca aparece en recibos/journals/auditoría.

## Instanciación y recuperación

Motor existente `POST /api/v1/customers/{id}/commands`, type=`device.createFromPrivateTemplate`, payload exactamente:

```text
{templateId,definitionVersion:1,definitionSha256,kind,rackId,roomId,name,color,poeBudget,
 notes:{sn,model,ip,firmware,text}}
```

If-Match es revisión habitual del cliente destino, no templates-N; recuperación/cancelación del motor de inventario existente. Sólo plantilla propia activa; otro propietario404, inactiva409template_inactive, hash/versiondistintos409template_changed (versiones diferentes de1 se rechazan422 por formato). No hay fallback a Manual/BASE. Kind debe coincidir exactamente con la plantilla; placement explícito: rackEquipment sólo rack con sizeUcapturada/capacidad; dose/endDevice sólo sala con sizeUphysicalNULL. Todos los grupos/puertos conservan atributos declarados y reciben UUIDs nuevos; **estadofree, wattsNULL, propiedades{} y cero conexiones**. Deviceproperties sólo icono, color solicitado, familia técnica normalizada y las cinco notas introducidas explícitamente por el usuario; no propaga el UUID de una plantilla privada a lectores del inventario. Un único commit/operación/auditoría/revisión del cliente. La acción `inventory.device.createFromPrivateTemplate` sí aparece en el canal de avisos con actor/revisión/recurso; no contiene el blueprint privado.

Captura/desactivación usan journal personal terminal independiente. Digest incluye familia, Systemhaus, propietario, contexto cliente original, intención normalizada y revisión personal original. Replay exacto se resuelve antes de leer equipo fuente/plantilla actual, incluso si ya se borró la fuente o se desactivó la plantilla. Otra intención/revisión/contexto con igual clave:409request_id_reused. Consulta en otro contexto:404. Otra sesión del mismo actor permite recuperación con permisos actuales; otro actor no ve la operación. Outerrevision/ETag de status/cancel son actuales, recibo interno histórico; refrescar listado después de confirmación.

Cancelación de petición no registrada acepta intención/revisión originales obsoletas sin consultar fuente/plantilla; registra fence durable+auditoría, sin cambiar colección/revisión. Comando tardío409operation_cancelled. Cancelar committed devuelve recibo original, no deshace. notRecorded no es fence. No duplicar auditoría al reintentar. Retención indefinida de fences hasta protocolo explícito de vencimiento; no se afirma purga30d.

Bloqueos: operación personal→clienteSHARE→sesión/permisos→agregado personal exclusivo; lectura usa clienteSHARE→sesión→agregado compartido. La creación de inventario usa operación existente→clienteUPDATE→sesión→agregado personal compartido. Cliente precede siempre al agregado, evitando inversión entre captura y creación. Sesión/grants actuales se revalidan tras esperas y antes del commit. Fallos revierten definición/estado/journal/auditoría/revisión conjuntamente; excepción23503/23505/23514 devuelve409templates_conflict, no éxito.

## Verificación y límites

Pruebas nativas del autor ejecutadas17.10.2026 en Windows11(10.0.26300), SDK10.0.401/Python3.12.3/PostgreSQL17.11, sobre pareja173congelada y baseline158esquema8:7focos de `development/server/tests/test_private_device_templates.py` en bases nuevas. [Cierre del backend y comandos](../evidence/s1-20261017/quince-tandas-159-173/backend/CIERRE.md).

PG01:7ejecuciones,6PASS+1FAIL de arnés,74.945s de unittest/90.093s total. El último assert06 buscaba la subcadena `definition` y confundió metadata autorizada `definitionSha256/definitionVersion` con la configuración completa. Corregido sólo a metadata exacta y claves prohibidas recursivas; PG02 repite únicamente06:PASS6.269s/15.516s total, misma pareja, sin recompilar. Se conserva el fallo/log/hashes original.

Autorrevisión posterior encontró que la rama de revocación de creación de03 usaba una plantilla de otro propietario, que ya habría producido404 sin revocación. Las restantes ramas03eran válidas; esa rama inicial se considera parcial, incluidas reproducciones independientes anteriores. Endurecida la precondición con plantillaPROPIA accesible/activa, una operación previa propia conservada y ausencia de la operación de creación tras revocar. PG03 repite únicamente03:PASS26.456s/33.657s total. La revisión independiente contrasta estáticamente este cambio sin afirmar una nueva ejecución independiente de03endurecido. No cambios C#/SQL/build por ambos ajustes de arnés.

Cobertura final de siete focos: migración8→9 con todas las filas/historia previas, inventario/favoritos/cuentas/grupos/cables poblados conservados y tres tablas nuevas vacías; captura/GETsinDML/Unicode/bytesinmutables; autorización/CSRF/validación/revocación/expiración tras espera; replay/cancelación/conflictos distintos/tombstones; instanciación de los tres kinds/UUIDdisjuntos/reinicio de estado y propiedades; concurrencia/rollback/auditoría/avisos con lector; límites128activos/32grupos/1MiB/revisiónmáxima y BASE/favoritos independientes. Combinaciones recibidas `rj45+true` y `rj45_poe+false` capturadas e instanciadas sin normalización; PoE ajeno aRJ45 rechazado por SQL/API. PG05 comprueba familia storage y rawfaceAUTO con nombre nuevoPDU; la verificación física visible pertenece al recorrido GUI, no se infiere de esta prueba de filas.

Todos los resultados nativos registran fuentes/distribución/baseline sin cambios y procesos APP/PG propios cerrados. Cero acceso al QA real por el autor backend; compilaciones y revisiones distintas se atribuyen al coordinador/revisor, no a estas ejecuciones. El cierre general registra los resultados GUI/Windows/revisión y sólo después podrá autorizar una copia Windows nueva con recuperación8. No es instalador completo, rollback posterior al QA, backup de desastre ni adopción de Wascar.
