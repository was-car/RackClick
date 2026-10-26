# Preparar y operar un laboratorio privado desde un recibo

**Aplicación1449/esquema13, servidor1089 exacto.** Recibo confirmado y continuación explícita por UUID sin conceder acceso. QA13 mantiene misma principal39tablas/recuperación96912 de37, cuentas/sesiones/puntero. Sólo artifactDirectory+bundleSha256; cadena1329→1449 sellada sin migrar.

Esta operación reúne distribución, instancia PostgreSQL y HTTPS local del perfil cerrado seleccionado (337/397/532: esquema9;592: esquema10;712/832/849: esquema11;969: esquema12;1089/1209/1329/1449: esquema13). Sólo crea un destino nuevo y privado. No instala un servicio Windows ni sustituye el paquete completo pendiente. Tampoco cambia la versión, los datos o las cuentas del QA de Wascar.

## Antes de crear

Usar Windows PowerShell5.1 x64. El runtime.NETCore/ASP.NET10 y PostgreSQL17.11 deben estar disponibles en rutas externas explícitas; se comprueban, pero no se descargan o instalan. No se requiere SDK, Python, Node o Git al operador. El equipo de desarrollo usa Python únicamente para reproducir los ensayos.

Conservar la referencia SHA256 del manifiesto de distribución fuera del archivo recibido. La [candidata1449 de laboratorio](../evidence/s1-20261018/sesenta-tandas-1390-1449/CANDIDATA1449-01.json) tiene referencia `55bdd496ec654494fd8e3400140e3e84241488986e24481939bad67cde7a91c6` y22archivos de servidor más18GUI. La selección QA es una operación separada, documentada en su cierre. Los scripts de operación también deben proceder del conjunto de fuentes sellado de esta entrega interna.

Elegir dos puertos distintos y libres entre1024 y65535. La raíz técnica de destino debe ser ASCII por la limitación de initdb comprobada anteriormente; nombres de usuario/Systemhaus admiten Unicode. El directorio padre debe existir, el destino no debe existir y las rutas deben ser disjuntas de las entradas y dependencias. No reutilizar un destino parcial o una base existente.

## Crear e inspeccionar

Desde la raíz del proyecto, adaptar las rutas reales y referencias:

```powershell
powershell.exe -NoProfile -File .\tools\windows\New-RackClickPrivateDeployment.ps1 -ManifestPath RUTA_MANIFIESTO -ExpectedManifestSha256 HASH_EXTERNO_DISTRIBUCION -ServerPath RUTA_SERVIDOR -FrontendPath RUTA_INTERFAZ -DotNetPath RUTA_DOTNET_EXE -PostgresBinPath RUTA_PG_BIN -DestinationPath C:\RackClick_SVR\.local\operacion\demo01 -PostgresPort 55441 -HttpPort 55442 -BootstrapUser "Administrador" -SystemhausName "Mi Systemhaus"
```

El padre del ejemplo es `C:\RackClick_SVR\.local\operacion`: prepararlo antes si no existe. La fábrica valida primero, después reserva exclusivamente el destino, prepara la distribución, crea un clúster/base/roles/secretos nuevos y el perfil HTTPS separado. Publica `deployment.json` al finalizar y devuelve `deploymentSha256`. Conservar ese hash fuera del despliegue. La salida correcta es `valid=true`, `code=deployment_prepared`, exit0. PostgreSQL queda detenido y la web aún no se ha iniciado.

El destino contiene sólo `distribution`, `instance`, `https`, `logs`, `deployment-state.json` y `deployment.json`. La cuenta inicial y contraseña generada se encuentran en `instance\private\admin-login.json`, con acceso local privado. No copiarlas al CMD, documentación pública, argumentos de proceso o Git. Los permisos de la aplicación se siguen comprobando en el servidor.

Comprobar el conjunto sin abrir la aplicación ni consultar PostgreSQL:

```powershell
powershell.exe -NoProfile -File .\tools\windows\Test-RackClickPrivateDeployment.ps1 -DeploymentPath C:\RackClick_SVR\.local\operacion\demo01 -ExpectedDeploymentSha256 HASH_EXTERNO_DESPLIEGUE
```

`deployment_verified` y `httpsValidated=true` confirman integridad actual de recibo, instancia y TLS. No significan que la web esté en ejecución. El inspector retiene referencias y archivos inmutables mientras se utiliza el conjunto; no enumera el contenido mutable de PostgreSQL/logs. [Contrato y límites del lector](INSPECCION-DESPLIEGUE-PRIVADO-WINDOWS-S1.md).

## Arrancar, detener y respaldar

Arrancar en primer plano utilizando sólo raíz y hash del despliegue:

```powershell
powershell.exe -NoProfile -File .\tools\windows\Invoke-RackClickPrivateDeployment.ps1 -Operation Start -DeploymentPath C:\RackClick_SVR\.local\operacion\demo01 -ExpectedDeploymentSha256 HASH_EXTERNO_DESPLIEGUE
```

Esperar el evento `ready` y usar la URL HTTPS que publica. Start fuerza validación TLS completa y cierre ordenado del host; reenvía los eventos nativos `ready`/`stopped` y conserva su código de salida. No hay instalación automática de confianza en navegador: el certificado autofirmado de siete días es para laboratorio. El ensayo usa un contexto cliente aislado con el PEM explícito, sin desactivar la validación de nombre o certificado.

En otra consola, detener:

```powershell
powershell.exe -NoProfile -File .\tools\windows\Invoke-RackClickPrivateDeployment.ps1 -Operation Stop -DeploymentPath C:\RackClick_SVR\.local\operacion\demo01 -ExpectedDeploymentSha256 HASH_EXTERNO_DESPLIEGUE
```

Esta operación distingue solicitud y confirmación. Sólo devuelve `stopConfirmed=true`, `valid=true` y exit0 tras comprobar el marcador final del mismo runId/instanceId, el lock de instancia libre, ausencia de postmaster.pid y ambos puertos cerrados. El plazo predeterminado es90s, configurable de1 a180 con `-StopTimeoutSeconds`. Un timeout devuelve error y no mata procesos. Repetir Stop tras la parada correcta devuelve `deployment_already_stopped` sin crear otra solicitud.

Los puertos se comprueban como ausencia de listeners en una instantánea local de IPv4/IPv6, incluyendo direcciones wildcard; un error al obtenerla no cuenta como cerrado. Esta lectura se combina con marcador y lock, sin prometer ausencia futura de listeners. La primera integración conservó un timeout de confirmación: la aplicación y PostgreSQL estaban detenidos, pero el chequeo anterior esperaba sólo500ms una conexión asíncrona que aquí devolvió rechazo después de2073ms. Se corrigió el chequeo y se probó con listeners reales abiertos/cerrados antes de repetir únicamente el método integrado. [API oficial](https://learn.microsoft.com/en-us/dotnet/api/system.net.networkinformation.ipglobalproperties.getactivetcplisteners?view=netframework-4.8.1).

La solicitud se publica atómicamente en el directorio del runId **capturado**, tras revalidar identidad y lock ocupado. Si comienza otra ejecución, no se dirige a ésta: nunca resuelve otra vez el runId para elegir el destino de publicación. Un cambio de ejecución durante la confirmación devuelve error. La revisión detectó y corrigió esa carrera antes de probar con PostgreSQL.

Durante la ejecución, crear backup en otro destino nuevo y disjunto:

```powershell
powershell.exe -NoProfile -File .\tools\windows\Invoke-RackClickPrivateDeployment.ps1 -Operation Backup -DeploymentPath C:\RackClick_SVR\.local\operacion\demo01 -ExpectedDeploymentSha256 HASH_EXTERNO_DESPLIEGUE -BackupPath C:\RackClick_SVR\.local\operacion\backup01
```

Sólo informa `deployment_backup_complete` tras éxito del backup nativo y verificación de manifiesto/dump. Conservar `backupManifestSha256` fuera del backup. Este dump no incluye PFX, archivos de configuración, roles globales ni una instalación completa. [Backup/restore nativos y límites](BACKUP-RESTAURACION-WINDOWS-S1.md).

Stop y Backup usan el modo Maintenance: validan recibo, instancia y distribución, pero no leen las claves TLS ni exigen un certificado vigente. Esto evita bloquear mantenimiento por un certificado dañado/caducado; no permite arrancar con TLS inválido. `Test-RackClickPrivateDeployment -Maintenance` permite comprobar ese núcleo explícitamente y publica `httpsValidated=false`. Si el estado activo pertenece a una ejecución HTTP manual diferente del origen HTTPS del recibo, Stop la rechaza; usar su comando nativo con la referencia de instancia correspondiente.

## Fallos y recuperación pendiente

Ante un fallo por etapa, conservar el destino parcial, estado y logs privados. No se publica éxito global ni se borran o sobrescriben sus archivos. La siguiente creación debe utilizar otro destino nuevo. No borrar postmaster.pid ni terminar procesos elegidos por nombre/PID para forzar la reutilización. La recuperación de datos en otra instalación usa RECUPERACION-DESPLIEGUE-WINDOWS-S1.md; la recuperación integral del host sigue pendiente.

No se acredita servicioSCM, identidad Windows mínima, arranque tras reinicio de Windows, CA/DNS/renovación productiva, instalación limpia en otra máquina, recuperación integral o adopción. `applicationGracefulExit` del lanzador tampoco certifica el vaciado universal de peticiones HTTP largas. [Creación](CREAR-DESPLIEGUE-PRIVADO-WINDOWS-S1.md) y [pruebas/resultados278–307](../evidence/s1-20261017/treinta-tandas-278-307/CIERRE.md) conservan las atribuciones y errores originales.

## Reproducir las pruebas de desarrollo

Desde este workspace y con evidencias de destino nuevas:

```powershell
C:/Python312/python.exe -B tools/tests/test_deployment_stop_identity.py --evidence evidence/RUTA_NUEVA_IDENTIDAD
C:/Python312/python.exe -B development/server/tests/test_private_deployment_flow.py --evidence evidence/RUTA_NUEVA_INTEGRACION
```

La primera es una intercalación de archivos controlada sobre funciones reales extraídas del AST; no inicia PostgreSQL/aplicación ni simula dos publicadores concurrentes. La segunda crea un laboratorio nuevo mediante comandos copiados a otra carpeta, con runtime real sinSDK: dos ejecuciones HTTPS por recibo y una HTTP nativa explícita únicamente para demostrar backup Maintenance con PFX dañado y PostgreSQL real. No es una nueva pasada de navegador o QA de Wascar.


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
