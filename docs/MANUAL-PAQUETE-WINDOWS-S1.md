# Paquete ZIP local de RackClick para validación interna

**Integración1450–1509 · candidata1449-01/esquema13.** Grupo creado→Abrir relaciones por UUID confirmado, sin asignaciones.40archivos22+18/7.159.235bytes; servidor1089 exacto. New/Restore en raíces nuevas; QA13 conserva datos/recuperación96912. Instalación definitiva y adopción pendientes.

En el inventario del cliente abre Mis plantillas privadas y pulsa Crear configuración nueva. Elige una semilla y Usar como borrador, modifica los campos tipados, Revisar configuración, confirma las etiquetas reutilizables y pulsa Guardar plantilla nueva. Se crea otra identidad; la original y sus equipos no cambian. Tras un envío incierto consulta su estado antes de repetir. Después de recargar, la definición no guardada ya no está en memoria: consulta o cancela para confirmar el fence y rehace el borrador; no hay reintento durable del blueprint. El administrador recuperado tiene su biblioteca privada propia; la del usuario original permanece ligada a ese usuario.

Las plantillas compartidas se consultan en el cliente y conservan sus etiquetas, autor y revisión. Publicar o retirar requiere templates.publish además del ámbito del cliente; el administrador asigna esa capacidad mediante grupos. Crear un equipo desde una compartida requiere escritura en el inventario. La migración de QA9 a QA10 conserva los permisos originales y no concede publicación automáticamente.

Interfaz1449-01 con servidor1089-02/esquema13 reutilizados sin compilar en1450–1509. Los paquetes337/397/532/592/712/832/849/969/1089/1209/1329 y sus informes se conservan como evidencia histórica y perfiles admitidos. Este ZIP reúne aplicación, runtime.NET10.0.12, PostgreSQL17.11 x64, operadores PowerShell y avisos de licencia. Es una entrega interna para comprobar preparación y operación en un directorio nuevo; publicación, redistribución y adopción siguen pendientes. No se necesita SDK, Node, Python o Git para operarlo. El productor de desarrollo se describe en CONSTRUIR-PAQUETE-WINDOWS-S1.md.

## Requisitos y confianza

Usar Windows PowerShell5.1 x64 en Windows11, cuenta local con permiso de crear el destino y su padre ya existente en disco local fijo. El ROOT elegido debe ser ASCII, inexistente y disjunto del ZIP y de los operadores de entrada. Elegir dos puertos loopback diferentes y libres, de1024 a65535. Otros Windows y otro equipo siguen pendientes de ensayo; la ejecución en un laboratorio de desarrollo no acredita una instalación limpia.

Obtener el ZIP y su SHA256 externo mediante el canal confiable de la entrega. El propio ZIP contiene todos los operadores necesarios; extraer primero sólo esos archivos con la receta siguiente, **después de contrastar el hash completo**. El SHA256 calculado sólo del archivo recibido sirve para contraste, no constituye aprobación de su procedencia. Los archivos dentro del paquete están ligados al inventario y al perfil337,397,532,592,712,832,849,969,1089,1209,1329 o1449 registrado por su SHA256 de manifiesto. Pasar otro hash en CLI no habilita una aplicación no registrada.

Los ejemplos usan C:\Entregas\RackClick.zip, un directorio de operadores confiables C:\Entregas\operators, y el padre ya preparado C:\Laboratorios. Sustituir HASH_ZIP_CONFIABLE por64dígitos hexadecimales de la referencia externa. Las rutas de ejemplo son locales y ASCII; nombres de usuario y Systemhaus admiten Unicode de hasta100 valores escalares según la política del servidor.

## Extraer únicamente los operadores desde el ZIP aprobado

En Windows PowerShell5.1 x64, pegar este bloque después de adaptar ZIP/hash. C:\Entregas debe existir y C:\Entregas\operators **no debe existir**. Esta preparación de comandos no reserva el ROOT de instalación. El bloque usa sólo APIs de Windows/.NET, mantiene el ZIP abierto contra escritura/borrado desde el hash hasta terminar, permite exactamente los25nombres fijados y crea archivos nuevos; todavía no ejecuta scripts del ZIP.

```powershell
$archivePath='C:\Entregas\RackClick.zip'
$expected='HASH_ZIP_CONFIABLE'
$bootstrap='C:\Entregas\operators'
$names=@(
'Invoke-RackClickPrivateDeployment.ps1','New-RackClickDatabaseBackup.ps1','New-RackClickLabHttpsProfile.ps1',
'New-RackClickLabInstance.ps1','New-RackClickPrivateDeployment.ps1','New-RackClickRecoveredInstance.ps1',
'RackClick.Backup.ps1','RackClick.Deployment.ps1','RackClick.Https.ps1','RackClick.Instance.ps1',
'RackClick.LaunchControl.ps1','RackClick.Process.Gate.ps1','RackClick.Process.ps1','RackClick.Stage.ps1',
'Test-StagedDistribution.ps1','Restore-RackClickPrivateDeployment.ps1','Stage-ServerDistribution.ps1',
'Start-RackClickLabInstance.ps1','Stop-RackClickLabInstance.ps1','Test-RackClickPrivateDeployment.ps1',
'Test-RuntimePrerequisites.ps1','Test-ServerDistribution.ps1','RackClick.OfflineBundle.ps1',
'Test-RackClickOfflineBundle.ps1','Install-RackClickOfflineBundle.ps1')
if ($expected -notmatch '^[a-fA-F0-9]{64}$') {throw 'Referencia SHA256 externa requerida'}
$inputStream=$null;$zip=$null;$sha=$null
try {
  $inputStream=[IO.File]::Open($archivePath,'Open','Read','Read')
  $sha=[Security.Cryptography.SHA256]::Create()
  $actual=[BitConverter]::ToString($sha.ComputeHash($inputStream)).Replace('-','').ToLowerInvariant()
  if ($actual -cne $expected.ToLowerInvariant()) {throw 'SHA256 del ZIP no coincide'}
  $inputStream.Position=0
  $null=[Reflection.Assembly]::LoadWithPartialName('System.IO.Compression')
  $zip=New-Object IO.Compression.ZipArchive($inputStream,[IO.Compression.ZipArchiveMode]::Read,$true)
  $entries=@($zip.Entries|Where-Object {$_.FullName.StartsWith('operators/',[StringComparison]::Ordinal)})
  if ($entries.Count -ne 25) {throw 'Inventario de operadores invalido'}
  foreach ($name in $names) {
    if (@($entries|Where-Object {$_.FullName -ceq ('operators/'+$name)}).Count -ne 1) {throw 'Operador requerido ausente o duplicado'}
  }
  $null=New-Item -ItemType Directory -Path $bootstrap -ErrorAction Stop
  foreach ($name in $names) {
    $entry=$entries|Where-Object {$_.FullName -ceq ('operators/'+$name)}
    $source=$null;$target=$null
    try {
      $source=$entry.Open()
      $target=[IO.File]::Open((Join-Path $bootstrap $name),'CreateNew','Write','None')
      $source.CopyTo($target);$target.Flush($true)
    } finally {if ($null -ne $target) {$target.Dispose()};if ($null -ne $source) {$source.Dispose()}}
  }
} finally {
  if ($null -ne $zip) {$zip.Dispose()}
  if ($null -ne $inputStream) {$inputStream.Dispose()}
  if ($null -ne $sha) {$sha.Dispose()}
}
```

Ante error conservar lo creado y elegir otro bootstrap nuevo. Los scripts de entrada proceden ahora del ZIP cuyo hash fue aprobado externamente. Los comandos siguientes vuelven a exigir el mismo hash y validan el paquete completo. El instalador ejecuta después la fábrica de su content instalado, no el bootstrap ni scripts del repositorio.

## Comprobar sin instalar

Desde PowerShell5.1 x64:

```powershell
& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -NonInteractive -File C:\Entregas\operators\Test-RackClickOfflineBundle.ps1 -ArchivePath C:\Entregas\RackClick.zip -ExpectedArchiveSha256 HASH_ZIP_CONFIABLE
```

Esperar exit0, valid=true y code=bundle_verified. La salida identifica bundleId, bundleArchiveSha256, bundleManifestSha256, applicationManifestSha256, versions, counts, verifiedFiles y uncompressedBytes. Se comprueban todos los bytes/hashes, esquema cerrado, inventario, rutas, tipos y límites antes de crear un destino. El ZIP permanece bloqueado contra escritura y borrado durante la lectura. El hash externo debe pertenecer a una fuente confiable: no hay parser adicional para detectar claves JSON duplicadas.

Se rechazan entradas directorio, rutas absolutas, backslash, traversal, ADS, segmentos vacíos, nombres DOS reservados, puntos/espacios finales, enlaces/reparse y colisiones de mayúsculas o archivo/directorio. Límites: ZIP512MiB, manifiesto8MiB, archivo256MiB, total descomprimido1GiB y10.000archivos. El perfil ZIP es single-volume, sin cifrado, métodos Store/Deflate y pie de directorio central clásico; los campos extra locales los interpreta la API ZIP bajo los mismos límites de bytes/hashes. No se modifica el ZIP ni el sistema.

## Preparar un ROOT nuevo

```powershell
& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -NonInteractive -File C:\Entregas\operators\Install-RackClickOfflineBundle.ps1 -ArchivePath C:\Entregas\RackClick.zip -ExpectedArchiveSha256 HASH_ZIP_CONFIABLE -DestinationPath C:\Laboratorios\RackClickNuevo01 -PostgresPort 55441 -HttpPort 55442 -BootstrapUser "Administrador inicial" -SystemhausName "Mi Systemhaus"
```

La salida correcta es exit0, valid=true, code=installation_prepared. Conservar installationSha256 y deploymentSha256 fuera del ROOT. El directorio contiene content, deployment, logs, installation-state.json e installation.json. Runtime y PostgreSQL permanecen en content\dependencies, fuera de deployment; los operadores usados se copian a content\operators. Todos los archivos se crean exclusivamente con CreateNew y se vuelven a verificar. La fábrica instalada recibe rutas explícitas de ese content; no busca herramientas en PATH o en el workspace.

Se crean clúster/base/cuentas/contraseñas nuevos y un perfil TLS loopback. PostgreSQL queda detenido y la web aún no se ha iniciado. La nueva credencial administrativa está únicamente en el archivo local privado C:\Laboratorios\RackClickNuevo01\deployment\instance\private\admin-login.json. Consultarla localmente como secreto, sin copiar contraseña a comandos, chats, Git o informes. No reutilizar credenciales de otro laboratorio.

El modo predeterminado es New. Su recibo installation.json schema1 se publica al final, después de comprobar el deployment en modo Full, PostgreSQL detenido y todos los hashes de content. Tiene once claves: schemaVersion, kind, id, rootPath, state, bundleId, bundleArchiveSha256, bundleManifestSha256, deploymentId, deploymentSha256 y publicOrigin. El estado contiene exactamente schemaVersion, installationId, status y code. prepared/installation_prepared es la única confirmación correcta; conservar también la referencia externa deploymentSha256 para operar. New rechaza parámetros BackupPath, ExpectedBackupManifestSha256 y RecoveryUser, incluso si se pasan vacíos.

## CRT compatible y permiso administrativo

El preflight observa el registro x64 Installed y las dos DLL System32 vcruntime140.dll/msvcp140.dll: PE x64 y versión mínima14.44.35211.0. Un CRT compatible se reutiliza aunque el ZIP contenga un redistribuible más reciente; no se copian DLL de System32 ni se cambia configuración global. Si falta, la ejecución normal termina antes de reservar ROOT con preflight_crt_prerequisite_missing.

Sólo para un equipo que realmente carezca de CRT compatible, el operador puede repetir con otro destino nuevo y -InstallPrerequisites desde una consola **ya elevada**. El comando no eleva por UAC. Antes de ejecutar exige el hash fijado, versión14.51.36247.0 y Authenticode válido de Microsoft. Usa /install /quiet /norestart y log privado. Salida0 exige nuevo inventario compatible. Salida3010 informa rebootRequired=true y fallo prerequisite_reboot_required: se requiere reinicio, no hay base creada ni recibo final de éxito. Conservar el parcial y, después del reinicio, preparar otro ROOT nuevo. Otros códigos fallan sin continuar. Esta rama global administrativa no se ha ejecutado en la sesión con token no elevado; sus decisiones se prueban por separado.

## Inspeccionar, arrancar, parar y respaldar

Usar exclusivamente los operadores instalados y HASH_DESPLIEGUE_EXTERNO obtenido de la salida válida:

```powershell
& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -File C:\Laboratorios\RackClickNuevo01\content\operators\Test-RackClickPrivateDeployment.ps1 -DeploymentPath C:\Laboratorios\RackClickNuevo01\deployment -ExpectedDeploymentSha256 HASH_DESPLIEGUE_EXTERNO
& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -File C:\Laboratorios\RackClickNuevo01\content\operators\Invoke-RackClickPrivateDeployment.ps1 -Operation Start -DeploymentPath C:\Laboratorios\RackClickNuevo01\deployment -ExpectedDeploymentSha256 HASH_DESPLIEGUE_EXTERNO
```

Start permanece en primer plano. Esperar ready y usar la URL HTTPS publicada. El certificado autofirmado loopback es temporal, de7días; no se escribe confianza en Windows ni se configura CA/DNS productivos. En otra consola:

```powershell
& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -File C:\Laboratorios\RackClickNuevo01\content\operators\Invoke-RackClickPrivateDeployment.ps1 -Operation Backup -DeploymentPath C:\Laboratorios\RackClickNuevo01\deployment -ExpectedDeploymentSha256 HASH_DESPLIEGUE_EXTERNO -BackupPath C:\Laboratorios\BackupNuevo01
& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -File C:\Laboratorios\RackClickNuevo01\content\operators\Invoke-RackClickPrivateDeployment.ps1 -Operation Stop -DeploymentPath C:\Laboratorios\RackClickNuevo01\deployment -ExpectedDeploymentSha256 HASH_DESPLIEGUE_EXTERNO
```

Guardar backupManifestSha256 externo sólo tras deployment_backup_complete. Esperar stopConfirmed=true; una solicitud de parada por sí sola no acredita la parada. Stop y Backup admiten mantenimiento con TLS caducado, Start exige Full. Detalles en OPERAR-DESPLIEGUE-PRIVADO-WINDOWS-S1.md; sus ejemplos antiguos desde workspace se sustituyen por las rutas instaladas anteriores.

## Recuperar desde backup confiable

El backup conserva base/datos, no una imagen de instalación, PKI o servicios. Sólo restaurar backups conocidos con SHA256 externo de manifest.json. Mantener el directorio local, privado, sin reparse y con exactamente manifest.json y data.dump. Si procede de USB/UNC, preparar una copia local privada y contrastar la referencia confiable. Un dump de procedencia desconocida puede ejecutar SQL: el hash no sustituye la confianza. La recuperación siempre usa otro ROOT, clúster/base/roles/administrador/TLS nuevos; conserva los datos, grupos, permisos y cuentas recuperados y revoca las sesiones copiadas. RecoveryUser debe ser un nombre nuevo.

Extraer los25 operadores **del nuevo ZIP confiable** usando el bloque anterior, en otro bootstrap nuevo; no ejecutar un instalador antiguo sobre el nuevo ZIP. Para preparar todo el content del perfil elegido y recuperar directamente un snapshot del mismo esquema SQL, usar el mismo instalador con Mode Restore:

```powershell
& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -NonInteractive -File C:\Entregas\operators\Install-RackClickOfflineBundle.ps1 -Mode Restore -ArchivePath C:\Entregas\RackClick.zip -ExpectedArchiveSha256 HASH_ZIP_CONFIABLE -DestinationPath C:\Laboratorios\RecuperadoNuevo01 -PostgresPort 55443 -HttpPort 55444 -RecoveryUser "Administrador recuperacion nuevo" -BackupPath C:\Laboratorios\BackupNuevo01 -ExpectedBackupManifestSha256 HASH_BACKUP_EXTERNO
```

Restore requiere los tres parámetros de recuperación y rechaza BootstrapUser/SystemhausName, incluso vacíos; conserva el nombre del Systemhaus recuperado. El preflight abre y fija manifest/dump antes de reservar ROOT y mantiene los handles hasta finalizar. ZIP, operadores, destino y backup deben ser disjuntos. No copia el backup al content ni lo incorpora al ZIP. La fábrica Restore usada procede de content\operators y recibe únicamente aplicación/runtime/PG de ese content verificado.

Restore no migra el esquema. Un backup9 requiere un perfil9; un backup10 requiere592; un backup11 requiere712,832 o849, con la misma historia/digests SQL001–011; un backup12 requiere969 y SQL001–012. Tras restaurar en la base nueva se exige historia exacta1..N y los digests SQL del perfil. Una mezcla entre esquemas (por ejemplo10→11) falla conservando el parcial antes de crear administrador, sin recibo de éxito.

La salida correcta conserva installation_prepared, valid=true y exit0, y agrega mode=Restore, sourceBackupManifestSha256 y recoveryAuditEventId. Guardar installationSha256 y deploymentSha256 fuera del ROOT, y contrastar el hash fuente con el backup elegido. El recibo installation.json schema2 contiene las once claves de schema1 y una duodécima recovery, objeto cerrado con backupManifestSha256 y auditEventId; no tratar schema2 como schema1. El estado conserva sus cuatro claves. No hay servidor web activo hasta Start. La credencial nueva está en RecuperadoNuevo01\deployment\instance\private\admin-login.json. Inspeccionar/arrancar/parar con RecuperadoNuevo01\content\operators, DeploymentPath RecuperadoNuevo01\deployment y el hash nuevo, siguiendo los mismos comandos anteriores.

Esto prepara una instalación **paralela desde un snapshot**. No actualiza en sitio ni conmuta usuarios, puertos, DNS o servicios. El backup v1 no identifica la instalación origen ni bloquea escrituras posteriores en ella. Seleccionar externamente el backup correcto y resolver frescura/conmutación antes de uso real. Mantener el origen y sus dependencias para volver a arrancarlo con sus propios operadores/hash si procede; los cambios hechos después en el recuperado no aparecen automáticamente en el origen. No prometer sincronización ni rollback de esas escrituras. Para comprobar la restauración: entrar con el administrador nuevo, verificar clientes/racks/Dosen/dispositivos finales y grupos/permisos, comprobar que una cookie anterior se rechaza, probar escritura/lectura en otra sesión y parada/reinicio. No sobrescribir el origen para hacer esta comprobación. Ver RECUPERACION-DESPLIEGUE-WINDOWS-S1.md para el operador de nivel inferior y sus límites.

## Fallos y límites vigentes

Ante error se conserva el parcial y su estado failed, sin hash de éxito. No se borra, mueve, sobrescribe, reanuda o reutiliza el destino, ni se modifica otra instalación. Los logs y solicitudes son privados y pueden contener secretos de procesos; no publicarlos. Para otro intento elegir ROOT nuevo después de revisar el motivo. El instalador no convierte un estado parcial en éxito ni mata procesos ajenos.

Pendientes: servicioSCM, identidad Windows mínima, arranque después de reinicio, PKI/renovación productiva, Windows limpio/otro equipo, recuperación integral/retención y QA/adopción final de Wascar. Derechos de redistribución VC++ y cumplimiento/oferta de fuentes LGPL requieren revisión antes de publicar o adoptar; este ZIP interno conserva los avisos pero no concede esa aprobación. Las pruebas ejecutadas realmente, intentos fallidos y hashes finales se atribuyen al cierre del grupo593–652; los informes anteriores se conservan como históricos, sin presentar este manual como evidencia de ensayo no realizado.


En712, abre Settings arriba a la derecha de Clientes para cambiar idioma o tema de tu cuenta. Espera confirmación del servidor; recarga y comprueba desde otra sesión de la misma cuenta. Otra cuenta conserva sus propios ajustes. En login sin sesión el ajuste es sólo fallback de ese navegador. Si aparece recuperación, consulta antes de reenviar; no se guarda el cambio como exitoso antes de confirmarlo.


## XLS (HTML RC9) en832

Entra con una cuenta que tenga lectura y reports.export para el cliente. Abre su tarjeta y Consultar inventario; al final del panel, inmediatamente después de Informes e impresión/SVG, pulsa XLS (HTML RC9). En Rack del informe elige por ruta/nombre/UUID; el texto completo aparece también debajo del selector. Pulsa Generar XLS (HTML RC9) y espera Generación confirmada por el servidor; después pulsa Descargar XLS (HTML RC9). Comprueba el archivo nuevo en Descargas(Ctrl+J). Generación confirmada no equivale a descarga ni guardado en disco.

Es HTML con extensión.xls, distinto del XLSX tabular. Excel puede avisar de discrepancia de formato; no cambies su seguridad ni habilites macros/contenido. La prueba de desarrollo en Excel16.0build20430 conservó87valores exactos sin fórmulas; creó tres pestañas, pero las tres tablas consecutivas están en Devices y las otras dos vacías. No se prometen tres hojas pobladas ni compatibilidad universal. Nombres/etiquetas/ceros/Unicode quedan literales; Technician vacío porque no existe el campo persistido. Created usa textolegacy creado o creaciónPG, no fecha de exportación.

Una solicitud incierta se consulta/reintenta con su identidad original en esta página. notRecorded no cancela. Recargar pierde la recuperaciónRAM; no se promete historial durable. Cambiar cuenta/cliente no habilita descargas anteriores. Un rechazo de permiso o sesión no se convierte en éxito. QA75–77 tienen guion detallado separado: sólo se habilitan al seleccionar la copia compatible, sin alterar observaciones anteriores.


## Aviso accesible de grupos en849

Inicia sesión con una cuenta sintética que pueda administrar seguridad. En Usuarios abre Grupos y permisos y localiza Relaciones de grupos · solo lectura, debajo de Actualizar grupos. Usa Tipo de grupo y Grupo seleccionado para elegir por nombre y UUID. La ficha mantiene el ID completo; el selector nativo puede recortarlo visualmente. Cambiar tipo retira la ficha anterior. Un aviso accesible compacto permanece desde la primera selección; no convierte la lista completa de relaciones en un anuncio.

Los nombres escritos por el usuario se conservan literalmente en EN/DE/ES. Elegir o navegar no cambia permisos ni guarda datos. Un error de lectura retira los detalles anteriores; la autorización se comprueba en el servidor. Las comprobaciones DOM/AX no prueban voz de Narrador/NVDA/JAWS. QA-78 explica la prueba manual con lector habitual; sólo realizarla cuando la guía del laboratorio indique disponible. Si no se dispone de lector, registrar la variante no realizada y Bloqueado. No se sobrescriben resultados anteriores.


## Paleta personal de tipos en969

Con cualquier cuenta activa, incluida Lector, pulsa Todos los clientes en la barra izquierda, debajo del título Infraestructura. Arriba a la derecha, junto al idioma y tema, pulsa Paleta. En la ventana central usa el cuadrado de color de cada tipo; RJ45 y RJ45 PoE son independientes. Estos cambios sólo son borrador: Cerrar descarta los no guardados. Pulsa Guardar abajo a la derecha y espera confirmación y lectura del servidor. El botón ↺ restablece un tipo en el borrador; Restablecer todo prepara los diez valores iniciales. Ambos requieren Guardar.

Tu paleta se recupera al recargar o iniciar la misma cuenta en otra sesión. Otra cuenta conserva la suya. Los colores explícitos de puerto y cable, estados, PoE y Click-Click mantienen su prioridad; no cambia inventario ni cables existentes. La sección Parejas de categorías de1089 permite preferencias personales para conexiones nuevas; se explica debajo. No se importan preferencias del HTML offline.

Ante una petición pendiente usa Consultar original, Reintentar original o Cancelar original; conserva la intención y reautentica la misma cuenta si se solicita. Una respuesta incierta no significa guardado. QA79–81 contienen pasos detallados; sólo realizarlos cuando la guía de tu snapshot indique disponible. Los resultados anteriores de Wascar se conservan.


FIX02, bloque970–1029: Restore12 rechazaba la candidata inicial por un literal de recuperación administrativa todavía11. Se conserva el ZIP01 fallido y se usa exclusivamente CANDIDATA969-FIX02 y el nuevo ZIP02. El cambio funcional es ese literal12; frontend, SQL001–012 y dependencias son iguales. Las DLL/PDB de dominio/servidor reflejan también la revisiónGit de compilación. No equivale a una adopción ni a otra versión de SDK/runtime. Resultados de New/Restore y revisión se atribuyen al cierre1029.


## Paleta por parejas de categorías en1089

En la barra izquierda pulsa **Todos los clientes**, debajo del título Infraestructura. Arriba a la derecha pulsa **Paleta**. Dentro del diálogo pulsa **Parejas de categorías**. Hay28 parejas simétricas y diez muestras. Selecciona una muestra; repetirla o × quita el color del borrador. **Restablecer todo** también sólo cambia el borrador. Pulsa **Guardar** abajo a la derecha y espera la confirmación del servidor y su GET. Cambiar a Tipos de puerto y volver conserva borradores; Cerrar los descarta.

Cada cuenta, incluido Lector, conserva su preferencia. Misma cuenta en otra sesión la recupera; otra cuenta no la hereda. Al crear conexiones, el servidor usa color manual válido→pareja de categorías→sin color. Se clasifica por clave real del preset de los equipos, no por su nombre traducido ni gn. El color queda guardado en el cable compartido. Cambiar la preferencia no recolorea conexiones anteriores, reconexiones, duplicados, puertos ni estados. No concede permisos de crear conexiones. El antiguo almacenamiento local de RC9 no se importa ni impone defaults.

Ante incertidumbre usa Consultar original/Reintentar original/Cancelar original con la misma cuenta e intención; no declares guardado por un mensaje pendiente. QA82–84 detallan los recorridos y sólo se habilitan tras selección/readiness real del nuevo QA13. No se modifican resultados anteriores de Wascar.


Integración1090–1149: perfil1089 cerrado por el manifiesto CANDIDATA1089-02 (SHA256 c8b3df5b8e0fb6c5db148b7ddca2a8064ade6b90557713fb0835cbf69bb9710c), SQL001–013 y22+18 artefactos. Un backup13 requiere ese perfil13: no ejecutar binarios12 sobre13. La copia de laboratorio es distinta de Restore administrativo: protege por separado principal969/12 (37 tablas) y recuperación849/11 (35), conserva preparado/sello1029 y copia sólo principal a nuevas1089/13 (39) y recuperación969/12 (37). SQL013 corre sólo en la nueva principal; sus dos tablas nuevas empiezan vacías. Cinco secretosPG nuevos y datos/cuentas/sesiones/privados/grants conservados; sin bootstrap/recover-admin. Retorno condicionado por ausencia de actividad en las cuatro ramas, incluso actividad compensada; ante incertidumbre conservarlas y resolver recovery_required, sin reescribir baselines. Pruebas Windows/QA nuevas1090–1149 se separan de1030–1089 y anteriores. No se compila ni se cambian dependencias al empaquetar.



## Alta de grupos1449 y operación1450–1509

Candidata1449-01: SHA25655bdd496ec654494fd8e3400140e3e84241488986e24481939bad67cde7a91c6,40archivos/22+18/7.159.235bytes/esquema13.195fuentes; sólo app.js difiere de1329, servidor1089/SQL001–013/CSS/dependencias exactos. Las secciones de integraciones anteriores son antecedentes.

Interfaz: INICIAR-QA-RESTAURADO.cmd→guía y credenciales privadas. Desde Todos los clientes elige Español arriba a la derecha y espera guardado; dentro de Administración no hay selector de idioma. Barra izquierda→Usuarios→debajo de Lista de cuentas, Grupos y permisos→Crear grupo. Elige Grupo de usuarios o Grupo de clientes, escribe nombre y pulsa Crear grupo. Tras commit, Grupo creado muestra nombre literal/tipo/UUID; Abrir relaciones abre sólo la ficha exacta y enfoca Grupo seleccionado. No añade miembros ni concede permisos. Navegar conserva los tres editores; salir de Administración/recargar retira el recibo temporal, sin borrar el grupo persistido.

Si queda pendiente: Consultar resultado del grupo, Reintentar alta original o Cancelar alta de grupo pendiente conservan la intención original. No registrado no acredita cancelación ni crea recibo; un commit ya confirmado se conserva ante fallo de limpieza, bloqueando continuación hasta resolver pendiente y leer snapshot válido. Los casos QA91–93 sólo se habilitan después de selección revisada de1449. Conserva observaciones y resultados anteriores; voz requiere lector habitual, no una prueba visual.

Actualización QA1509: mismo clúster/principal13(39tablas)/recuperación96912(37), cuentas/contraseñas/sesiones/permisos/datos/puntero. Sólo artifactDirectory+bundleSha256; nueva versión1449 y registro/sello propios. Cadena1149→1209→1329 intacta, inventario exacto, nada de migrar/copiar bases/bootstrap/recover-admin/login/DML de aplicación en QA real. Baseline actual capturado una vez. Sólo la misma operación explícita puede reentrar tras rolled_back confirmado, con registro/sello/baseline/parent1329/puntero intactos y sin actividad intermedia. Interferencia o incertidumbre bloquean retorno; sin rollback tardío.

New/Restore nativos usan laboratorio nuevo, secretos/TLS propios y runtime sinSDK; no acreditan otra máquina, Windows limpio, SCM/PKI productiva o voz. Instalación definitiva, licencias/redistribución, recuperación integral y adopción de Wascar siguen pendientes.

## Antecedente histórico · alta guiada1209 y operación1210–1269

Candidata1209-01: SHA256 dc79c53fe188187637972c2cad479edd1868d1942414c602de17bb4454bd153b,40 archivos/22+18/7.146.303 bytes/esquema13. Sólo app.js difiere de1089;22 archivos de servidor, SQL001–013, CSS y dependencias exactos. No ejecutar un perfil12 contra una base13. Los apartados de integración1090–1149 describen la copia histórica12→13, no la actualización actual.

En la barra lateral izquierda pulsa **Usuarios**, cerca de la parte inferior. En **Secciones de administración**, a la izquierda del contenido, pulsa **Crear cuenta**. En el centro completa **Nombre de usuario** y **Contraseña**, pulsa **Crear usuario** y espera la confirmación del servidor. La tarjeta **Cuenta creada** muestra nombre literal y UUID completo. Pulsa **Continuar a membresías**: abre **Grupos y permisos** y enfoca **Membresías de usuarios**. Si faltan cuentas nuevas, pulsa **Actualizar grupos**; contrasta UUID, elige un grupo explícito y pulsa **Guardar asignación**. La navegación no asigna grupos ni concede permisos. Vuelve a la tarjeta y pulsa **Revisar permisos efectivos**; en el panel pulsa **Actualizar cuentas** y **Consultar permisos**. Una cuenta sin grupos no obtiene acceso por su nombre ni por aparecer en una lista. Compruébalo iniciando esa cuenta en otro perfil de navegador.

Ante un guardado incierto usa Consultar original/Reintentar original/Cancelar original con la misma cuenta e intención. Una coincidencia en una lista o notRecorded no demuestra alta. El recibo confirmado permanece sólo en memoria, sin contraseña; un borrador/petición/recuperación pendiente bloquea la continuación. Después de401/403 se retiran sus datos. En390px usa desplazamiento; conserva EN/DE/ES y nombres propios. Los pasos detallados son QA85–87 en la guía, disponibles sólo tras verificar selección real1209, cuentas/roles y configuración. No se sobrescriben resultados de Wascar.

Actualización QA1269 de artefactos: misma raíz/clúster/principal13(39 tablas)/recuperación969/12(37), mismos OIDs/cuentas/sesiones/grants/secretos y puntero. Nueva versión con40 archivos; previous/preview/selected privados sellados. Sólo artifactDirectory y bundleSha256 cambian en manual-qa.json. El preparado1149, su sello, configuración fuente y artefactos1089/969 quedan como evidencia exacta. No hay migrate/bootstrap/recover-admin ni login/DML de aplicación sobre el QA actual. Se comparan datos actuales, no la foto histórica de creación.

Preview/readiness13→parada confirmada→selección atómica→GET/readiness13→parada/verificación. Retorno sólo dentro de la operación fallida si inputs, quietud y watermark único del clúster, comprobado antes/después de ambasDB, coinciden con el baseline original. Actividad incluso compensada o incertidumbre exige recovery_required y conservar selección/versiones; no renovar baseline ni ofrecer rollback posterior. El watermark es conservador por clúster. Siete runtime/logs anteriores se archivan privadamente; no se promete igualdad de archivos físicos PG tras arrancar. Si hay procesos ajenos o sesiones activas, no forzar parada.

Las pruebas New/Restore de Windows1269 usan fixtures nuevos y API/transporte exactoapp.js; no son una nueva pruebaDOM/voz/Office ni instalación limpia en otro Windows/SCM/PKI productiva/CRT elevado/licencias aprobadas. Cero builds/descargas/cambios de versiones al empaquetar. Producto final y QA/adopción de Wascar siguen pendientes.


## Antecedente histórico · relaciones por UUID1329 y operación1330–1389

Candidata1329-01: SHA25638bbae727ffd545436506ab65d1c66525a64bf316e0a9354079cace0aa60c6b6,40archivos/22+18/7.148.383bytes/esquema13. Sólo app.js difiere de1209; servidor1089/SQL001–013/CSS/dependencias exactos. Las integraciones anteriores se conservan como antecedentes, no describen la selección nueva.

Para comprobar la interfaz: ejecuta INICIAR-QA-RESTAURADO.cmd y usa la guía y credenciales privadas que abre. Elige Español arriba a la derecha y espera el guardado del idioma. En la barra izquierda pulsa Usuarios, cerca de la parte inferior. Debajo de Lista de cuentas abre Grupos y permisos. Dentro busca Relaciones de grupos · solo lectura, encima de Crear grupo; no hay un botón Relaciones de grupos en Secciones de administración.

En Tipo de grupo elige Grupos de usuarios y en Grupo seleccionado contrasta el UUID completo. Dentro de Permisos asignados, una concesión explícita sobre un grupo de clientes ofrece Ver grupo de clientes. Ese botón abre exactamente su UUID y lleva el foco al selector persistente. Desde la ficha de clientes, Ver grupo de usuarios vuelve a su origen exacto. Nombres iguales no implican identidad; pertenencias múltiples se conservan. Las concesiones globales y directas a un cliente no se convierten en grupos. Navegar no guarda, asigna miembros o permisos ni cambia el usuario común o los borradores.

La ayuda de Crear grupo dirige a editores de membresías y Permisos de grupos de usuarios, que sí requieren acciones explícitas y confirmación del servidor. Actualizar grupos retira datos obsoletos o denegados. EN/DE/ES mantienen nombres literales; usa desplazamiento en ventana estrecha. La prueba de voz requiere tu lector habitual: si no está disponible, registra Bloqueado para esa parte. Los casos QA88–90 sólo están habilitados cuando la guía confirma la distribución1329 seleccionada y sus cuentas/configuración revisadas. No cambies resultados anteriores por disponer de código nuevo.

QA1389 conserva principal13(39tablas), recuperación969/12(37), OIDs/cuentas/sesiones/grants/secretos y puntero. Se añade una versión1329, con configuración previous/preview/selected y registro/sello privados; sólo artifactDirectory y bundleSha256 cambian en manual-qa.json. El preparado1149 y overlay1209/1269 permanecen byteexactos, sin reescribir historia. La validación de la cadena excluye únicamente el descendiente identificado; una versión ajena o un sello alterado impide continuar. No copiar/migrar bases ni ejecutar bootstrap/recover-admin/login/DML de aplicación en el QA real.

Capturar baseline actual una sola vez, no la foto histórica de creación. Preview/readiness13, parada confirmada, selección atómica, GET/readiness13, parada y comparación de ambas bases/historias/permisos/actividad. Un cambio incluso compensado o una duda bloquea retorno y mantiene recovery_required; no renovar baseline ni ofrecer rollback tardío. Si existen sesiones o procesos ajenos, conservarlos y no forzar parada. Archivos runtime originales archivados privadamente; no se promete igualdad de archivos físicos PostgreSQL tras arrancar.

New/Restore de Windows se comprueban en fixtures nuevas con runtime sinSDK y secretos propios. El transporte app.js y las pruebasAPI no son una nueva ejecuciónDOM/voz/Office ni instalación limpia en otroWindows/SCM/PKI productiva. Licencias/redistribución, recuperación integral e instalación final y QA/adopción de Wascar siguen pendientes. Sin descargas ni cambios de versiones durante esta integración.

Si una operación1389 termina en rolled_back confirmado y con sus procesos detenidos, sólo se admite reintentar el mismo --operation explícito: registro, sello, baseline, puntero y parent1209 exactos y sin actividad intermedia. No descubrir otra operación ni recapturar el baseline; cualquier interferencia bloquea la reentrada. No es un rollback tardío.
