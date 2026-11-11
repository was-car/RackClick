# Revisión independiente · informes y contexto del rack

30.10.2026. Revisión UX acotada y distinta de la implementación. Se parte de `racks-first`; no se editó producto, QA, VM, ledger, continuidad ni GitHub.

**Dictamen: favorable para esta tanda de presentación/contexto.** Sin hallazgos P1/P2 confirmados en el cambio revisado. No acredita todos los formatos, permisos, accesibilidad ni la entrega instalada.

## Contraste independiente

- Comparé los tres exportadores con sus copias anteriores: el tramo íntegro de `run` y `download` es idéntico. Sus claves de actor/cliente/filtro, generaciones, efectos de limpieza, permisos y reintentos no se modifican. `InventoryPanel` sólo añade las props de contexto; al retirarlas, coincide con su copia previa.
- El contexto se busca dentro de `project.racks`, y SVG normaliza la cara a frontal/trasera. La primera apertura propone el rack únicamente con selección vacía; `contextInitialized` impide reaplicarlo al reabrir. No existe un efecto que sobrescriba campos al cambiar el rack visible.
- Después de esa primera apertura, adoptar el rack/cara es una acción explícita. Sus botones se bloquean con `locked`, igual que los selectores existentes. Cambiar el contexto visible no altera la clave de una operación pendiente o confirmada; adoptar explícitamente otro filtro sí utiliza la invalidación previa del componente.
- `ReportTechnicalDetails` contiene revisión, ID de solicitud y SHA. Los estados pendiente/error, comprobación, reintento y descarga permanecen fuera del desplegable de metadatos. No se añade un cierre externo que permita esconder una operación incierta ni se cambian las claves de montaje de exportadores.
- El CSS anterior se conserva. Los nuevos estilos son locales, permiten envolver texto y dan al resumen un área de al menos 44 px y foco visible. Las tres etiquetas nuevas están disponibles en EN/DE/ES; nombres y datos de inventario continúan como texto React.

## Evidencia funcional y visual leída

Inspeccioné las capturas reales anteriores y nuevas de escritorio y móvil de 390 px. La selección inicial refleja rack/cara, «Detalles técnicos» queda cerrado inicialmente y se conserva el diseño RC9. Las advertencias de formato siguen identificando XLS como HTML, sin presentarlo como XLSX.

Leí `browser-original/result.json` y `after/browser.json`, ejecutados por el coordinador en Windows/Edge 156 con PostgreSQL real: **PASS**, 10 clientes, 5408 puertos y 10 tablas de inventario iguales. El foco registra:

- Primera apertura de los tres formularios, incluido SVG trasero.
- Selección vaciada manualmente conservada al cerrar/reabrir y ámbito cliente de imprimible sin sobreescritura.
- Detalles nativos por teclado; controles de pendiente/error fuera de metadatos cerrados.
- Cambio real del rack visible durante una petición incierta sin alterar ID, cara ni ámbito; adopción bloqueada, reintento del mismo ID y confirmación.
- Adopción explícita posterior que invalida la confirmación anterior; imprimible y XLS HTML confirmados por servidor.
- EN/DE/ES, 390 px sin desbordamiento, recarga y otra sesión, sin excepciones JS.

No ejecuté otra suite ni otro laboratorio: respeté el ensayo concurrente y el gasto moderado. El build y los resultados de 37/801 pruebas son resultados comunicados por el coordinador, no ejecuciones del revisor. La regresión histórica SVG seguía en curso al cerrar este documento; no se incluye aquí como pasada.

## Límites y observaciones

**P3, continuación visual:** los selectores y la línea de rack seleccionado todavía muestran rutas/UUID extensos. Esta tanda pliega metadatos de solicitud, no elimina toda información técnica de la interfaz. Se conserva esa desambiguación mientras se resuelve su presentación posterior.

No se midió lector de pantalla, Firefox/Safari ni todas las variantes de impresión/Office. Las guardas de autorización se contrastaron por código; el foco principal no sustituye una nueva matriz completa de roles. Mantener QA manual como preparado hasta identificar una candidata integrada disponible para Wascar.

## Archivos y trazabilidad

Consultados: `InventoryPanel.jsx`, `InventoryPrintExport.jsx`, `InventoryRackSvgExport.jsx`, `InventoryRc9ExcelExport.jsx`, `ReportTechnicalDetails.jsx`, `report-ui-words.ts`, `server.css`, sus copias previas y la investigación del lote. Símbolos: `togglePanel`, `useOpenRack`, `contextInitialized`, `ReportTechnicalDetails` y guardas `run`/`download`.

Evidencia propia: [REVISION-ESTATICA.json](../evidence/s1-20261030/report-tools/REVISION-ESTATICA.json), con hashes, comparación de funciones y hashes de los resultados leídos. No se asignan puntos de cierre por esta revisión.

## Adenda final · regresión SVG y fixtures

Leí la regresión histórica terminada: `svg-regression-final/fixture.json` registra **PASS**, salida de navegador 0; `browser.json` registra PASS y ninguna excepción JS. Son ejecuciones del coordinador. Incluye tres descargas SVG exactas, ambas caras, extremos fuera del rack, equipos plegados/búsqueda, respuestas perdidas, metadatos de cara incorrecta retenidos, permisos HTTP 403 y controles ausentes para lector/editor, otros actores, idiomas y 390 px. No ejecuté otra suite.

Se conserva el intento `svg-regression` con FAIL/salida1. Comparé el único cambio de línea de `browser-inventory-rack-svg.mjs`: la expectativa anterior asumía un selector vacío aun con rack abierto. Ahora exige primero la selección contextual y Generar habilitado; después vacía explícitamente el selector y vuelve a exigir Generar deshabilitado. Se mantienen el negativo y el resto del recorrido de generación, recuperación y descarga; no se cambia producto para satisfacer la prueba.

En el fixture de carrera `inventory-rack-svg.test.mjs`, el diff sólo añade la importación y el argumento `reportUiWords` al constructor de ensayo. Las aserciones permanecen idénticas. El coordinador registra 801 pruebas Node correctas; no se atribuyen al revisor.

Los siete hashes de producto de esta revisión permanecen iguales. El dictamen favorable se mantiene, con los límites ya indicados.
