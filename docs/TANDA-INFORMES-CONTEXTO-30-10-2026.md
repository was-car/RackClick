# Tanda · informes con contexto del rack

30.10.2026. Desarrollo probado y revisado en laboratorio. Aún no está integrado en la candidata 10 de Wascar; se conservan su instalación, inventario y MFA.

## Comportamiento

- En la **primera apertura** de Informes e impresión, SVG y XLS HTML RC9 se propone el rack que está abierto. SVG toma también la cara visible.
- Una elección manual, incluso dejar vacío el rack o elegir el informe de cliente completo, permanece al cerrar y abrir el formulario. No se vuelve a rellenar automáticamente.
- Después de esa primera apertura, adoptar otro rack es explícito: **Usar el rack abierto** o **Usar el rack y la cara visibles**. El botón se bloquea mientras el informe está ocupado o pendiente. Navegar a otro rack no cambia una solicitud en curso.
- Revisión, ID de solicitud y SHA256 quedan bajo **Detalles técnicos**, accesible también por teclado. Pendientes, errores, consultar/reintentar, filas y descarga permanecen fuera del panel técnico.
- Al cambiar explícitamente el alcance se retira la confirmación anterior; hay que generar el nuevo resultado. Se mantienen la comprobación del servidor, los permisos y la identidad de cada solicitud.

Los componentes permanecen montados. Las funciones de transporte, recuperación y descarga son idénticas a la tanda anterior; no se modifican backend, SQL, MFA, dependencias o versión React. La [investigación previa](../evidence/s1-20261030/report-tools/INVESTIGACION-PREVIA.md) explica por qué se conservó el contexto en lugar de sincronizarlo con cada navegación.

## Resultado comprobado

- Build privado y 37 pruebas del adaptador correctos; **801 unidades frontend correctas**.
- Edge y PostgreSQL 17.11 con los **10 clientes y 5408 puertos originales**: propuesta inicial de los tres formularios, cara SVG, opciones manuales conservadas, teclado, solicitud incierta, cambio de rack durante el pendiente, reintento con el mismo ID y confirmación.
- Informes imprimible y XLS HTML también confirmados por servidor; idiomas EN/DE/ES, ventana de 390 px, recarga y sesión separada correctos. Las diez tablas de inventario permanecen iguales.
- Regresión SVG existente final correcta: descargas reales, ambas caras, validación de contenido, solicitudes recuperadas, permisos y persistencia. No se declaran ensayos Windows/VM nuevos por reutilizar el servidor ya compilado.
- [Revisión independiente favorable](REVISION-INFORMES-CONTEXTO-30-10-2026.md), con fuente y capturas contrastadas. El revisor no implementó ni repitió el laboratorio.

Se conservan dos fallos de fixtures y su corrección: el test de carrera necesitaba recibir el nuevo diccionario de presentación; la regresión SVG esperaba un selector vacío aun con rack abierto. Se mantuvieron todas las aserciones de carrera y el negativo de selección vacía, ahora comprobado tras limpiar explícitamente el campo. Una copia privada inicial omitió la entrada de referencia RC9: se repuso sin alterar sus bytes antes del build final. No se modificó producto para ocultar esos fallos.

## Alcance restante

REQ-UX-03 avanza en tres exportadores; quedan integrar una candidata, simplificar rutas/UUID extensos y tratar el resto de controles/formatos. Se conservan los avisos de formato: XLS HTML RC9 no se presenta como XLSX, PDF nativo ni backup.

[QA-135 para Wascar](QA-INFORMES-CONTEXTO-WASCAR.md) está preparado y marcado no disponible hasta la integración; los 134 casos previos y sus resultados se conservan. Las guías HTML se regeneran. El índice de cierre restante permanece **9,76/100**, sin cambiar base/pesos ni acreditar todo P-07 o P-11 por este foco.
