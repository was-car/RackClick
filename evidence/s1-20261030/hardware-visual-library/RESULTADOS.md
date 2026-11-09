# Biblioteca visual de carcasas principales

30.10.2026 · Coordinador: selección, infraestructura, genéricos y ensamblado. Dos recopiladores con carpetas separadas: firewalls y red/NAS. Revisor release distinto de los tres autores.

## Investigación y decisión antes de recopilar

Se consultaron AGENTS, hoja/registro maestro, ALCANCE-CATALOGO-FABRICANTES, fuentes primarias de29–30.10y el primer perfil StarTech. Wascar pide forma/color reconocibles por modelo y permite genérica para el resto. Su decisión posterior a la revisión de disco es conservar todo: no se ejecuta limpieza.

Se aprovechan las fuentes existentes y el ZIPNetBox fijado19470a551058fc9207f036371beefc41b197202e. Se investigaron manuales/fichas/galerías originales de proveedores. Se reúnen35modelos representativos; no se afirma descargar el mercado entero. Fotos quedan privadas y los SVGgenéricos son propios. Sin extraer PacketTracer ni instalar dependencias nuevas. Los metadatos por activo y sus URLs están en docs/CARCASAS-PRINCIPALES/INDICE.json.

## Resultado concreto

-35modelos/14fabricantes;92imágenes únicas(84oficiales o derivadas de documento oficial,8elevaciones NetBox ya locales),8PDFfuente,10SVGgenéricos.78.858.054bytes de referencias.
-58imágenes con modelo identificado,6compartidas de fabricante,20familia/variante y8comunidad. No equivalen a plantillas validadas ni verifican todos los conectores.
-16registros sin caras pendientes declaradas;19tienen incertidumbre/faltantes. Especiales:100Ffigura101F, XG135/XGS116traserasw, JL682Alineup1930, QNAPRAM y configuraciónservidores.
-Visor VER-CARCASAS-PRINCIPALES.html y ZIPportátil02:114entradas,68.073.854bytes. Manifiesto, whitelist de archivos y SHA256SUMS; no se incluyen fuentesHTML, perfiles, scripts, ZIPmarketing ni extracciones rechazadas.
-Generales por categoría sin puertos/U/PoE deducidos. Regla propuesta de integración: coincidencia exacta de fabricante/modelo/variante/revisión; genérica si falta o no está comprobada. Renderer/catálogoSQL e instalación10no se modifican. StarTech de desarrollo18se conserva.

## Verificación ejecutada realmente

Windows del proyecto, Python3.12, Node24.21.0y Edge nativo. No nuevos testsPostgreSQL/WindowsService/producto: la aplicación no cambió.

1. Los recopiladores comprobaron bytes, formato, tamaño ySHA; registraron fuentes y límites. Networkinspeccionó33de40imágenes y las7perspectivas restantes sólo por metadatos. Firewalls verificó sus30seleccionadas; el coordinador inspeccionó lámina de infraestructura y las capturas del visor.
2. Generador privado validó35IDs únicos, rutas internas sinreparse, firmasPNG/JPEG/WebP/PDF y hashes antes de formar la whitelist; redactó un visor sin recursos de red. No es un generador de catálogosSQL ni un descargador universal.
3. Navegador02:8focosPASS. Raíz, portátil y ZIPextraído:35tarjetas y102imágenes cargadas por visor(92referencias+10genéricos). Búsqueda modelo1resultado, filtroSophos4, abrir/cerrar zoom,390px sin desbordamiento, sin erroresniHTTPexterno. Resultado NAVEGADOR-02.json. Capturas y perfiles permanecen privados porque muestran fotografías de terceros.
4. Revisor independiente01: trespins,114nombresZIP exactos,CRC/bytes,100referencias+10SVG, enlaces locales y fuentesHTTPS,6referencias visuales+genéricos. Sin hallazgos bloqueantes para consulta privada. No verificó exactitud92imágenes ni ejecutó nuestros filtros.
5. Delta02: sólo cambia CSSdelcheckbox delvisor, literal de edición enmanifest ysumas; prefijoZIP02.110activos+LEEMEidénticos a01. Revisor distinto recomputaZIP02/pins/delta; favorable para consulta privada. LosZIP01y02se conservan. La primera pasada de navegador01también pasó8focos, pero su captura mostró checkboxdemasiado ancho; se corrige en02y se repite sobre la definitiva.

Comandos principales realmente usados:

```powershell
C:/Python312/python.exe -X utf8 -B .local/hardware-visual-ecdcfe0f648648288378169d3b92917b/build_library.py --edition 02
C:/RackClick_SVR/.local/node-v24.21.0-win-x64/node.exe .local/hardware-visual-ecdcfe0f648648288378169d3b92917b/verify_gallery.mjs
```

El ZIPse extrajo en destino nuevo de laboratorio para la prueba portable; no se sobreescribieron carpetas ajenas. No se hizo una prueba negativa nueva del recolector ni se afirma una fase roja: es una biblioteca/visor nuevos. Las validaciones del revisor son independientes de las del generador.

## Pins de la entrega02

| Pieza | SHA256 |
|---|---|
| ZIP |12ddc218ac265676c48db34043d461e341dd1c3af7745f8ee9907951fa460786|
| REFERENCIAS.json |3cdf319c171b574c13a80ea1082b253add3a697187a441c316063b8e1989cefd|
| SHA256SUMS.txt |9c0a321ead7603dccad8b5ad00ded421f156dda49f10e6db664a7e80faaa80bd|

## Límites y siguiente paso

No hay garantía de licencia de redistribución por disponibilidad pública o por el CC0delrepositorio. La biblioteca está en.localy no se publica. Dibujo propio específico/integración por revisión, configuración de módulos/puertos y ensayosGUI siguen pendientes. La comparación visual acotada no acredita los35modelos conectables ni sus variantes. Ninguna imagen se utiliza para inferir topología.

Siguiente: carcasa StarTech propia con forma/color/etiquetas y caras contrastadas, conservando Click-Click/UUIDs; después ampliar modelos por el mismo contrato y resolver los formatos/instalador pendientes. No se ha activado un casoQA de producto por esta colección.

Sin borrados, DB/VM/QA/MFA/instaladores/commits/push. Índice de cierre restante9,76/100intacto; ninguna subida de porcentaje por contar imágenes, modelos o verificaciones.
