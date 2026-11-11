# Informes HTML imprimibles · S1 · 17.10.2026

Grupo99–113. Tres formatos: informe **tabular** de rack, informe **tabular** del cliente completo y etiquetas de **racks**. Reutiliza la paleta, tablas y medidas de etiquetas RC9; no acredita la representación gráfica frontal SVG completa, logo/branding del cliente, técnico, PDF nativo, XLS o etiquetas de puertos/cables. No altera la GUI aprobada ni el HTML RC9 adoptado. Estado de compilación, pruebas nativas, revisión y disponibilidad real: evidencia del grupo, sin deducir éxito de este contrato.

`POST /api/v1/customers/{id}/reports/printable` requiere sesión, Origin/CSRF, `X-RackClick-Actor`, `Idempotency-Key` e `If-Match` de revisión fuente del cliente. JSON cerrado de exactamente **TRES** claves obligatorias:

```json
{"reportKind":"rack","language":"es","rackIds":["11111111-1111-1111-1111-111111111111"]}
```

- `reportKind`: `rack`, `client`, `rackLabels`; `language`: `en`, `de`, `es`.
- `rack`: exactamente un UUID. `client`: array vacío, todo el cliente, máximo20racks; no filtra ni trunca. `rackLabels`:1..64UUID distintos del mismo cliente.
- UUID D no vacío, cadenas sin otras formas; mayúsculas permitidas en entrada, salida y digest normalizados a minúsculas y orden ordinal por UUID. Ordenar la misma selección no cambia la petición idempotente; los duplicados, también con distinta caja, son inválidos. IDs ajenos/inexistentes404.
- Claves extra, ausentes o duplicadas, enums/tipos/cardinalidad inválidos422 `request_invalid`. Revisión ausente428, formato inválido422, nueva petición obsoleta412; actor/CSRF/Origin según frontera vigente. Cuerpo máximo16KiB según frontera general.

Resultado200 exacto, ETag de la revisión **fuente**:

```text
{kind:'report',customerId,revision,requestId,operationId,
 report:{reportKind,language,rackIds,filename,
 contentType:'text/html; charset=utf-8',encoding:'utf-8',
 templateVersion:'rackclick-print-v1',rowCount,byteLength,sha256,contentBase64}}
```

Nombre ASCII `rackclick-{rack|client|rackLabels}-{customerUUID}-r{revision}-{language}.html`; ningún nombre de usuario se interpola en cabeceras o filename. HTML UTF‑8 sin BOM, máximo4194304bytes. `rowCount` cuenta exactamente las filas/secciones marcadas `data-report-row`, máximo10000 entre todas las tablas del artefacto; cabeceras no cuentan. Marcas: site/building/room/rack/device/group/port/connection/rack-label, cada una con `data-id` UUID. Exceso de bytes/filas o más de20racks en informe de cliente:422 `report_too_large`, sin resultado parcial, operación ni auditoría. Seleccionar más de64etiquetas es petición inválida422. SHA256 minúscula sobre los bytes exactos. Generar en servidor no equivale a que el navegador haya iniciado descarga o completado impresión.

El informe de rack incluye rack, equipos, grupos y puertos propios, más cables que lo tocan y ambos extremos completos aunque estén fuera. El de cliente incluye sitios/edificios/salas, racks, equipos de rack y de sala, grupos, puertos y todas las conexiones. Las etiquetas incluyen nombre, ruta real, ubicación, UUID, cliente/revisión fuente y recuentos documentados de equipos/cables que tocan el rack. Sin crear continuidad por una Dose, rack para objetos de sala, U para Dose/finales, ni mediciones de energía. Valores técnicos persistidos conservan su código; títulos/cabeceras fijos se traducen. Datos de usuario mantienen identidad y Unicode, escapados para HTML. `properties`, contraseñas, sesiones y JSON privado no se publican. Se omite Systemhaus, logo y técnico; no se exige una tercera capacidad ni se inventan esos datos.

HTML autónomo pasivo: `<!doctype html>`, `html lang`, meta `rackclick-template`, `body data-report-kind`; CSS fijo sin URLs o datos de usuario, fuentes locales. CSP mediante meta anterior al contenido:

```text
default-src 'none'; script-src 'none'; style-src 'unsafe-inline'; img-src 'none'; font-src 'none'; connect-src 'none'; object-src 'none'; frame-src 'none'; base-uri 'none'; form-action 'none'
```

Sin scripts, eventos, formularios, marcos, objetos, imágenes, descargas de fuentes ni recursos externos. No añade botón JavaScript dentro del archivo: el usuario emplea la impresión de su navegador. CSS de referencia: fondo blanco/texto#152b3c, cabecera verde#08794e, tabla12px/borde#a4b1bc/cabecera#edf2f5/padding7px; etiquetas336px, borde2px/radio8px/padding16px, dos columnas de impresión separadas16px; A4vertical/margen12mm. Escala física y opciones de la impresora requieren QA; no hay garantía de etiquetas adhesivas específicas.

Corrección de impresión FINAL02 (P2-113-PRINT): el listado de puertos usa cuatro columnas35%/30%/20%/15% tanto en pantalla como al imprimir: identidad de puerto/grupo; equipo y UUID de ubicación; atributos técnicos con títulos EN/DE/ES; conexiones y UUID remotos. Conserva etiquetas literales y todos los IDs, sin truncar, ocultar ni cambiar el número de filas. La jerarquía completa se presenta en la tabla de equipos, evitando repetirla en cada puerto. Las conexiones conservan el contexto completo independiente de ambos extremos. La candidata inicial y sus pruebas quedan preservadas; las medidas reales de páginas de FINAL02 y su revisión se acreditan exclusivamente en evidencia, no por esta descripción de fuentes.

`GET /api/v1/customers/{id}/reports/printable/operations/{requestId}` devuelve `{state:'committed'|'notRecorded',customerId,requestId,operation:resultado|null}` sólo para actor original/Systemhaus/cliente/familiaHTML. Exige **ahora** `inventory.read` y `reports.export`, incluso para claves desconocidas. Ausencia read404, export403, sesión401. Clave propia no registrada: notRecorded; actor distinto no revela operación. Cliente/formato/familia equivocados404 sin contenido. notRecorded no es cancelación; no existe endpoint nuevo de cancelación.

Igual cuerpo normalizado/ruta/actor/revisión/clave devuelve los bytes históricos completos después de cambios o reinicio. Otra revisión/carga/familia con la misma clave409 `request_id_reused`; nueva clave obsoleta412. Locks y transacción: advisory por casa/actor/clave, customer FOR SHARE, sesión/read/export después de esperas y antes del commit. Nombre del cliente se lee bajo ese bloqueo y autorización. Snapshot autorizado y proyección privada común con vistas/CSV. Inventario y revisiones customer/Systemhaus permanecen intactos. `operation.result_json` conserva el artefacto; auditoría en la misma transacción. Fallo de constraint409 `report_conflict`; DB503 según frontera. Retención30días sigue pendiente; la memoria del snapshot no acredita escala masiva.

Auditoría `reports.printable.generate`, resource_id=customerId, before_json SQLNULL; after_json exclusivamente customerId/sourceRevision/reportKind/language/rackIds/rowCount/byteLength/sha256/templateVersion. Sin HTML/base64 ni campo `revision` interpretado como cambio de inventario; sin contexto administrativo artificial.

CSV conserva rutas/DTO/bytes. Su lector histórico valida constantes CSV y tipos ports/connections; el nuevo valida constantes HTML y tipos nuevos. GET de familia cruzada404; POST con clave cruzada409. Ambos mantienen `kind=report`, por lo que `PostgresStore.RejectReportOperation` ya bloquea recuperación/replay/cancelación genéricos sin ampliar su bypass. SQL001–007/esquema7, catálogo9 y bootstrap no cambian; `reports.export` se concede explícitamente, sin grants retroactivos.

Implementación: `InventoryPrintableReports.GeneratePrintableReport/PrintableReportStatus/ParsePrintableFilter/BuildPrintableReport/StoredPrintableReport`, `InventoryReports.StoredReport`, dos rutas y OpenAPI parcial. Runner `test_inventory_printable_reports.py` requiere `--dll --frontend --evidence --case` explícitos; siete focos máximos, laboratorios PostgreSQL/roles/bases nuevos y artefactos congelados, sin build dentro del runner ni acceso al QA real. Salidas/sources/hashes/versiones/tiempos y pruebas realmente ejecutadas se registran en `evidence/s1-20261017/quince-tandas-99-113/backend/`.
