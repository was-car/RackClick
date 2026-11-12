# Administración · datos de ejemplo y copias de inventario

12.11.2026. Implementación autorizada por Wascar tras aprobar la propuesta del panel. Trabajo aislado desde `98ad435`; las instalaciones A/B/D/E se conservan.

## Resultado de esta entrega

Un panel EN/DE/ES en Administración permite cargar Demo50, descargar una copia de todos los clientes y restaurar esa copia sobre inventario vacío. Conserva cuentas, permisos, sesiones y MFA. Los nombres escritos por las personas no se traducen.

La etiqueta es **Copia de inventario**: contiene clientes, sitios, edificios, salas, racks, equipos, grupos de puertos, puertos y conexiones, con UUID, montajes y metadatos. No contiene cuentas, credenciales, factores, claves, grupos de seguridad, preferencias ni plantillas privadas/compartidas. No es `pg_dump` ni recuperación de Windows. Las guardias Restore48 permanecen. No se sobrescribe ni fusiona inventario existente en esta entrega.

## Contrato

- Requiere sesión vigente y concesiones globales `systemhaus.manage` y `security.manage`; además `inventory.read`/`reports.export` al exportar y `customer.create`/`inventory.edit` al importar. Validación también en servidor, incluida después de esperas y antes de commit.
- Archivo cerrado `RackClickInventoryBackup`, versión1, esquema48, fecha UTC, clientes con id/nombre/revisión y sus ocho colecciones. Límite de archivo32MiB, 100000 filas y 500 clientes. Propiedades desconocidas/duplicadas y relaciones/modelos inválidos se rechazan. Sólo columnas/tablas internas autorizadas; nunca ejecutar SQL del archivo.
- Copia consistente bloqueando Systemhaus y revisiones de clientes; auditoría sólo metadatos, archivo con longitud/SHA256 comprobados antes de descargar.
- Restauración y Demo50 en una transacción: vacío bajo bloqueo de Systemhaus, UUID conservados, relaciones/capacidad/perfiles/puertos/cables validados, revisión/auditoría/recibo confirmados con commit. Cuenta y MFA no se importan ni se alteran.
- Demo50 reutiliza los 50 JSON sintéticos versionados `development/examples/demo50-trilingual03/DATOS-DEMO50`, con sus pins. 50 clientes,66 sitios,88 edificios,226 salas,180 racks,1563 equipos,2869 grupos,20665 puertos y2207 conexiones.
- Idempotency-Key + actor + revisión esperada y digest de contenido. Replay precede al rechazo por destino ya poblado; recibo propio recuperable con autoridad actual. No repetir automáticamente tras respuesta incierta. UI conserva intención no secreta, permite consultar y muestra fases reales, sin porcentajes inventados.
- Cancelación expresa de una solicitud pendiente mediante el mismo bloqueo de operación: si ya se confirmó, recupera ese recibo; si no, registra una cancelación que impide su ejecución posterior. `notRecorded` por sí solo no desbloquea el panel. Se reutiliza el patrón de fence de `UserPreferences` en `operation`, sin tabla nueva: `operation_cancellation` exige cliente y no sirve para un destino global vacío.
- Vista previa antes de restaurar; confirmación expresa de cada importación. La comprobación de vacío de la vista no sustituye la de la transacción.
- No nueva dependencia ni migración SQL. Distribución de aplicación48 nueva identificada por hash, edición Windows20 nueva y Release propia.19 se conserva.

## Investigación y decisión

Reutilizar `InventoryStore.Snapshot`, lectores `InventoryJson`, validadores físicos de InventoryStore y patrón operation/audit existente. El exportador actual es sólo por cliente y no incluye nombre. El replay Demo50 por HTTP tiene2553 comandos y no es una transacción global: se conserva como referencia, no como restaurador del panel.

Los operadores PostgreSQL necesitan rol de backup separado; la recuperación completa requiere autoridad CREATEDB y material MFA, y Restore48 sigue bloqueado. No elevar el host ni darle DDL para añadir un botón.

Fuentes primarias: [ASP.NET Core, carga de archivos](https://learn.microsoft.com/en-us/aspnet/core/mvc/models/file-uploads?view=aspnetcore-10.0), [PostgreSQL17, copias SQL](https://www.postgresql.org/docs/17/backup-dump.html). Sin paquetes copiados ni cambios de versiones/licencias.

## Aceptación

Laboratorio PostgreSQL17 nuevo y rol runtime sin DDL; carga50 completa, recarga y segundo login, copia/restore en otra base, igualdad de las nueve colecciones y seguridad invariable. Negativos de permisos/CSRF/Origin/cuerpo excesivo/copia alterada/relaciones/modelos/vacío/concurrencia/replay/rollback. GUI con selección de archivo, confirmación y consulta de resultado incierto. Revisión independiente y empaquetado/hash/descarga antes de publicación. Prueba instalada por Wascar posterior; no acreditarla por laboratorio.
