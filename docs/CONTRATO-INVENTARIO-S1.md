# Inventario S1 — propuesta de modelo y comandos para el siguiente bloque

28.09.2026. Encargo del coordinador después del fundamento. Documento iniciado como diseño; **primer tramo implementado y compilado, verificación PostgreSQL/GUI de inventario en curso**. Conserva el alcance de `CONTRATO-SERVIDOR-v0.1.md`, la instrucción actual de Wascar y la GUI RC9. La revisión y pruebas del fundamento ya están separadas; este avance no implica adopción ni candidata completa.

## Base inspeccionada y diferencias conscientes

Fuente ensamblada leída: `development/frontend/rc9-reference/RackClick-v0.9.0-rc9-Adoptada-2026-09-28/evidence/integrated-source.jsx`, SHA256 `dda18f60915b0058a8d65329e04464599bb3b3d6e48532dc48efc213328fa7ad`. Es copia de trabajo del ZIP; no se modifica el HTML adoptado.

| Símbolos/líneas de esa fuente | Comportamiento que debe conservarse o trasladarse explícitamente |
|---|---|
| `irLocationKey`, `irLocations`, `IRInfrastructure`, 11–40 | Jerarquía visible cliente/sede/edificio/sala, asignación de rack, rechazo de borrar ubicación ocupada. Offline identifica por nombres; servidor lo sustituye por UUID sin fusionar homónimos. |
| `IRFaceEditor`, `irPortFace`, `irPoeEnabled`, `irPoeStats`, 42–46 | Cara explícita/automática sobre el mismo puerto; PoE de RJ45 y watts desconocidos distintos de cero. |
| `irMoveDevice`, 175–187; `moveDevToRack`, 2281–2296 | Mover conserva equipo, puertos y cables; local/cross-rack cambia según propietarios actuales. Destino del cliente y capacidad de rack revalidados. |
| `irPowerPairAllowed`, 326 | Alimentación solo con alimentación; no unir dos entradas o dos salidas declaradas. Roles sin especificar no inventan un circuito. |
| `PT`, `PS`, 399–417; `reconcilePorts`, 619–645; `mkP`, 648–651 | Tipos y estados RC9; edición conserva IDs/atributos de puertos retenidos. `gn` reinicia por grupo y no identifica un puerto. |
| `rc8ReconnectProject`, 2009–2017 | Reconexión conserva UUID y atributos del cable; valida ambos extremos, ocupación, cliente y estado antes de sustituir. |
| `getGroupColorForConn`, 2052 | Color elegido tiene prioridad sobre regla por grupos. |
| `addRack`, `saveRackEdit`, 2262–2277; `duplicateRack`, 2572–2582 | Alta/edición; duplicar remapea equipos/puertos/conexiones locales. No copia conexiones hacia racks externos. |
| `irRoomFor`, `dragReorder`, 2585–2608; `saveEdit`, 2649–2673 | Capacidad U, orden documental y reducción de puertos con confirmación del impacto. Orden de array no es una U física medida. |
| `batchPortStatus`, `batchPortPoe`, `batchPortColor`, 2710–2732 | D-009: rangos por `gn` pueden abarcar grupos distintos. Se conserva la operación visible, pero el contrato servidor exige IDs y grupo/tipo. |
| `allowNewPairs`, `onPort`, `doBulkConnect`, 2735–2852 | Click-Click, confirmación reserved, disabled/faulty impiden nuevas conexiones; lotes atómicos; cables existentes siguen inspeccionables. |

RC9 contiene la etiqueta `Label / Dose`, pero no una entidad relacional de toma de pared ni de dispositivo final en sala; su catálogo describe AP como un espacio documental de 1U. El servidor necesita representar ambos fuera del rack. Esa ampliación procede del requisito actual, no de una capacidad ya demostrada por RC9.

## Modelo propuesto

Todas las identidades nuevas son UUID y los nombres editables se conservan sin traducir. Las tablas de inventario llevan `systemhaus_id` y `customer_id`; claves alternativas/FK compuestas mantienen pertenencia hasta el puerto. No basta comprobar un UUID enviado por el navegador. Las extensiones JSON conocidas/desconocidas se preservan con límites de tamaño/tipo y nunca conceden autoridad.

| Tabla/entidad propuesta | Datos y relaciones principales |
|---|---|
| `site` | UUID, cliente, nombre, metadatos/extensiones. |
| `building` | UUID, cliente, `site_id` obligatorio y FK compuesta. |
| `room` | UUID, cliente, `building_id` obligatorio y FK compuesta. |
| `rack` | UUID, cliente, `room_id` opcional para legado sin asignar, nombre, texto libre `location`, `size_u`, extensiones. |
| `device` | UUID, cliente, `kind` = `rackEquipment`, `dose` o `endDevice`; nombre, preset/catálogo opcional, notas, modelo, serie, IP, firmware, icono/color, presupuesto PoE y extensiones. |
| Ubicación de `device` | `rackEquipment`: `rack_id` obligatorio, `room_id` directo nulo, altura U y orden documental. `dose`/`endDevice`: `room_id` obligatorio, `rack_id` nulo; sin U ficticia. CHECK de exclusión y FK compuestas. La sala de equipo en rack se deriva de su rack. |
| `port_group` | UUID estable, cliente/equipo, nombre/prefijo si existe, familia de conector y orden. No se identifica solo por tipo; dos grupos RJ45 pueden ser diferentes. |
| `port` | UUID, cliente/equipo/grupo coherentes; tipo RC9, `gn` documental, orden, etiqueta, estado, PoE, watts nullable, color, cara `auto/front/rear`, rol eléctrico `unspecified/inlet/outlet`, extensiones. |
| `connection` | UUID, cliente, nota, color explícito nullable, estado de patch compatible con RC9, datos originales/extensiones y fecha servidor. Sin copia autoritativa de nombres ni flags local/cross-rack. |
| `connection_endpoint` | Cliente, conexión, ordinal 0/1 y `port_id`; FK compuesta a conexión y puerto. Exactamente dos extremos al commit; no se conecta un puerto consigo mismo. |
| Mapeo legado/originales | Identidad del original y correspondencia estable `legacy ID → UUID` por entidad/cliente. Original exacto en staging; nunca resolver importación por coincidencia de nombres. |

Restricciones adicionales:

- `UNIQUE(customer_id, port_id)` en extremos impide doble ocupación normal; `UNIQUE(customer_id, connection_id, ordinal)` y CHECK 0/1, más constraint trigger diferido, garantizan dos extremos distintos al commit. Alternativa equivalente debe probar las mismas invariantes. Ningún extremo puede referir un puerto ajeno al cliente de la conexión.
- FK compuesta `(customer_id, device_id, group_id)` mantiene al puerto en un grupo del propio equipo. Los tipos permitidos proceden del catálogo RC9; `rj45` y `rj45_poe` comparten familia para no cambiar identidad/grupo al alternar PoE.
- Borrado de puerto/equipo con dependencias usa RESTRICT; el comando confirma y elimina expresamente los cables afectados. Una cascada oculta no sustituye la previsualización. Borrar una conexión sí puede eliminar sus propios extremos en la misma transacción.
- Altura y tamaño U enteros positivos para racks/equipos de rack; sumar capacidad bajo el lock de revisión del cliente. Orden estable y único por rack, actualizable sin posiciones intermedias duplicadas. No se inventa `physicalU` a partir del orden.
- Nombres vacíos heredados no crean sedes/edificios/salas ficticios. Legado parcial conserva texto original y rack sin asignar hasta mapeo explícito. Una toma o dispositivo final nuevo requiere sala real.

## Dosen y dispositivos finales

Una Dose es un objeto con identidad, sala, etiqueta y sus propios puertos explícitos. Un dispositivo final también pertenece a una sala y puede tener puertos de datos/PoE/alimentación según datos documentados. Ambos participan en selección y conexiones por UUID; no necesitan rack ficticio ni consumen U. Renombrarlos no cambia puertos o enlaces. Sus propiedades/tooltips usan la misma proyección autorizada que el equipo de rack.

**Incertidumbre que debe resolverse antes de modelar pasos internos:** el material recibido no define una toma pasante con entrada de cableado fijo y salida de latiguillo simultáneas, ni un modelo de terminal/empalme interno. El modelo de un puerto lógico y una ocupación conserva la regla RC9, pero no representa por sí solo toda la ruta patch panel → cable fijo → toma → latiguillo → dispositivo final sobre ese mismo puerto. No crear un segundo terminal porque se vea una cara trasera, ni almacenar dos cables en el mismo puerto para ocultar esa limitación.

El siguiente diseño de terminales/pasos internos necesita describir identidades y tipo de enlace explícitos, separación datos/AC, qué se selecciona con Click-Click y qué ruta puede afirmarse. Hasta fijarlo, se puede implementar jerarquía, objetos Dose/final, puertos y conexiones externas de una ocupación; no declarar cumplida la topología pasante completa. No bloquea el CRUD autorizado ni justifica quitar Dosen del alcance final.

## API y transacción por cliente

Rutas previstas por contrato: `GET /api/v1/customers/{id}/project` devuelve snapshot coherente `{customerId, revision, sites, buildings, rooms, racks, devices, portGroups, ports, connections}` con ETag; `POST /api/v1/customers/{id}/commands` recibe `{type,payload}` y devuelve `{customerId,revision,requestId,operationId,result}` confirmado tras commit. Son propuestas para el próximo bloque, todavía no endpoints implementados.

Comandos requieren cookie vigente, Origin, CSRF, If-Match de cliente, Idempotency-Key UUID y actor original. El encabezado `X-RackClick-Actor`, opcional en fundamento por compatibilidad, será obligatorio en la nueva ruta de comandos; la GUI ya lo envía. El servidor deriva Systemhaus/usuario de sesión, nunca del payload. Lectura requiere `inventory.read`; mutación requiere además la capacidad específica efectiva por grupos de usuarios/grupos de clientes. Recurso no visible →404; visible sin capacidad →403. Denegación por defecto.

Usar `customer.revision` como revisión agregada del inventario y metadatos de ese cliente, sin incrementar ni bloquear Systemhaus por cada cable. El alta de clientes/renombrado Systemhaus conserva su alcance global; el renombrado de cliente deberá coordinar la misma revisión local sin invertir el orden de locks. Pruebas deben demostrar que un lock de cliente A no bloquea la edición de B. No anunciar esta propiedad por disponer del diseño: hoy fundamento todavía usa lock Systemhaus.

Dentro de una transacción: bloquear fila de cliente, comprobar sesión/autorización vigente y ámbito de todos los IDs; buscar replay autorizado por actor/cliente/clave/digest; validar revisión y dominio; mutar; incrementar revisión una vez; escribir auditoría y resultado idempotente; commit; responder. Errores 428/412/409/422 conservan borrador, nunca sustituyen datos con un snapshot ciego. Un replay conserva el resultado original incluso con una revisión actual posterior; una clave con cuerpo/acción/cliente distintos devuelve 409. La coordinación de revocación administrativa necesita su propio protocolo y pruebas pendientes D-006.

## Catálogo de comandos propuesto

| Familia | Payload esencial y reglas |
|---|---|
| `site/building/room.create/update/delete`, `rack.assignRoom` | UUID padre/objeto explícitos; `inventory.edit`. Borrar ubicación ocupada devuelve impacto y exige reasignación previa; no borrar un árbol implícitamente. |
| `rack.create/update/duplicate/delete` | Nombre, sala opcional, tamaño y texto libre; duplicación remapea UUID de dispositivos/grupos/puertos/cables internos, opción explícita de incluir cables locales, jamás clona enlaces hacia objetos externos. Borrado requiere capacidad separada propuesta `inventory.delete` y confirmación del impacto. |
| `device.create/update/move/reorder/delete` | `kind`, placement, propiedades y IDs; capacidad y cliente de origen/destino comprobados. Mover conserva UUID/puertos/enlaces, local/cross se deriva de la ubicación actual. Datos de rack y sala no se mezclan por nombres. |
| `device.editPortGroups` | Grupos con `groupId`, familia/tipo, `retainedPortIds`, altas explícitas y `removedPortIds`; conserva atributos/cables de retenidos. Previsualización devuelve IDs de puertos/cables afectados, ligada a revisión y digest. Reducción exige aceptación exacta de ese impacto; nunca truncar por cantidad sin enumerarlo. |
| `ports.setStatus/setPoe/setWatts/setColor/setLabel/setFace/setPowerRole` | Para lotes: `deviceId`, `groupId`, `expectedType` o familia declarada, lista única `portIds`, valor. Rechazar ID ajeno, duplicado, grupo/tipo distinto o lote vacío; no omitir elementos silenciosamente. `gnFrom/gnTo` sirve solo para selección visual previa, nunca como selector del servidor. |
| `connections.create/createBatch` | Pares de UUID de puertos, atributos y `confirmedReservedPortIds`; cada extremo existe y pertenece al cliente, disponible, sin repetirse en el lote. Fallo de un par revierte todos. Click-Click sigue siendo dos selecciones; confirmación reserved separada del guardado. |
| `connections.reconnect` | UUID conexión, extremo que se conserva y puerto nuevo; verificar que el extremo aún coincide. Sustituir un extremo conservando UUID, nota, color y patch. Cancelar no manda comando; error/colisión conserva cable anterior. |
| `connections.update/disconnect` | UUID y campos permitidos; sin aceptar nombres/tipos/racks derivados como autoridad. Estado/color/nota no reconstruyen extremos. |
| `operations.compensate` | Operación propia, cliente y revisión actual; compensación autorizada condicionada a objetos/revisiones afectados. Sin restaurar historial/snapshot completo sobre trabajo de otro usuario. |

`inventory.delete` es nombre propuesto de capacidad, no concesión existente; debe incorporarse al catálogo/roles/migración y probarse antes de habilitar controles. Export/reportes/importación/catálogo/favoritos/preferencias conservan sus capacidades, ámbitos y bloques del contrato principal; no se eliminan por centrar este documento en inventario.

Estados permitidos RC9: `free`, `reserved`, `disabled`, `faulty`; ocupado se deriva de extremos, no de un segundo estado almacenado. Deshabilitar un puerto conectado conserva el cable documentado, permitiendo verlo/desconectarlo; bloquea nuevas conexiones. PoE solo RJ45, apagar preserva watts; desconocido `null` no equivale a 0. El editor RC9 limita watts documentados a 0–90 y rechaza no finitos; mantener esa regla de paridad sin presentarla como certificación eléctrica. Presupuesto PoE suma puertos elegibles habilitados y cuenta desconocidos; nunca watts AC. Cambiar rol de alimentación debe revalidar enlaces existentes. Para puertos no power, RC9 no implementa una matriz física completa de compatibilidad: no imponer una nueva por intuición ni prometer certificación de medio/transceptor.

## Casos que deben bloquear la integración de cada operación

1. Crear sitio/edificio/sala/rack/equipo, recargar y leer desde segundo usuario autorizado y después de reiniciar servicio; comprobar UUID, revisión y SQL. No localStorage maestro.
2. Homónimos de clientes/salas permanecen distintos; objeto conocido de otro cliente falla en lectura y escritura; grupos de clientes unen permisos sin conceder acceso global accidental.
3. Dos grupos con `gn=1` (incluso mismo tipo): lote solo cambia los UUID enumerados; grupo/tipo incorrecto revierte todo.
4. Editar grupo +2 conserva conexiones/watts/color/IDs; reducción sin confirmación/revisión actual no cambia nada; aceptación exacta elimina solo el impacto informado.
5. Dos escritores mismo puerto: un commit, otro conflicto; dos clientes bajo locks separados avanzan independientemente. Mismo UUID idempotente simultáneo: una operación/auditoría, mismo resultado.
6. Reconexión local↔cross-rack conserva cable/atributos; destino ocupado, deshabilitado, faulty, ajeno o reserved sin confirmar conserva enlace original.
7. Cambio de cara conserva una identidad/ocupación; PoE off conserva watts; AC no aparece en presupuesto PoE; roles incompatibles rechazan mutación sin datos parciales.
8. Dose y dispositivo final viven en sala sin U/rack ficticio; autorización y movimientos revalidan pertenencia. El caso de paso interno se mantiene pendiente explícito hasta resolver el modelo indicado.
9. Duplicado remapea todo UUID interno, no roba ni clona conexión externa; mover equipo actualiza tooltips/ruta derivada desde snapshot vigente.
10. Fallo forzado entre cambio y auditoría revierte datos/revisión/operación; replay tras respuesta perdida devuelve resultado original; reautenticación bajo otro actor no reenvía operación incierta.
11. Undo propio frente a edición ajena produce conflicto o compensación acotada; nunca restaura todo el cliente. Doble ocupación importada conserva original íntegro en staging sin commit parcial.
12. GUI RC9 mantiene frontal/trasera, Click-Click, confirmaciones, informes e idiomas EN/DE/ES; cadenas del usuario no se traducen; éxito solo tras respuesta servidor. QA visual y capturas nuevas separadas de evidencias históricas.

Orden de ejecución: migración versionada y tests de pertenencia/revisión → CRUD jerarquía → equipos/grupos/puertos → conexiones/reconexión/lotes → proyección/adaptador RC9 por cada tramo comprobado. Ningún paso es un instalador parcial para Wascar; la candidata final sigue incluyendo administración, instalación Windows reproducible, manual, evidencias y recuperación.

## Contrato operativo del primer tramo escrito

Fuentes: `InventoryStore.cs`, `InventoryDevices.cs`, `InventoryConnections.cs`, `InventoryImpact.cs`, `InventoryDuplicate.cs`, `InventoryJson.cs`, `OpenApiInventory.cs`; SQL aditiva `002-inventory.sql`. La cancelación durable proviene del trabajo separado del coordinador `OperationCancellation.cs` + SQL `003-operation-cancellation.sql`. `001-foundation.sql` permanece intacta. Bootstrap aplica las tres migraciones; `--migrate` comprueba digest y aplica solo pendientes en transacción, sin reinicializar datos. `/health/ready` exige esquema 3. Las versiones .NET/Npgsql permanecen fijadas.

El catálogo propuesto anterior se concreta agrupando acciones de puerto en `ports.update` y usando `device.editPortGroups`. Los nombres exactos y schemas están expuestos por `/api/v1/openapi.json` autenticado; no existen aliases ficticios `ports.set*`. Tampoco está implementado aún `operations.compensate`: undo colaborativo sigue pendiente, no equivale a cancelación de una petición no confirmada.

Snapshot `GET /api/v1/customers/{id}/project`, con ETag: `{customerId,revision,sites,buildings,rooms,racks,devices,portGroups,ports,connections}`. Cada colección conserva sus UUID. Campos específicos:

| Colección | Campos, además de `id` |
|---|---|
| sites | `name,properties` |
| buildings | `siteId,name,properties` |
| rooms | `buildingId,name,properties` |
| racks | `roomId` nullable, `name,location,sizeU,properties` |
| devices | `kind,rackId,roomId,name,sizeU,sortOrder,poeBudget,properties`; nullable cuando no corresponde, sin U ficticia en Dose/final. |
| portGroups | `deviceId,type,name,prefix,sortOrder`; `type` es familia (`rj45` engloba puertos rj45/rj45_poe). |
| ports | `deviceId,groupId,type,gn,sortOrder,label,status,poe,watts,color,face,powerRole,properties`. |
| connections | `fromPortId,toPortId,note,color,patch,createdAt,properties`; patch **texto** `none/planned/progress/done/tested`, proyección RC9 a `patchStatus`. |

`properties` conserva metadatos de usuario, por ejemplo `preset/icon/color/notes.{sn,ip,model,firmware,text}`; actualizaciones hacen merge recursivo para mantener claves desconocidas. Nunca sustituye los campos de identidad/propietario. Límite 8192 bytes por objeto properties y 16384 bytes por petición. Las notas de cable conservan espacios, CR/LF y tabuladores (2000 valores escalares); nombres siguen trim y límite 100. Caras no cambian identidad ni ocupación.

Todos los comandos usan `POST /api/v1/customers/{id}/commands`, `{type,payload}`, Origin/CSRF/cookie y tres cabeceras obligatorias: If-Match de cliente, Idempotency-Key UUID, X-RackClick-Actor del usuario original. Resultado 200 tras commit: `{customerId,revision,requestId,operationId,result:{resourceId,...}}`; `createdIds`, `changedIds` o `removedIds` describen el efecto cuando corresponde. El adaptador recarga el snapshot autorizado; no almacena inventario maestro paralelo.

| Tipo exacto | Payload operativo |
|---|---|
| site/building/room.create | `{name,properties?}` más `siteId` para edificio o `buildingId` para sala. |
| site/building/room.update | `{id,name?,properties?,siteId?/buildingId?}` según entidad. |
| site/building/room.delete | `{id}`; capacidad inventory.delete; FK impide borrar ubicación usada. |
| rack.create/update | Crear `{name,sizeU,roomId?,location?,properties?}`; actualizar `{id,...campos opcionales}`. |
| rack.assignRoom | `{id,roomId:null|UUID}`. |
| rack.duplicate | `{id,name?,includeConnections:boolean,confirmedReservedPortIds?:[]}`; IDs remapeados, solo enlaces internos. Puertos disabled/faulty impiden copiar sus cables; reserved exige confirmar los IDs originales afectados. |
| rack.delete / device.delete | `{id,confirmationToken}` obtenido con previsualización del mismo payload sin token. |
| device.create | `{kind,name,rackId?|roomId?,sizeU?,poeBudget?,properties?,portGroups:[{type,count,name?,prefix?}]}`; grupos y puertos se crean en la misma transacción, cada grupo 1–96 puertos. |
| device.update / device.move | Actualizar `{id,name?,sizeU?,poeBudget?,properties?}`; mover `{id,rackId}` o `{id,roomId}` conforme kind; no cambia kind por un rename. |
| device.reorder | `{rackId,deviceIds:[todos los IDs del rack en el orden deseado]}`; no omitir/duplicar otro equipo. |
| device.editPortGroups | `{deviceId,groups:[{id?,type,name?,prefix?,retainedPortIds:[],addCount}],removedPortIds:[],confirmationToken?}`. Lista deseada completa; retención por IDs del mismo grupo. Suma retained+add entre 1–96 por grupo, máximo 32 grupos. Token obligatorio si se quitan puertos/grupos. |
| ports.update | `{deviceId,groupId,groupType,portIds:[UUID],changes:{status?,poe?,watts?,color?,label?,face?,powerRole?,properties?}}`; lista única no vacía, máximo 256 IDs y validación exacta del grupo/familia. |
| connections.create | `{fromPortId,toPortId,note?,color?,patch?,properties?,confirmedReservedPortIds:[]}`. |
| connections.createBatch | `{pairs:[{fromPortId,toPortId,note?,color?,patch?,properties?}],confirmedReservedPortIds:[]}`; máximo 128 pares, sin repetir ningún extremo. |
| connections.reconnect | `{connectionId,keepPortId,newPortId,confirmedReservedPortIds:[]}`. |
| connections.update / disconnect | Actualizar `{connectionId,note?,color?,patch?,properties?}`; desconectar `{connectionId}`. |

Previsualización: `POST /customers/{id}/commands/preview`, mismo `{type,payload}`, actor/CSRF/If-Match, sin Idempotency-Key requerido. Solo `rack.delete`, `device.delete`, `device.editPortGroups`. Respuesta `{customerId,revision,impact:{rackIds,deviceIds,groupIds,portIds,connectionIds},confirmationToken}`. Commit añade ese token al mismo payload; todo se valida nuevamente. Revisión antigua 412; token ausente o no coincidente 409 `impact_confirmation_required`; ID externo 404; grupo/selector incorrecto 422. El token liga el actor, la revisión y el digest del payload/impacto, no concede permisos.

Recuperación de respuesta incierta: `GET /customers/{id}/operations/{requestId}` responde `committed` con `operation` original, `cancelled` con cancelación registrada o `notRecorded`. Este último **no** demuestra que una petición retrasada nunca llegará. Para resolverlo, `POST /customers/{id}/operations/{requestId}/cancel` recibe el comando original y If-Match **original**, actor/CSRF y Idempotency-Key idéntico al UUID de ruta. Bajo el mismo lock de clave devuelve commit existente o registra cancelación durable con auditoría; no modifica revisión de inventario. Un comando que llegue después se rechaza 409 `operation_cancelled`; clave con otro digest, 409 `request_id_reused`; header distinto de ruta, 422 `request_id_mismatch`. No borrar el diario del navegador antes de confirmar una de las dos respuestas terminales.

Locks: clave `(Systemhaus,actor,requestId)` compartida entre fundamento/inventario/cancelación, después fila de cliente para inventario. No hay lock Systemhaus en comandos de inventario. Tras esperas se revalida sesión con `clock_timestamp()` y se bloquean sesión/usuario con FOR SHARE; logout/desactivación posterior espera al commit y una sesión ya expirada o revocada se rechaza. Revocación administrativa de grupos/último administrador sigue perteneciendo a D-006; no se afirma resuelta por este control.

Evidencia del implementador: `evidence/s1-20260928/backend-inventory/`, compilación Windows y 76 casos puros de dominio correctos antes de iniciar arneses nativos. Las pruebas PostgreSQL, revisión y GUI de este tramo tienen otros responsables y se consignan en sus informes; no se convierten en PASS porque el código compile.
