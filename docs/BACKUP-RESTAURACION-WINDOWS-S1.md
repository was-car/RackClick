# Backup y restauración nativos Windows · tandas 198–207

Preparación interna S1: Windows PowerShell 5.1 de 64 bits y PostgreSQL **17.11 x64**, herramientas ya instaladas y verificadas. No requiere Python, SDK o Node para operar estos comandos. No instala servicios ni configura HTTPS; no constituye el instalador final ni la aceptación de recuperación de la aplicación. [Ejecuciones y correcciones de este bloque](../evidence/s1-20261017/treinta-tandas-188-217/database/CIERRE.md).

`tools/windows/RackClick.Backup.ps1` reutiliza sin modificar las funciones de SHA256, arquitectura PE y comprobación de versiones de la tanda 186. Los dos comandos emiten un único JSON UTF-8 y códigos de salida 0 correcto, 1 fallo operativo/incompatibilidad, 2 entrada/integridad indeterminada o rechazada. No imprimen la contraseña, argumentos SQL ni errores crudos de PostgreSQL.

## Perfil y secreto privados

Se requiere una identidad PostgreSQL local previamente creada por el administrador. El backup necesita lectura completa del origen; para restaurar se utiliza otro usuario `LOGIN NOSUPERUSER CREATEDB NOCREATEROLE` con permiso de conexión a la base de mantenimiento indicada. No se modifican roles existentes ni se conceden permisos automáticamente. El usuario de restauración será propietario de la base nueva y de sus objetos.

El perfil JSON contiene exactamente `schemaVersion`, `host`, `port`, `database`, `user` y `passwordFile`. `host` debe ser `127.0.0.1` explícito, puerto 1024–65535. Los identificadores son ASCII minúsculos, letras/dígitos/guion bajo, máximo 63 caracteres. `passwordFile` es **un archivo con la contraseña sola**, UTF-8 sin BOM, no un archivo pgpass; no se introduce la contraseña en argumentos del comando. El perfil de restauración puede usar `database: "postgres"` como mantenimiento. Nunca apuntar un ensayo al perfil del QA real.

Ejemplo de preparación en una consola PowerShell 5.1 del operador, cambiando sólo rutas/puerto/base/usuario por los de la instancia identificada. `C:\RackClick-Privado` debe ser nuevo; su directorio padre debe existir. El secreto se pide oculto y se escribe después de limitar la ACL. El administrador debe haber creado la identidad PostgreSQL y asignado permisos por su procedimiento privado.

```powershell
$PostgresBinPath = 'C:\RackClick_SVR\.local\postgresql-17.11-4\pgsql\bin'
. C:\RackClick_SVR\tools\windows\RackClick.Backup.ps1
$privatePath = New-BackupPrivateDirectory 'C:\RackClick-Privado'
$secretFile = Join-Path $privatePath 'password.txt'
$securePassword = Read-Host 'Contraseña PostgreSQL de esta identidad' -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
try {
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    [IO.File]::WriteAllText($secretFile, $plainPassword, (New-Object Text.UTF8Encoding($false)))
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    $plainPassword = $null
    $securePassword.Dispose()
}
$profile = [ordered]@{ schemaVersion=1; host='127.0.0.1'; port=55432; database='rc_origen'; user='rc_operador'; passwordFile=$secretFile }
[IO.File]::WriteAllText((Join-Path $privatePath 'profile.json'), ($profile | ConvertTo-Json), (New-Object Text.UTF8Encoding($false)))
```

El helper verifica que el propietario y las concesiones de lectura/escritura del perfil y del archivo secreto sólo correspondan al SID actual o SYSTEM. No repara una ACL amplia silenciosamente. Los archivos privados y todos los dumps permanecen fuera de Git, evidencias compartidas y paquetes de desarrollo. La contraseña existe brevemente en memoria para construir un pgpass temporal privado; éste se borra al terminar la operación. No se afirma borrado seguro de memoria/disco ni cifrado del backup.

## Crear un backup

```powershell
& C:\RackClick_SVR\tools\windows\New-RackClickDatabaseBackup.ps1 `
  -PostgresBinPath 'C:\RackClick_SVR\.local\postgresql-17.11-4\pgsql\bin' `
  -ProfilePath 'C:\RackClick-Privado\profile.json' `
  -DestinationPath 'C:\RackClick-Backups\nuevo-20261017'
```

El padre de destino debe existir y el destino debe ser **nuevo**, en volumen local fijo. Se rechazan rutas relativas/UNC, ADS, componentes ambiguos y reparse/junctions en ancestros. CreateDirectoryW crea el directorio de forma exclusiva y con ACL restringida al SID actual y SYSTEM desde su creación; no adopta un destino creado en una carrera. PostgreSQL servidor y herramientas deben ser 17.11; la conexión usa contraseña sin interacción. Variables PG heredadas se eliminan únicamente del proceso hijo; `psql` utiliza `-X -w` y `ON_ERROR_STOP`.

`pg_dump --format=custom --no-owner --no-acl` escribe primero `data.dump.partial`. Sólo tras exit 0, archivo no vacío y SHA256 se cambia al nombre final y se escribe `manifest.json`. `--no-owner` de pg_dump no controla propietarios de un archivo custom: esa política se aplica efectivamente en pg_restore. El manifiesto schema1 contiene versión, formato, nombre fijo, longitud, SHA256 y hora UTC; no contiene usuarios, contraseña ni perfil. El JSON de éxito publica `manifestSha256`: conservarlo en un registro aprobado separado del backup. Un manifiesto recibido junto a su propio hash no prueba autenticidad.

Se conserva íntegro el nombre Unicode de las carpetas. Las herramientas PostgreSQL17.11 observadas fallaron al recibir por argv un archivo absoluto bajo una carpeta `Ω`; el helper usa `ProcessStartInfo.WorkingDirectory` Unicode y el nombre relativo fijo `data.dump.partial`/`data.dump`. Tanto backup como restore se comprobaron así en Windows real; no se transliteran nombres ni se cambia el destino indicado.

Si falla, la salida es no cero y el directorio incompleto conserva `INCOMPLETE.json` y el parcial que exista; no se convierte en copia válida. No se sobrescribe una copia previa ni se elimina por fallo una copia válida. No se implementa retención/rotación automática.

## Restaurar solamente en una base nueva

```powershell
& C:\RackClick_SVR\tools\windows\Restore-RackClickDatabaseBackup.ps1 `
  -PostgresBinPath 'C:\RackClick_SVR\.local\postgresql-17.11-4\pgsql\bin' `
  -ProfilePath 'C:\RackClick-Restore-Privado\profile.json' `
  -BackupPath 'C:\RackClick-Backups\nuevo-20261017' `
  -ExpectedManifestSha256 '<SHA256 de la referencia aprobada externa>' `
  -NewDatabaseName 'rc_restore_laboratorio_nuevo'
```

El nombre nuevo debe satisfacer `rc_restore_[a-z0-9_]{1,48}`. Primero valida SHA256 de referencia, formato cerrado del manifiesto, los **dos archivos exactos**, longitud/hash del dump y ausencia de reparse. Mantiene handles de lectura que niegan escritura/borrado del manifiesto y del dump desde la validación hasta terminar pg_restore; los libera incluso ante fallo. No usa rutas suministradas por el manifiesto para encontrar archivos arbitrarios. Después comprueba conexión/versiones y `rolcreatedb=true` del usuario explícito, incluso si fuera superusuario. Si ya existe la base, aborta: no hay DROP, `--clean`, borrado ni restauración encima. Una carrera de creación también falla sin sobrescribir.

Se crea una base desde template0, con el propietario del perfil y conexión PUBLIC revocada. `pg_restore --single-transaction --exit-on-error --no-owner --no-acl` aplica los objetos en una transacción única y verifica el código de salida. Los roles globales/ACL previos no se recuperan. Si el restore falla, la base **nueva** queda conservada para diagnóstico, sin borrar bases ajenas; `newDatabaseCreated` distingue este caso y el rollback evita objetos parcialmente restaurados. No reintentar usando ese mismo nombre.

El éxito devuelve `restore_complete_isolated`, `newDatabaseName` y siempre `applicationStartAllowed:false`. Es una restauración aislada: las sesiones y hashes de cuentas presentes en el dump se conservan como datos; **este componente no revoca sesiones, no concede permisos runtime, no cambia la configuración ni arranca la aplicación**. Antes de activar una recuperación real hay que verificar identidad/esquema/datos, revocar sesiones según el procedimiento revisado, preparar credenciales/runtime nuevos, revocar CREATEDB temporal, probar reinicio/acceso y seleccionar la nueva base mediante el flujo de operación correspondiente. No ejecutar la aplicación contra una restauración sólo por obtener exit 0 aquí.

Un dump es código/datos de una fuente confiable; los hashes verifican integridad relativa a una referencia aprobada, no vuelven seguro un dump hostil. No se acredita cifrado, UNC/USB, retención, recuperación de roles globales, servicio/TLS ni recuperación completa ante desastre en estas tandas.

## Pruebas y evidencia

El runner de desarrollo `tools/tests/test_database_backup.py` usa exclusivamente un clúster nuevo `pg_support.Lab`, herramientas fijadas y copias/secretos bajo `.local` ignorado. Aplica SQL001–009 sin cambiarlos y datos sintéticos Unicode. Comprueba roundtrip custom y objetos/propietarios, limpieza de PG env, ACL/secretos, destinos existentes, fallo preservado, manifiesto/dump/rutas/reparse, base ya existente/CREATEDB, rollback de restore defectuoso y bloqueo de escritura del manifiesto/dump validados. El primer grupo de ocho tuvo tres PASS y cinco FAIL por el problema Unicode; se conserva completo. Tras corregirlo, los cinco afectados pasaron en un laboratorio nuevo; las tres ramas anteriores no cambiaron y no se repitieron. La revisión independiente registra sus propios casos y resultado aparte. Las ejecuciones realmente realizadas se registran en `evidence/s1-20261017/treinta-tandas-188-217/database/`; no se atribuyen pruebas históricas como nuevas. El coordinador registra aparte la integración con bootstrap/login/datos/reinicio.

Fuentes oficiales para las opciones: [pg_dump17](https://www.postgresql.org/docs/17/app-pgdump.html), [pg_restore17](https://www.postgresql.org/docs/17/app-pgrestore.html), [archivo de contraseñas libpq17](https://www.postgresql.org/docs/17/libpq-pgpass.html). Las versiones instaladas se fijan por el lock del repositorio; no se descargan ni cambian versiones en estos comandos.
