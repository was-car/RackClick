# Carcasas principales · cartera de 506 modelos

30.10.2026 · **Edición 04: 506 modelos distintos**, con mínimo de 500 solicitado por Wascar.

**[Abrir el visor](../../VER-CARCASAS-500.html).** El acceso habitual VER-CARCASAS-PRINCIPALES.html apunta a la edición actual. Buscar por fabricante/modelo, filtrar y pulsar una imagen para ampliar. Páginas de 24 modelos para limitar las imágenes activas.

[Lista completa](CARTERA-500.md) · [CSV](MODELOS-500.csv) · [Fuentes y hashes](INDICE-04.json) · [Evidencia](../../evidence/s1-20261030/hardware-visual-500/RESULTADOS.md) · [Colección220 anterior](README-03.md).

## Qué contiene

- 506 claves normalizadas fabricante/modelo y 506 conjuntos completos de imágenes distintos, todos con imagen asignada.
- 220 productos anteriores preservados, 280 comunitarios adicionales y 6 incorporaciones oficiales de fabricantes/tipos faltantes.
- 871 contenidos de imagen distintos por SHA256, en 904 asociaciones/archivos; 12 documentos y 13 genéricos propios. Varias fotos del mismo producto y genéricos no inflan el número de modelos.
- Fabricantes de redes, seguridad, servidores, almacenamiento, energía y cableado. Las denominaciones de origen incluyen alias y nombres históricos; no son un conteo de empresas independientes. Consulta la lista para ver exactamente los productos incluidos.

## Distribución

| Tipo | Modelos |
|---|---:|
| Firewall/seguridad | 78 |
| Switch | 187 |
| Router/gateway | 47 |
| NAS | 25 |
| Panel | 23 |
| Bandeja | 1 |
| Rack | 4 |
| UPS/SAI | 13 |
| Servidor | 46 |
| Punto de acceso | 8 |
| PDU | 19 |
| Otros equipos físicos | 43 |
| Almacenamiento | 12 |

## Calidad y procedencia

Se conserva íntegra la selección anterior. Los 280 adicionales se eligen por cuotas y modelo, con prioridad para fabricantes nuevos; se comparan identidad, SKU, alias y conjuntos completos de imágenes contra los 220 previos. Se excluyen genéricos, módulos/adaptadores como relleno, variantes sólo de RAM y duplicados completos. Los miembros del ZIP NetBox se contrastan por SHA256, CRC, tamaño, formato y dimensiones; no se vuelve a descargar el archivo de 1 GB ni se ejecuta código del repositorio.

Las incorporaciones oficiales se buscan en páginas, fichas o galerías del fabricante y conservan sus fuentes por activo. Fotografías en perspectiva, esquemas y dibujos técnicos se identifican como tales; no se inventa una trasera ni se presenta una variante vecina como exacta.

Los recursos comunitarios siguen `community_unverified`. No se han verificado 500 fichas de hardware, fechas, licencias, puertos o montajes. Las fotografías se mantienen privadas; su disponibilidad pública no autoriza automáticamente empaquetarlas en el producto o publicarlas en GitHub.

## Carcasa específica y genérica

La biblioteca prepara referencias para dibujar carcasas propias con forma, color, etiquetas y caras contrastados. Para modelos o caras sin definición fiable corresponde una genérica por categoría. Ninguna silueta añade conectores, fuentes, PoE, U, medidas o circuitos; los controles Click-Click seguirán los UUID del inventario.

Esta colección no modifica el selector/racks de la aplicación ni instala 506 plantillas. El siguiente trabajo recomendado es integrar un primer grupo de carcasas utilizadas, empezando por StarTech, y validar creación/puertos/conexiones/guardado/recarga antes de ampliar las plantillas funcionales.

## Verificación y archivos

Visor y ZIP se comprueban en Windows/Edge: recorrido de todos los modelos por páginas, decodificación de imágenes, búsqueda/filtros/zoom y primera página a 390 px, ausencia de solicitudes HTTP externas y cantidad de imágenes activas acotada por paginación. Los comandos y resultados efectivamente ejecutados, muestra visual y revisión independiente están en la evidencia. Esto no sustituye la revisión física de cada modelo.

Carpeta local: `.local/hardware-visual-500-fe06c3650ef34f5385fdfe813ffcbf7f/`.

- `RackClick-Carcasas-Principales-04.zip`: 304,218,972 bytes (~290,13 MiB), 933 entradas.
- SHA256 del ZIP: `b1b6341cccc2fd842e7250963efa9593ae8e6807289fdefa037890f8e8074490`.
- SHA256 del manifiesto: `05e9617b34c49da95bc0e47c6717c8860453ec30d753b0eb14f3da093710c899`.
- SHA256 de las sumas: `177bca21eb7d1a3651002cff891a3aaa7ffa2dd78b231a8df28023344d6b321d`.

Para consultar en otra carpeta/equipo: copiar el ZIP, verificar su hash, extraer en carpeta nueva y abrir ABRIR-CARCASAS.html. No requiere servidor, PostgreSQL o contraseñas. Los ZIP 01/02/03 y los accesos/índices anteriores se conservan. Los manifiestos históricos no se usan para verificar los archivos actuales.

Se mantiene la decisión de no limpiar archivos. Sin cambios en DB, VM, QA, MFA, instaladores, commits o push. **Índice de cierre restante 9,76/100, sin crédito automático ni nuevo porcentaje global por contar recursos.**

## Integración posterior · lote 01

Se ha integrado por separado el primer frontal propio StarTech C6PANELUTP241UFT en desarrollo, con revisión exacta y trasera genérica explícita. [Ver capturas y resultado](../INTEGRACION-CARCASAS-LOTE01.md). La biblioteca de506 sigue siendo de consulta; sus fotos no se incorporan al producto ni se instalan todos los modelos por este cambio. La QA de la instalación actual continúa pendiente de la candidata completa.
