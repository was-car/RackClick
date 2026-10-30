# RackClick · servidor y documentación de red

**Repositorio privado de desarrollo · actualización 30.10.2026.** RackClick documenta clientes, sitios, edificios, salas, racks, equipos, puertos y conexiones. Conserva el diseño RC9 y el flujo Click-Click para recorrer y conectar infraestructura.

## Empezar

**[Instalación desde GitHub, paso a paso](docs/INSTALACION-DESDE-GITHUB.md)**: requisitos, herramientas oficiales, compilación, arranque, acceso privado, datos sintéticos y parada. No requiere una base existente. El laboratorio sólo escucha en este Windows y conserva las bases que crea.

La instalación como **servicio Windows con HTTPS** tiene un [manual propio de edición 10](docs/PASOS-COMPLETOS-INSTALADOR10-WASCAR.md). Su instalador binario permanece en la entrega privada local, pendiente de cerrar las condiciones de redistribución; no se incluye ni se publica como Release en este repositorio. La demo de fuentes no sustituye ese servicio ni habilita MFA.

## Qué contiene esta actualización

| Parte | Estado |
|---|---|
| ASP.NET Core/.NET 10, Npgsql directo y PostgreSQL 17 | Fuentes congeladas de la candidata 10, esquema 15. Migración e identidad de ejecución separadas. |
| Frontend React/JavaScript/TypeScript | GUI RC9, jerarquía, inventario, grupos/permisos y panel MFA. Sin CDN en ejecución. |
| MFA | Enrolamiento, login/verificación, gestión propia y administrativa, claves Windows/DPAPI y política de 45 días. Cuenta administrativa probada por Wascar en la candidata nativa. Recuperación portable y aceptación completa pendientes. |
| Ejemplo sintético | 10 clientes, 68 racks, 311 equipos, 5408 puertos y 623 conexiones. Inventario canónico, sin usuarios, contraseñas, sesiones ni secretos MFA. |
| Arranque de demostración | `tools/start_demo.py`: base nueva, importación confirmada, credenciales locales aleatorias y parada de sus propios procesos. HTTP en loopback; proveedor MFA desactivado explícitamente. |
| Plan y requisitos | [Hoja de ruta maestra](docs/HOJA-DE-RUTA-MAESTRA.md), trazabilidad RC10 y registro de peticiones pendientes. |
| Investigación | [Fuentes oficiales y repositorios originales](docs/FUENTES-OFICIALES-DESARROLLO.md), con criterios de licencia, compatibilidad y reutilización. |

Versiones fijadas: SDK 10.0.401, runtime 10.0.12, PostgreSQL 17.11, Node 24.21.0, esbuild 0.25.10, Npgsql 10.0.3 y Otp.NET 1.4.1. No actualizar silenciosamente `global.json` ni los locks para sortear una restauración fallida.

## Qué sigue pendiente

Esta publicación no es adopción del servidor final. Faltan recuperación integral de secretos/MFA, rotación/códigos/emergencia, variantes y aceptación de inventario, paridad RC10, mejora visual de administración, backups desde el dashboard, instalación/red/actualización completas, rendimiento medido, licencias y QA final. El [índice de cierre](docs/HOJA-DE-RUTA-MAESTRA.md) mide el pendiente: 9,76/100; no es un porcentaje global nuevo del producto.

Los documentos históricos conservan resultados anteriores y pueden enlazar evidencias privadas no publicadas. La guía anterior y la hoja de ruta tienen precedencia para continuar. Algunos empaquetadores históricos dependen de artefactos `.local` excluidos y no reconstruyen por sí solos los ZIP congelados.

## Datos, seguridad y procedencia

El código propio no recibe una licencia abierta por alojarse aquí. Se conservan los avisos de terceros y la [revisión de publicación](docs/REVISION-PUBLICACION-30-10-2026.md). No copiar imágenes ni módulos de terceros sin revisar sus términos.

No se publican laboratorios, bases, credenciales, claves, sobres MFA, certificados privados, binlogs, transcripciones ni resultados personales de QA. El ejemplo es sólo inventario sintético; cada instalación necesita sus propias identidades y secretos. [PUBLICATION-TRANSFORMS.json](PUBLICATION-TRANSFORMS.json) registra las seis contraseñas de fixtures sustituidas por generación aleatoria en esta selección, sin cambiar el código de producto congelado.

No hay despliegue automático ni CI que se anuncie como verde. Las pruebas Windows/DPAPI/PostgreSQL necesitan su entorno real. Los pasos efectivamente repetidos sobre esta selección se registran en [PUBLICACION-GITHUB-30-10-2026.md](docs/PUBLICACION-GITHUB-30-10-2026.md).
