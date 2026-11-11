# F-06.02 · integración nativa de inventario de backup

09.11.2026. Continuación del paso20; D/E conservados. Plan del subproyecto operativo de metadatos. No concede retirada ni modifica los pesos del cierre.

**Objetivo:** producir y comprobar un inventario lateral desde el operador Windows, con censo y dump en una misma instantánea PostgreSQL. Reutilizar `MfaKeyRetention`, RCKEY/RCKPAY y el backup SQL cerrado de dos archivos.

**Arquitectura:** CLI local de dos mensajes, sin listener, con conexión de backup separada recibida por stdin. Mantiene RepeatableRead/read-only y un snapshot exportado hasta concluir el dump. Un operador nuevo publica sólo en destinos exclusivos privados, separa `database/` de `mfa-inventory.json`, y registra los pines en otro directorio privado. Un consumidor requiere el pin externo de ese recibo; no deduce confianza o completitud de un archivo recalculado.

**Restricciones:** .NET10.0.401/Npgsql10.0.3/PG17.11/esquema45; sin dependencias ni migraciones. Sólo nombres nativos `rc_db_<uuid>`, propietario `rc_owner_<uuid>` y rol `rc_backup_<uuid>` sin DML/DDL/superprivilegios. Sobre ya exportado fuera del servidor y clave introducida interactivamente, nunca argv. El operador no copia el sobre al backup. El registro no declara catálogo global completo ni expira backups. No toca anillo, claves, factores, usuarios, servicios o VM.

## Tareas y propiedad

- [x] CLI: `MfaBackupInventoryCommand.cs` y `MfaBackupInventoryCommandTests.cs`; propietario agente backend. Mensaje inicial `operation=snapshot`, `installationId`, `connectionString`, `envelopeBase64`, `envelopePassword`; respuesta `snapshot_ready`/snapshot. Mensaje final exacto `backupId`, `manifestSha256`, `dumpSha256`; respuesta inventario base64/SHA256. Rama `operation=verify` consume inventario y pines externos, sin conexión. Límites, campos exactos, Unicode inválido, errores sanitizados, cancelación/EOF/timeout y cierre de transacción. No IO de archivos.
- [x] Coordinador: wiring de Program, operadores nuevos `New-RackClickMfaDatabaseBackup.ps1`, `Test-RackClickMfaDatabaseBackup.ps1`, auxiliar compartido y tests Python/harness PG. CLI antes del host, exclusión mutua de modos. Copia de fuentes/build aislada. Rojo de protocolo/operador, verde nativo PG y restauración del dump a otra DB sintética para contrastar versiones con escritura concurrente después de exportar snapshot.
- [x] Revisor distinto: contraste del conjunto final, negativo real de pins/paquete/snapshot, sin modificar producto. Registrar límites, actualizar continuidad/CHANGELOG/evidencia y generadores. F06.02 permanece `in_progress`/+0 hasta retirada real con coordinador/fence/publicación recuperable; no se atribuye a una prueba de metadatos.

## Focos de revisión

- Identidad DB/rol/propietario equivocada: rechazo antes de dump/salida positiva.
- Escritor concurrente tras snapshot: no entra en el censo ni dump de esa operación; no se presenta snapshot como lease para retirar.
- Sobre sin una versión necesaria, contraseña incorrecta, stdin truncado o error pg_dump: ningún backup completo/recibo positivo; conservar parcial.
- Contenido o pin alterado, tercer archivo histórico, ruta existente o reparse: rechazo; no sobreescribir/adoptar ni borrar contenido ajeno.
- Datos sensibles: stdin privado, diagnóstico constante, proceso hijo sin hooks/profilers, entorno PG limpiado; logs/binlogs privados.

## Investigación y decisiones

Reutilizada la evidencia `f06-02-retencion` (115 pruebas de componentes y10PG); no se repite por inercia. Consulta oficial09.11.2026: [pg_dump --snapshot](https://www.postgresql.org/docs/17/app-pgdump.html), [pg_export_snapshot](https://www.postgresql.org/docs/17/functions-admin.html#FUNCTIONS-SNAPSHOT-SYNCHRONIZATION). El exportador mantiene la transacción mientras el dump importa la instantánea. Esto cubre censo/dump SQL, no la coherencia del anillo en disco ni exclusión de una retirada. No se copian bibliotecas ni cambian versiones.

Decisión: operación explícita nueva; el backup diario histórico conserva su formato y comportamiento. Los backups anteriores sin inventario siguen siendo dependencias desconocidas que bloquean la retirada. Un recibo externo auténtico liga un backup; no demuestra que estén registrados todos los backups.
