# Editor de configuración privada — contrato473–532

Estado: implementado, probado en Windows/PostgreSQL/Edge y revisado independientemente; QA restaurado532 disponible, aceptación manual pendiente. Nueva configuración se guarda como plantilla propia NUEVA, con UUID y definiciónV1 inmutables. No se actualizan bytes/hash/versión ni equipos de plantillas existentes. Sin compartir/publicar, SQL nueva, versiones fijadas nuevas ni rediseño RC9. Avance77/100 aproximado;60/60hitos internos cerrados, no60módulos ni60suites.

## API y persistencia

P=`/api/v1/customers/{customerId}/catalog/private-templates`.

POST `P/configurations`, DTO cerrado `{type:'create', name, definitionVersion:1, definition:<objetoV1>}`. El servidor obtiene actor/House/propietario de sesión, exige inventory.read+inventory.edit actuales del cliente, CSRF/actor, If-Match `templates-N` e Idempotency-Key. Mismos locks y revalidaciones actuales; revisión personal, fila nueva, operación y auditoría en un commit. No incrementa revisión del inventario/Systemhaus ni altera equipos, favoritos, BASE u otras plantillas. GETlista/detalle y creación de equipo desde la nueva plantilla siguen el contrato existente.

DefiniciónV1 reutiliza los campos/modelos existentes. Parser de entrada cerrado recursivo; rechaza duplicadas, campos extra, IDs/estado/cables/notas/properties y combinaciones imposibles. Reutilizar ValidateDefinition/DefinitionJson/DefinitionHash, con validación adicional para entrada nueva de GN únicos DENTRO de cada grupo (repetición entre grupos válida), claves de grupo únicas y límites/orden/tipos reales. No reinterpretar ni reserializar definiciones históricas. Canonicalizar solamente la definición nueva. Nombre/prefix/label/límites y PoE/AC según el dominio comprobado, no inventar restricciones o capacidades.

Máximo definición1MiB según contrato previo; sólo esta ruta admite cuerpo hasta1MiB+16KiB. Límite global16KiB permanece. Ajustar antes de leer/bindear JsonElement, sin subir global ni confiar sólo en Content-Length. Validar autoridad antes de materializar el cuerpo cuando sea posible. Registrar pruebas cuerpo grande, exceso y ruta legacy limitada.

No ampliar el record Intent serializado de capture/rename/deactivate: añadir nulls cambia sus digests. Nueva intención/familia de digest incluye nombre normalizado, versión y SHA256 de los bytesUTF8 del subobjeto definition EXACTAMENTE enviado (`GetRawText`, no hash canónico C#). El servidor calcula y valida ese hash; el resultado publica el hash canónico de la definición nueva guardada. JSON semánticamente igual pero con bytes distintos no es el mismo intento idempotente. No convertir un replay en otra plantilla/evento.

Recuperación: GET `P/operations/{key}` existente recupera recibo propio, con validación de tipo create. Nuevo POST `P/configurations/operations/{key}/cancel`, DTO cerrado `{type:'create',name,definitionVersion:1,inputDefinitionSha256}`; mismo digest que creación y fence transaccional aunque el cuerpo ya no esté en memoria. No acepta definición ni templateId en cancelación. Mantener estado committed/cancelled/notRecorded, conflictos de clave y política vigente de permisos/actor/propietario.

## GUI y diario privado

Editor tipado integrado en el diálogo de plantillas privadas RC9; semilla vacía coherente, BASE o propia activa que el usuario ya puede leer. Guardar como nueva plantilla; no JSON libre ni datos de implementación en el flujo del producto. Campos claros para tipo de objeto, tamaño/presupuesto/visual, grupos/prefijos/tipo y puertos con etiquetas/cara/AUTO/PoE/roles; tomar límites y formas reales de RC9 y del validador existente. Mostrar preview y requerir confirmación de reutilización de etiquetas antes de guardar. Identidad de grupo local y GN explícito, nunca gn como identidad global. Dosen/finales sin U/circuitos ficticios. Usuarios/nombres literales, textosEN/DE/ES y layoutRC9 conservados.

Diario NUEVO compacto, separado del legacy: contexto actor/cliente/key/revisión, nombre normalizado, versión y hashinput, sin definición/blueprint, contraseña o inventario en almacenamiento durable del navegador. Cuerpo exacto sólo en memoria. Mientras se conserva, reintento exacto; después de recarga/cierre sólo consultar/cancelar, y rehacer borrador tras fence conocido. Explicar esta disponibilidad con texto honesto, sin éxito fantasma ni reenvío automático como nueva operación. Reautenticación sólo misma cuenta, abort/scope-generation y cierre conservadores; bloqueo de refresco/Click-Click mientras haya trabajo pendiente.

## Verificación y entrega del bloque

Pruebas Windows/PostgreSQL de persistencia/reinicio, originales y equipos intactos, owner/ámbitos/permisos tras espera/CSRF, límites/Unicode/IDs/tipos, idempotencia/cancel/replay/rollback/auditoría y digests legacy intactos. Node estricto y Edge con escritura→recarga→segunda sesión, pérdida de respuesta/consulta y recarga sin blueprint durable, idiomas/390px/Click-Click. Revisión independiente distinta del implementador.

Congelar una candidata532 con editor, XLSX397 y avisos472, SQL9 exacta. Integrarla con perfiles cerrados de paquete y actualizador compatible185→532, ensayados antes de seleccionar QA restaurado. Mantener datos/cuentas/claves/puerto52346 y resultados de Wascar; cambiar sólo artefactos de configuración, sin auth/SQL DML de aplicación en el QA real. Original185 retenido; no prometer rollback posterior a actividad. Si hay sesión/proceso ajeno o actividad inesperada, rechazar sin detenerlo/sobrescribirlo.

QA y paquete final requieren sus pruebas concretas. Añadir casos detallados y registrar disponibilidad REAL sólo tras selección verificada; no asignar Pass de Wascar. No publicar, adoptar ni declarar servidor final. Faltan compartición/publicación, funciones restantes y cierreWindows/QA según continuidad.

## Resultado del 18.10.2026

[Informe completo y atribución FINAL02/03](../evidence/s1-20261018/sesenta-tandas-473-532/CIERRE.md). Creación y recuperación probadas; legacy conserva digest y definiciones exactas. El único cambio de producto02→03 es ancho mínimo620px de la tabla de preview con scroll contenido; servidor idéntico. GuíasQA66–68 con ubicaciones y botones exactos; sin Pass de Wascar. Paquete532 y selección compatible confirmados; SQL9 y dependencias fijadas intactas.
