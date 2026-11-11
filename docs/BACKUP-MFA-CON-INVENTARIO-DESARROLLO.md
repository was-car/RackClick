# Backup SQL con inventario MFA · operador de desarrollo

09.11.2026 · Extensión explícita de F-06.02. No actualiza D, el backup diario instalado o la candidata16. No es una orden de retirada de claves.

## Entrada y confianza

Se usa una publicación de fuentes que incluya `--mfa-backup-inventory`, un runtime .NET10 oficial ya instalado, PostgreSQL17.11 y el perfil privado del rol `rc_backup_<uuid>`. El ID debe coincidir con la DB `rc_db_<uuid>` y su propietario `rc_owner_<uuid>`. No sirve la cuenta de ejecución ni una conexión de otro laboratorio. El rol no necesita DML, DDL ni pertenencias a otros roles.

El directorio de herramienta contiene `SHA256SUMS`, con `hash  ruta/relativa` por archivo, excluido el propio índice. Se entrega su SHA256 por una referencia de confianza separada. Se verifican y retienen los archivos mientras corre el hijo; no se acepta añadir DLL o modificar dependencias. Esta referencia de desarrollo no convierte los binarios en instalador aprobado ni instala un runtime.

El sobre RCKEY ya exportado debe estar disponible en un medio del custodio, junto con su hash independiente. La contraseña se solicita con `Read-Host -AsSecureString` y se transporta al hijo por stdin; no se escribe en argv, perfil o recibo. El proceso sí necesita copias administradas temporales: no se promete borrado universal de memoria. El sobre **no se copia** al backup ni al registro; el custodio lo conserva fuera del servidor y sus backups. El laboratorio usa material exclusivamente sintético.

## Crear una copia nueva

`tools/windows/New-RackClickMfaDatabaseBackup.ps1` recibe:

- `PostgresBinPath`, `ProfilePath`, `DotnetPath` y `ToolDirectory`: ubicaciones explícitas verificadas, sin búsqueda automática de una instalación.
- `ExpectedToolSumsSha256`, `InstallationId`, `EnvelopePath` y `ExpectedEnvelopeSha256`.
- `DestinationPath`: carpeta nueva de backup; el padre ya existe. Nunca se adopta ni sustituye un destino existente.
- `RegistryDirectory`: directorio privado existente y separado del destino. El operador no inicializa un catálogo global ni retira registros.

La CLI valida el sobre y la identidad antes de crear la salida. Mantiene una transacción PostgreSQL RepeatableRead/read-only y exporta su snapshot. El mismo snapshot pasa a `pg_dump --snapshot`; la CLI continúa abierta hasta recibir los hashes finales. Esto liga el censo de factores al dump incluso con escrituras concurrentes posteriores, sin bloquearlas ni afirmar que sea un permiso de retirada.

La salida terminada contiene:

```text
<destino nuevo>/
  database/
    manifest.json
    data.dump
  mfa-inventory.json
<registro privado separado>/
  <backupId>.json
```

`database/` conserva exactamente los dos archivos y ocho campos del formato histórico. El lateral incluye versiones pendientes/activas/deshabilitadas, versiones del sobre y la activa requerida también con cero factores. El recibo liga instalación, backupUUID e inventario/manifiesto/dump/sobre mediante SHA256. La salida imprime `backupId` y `receiptSha256`; el custodio debe conservar este pin independientemente del conjunto transferido. Un archivo y su hash recalculado por el receptor no autentican la procedencia.

Un fallo conserva los parciales, incluido `INCOMPLETE.json` cuando ya se creó el destino. No se reintenta, sobreescribe ni elimina automáticamente. Un registro escrito antes de un corte no convierte por sí solo el intento en completo. El consumidor rechaza la marca incompleta y entradas extra.

## Comprobar una copia

`tools/windows/Test-RackClickMfaDatabaseBackup.ps1` necesita `DotnetPath`, `ToolDirectory`, `ExpectedToolSumsSha256`, `BackupDirectory`, `ReceiptPath` y **`ExpectedReceiptSha256` externo**. Comprueba el recibo canónico, el manifiesto/dump histórico y el inventario lateral usando la misma CLI en modo `verify`, sin conexión DB ni contraseña del sobre. Devuelve las versiones requeridas; no devuelve claves ni inicia un servicio.

`mfa_backup_inventory_verified` acredita integridad/vínculos contra las referencias suministradas. No prueba la custodia externa actual, la disponibilidad de cada clave en disco, el acceso del servicio, la integridad de todos los digests de migración, un Restore completo o un catálogo global exhaustivo. Los indicadores `catalogComplete=false` y `retirementAuthorized=false` son deliberados.

## Continuación de F-06.02

Los backups anteriores sin este inventario siguen siendo dependencias desconocidas. No se inventa un catálogo vacío o completo ni se da por expirado un backup. Antes de retirar una versión hacen falta registro autoritativo completo, exclusión/fence, recenso y validación del material vivo, y publicación recuperable del anillo conforme a F-06.01/.03. Este operador cubre producción y consumo nativos de metadatos; no resuelve esas compuertas ni cierra por sí solo el paso20.

Investigación y secuencia: [plan](PLAN-F0602-INTEGRACION-BACKUP.md), [contrato de retención](CONTRATO-INVENTARIO-RETENCION-MFA-v1.md), [PostgreSQL17 · pg_dump](https://www.postgresql.org/docs/17/app-pgdump.html), [sincronización de snapshots](https://www.postgresql.org/docs/17/functions-admin.html#FUNCTIONS-SNAPSHOT-SYNCHRONIZATION).
