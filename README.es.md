# RackClick

**[English](README.md) · [Deutsch](README.de.md) · [Español](README.es.md)**

RackClick documenta infraestructura de red mediante una vista interactiva de racks, equipos y conexiones físicas. Selecciona dos puertos con **Click–Click** para documentar un cable y seguir sus extremos por la infraestructura del cliente.

El servidor lleva la interfaz offline consolidada a datos compartidos con permisos comprobados en el servidor. La jerarquía es **Systemhaus → clientes → sitios → edificios → salas → racks → equipos → puertos y conexiones**. Las tomas y los dispositivos finales de sala también forman parte del inventario.

## Qué incluye

- Frontal y trasera interactivos, montaje físico y bandejas, estados de puertos, cableado y documentación de alimentación/PoE.
- Catálogo con búsqueda: **884 revisiones de perfiles para 877 modelos comerciales distintos**, incluidos los 506 seleccionados originalmente, routers de proveedores alemanes y repetidores. Una revisión no equivale a otro modelo físico.
- Inventario compartido, ámbitos de clientes, grupos de usuarios y clientes, capacidades, auditoría y guardado confirmado.
- Enrolamiento/login MFA y administración de usuarios nativos. La política concede **45 días** antes de exigir MFA; los administradores globales del Systemhaus están exentos. Recuperación portable, emergencia, rotación y aceptación completa siguen pendientes.
- Interfaz en **inglés, alemán y español**. La presentación del proyecto y la guía de demostración desde fuentes están en esos tres idiomas; los registros técnicos históricos conservan su idioma original.

## Probar las fuentes

Sigue la **[guía de demostración desde fuentes para Windows](docs/INSTALACION-DESDE-GITHUB.md)**: requisitos, descarga, herramientas oficiales fijadas, compilación, comprobación, acceso y parada.

El ejemplo contiene **10 clientes sintéticos, 68 racks, 311 equipos, 5408 puertos y 623 conexiones**. Es sólo inventario, sin cuentas, sesiones ni factores MFA. Cada arranque crea otro laboratorio PostgreSQL local con credenciales aleatorias. La demo usa HTTP en loopback y desactiva explícitamente MFA; no es el instalador del servicio Windows ni un despliegue de red.

## Estado de desarrollo · 3 de noviembre de 2026

El esquema actual de las fuentes es **45**. La aplicación se actualizó sobre una instalación Windows de prueba existente, con HTTPS, servicio automático y backups comprobados, conservando inventario y seguridad. Quedan la instalación limpia New/Restore y la comprobación tras reiniciar Windows de este paquete más reciente. Los ensayos anteriores no sustituyen esos recorridos.

Paridad offline, recuperación, rendimiento y QA final continúan según la [hoja de ruta maestra](docs/HOJA-DE-RUTA-MAESTRA.md). Descubrimiento SNMP/LLDP y federación real de identidades son alcance posterior. Es una selección privada de fuentes en desarrollo, no una versión final adoptada para producción.

## Tecnologías y carpetas

Frontend **React/JavaScript**; servidor **C# / ASP.NET Core / .NET 10**; **PostgreSQL 17** mediante Npgsql directo y migraciones SQL.

| Ruta | Uso |
|---|---|
| `development/frontend/` | Interfaz, perfiles interactivos y pruebas frontend |
| `development/server/` | Dominio, servidor HTTP, migraciones SQL y pruebas |
| `development/hardware/` | Entradas del catálogo y referencias de modelos |
| `development/examples/` | Inventarios sintéticos de ejemplo |
| `tools/` | Fuentes de compilación, validación, demo y operadores Windows |
| `docs/` | Guías, contratos, decisiones y planificación |
| `reference/` | Referencia offline adoptada que utiliza la compilación |

Los instaladores binarios se conservan fuera de GitHub mientras se revisan sus condiciones de redistribución. Se excluyen bases privadas, credenciales, certificados, claves MFA y registros de compilación. El acceso al repositorio no concede una licencia abierta nueva; siguen aplicando los [avisos de terceros](THIRD-PARTY-NOTICES.md). Usa los locks y herramientas documentados, sin cambiar versiones para ajustarlas a otro SDK instalado.
