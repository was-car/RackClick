# RC10 offline frente a RackClick servidor10

29.10.2026 · Auditoría funcional y técnica de sólo lectura.

**302 acciones del offline comparadas una por una con el servidor10:** 47 equivalentes, 122 adaptadas, 62 parciales y 71 ausentes en el recorrido comparado. No son porcentajes de producto ni 71 funciones que deban copiarse sin criterio.

- **[Abrir comparación visual con buscador y filtros](../COMPARACION-RC10-SERVIDOR.html)**
- [Las 302 comparaciones: propósito, acción, resultado, fuentes y trabajo pendiente](PARIDAD-RC10-MATRIZ-COMPLETA.md)
- [Plan completo por prioridades, con cada acción trazada](PLAN-PARIDAD-RC10-SERVIDOR.md)
- [CSV de la matriz](../evidence/s1-20261029/comparacion-rc10-servidor/MATRIZ-COMPLETA.csv) · [Funciones](../evidence/s1-20261029/comparacion-rc10-servidor/FUNCIONES-COMPLETAS.csv) · [Eventos](../evidence/s1-20261029/comparacion-rc10-servidor/ACCIONES-COMPLETAS.csv) · [Servidor](../evidence/s1-20261029/comparacion-rc10-servidor/SERVIDOR-COMPLETO.csv)

## Referencias fijadas

- Offline original: RackClick-v0.9.0-rc10-Offline.html, 976.987 bytes; SHA256 **241b49e49c2489d33615c0b648ade46a54a90bbd5d012d6a2d7b2215b8d668b0**. Original y copia conservados intactos.
- Servidor: instalador10 / esquema15. DLL **b7a2b50f2491245af8ea07d9880a3fc6872de607303d621336ef0a928fa83e21**; manifiesto **294b61577ed7aa8fe68ddb1ecd6c4f11a20b4f03935c11a22404009aec6a00fb**.
- Los 18 archivos del frontend coinciden byte a byte con los del paquete10; 213 fuentes congeladas y sus hashes sustentan las citas. Las fuentes de desarrollo posteriores no se cuentan como instaladas.
- C incluye el MFA administrativo probado por Wascar y el Full Backup original cargado anteriormente. Esta auditoría no se conectó a C ni modificó VM, instalación, base o claves.

## Estados

- **Equivalente:** resultado funcional comparable localizado.
- **Adaptada al servidor:** conserva el propósito con otra persistencia, autorización o recorrido.
- **Parcial:** existe una parte, pero falta un control, dato, resultado o acceso.
- **Ausente:** no se localizó ese recorrido en la candidata fijada; una herramienta externa no satisface automáticamente la misma GUI.

Lectura de fuente no significa prueba de todos los clics. Las filas llevan símbolos y líneas; las ejecuciones dinámicas tienen sus propios casos y límites.

## Comparación por áreas

| Área | Acciones | Equivalentes | Adaptadas | Parciales | Ausentes |
|---|---:|---:|---:|---:|---:|
| Navegación | 9 | 3 | 4 | 2 | 0 |
| Ámbito | 3 | 0 | 1 | 2 | 0 |
| Systemhaus e infraestructura | 15 | 0 | 13 | 2 | 0 |
| Cliente y proyecto | 7 | 0 | 1 | 1 | 5 |
| Rack | 20 | 7 | 8 | 1 | 4 |
| Equipo | 38 | 14 | 15 | 6 | 3 |
| Catálogo y plantillas | 10 | 0 | 10 | 0 | 0 |
| Equipo personalizado | 10 | 4 | 4 | 2 | 0 |
| Caras y alimentación | 12 | 3 | 8 | 1 | 0 |
| Puerto | 25 | 9 | 13 | 3 | 0 |
| Lotes de puertos | 16 | 0 | 16 | 0 | 0 |
| Conexiones | 22 | 4 | 4 | 14 | 0 |
| Conexiones en lote | 11 | 0 | 7 | 4 | 0 |
| Búsqueda y filtros | 5 | 1 | 1 | 3 | 0 |
| Preferencias visuales | 13 | 2 | 9 | 0 | 2 |
| Historial y atajos | 10 | 0 | 1 | 5 | 4 |
| JSON e importación | 13 | 0 | 0 | 0 | 13 |
| CSV e intercambio | 5 | 0 | 0 | 1 | 4 |
| Informes | 15 | 0 | 2 | 10 | 3 |
| Imágenes y documentos | 6 | 0 | 0 | 2 | 4 |
| Etiquetas y QR | 5 | 0 | 1 | 3 | 1 |
| Demo e idioma | 4 | 0 | 0 | 0 | 4 |
| Persistencia y recuperación | 23 | 0 | 4 | 0 | 19 |
| Fallo de aplicación | 5 | 0 | 0 | 0 | 5 |

## Diferencias de mayor impacto

1. **El rack necesita prioridad visual.** PoE y varios bloques de exportación preceden al rack. La grabación de Wascar y la fuente coinciden en esa causa del desplazamiento. Racks primero, detalles plegables y acciones agrupadas quedan en el plan; aquí no se rediseñó la GUI.
2. **Hay más exportación servidor de lo que parece.** CSV, XLSX nativo, SVG frontal/trasero, HTML imprimible y XLS basado en HTML existen en vistas distintas. Se ejecutaron por HTTP en un laboratorio nuevo. Hay que ordenar su acceso. XLS HTML con tres tablas no equivale a tres hojas XLSX pobladas; HTML imprimible tampoco acredita generación nativa PDF.
3. **Falta intercambio JSON general desde el panel.** Exportar/importar proyecto, cliente o rack y fusionar con nuevos IDs tiene cobertura offline. El cargador externo fijado al Full Backup original no sustituye una interfaz general con vista previa y validaciones.
4. **Falta backup/restore administrativo desde dashboard.** Existen backup PostgreSQL, tareas y restauración operativa hacia una instancia nueva. No se cuentan como botones web; integración portable de custodia MFA y recuperación sigue pendiente.
5. **Faltan PNG y detalles de presentación.** Normal/HD/transparencia, técnico documental, logo del cliente, selector de iconos de instancia y zoom figuran en los pendientes.
6. **Hay parciales visibles pequeños.** El prefijo se persiste, pero tooltip/inspector físico busca otra propiedad; el destello de puertos no está conectado. La GUI bloquea convertir tipo de grupo aunque backend/SQL admiten conversión condicionada. PoE cambia alias rj45/rj45_poe conservando identidad/familia: no es tipo literalmente inmutable.
7. **El servidor añade funciones propias.** Usuarios, grupos, capacidades/ámbitos, MFA con gracia45 y excepción del administrador global, sesiones/CSRF, auditoría, conflictos/idempotencia y operación Windows. Las 471 entradas distinguen fuente, pruebas históricas y herramientas externas.

## Componentes del rack y catálogo

**33 presets offline frente a 33 presets stock del servidor**, además de **10 representaciones de tipo de puerto** y 7 categorías offline. El offline define 25 referencias base y agrega ocho con Object.assign: 33 efectivas, trazadas por clave en ambos lados. CATALOGO-MODELOS.json y la pestaña Modelos detallan altura, icono, color y grupos/puertos.

Se incluyen las mutaciones posteriores a la declaración base: alimentación adicional de 14 presets, PDU con 9 puertos eléctricos y UPS con 5 eléctricos más gestión/USB. También se registran las siete categorías del menú CATS. La revisión independiente detectó que la primera extracción sólo leía los 25 iniciales; se corrigió antes de cerrar.

No significa que cada preset haya sido instanciado ni que exista un modelo de cada fabricante. El grupo servidor normaliza rj45_poe a familia rj45, conservando el atributo de puerto: la diferencia literal no implica pérdida de PoE. Dosen y dispositivos finales son objetos servidor con reglas propias. El plan exige sus recorridos y matriz de caras/energía/PoE; no inventa circuitos físicos.

## Pruebas ejecutadas

**Offline, Edge aislado:** 50 escenarios base, **49 recorridos funcionales finales PASS y una observación que confirma un hallazgo**. Navegación, demos/idiomas, edición, Click-Click, reconexión, undo/redo, grupos, plantillas, JSON, CSV, informes, PNG y persistencia local constan en BROWSER-RESULTADOS.json. Hubo 12 intentos fallidos del harness por selectores/supuestos; se conservan y no se convierten en fallos del producto. Cero excepciones JavaScript de aplicación observadas y diez descargas. Sin impresora física ni Excel instalado.

**RC10-B42:** un lote de rango 1–1 cambia cuatro puertos de grupos/tipos distintos con gn=1. Deshacer revierte el cambio. Es ambigüedad del offline: conservar en servidor IDs y grupo/tipo, sin copiarla.

**Servidor10, PostgreSQL17.11 nuevo aislado:** **23/23 PASS** sobre DLL publicada y frontend fijados. Lectura de diez clientes/5.408 puertos en dos sesiones; catálogo/favoritos/plantillas; generación y recuperación de CSV, XLSX, HTML, SVG y XLS HTML; verificación de contenido/hash; rechazos Origin/CSRF; escritura Unicode, relectura e idempotencia. Laboratorio detenido. Se conservaron intentos del harness con supuestos de contrato incorrectos; no fueron defectos de producto.

El ensayo servidor fue HTTP loopback y rol de ejecución restringido: **no es prueba nueva de GUI, HTTPS instalado, MFA real ni VM**. Las pruebas anteriores conservan fecha y autor.

## Inventario técnico

- **1.298 definiciones JavaScript de aplicación offline**, incluidas anónimas/callbacks.
- **2.500 definiciones del bundle servidor**, incluidas callbacks y código empaquetado; **3.798 en total**.
- **441 sitios de evento/callback/listener offline y 546 del servidor**, **987 en total**.
- **103 rutas HTTP literales** y **271 usos** de componentes React.
- Dos scripts de impresión contenidos en cadenas de documentos generados se registran aparte. Se identifican React/ReactDOM/html2canvas, pero sus funciones internas no se cuentan como funciones de RackClick.

Cada función tiene archivo/línea, nombre/propietario, firma, llamadas, descripción inferida, fragmento y hash. Cada evento tiene elemento, evento, handler y enlace de función cuando se resuelve por offset. **Las descripciones automáticas son inferencias, no especificaciones humanas revisadas de cada callback.** Las 302 acciones son el catálogo funcional legible; no son 3.798 funciones de producto independientes.

V8 enumeró 1.018 rangos offline y observó ejecución en 754; el emparejamiento AST identifica 753 definiciones. Sus universos difieren: V8 recoge rangos compilados y AST todas las definiciones. **Observar ejecución no acredita corrección ni todas las ramas.** La validación individual sigue pendiente. El bundle servidor no tiene cobertura JS medida en este ensayo HTTP.

Se enumeran construcciones sintácticas detectables por AST, no todas las combinaciones de datos, llamadas indirectas o botones que genera un bucle. No se promete haber pulsado cada combinación: quedan inventario, fuentes y huecos de verificación. Los 30 componentes principales y 99 definiciones de nivel superior tienen análisis humano en OFFLINE-ANALISIS.md.

## Revisión y decisiones

Revisores distintos del autor de cada mitad contrastaron **30 correspondencias focales**. Se conciliaron O-091, O-093, O-143, O-275 y O-277; originales y revisiones se conservan. No se declara doble revisión de las 302 filas.

No portar literalmente SAVE_KEY/autosave como DB maestra, limpiar auditoría, traducir nombres propios o QR decorativo como real. Restaurar inventario y recuperar PostgreSQL/MFA completo son operaciones diferentes. La matriz y el plan registran cada decisión.

## Evidencia y continuidad

[Evidencias, inventarios y límites](../evidence/s1-20261029/comparacion-rc10-servidor/README.md). El visor se abre localmente sin Internet. Perfiles, descargas de prueba, fuentes copiadas y diagnósticos privados quedan bajo .local; no forman parte de la entrega.

No se cambió código, versiones, referencia adoptada, resultados de Wascar, VM, QA o bases existentes. Se documenta trabajo, sin declararlo implementado. **Índice de cierre restante9,76/100 sin incremento; no se recalculó un porcentaje global del producto.**
