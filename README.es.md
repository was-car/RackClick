# RackClick

**[English](README.md) · [Deutsch](README.de.md) · [Español](README.es.md)**

RackClick documenta infraestructura de red mediante una vista interactiva de racks, equipos y conexiones físicas. Selecciona dos puertos con **Click–Click** para documentar un cable y seguir sus extremos por la infraestructura del cliente.

El servidor lleva la interfaz offline consolidada a datos compartidos con permisos comprobados en el servidor. La jerarquía es **Systemhaus → clientes → sitios → edificios → salas → racks → equipos → puertos y conexiones**. Las tomas y los dispositivos finales de sala también forman parte del inventario.

## Instalar en Windows Server

Descarga el **[instalador Windows Online20](https://github.com/was-car/RackClick/releases/tag/windows-online20-schema48-admin-data)** y su SHA256 externo; sigue el **[manual completo EN/DE/ES](docs/INSTALACION20-PASO-A-PASO.md)**. La descarga es pública y no requiere cuentaGitHub. Usa Windows Server2025 x64 nuevo con Escritorio e Internet, sin controlador de dominio. Las dependencias se adquieren y verifican desde sus proveedores oficiales; no necesitas compilar.

Desde **Administración → Datos y copias de inventario** puedes cargar los50clientes sintéticos sobre inventario vacío, descargar una copia de todos los clientes y previsualizar/restaurar eseJSON en otro destino vacío. Las cuentas, permisos yMFA del destino se conservan. La copia es sólo inventario; no incluye seguridad, plantillas privadas/compartidas niWindows. Restore48 completo y cambio automático de red48 permanecen bloqueados.

La edición20 incorpora el panel nuevo; el ensayo nativo de su instalación desde cero está pendiente. La [edición19 conservada](docs/PUBLICACION-ONLINE19-12-11-2026.md) sí fue ensayada enB con servicio,HTTPS,50clientes ydatos trasreinicio; su primer verificadorautomático falló yelmanual pasó. No atribuir eseensayo a20. Candidata de pruebas, sin adopción productiva final.

## Qué incluye

- Frontal y trasera interactivos, montaje físico y bandejas, estados de puertos, cableado y documentación de alimentación/PoE.
- Catálogo con búsqueda: **884 revisiones de perfiles para 877 modelos comerciales distintos**, incluidos los 506 seleccionados originalmente, routers de proveedores alemanes y repetidores. Una revisión no equivale a otro modelo físico.
- Inventario compartido, ámbitos de clientes, grupos de usuarios y clientes, capacidades, auditoría y guardado confirmado.
- Enrolamiento/login MFA y administración de usuarios nativos. La política concede **45 días** antes de exigir MFA; los administradores globales del Systemhaus están exentos.
- Interfaz en **inglés, alemán y español**. La presentación del proyecto y la guía de demostración desde fuentes están en esos tres idiomas; los registros técnicos históricos conservan su idioma original.

## Probar las fuentes

Sigue la **[guía de demostración desde fuentes para Windows](docs/INSTALACION-DESDE-GITHUB.md)**: requisitos, descarga, herramientas oficiales fijadas, compilación, comprobación, acceso y parada.

El ejemplo contiene **10 clientes sintéticos, 68 racks, 311 equipos, 5408 puertos y 623 conexiones**. Es sólo inventario, sin cuentas, sesiones ni factores MFA. Cada arranque crea otro laboratorio PostgreSQL local con credenciales aleatorias. La demo usa HTTP en loopback y desactiva explícitamente MFA; no es el instalador del servicio Windows ni un despliegue de red.

La **[Demo50 trilingüe opcional](docs/DEMO50.es.md)** contiene **17 nombres de empresa ficticios en inglés, 17 en alemán y 16 en español**, con 180 racks, 1.563 equipos, 20.665 puertos y 2.207 conexiones. Abre su [visor HTML](development/examples/demo50-trilingual03/DATOS-DEMO50/VER-50-CLIENTES.html) desde el clon descargado. El inventario de origen sigue en esquema43 y cubre 868 parejas perfil/revisión históricas; el catálogo actual tiene 884 revisiones. El cargador revisado requiere un servidor48 vacío y no importa autenticación. La demo de diez clientes desde fuentes sigue siendo independiente.

## Estado de desarrollo · 12 de noviembre de 2026

El esquema actual de las fuentes es **48**. La instalación Windows de pruebas A contiene los **50 clientes sintéticos**, comprobados tras reiniciar Windows con arranque automático del servicio, validación HTTPS normal y backup contrastado. A se instaló con edición17 y una finalización acotada revisada de tareas/recibos faltantes. La edición18 corrige aquel fallo del instalador; su instalación completa desde cero todavía no se ha ejecutado. El primer chequeo automático de HTTPS tras arrancar falló; el comprobador oficial manual posterior pasó. **Restore48 sigue deshabilitado** y la aceptación productiva final está pendiente.

Los códigos de recuperación MFA, emergencia/pérdida local, rotación, catálogo de backups y retención de versiones ya tienen componentes internos implementados, revisados por otra persona y ensayos de laboratorio acotados. Sus límites individuales permanecen en el plan numerado; esto no acredita todos los escenarios de recuperación o mantenimiento en producción.

Paridad offline, recuperación, rendimiento y QA final continúan según la [hoja de ruta maestra](docs/HOJA-DE-RUTA-MAESTRA.md). Descubrimiento SNMP/LLDP y federación real de identidades son alcance posterior. Es una selección privada de fuentes en desarrollo, no una versión final adoptada para producción.

## Tecnologías y carpetas

Frontend **React/JavaScript**; servidor **C# / ASP.NET Core / .NET 10**; **PostgreSQL 17** mediante Npgsql directo y migraciones SQL.

| Ruta | Uso |
|---|---|
| `development/frontend/` | Interfaz, perfiles interactivos y pruebas frontend |
| `development/server/` | Dominio, servidor HTTP, migraciones SQL y pruebas |
| `development/hardware/` | Entradas del catálogo y referencias de modelos |
| `development/examples/` | Inventario original de diez clientes para la demo desde fuentes |
| `DEMO-50-CLIENTES-01/` | Colección opcional de 50 clientes, visor y matriz de cobertura |
| `tools/` | Fuentes de compilación, validación, demo y operadores Windows |
| `docs/` | Guías, contratos, decisiones y planificación |
| `reference/` | Referencia offline adoptada que utiliza la compilación |

La Release online distribuye la aplicación revisada y adquiere los runtimes directamente de sus proveedores oficiales. Se excluyen bases privadas, credenciales, certificados, claves MFA y registros de compilación. El acceso al repositorio no concede una licencia abierta nueva; siguen aplicando los [avisos de terceros](THIRD-PARTY-NOTICES.md). Usa los locks y herramientas documentados, sin cambiar versiones para ajustarlas a otro SDK instalado.
