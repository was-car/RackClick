# RackClick20 · instalación y datos desde el navegador

12.11.2026 · candidata de pruebas, esquema48. [English](#english) · [Deutsch](#deutsch).

## Español

Requisitos: Windows Server2025 x64 con Escritorio, conexión a Internet, sin controlador de dominio y acceso de administrador de Windows. Para probar desde cero, usar una máquina limpia; conservar las instalaciones anteriores. GitHub no requiere iniciar sesión para descargar esta Release pública. Cada instalación genera sus propias cuentas, contraseñas, certificados y claves.

1. En Inicio, escribir **Windows PowerShell**, pulsar con botón derecho y elegir **Ejecutar como administrador**.
2. Crear **C:\RackClick_Prueba20**. Descargar **RackClick-Windows-Online-20.zip** y su SHA256 de la Release **windows-online20-schema48-admin-data**. Usar una carpeta nueva; no sobrescribir una instalación.
3. Comprobar el ZIP antes de extraer:

```powershell
Get-FileHash -LiteralPath 'C:\RackClick_Prueba20\RackClick-Windows-Online-20.zip' -Algorithm SHA256
```

SHA256 publicado: `2644dc115ed03086a5a1d60b5e6418989350ebaf08942e8c07d81a5bdda813fb`.

**Alternativa: descargar, comprobar y abrir desde PowerShell.** Este bloque realiza los pasos 2 a 4; no requiere cuenta de GitHub. Pégalo en la PowerShell de administrador del servidor limpio. Si la carpeta ya existe, se detiene para conservarla.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $ProgressPreference = 'SilentlyContinue'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $carpetaRackClick = 'C:\RackClick_Prueba20'
    if (Test-Path -LiteralPath $carpetaRackClick) {
        throw 'La carpeta ya existe. Consérvala y usa otra carpeta nueva.'
    }
    New-Item -ItemType Directory -Path $carpetaRackClick | Out-Null
    $urlRackClick = 'https://github.com/was-car/RackClick/releases/download/windows-online20-schema48-admin-data/RackClick-Windows-Online-20.zip'
    $zipRackClick = Join-Path $carpetaRackClick 'RackClick-Windows-Online-20.zip'
    Invoke-WebRequest -UseBasicParsing -Uri $urlRackClick -OutFile $zipRackClick
    $hashRackClick = '2644dc115ed03086a5a1d60b5e6418989350ebaf08942e8c07d81a5bdda813fb'
    if ((Get-FileHash -LiteralPath $zipRackClick -Algorithm SHA256).Hash -ine $hashRackClick) {
        throw 'El ZIP no coincide. No extraer ni ejecutar.'
    }
    $extraidoRackClick = Join-Path $carpetaRackClick 'Extraido'
    Expand-Archive -LiteralPath $zipRackClick -DestinationPath $extraidoRackClick
    Start-Process -FilePath (Join-Path $extraidoRackClick 'RackClick-Windows-Online-20\INICIAR-RACKCLICK.cmd')
}
```

Cuando se abra el asistente, continuar desde el paso 5. Si usaste este bloque, no vuelvas a ejecutar el paso 4.

4. Si coincide, extraer:

```powershell
Expand-Archive -LiteralPath 'C:\RackClick_Prueba20\RackClick-Windows-Online-20.zip' -DestinationPath 'C:\RackClick_Prueba20\Extraido'
Start-Process -FilePath 'C:\RackClick_Prueba20\Extraido\RackClick-Windows-Online-20\INICIAR-RACKCLICK.cmd'
```

5. Revisar las condiciones de proveedores y confirmar **ADQUIRIR**. Se descargan y verifican las dependencias oficiales; el usuario no compila ni instala herramientas de desarrollo manualmente.
6. Elegir **Conservar anteriores e instalar → New**. Introducir la IP/subred reales del servidor. Puertos previstos: HTTPS5443 y PostgreSQL local55441. Elegir nombre de empresa y administrador propios, por ejemplo **Demo IT Services** y **DemoAdmin**. La cuenta Windows estándar del servicio es distinta de ese administrador de la aplicación. Autorizar la confianza local de la CA para comprobar HTTPS.
7. Esperar la comprobación de servicio, HTTPS y copia inicial. **Acceso privado** permite consultar las credenciales nuevas localmente; **Abrir RackClick** abre el navegador. Nunca copiar cuentas o MFA de otra instalación.
8. En RackClick, entrar con el administrador global y abrir **Administración → Datos y copias de inventario**. El panel incluye tres recorridos:
   - **Cargar los50clientes de ejemplo**: comprobar el resumen, confirmar y esperar el resultado del servidor. Sólo funciona con inventario vacío. No repetir ante respuesta incierta: usar la consulta de la solicitud original.
   - **Crear copia de inventario**: confirmar la operación, esperar el recibo y descargar el JSON verificado. Contiene clientes y sus sitios, edificios, salas, racks, equipos, grupos, puertos y conexiones. Las notas y metadatos escritos también se incluyen.
   - **Restaurar inventario**: seleccionar ese JSON en otra instalación vacía, revisar la vista previa y confirmar. Se conservan las identidades y conexiones del inventario; la cuenta y MFA del destino permanecen. La operación se confirma después del commit completo.
9. La demostración debe mostrar50clientes con nombres17EN/17DE/16ES;66sitios,88edificios,226salas,180racks,1563equipos,2869grupos,20665puertos y2207conexiones. Cambiar el idioma no traduce nombres propios. No ejecutar además el cargador CMD sobre esos datos.
10. Reiniciar Windows manualmente, sin revertir el snapshot. Al volver, abrir **RackClick-VERIFICAR-20-… → Verificar instalacion** desde el Escritorio; comprobar **postboot_verified**, el acceso web y los datos. Si el verificador automático temprano falla, conservar ese resultado y contrastarlo con el oficial manual; no interpretarlo como éxito automático.

**Qué protege esta copia:** inventario de todos los clientes. **Qué no incluye:** cuentas, contraseñas, grupos/permisos, MFA, claves, preferencias, plantillas privadas/compartidas, auditoría completa o configuración Windows. El backup PostgreSQL y su material de recuperación tienen otro procedimiento. Restore48 completo y cambio automático de red48 permanecen bloqueados; este botón no los sustituye ni los habilita.

Si una operación termina sin confirmación, mantener la solicitud original y consultar su resultado. Un resultado no registrado no demuestra por sí solo cancelación. No vaciar el inventario ni volver a cargarlo para eludir el control.

## English

Use a fresh Windows Server2025 x64 with Desktop Experience, Internet access and Windows administrator privileges, not a domain controller. Download the public **RackClick-Windows-Online-20.zip** and its externalSHA256 from the Release; no GitHub login is needed. Create **C:\RackClick_Prueba20**, open PowerShell as administrator, verify the hash and extract into a new folder using the commands above. Run **INICIAR-RACKCLICK.cmd**, review provider terms, confirm **ADQUIRIR**, then choose **Conservar anteriores e instalar → New**. Enter your own server address/subnet, organization and application administrator. Fresh credentials are available locally through **Acceso privado**.

In the browser open **Administration → Data and inventory copies**. Load50sample customers only into empty inventory; confirm and wait for the committed result. Create/download an inventory backup, or select thatJSON for preview and restoration into another empty installation. Customer/objectUUIDs, mounting, ports and connections are preserved; destination accounts and MFA remain. On uncertain responses query the original request instead of submitting another import.

The expected demonstration has50customers/180racks/1563devices/20665ports/2207connections,17English/17German/16Spanish company names. Do not run the externalCMD loader again. Restart Windows manually and use the desktop **RackClick-VERIFICAR-20 → Verificar instalacion**, requiring **postboot_verified** and persistent data.

Inventory files exclude authentication, permissions, MFA keys, preferences, private/shared templates and Windows configuration. They are not PostgreSQL or complete-server recovery. FullRestore48/network48 remain disabled. This delivery is a test candidate; native acceptance requires the new installation trial.

## Deutsch

Neuen Windows Server2025 x64 mit Desktopdarstellung, Internet und Windows-Administratorrechten verwenden; keinen Domänencontroller. Öffentliche **RackClick-Windows-Online-20.zip** und externeSHA256 aus dem Release herunterladen; keineGitHubAnmeldung erforderlich. **C:\RackClick_Prueba20** anlegen, PowerShell als Administrator öffnen, Hash prüfen und mit den obigen Befehlen in einen neuen Ordner entpacken. **INICIAR-RACKCLICK.cmd** starten, Anbieterbedingungen prüfen, **ADQUIRIR** bestätigen und **Conservar anteriores e instalar → New** wählen. EigeneIP/Subnetz, Organisation und Anwendungsadministrator eingeben. NeueZugangsdaten lokal über **Acceso privado** abrufen.

Im Browser **Administration → Daten und Inventarkopien** öffnen.50Beispielkunden nur in ein leeres Inventar laden, bestätigen und auf den abgeschlossenenServervorgang warten. Inventarsicherung erstellen/herunterladen oder dieseJSONDatei zur Vorschau und Wiederherstellung in einer anderen leeren Installation auswählen. Kunden-/ObjektUUIDs, Montage, Ports und Verbindungen bleiben erhalten; Konten undMFA am Ziel bleiben unverändert. Bei unklarerAntwort den ursprünglichenAuftrag abfragen, keine zweiteImportanforderung senden.

Erwartet:50Kunden/180Racks/1563Geräte/20665Ports/2207Verbindungen,17englische/17deutsche/16spanischeFirmennamen. DenexternenCMDLader nicht erneut verwenden. Windows manuell neu starten; Desktopzugang **RackClick-VERIFICAR-20 → Verificar instalacion**, Ergebnis **postboot_verified** und Datenbestand prüfen.

Inventarsicherungen enthalten keineAnmeldung, Berechtigungen, MFA-Schlüssel, Einstellungen, privaten/geteiltenVorlagen oderWindowskonfiguration. Sie ersetzen keinePostgreSQL-/Serverwiederherstellung. FullRestore48/Netzänderung48 bleiben gesperrt. Testkandidat; nativeAbnahme erst nach dem neuenInstallationstest.
