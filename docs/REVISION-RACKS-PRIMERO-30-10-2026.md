# Revisión independiente · racks primero

30.10.2026 · Revisor UX distinto del implementador. Alcance: presentación de inventario de la tanda `racks-first`, sin modificar producto, VM, QA, backend, catálogo QA ni ledger.

**Dictamen: favorable para la tanda de presentación.** No encontré un hallazgo P1/P2 confirmado en los cambios revisados. No acredita instalación, adopción ni paridad completa RC9/RC10.

## Contraste realizado por el revisor

- Leí las instrucciones vigentes, el briefing, el perfil UX y las observaciones de Wascar sobre racks e informes. Comparé los cuatro archivos de producto con la copia anterior conservada por el coordinador.
- En `InventoryPanel`, la vista física/tarjetas precede ahora a PoE e informes. La jerarquía conserva sus nodos montados y se abre al gestionar infraestructura o navegar a sede, edificio o sala. Los accesos nuevos desplazan y enfocan secciones identificadas por cliente.
- Contrasté las invocaciones de `InventoryPrintExport`, `InventoryRackSvgExport`, `InventoryRc9ExcelExport`, `IntegratedPhysicalRack`, `IntegratedInspector`, `OperationDialog` y `ClientChangeNotice`: son idénticas a las anteriores, incluidas claves, permisos, bloqueos y callbacks. Los exportadores no se colocan dentro de un desplegable externo ni se desmontan al usar los accesos.
- En `PoeBudgetSummary`, el cálculo sigue usando `poeBudget` con los mismos dispositivos/puertos; los artículos y sus identidades se conservan. El resumen nativo muestra el exceso y los datos incompletos incluso cerrado. No hay formulario ni operación pendiente dentro de este desplegable de lectura.
- El CSS anterior se conserva íntegro. Los nuevos selectores se limitan a jerarquía, PoE y accesos secundarios. EN/DE/ES tienen las dos etiquetas nuevas sin traducir nombres del inventario.
- Inspeccioné capturas reales antes/después de escritorio, móvil de 390 px, el primer fallo y la recarga final. El escritorio deja de empezar con páginas de PoE: muestra las tarjetas de racks con el mismo diseño RC9. En móvil aparecen el icono y título del primer rack en la primera pantalla.

## Resultado funcional leído, ejecutado por el coordinador

`browser-original-2/result.json` y `after/browser.json` registran PASS en Windows/Edge 156 con PostgreSQL real: 10 clientes, 5408 puertos y las 10 tablas de inventario iguales. Constan apertura por teclado, foco de ida/vuelta, selección Click-Click y formulario de informe conservados, error/petición incierta visible y reintento del mismo ID, apertura de jerarquía antes de enfocar, recarga y otra sesión. No hay excepciones JS registradas.

El primer intento falló por timeout al despachar Enter mediante CDP. Lo inspeccioné como FAIL y se conserva. El coordinador corrigió el foco/despacho de teclado del ensayo y la repetición pasó; los cuatro hashes de producto revisados no cambiaron. No se sustituye el negativo por una afirmación de éxito retrospectiva.

No repetí navegador, PostgreSQL ni suites: respeté el ensayo concurrente y la preferencia de gasto moderado. Las 37 pruebas de build y las 801 unitarias fueron comunicadas por el coordinador; no son ejecuciones mías.

## Observaciones y límites

- **P3, mejora posterior:** la cabecera y toolbar aún ocupan bastante altura en móvil. Esta tanda coloca el primer rack en pantalla, pero no completa la simplificación general de herramientas ni la administración visual solicitada.
- La inspección de capturas no equivale a una prueba con lector de pantalla. No comprobé Firefox/Safari, temas adicionales, despliegue instalado ni MFA real en este laboratorio.
- El cliente original más cargado y la conservación de datos están cubiertos por el foco leído; no representan QA completa de todos los clientes/modelos.
- Mantener el caso manual como preparado hasta identificar una candidata integrada disponible para Wascar. El coordinador conserva la responsabilidad del catálogo QA, continuidad y métrica; esta revisión no asigna puntos.

## Archivos y evidencia

Producto: `development/frontend/src/InventoryPanel.jsx`, `PoeBudgetSummary.jsx`, `server.css`, `inventory-layout-words.ts`. Símbolos principales: `InventoryPanel`, `showHierarchy`, `focusSection`, `PoeBudgetSummary`, `inventoryLayoutWords`.

Evidencia propia: [REVISION-ESTATICA.json](../evidence/s1-20261030/racks-first/REVISION-ESTATICA.json), con hashes y contraste de siete invocaciones. Las capturas y salidas crudas del ensayo permanecen privadas bajo el directorio de trabajo indicado por `.local/racks-first-current.txt`.
