# Revisión independiente acotada · online19

12.11.2026 · Perfil `rackclick_security` · sólo lectura de producto y probes privados.

**Dictamen a este corte:** el bloqueo de creación de `work` fue comunicado y corregido por el implementador. La versión actual del lanzador pasa la prueba independiente de ese contrato y la suite acotada: **20/20**. No se encontraron otros bloqueantes para continuar la preparación de un activo final y su ensayo B. Este corte revisa **Core02 y su wrapper real**, no acredita todavía un ZIP online final ni instalación B, publicación o adopción.

## Encargo y separación

Coordinador: revisión de entradas, pins, rutas, ZIP, reparse, entorno, descargas y límites de distribución de la edición19; detenerse antes de instalar. Workspace leído: `C:\RackClick_SVR\.local\github-installable-20261112\worktree`. No se editó producto, VM, cuentas, SQL, GUI ni MFA; no se compiló con SDK, instaló, elevó, hizo commit o publicó. Propiedad de escritura limitada a este informe y `.local/github-installable-20261112/security-review/`.

Se leyó `AGENTS.md`, `docs/BRIEFING-MAESTRO.md`, `docs/EQUIPO-Y-SKILLS.md`, `.codex/agents/security.toml`, el contrato `docs/ENTREGA-GITHUB-EQUIVALENTE-W02A.md` y `docs/superpowers/plans/2026-11-12-instalador-online19.md`. La consulta de `using-superpowers/SKILL.md` señala que los subagentes enviados a tarea específica lo omiten; para afirmaciones de verificación se aplicó `verification-before-completion/SKILL.md`.

Estado Git observado antes de escribir evidencia: modificaciones preexistentes en los dos productores nativos; archivos nuevos online19, manuales, avisos y pruebas. Se respetaron sus cambios concurrentes. No se reutiliza el límite histórico R0 para reinterpretar la autorización S1; la limitación de sólo revisión corresponde a este encargo.

## Hallazgos

### ON19-01 · Alta, bloqueaba Prepare/Install · corregido por otro agente

El `Invoke-OnlineAssembly` leído inicialmente ejecutaba `CreateDirectory($Stage\work)` antes de lanzar Python. `assemble()` llama `require_new_work()` y rechaza toda carpeta existente con `new_assembly_root_required`. Así el recorrido real fallaba siempre antes de montar o instalar, aunque los tests con ensamblador sustituido pasaran.

Se notificó al coordinador antes de cualquier ensayo B. El implementador retiró esa creación y añadió `test_assembler_receives_new_work_path_and_creates_it_itself`; el stage padre privado se conserva. Comprobaciones propias: llamada a `assemble()` sobre el Core02 real con raíz precreada reproduce el rechazo sin escribir en esa raíz; la nueva prueba del lanzador real con Python fixture pasa en Windows PowerShell5.1. La prueba fixture verifica el contrato de creación; no reemplaza Prepare completo con descargas reales.

Lanzador corregido comprobado: SHA256 `65156ed6aacf81ae46b41ecfc006efd1ed6b47d6d1d3cf0b8e538b5e93e03a50` del template `tools/windows/online-install/Install-RackClickOnline.ps1`.

### ON19-02 · Baja, CLI directo · diagnóstico escrito tras rechazo de raíz existente

El bloque `__main__` de `tools/online-install/assemble.py` captura cualquier fallo y, si `args.work_root.is_dir()`, escribe `assembly-error.private.txt` allí. Por tanto una invocación directa con raíz ya existente falla con `new_assembly_root_required` pero añade ese archivo; la función `assemble()` por sí sola no lo añade. El probe conserva intacto el archivo `keep.txt` y observa el nuevo diagnóstico. Un diagnóstico previo con el mismo nombre sería reemplazado por `write_text()`.

No es un bypass demostrado del recorrido Windows: el lanzador fija una raíz hija nueva dentro del stage privado creado con ACL administrativa, y la corrección ON19-01 deja al ensamblador crearla. No bloquea el ensayo B; limita la afirmación de que **toda** invocación directa rechazada preserva absolutamente el directorio. No se modificó el CLI durante la revisión.

## Artefactos medidos

| Artefacto | Medida independiente |
|---|---|
|`Core19-02.zip`|8.799.576bytes;197miembros; SHA256 `b823c8d80b82c6b2fc332eea1e99e8e30cc7c46fe2ae7ffc8c1ff3678e4d854d`|
|Inventario Core02|196filas más `FILES.json`; todos los bytes del ZIP coinciden con el árbol verificado;79archivos de aplicación y37de servicio|
|`host-assembly-02/.local/RackClick-Servidor-19.zip`|SHA256 `4bb169adf155cb521ace5917afce40ddf3a59ff5a4123c5ce726bcc3f28584dd`|
|Bundle dentro del payload real|SHA256 `098392ebfc62f2fe5ec9f79909ea3bdbecbf3c565286747a5a9d9507fccd8d40`;79archivos de aplicación idénticos a Core02|
|DLL del servicio dentro del payload real|SHA256 `130e9cc3959d414a0e00759a2e3323a0fc004d76113df56c250f319d38065c61`; apphost EXE ausente|
|MIT completo del servicio|1115bytes; SHA256 `ae48df11a335dc1a615f4f938b69cba73bcf4485c4f97af49b38efb0f216353b`|
|THIRD-PARTY-NOTICES del servicio|78041bytes; SHA256 `6d15e10a101c6bfff2ab4429ed061bf76c456fc4b23ad6b03e0d0f8377148a21`|

Core02 no transporta `python.exe`, `python312.dll`, `vc_redist.x64.exe`, el apphost del servicio ni árboles `dependencies/` del runtime/PostgreSQL. Sí contiene bibliotecas de paquetes de la aplicación y del servicio, con los avisos aplicables. La ausencia medida es del Core02; no se extrapola a un activo final aún no leído.

**Contraste posterior de Core03:** `Get-FileHash -Algorithm SHA256` sobre `Core19-03.zip` devolvió también `b823c8d80b82c6b2fc332eea1e99e8e30cc7c46fe2ae7ffc8c1ff3678e4d854d`; conserva8.799.576bytes. Core03 es idéntico aCore02. El endurecimiento del colector sobre los79archivos de aplicación no forma parte del Core que transporta y no cambia este inventario. Se leyó su incorporación de pinsinventory/sums, digest por archivo y suma debytes; no se atribuye una nueva ejecución de ese colector a esta revisión.

## Pruebas ejecutadas realmente

Host Windows; `C:\Python312\python.exe -B`; pruebas PowerShell lanzadas con Windows PowerShell5.1. `TEMP`/`TMP` de la ejecución de pruebas apuntaron exclusivamente a la carpeta privada de revisión. No hubo elevación ni instalación. Las peticiones de los probes son simuladas; la navegación oficial de licencias es independiente de ellos.

Comando propio desde el worktree:

```text
C:\Python312\python.exe -B -m unittest tools.tests.test_online_installer19 tools.tests.test_online_installer19_windows -v
```

Resultado: **20 pruebas,11,830s,OK,exit0**. Incluye las7Python y13Windows actuales: pines, URL, host, cuenta/servicio existente, denegación previa a stage, rutasZIP, duplicados, symlink, tamaño/hash, entorno, salida de hijos acotada, comprobación de árbol nativo y separación Prepare/delegación Install. Los hechos de host para Server2025/noDC y algunas dependencias se simulan; ejecutar esta suite no instala ni certifica un Server2025 limpio.

Además se ejecutó el template actual con Windows PowerShell5.1, `-NoProfile -NonInteractive -File ...\Install-RackClickOnline.ps1 -Mode Check`, sobre este host: `exit2`, JSON `{"success":false,"code":"host_not_supported","installed":false}`. Es rechazo esperado del host Windows11 antes de crear stage; no se presenta como Check enB ni como verificación de pins sustituidos del activo final.

Prueba adicional propia:

```text
C:\Python312\python.exe -I -B .local\github-installable-20261112\security-review\probe_review.py
```

Ocho focos, todos con el resultado esperado, guardados en `probes-01.json`:

1. Core02 exacto, inventario/bytes, conteos79/37 y ausencia de rutas de runtimes restringidos.
2. Wrapper19 real: bundle098, aplicación79, DLL130e, MIT1115/TPN78041 y apphost ausente.
3. Redirección a host ajeno/HTTP/usuario/puerto ajeno rechazada antes de seguirla;4casos, sin red.
4. Flujo de proveedor que supera bytes fijados rechazado antes de escribir el bloque excedente;0bytes del fixture escritos; no se ejecuta.
5. Pin incorrecto y destino existente rechazados; contenido previo conservado.
6. Junction real creada sólo en el fixture privado: `no_reparse()` y `acquire()` rechazan el padre; no crean el archivo en su destino.
7. Raíz precreada del ensamblador real rechazada con el Core02 real, sin descargas ni escritura mediante la función.
8. Efecto del diagnóstico CLI en raíz existente reproducido, conservando el archivo testigo y código de fallo.

Salidas privadas: `security-review/unit-independent-01.log`, `probe_review.py`, `probes-01.json` y fixtures. El fichero `windows-initial-reviewed.ps1` es una copia del template ya corregido al iniciar la suite; no se presenta como versión roja original. La evidencia roja/verde del implementador se conserva en `windows-worker`, pero el dictamen anterior usa la reproducción y ejecución propias descritas.

## Archivos y símbolos consultados

Además de los contratos citados:

- `tools/build_online_installer19.py`: `members`, `collect`, `write_zip`, pins y filtro de transporte.
- `tools/online-install/assemble.py`: `safe_name`, `no_reparse`, `unique`, `read_json`, `verify_core`, `check_url`, `Redirect.redirect_request`, `verify_provider`, `acquire`, `require_new_work`, `extract_new`, `assemble` y manejo de error CLI.
- `tools/windows/online-install/Install-RackClickOnline.ps1`: `Assert-OnlineNoReparse`, `Assert-OnlineHostFacts/Host/FreshHost/Admin/Pins`, `Open-OnlineCore`, `Confirm-OnlineDownloads`, `New-OnlineStage`, `Assert-OnlineArtifact/PythonUri`, `Receive-OnlinePython`, `Assert-OnlineZipRawNames`, `Expand-OnlineZip`, `Set-OnlineChildEnvironment`, `ConvertTo-OnlineArgument`, `Invoke-OnlineAssembly`, `Assert-OnlineExtractedTree`, `Invoke-OnlineNativeLauncher`, `Write-OnlineSummary`, `Invoke-OnlineInstall` y tipos `Folder`/`Child`.
- `INICIAR-RACKCLICK.cmd`, ambos tests online19 y nuevo test del contrato work-root.
- `tools/package_server_installer.py`: `checked_edition`, `checked_path`, `safe_name`, `build` y diff de19; `tools/package_clean_server_installer.py`: `clean_build` y diff de19.
- `tools/package_offline_bundle.py`: pins/profiles48, fuentes, operadores y licencias; no se reconstruyó un bundle nuevo durante esta revisión.
- `development/online-installer19.sources.json`, `development/windows-service/packages.lock.json`, avisos `licenses/service-host-*`, manuales19online/SQL; Core02 `FILES.json`, receta y archivos seleccionados; recibo02 y ZIPnativo/payload/bundle anidados reales.
- Evidencia de investigación existente `service-licenses.json`, `prepare_resources.py` y `python-pin.json`; no se ejecutaron esos productores.

## Límites de licencias, seguridad y publicación

Se reconsultaron fuentes oficiales: [paquete WindowsServices10.0.12](https://www.nuget.org/packages/Microsoft.Extensions.Hosting.WindowsServices/10.0.12) identifica licenciaMIT; [redistribución de VC++](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files?view=msvc-170) exige atender los derechos y términos aplicables a quien redistribuye. Los avisos del servicio y el contrato del runtime son piezas distintas. Esta revisión mide su separación y el modelo de adquisición directa; no afirma una licenciaVisualStudio inexistente ni autoriza alojar CRT/runtime/PostgreSQL/Python enGitHub.

No ejecutados: descarga real de los4proveedores, fallo de red real, verificaciónAuthenticode de Python enB, creación real del stage protegido bajoProgramData mediante Prepare, Prepare integral del activo final, instalación New, PostgreSQL real, servicio/HTTPS/postboot, MFA/login/recuperación, ámbitos/revocaciónAPI, cargaDemo50 y backupB. Las pruebas de autenticación/autorización/revocación de la aplicación quedan fuera: se preservan los bytes79 de la app existente y no se convierte esa igualdad en nuevas pruebas funcionales. No se hizo un escaneo exhaustivo de secretos/historial ni una auditoría global de licencias. El secreto y los parámetros de instalación nativa no se crean durante esta revisión.

Antes de ejecutar InstallB debe revisarse el **ZIPonline final exacto**, con pinsCore/native/Python sustituidos y hash externo, evitando llamar revisado a Core03 por semejanza conCore02. Cambios posteriores de productor o de Core requieren registrar el nuevo hash y verificar su diferencia pertinente. La autorización de preparación no sustituye QA ni adopción final deWascar. Métrica del contrato **26,63/100 del cierre restante**, sin aumento por esta revisión y sin porcentajeglobal nuevo.

## Adenda · revisión del ZIP final Core04 antes de B

Esta adenda sustituye el pendiente de revisión del activo final del corte anterior. **Dictamen favorable** para ejecutar Check/Prepare enB y, si el montaje verifica el wrapper/árbol exactos y pasan los prechecks nativos, continuar el ensayo autorizado New19. No quedan hallazgos bloqueantes abiertos en este alcance. El dictamen no convierte esos pasos pendientes en pruebas ya ejecutadas, ni es adopción productiva.

Activo leído íntegramente: `.local/github-installable-20261112/entrega-19/RackClick-Windows-Online-19.zip`, **12.652.565bytes/68miembros**, SHA256 **`470e28c2848555b575aeff1ee3b2d98efb9819ef6e4116e7e1839a723247d231`**. El archivo externo `.sha256` coincide en hash y nombre. Se verificaron67hashes internos, con inventario exacto: CoreZIP,PS1,CMD,manual,recibo,SHA256SUMS y62miembrosDemo. Sin extras ni rutas duplicadas, traversal o symlink en la lectura del ZIP.

Core04 dentro del activo: SHA256 `572215e3e99b2510f64433ba458beead7de69c761b722ef521b0abb221ca35e5`,197miembros y196filas verificadas por tamaño/hash. Comparación byte por byte de **todos** los miembros contra Core02: sólo cambian `assemble.py` y `FILES.json`. Por tanto aplicación79,servicio37,DLL130e,avisosMIT/TPN,Npgsql/Otp,fuentes/operadores,receta,Demo03 y manual nativoSQL permanecen exactos. `assemble.py` del Core04 coincide con la fuente corregida actual.

No hay EXE/DLL/PDB/PFX/key/env sueltos en el activo externo; sus62miembrosDemo coinciden exactamente con los dos subdirectorios autorizados del ZIPDemo03 pinado del Core. Se comprobó además ausencia de CRT/Python/apphost del servicio y árboles de runtimes en Core04, junto con la igualdad completa anterior. No se aloja el wrapper nativo con sus dependencias en este activo online. Las bibliotecas de paquetes ya descritas se conservan en el Core con sus avisos; esta comprobación no los redefine como código propio.

La copia de `Install-RackClickOnline.ps1` empaquetada coincide exactamente con el template Windows ya revisado, sustituyendo una vez cada uno de los4tokensCore/native/PythonSha/PythonBytes; no queda ningún token. Native sigue fijado a `4bb169adf155cb521ace5917afce40ddf3a59ff5a4123c5ce726bcc3f28584dd`. CMD coincide con su fuente ahora situada en `tools/windows/online-install/INICIAR-RACKCLICK.cmd`. El manual externo es `INSTALADOR19-ONLINE.html`, distinto del manualSQL nativo; se confirmó que el manualSQL pinado no cambió. El recibo declara los4proveedores exactos, `thirdPartyRuntimeBinariesIncluded:false` y `productionAdopted:false`.

### Cierre de ON19-02 y pruebas propias de esta adenda

**ON19-02 corregido por el coordinador.** Se leyó el control `_owned_work`: empieza enNone,se restablece al comenzar `assemble()`,se asigna sólo después de crear una raíz exclusiva y restringe el diagnósticoCLI a esa raíz. Probe sobre el **CLI extraído del Core04 empaquetado**, con Core04 real y raíz existente que contiene tanto un testigo como un diagnóstico previo: exit1/`new_assembly_root_required`; ambos archivos conservados byte por byte y ningún miembro nuevo. El efecto anterior no persiste.

Ejecución propia adicional, limitada a los cambios nuevos; no se repitió la suite completa anterior:

```text
C:\Python312\python.exe -B -m unittest tools.tests.test_online_installer19.Online19Tests.test_cli_rejection_cannot_add_diagnostic_to_unowned_work_root tools.tests.test_online_installer19.Online19Tests.test_outer_package_rejects_unreviewed_core_before_creating_output -v
```

Resultado: **2/2,0,165s,OK,exit0**, salida privada `security-review/targeted-final04-tests.log`.

```text
C:\Python312\python.exe -I -B .local\github-installable-20261112\security-review\probe_final04.py
```

Resultado: **exit0/success:true**, salida `security-review/final04/final04-review.json`. Además de todas las mediciones anteriores, este probe:

- Carga el **PS1 empaquetado con sus pins sustituidos** en WindowsPowerShell5.1. `Assert-OnlinePins`, `Open-OnlineCore` y `Invoke-OnlineInstall('Check')` verifican el Core real. Sólo se sustituyen `Assert-OnlineHost` y `Assert-OnlineFreshHost` porque este host es Windows11; `New-OnlineStage` es un testigo que arrojaría error si se llamara. Resultado `online_checked`,sin llamar al testigo. No se presenta como CheckB real.
- Ejecuta `package()` en una salida privada nueva con el Core04 y wrapper19 exactos; produce de nuevo **el ZIP de12.652.565bytes con SHA470e28… exacto**. Es repetición del empaquetado de transporte, sin construir producto,bundle,servicio oinstalación.
- Da a `package()` el Core04 correcto y un native alterado: rechazo `native_release_pin_invalid` antes de crear el ZIP. Complementa el test del Core incorrecto.

Los archivos nuevos de prueba/extracción se encuentran exclusivamente en `security-review/final04/`; no se modificó el activo recibido ni producto. No se descargó, compiló, elevó, creó cuenta/servicio o instaló en esta adenda.

### Secuencia que debe conservar el ensayo B

`Assert-OnlineFreshHost` rechaza cualquier entradaRackClick bajoProgramData. Un `Prepare` exitoso deja precisamente un stage `RackClick-Online19-…`; lanzar después `Install` como una segunda ejecución desde cero lo rechazaría con `existing_installation`. Es una consecuencia de conservar la tentativa y denegar reutilización, no un nuevo bypass demostrado ni motivo para borrar el stage.

Para la tentativa única se puede hacer **Check→Install**, donde Install prepara/verifica/delega dentro de una llamada. Si se ejecuta **Prepare** por separado para inspección, el paso posterior es abrir explícitamente una vez el `INICIAR.ps1` nativo ya verificado en el stage informado; registrar preparación e inicio explícito, sin llamarlo una nueva ejecución integral de Install. El coordinador recibió este límite antes de operarB.

Se mantienen los no ejecutados del corte anterior paraB: adquisición de proveedores/Authenticode/ACLreal,nativoNew,servicio/HTTPS/MFA/Demo50/backup/reinicio y aceptación. No se certifican autenticación,ámbitos o revocaciónAPI por el empaquetado; la app79 sigue exacta. La publicación requiere conservar este ZIP/hash y el recibo real del ensayo, con Releaseprivada sin adopción automática. Métrica **26,63/100 del cierre restante**, sin aumento por la revisión.

## Adenda · outer02 tras fallo de red en B

**Dictamen favorable de la corrección acotada**, sin bloqueantes nuevos detectados. Se revisó el activo nuevo de `.local/github-installable-20261112/entrega-19-02/RackClick-Windows-Online-19.zip`: **12.653.708bytes/68miembros**, SHA256 **`186cecafcfa27009f9476ba5fc58bd6538710eb9d487886f8844008998296806`**. El anterior470e28… conserva íntegro su SHA256; no se sobrescribió.

Comparación independiente de todos los miembros: cambian únicamente **`Install-RackClickOnline.ps1`, `00-LEEME.html` y `SHA256SUMS.txt`**. Los67hashes internos coinciden. Core04 sigue `572215e3e99b2510f64433ba458beead7de69c761b722ef521b0abb221ca35e5`; pin nativo sigue4bb169…; recibo,CMD y62miembrosDemo exactos al470e. Se comprobó que el PS1 corresponde al template actual sustituyendo sus4tokens una vez, sin tokens pendientes. La igualdad del Core conserva la comprobación anterior de app79,servicio37,licencias y ausencia de runtimes restringidos; no se reconstruyó ni probó otra aplicación.

### Cambios de seguridad contrastados

- `Receive-OnlinePython`: tipa `WebException` y `SocketException` como `download_unavailable`, y el `IOException` de lectura de red recibe el mismo código. Se conserva la restauraciónTLS, sin reintento ni continuación tras el fallo. Las guardiasHTTPS/host/redirección/tamaño/hash siguen presentes y no se sustituyen por el manejo del error. Un fallo antes de obtener respuesta no crea el archivo; esta comprobación no promete que una desconexión a mitad de flujo borre un archivo parcial, que tampoco sería ejecutable sin verificar.
- `Get-OnlineInstallationRoots`, `Test-OnlinePreviousTransport`, `Assert-OnlineFreshHost`: sólo omite en el detector un **directorio hijo directo deProgramData**, sin reparse en su ruta, nombre exacto sensible a mayúsculas `RackClick-Online19-` más32hexminúsculos, ownerAdministradores oSYSTEM, DACLprotegida y exactamente2ACEexplícitas diferentesSYSTEM/Administradores,AllowFullControl,OI/CI y sin propagación especial. Otro propietario,nombre similar,archivo,junction,ACLpública/heredable/incompleta/deny o coincidencia enProgramFiles se rechaza. Las guardias de servicios y cuentas conservan su orden y rechazo. No se enumera ni utiliza contenido del stage omitido; no se borra,modifica,adopta o reanuda. El creador sigue generando un GUIDnuevo exclusivo.
- Manual externo: añade recursos de prueba sugeridos, espacio libre, necesidad deInternet/NAT y consulta de términos oficiales antes deADQUIRIR; conserva el manual nativoSQL pinado dentro del Core. La recomendación de recursos no es una medición de capacidad o rendimiento realizada por esta revisión.

La advertencia de la adenda anterior de que **todo** stage previo impediría otra invocación queda superada por esta excepción validada. Ahora una tentativa nueva puede ignorar un stage que cumpla estrictamente esos criterios y crea otro nuevo; eso no convierte un fallo anterior en éxito ni permite repetir una instalación parcialmente ejecutada. Con servicios/cuentas/instalación existentes sigue rechazando.

### Pruebas independientes nuevas, sin suite completa

Se ejecutaron sólo5pruebas pertinentes enWindowsPowerShell5.1, conTEMP/TMPdepruebas en el espacio privado:

```text
C:\Python312\python.exe -B -m unittest tools.tests.test_online_installer19_windows.OnlineWindowsTests.test_python_network_failure_is_sanitized_without_retry_or_output tools.tests.test_online_installer19_windows.OnlineWindowsTests.test_private_old_transport_allows_new_attempt_but_installations_and_aliases_reject tools.tests.test_online_installer19_windows.OnlineWindowsTests.test_private_transport_reparse_or_file_or_programfiles_name_is_rejected tools.tests.test_online_installer19_windows.OnlineWindowsTests.test_existing_rackclick_service_or_account_is_preserved tools.tests.test_online_installer19_windows.OnlineWindowsTests.test_python_url_closed_https_and_exact_size_hash -v
```

Resultado propio: **5/5,6,241s,OK,exit0**. El timeout usaWebRequestfixture:1solallamada,código sin detalleprivado,TLSrestaurado,ningúnarchivo. LasACLsonDirectorySecurityfixtures,sin cambiarACLdelhost; eljunctiondeltest esreal y privado. Elrecibo delstageanterior se conserva byteporbyte; nombres similares y las demás instalaciones siguen rechazados. No se presenta el16/16delimplementador como ejecución propia.

Probe propio `C:\Python312\python.exe -I -B .local\github-installable-20261112\security-review\probe_network_stage02.py`: **exit0/success:true**. Mide ZIP/delta/hash descritos y ejecutaCheck con elPS1 empaquetado yCore04real. Sólo sustituye hechos dehost/freshhost porque el equipo de revisión esWindows11; `New-OnlineStage` arrojaría error si se llamara y no se llama. Resultado `online_checked`. Se inspeccionaron losdiffs dePS1/manual extraídos de los dosZIPreales, sin fiarse sólo deldiff delworktree.

Evidencia propia nueva: `security-review/network-stage-targeted-tests.log`, `probe_network_stage02.py`, `network-stage02/review-outer02.json`, `packaged-check.log` y losdosdiffs. No se hizo otra suitecompleta ni otra compilación/descarga/instalación/operaciónVM; esta revisión escribe únicamente aquí y en su carpeta privada.

### Estado real recibido y límites

El coordinador comunica que enB el primerPreparefalló antes dePython porredhost-only sinpuertadeenlace, con0servicios/0cuentas. Posteriormente ejecutó elCheck delnuevo186c enB:exit0/`online_checked`,ignorando elstageprivado anterior;siguen0servicios y sin nuevoPrepare. **Es evidencia comunicada por el coordinador, no ejecución mía ni un ensayo de instalación exitoso.** La red/NAT sigue pendiente deWascar. El fallo previo y su recibo deben conservarse.

Se puede continuar el ensayo autorizado al disponerBdeInternet, usando este186c exacto y conservando resultados separados de cada tentativa. Siguen sin acreditarse adquisición real completa,Authenticode/montajeNew,servicio/HTTPS/MFA,Demos/backup/reinicio yQAfinal de este activo. Sin publicación realizada por este revisor ni aprobación de adopción. Métrica **26,63/100delcierre restante**,sin aumento por esta revisión.

## Adenda · transporte 03 con descarga TLS de Windows y caché verificada

**Dictamen favorable para Prepare03**, con el activo exacto identificado abajo. No se encontraron bloqueantes nuevos en esta revisión acotada. Se mantiene la necesidad de comprobar la descarga completa, el montaje y los resultados reales en B antes de atribuirles éxito.

Activo revisado: `.local/github-installable-20261112/entrega-19-03/RackClick-Windows-Online-19.zip`, **12.655.070 bytes / 68 miembros**, SHA256 **`4d9dccbe75cc6a1900204699459fa0653cfaa4722626f9b48484e9259aacd6bf`**. Sus 67 hashes internos coinciden. Comparación completa frente a 186cec…: cambian sólo `Install-RackClickOnline.ps1`, `ENTREGA.json` y `SHA256SUMS.txt`. La única diferencia del recibo es `transportRevision:3`. Core04, driver, wrapper nativo, manual, CMD, avisos y Demo62 conservan los bytes ya revisados. Los activos anteriores 470e28… y 186cec… conservan sus hashes; no se sobrescribieron.

### Cadena de confianza y cambios consultados

Se inspeccionó el delta del PS1 extraído de ambos ZIP, además de la fuente y sus pruebas. El PS1 empaquetado coincide exactamente con el template actual tras sustituir sus cuatro tokens; no quedan tokens pendientes.

- El core sigue fijado a `572215e3e99b2510f64433ba458beead7de69c761b722ef521b0abb221ca35e5` y el nativo a `4bb169adf155cb521ace5917afce40ddf3a59ff5a4123c5ce726bcc3f28584dd`.
- `Get-OnlineProviders` comprueba los **bytes exactos** de `recipe.json` antes de parsear JSON: SHA256 literal `f382af8c4c242d243ab605e7ba6065e098e09d841ee1495739a74908005ae684`, medido también en el Core04 real. Requiere tres IDs únicos y siete propiedades exactas por proveedor; perfiles cerrados para nombre de archivo y algoritmo, tamaños positivos acotados, digests con longitud/formato correctos y rutas de destino delimitadas. Los valores concretos de URL, tamaño y digest quedan anclados por el pin de la receta. No hay un argumento CLI para sustituir la URL o la receta admitida.
- `Assert-OnlineProviderUri` exige HTTPS, puerto443, sin usuario ni fragmento, y hosts propios del ID: Microsoft para SDK, `get.enterprisedb.com` para PostgreSQL y `download.visualstudio.microsoft.com` para CRT. Comprueba de nuevo cada redirección; no usa redirección automática. Un host autorizado para otro proveedor no basta.
- `New-OnlineRequest` usa `HttpWebRequest` con la validación TLS ordinaria de Windows, sin sustituir callbacks globales ni por petición, sin añadir CA ni aceptar certificados manualmente. En un proceso PowerShell nuevo se comprobó que ambos callbacks están en null. Esto conserva la comprobación normal de certificado/cadena/nombre del proveedor; no es un certificado pinado nuevo ni una prueba propia de conexión TLS real a B.
- `Receive-OnlineProvider` exige estado200, tamaño declarado cuando existe, límite de bytes durante el flujo y tamaño/digest final SHA256 o SHA512 según perfil. Archivos `CreateNew`, tiempos de petición/lectura90s y límite de flujo por proveedor; restaura TLS en `finally`. Redirección ajena, contenido corto/excesivo, hash incorrecto o error de lectura se detienen. Un archivo parcial no se acepta ni se ejecuta.
- `Receive-OnlineProviders` crea un directorio `Stage/providers` nuevo; rechaza uno existente. `Assert-OnlineProviderCache` exige exactamente los tres archivos, sin subdirectorios ni reparse, y vuelve a verificar tamaños/digests. `Invoke-OnlineAssembly` llama a esta guardia **antes de consultar Authenticode o iniciar Python** y pasa la ruta fija mediante `--cache`. El driver Core04 ya soportaba ese argumento: vuelve a verificar cada candidato, copia exclusivamente y verifica la copia; no se cambió para esta entrega.

Se conservaron las guardias de stage, host, cuentas, servicios, pins del core/nativo, entorno del hijo y árbol nativo. La igualdad del Core conserva las comprobaciones previas de aplicación79, servicio37 y licencias; no hay una nueva compilación, SQL o modificación de MFA en este cambio.

### Pruebas propias nuevas

Se ejecutaron sólo cinco pruebas pertinentes en Windows PowerShell5.1; no otra suite completa:

```text
C:\Python312\python.exe -B -m unittest tools.tests.test_online_installer19_windows.OnlineWindowsTests.test_provider_recipe_pin_profiles_and_changed_metadata_reject_before_cache_creation tools.tests.test_online_installer19_windows.OnlineWindowsTests.test_provider_windows_transport_caps_hash_and_redirect_hosts tools.tests.test_online_installer19_windows.OnlineWindowsTests.test_provider_cache_missing_partial_or_extra_rejects_before_python tools.tests.test_online_installer19_windows.OnlineWindowsTests.test_provider_set_is_fresh_complete_and_never_reuses_existing_cache tools.tests.test_online_installer19_windows.OnlineWindowsTests.test_assembler_receives_new_work_path_and_creates_it_itself -v
```

**Resultado: 5/5, 7,230s, OK, exit0.** Incluye receta cambiada, SHA512, tamaños incorrectos con/sin Content-Length, cortos/excesivos, redirección ajena, IOException real de un Stream fixture, una petición sin reintento, caché incompleta/extra y creación exclusiva de caché y work. Se comprobó el paso de `--cache` en la prueba del proceso hijo. Las respuestas de descarga son fixtures y no conexiones reales.

Probe propio adicional:

```text
C:\Python312\python.exe -I -B .local\github-installable-20261112\security-review\probe_schannel03.py
```

**Resultado final: exit0 / success:true**, en `security-review/schannel03-02/review-transport03.json`. Verifica el inventario/delta/pins descritos utilizando el PS1 y core extraídos del activo exacto. Llama a `Invoke-OnlineAssembly` real con caché ausente y luego parcial, y coloca un testigo en `Get-AuthenticodeSignature` que fallaría si se alcanzase: ambas llamadas se rechazan con `provider_cache_incomplete`, antes del testigo, sin crear `work` y conservando el parcial. Una receta alterada se rechaza antes de crear caché. También prueba rechazo de cruces SDK/CRT/PostgreSQL, host con sufijo ajeno y puerto distinto. `Open-OnlineCore` y los pins se comprueban sobre el archivo real; no hay descarga, instalación o VM.

La primera ejecución del probe dejó un directorio privado incompleto `schannel03`: su función de arnés no forzaba exit0 después de una excepción esperada y capturada, por lo que PowerShell devolvía exit1 aunque la aserción del código de rechazo fuera correcta. Se corrigió sólo el arnés privado añadiendo el cierre explícito, y se repitió en el directorio nuevo `schannel03-02`. No fue un fallo del producto ni se modificó código de aplicación para obtener el resultado.

Evidencia propia: `security-review/schannel03-targeted-tests.log`, `probe_schannel03.py`, `schannel03-02/review-transport03.json` y `launcher-delta.diff`. El 20/20 del implementador y el 9/9 Python del coordinador son resultados comunicados, no se contabilizan como nuevas ejecuciones propias.

### Hechos de B comunicados y límites

El coordinador informa que B ya tiene salida a Internet, que Prepare02 falló en Python con `SSL missing local issuer` antes del SDK/instalación y con cero cuentas/servicios, y que las tres peticiones HEAD desde .NET/Windows dieron200 y tamaños exactos con TLS normal, sin callbacks de confianza ni CA manual. También comunica Check03 real exit0 en B y cero servicios. Estos hechos **no fueron ejecutados por este revisor**; no sustituyen el GET completo con pins ni Prepare03.

La revisión permite continuar el ensayo autorizado con **4d9dcc… exacto**, conservando fallos anteriores separados. No se acredita todavía descarga completa de los tres proveedores por este transporte, montaje03, ejecución New19, CRT/reinicio, PostgreSQL, servicio, HTTPS, MFA, Demo50, backup o postboot en B. No se publicó ni adoptó el producto desde esta revisión. Métrica **26,63/100 del cierre restante**, sin aumento por el cambio de transporte o por este informe.
