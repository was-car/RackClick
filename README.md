# RackClick · desarrollo privado

Documentación visual de infraestructura y cableado de red, con GUI RC9/Click-Click y servidor ASP.NET Core/.NET 10, Npgsql directo y PostgreSQL 17. Todos los usuarios trabajan desde el navegador.

## Estado de esta copia

Foto de fuentes de desarrollo para `was-car/RackClick` privado, 26.10.2026. No es una release, un instalador verificado o una adopción de producción. MFA está en desarrollo y no se habilita todavía. El escritor inicial L2c tiene pendiente MFA-L2C-01 (identidad del staging), descrito en docs/REVISION-MFA-L2C-CODEX-26-10-2026.md.

La cifra acreditada es 7,63/100 del plan de cierre pendiente; no un porcentaje global nuevo del producto. Los bloques parciales se distinguen de la candidata/QA final.

## Estructura

- `development/server`: servidor, dominio, SQL y pruebas.
- `development/frontend`: GUI y pruebas; usa la referencia RC9 de `reference/`.
- `development/windows-service`: host del servicio Windows.
- `tools`: herramientas propias de desarrollo, verificación y empaquetado.
- `docs`: selección de contratos, decisiones y guías.

## Preparar desarrollo

Leer AGENTS.md y docs/CONTINUIDAD-CODEX.md. Mantener SDK10.0.401 exacto de global.json; no actualizar pins silenciosamente. Herramientas oficiales: development/toolchain.lock.json y tools/windows/Initialize-Toolchain.ps1. El frontend usa Build-Frontend.ps1; el servidor usa su solución/csproj y locks. Consultar los README de cada componente.

Los laboratorios requieren identidades y secretos nuevos locales. No se incluyen conexiones, usuarios o datos de ninguna instalación existente. Las pruebas PostgreSQL/Windows necesitan su entorno real; no se declaran ejecutadas por publicar esta copia.

## Alcance de la publicación

Se conserva el historial original en la PC. Esta copia inicia un historial seleccionado: excluye laboratorios, backups/dumps, claves/certificados, diagnósticos, transcripciones, evidencias históricas masivas, instaladores/candidatas y archivos de terceros descargados para investigación. El ZIP RC9 es una entrada de fuentes necesaria para compilar el frontend, no un instalador del servidor.

Parte de las pruebas y empaquetadores históricos necesita artefactos/evidencias locales excluidos: no se garantiza reproducir esos ensayos o los instaladores congelados desde este clon. `npm run test:build` tiene una referencia a un archivo ausente y no se presenta como chequeo funcional. Las guías/documentos históricos pueden contener enlaces a material local no publicado.

No se incorpora una licencia abierta al código propio con esta publicación privada. Se mantienen los avisos de terceros; revisar sus obligaciones antes de redistribuir paquetes o abrir el repositorio.

## Actualizaciones

Investigar antes de implementar, pruebas pertinentes, revisión independiente, selección de archivos, escaneo de secretos y commit. No añadir `.local`, exports QA, backups o todos los archivos con `git add -A`. La publicación del código no modifica el servidor QA.

No hay CI/deploy automático activado en esta copia. Antes de configurarlo, adaptar los tests Windows/DPAPI y sus dependencias; no prometer verde de Linux para esas pruebas.

La copia exportada sustituye cuatro contraseñas constantes de fixtures por generación CSPRNG al ejecutar las pruebas. PUBLICATION-TRANSFORMS.json registra rutas y hashes sin valores; las fuentes originales no se editaron. Auxiliares de cierre histórico quedan excluidos.

El escritor L2c y sus tests se fijan a la última fuente revisada indicada en PUBLICATION-TRANSFORMS.json. Cambios concurrentes posteriores permanecen en el workspace original y se incorporarán tras su revisión.
