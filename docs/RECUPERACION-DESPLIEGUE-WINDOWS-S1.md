# Recuperar un despliegue privado en un destino nuevo

**Compatibilidad1449/esquema13.** Restore administrativo crea raíz/base/roles/TLS/admin nuevos, revoca sesiones copiadas y conserva propietarios. ActualizaciónQA1509 sólo interfaz en misma raíz13/recuperación12; retorno durante fallo sujeto a entradas/quietud/actividad y misma operación explícita, nunca rollback tardío. Recuperación integral y adopción pendientes.

Capacidad interna S1 del grupo308–337, ampliada en398–427 por `Install-RackClickOfflineBundle.ps1 -Mode Restore`. El operador inferior `Restore-RackClickPrivateDeployment.ps1` prepara otra instalación de laboratorio a partir de un backup nativo confiable: distribución aprobada → clúster/base/roles nuevos → recuperación administrativa transaccional → perfil TLS nuevo. Conserva el Systemhaus, clientes, inventario y cuentas recuperados. No inicia el servidor al terminar. La prueba integral y su revisión se atribuyen al cierre del coordinador; este documento no certifica por sí solo una instalación limpia ni una candidata adoptada. Los informes308–337 y338–367 conservan su carácter histórico.

## Desde el paquete completo actual

El modo Restore del instalador reúne content, dependencias y recuperación en una raíz nueva. Usar el ZIP del perfil de procedencia confiable y su SHA256 externo; extraer primero sus25 operadores según MANUAL-PAQUETE-WINDOWS-S1.md. El lector sólo admite los perfiles337/397/532 (esquema9) y592 (esquema10)/712,832 y849 (esquema11)/969 (esquema12)/1089,1209,1329,1449 (esquema13) registrados; no acepta versiones arbitrarias por recibir su hash. No modificar ni reutilizar el bootstrap antiguo.

```powershell
& "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -NonInteractive -File C:\Entregas\operators\Install-RackClickOfflineBundle.ps1 -Mode Restore -ArchivePath C:\Entregas\RackClick.zip -ExpectedArchiveSha256 HASH_ZIP_CONFIABLE -DestinationPath C:\Laboratorios\RecuperadoNuevo01 -PostgresPort 55443 -HttpPort 55444 -RecoveryUser "Administrador recuperacion nuevo" -BackupPath C:\BackupsPrivados\CopiaAprobada -ExpectedBackupManifestSha256 HASH_BACKUP_APROBADO
```

No pasar BootstrapUser ni SystemhausName con Restore. Los tres parámetros BackupPath, ExpectedBackupManifestSha256 y RecoveryUser son obligatorios; New, que sigue siendo el modo predeterminado, los rechaza incluso vacíos. Mode es exactamente New o Restore. El backup se abre contra escritura/borrado antes de crear ROOT y se mantiene fijado hasta acabar; debe ser disjunto de ZIP/operadores/destino. No se copia al content.

La fábrica Restore que ejecuta el instalador procede del content recién extraído y verificado, junto con su aplicación/runtime/PG. El layout de instalación conserva content, deployment, logs, installation-state.json e installation.json. La credencial nueva está en deployment\instance\private\admin-login.json. PostgreSQL queda detenido antes del recibo de éxito. La salida Restore agrega mode, sourceBackupManifestSha256 y recoveryAuditEventId a la salida previa; el recibo installation.json usa schema2 y doce claves: las once schema1 más recovery={backupManifestSha256,auditEventId}. Sus formatos no son intercambiables. deployment.json conserva schema1 y once claves; ese despliegue se inspecciona/arranca/para mediante content\operators pasando DeploymentPath ROOT\deployment y ExpectedDeploymentSha256 de la nueva salida válida.

La recuperación es paralela desde el snapshot elegido. El backup v1 no identifica el deployment origen, no bloquea nuevas escrituras en éste y no garantiza frescura. Seleccionar y contrastar externamente el origen/backup y resolver la conmutación antes de uso real. No hay actualización en sitio, parada/reserva automáticas del origen, sincronización entre instalaciones ni rollback de cambios posteriores al snapshot. Conservar origen/binarios/secretos para la comprobación de regreso con sus operadores/hash propios. El ensayo histórico337→397 usa un origen sintético controlado sin escrituras tras backup; no acredita esa coordinación en una instalación activa real.

Comprobar con el administrador nuevo: inventario y Dosen/dispositivos finales conservados, grupos/ámbitos efectivos, cuentas antiguas activas con su contraseña original y cookies anteriores denegadas. Probar una escritura, lectura desde otra sesión y un ciclo Stop/Start confirmado. Consultar XLSX en397/532/592/712, editor privado en532/592/712 y compartidas en592/712 y preferencias personales en712. Un fallo conserva el parcial, estado failed y sin hash de éxito; escoger otra raíz en un nuevo intento. Las ejecuciones nuevas y sus fallos se atribuyen al cierre713–772;593–652 y los demás informes anteriores se conservan como evidencia histórica.

Se separa de `New-RackClickPrivateDeployment` porque bootstrap exige una base vacía y crea otro Systemhaus, mientras que recuperar debe conservar el existente. También se separa de `Restore-RackClickDatabaseBackup`, cuya salida `rc_restore_*` sigue siendo una base aislada sin recibos operativos, administrador nuevo ni ciclo completo. Los tres comandos y lectores anteriores se mantienen con sus contratos.

## Entradas y preparación

Usar Windows PowerShell5.1 x64, runtime.NET10 compatible y PostgreSQL17.11 x64 ya verificados. No se descarga ni instala ninguna dependencia durante la recuperación. La distribución registrada incluye el CLI `--recover-admin`, la interfaz de su perfil y la secuencia aprobada SQL001..N (N=9 para337/397/532; N=10 para592; N=11 para712/832/849; N=12 para969; N=13 para1089/1209/1329/1449). El operador no necesita SDK.NET, Python, Node, Git ni OpenSSL para estos comandos; las pruebas de desarrollo pueden usar herramientas adicionales.

El operador debe obtener por un canal confiable **dos referencias externas**: SHA256 del manifiesto de distribución y SHA256 de `manifest.json` del backup. No tomar como aprobación un hash recalculado del mismo archivo recibido sin contrastarlo. El backup debe proceder de la operación nativa conocida, con exactamente `manifest.json` y `data.dump`; ambos archivos y el directorio deben ser locales, privados para SIDactual+SYSTEM y sin junction/reparse. Si procede de USB/UNC, preparar manualmente una copia local privada y contrastar la misma referencia externa antes de invocar el comando. El comando no lee UNC ni cambia ACL de una fuente existente.

Un hash vincula los bytes de una fuente confiable; no convierte un dump desconocido en contenido seguro. PostgreSQL advierte que una restauración puede ejecutar código arbitrario elegido por quien controla el origen. Usar únicamente backups confiables. [Documentación oficial de pg_restore17](https://www.postgresql.org/docs/17/app-pgrestore.html).

La nueva raíz de destino debe ser ASCII, no existir y tener un padre existente en disco local fijo, disjunto del backup, distribución, runtime y PostgreSQL. Es el límite técnico observado de initdb17.11 en Windows. Backup y fuentes pueden tener Unicode: `pg_restore` recibe cwd Unicode y el nombre relativo fijo `data.dump`, evitando el límite ANSI de nombres de archivo en argv. No se crean alias8dot3 ni se translitera la ruta. Los nombres de usuarios/datos admiten la política Unicode de la aplicación.

Elegir dos puertos loopback distintos, disponibles y entre1024–65535. Una ocupación posterior al preflight puede hacer fallar la creación; el parcial se conserva.

```powershell
powershell.exe -NoLogo -NoProfile -NonInteractive -File tools/windows/Restore-RackClickPrivateDeployment.ps1 `
  -ManifestPath C:\Paquete\manifest.json -ExpectedManifestSha256 HASH_DISTRIBUCION_APROBADO `
  -ServerPath C:\Paquete\server -FrontendPath C:\Paquete\frontend `
  -DotNetPath C:\Runtime\dotnet.exe -PostgresBinPath C:\PostgreSQL17\bin `
  -DestinationPath C:\Laboratorios\RecuperadoNuevo -PostgresPort 55441 -HttpPort 55442 `
  -RecoveryUser "Administrador recuperacion" -BackupPath C:\BackupsPrivados\CopiaAprobada `
  -ExpectedBackupManifestSha256 HASH_BACKUP_APROBADO
```

Los marcadores HASH son referencias de64dígitos hexadecimales, no credenciales. `RecoveryUser` debe normalizar a un nombre que no exista en el backup. La normalización autoritativa es .NET, igual que login; PowerShell no calcula un casefold alternativo. No existe parámetro SystemhausName: el nombre recuperado se conserva. Un nombre ya ocupado, incluso tras trim/minúsculas invariantes, causa rechazo sin reemplazar la cuenta anterior.

## Protocolo y resultado

El preflight verifica referencias, ACL/noReparse/rutas/puertos, los36,37,38,39 o40 artefactos de distribución según el perfil y runtime/herramientas17.11 x64. Abre el manifiesto y dump del backup con `FileShare.Read`, y mantiene esos handles contra escritura/borrado hasta terminar. Igual con distribución y artefactos. `pg_restore --list` debe terminar correctamente, sin stderr, presentar archivo CUSTOM de17.11 y las tablas esenciales. Ese listado comprueba que el archivo se puede interpretar; no sustituye la confianza en la fuente ni la validación de esquema posterior. Ninguna raíz de destino se reserva antes de completar el preflight.

Se crea la raíz atómicamente con ACL privada. Un UUID nuevo deriva `rc_cluster_<32hex>`, `rc_owner_<32hex>`, `rc_runtime_<32hex>` y `rc_db_<32hex>`. Contraseñas de clúster, propietario, runtime y nuevo administrador son aleatorias nuevas de64hex. El `initdb` nuevo utiliza SCRAM, checksums y escucha exclusiva127.0.0.1. Su proceso queda en un JobObject propio desde antes de ejecutar. El clúster sólo crea la base/roles nuevos; propietario y runtime son NOSUPERUSER/NOCREATEDB/NOCREATEROLE/NOREPLICATION/NOBYPASSRLS.

Antes de restaurar, el script comprueba propietario exacto y ausencia de relaciones públicas, y escribe en **esa base nueva**:

```text
RackClickRecoveryPending:<UUID-D-minusculas>:<SHA256-externo-del-manifest-backup>
```

`pg_restore` se conecta como el propietario nuevo, con `--single-transaction --exit-on-error --no-owner --no-acl`. No utiliza `--clean`, `--create`, DROP ni SQL de entrada del operador. Contraseñas se transmiten por archivos privados de contraseña/entorno/stdin; no por argumentos. Sólo el dump aprobado aporta el SQL restaurado. Se comprueba historia exacta1..N y digests según el perfil validado9/10/11/12/13; el CLI los comprueba también antes de escribir, sin migración ni bootstrap implícitos. Si un backup9 se usa con Stage10, se conserva la nueva base parcial tras pg_restore y se rechaza antes del CLI administrativo; no hay recibo de éxito ni cambios en el origen.

El CLI `--recover-admin` recibe conexión de propietario y `Recovery__User`, `Recovery__ExpectedDatabase`, `Recovery__BackupSha256` por entorno. Esta última variable contiene el hash de **manifest.json**, nunca el hash de data.dump. La contraseña administrativa nueva llega por stdin y se cierra con EOF. En una transacción exige propietario/base/comentario exactos, crea usuario/grupo y los grants FoundationAdmin de ese esquema (9,10,11,12 o13, incluido templates.publish en10/11/12/13 únicamente para el grupo administrativo nuevo), borra todas las sesiones recuperadas, incrementa revisión de Systemhaus, registra `deployment.recover` y consume el comentario poniéndolo a NULL. La salida `committed` se produce tras commit. Conserva contraseñas/estado de las cuentas anteriores y el nombre/ID del Systemhaus. [Contrato del CLI](RECUPERAR-ADMINISTRADOR-S1.md).

Se verifican usuario persistido por su UUID y nombre UTF8 transportado como hex, nombre/ID del Systemhaus y cuentas anteriores intactos, grants globales nuevos, sesiones0, comentarioNULL, evento de recuperación vinculado al UUID nuevo/hashfuente y privilegios runtime sin CREATE/TEMP/propiedad de tablas. El runtime recibe USAGEpublic y DML en las tablas. El PG propio se detiene con pg_ctl y se exige ausencia de postmaster.pid. En fallos se intenta primero pg_ctl fast con identidad de Job comprobada y límite45s (pg_ctl30s); sólo si eso falla se cierra ese Job, se informa cleanup fallido y se conserva el parcial. No se seleccionan procesos por nombre/PID ajeno.

La instancia mantiene exactamente los cinco archivos privados existentes: `admin-login.json`, `backup-profile.json`, `cluster-password.txt`, `owner-password.txt`, `runtime.json`. `admin-login.json` contiene el nombre real normalizado del **nuevo** administrador y su contraseña nueva. Tratarlo como secreto local: no incluirlo en evidencia pública ni paquetes. Los logs/solicitudes también son privados y pueden contener credenciales de entorno/stdin; no publicarlos. El fichero privado de contraseña de pg_restore permanece únicamente dentro de logs privados.

Se prepara un perfil TLS externo nuevo, autofirmado de7días loopback, con clave/certificado/contraseña nuevos. No escribe en el almacén de confianza, no crea SCM/UAC ni configura una identidad de servicio Windows. El despliegue final tiene exactamente seis entradas:

```text
RecuperadoNuevo\
  distribution\
  instance\
  https\
  logs\
  deployment-state.json
  deployment.json
```

El recibo `deployment.json` conserva exactamente las once claves actuales y `state=prepared`; `Read-RackClickPrivateDeployment` lo valida con los lectores de instancia/TLS existentes, sin cambios de formato. El manifiesto de instancia conserva19claves y `initialized`, estado `instance_initialized`. La publicación ocurre al final, tras verificar los componentes y PG detenido. Un fallo posterior de validación/cierre cambia el estado a failed y no devuelve referencia de éxito; los lectores rechazan ese estado aunque haya quedado un recibo parcial.

La salida pública devuelve valid/exitCode/code, IDs nuevos, hash de recibo, URLloopback, sourceBackupManifestSha256 y recoveryAuditEventId. No imprime contraseñas, datos restaurados ni rutas de archivos secretos. Conservar `deploymentSha256` fuera del nuevo directorio. La URL indica configuración preparada, no servidor activo.

Operar el nuevo destino con `Test-RackClickPrivateDeployment.ps1` e `Invoke-RackClickPrivateDeployment.ps1`, pasando esa raíz y hash externos; se mantiene el contrato de [operación por recibo](OPERAR-DESPLIEGUE-PRIVADO-WINDOWS-S1.md). El primer arranque sirve para comprobar login nuevo, conservación de datos y rechazo de cookies previas; no reutilizar una cookie del origen como credencial de recuperación. Las cuentas antiguas continúan pudiendo autenticar si estaban activas; sus sesiones anteriores se eliminaron.

Puede respaldarse otra vez esta instancia y recuperarla en un **tercer UUID nuevo**: la auditoría anterior se conserva y no bloquea otra recuperación. Repetir el CLI sobre la misma instancia ya inicializada sí se rechaza. Ningún comando reanuda un destino parcial ni adopta un ROOT ya existente.

## Fallos y límites

Los errores se identifican por fase: preflight, stage, instance, https, finalize; el aprovisionador añade cluster/restore/administrator/verify/stop donde corresponda. Tras reservar destino, se conserva la raíz con estado failed y logs privados. No se borra la base parcial, no se reemplaza un recibo preexistente y no se reintenta sobre el mismo directorio. Si la confirmación del commit resulta incierta, conservar y revisar el parcial: no crear otra cuenta automáticamente en esa base. Para otro intento se necesita otro ROOT/UUID. El origen/backup permanece abierto sólo en lectura.

Un cierre forzado puede conservar un postmaster.pid obsoleto dentro del parcial. No borrarlo ni detener un proceso ajeno por interpretar ese número; la identidad válida es el Job propio. No usar estos comandos como actualización, reset, rollback de archivos sobre base9 ni reparación de instalaciones existentes.

Pendientes de aceptación separada: Windows limpio/otro equipo, SCM/identidad mínima de servicio, PKI/DNS/renovación productivos, backup de instalación completa/retención/NAS/USB, manual visual final y QA/adopción de Wascar. Esta recuperación reconstruye el despliegue desde distribución aprobada y backupDB; no restaura binarios/configuración/PKI anteriores por confianza implícita. No modifica las copias QA compartidas ni RC9 adoptada.

## Diez hitos históricos318–327 y evidencia

| Hito | Resultado previsto y comprobación |
|---|---|
|318|Contrato de recuperación separado de bootstrap/restore aislado, parámetros y compatibilidad de lectores.|
|319|Backup con hash externo, ACL privada y locks de manifest/dump durante todo el proceso.|
|320|Preflight completo antes de ROOT: distribución/runtime17.11 x64/listado/puertos/rutas nuevas y disjuntas.|
|321|Clúster/base/roles/contraseñas nuevos, Job propio, SCRAM y base inicialmente vacía.|
|322|Restauración transaccional como propietario limitado; marcador exacto y esquema9 sin migración.|
|323|CLI admin nuevo/grants/sesiones0/auditoría/consumo de marcador atómicos.|
|324|Verificación de invariantes, runtimeDML sinDDL, secretos/normalización y parada PG confirmada.|
|325|Stage→RecoveredInstance→TLS, layout6 y recibo11 compatibles con lectores actuales.|
|326|Fallos conservados/estado failed, limpieza de procesos/locks y restauración de entorno Process en finally.|
|327|Manual, fuente congelada, probes sinPG y revisión independiente previa al único ensayo integral coordinado.|

Estos hitos describen alcance de implementación; su ejecución real y la revisión quedan en [evidencia native](../evidence/s1-20261017/treinta-tandas-308-337/native/) y en el cierre conjunto. Probes puros: `powershell.exe -NoProfile -File evidence/s1-20261017/treinta-tandas-308-337/native/preflight-probes01.ps1`. No invocan PostgreSQL, build, servicios ni almacenes de certificados. La prueba integral PG/Windows/runtime sinSDK es responsabilidad del coordinador tras revisión independiente. No inferir ese PASS del análisis sintáctico ni del preflight.

Progreso de referencia al abrir este grupo:73/100 provisional en [PROGRESO-GLOBAL](PROGRESO-GLOBAL.md). La decisión de avance global corresponde al cierre coordinado con evidencia nueva, sin puntos automáticos por estos diez hitos.


La integración593–652 añade el perfil10 a la instalación nativa y a Restore; sus comandos, resultados reales y revisión se registran en evidence/s1-20261018/sesenta-tandas-593-652. No confundir Restore administrativo (revoca sesiones y crea administrador) con la copia QA9→10: ésta conserva cuentas/sesiones y permisos originales, y no otorga templates.publish automáticamente.


Integración713–772: perfil11 y recuperación administrativa CLI11 se comprueban con pruebas NUEVAS en su cierre. No confundir Restore administrativo (revoca sesiones, crea administrador) con copiaQA10→11 (conserva cuentas/sesiones/permisos, origen10 y recuperación10 separada). Retorno de QA sólo sin actividad comprobada; después de trabajar no se promete rollback de escrituras.


Integración833–847:832-02 conserva esquema11 y añade XLSHTML con tres tablas; probar exportación/recuperación del recibo con autorización vigente tras Restore. La copiaQA11→11 guarda además recuperación712 separada y no ejecuta --migrate ni recover-admin. Sólo retorno por puntero sin actividad comprobada en ambas ramas, incluida actividad compensada. No intercambiar esta operación con Restore del instalador. Los ensayos847 y sus fallos se registran en su evidencia nueva, conservando los informes históricos.


Integración850–909: la nueva copia conserva el laboratorio832 completo, incluidos su preparado/sello847 y la recuperación712. Se copian sólo los datos actuales de su base principal a las ramas849 y recuperación832 en un clúster nuevo. No se supone igualdad entre las dos bases del origen: se protegen sus snapshots por separado. El retorno exige ausencia de actividad en todas las ramas, incluida actividad compensada; si hay actividad se conservan las ramas y se requiere recuperación explícita. No sustituye el Restore administrativo del instalador. Los resultados nuevos se registran separados de847/848/849 y de las pruebas históricas.


Integración970–1029: copiaQA849→969 conserva el origen completo, preparado/sello909 y recuperación832/11. Sólo la principal se copia a nuevas969/12 y recuperación849/11; SQL012 corre únicamente en destino. Se comparan por separado las dos bases del origen. Las35tablas/historia previas se conservan y las dos nuevas tablas de paleta arrancan vacías en12. Cuentas, contraseñas, sesiones y privados de aplicación permanecen; secretosPG nuevos. El retorno exige ausencia de actividad en todas las ramas, incluso INSERT+DELETE compensado. Si hay actividad/estado incierto, conservar ramas y resolver recovery_required; no arrancar binarios11 sobre12. New/Restore del ZIP y copiaQA son recorridos distintos. Sus evidencias nuevas se separan de910–969 y anteriores.


FIX02, bloque970–1029: Restore12 rechazaba la candidata inicial por un literal de recuperación administrativa todavía11. Se conserva el ZIP01 fallido y se usa exclusivamente CANDIDATA969-FIX02 y el nuevo ZIP02. El cambio funcional es ese literal12; frontend, SQL001–012 y dependencias son iguales. Las DLL/PDB de dominio/servidor reflejan también la revisiónGit de compilación. No equivale a una adopción ni a otra versión de SDK/runtime. Resultados de New/Restore y revisión se atribuyen al cierre1029.


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
