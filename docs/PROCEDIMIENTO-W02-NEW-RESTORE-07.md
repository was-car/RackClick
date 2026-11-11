# W-02 · Recorrido New y Restore de la edición 07 en VM Windows Server 2025 limpia

Estado vigente: **ejecutado en VM de laboratorio el 25.10.2026** (New en W02-A; Restore al tercer intento en W02-B; verificación posterior al reinicio registrada en ambas). Codex acredita W-02.01 con 0,50 puntos; W-02 queda en 0,50/2,50. W-02.02 sigue con evidencia parcial y 0 puntos. Evidencia: `evidence/s1-20261025/w02-vm-limpia-07-claude/ejecucion-2026-10-25/` (incluida la adenda para Codex). Cambios pendientes de Codex: nombre nuevo de administrador de recuperación (en hoja e interfaz), explicación del bloqueo de cuenta preservada, y presentación del estado posterior al reinicio. Las instrucciones de este documento describen el procedimiento, no un ensayo nuevo.

## Nota del auxiliar W-02-R3 (no cambia la edición 07)

El ejecutor `Invoke-W02TrialPlan.ps1` incorpora desde W-02-R3 lo siguiente. Es un cambio del auxiliar externo, con su propia versión y hash. **Los paquetes 07 y el instalador `INICIAR.ps1` no cambian.**

- **Carpeta por intento:** cada Execute crea `OutputDirectory\runs\<id>\`.
- **Recibo de inicio:** `recibo-inicio.json` se publica antes de la primera llamada `-VerifyOnly`. Si no se puede publicar, no se lanza el envoltorio.
- **Fases con salida observada:** `fase-02-verify.json`, `fase-03-interactiva-inicio.json` y `fase-04-interactiva-fin.json`. Una fase sin salida observada no se rellena: la recogida la indica como `unknown`.
- **Recogida de solo lectura:** `-Mode Reconcile -OutputDirectory <carpeta> [-ResultPath <result.json preboot>] [-ManagementPath <carpeta de gestion>]`. Escribe un único informe `reconciliacion-<id>.json`. No invoca el envoltorio, el instalador, la limpieza ni ninguna acción sobre la VM.

Estas instrucciones describen el auxiliar actual. El ensayo 07 ya realizado usó la versión anterior y su evidencia no se reescribe.

## 1. Alcance

Cubre: instalación nueva (New) y restauración (Restore) de la edición 07 con los artefactos fijados, en una VM Windows Server 2025 que no es controladora de dominio.

No cubre, y no debe registrarse como probado con este recorrido:

- El equipo de desarrollo **LEAO** y la VM QA **192.168.250.78**. Ambos están excluidos por el ejecutor y no reciben esta prueba.
- Windows 11 como host de servidor (W-02.04). Es un ensayo distinto.
- Una controladora de dominio real (la comprobación "DC antes de mutaciones" de W-02.03 necesita un laboratorio con DC).
- Cuenta de servicio, SCM y reinicio como tarea propia (W-03); HTTPS, CA y red (W-04); MFA, proveedor de laboratorio, custodia D2, reproducibilidad y redistribución (tareas propias).

## 2. Requisitos y registro de la VM (W-02.01)

Requisitos:

- Windows Server 2025 (`Microsoft Windows Server 2025 …`), x64, de tipo servidor (no cliente) y **sin** rol AD DS ni controlador de dominio.
- Cuenta de administrador local propia de la prueba. No usar cuentas de QA ni contraseñas existentes.
- IPv4 interna dentro de una subred que se declarará en la hoja de datos. La IP no puede ser 192.168.250.78.
- Sin SDK de .NET, Node ni Python previos para el ensayo limpio (W-02.02). El ejecutor registra en `herramientas_previas` lo que encuentra, como dato.
- Tomar un punto de restauración (checkpoint) de la VM antes de empezar. No forma parte del recorrido, pero permite repetir desde cero.

Registro obligatorio antes de instalar. Guardarlo en `C:\W02\informes\registro-vm.txt` (privado) y resumirlo en la evidencia sin datos de cuentas:

| Dato | Cómo obtenerlo |
|---|---|
| Imagen o ISO y fecha de creación | Origen de la plantilla y hash del medio |
| Edición y build | `Get-CimInstance Win32_OperatingSystem` (Caption, Version, BuildNumber) |
| Nombre del equipo | `$env:COMPUTERNAME` |
| Rol del equipo | `Get-CimInstance Win32_ComputerSystem` (DomainRole: debe ser 2 servidor independiente o 3 servidor miembro; 4 y 5 son controladores de dominio) |
| IPv4 y subred | `Get-NetIPAddress -AddressFamily IPv4` |
| Discos y espacio libre | `Get-Volume` |
| Cuentas locales | Nombres únicamente |
| Versión de PowerShell | `$PSVersionTable.PSVersion` |
| Hipervisor y red virtual | Nombre del conmutador |

## 3. Artefactos exactos

Origen en LEAO: `.local/instalador-07/entrega/`. Copiarlos a la VM por un medio aprobado y comprobar el hash tras copiar. Los ZIP no se descomprimen en la carpeta de artefactos.

| Fichero | Tamaño (bytes) | SHA256 | Uso en este recorrido |
|---|---|---|---|
| `RackClick-Servidor-07.zip` | 117668829 | `3ca223230fc5ea1ab1e2ce7e40c9b7ca222ef65e4735412cb3fdb7cfd19ddca1` | Envoltorio de arranque. Su `PAQUETE.json` interno debe ser `bca8e213acca4dd568140d8b769d5ad8a4ef6f1b06ee52f6a6cff820a5de4b13` (833 bytes) |
| `RackClick-Servidor-07-payload.zip` | 117645278 | `71469d1e084fe1927eadfc2122540868c1db8bf9ac1d22f8819574e4afef8d37` | Payload (dentro del envoltorio como `Servidor.zip`) |
| `RackClick-Bundle-M3-14-07.zip` | 117388494 | `6d5a3896422c308e6b086822aaaa76a5fb6cc2584cf0664666f96504709e14f8` | Bundle interno fijado en el payload |
| `RackClick-Cambiar-IP-07.zip` | 265182 | `b36fd6d394f090d4fcbc16fa7c278132486a58ed8c774199b5001ea0030703bd` | No se usa aquí (cambio de IP es otro recorrido) |

`payload.json` dentro del payload tiene SHA256 `25a764a9fa40f0e8feb39cfbc9b2b3f1f21bb1137738edd53614b257f6277ec7`. El ejecutor lo comprueba.

Carpetas de trabajo en la VM (ejemplo; cualquier ruta local nueva sirve):

- `C:\W02\artefactos\`: los ZIP copiados.
- `C:\W02\envoltorio\`: vacía. Aquí se descomprime el envoltorio.
- `C:\W02\hojas\`: hojas de datos (JSON).
- `C:\W02\informes\`: salida del ejecutor y registro.
- `C:\W02\restore\`: solo para la fase Restore, copia del backup de la VM A.

Ejecutor: copiar `tools/windows/w02/Invoke-W02TrialPlan.ps1` a `C:\W02\` junto a las carpetas. Sus informes incluyen su propio SHA256.

## 4. Hoja de datos (15 campos)

El validador oficial (`RackClick.Setup.ps1`) exige estos 15 campos, con este nombre, en un JSON. Ningún campo es una contraseña. Todos los valores de ejemplo son ficticios.

| Campo | Regla oficial | Ejemplo ficticio |
|---|---|---|
| `schemaVersion` | Siempre `1` | `1` |
| `id` | GUID en minúsculas, formato `D` | `2b7e1c3a-9d4f-4e8a-b1c2-0f3e5d6a7b8c` |
| `bindAddress` | IPv4 no loopback, no 169.254.x.x, dentro de `allowedSubnet` | `192.168.206.10` |
| `publicHost` | Nombre DNS o IPv4 válido | `w02-prueba.lan` |
| `httpsPort` | Entre 1024 y 65535; distinto de `postgresPort` | `8443` |
| `postgresPort` | Entre 1024 y 65535; distinto de `httpsPort` | `55432` |
| `allowedSubnet` | IPv4 con prefijo /8 a /32, canónica (la dirección de red) y que contiene `bindAddress` | `192.168.206.0/24` |
| `systemhaus` | Texto sin saltos de línea ni comillas, máximo 100 caracteres | `Sistemhaus de prueba` |
| `bootstrapUser` | Igual que `systemhaus` | `admin-prueba` |
| `serviceName` | `RackClick` o `RackClick-Recovery-` + 8 a 32 hex en minúsculas | `RackClick` |
| `accountName` | `RackClickSvc` + hasta 8 letras o cifras | `RackClickSvcW02` |
| `mode` | `New` o `Restore` | `New` |
| `backupPath` | Vacío en New; ruta local en Restore | `""` |
| `backupManifestSha256` | Vacío en New; 64 hex en minúsculas en Restore | `""` |
| `trustOnServer` | Debe ser `true` (confianza explícita en el servidor) | `true` |

Plantilla de la hoja New (guardar en `C:\W02\hojas\new.json`):

```json
{
  "schemaVersion": 1,
  "id": "2b7e1c3a-9d4f-4e8a-b1c2-0f3e5d6a7b8c",
  "bindAddress": "192.168.206.10",
  "publicHost": "w02-prueba.lan",
  "httpsPort": 8443,
  "postgresPort": 55432,
  "allowedSubnet": "192.168.206.0/24",
  "systemhaus": "Sistemhaus de prueba",
  "bootstrapUser": "admin-prueba",
  "serviceName": "RackClick",
  "accountName": "RackClickSvcW02",
  "mode": "New",
  "backupPath": "",
  "backupManifestSha256": "",
  "trustOnServer": true
}
```

**Identificador (`id`).** El ejecutor valida el formato del `id` de la hoja, pero la interfaz genera su propio UUID al instalar. Ese UUID real se registra aparte, en el registro de la VM, y **no** se exige que coincida con el de la hoja. Lo que sí se compara, después de la instalación, son los otros 14 campos: `schemaVersion` y los 13 valores configurables (`bindAddress`, `publicHost`, `httpsPort`, `postgresPort`, `allowedSubnet`, `systemhaus`, `bootstrapUser`, `serviceName`, `accountName`, `mode`, `backupPath`, `backupManifestSha256`, `trustOnServer`).

Límite conocido: el ejecutor no compara la hoja con el plan que genera la interfaz. Esa comparación es manual, de los 14 campos anteriores, y debe anotarse. Si la interfaz guarda su plan en la carpeta privada del informe, compararlo también. Pendiente de confirmar en la VM.

Credenciales: la interfaz puede pedir claves. Se introducen solo en la interfaz, no se escriben en la hoja, en el informe ni en el chat, y se guardan solo en el gestor de contraseñas del operador. La cuenta de servicio recibe una clave aleatoria cifrada local, según indica el propio resumen del instalador.

## 5. Recorrido New (W-02.02)

**5.1 Comprobación de artefactos (sin cambios en la VM).** En PowerShell de Windows, como administrador:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\W02\Invoke-W02TrialPlan.ps1 -Mode Check -OutputDirectory C:\W02\informes -ArtifactDirectory C:\W02\artefactos
```

Debe dar `pass`. Si falla, parar y registrar el código del informe `check-report.json`.

**5.2 Descompresión del envoltorio.** Descomprimir `RackClick-Servidor-07.zip` en `C:\W02\envoltorio\`. Se crea la subcarpeta `RackClick-Servidor-07\`; esa subcarpeta es la que se pasa como `-WrapperDirectory`.

**5.3 Validación de la hoja.** Guardar la hoja en `C:\W02\hojas\new.json` y ejecutar:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\W02\Invoke-W02TrialPlan.ps1 -Mode Plan -OutputDirectory C:\W02\informes -ArtifactDirectory C:\W02\artefactos -PlanPath C:\W02\hojas\new.json
```

Debe dar `setup_plan_valid`. Cualquier otro código se registra; no se corrige por adivinación. Si el código es `plan_field_control_character` o `plan_field_invalid_path_character`, el informe indica el campo en `field`. `plan_json_invalid` no identifica campo, porque la hoja no se pudo leer.

**5.4 Arranque guardado.** Solo la VM de prueba puede aparecer en la allowlist; el nombre se escribe dos veces (allowlist y confirmación):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\W02\Invoke-W02TrialPlan.ps1 -Mode Execute -OutputDirectory C:\W02\informes -ArtifactDirectory C:\W02\artefactos -PlanPath C:\W02\hojas\new.json -WrapperDirectory C:\W02\envoltorio\RackClick-Servidor-07 -AllowedComputerName NOMBRE-VM -ConfirmComputerName NOMBRE-VM
```

El ejecutor comprueba, en este orden:

1. Que el equipo no está excluido (LEAO).
2. Que está en la allowlist y que el nombre confirmado coincide.
3. **Vuelve a validar la hoja con el validador oficial.** Un `plan-report.json` anterior no cuenta como validación; sus puertos y valores se derivan de la hoja validada ahora.
4. Que el Check nuevo pasa.
5. **Que el contenido del envoltorio coincide con el ZIP oficial fijado por hash**, con su `PAQUETE.json` auténtico (`bca8e213…`). Un `PAQUETE.json` local, aunque coherente consigo mismo, no basta. Se rechazan ficheros extra, nombres no listados y puntos de reparse.

Los ficheros validados quedan **bloqueados** desde esa comprobación hasta el final de los dos lanzamientos: se abren solo para lectura y sin compartir escritura ni borrado. Sus hashes se comprueban sobre esos mismos identificadores antes de la primera llamada y de la segunda. Así ni el envoltorio ni otro proceso pueden cambiar esos bytes entre ambas llamadas.

Después ejecuta `INICIAR.ps1 -VerifyOnly` con los ficheros bloqueados (no instala, pero deja un área privada en `%LOCALAPPDATA%\RackClick`). **Antes de seguir, comprobar esa primera llamada:** `execute-report.json` no debe contener `execute_verify_failed`, y `execute-verify-salida.json.err` debe estar vacío. Solo entonces el ejecutor lanza el `INICIAR.ps1` oficial interactivo. Si la primera llamada no puede leer el envoltorio retenido, parar y recoger el informe; no retirar el bloqueo para continuar.

En la interfaz oficial: confirmar la limpieza (en una VM limpia el resumen no debe mostrar bloqueos) y elegir **New**. Introducir los mismos valores de la hoja. El ejecutor no interpreta el resultado de la interfaz; espera a que el proceso termine y registra su código de salida.

**5.5 Reinicio y acceso de verificación.** El instalador devuelve el estado `awaiting_reboot` con código de salida 3 cuando falta reiniciar (runtime, PostgreSQL 17 o CRT). En ese caso:

1. Copiar el mensaje exacto del instalador y la hora.
2. Reiniciar la VM.
3. Abrir el acceso `RackClick-VERIFICAR-05-<8 caracteres>.cmd` que esta edición 07 dejó en el Escritorio durante la instalación. Es el de esta 07; el `05` del nombre es la etiqueta histórica ya documentada. Abre el panel de la instalación existente con `Show-RackClickInstalledServer.ps1 -VerifyInstallation` (pide elevación). Seleccionar la instalación si el panel la ofrece.
4. Pulsar **Verificar instalacion** (así aparece el botón) y anotar el resultado.

Tras reiniciar no se vuelve a ejecutar Execute, `INICIAR.ps1` ni la limpieza. El ejecutor no reanuda el flujo automáticamente, y no se declara fallido por ello. Si el acceso no existe, o no abre ninguna instalación, parar y recoger el informe; no improvisar otra instalación. No ejecutar pasos manuales que no estén documentados.

**5.6 Verificación.** Usar el botón **Verificar instalacion** del panel de instalación de RackClick y anotar su resultado. No ampliar a HTTPS, MFA ni red; eso corresponde a otras tareas.

**5.7 Informe.** Al terminar, `Collect-RackClickInstallReport.ps1` crea un ZIP sanitizado en el Escritorio del usuario que ejecutó la instalación. Copiar ese ZIP y su SHA256 a la evidencia. Si el paquete extraído no aparece con ese nombre, buscarlo en `%LOCALAPPDATA%\RackClick\SetupPayloads\<id>\operators\server-install\` y registrar la ruta usada.

**5.8 Copia de seguridad.** El instalador ya ejecuta una vez la tarea de copia al terminar. Para la fase Restore, comprobar que existe una copia completa en la VM A (la exportación exige `scheduled_backup_complete`). Si no existe, parar y registrar.

## 6. Recorrido Restore (dos VM)

Restore necesita una copia de una instalación New. Se usan dos VM: la VM A (New, del apartado 5) y la VM B (la que se restaura). La VM B tiene **sus propias** IP y `publicHost`; no reutiliza los de la VM A.

**6.1 Dato de prueba en la VM A.** Con la interfaz de RackClick, crear un cliente o sistema de prueba sintético con un nombre reconocible. Lanzar después la tarea de copia de RackClick (su nombre exacto aparece en el informe y en el Programador de tareas) y esperar a que termine.

**6.2 Exportación en la VM A.** Ejecutar como administrador, con la carpeta de gestión que muestra el instalador (`managementPath`):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "RUTA\Export-RackClickServerBackup.ps1" -ManagementPath "CARPETA-GESTION"
```

Se pide elevación (UAC). El exportador abre un diálogo: elegir una **carpeta local NTFS** del operador (el exportador rechaza otras). Crea `RackClick-Backups\<guid>\` con `manifest.json` y `data.dump`, y junto a ella `RackClick-Backups\<guid>.sha256.txt` con el SHA256 del manifiesto. Ese valor es el que se pone en la hoja.

Comprobar el resultado: en la carpeta de gestión queda un fichero `backup-export-*.json` cuyo campo `code` debe ser `export_complete`. Si no lo es, parar y registrar el código.

**6.3 Traslado y comprobación en la VM B.** Copiar la carpeta `<guid>\` y su `<guid>.sha256.txt` a `C:\W02\restore\`. Comprobar:

```powershell
(Get-FileHash -LiteralPath C:\W02\restore\<guid>\manifest.json -Algorithm SHA256).Hash.ToLowerInvariant()
```

Debe coincidir con el valor de `<guid>.sha256.txt`. Si no coincide, parar.

**6.4 Hoja Restore y ejecución en la VM B.** Crear la hoja de la VM B con su propia `bindAddress`, `publicHost` y `allowedSubnet`, y con estos valores: `mode` = `Restore`, `backupPath` = ruta local de la carpeta copiada, `backupManifestSha256` = el valor de `<guid>.sha256.txt`. Después, repetir los apartados 5.1 a 5.4. En la interfaz, elegir **Restore** y los mismos valores.

Repetir también 5.5 a 5.7 (reinicio y acceso de verificación si lo pide el instalador, verificación y informe), desde la VM B.

**6.5 Comprobación de datos.** En la VM B, debe existir el dato sintético creado en 6.1. Si no aparece, registrarlo como fallo de restauración.

## 7. Criterios de parada

Parar, registrar el código y no reintentar mutando si ocurre cualquiera de estos casos:

- Un `Check` o `Plan` no pasa.
- Un hash no coincide, el manifiesto de la copia no coincide con el `.sha256.txt`, o el `PAQUETE.json` del envoltorio no coincide con el autorizado.
- Aparece un fichero extra en el envoltorio o un punto de reparse.
- El host es controlador de dominio, tiene una IP excluida, o ya existe un servicio `RackClick*`.
- Un puerto de la hoja ya está ocupado.
- El nombre del equipo es LEAO o la IP es 192.168.250.78.
- La primera llamada (`-VerifyOnly`) no termina bien: `execute-report.json` con `execute_verify_failed`, o `execute-verify-salida.json.err` con contenido, sobre todo errores de compartición. No retirar el bloqueo para continuar.
- El exportador no devuelve `export_complete`.
- Tras reiniciar, el acceso `RackClick-VERIFICAR-05-*.cmd` del Escritorio no existe o no abre la instalación existente, o la verificación con **Verificar instalacion** no pasa.
- El instalador devuelve un código que no se entiende.

No borrar servicios, bases ni carpetas que no sean de esta VM de prueba. La limpieza solo se hace con el flujo de reset que propone el propio envoltorio, tras su confirmación, y solo en la VM de prueba.

## 8. Evidencia que se entrega

Carpeta: `evidence/s1-20261025/w02-vm-limpia-07-claude/`, con un subdirectorio por ejecución:

- `registro-vm.md` (sin cuentas ni contraseñas), con el UUID que generó la interfaz.
- Informes del ejecutor: `check-report.json`, `plan-report.json`, `execute-report.json`, con sus SHA256.
- Mensajes exactos de reinicio, si los hubo, y el resultado de la verificación tras abrir el acceso RackClick-VERIFICAR-05-*.cmd.
- ZIP sanitizado del instalador y su SHA256.
- Resultado de la verificación del panel y del dato de prueba (Restore), y el `backup-export-*.json` con `export_complete`.

Usar nombres sintéticos en la hoja y en el dato. No incluir hojas con nombres reales de clientes ni la carpeta privada del instalador.

## 9. Subpasos de W-02 (estado)

Cada subpaso pesa 1/2 punto del cierre (según `docs/PLAN-CIERRE-RACKCLICK.json`, sin modificar aquí).

| Subpaso | Qué exige | Dónde se cubre | Estado |
|---|---|---|---|
| W-02.01 | VM limpia Windows Server 2025 sin AD DS, con registro | Apartado 2 | pendiente |
| W-02.02 | Entrega completa sin SDK/Node/Python previos; runtime, PostgreSQL 17 y CRT; reinicio | Apartados 5.1 a 5.5 | pendiente |
| W-02.03 | Dependencias compatibles presentes; rechazo de versión incompatible, puertos ocupados y DC antes de mutaciones | Apartados 5.1, 7; rechazo de versión y DC real pendientes | pendiente |
| W-02.04 | Windows 11 como posible host, o límite explícito | Fuera de este procedimiento | pendiente |
| W-02.05 | Criterio de cierre y revisión independiente | Apartados 5.6, 6.5, 8 | pendiente |

El Restore de los apartados 6.x es parte del criterio de cierre de W-02 ("recorrido nuevo completo"), y debe registrarse junto a W-02.02 y W-02.05.

## 10. Límites conocidos

- Ningún paso de este procedimiento se ha ejecutado en una VM real. El ejecutor se probó en un equipo de desarrollo con rechazos, con la verificación del envoltorio sobre una copia y con la comprobación de puerto ocupado; la ruta de lanzamiento no se ha probado.
- **Diagnóstico de rutas (H1).** El ejecutor rechaza antes del validador oficial los caracteres de control (en cualquier campo de texto) y los caracteres inválidos para ruta (solo en `backupPath`), con códigos propios: `plan_field_control_character`, `plan_field_invalid_path_character` y `plan_json_invalid`. Los dos primeros indican el campo; `plan_json_invalid` no identifica campo. El validador oficial (`RackClick.Setup.ps1`) no se ha modificado. Si una ruta inválida no cubierta por ese diagnóstico llega al validador, este lanza una excepción de .NET sin código oficial, y el ejecutor la registra como `w02_plan_failed` y falla cerrado. Pendiente de decidir si se corrige en el validador en una edición posterior.
- **Etiquetas "05" (H3).** El envoltorio 07 contiene tres textos con la etiqueta antigua "05", visibles al operador: el título del formulario `RackClick 05 - Preparar instalacion en servidor de a…`, el título del cuadro de error `RackClick 05` y el nombre del verificador `RackClick-VERIFICAR-05-`. No se cambian en la edición 07 porque implicaría regenerar el paquete. Se parametrizarán en una edición sustantiva posterior.
- Comparación de la hoja con el plan de la interfaz: manual, pendiente de confirmar en la VM.
- Exclusiones de LEAO y de 192.168.250.78 y allowlist: controles adicionales del ejecutor. No sustituyen a las comprobaciones reales del host.
