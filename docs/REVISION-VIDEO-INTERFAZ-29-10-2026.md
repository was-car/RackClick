# Revisión de la grabación de interfaz de Wascar

29.10.2026. Fuente: `C:\Users\w.p\Videos\Aufzeichnung 2026-10-29 224943.mp4`, duración2min46s. Revisión local de imágenes y explicación de Wascar; no se modificó código de aplicación, instalación, base, cuentas, MFA ni VM.

## Qué muestra y pide Wascar

La comparación confirma diferencias de presentación entre el servidor y la demo mostrada al final. Wascar pide que el rack aparezca arriba, que no haya que desplazarse por páginas de información para llegar a él y que informes/exportaciones se manejen con la claridad que muestra en la demo. Es una observación de QA visual, no aceptación final de toda la interfaz.

| Tiempo aproximado | Observación de la grabación |
|---|---|
| 00:00–00:32 | Resúmenes de consumo/PoE por equipo ocupan gran parte de la página; para llegar al rack y a otras acciones se requiere mucho desplazamiento. El rack y sus puertos sí llegan a mostrarse. |
| 00:32–01:12 | Gestión de infraestructura e informes aparecen como bloques extensos. Los selectores exponen UUID completos y se muestran revisiones, hashes y explicaciones técnicas en el recorrido principal. |
| 00:40–01:52 | Se usan controles de generación/descarga XLS y SVG. El SVG descargado se llega a visualizar; esto no prueba todas las exportaciones ni un informe completo en PDF. |
| 02:08–02:46 | La demo presenta tarjetas de clientes/racks, barra compacta de acciones, vista física y un informe legible. Se ven opciones de PDF, XLS, PNG y otras acciones que Wascar usa como referencia de experiencia. Ver los botones no equivale a haber ensayado cada formato. |

La página externa no accesible dentro de la VM es distinta del servidor RackClick que sigue abierto. Wascar señala en la grabación que esa VM no tiene Internet; no se diagnostica caída del servicio por ese tramo.

Se muestran clientes/racks distintos en el servidor y la demo. La comparación sirve para valorar distribución y recorrido; no demuestra igualdad o pérdida de inventario entre ambos conjuntos.

## Causa localizada en el código actual

En `development/frontend/src/InventoryPanel.jsx`, el render coloca `PoeBudgetSummary`, `InventoryPrintExport`, `InventoryRackSvgExport` e `InventoryRc9ExcelExport` antes del bloque que contiene la jerarquía/tarjetas o el rack seleccionado.

`PoeBudgetSummary.jsx` recorre todos los equipos del cliente cuando no hay rack seleccionado. La combinación de ese contenido y su posición explica el desplazamiento observado. Esto es evidencia de orden de presentación, no de pérdida de datos.

El componente `InventoryPrintExport.jsx` ya contempla informes de rack/cliente/etiquetas. Por eso no se declara que falte toda la lógica de informes: hay que hacerla visible y utilizable. El control XLS actual se identifica como **HTML RC9**, no un XLSX nativo; no anunciar otro formato por cambiar el nombre del botón.

## Corrección que debe seguir

1. **Racks al principio.** Al entrar al cliente, tarjetas y acceso a racks visibles antes de resúmenes extensos. Al seleccionar un rack, mostrar inmediatamente su título, frontal/trasera y vista física.
2. **Información secundaria plegable.** PoE/energía, detalles del inventario y gestión de sitios/edificios/salas en secciones compactas. No ocultar errores ni cambios pendientes dentro de un bloque cerrado.
3. **Barra de acciones ordenada.** Agrupar informes, impresión y exportaciones cerca del rack; aprovechar la selección actual y evitar formularios repetidos extendidos por la pantalla.
4. **Informes claros.** Facilitar el informe del rack/cliente, su vista previa e impresión/PDF. Revisar cada formato visible y sus límites antes de anunciarlo como operativo.
5. **Detalle técnico bajo demanda.** Mantener los IDs reales, revisiones, autorización y confirmación del servidor; presentar nombres/rutas comprensibles y relegar los datos técnicos extensos a una sección de detalles.

Conservar Click-Click, puertos/cables, frontal/trasera, idiomas, datos restaurados y MFA. La demo del vídeo indica **v0.9.0-rc10**; es material comparativo. La referencia adoptada del proyecto sigue siendo RC9: no se incorpora otra versión ni su almacenamiento offline de forma automática.

## Aceptación de la corrección

- Abrir un cliente con los datos originales y localizar sus racks sin atravesar listas de equipos/PoE.
- Seleccionar un rack desde las tarjetas y desde la navegación izquierda; vista física accesible inmediatamente en ambos casos.
- Desplegar/cerrar información secundaria sin perder selección, borradores, alertas o contexto.
- Abrir informe/exportación del rack actual con una selección inicial correcta; comprobar cada descarga real y recargar.
- Comparar EN/DE/ES y tamaños de pantalla, con el mismo conjunto de datos y candidato identificados.
- Registrar QA visual de Wascar y revisión independiente antes de actualizar la instalación.

Estado: **revisión y requisitos registrados; corrección de código pendiente**. No se han instalado versiones nuevas ni repetido instalación/restauración. Índice de cierre restante9,76/100 sin incremento por esta revisión.
