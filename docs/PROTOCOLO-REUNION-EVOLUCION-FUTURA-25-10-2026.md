# Protocolo de reunión · posibles ampliaciones de RackClick

**Fecha:**25.10.2026, Europe/Berlin. **Participantes:**Wascar y Codex. **Estado:**registro de conversación e investigación documental; propuestas para después de completar todos los puntos del alcance vigente.

## 1. Acuerdo de alcance

Wascar propone estudiar herramientas de apoyo, descubrimiento de equipos de red y productos de documentación comparables. Pide guardar lo hablado para retomarlo después de terminar el proyecto actual.

Este registro conserva esas posibilidades **fuera del plan de cierre vigente**. No añade tareas, pesos, fechas, compromisos de entrega ni dependencias. El indicador permanece en7,63/100 de cierre del trabajo pendiente; no es porcentaje global del producto. La línea base RC-CIERRE-20261025-v1 y sus requisitos se mantienen intactos.

La reunión autoriza consultar fuentes públicas y guardar este protocolo. No se han instalado programas, descargado ejecutables, creado cuentas, enviado formularios o correos a proveedores, escaneado redes ni operado VM/QA. El desarrollo de Codex permanece en pausa durante la conversación. La entrega de Claude se tratará al retomar el trabajo técnico.

## 2. REA y el mapa de código

Wascar solicita investigar [morluto/rea](https://github.com/morluto/rea).

- REA ofrece herramientas MCP/CLI de ingeniería inversa y observación de aplicaciones: JavaScript/Electron, análisis estático de .NET y otras superficies. El repositorio declara licencia MIT. [Fuente oficial](https://github.com/morluto/rea#readme).
- Su proveedor .NET analiza artefactos y metadatos; no ejecuta el ensamblado ni demuestra comportamiento CLR, seguridad de MFA o persistencia PostgreSQL. [Alcance .NET](https://github.com/morluto/rea/blob/main/docs/managed-code-analysis.md).
- La observación de navegador puede ayudar a investigar una interfaz. Su alcance depende del proveedor; no equivale por sí sola a automatizar toda la QA. [Observación web](https://github.com/morluto/rea/blob/main/docs/browser-observation.md).
- Codebase Memory ya instalado sirve para navegar el grafo de las fuentes propias. REA se estudiaría como complemento para una investigación concreta sobre artefactos o comportamiento. No se ha medido un ahorro de tiempo o créditos.

**Propuesta de Codex:**evaluarlo más adelante con un caso pequeño y medible, sin convertirlo en requisito para cerrar el proyecto. El soporte Windows, las herramientas adicionales y sus versiones deberán verificarse entonces. Esta reunión no aprueba su instalación ni promete un descubridor de red basado en REA.

## 3. Descubrimiento de switches, routers y puertos

Wascar pregunta si RackClick podría registrar automáticamente equipos y puertos, y expresa preocupación por la variedad de modelos.

La respuesta técnica es favorable, con compatibilidad y límites que deberán comprobarse por plataforma:

| Fuente | Información que podría aportar |
|---|---|
| SNMP, preferiblemente v3 con autenticación/cifrado y permisos de lectura | Interfaces, nombres/descripciones, velocidad y estados; otros datos según las MIB y el equipo. |
| LLDP | Identidad de vecinos y puertos anunciados. Puede consultarse la información del equipo mediante su interfaz de gestión. |
| API del fabricante/controlador | Datos adicionales o una alternativa cuando la plataforma lo permita. Requiere adaptadores específicos. |

Referencias primarias: [IF-MIB/RFC2863](https://www.rfc-editor.org/info/rfc2863/), [seguridad SNMPv3/RFC3414](https://datatracker.ietf.org/doc/html/rfc3414), [datos de vecinos LLDP documentados por Cisco](https://www.cisco.com/c/en/us/td/docs/routers/ncs4000/software/reference/guide/otncommandreferenceguide/m-lldp.pdf).

**Límites señalados en la conversación:**

- Un puerto sin enlace puede estar reservado o conectado a un equipo apagado. La observación operativa y el estado documental deben conservar significados separados.
- Las interfaces observadas pueden incluir VLAN, túneles o agregaciones. No todas representan un conector físico dibujable.
- LLDP informa de vecinos anunciados, pero de esos datos no se deduce el recorrido por patch panels, Dosen y cableado pasivo. Ese recorrido requeriría documentación o confirmación humana.
- Una IP, un nombre o un número de puerto no bastan para decidir una identidad. El mapeo deberá respetar los UUID de RackClick, pertenencias, grupo/tipo y los identificadores externos disponibles; ifIndex puede variar entre reinicializaciones, según RFC2863.
- No se promete compatibilidad universal. Los equipos sin gestión, LLDP deshabilitado, restricciones de acceso y diferencias de firmware pueden limitar la información.

## 4. Reutilizar recolectores y catálogos

Se comentaron tres recursos para evitar desarrollar toda la recopilación y todas las plantillas desde cero:

- **LibreNMS:**descubrimiento con SNMP y LLDP/CDP, más API de dispositivos/puertos. Posible fuente externa de observaciones para RackClick. [Descubrimiento](https://docs.librenms.org/Extensions/Auto-Discovery/), [API de puertos](https://docs.librenms.org/API/Ports/).
- **Netdisco:**inventario y localización por IP/MAC, recopilación por SNMP/CLI/API y acceso por API. [Proyecto oficial](https://netdisco.org/).
- **NetBox Device Type Library:**definiciones comunitarias YAML organizadas por fabricante/modelo. Podrían servir de base para adaptar plantillas a nuestro modelo; no se declara importación compatible sin conversión y validación. [Repositorio](https://github.com/netbox-community/devicetype-library).

Los recolectores pueden implicar un servicio Linux/contenedor y su mantenimiento; RackClick podría conservar su servidor Windows y el acceso por navegador. [Instalación oficial de LibreNMS](https://docs.librenms.org/Installation/Install-LibreNMS/). No se decide instalar una segunda plataforma de documentación ni cambiar la base de RackClick.

**Flujo propuesto, todavía sin implementar:**

`Equipos → recolector de lectura → observaciones y diferencias → confirmación autorizada → inventario RackClick`

Al retomarlo habría que definir frecuencia, fecha/fuente de cada observación, deduplicación y resolución de diferencias. Un equipo inaccesible no debería provocar borrados automáticos. Nombres, etiquetas y conexiones documentadas requerirían reglas explícitas de conservación. La aprobación y el commit seguirían comprobándose en el servidor, con ámbitos por cliente y auditoría. Las credenciales quedarían en el servidor/recolector, fuera del navegador y de los documentos públicos.

## 5. Patchdocs: acceso e instalador

Consulta solicitada por Wascar:[patchdocs.io](https://patchdocs.io/).

**Resultado comprobado:**la [FAQ oficial](https://patchdocs.io/faq/) lo describe como plataforma cloud utilizada desde el navegador, sin instalación local. La portada dirige al [registro oficial](https://app.patchdocs.io/register). No se encontró un instalador local público ni un repositorio oficial público del producto en las páginas y búsquedas consultadas; esto no demuestra que no exista alguna oferta privada.

Existe una discrepancia comercial: la portada anuncia30días de prueba y la FAQ menciona7. No fijar la duración sin comprobar las condiciones que presente el proveedor al registrarse. No se realizó ningún registro ni se inició prueba.

Se conserva como candidato de evaluación funcional de documentación visual. La consulta de su web no acredita una integración API con RackClick ni permite afirmar cómo funciona internamente.

## 6. Pathfinder: acceso e instalador

Consulta solicitada por Wascar:[pathfinder.de](https://www.pathfinder.de/), producto de tripunkt GmbH.

**Sí existe una vía oficial para conseguir el instalador:**

1. Solicitar la prueba desde la web. La [FAQ oficial](https://www.pathfinder.de/faq/) anuncia30días y explica que, tras revisar la solicitud en horario laboral, envían el enlace por correo.
2. Si se dispone de Pathfinder-ID, acceder al [portal oficial](https://pathfinder.support/Account/Login). El [manual de activación](https://manual.pathfinder.de/en/doc/3/license-activation) documenta allí la descarga del instalador y la licencia.

No se verificó un enlace público directo al setup que permitiera descargarlo sin solicitud/cuenta. Por tanto **no hay un EXE obtenido en esta reunión**. Tampoco se enviaron datos al proveedor.

No se encontró un repositorio público oficial del código del producto en la búsqueda acotada. El manual enlaza [PSPathfinder](https://github.com/falkheiland/PSPathfinder), pero lo identifica expresamente como wrapper externo no soportado por tripunkt. Es un complemento para la API, no el instalador ni el producto completo. [Fuente del fabricante](https://manual.pathfinder.de/en/doc/3/request-samples).

Para una evaluación futura se seguirían el instalador y la documentación correspondientes a la licencia/versión recibida, en laboratorio separado. No se fijan requisitos de despliegue a partir de páginas de versiones distintas.

## 7. Cómo retomar después del alcance vigente

Quedan como preguntas para esa futura fase, sin solicitarlas ni resolverlas ahora:

- Marcas/modelos/firmwares y cantidad aproximada de dispositivos que Wascar querría cubrir primero.
- Disponibilidad de SNMPv3, LLDP y APIs; acceso de lectura desde cada red de cliente.
- Recolector existente aprovechable frente a uno nuevo; instalación local, conectividad y mantenimiento.
- Qué datos pueden proponerse automáticamente y cuáles requieren validación humana.
- Productos a evaluar mediante acceso oficial, con datos ficticios y criterios concretos de comparación.
- Licencias, exportaciones/API, formatos de catálogo y compatibilidad verificables para cualquier reutilización.

**Secuencia propuesta al reabrir esta idea:**seleccionar pocos modelos representativos; comprobar datos de lectura en laboratorio; medir utilidad y mantenimiento; después decidir alcance, arquitectura y aceptación de una ampliación. No se adoptan automáticamente diseños de otros productos ni se modifica la GUI RC9 aprobada por esta conversación.

## 8. Cierre del registro

Se archivan las posibilidades y las vías oficiales de acceso. No hay decisión de compra, instalación, despliegue, incorporación al plan o adopción. La siguiente revisión de Claude pertenece al trabajo vigente y se tratará por separado. Cierre del plan pendiente7,63/100, sin incremento por esta reunión; porcentaje global sin recalcular.

Este protocolo resume la conversación y sus fuentes consultadas el25.10.2026; no es una transcripción literal ni una verificación práctica de esos productos. Los enlaces y condiciones pueden cambiar: deberán comprobarse al retomar la evaluación.

## 9. Adenda · búsqueda multilingüe en GitHub y cierre de la investigación

25.10.2026. Wascar solicita una última búsqueda de proyectos que puedan servir para futuras ampliaciones y precisa que se busque en varios idiomas. **La búsqueda queda cerrada documentalmente con esta selección.** Ningún candidato se instala, se incorpora al plan actual o se convierte en dependencia por aparecer aquí.

### 9.1 Método y términos utilizados

| Idioma de consulta | Ejemplos de palabras clave empleadas |
|---|---|
| Alemán | Netzwerk Dokumentation, Netzwerkdokumentation, Netzwerk-Dokumentation, Kabelmanagement |
| Inglés | network documentation, rack cabling, DCIM, network discovery SNMP LLDP |
| Español | documentación de redes, inventario de red SNMP, documentación redes cableado racks código abierto |
| Francés | documentation réseau, découverte réseau SNMP, logiciel cartographie réseau open source |
| Portugués | documentação de rede, inventário rede SNMP |
| Italiano | documentazione di rete, rack |

Se usó búsqueda web restringida a GitHub y consultas generales, verificando los candidatos en sus repositorios, README, documentación y avisos de licencia. Se descartaron resultados de formación, ejemplos de una red particular, pentesting sin relación directa y proyectos que sólo coincidían por nombre. El idioma de la búsqueda no certifica que la aplicación tenga interfaz en ese idioma ni satisface automáticamente EN/DE/ES de RackClick.

La selección siguiente contiene **16 proyectos/recursos**, con distintas funciones. Las descripciones son hallazgos documentales y la utilidad para RackClick es una propuesta de Codex; no son resultados de instalación, auditoría completa ni compatibilidad demostrada.

### 9.2 Recolectores y componentes para estudiar primero

| Proyecto y fuente primaria | Posible utilidad posterior | Licencia declarada y límite observado |
|---|---|---|
| [Netdisco](https://github.com/netdisco/netdisco) | Recopilar dispositivos, direcciones MAC/IP y pertenencia a puertos; posible integración de observaciones por API. | [BSD-3-Clause](https://github.com/netdisco/netdisco/blob/master/LICENSE.md). Aplicación propia con PostgreSQL; el despliegue e intercambio de datos requieren diseño. No conectar sus tablas directamente a las de RackClick. |
| [LibreNMS](https://github.com/librenms/librenms) | Descubrimiento y monitorización SNMP/LLDP/CDP; posible fuente de dispositivos, puertos y estados por API. | GPLv3 y avisos/excepción del proyecto. Es un servicio adicional de monitorización, no una biblioteca del servidor .NET. [API](https://docs.librenms.org/API/Ports/). |
| [GLPI Agent](https://github.com/glpi-project/glpi-agent) | Tareas de descubrimiento e inventario de red por SNMP; estudiar un recolector con paquetes oficiales para Windows y otros sistemas. | GPLv2+. Su protocolo/tareas pertenecen al ecosistema GLPI; la conexión con RackClick no está implementada ni demostrada. [README](https://github.com/glpi-project/glpi-agent/blob/develop/README.md). |
| [NetXMS](https://github.com/netxms/netxms) | Descubrimiento, topología, controladores por fabricante y REST API. El README enlaza instaladores Windows. | [Licencias mixtas por componente](https://github.com/netxms/netxms/blob/master/COPYING): GPLv2+ y LGPLv3+, además de terceros. Plataforma amplia de gestión, con operación y permisos propios. |
| [C# SNMP Library / #SNMP](https://github.com/lextudio/sharpsnmplib) | Candidato si se decide desarrollar un conector SNMP directamente en C#; el README declara SNMPv1/v2c/v3 y operaciones asíncronas. | [MIT](https://github.com/lextudio/sharpsnmplib/blob/master/LICENSE). Es una biblioteca: siguen pendientes perfiles, normalización, secretos, límites y pruebas con equipos. El README diferencia soporte Enterprise MIB en una edición Pro. No se elige versión ni se añade paquete ahora. |

Estos cinco candidatos representan alternativas o piezas distintas; no se propone instalar los cinco. Al retomar se compararía recolector externo frente a conector propio según equipos, mantenimiento y pruebas necesarias.

### 9.3 Modelos, catálogos e interacción visual

| Proyecto y fuente primaria | Posible referencia para RackClick | Licencia declarada y límite observado |
|---|---|---|
| [NetBox](https://github.com/netbox-community/netbox) | Modelos de racks, interfaces, cables, frontal/trasera, energía e IPAM. | [Apache-2.0](https://github.com/netbox-community/netbox/blob/main/LICENSE.txt). Su núcleo documenta el estado previsto; no es un descubridor/monitor de equipos. Referencia de modelos/API, sin migrar nuestro producto. [Introducción](https://github.com/netbox-community/netbox/blob/main/docs/introduction.md). |
| [NetBox Device Type Library](https://github.com/netbox-community/devicetype-library) | Catálogo YAML por fabricante/modelo para estudiar conversión a plantillas y reducir altas manuales. | [CC0-1.0](https://github.com/netbox-community/devicetype-library/blob/master/LICENSE.txt). Hay que validar cada definición, sus atributos/recursos y su adaptación; no existe importador RackClick acreditado. |
| [RackScope](https://github.com/marcosblg/rackscope) | Referencia especialmente cercana a la interacción de cableado: HTML offline, selección de bocas, etiquetas y exportaciones; README en español/inglés. | El README actual declara AGPL-3.0 y distingue versiones antiguas MIT. Modelo local/JSON y modo servidor opcional PHP; no acredita nuestro contrato multiusuario, PostgreSQL o autorización por ámbitos. No reemplaza RC9 ni se copia su código/identidad por esta reunión. |
| [Nautobot](https://github.com/nautobot/nautobot) | Modelos de ubicaciones, racks, interfaces, cables e IPAM; extensión mediante Apps y Jobs. | [Apache-2.0](https://github.com/nautobot/nautobot/blob/develop/LICENSE.txt). Plataforma Python/Django de alcance amplio; no es un módulo .NET intercambiable. |
| [RackTables](https://github.com/RackTables/racktables) | Reservas, puertos compatibles, enlaces físicos, racks y subredes como referencia funcional. | [GPLv2 y avisos incluidos](https://github.com/RackTables/racktables/blob/master/COPYING). Aplicación PHP con MySQL/MariaDB; no representa una integración ya disponible en RackClick. |
| [phpIPAM](https://github.com/phpipam/phpipam) | IPAM, subredes, VLAN/VRF, grupos y relación de direcciones con dispositivos. | [GPLv3](https://github.com/phpipam/phpipam/blob/master/misc/gpl-3.0.txt). Prioridad eventual para IPAM; no se presume equivalencia con recorrido de cableado físico. |
| [InfraNet Pro](https://github.com/muttley1973/infranetpro) | Referencia EN/IT de racks/planos y conciliación con SNMP, LLDP/CDP e IPAM. | AGPL-3.0-or-later según README. Declara almacenamiento JSON servido por un proceso y limitaciones multiusuario; no equivale al servidor PostgreSQL de RackClick. No se han ejecutado sus pruebas ni verificado sus afirmaciones. |
| [Scanopy](https://github.com/scanopy/scanopy) | Descubrimiento y diagramas de capas2/3, cargas y aplicaciones; posible contraste de mapas observados. | [AGPL-3.0 en Community](https://github.com/scanopy/scanopy/blob/main/LICENSE.md); también ofrece ediciones comerciales. Hay que comprobar funciones/edición exactas. Una vista L2 descubierta no demuestra el recorrido por cableado pasivo. |

### 9.4 Referencias con reservas adicionales

| Proyecto | Razón para conservarlo y reserva |
|---|---|
| [openDCIM](https://github.com/opendcim/openDCIM) | Inventario, conexiones y distribución eléctrica; README declara GPLv3. **El README pide mantenedor**, anuncia relevo y una última versión prevista26.01. Se guarda como referencia documental con riesgo de continuidad, no como recomendación de despliegue. |
| [Netdot](https://github.com/cvicente/Netdot) | Reúne SNMP, topología, IPAM y planta de cableado. El manual declara GPLv2 o posterior y muestra documentación histórica. No se verificó soporte actual de dependencias ni mantenimiento; referencia conceptual sin recomendar instalación. |
| [inventario-lan](https://github.com/fmbrieva/inventario-lan) | README en español con inventario SSH/NAPALM/SNMP y exportaciones JSON/CSV, licencia declarada Apache-2.0. El propio README indica script pendiente de publicación; no se clasifica como componente operativo disponible. |

### 9.5 Conclusiones para una futura evaluación

La combinación más razonable para **estudiar**, a juicio de Codex, sería:

1. Comparar **Netdisco y LibreNMS** como fuentes externas de lectura; considerar GLPI Agent o NetXMS si sus capacidades de despliegue/recopilación encajan mejor con las redes reales de Wascar.
2. Estudiar **Device Type Library** para el catálogo y **NetBox/RackTables/Nautobot** como referencias de modelo, sin sustituir la arquitectura de RackClick.
3. Evaluar **#SNMP** sólo si se decide asumir un conector propio y su mantenimiento.
4. Usar **RackScope, InfraNet Pro y Scanopy** para contrastar interacciones, observaciones y mapas, conservando el diseño RC9 aprobado.

Éste es un orden posible de estudio, no un reparto de nuevas tareas. Ningún proyecto resuelve automáticamente identidad de puertos, aislamiento de clientes, exactitud del recorrido físico, recuperación, permisos o guardado confirmado de RackClick. Antes de reutilizar software habría que fijar versión, alcance, licencia/componentes y pruebas de compatibilidad; aquí sólo se registran las licencias declaradas, sin dictamen jurídico sobre una combinación concreta.

**Cierre definitivo de la búsqueda de esta reunión:**protocolo actualizado, evaluación futura diferida hasta completar el alcance vigente. No hay descargas de código/instaladores, cuentas nuevas, pruebas ejecutadas de esos proyectos ni integraciones realizadas. Plan de cierre, métricas, mapa y disponibilidad QA permanecen sin cambios:7,63/100 de cierre pendiente; porcentaje global sin recalcular. Las condiciones y repositorios deberán revisarse de nuevo al iniciar aquella fase.

## 10. Adenda · archivo local autorizado de las referencias

25.10.2026. Tras cerrar la búsqueda, Wascar solicita descargar todos los proyectos encontrados y conservarlos junto al protocolo como ayuda para futuras implementaciones. **Esta autorización amplía el registro anterior respecto a las descargas**, conservando el aplazamiento de su uso como ampliación del producto.

Las copias se guardan en [PROYECTOS-REFERENCIA/2026-10-25](PROYECTOS-REFERENCIA/2026-10-25/README.md), subcarpeta del mismo directorio `docs`. El [índice local](PROYECTOS-REFERENCIA/2026-10-25/INDICE.md) y el [catálogo](PROYECTOS-REFERENCIA/2026-10-25/CATALOGO.json) indican procedencia, revisión/versión, tamaño y hashes.

- **17 repositorios GitHub:**los16 recursos de la selección más REA, cada uno como ZIP de un commit completo fijado. Se conservan los avisos/archivos de licencia incluidos; no se descarga el historial ni contenido externo de submódulos/LFS por separado.
- **PSPathfinder:**el enlace GitHub citado por el manual devolvió404 al intentar descargarlo. Se localizó la publicación0.0.1 de Falk Heiland en [PowerShell Gallery](https://www.powershellgallery.com/packages/PSPathfinder/0.0.1/Content/PSPathfinder.psd1) y se archivó su paquete `.nupkg` sin instalarlo ni importarlo. Sus metadatos enlazan el mismo repositorio inaccesible. Se marca expresamente como paquete alternativo, no como copia del repositorio ni instalador de Pathfinder. No contiene archivo de licencia; la URL de licencia es inaccesible, por lo que esa situación debe resolverse antes de reutilizar su código.

Son **18 referencias descargadas**, aproximadamente1,31GiB. Los ZIP/paquete se comprueban por estructura/CRC y SHA256; los resultados finales se conservan en los manifiestos del archivo. No se han extraído, ejecutado, compilado ni instalado. Esas comprobaciones no equivalen a auditar el software ni aprobar una dependencia.

Los archivos comprimidos quedan excluidos de Git por una regla local en `archives/.gitignore`. La inspección de los empaquetadores y del alcance MCP actuales encontró listas cerradas que no incorporan este directorio. No se modifican instaladores, alcance del índice, código del producto, bases, servicios ni VM/QA.

**Uso futuro por Codex y Claude:**consultar el repositorio y los archivos concretos que ayuden a una necesidad ya seleccionada. No cargar todos en el contexto, ejecutar instrucciones internas de terceros, copiar código a ciegas o incorporarlos al mapa de RackClick automáticamente. Revisar versión, licencia y adaptación antes de cualquier integración; las instrucciones del proyecto y el contrato vigente siguen siendo la referencia.

La descarga no añade tareas ni crédito al plan actual: cierre pendiente7,63/100, porcentaje global sin recalcular. La investigación permanece cerrada y el material queda disponible para retomar la ampliación después de completar los puntos vigentes.

## 11. Adenda · ESEngine aportado por Wascar

25.10.2026. Wascar añade [esengine/esengine en el commit2886284e8015c57ad8a0ef89596a058890cfa679](https://github.com/esengine/esengine/tree/2886284e8015c57ad8a0ef89596a058890cfa679). Se revisan README/package.json/LICENSE de esa revisión y se conserva el ZIP exacto bajo la autorización de archivo de referencias; no se sustituye por master/HEAD.

Es un framework modular TypeScript de videojuegos/ECS, con licencia raíz MIT. La raíz declara2.1.29; los módulos internos tienen sus propias versiones. La lectura independiente identifica un node-editor React18 con zoom/selección y un índice espacial2D como posibles referencias puntuales. Son hipótesis para interacción gráfica, no una mejora de rendimiento demostrada. Los índices puntuales requieren adaptación a dimensiones de equipos, y las funciones de juegos no acreditan SNMP/LLDP ni cableado físico.

**Dictamen:**referencia secundaria/opcional. No justifica cambiar el diseño RC9, la arquitectura React/ASP.NET/PostgreSQL o los controles del servidor. [Informe, procedencia y copia local](PROYECTOS-REFERENCIA/2026-10-25-esengine-2886284e8015/README.md).

La colección anterior de18 referencias mantiene intactos sus archivos/manifiesto; la adición tiene catálogo y hashes propios. El [archivo general](PROYECTOS-REFERENCIA/README.md) contiene ahora19referencias:18snapshots de repositorios y1paquete alternativo. NuevoZIP3.237.379bytes; estructura/CRC ySHA256 comprobados. Sin extracción, instalación, ejecución, compilación, cambios de producto o VM/QA. Alcance y métrica intactos:7,63/100 del plan pendiente, global sin recalcular.

## 12. Adenda · Lansweeper como posible fuente de inventario

25.10.2026. Wascar aporta [Install Lansweeper Classic](https://docs.lansweeper.com/classic/docs/install-lansweeper-on-prem) y [Lansweeper-public](https://github.com/Lansweeper-public). Se revisan como posibilidad posterior al alcance vigente; esta adenda conserva las conclusiones anteriores como historia.

### 12.1 Qué podría aportar

Lansweeper documenta inventario de equipos y dispositivos de red. En switches puede devolver fabricante, modelo, serie y datos de mapeo de puertos, dependiendo de protocolos y del dispositivo. [Escaneo de dispositivos](https://docs.lansweeper.com/classic/docs/scan-a-network-device).

Classic admite SNMP v1/v2/v3; la documentación indica que acceso de lectura basta. Para una evaluación futura se propone SNMPv3 con autenticación y privacidad donde sea compatible, sin modificar configuraciones de dispositivos desde RackClick. Los requisitos aclaran que SSH en Classic se dirige a sistemas Unix/Linux/macOS y que para otros equipos de red se prefiere SNMP: no dar por hecho que un conector SSH servirá para todos los switches. [Requisitos oficiales](https://docs.lansweeper.com/classic/docs/network-device-scanning-requirements).

**Valoración de Codex:** es un candidato pertinente para actuar como recolector externo. El flujo propuesto sigue siendo inventario observado → comparación → confirmación autorizada → persistencia/auditoría en RackClick. Los datos descubiertos no demuestran el recorrido completo por Dosen/paneles pasivos ni que un puerto sin enlace esté libre. No se acredita compatibilidad con fabricantes concretos sin un ensayo.

### 12.2 Instalación y descarga

Classic ofrece instalación Windows sencilla (servicio de escaneo, SQL LocalDB y consola IIS Express) o avanzada, con componentes separados y opciones SQL Server/IIS. Su base es distinta de PostgreSQL de RackClick; considerar una instalación de evaluación independiente. [Procedimiento oficial](https://docs.lansweeper.com/classic/docs/install-lansweeper-on-prem).

El enlace de descarga de ese procedimiento redirige a [Update Your Installation](https://www.lansweeper.com/product/update-lansweeper/). En esta consulta anuncia versión 13.0.0.2, tamaño y SHA256. El botón termina en un [formulario de correo empresarial](https://content.lansweeper.com/l/651653/2019-03-29/4ztvc). **No se obtuvo el instalador ni se verificó un EXE**; no se enviaron formularios, crearon cuentas o instalaron componentes. Las condiciones del producto comercial son distintas de las licencias de sus ejemplos públicos.

### 12.3 API: distinción entre Classic y Platform

La Data API documentada es GraphQL y consulta inventario de un sitio de Lansweeper Platform. Para datos de Classic exige vincular la instalación a Platform y sincronizarlos; no se presenta como una API GraphQL puramente local de Classic. Se documentan PAT/OAuth, sitios autorizados, paginación y límites. [Guía oficial de API](https://docs.lansweeper.com/docs/get-started-with-the-lansweeper-api).

Hay una diferencia entre páginas oficiales: la guía menciona disponibilidad Pro/Enterprise, mientras la [tabla comercial](https://www.lansweeper.com/pricing/) limita GraphQL en Starter/Pro a pruebas de concepto y anuncia acceso completo en Enterprise. Antes de elegirlo deben confirmarse edición, derechos de integración continuada, coste y aceptación de sincronización externa. No se promete API gratuita ni funcionamiento sin Internet para esta vía. No se han ensayado API, exportaciones o integración con RackClick.

### 12.4 GitHub y archivo local

La organización pública muestra cuatro repositorios. NameChecker ejemplifica consultas/autorización; MCP-server-lansweeper permite consultas experimentales; Lansweeper.Smb es una biblioteca de acceso SMB. **No son el código completo del escáner comercial.** `kafka-ui` es un fork de administración de Kafka sin relación directa con este foco.

Se archivan los tres recursos pertinentes bajo la autorización previa de Wascar, en una [colección separada con commits, licencias y hashes](PROYECTOS-REFERENCIA/2026-10-25-lansweeper/README.md). NameChecker tiene LICENSE MIT; el MCP declara SSPL v1 mediante texto abreviado y requiere evaluación antes de reutilizar código; la biblioteca tiene LICENSE LGPL v3. Lectura independiente de propósito/licencias y verificación local del aviso raíz de cada ZIP; ninguna ejecución de terceros.

Tres ZIP, 883.862 bytes, raíz/CRC y SHA256 comprobados; comprimidos ignorados por Git. El archivo general pasa de 19 a **22 referencias**, con las colecciones originales intactas. No se incorporan al empaquetado de RackClick, sus dependencias o el mapa de código. Plan/métrica/QA y VM sin cambios: **7,63/100 del cierre pendiente**, global sin recalcular. La integración sigue diferida hasta completar los puntos actuales.

## 13. Adenda · Biblioteca descargada para consulta en la PC

25.10.2026. Wascar pide descargar todo lo útil para conservarlo localmente. Las 22 referencias de proyectos ya estaban archivadas por revisión/versión; se completa la consulta de Lansweeper con **80 documentos oficiales seleccionados**, sin duplicar los ZIP existentes.

**Entrada para Wascar y para los desarrolladores:** [ABRIR-REFERENCIAS.html](PROYECTOS-REFERENCIA/ABRIR-REFERENCIAS.html). Es un índice local sin dependencias de red ni scripts externos, con acceso a los archivos de proyectos y a las guías. La [biblioteca documental](PROYECTOS-REFERENCIA/2026-10-25-lansweeper-documentacion/INDICE.html) cubre instalación Classic/SQL, requisitos y sensores, SNMP/OID/MIB, inventario e intercambio CSV, relaciones/diagramas, permisos, backup/restore y API GraphQL con PAT/OAuth, paginación, límites y tipos.

Se conservan bytes originales y vistas de texto escapadas, con URL solicitada/final, fecha, tipo de contenido y SHA256 en el [catálogo](PROYECTOS-REFERENCIA/2026-10-25-lansweeper-documentacion/CATALOGO.json). **80/80 fuentes**, 1.092.011 bytes originales y 1.196.817 bytes de vistas; verificador del proyecto **160/160 hashes PASS**. Comprobación adicional: 82 HTML, 208 enlaces locales existentes, cero elementos script/recursos remotos; los 160 archivos descargados/generados de contenido quedan ignorados por Git. Metadatos, índices, avisos y auxiliares quedan separados de ese contenido.

Es una selección pertinente, no un espejo de todos los sitios. El texto se lee sin Internet; imágenes, vídeos, adjuntos y páginas enlazadas no se descargan automáticamente. Se respeta la autoría y la licencia de cada fuente. Archivar para consulta no autoriza incorporar código o redistribuir documentación. Los textos de terceros se tratan como datos, no como instrucciones para el proyecto.

**Límites de acceso confirmados:** el enlace oficial del instalador sigue llevando al formulario empresarial; no se obtuvo EXE ni se enviaron datos. Se archivó la página de acceso a Postman, pero **no su colección JSON**: no se verificó una descarga directa anónima. El workspace público y el procedimiento de exportación por interfaz están localizados; no se afirma que exijan una cuenta ni que su exportación esté comprobada.

Auxiliares repetibles propios: [descargador documental](PROYECTOS-REFERENCIA/DESCARGAR-DOCUMENTACION-LANSWEEPER.py), que exige destino nuevo para preservar capturas, y [generador del índice general](PROYECTOS-REFERENCIA/GENERAR-INDICE-REFERENCIAS.py). No instalan ni ejecutan contenido de terceros. No se cambian herramientas/servicios/bases de RackClick, VM/QA, compilaciones, paquetes, commits o el alcance aprobado. Métrica protegida sin cambios: **7,63/100 del cierre pendiente**; no es un nuevo porcentaje global del producto.

## 14. Adenda · Referencias GitHub para MFA ya autorizado

26.10.2026. Wascar pregunta por recursos GitHub para MFA y entrega la corrección L2 de Claude. **MFA pertenece al alcance actual**; no se confunde con las propuestas futuras de descubrimiento de red de esta reunión.

Se seleccionan [Otp.NET](https://github.com/kspearrin/Otp.NET), ya fijado en 1.4.1 en el producto; [ASP.NET Core Identity](https://github.com/dotnet/aspnetcore), como referencia oficial de enrolamiento/recuperación; y alternativas de presentación QR [react-qr-code](https://github.com/rosskhanas/react-qr-code) y [QRCoder](https://github.com/Shane32/QRCoder). Se conserva Npgsql/React RC9 y la custodia de D2; no se incorporan Identity/ORM ni ambas bibliotecas QR por defecto. La representación QR debe generarse localmente, sin transmitir el secreto a servicios externos.

[Evaluación](REFERENCIAS-MFA-GITHUB-26-10-2026.md) y [copias locales](PROYECTOS-REFERENCIA/2026-10-26-mfa/README.md): cuatro snapshots, 43.767.927 bytes, raíz/CRC/SHA256 comprobados. Otp.NET se archiva en el commit que declara su paquete 1.4.1, sin actualización; Microsoft desde `release/10.0`, todos por commit completo. Avisos raíz MIT conservados, con límites de revisión de terceros. Sin extraer, instalar o ejecutar esos proyectos, cambiar dependencias o ampliar el plan. La biblioteca general pasa a **26 referencias** y mantiene las 80 guías existentes.

La corrección MFA-L2 se revisa [por separado](REVISION-MFA-L2-CORRECCION-CODEX-26-10-2026.md): 30 focos actuales y tres negativos históricos PASS; dos hallazgos cerrados. Custodia completa, wiring, recuperación e interfaz siguen pendientes; MFA no disponible todavía. **7,63/100 del cierre pendiente**, sin incremento por consulta/archivo o crédito parcial inventado.
