# Informes CSV de inventario · S1 · 17.10.2026

Grupo84–98: descarga CSV de puertos y conexiones del cliente o de un rack concreto. No implementa HTML, etiquetas, transferencia, importación, XLS/JSON de intercambio ni paquete de campo. Las consultas en pantalla69–83 siguen requiriendo sólo inventory.read; descargar informes exige inventory.read Y reports.export vigentes en el cliente. Nueva capacidad cerrada añadida al catálogo existente y bootstrap de instalaciones NUEVAS; ninguna concesión automática ni SQL/DML contra instalaciones existentes. Wascar concede la capacidad explícitamente mediante su panel. security.manage global conserva su protección del último administrador, independiente del número de capacidades del catálogo.

## Petición y resultado exactos

`POST /api/v1/customers/{id}/reports/csv`, cookie vigente, Origin, X-RackClick-CSRF, X-RackClick-Actor obligatorio, Idempotency-Key y If-Match de la revisión del cliente. Cuerpo JSON cerrado con CINCO claves obligatorias:

```json
{"reportKind":"ports","query":"","status":"all","family":"all","rackId":null}
```

reportKind ports/connections; query hasta200 escalares Unicode, NFC+OrdinalIgnoreCase para comparar sin alterar salida. status all/free/reserved/disabled/faulty; family all/rj45/sfp/sfp28/qsfp/mgmt/console/power/usb_a/usb_c, derivado de InventoryRules.Family (rj45_poe→rj45). Para connections status y family deben ser all. Sin parámetros de paginación: se incluye la totalidad del filtro o se rechaza. Claves desconocidas, duplicadas, ausentes, tipos/enums inválidos422 request_invalid. rackId null significa todo el cliente; UUID D no vacío identifica rack del mismo cliente, ajeno/inexistente404. Puertos: sólo pertenecientes al rack; conexiones: al menos un extremo pertenece al rack, ambos extremos permanecen completos. Query conserva la semántica de las vistas en pantalla; no busca properties ni secretos.

Respuesta200 JSON, ETag de la revisión FUENTE, exactamente:

```text
{kind:'report',customerId,revision,requestId,operationId,
 report:{reportKind,query,status,family,rackId,filename,
 contentType:'text/csv; charset=utf-8',encoding:'utf-8-bom',
 csvValueEncoding:'spreadsheet-safe-apostrophe-v1',rowCount,byteLength,sha256,contentBase64}}
```

filename ASCII `rackclick-{ports|connections}-{customerUUID}-r{sourceRevision}.csv`; no nombres escritos por usuario en cabeceras HTTP o nombres de fichero. SHA256 hexadecimal minúscula sobre bytes exactos, incluido BOM. Máximo10000filas de datos y4194304bytes (4MiB) incluido BOM, cabecera y saltos: exceder devuelve422 report_too_large y no persiste resultado parcial. Ninguna revisión customer/Systemhaus ni fila de inventario cambia por generar el informe.

`GET /api/v1/customers/{id}/reports/operations/{requestId}` recupera sólo operación del actor original, en su Systemhaus/cliente, con inventory.read+reports.export vigentes incluso para claves desconocidas. Respuesta exacta `{state:'committed'|'notRecorded',customerId,requestId,operation:resultado|null}`. No inventa revisión actual ni considera notRecorded una cancelación. No hay endpoint de cancelación de informes, nuevo journal de inventario ni cancelación implícita al cerrar una vista.

Un reintento del POST con misma ruta/cuerpo/revisión/clave devuelve el resultado original completo, autorizado AHORA, aunque cambie posteriormente la revisión del inventario. Otra carga/revisión con la misma clave409 request_id_reused; petición NUEVA con revisión obsoleta412 revision_conflict. Sesión401 authentication_required; lectura ausente404 not_found; export ausente403 forbidden; formato If-Match422 revision_invalid, ausencia428 revision_required. Colisión/constraint transaccional409 report_conflict. Fallo de DB503 según frontera general. No se afirma descarga exitosa porque el servidor haya generado bytes.

## CSV versión1

BOM UTF-8 EF BB BF; separador coma; TODOS los campos, incluidas cabeceras, entre comillas dobles; comillas internas duplicadas RFC4180; CRLF al terminar cada registro, también el último. Notas con CR/LF permanecen dentro de su campo entre comillas. Nombres, notas y etiquetas no se traducen ni normalizan en la salida. null se representa por celda vacía, booleanos true/false, gn y revisión decimales invariantes, watts decimal invariant sin sumar AC/PoE. IDs fuente UUID D; listas de IDs separadas por punto y coma, orden de conexiones consistente. Orden de filas por UUID fuente.

Protección SELECTIVA `spreadsheet-safe-apostrophe-v1`: añadir exactamente un apóstrofo si el texto original empieza por apóstrofo, TAB, CR o LF, o si su primer carácter después de TrimStart es uno de `= + - @`. Una cadena que ya empieza por apóstrofo queda con DOS al principio. Los demás valores, incluidos vacío, nombres normales, UUID y números positivos, permanecen literales. Para invertir esta codificación de celda: quitar un apóstrofo sólo cuando la celda codificada empieza por apóstrofo; en otro caso conservarla. CSV no preserva la diferencia entre null y cadena vacía. No es importación ni roundtrip del inventario, ni garantía de comportamiento universal de Excel u otras hojas de cálculo.

Cabecera ports exacta (29columnas):

```text
customer_id,source_revision,port_id,device_id,device_name,device_kind,rack_id,rack_name,room_id,room_name,site_id,site_name,building_id,building_name,group_id,group_name,type,family,gn,label,status,face,poe,watts,color,power_role,connected,connection_ids,peer_port_ids
```

Cabecera connections exacta: siete columnas `customer_id,source_revision,connection_id,note,color,patch,cross_rack`, seguidas de las27columnas ports DESDE port_id hasta peer_port_ids con prefijo `from_`, y esas mismas27con prefijo `to_` (61columnas). cross_rack true/false sólo cuando ambos extremos tienen rack real; vacío si falta alguno. Dose/final conservan sala y ruta real, sin inventar rack ni paso/circuito interno. Rack legado sin sala conserva UUID/nombre de rack y contexto de sala vacío. gn nunca sustituye port_id/group_id/type como identidad.

## Persistencia, permisos y rutas alternativas

ReadCommitted, LockOperation compartido por casa/actor/request, customer FOR SHARE, sesión/read/export tras esperas; snapshot único y proyección privada común con vistas en pantalla, filtro de rack y sin paginación; CSV acotado y resultado durables en operation.result_json, auditoría en la misma transacción; última sesión/read/export antes de commit y retorno. Resultado durable permite recuperar bytes originales sin reconstruir un snapshot histórico. Sin DDL nuevo; el esquema7 y SQL001–007 permanecen iguales. Retención30días es objetivo contractual pendiente, no borrado programado implementado; almacenamiento de artefactos indefinido debe revisarse al cerrar operación/retención.

Auditoría `reports.csv.generate`, resource_id=customerId, before_json SQLNULL y after_json sólo metadata: customerId, sourceRevision, filtros, rowCount, byteLength, sha256, csvValueEncoding. Sin contenido/base64 ni campos `revision` que el feed de cambios interpretaría como mutación. Sin audit_context administrativo artificial ni evento/cambio de inventario.

PostgresStore.LockOperation rechaza404 un resultado con kind=report en rutas genéricas de inventario/fundamento/administración/cancelación/replay; sólo GenerateReport/ReportStatus usan allowReport=true y su autorización dual. Estados administrativos ya filtran JOINaudit+actionIN específicos y devuelven notRecorded sin contenido para requestIds de reportes; no se amplían por inercia. Compensación exige evidencia de mutación, incompatible con beforeNULL del reporte. Ninguna ruta genérica de inventario puede recuperar contentBase64 con inventory.read solamente.

Implementación: InventoryReports.GenerateReport/ReportStatus/ParseReportFilter/BuildReportCsv; PostgresStore.LockOperation/RejectReportOperation; InventoryReadViews.ProjectView con opciones privadas de reutilización sin alterar DTO/semántica de sus3GET; Infrastructure.Capabilities.ReportsExport/FoundationAdmin. AdminGrantWrites, AdminAuditAdministrativeDetail y OpenApiAdmin ya derivan catálogo/validación de FoundationAdmin y admiten la capacidad nueva sin duplicar lógica. Dos rutas y parcial OpenApiInventoryReports registrados. No se han concedido capacidades por nombre de grupo.

Pruebas nativas/artefactos/hashes/resultados en `evidence/s1-20261017/quince-tandas-84-98/backend/`; runner test_inventory_reports.py exige --dll --frontend --evidence --case explícitos, con7focos propios máximo. Revisión independiente por otro agente, GUI y QA de Wascar se registran por separado. Carga snapshot de cliente en memoria; salida acotada no certifica escala masiva ni instalador/candidata completa.
