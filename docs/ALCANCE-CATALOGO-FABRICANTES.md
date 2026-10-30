# Catálogo real de fabricantes para RackClick

Investigación iniciada 29.10.2026 y cerrada 30.10.2026 · Alcance solicitado por Wascar. **No se han instalado estas plantillas en la aplicación.**

Objetivo: elegir **marca → familia → modelo → variante/revisión**, ver sus caras y puertos, y crear el equipo completo sin fabricar su plantilla manualmente. Conservar Click-Click, identidades de puertos, permisos y guardado confirmado por servidor.

[Catálogo de consulta](../CATALOGO-HARDWARE.html) · [Datos y fuentes](CATALOGO-HARDWARE-REFERENCIA/README.md) · [Comparación RC10/servidor](COMPARACION-OFFLINE-RC10-SERVIDOR.md).

## Qué existe y qué se pretende añadir

El catálogo actual contiene 33 presets genéricos en 7 categorías, favoritos y plantillas privadas/compartidas. Es una base funcional, pero «Switch24P» no identifica la distribución de un Cisco, Aruba o FortiGate real. Tampoco una imagen convierte por sí sola un dibujo en un equipo conectable.

Se reutilizará ese flujo y su creación transaccional. Se propone ampliar datos/metadatos, selección y representación física; no sustituir ASP.NET/Npgsql/PostgreSQL ni rediseñar la GUI. Referencias internas: GUI-CATALOGO-BASE-S1.md, API-CATALOGO-BASE-S1.md, InventoryCatalogBrowser/Dialog/Fields, inventory-catalog.ts, InventoryRc9Catalog y plantillas privadas/compartidas.

Los archivos de esta investigación separan:

1. **Identidad recopilada:** marca, nombre, modelo, SKU, archivo y procedencia.
2. **Definición comunitaria:** altura, interfaces y componentes declarados en un repositorio; aún puede contener errores u omisiones.
3. **Campos contrastados con fabricante:** dato y localizador de manual/ficha, con incógnitas explícitas. Un perfil parcial no es una plantilla aprobada.
4. **Plantilla validada de RackClick:** transformación revisada, caras/geometría, pruebas y licencia de recursos. **Ninguna plantilla nueva alcanza este estado en este bloque.**

## Cobertura temporal y límites medibles

La ventana objetivo será aproximadamente **29.10.2018–29.10.2026**, más equipos anteriores que sigan instalados en clientes. «Lanzado», «a la venta», «soportado» y «presente en una instalación» son fechas/estados distintos.

La referencia comunitaria fijada es del 25.10.2026 y no es el HEAD consultado el 29.10. Los nombres y especificaciones oficiales se contrastan en esta investigación, pero **no se ha acreditado un censo de todos los productos del mercado de esos ocho años**. El repositorio también contiene modelos más antiguos. Fecha desconocida se guarda como nula; no se deduce de un sufijo923/1221, del copyright o de la fecha de una contribución Git.

Un modelo retirado se conserva para documentar la instalación; no se recomienda comprarlo ni desaparece de un inventario al actualizar el catálogo. Estado comercial es regional cuando así lo es la fuente.

## Marcas y tipos que se quieren cubrir

Esta es la prioridad de producto, no una afirmación de que cada marca ya tenga plantillas listas. El visor muestra el número realmente recopilado de cada fabricante.

| Tipo | Prioridad inicial | Ampliación prevista |
|---|---|---|
| Firewalls/UTM | Sophos XG/XGS, Fortinet FortiGate, Palo Alto PA | WatchGuard, SonicWall, Check Point, Cisco Secure Firewall, Juniper SRX, Netgate |
| Switches | Cisco Catalyst/Nexus/Meraki, HPE Aruba CX/Instant On | Juniper EX/QFX, Arista, Dell, Extreme, Huawei, Ubiquiti, MikroTik, TP-Link Omada, NETGEAR, D-Link, Zyxel, FS |
| Routers y gateways | Cisco ISR/ASR/Catalyst, MikroTik, Juniper, Ubiquiti | LANCOM, DrayTek, AVM y variantes empresariales confirmadas |
| NAS | Synology DiskStation/RackStation/FlashStation, QNAP TS/TVS | ASUSTOR, TerraMaster, Buffalo, TrueNAS/iXsystems; ReadyNAS histórico |
| Almacenamiento empresarial | Separado de NAS: NetApp, Dell EMC y cabinas documentadas | Pure Storage, HPE, IBM; diferenciar controladoras, bandejas y enlaces SAS/FC |
| Servidores | Dell PowerEdge, HPE ProLiant, Lenovo ThinkSystem, Supermicro | Fujitsu PRIMERGY, Cisco UCS y sus módulos/chasis |
| Racks | APC/Schneider, Rittal, DIGITUS | Eaton, Vertiv, Triton, StarTech y modelos con medidas verificadas |
| UPS/PDU | APC, Eaton, Raritan, Vertiv | CyberPower, Tripp Lite; variantes de tomas y alimentación regional |
| AP y equipos de sala | Aruba, Cisco/Meraki, Ubiquiti, Ruckus, Omada | Dosen/paneles/tomas según modelo; AP no se convierte automáticamente en equipo de 1U |
| Paneles/óptica | DIGITUS, Panduit, Corning, R&M, Leviton y modelos documentados | Keystone, casetes, transceptores y módulos como componentes distintos |

No se mezclarán HPE completo y Aruba como si fueran la misma línea de producto. Se conservan fabricante original, marca comercial y alias de búsqueda; una compra empresarial o cambio de nombre no altera la identidad histórica de un modelo.

## Datos mínimos por plantilla

| Grupo | Datos |
|---|---|
| Identidad | fabricante original, marca, familia, modelo exacto, SKU/part number, variante, revisión hardware, alias, identificador estable |
| Procedencia | URL primaria y comunitaria, commit, ruta, hash, localizador de tabla/página, fecha de consulta, campos verificados/pendientes |
| Montaje | rack/desktop/torre/pared/0U, alturaU si corresponde, ancho/profundidad, ocupación y kit opcional; rack exterior separado del montaje de 19 pulgadas |
| Puertos | nombre impreso, posición/orden, tipo de jaula/conector, velocidad/capacidad, grupo, cara y rol; clave de plantilla separada del UUID de instancia |
| Energía | entrada/salida, conector real, fuentes instaladas/opcionales, PoE in/out, norma y presupuesto condicionado a PSU; carga consumida no se inventa |
| Componentes | bahías/módulos/linecards, ópticas y breakout permitidos, ranuras vacías y piezas instaladas |
| Representación | vista frontal y trasera, geometría de cada puerto, orientación, coordenadas y recurso visual con licencia/procedencia |
| Mantenimiento | versión de catálogo/plantilla, estado comercial/soporte y ámbito regional; fecha de lanzamiento desconocida nula |

La ficha no almacenará una contraseña, IP real, número de serie de cliente, estado ocupado ni cables de otra instalación. Crear instancias genera sus propios UUIDs y deja los puertos operativos libres; actualizar una plantilla no mueve ni elimina puertos/cables ya creados.

## Reglas físicas importantes

- **Conectores combo:** una boca RJ45 y una SFP pueden compartir la misma interfaz. Modelar bocas físicas y exclusión lógica; no duplicar capacidad ni permitir dos cables activos incompatibles. Se observaron ejemplos FortiGate80F y PA415/445/455.
- **Módulos opcionales:** una ranura no implica puertos instalados. Una tarjeta10GbE opcional de NAS, una linecard o una segundaPSU se selecciona aparte.
- **NAS:** bahías de disco, M.2, PCIe, USB, HDMI y eSATA no son todos puertos Ethernet. Un NAS de escritorio no ocupa1U por decreto; bandeja/kit y objeto tienen ocupaciones distintas.
- **Puertos ópticos:** jaula SFP/SFP+/SFP28/QSFP y conector del transceptor no son lo mismo. Breakout cambia interfaces lógicas, no multiplica automáticamente orificios.
- **Gestión/console/stack:** una consola RJ45 no acepta un enlace Ethernet ordinario sólo por su forma; distinguir función y protocolo.
- **Frontal/trasera:** el fabricante determina la cara y etiquetas; no inventar una boca trasera o circuito interno por simetría. Una foto no acredita conectividad eléctrica interna.
- **PoE:** capacidad/budget, PSU instalada y consumo real son datos distintos. Conservar los controles del servidor por IDs/grupo/tipo; gn puede repetirse.
- **Variantes:** Wi-Fi, PoE, AC/DC, PSU redundante y revisión física pueden cambiar puertos/cara. Sufijos de licencia de software pueden compartir el mismo perfil físico, conservando sus SKU como variantes/alias comprobados.

## Presentación propuesta

En **Añadir equipo → Catálogo**, conservar el diálogo y añadir:

1. Buscador por marca, familia, modelo, SKU y alias.
2. Marca → familia → modelo; filtros de tipo, montaje, puertos, PoE y estado histórico.
3. Vista previa frontal/trasera, listado de grupos y advertencias de módulos/puertos combo.
4. Selector explícito de configuración/módulos, sin marcar opcionales como instalados.
5. Resumen de lo que se creará y confirmación del servidor. Guardar/recargar/otra sesión deben conservar el mismo objeto.
6. Favoritos y plantillas propias continúan; el catálogo puede usarse localmente desde la instalación sin depender de Internet durante la operación.

«Confirmado por fabricante», «comunitario» y «pendiente de revisión» no se presentarán como un único sello de calidad. El catálogo de investigación no será seleccionable como predeterminado hasta pasar el control de publicación.

## Imágenes y Packet Tracer

Una fotografía pública no acredita permiso de redistribución o modificación. La licencia CC0 del repositorio comunitario no concede marcas ni derechos de terceros que su autor no posea. Se conservará licencia/procedencia por recurso; imágenes desconocidas quedan fuera del paquete de aplicación.

Cisco permite utilizar sus [iconos de topología sin alterarlos](https://www.cisco.com/c/en/us/about/brand-center/network-topology-icons.html); son iconos conceptuales, no permiso general para extraer carátulas de Packet Tracer o fotografías. No se accedió a Packet Tracer ni hace falta instalarlo para recopilar estos datos.

Primera opción: geometría propia basada en hechos y/o recursos cuya licencia esté comprobada. Una imagen con superposición de puertos conserva los UUIDs y acciones Click-Click. SVG de terceros debe sanearse: sin scripts, eventos, enlaces/recursos externos ni HTML activo. No se ejecutan scripts de repositorios descargados.

## Entregas de desarrollo propuestas

Los números siguientes son objetivos iniciales para organizar el trabajo, no avance realizado ni aumento automático del denominador vigente.

1. **C-HW-01 · Inventario y fuentes:** registro versionado/consulta local, fabricantes, modelos, procedencia y huecos. Este bloque entrega esa base de investigación.
2. **C-HW-02 · Contrato y conversión:** esquema de identidad/variantes/geometría, mapa de conectores y componentes que el modelo actual aún no representa. Rechazar mapeos ambiguos; no convertir desconocidos a RJ45.
3. **C-HW-03 · Primer catálogo curado propuesto de 100 perfiles:**12 Sophos, 16 Fortinet, 12 Palo Alto, 20 Cisco, 12 Aruba, 8 Synology, 8 QNAP, 6 racks y 6 UPS/PDU. Selección exacta según disponibilidad de fuentes completas y uso; no 100 nombres sin comprobar. El número es una propuesta de entrega inicial, no una promesa de 100 ya listos.
4. **C-HW-04 · GUI y vistas:** filtros marca/familia/modelo, preview y configuración; conservar formularios, idiomas, favoritos y permisos.
5. **C-HW-05 · Prueba por modelo:** identidad, altura, grupos, etiquetas, energía y caras frente a fuente; geometría; crear dos instancias con UUIDs distintos; edición/cables/recarga/otra sesión; prohibiciones combo/modular y usuarios sin permiso.
6. **C-HW-06 · Publicación de catálogo:** manifiesto/digest, compatibilidad, actualización sin modificar instancias existentes, rollback del catálogo y licencias. Revisar alguien distinto del implementador; candidata completa y QA detallada de Wascar.
7. **C-HW-07 · Ampliación mantenible:** incorporar marcas/modelos restantes mediante el mismo proceso; catálogo de investigación grande, conjunto predeterminado curado y paquetes por familia. Medir búsqueda/tiempo/memoria con muchos modelos antes de fijar umbrales.

Los 100 perfiles iniciales no limitan la meta de catálogo amplio: evitan convertir miles de contribuciones heterogéneas en predeterminados sin control. También permiten añadir nuevos modelos sin rehacer la aplicación.

## Criterio de cierre de cada modelo

- Nombre/SKU y revisión sin ambigüedad; fuente primaria conservada y campos desconocidos explícitos.
- Cantidad/función de cada puerto, cara, energía, ocupación y módulos comprobados; coordenadas y recurso visual aptos para redistribución.
- Negativos y persistencia pertinentes pasan sobre laboratorio nuevo, con rol runtime restringido. No usar una imagen bonita como prueba de topología.
- Revisión independiente, guía QA con pasos de selección/creación/clic y resultado esperado; disponible sólo en la candidata que lo contiene.
- Registro de versión y migración de catálogo; ningún dato/puerto/cable previo se sobrescribe al actualizar.

La investigación no cambia la instalación actual ni el catálogo de 33. **Índice de cierre restante 9,76/100 sin incremento**: el alcance nuevo queda descrito, no implementado ni ponderado silenciosamente.
