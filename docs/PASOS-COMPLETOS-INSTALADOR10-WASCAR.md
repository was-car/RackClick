# RackClick 10 — manual autónomo de instalación desde cero

29.10.2026. Procedimiento **New**, desde Windows limpio hasta primer acceso, MFA y backup. Guarda este manual con el ZIP para usarlo sin Codex ni Claude. Los nombres, IP y sufijo del acceso del Escritorio serán los de tu nueva instalación.

Corresponde a `RackClick-Servidor-10.zip`, esquema 15, ensayado en Windows Server 2025. La edición 10 sigue siendo candidata de laboratorio: la recuperación portable MFA y la adopción productiva están pendientes. La VM C del ensayo ya está instalada; este manual es para una nueva instalación en Windows limpio.

## 00. Requisitos y punto de partida

- Windows Server 2025 x64 con experiencia de escritorio, iniciado y conectado a la red prevista, sin rol de controlador de dominio.
- Una cuenta Windows con permisos de administrador local para aceptar la elevación.
- Espacio para aplicación, PostgreSQL, datos y backups. El instalador comprueba al menos 2 GiB libres en C; reserva además espacio para tus datos y copias.
- La entrega 10 completa, guardada fuera de la VM para conservarla si reviertes un snapshot.

El paquete incluye runtime .NET 10.0.12, PostgreSQL 17.11 y Visual C++ 14.51.36247.0. Crea base, roles, cuenta Windows de servicio, contraseñas y almacén MFA. No necesitas preparar SDK, Node, Python o usuarios PostgreSQL manualmente.

Si utilizas VMware, crea tú un snapshot del Windows limpio antes de empezar. El sistema operativo debe estar instalado; este procedimiento no requiere que tu VM tenga el nombre de la del ensayo.

## 01. Guardar y copiar los archivos


Guarda la carpeta **servidor10** fuera del servidor o de la VM. En el PC del proyecto, la entrega está en:

`C:\RackClick_SVR\.local\entregas\servidor10`

Copia la carpeta **servidor10** al Escritorio **dentro de la VM limpia**. Si recibes `RackClick-Entrega10-Con-Manual.zip`, usa **Extraer todo** y elige el Escritorio como destino: el ZIP contiene esa carpeta `servidor10`. Abre `00-MANUAL-INSTALACION-10.html` para leer los pasos en el navegador; el TXT sirve para Bloc de notas.

Por ejemplo, si el usuario Windows es Wascar, el ZIP quedará en:

`C:\Users\Wascar\Desktop\servidor10\RackClick-Servidor-10.zip`

Si utilizas otro usuario Windows, su Escritorio tendrá otra ruta. Los comandos siguientes detectan ese Escritorio automáticamente.


## 02. Abrir PowerShell como administrador

1. Dentro del Windows Server pulsa **Windows+R**. En VMware haz antes clic dentro del escritorio de la VM; **Ctrl+G** captura su teclado si hace falta.
2. Escribe `powershell.exe`.
3. Mantén pulsadas **Ctrl+Mayús** y pulsa **Enter**.
4. Acepta **Sí / Ja**. La consola debe mostrar **Administrador / Administrator** en el título.
5. Para pegar un bloque, cópialo, haz clic en la consola y pulsa **Ctrl+V** o el botón derecho; después **Enter**. **Ctrl+Alt** libera teclado y ratón de VMware.

Comprueba que estás en el servidor deseado, no en el PC que sólo usará el navegador:

```powershell
$env:COMPUTERNAME
```

## 03. Consultar la IP y la red

Este bloque sólo consulta Windows; no cambia su dirección. Anota la IP y la Red de la tarjeta conectada a la red que utilizarán tus clientes.

```powershell
Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.AddressState -eq 'Preferred' -and
        $_.IPAddress -notlike '127.*' -and
        $_.IPAddress -notlike '169.254.*'
    } |
    ForEach-Object {
        $direccion = $_.IPAddress
        $prefijo = $_.PrefixLength
        $bytesRed = [Net.IPAddress]::Parse($direccion).GetAddressBytes()
        for ($i = 0; $i -lt 4; $i++) {
            $bits = [Math]::Min(8, [Math]::Max(0, $prefijo - $i * 8))
            $mascara = 256 - [int][Math]::Pow(2, 8 - $bits)
            $bytesRed[$i] = $bytesRed[$i] -band $mascara
        }
        [pscustomobject]@{
            Tarjeta = $_.InterfaceAlias
            IP = $direccion
            Red = ([Net.IPAddress]::new($bytesRed).ToString() + '/' + $prefijo)
        }
    }
```

Ejemplo del ensayo: IP `192.168.206.131`, red `192.168.206.0/24`. No copies esos valores a otra máquina: utiliza sus propios resultados. El instalador no cambia la IP de Windows. Para uso diario conserva una dirección estable en la red.

## 04. Verificar el ZIP

En la consola elevada del paso 02 pega este bloque completo:

```powershell
$ErrorActionPreference = 'Stop'

if ($env:COMPUTERNAME -eq 'LEAO') {
    throw 'Este bloque se ejecuta dentro de la VM limpia, no en LEAO.'
}

if (@(Get-Service -Name 'RackClick*' -ErrorAction SilentlyContinue).Count -gt 0) {
    throw 'Este Windows ya tiene un servicio RackClick. Utiliza su panel; no reinstales encima.'
}

$instancias = 'C:\ProgramData\RackClick\Instances'
if ((Test-Path -LiteralPath $instancias) -and
    @(Get-ChildItem -LiteralPath $instancias -Force).Count -gt 0) {
    throw 'Hay archivos de instalaciones anteriores. Conserva su estado y comunícalo.'
}

$zip = Join-Path ([Environment]::GetFolderPath('Desktop')) 'servidor10\RackClick-Servidor-10.zip'
$hashEsperado = '8c74b3b52d8b65f22473408ea9e23820898de9005628d6a0b14d3894cbd89e4c'

if ((Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash -ine $hashEsperado) {
    throw 'El ZIP no coincide con la edición 10 verificada. No ejecutar.'
}

'ZIP10 CORRECTO. Puedes seguir con la extraccion en esta consola.'
```

Debe aparecer **ZIP10 CORRECTO**. Una parada por servicio existente significa que ese equipo ya contiene RackClick: este procedimiento New se detiene para conservarlo.


## 05. Crear la carpeta y descomprimir

La carpeta de extracción será **C:\RackClick_Instalacion10**. Es la carpeta del instalador; el asistente crea después las carpetas de programa y datos.

Continúa en la misma consola, después del mensaje ZIP10 CORRECTO:

```powershell
$ErrorActionPreference = 'Stop'

if ($env:COMPUTERNAME -eq 'LEAO') {
    throw 'Este bloque se ejecuta dentro de la VM limpia, no en LEAO.'
}

if (@(Get-Service -Name 'RackClick*' -ErrorAction SilentlyContinue).Count -gt 0) {
    throw 'RackClick ya está instalado. No continuar con una instalación nueva.'
}

$zip = Join-Path ([Environment]::GetFolderPath('Desktop')) 'servidor10\RackClick-Servidor-10.zip'
$destino = 'C:\RackClick_Instalacion10'

if (Test-Path -LiteralPath $destino) {
    throw 'La carpeta ya existe. Conservala; si ya extrajiste correctamente esta edicion, utiliza su CMD.'
}

if ((Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash -ine
    '8c74b3b52d8b65f22473408ea9e23820898de9005628d6a0b14d3894cbd89e4c') {
    throw 'El ZIP cambió. No descomprimir.'
}

Expand-Archive -LiteralPath $zip -DestinationPath $destino
'Carpeta preparada: C:\RackClick_Instalacion10\RackClick-Servidor-10'
```

`Expand-Archive` crea la carpeta: no necesitas crearla previamente a mano.


## 06. Lanzar el asistente

En esa misma consola pega:

```powershell
$entrada = 'C:\RackClick_Instalacion10\RackClick-Servidor-10\00-LIMPIAR-Y-REINSTALAR.cmd'
& $entrada
```

Se abrirá el resumen del envoltorio. En la VM limpia revisa el destino y pulsa **Conservar anteriores e instalar**. Después aparece el formulario del instalador. El proceso no requiere cambiar globalmente la política de ejecución de PowerShell.


## 07. Rellenar el formulario
Los campos están en el centro del asistente. Usa la IP y la red obtenidas en 03, no una dirección de otra máquina.

| Campo | Valor que debes indicar |
|---|---|
| IP de escucha del servidor | La IP de la tarjeta de red elegida en 03 |
| Nombre DNS o IP para el navegador | Para este procedimiento, esa misma IP; un nombre DNS sólo si ya resuelve al servidor |
| Puerto HTTPS | `5443`, si está libre |
| Puerto PostgreSQL local | `55441`, si está libre; se usa dentro del servidor |
| Red autorizada | La red que muestra el comando de03 |
| Nombre de Systemhaus | El nombre que quieras mostrar en la aplicación |
| Administrador de RackClick | Tu primer usuario de aplicación, por ejemplo `Wascar` |
| Nombre del servicio Windows | `RackClick` |
| Cuenta Windows estándar del servicio | `RackClickSvc10`; el instalador la creará y debe estar libre |
| Modo | **New** |
| Carpeta del backup y SHA256 de su manifiesto | Vacíos para New |

Debajo de los campos, mantén marcada la autorización de confianza de la CA local **en este servidor**. Abajo a la izquierda pulsa **Revisar e instalar**, revisa el resumen y confirma.

El asistente crea la cuenta estándar de servicio y los roles PostgreSQL. Son distintos del administrador de aplicación y del usuario Windows con el que has abierto PowerShell. Las contraseñas se generan localmente; no debes escribirlas en estos campos.

## 08. Esperar, reiniciar y verificar

1. Espera sin volver a pulsar instalar. Si un paso falla, conserva el código y el informe del Escritorio.
2. Si Visual C++ solicita explícitamente reinicio con `setup_crt_restart_required`, guarda el informe, reinicia Windows y vuelve a abrir el CMD ya extraído del paso 06. No repitas la descompresión. Ese reinicio corresponde al prerrequisito anterior al alta de la instancia; un error genérico requiere consultar 13, no repetir intentos a ciegas.
3. Al completar HTTPS y backup, el asistente indicará que falta comprobar el reinicio: `awaiting_reboot`.
4. Reinicia Windows desde **Inicio → Encendido → Reiniciar**.
5. Cuando vuelva el Escritorio, abre el nuevo **RackClick-VERIFICAR-10-<8 caracteres>.cmd** creado por esa instalación. El sufijo se genera en cada instalación: no hay uno fijo que debas copiar del ensayo.
6. En la parte inferior pulsa **Verificar instalacion**. El resultado esperado es **postboot_verified**.
7. Continúa con **Acceso privado → Abrir RackClick**, como en 09.


Si al abrir el panel justo después del arranque aparece `postboot_https_health_failed`, espera uno o dos minutos y pulsa **Verificar instalacion** otra vez cuando el servicio esté listo. Esa comprobación no reinstala RackClick. Si el error persiste, conserva el informe.

El 100% del panel corresponde a la instalación técnica de ese servidor; no al porcentaje global de desarrollo del proyecto.

## 09. Obtener las credenciales y entrar

1. En el panel del acceso **RackClick-VERIFICAR-10-…cmd** pulsa **Acceso privado**.
2. Se abre un archivo local con `username` y `password`. Usa el administrador de aplicación que elegiste en 07 y el valor de `password`, sin las comillas.
3. Pulsa **Abrir RackClick**. El navegador abre la URL del propio panel, con la IP o nombre y puerto que configuraste.
4. Inicia sesión. El formato habitual será `https://IP_DEL_SERVIDOR:5443`.

La contraseña de aplicación es distinta de la contraseña Windows del operador. Consúltala localmente y guárdala en tu gestor de contraseñas; no la incluyas en informes ni capturas compartidas.

Para el uso diario abre esa misma URL en el navegador. El servicio inicia con Windows. No necesitas el acceso `.url` creado durante el ensayo: el botón del panel y tu URL funcionan en cada nueva instalación.

## 10. Configurar y probar MFA

1. Si lo necesitas, selecciona **Español** en el selector superior derecho de la página inicial y espera la confirmación del guardado.
2. En la barra lateral izquierda, cerca de tu nombre y antes de **Cerrar sesión**, pulsa **Mi seguridad**.
3. Pulsa **Activar MFA**.
4. En el formulario que aparece debajo escribe **Tu contraseña actual** de aplicación.
5. Marca **Entiendo el efecto sobre esta cuenta y sus sesiones** y pulsa **Confirmar cambio**.
6. Si vuelve al login, entra de nuevo. Si aparece **Iniciar sesión de nuevo**, pulsa ese botón.
7. Añade el QR o la clave manual a tu autenticador TOTP del teléfono. Conserva ese registro en el autenticador.
8. Escribe los seis dígitos actuales y pulsa **Confirmar autenticador e iniciar sesión**.
9. Vuelve a **Mi seguridad** y comprueba que el factor está activo.
10. Pulsa **Cerrar sesión** y entra otra vez. Debe pedir contraseña y código. Usa un código nuevo y pulsa **Verificar e iniciar sesión**.

Los usuarios ordinarios, técnicos y administradores de clientes tienen 45 días: nuevos desde creación y anteriores desde activación persistida de la política. El administrador global de Systemhaus está exento de la obligación automática y puede gestionar su propio factor. Administrar el MFA de otra cuenta exige permisos del servidor y una sesión que haya completado MFA.

Una instalación New crea el administrador inicial. Los usuarios adicionales se crean después en la administración web y reciben sus grupos y ámbitos; las cuentas sintéticas del ensayo no son usuarios predeterminados del instalador.

## 11. Acceder desde otro PC

El cliente necesita navegador, conectividad con el servidor y pertenecer a la red autorizada. No se instala allí RackClick, PostgreSQL, .NET ni herramientas de desarrollo. PostgreSQL permanece local; el acceso de los usuarios es por HTTPS.

La confianza marcada en 07 se aplica al servidor. Para esta CA local, otro PC debe confiar en el certificado público de esa instalación:

1. En el panel del servidor anota el UUID que aparece junto a **Instancia**.
2. En el servidor abre PowerShell como administrador y pega este bloque. Copia sólo el certificado público al Escritorio:

```powershell
$ErrorActionPreference = 'Stop'
$textoId = Read-Host 'UUID que muestra el panel en Instancia'
$id = [guid]::Empty
if (-not [guid]::TryParseExact($textoId, 'D', [ref]$id)) {
    throw 'UUID de instancia invalido.'
}
$ca = Join-Path ('C:\ProgramData\RackClick\Instances\' + $id.ToString('D')) 'management\RootCA.cer'
$copiaCa = Join-Path ([Environment]::GetFolderPath('Desktop')) 'RackClick-CA-Publica.cer'
if (Test-Path -LiteralPath $copiaCa) {
    throw 'Ya existe una copia con ese nombre. Conserva ese archivo antes de continuar.'
}
Copy-Item -LiteralPath $ca -Destination $copiaCa -ErrorAction Stop
Get-FileHash -LiteralPath $copiaCa -Algorithm SHA256
```

3. Anota el hash, copia `RackClick-CA-Publica.cer` al Escritorio del cliente y comprueba allí ese mismo archivo. No copies PFX ni claves privadas:

```powershell
Get-FileHash -LiteralPath (Join-Path ([Environment]::GetFolderPath('Desktop')) 'RackClick-CA-Publica.cer') -Algorithm SHA256
```

4. Después de comprobar que coincide, en PowerShell de administrador del **cliente** importa ese certificado público:

```powershell
$caPublica = Join-Path ([Environment]::GetFolderPath('Desktop')) 'RackClick-CA-Publica.cer'
Import-Certificate -FilePath $caPublica -CertStoreLocation 'Cert:\LocalMachine\Root'
```

5. Abre la URL que muestra el panel del servidor. Comprueba el acceso en cada cliente. Esta importación no se ejecutó en otro PC durante el ensayo descrito; sigue el procedimiento con el certificado de tu propia instalación.

## 12. Exportar un backup

1. Abre el panel **RackClick-VERIFICAR-10-…cmd**.
2. En la fila de botones, a la derecha, pulsa **Exportar backup**.
3. Elige una carpeta local NTFS o un soporte NTFS.
4. Espera **Backup exportado y verificado / export_complete**.
5. Conserva juntos `manifest.json`, `data.dump` y el SHA256 entregado. Guarda una copia fuera de la VM.

El panel exporta el último backup programado validado. Comprueba su fecha: no presupongas que incluye cambios posteriores. La programación diaria utiliza la hora local del servidor.

**Límite de esta edición:** el dump no contiene las claves MFA. Su sobre portable y la recuperación completa en otra máquina siguen pendientes de integración. Restore con factores se bloquea con `recovery_mfa_envelope_required`; un JSON de RC9 tampoco equivale a un dump PostgreSQL. Este manual cubre New y no presenta esas restauraciones como operativas ni la candidata como producto final adoptado.

## 13. Qué hacer ante una parada

| Resultado | Acción |
|---|---|
| ZIP ausente | Revisa Escritorio/servidor10 y el nombre exacto de la edición 10 |
| Hash distinto | Consigue la copia correcta; no cambies el hash esperado para aceptar otro archivo |
| Servicio o instancia existente | Conserva esa instalación y usa su panel, o instala New en el Windows limpio previsto |
| Carpeta de extracción existente | Conserva sus archivos. Si ya descomprimiste correctamente, abre el CMD del paso 06; no mezcles ediciones |
| Controlador de dominio rechazado | Utiliza otro Windows Server sin el rol AD DS |
| Puerto ocupado | En New elige un puerto libre en el formulario y anota la URL resultante |
| Reinicio explícito de Visual C++ | Sigue el paso 08 y vuelve a abrir el CMD existente sin descomprimir otra vez |
| Otro fallo de instalación | Conserva el ZIP de informe del Escritorio y el estado del intento; no borres cuentas, claves ni bases para forzar el paso |
| HTTPS todavía no listo al arrancar | Espera uno o dos minutos y pulsa Verificar instalacion; conserva el informe si persiste |
| Aviso de certificado desde otro PC | Comprueba URL, conectividad, fecha y confianza de CA según el paso 11 |
| Falta contraseña de aplicación | Abre Acceso privado; no utilices como sustituto tu contraseña Windows |
| Fallo de MFA | Conserva el mensaje. No borres mfa-keys ni sustituyas la clave que cifra factores existentes |

Si es un laboratorio desechable y decides volver al snapshot limpio, guarda antes informes y datos que quieras conservar fuera de la VM. Revertir elimina todos los cambios posteriores, incluidos el servidor y los archivos recién copiados; no equivale a restaurar la aplicación en otra máquina.

## 14. Registro de tu propia instalación

Copia esta tabla a un archivo propio antes de rellenarla para conservar tus resultados al actualizar el manual.

| Dato o prueba | Tu resultado |
|---|---|
| Fecha, nombre del servidor y versión Windows | |
| IP, red y URL final | |
| Systemhaus y usuario administrador, sin contraseña | |
| Hash del ZIP comprobado | Pass / Not Pass / No probado |
| Instalación y primer backup | Pass / Not Pass / No probado |
| Reinicio y postboot_verified | Pass / Not Pass / No probado |
| Login desde el servidor | Pass / Not Pass / No probado |
| MFA: enrolamiento y siguiente login | Pass / Not Pass / No probado |
| Acceso desde otro PC, si lo utilizas | Pass / Not Pass / No probado |
| Exportación de backup y fecha de la copia | |
| Observaciones y códigos, sin secretos | |

## Referencias

- Implementación y ensayo: `docs/INSTALADOR10-PERFIL.json` y `evidence/s1-20261029/installer10-vm-codex/RESULTADOS.md`.
- [Microsoft: Expand-Archive](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.archive/expand-archive?view=powershell-5.1).
- [Microsoft: Import-Certificate](https://learn.microsoft.com/en-us/powershell/module/pki/import-certificate?view=windowsserver2025-ps).
