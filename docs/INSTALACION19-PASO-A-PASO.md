# Instalar RackClick Online19 desde cero

**[Español](#español) · [English](#english) · [Deutsch](#deutsch)**

Descarga de pruebas: [Release Windows Online19](https://github.com/was-car/RackClick/releases/tag/windows-online19-schema48), en el repositorio privado. Incluye la aplicación48 y el cargador opcional de los 50 clientes. Necesitas acceso autorizado a GitHub.

## Español

1. Prepara un **Windows Server 2025 x64 con Escritorio**, nuevo y sin el rol de controlador de dominio. Usa una cuenta administradora de Windows. Conserva tú mismo un snapshot si es una VM.
2. Comprueba Internet dentro de Windows. En VMware, una red sólo de anfitrión sin puerta de enlace no permite descargar; utiliza una conexión con salida a Internet. No necesitas instalar manualmente PostgreSQL, .NET, SDK, Node ni Python.
3. Descarga de la Release **RackClick-Windows-Online-19.zip**, su archivo **.sha256** y esta guía. Revisa también las [condiciones de .NET para Windows](https://dotnet.microsoft.com/en-us/dotnet_library_license.htm) y los enlaces de proveedores del HTML incluido.
4. En el Explorador crea **C:\RackClick_Instalar19**. Copia allí el ZIP. Si ya existe una preparación o instalación, conserva todo y usa otra carpeta nueva; no borres bases ni cuentas para repetir.
5. Abre **Inicio**, escribe **Windows PowerShell**, pulsa con el botón derecho y elige **Ejecutar como administrador**. Acepta la elevación de Windows.
6. Ejecuta esta comprobación y compara el resultado completo con el archivo externo de la Release:

   ```powershell
   Get-FileHash -Algorithm SHA256 -LiteralPath 'C:\RackClick_Instalar19\RackClick-Windows-Online-19.zip'
   ```

   SHA256 de esta entrega: `4d9dccbe75cc6a1900204699459fa0653cfaa4722626f9b48484e9259aacd6bf`. Si difiere, no extraigas ni ejecutes el archivo.

7. Extrae a una carpeta nueva:

   ```powershell
   Expand-Archive -LiteralPath 'C:\RackClick_Instalar19\RackClick-Windows-Online-19.zip' -DestinationPath 'C:\RackClick_Instalar19\Extraido19'
   ```

8. En el Explorador abre **Extraido19 → RackClick-Windows-Online-19**. Abre **00-LEEME.html**. Después pulsa con el botón derecho en **INICIAR-RACKCLICK.cmd → Ejecutar como administrador**.
9. El lanzador explica las descargas oficiales. Escribe **ADQUIRIR** cuando lo solicite. Descarga aproximadamente700MB, comprueba tamaños y hashes y prepara el instalador. Python es temporal; no se compila RackClick ni se añaden herramientas globales a Windows. Ante un fallo, conserva su código e informe; no cambies versiones ni repitas una instalación parcial.
10. Aparece **RackClick 19 - Preparar instalacion en servidor de aplicaciones**. En un servidor vacío debe indicar que no existen **C:\ProgramData\RackClick** ni **C:\Program Files\RackClick**. Pulsa **Conservar anteriores e instalar**. Ese botón es la confirmación; no exige escribir otra frase. Si está deshabilitado o aparecen bloqueadores, detente y conserva el informe. No es una orden de borrar datos.
11. En el asistente selecciona **New**. Revisa todos los campos: IP de escucha, nombre/IP del navegador, HTTPS5443, PostgreSQL55441, subred autorizada, nombre del Systemhaus, administrador de RackClick, nombre del servicio y cuenta Windows estándar. Usa la IP real del servidor; **no copies la IP particular de nuestra VM**. El instalador no cambia IP o DNS de Windows.
12. Mantén la autorización de confianza de la CA local en este servidor y pulsa **Revisar e instalar**. Se crean cuentas, contraseñas, claves y certificados nuevos. El servicio usa una cuenta estándar y PostgreSQL permanece local.
13. Espera el resultado de preparación: HTTPS y backups comprobados, con reinicio pendiente. Si Windows solicita reiniciar por Visual C++, sigue esa indicación y conserva la preparación; no cambies permisos ni instales otro redistribuible a ciegas. Si hay otro fallo, conserva el informe y no reinstales sobre datos parciales.
14. En el panel instalado pulsa **Acceso privado** para consultar localmente el usuario y contraseña nuevos. No compartas contraseñas ni códigos MFA por el chat. **Abrir RackClick** abre la URL HTTPS de tu servidor. No se reutilizan las credenciales de W02-A.
15. Para reproducir nuestra demostración completa, abre desde el paquete extraído **CARGAR-50-CLIENTES → CARGAR-50-CLIENTES.cmd**. Introduce la URL HTTPS del servidor nuevo, su administrador global y contraseña en privado; TOTP si ya activaste MFA. Sobre el servidor vacío confirma **CARGAR 50 CLIENTES SINTETICOS**, una sola vez. Espera **demo50_loaded_verified**. Si falla o el resultado es incierto, conserva los datos parciales y no repitas la carga.
16. Comprueba los 50 clientes:17 nombres ingleses,17 alemanes y16 españoles. Son datos ficticios. Los nombres propios se conservan al cambiar el idioma. Resultado esperado:66 sitios,88 edificios,226 salas,180 racks,1563 equipos,2869 grupos,20665 puertos y2207 conexiones. La carga utiliza2553 comandos y no importa usuarios ni factores MFA.
17. Genera otra copia desde el panel administrativo después de cargar los datos. Conserva el resultado. El técnico también puede ejecutar la tarea oficial de backup y comprobar su recibo; no es un snapshot de VMware.
18. Reinicia **Windows** desde Inicio → Encendido → Reiniciar, sin revertir snapshots. Al volver, abre el acceso **RackClick-VERIFICAR-19-…** del Escritorio y pulsa **Verificar instalacion**. El resultado esperado es **postboot_verified**. Comprueba la web y los 50 clientes.
19. **Observación de esta candidata:** la comprobación automática temprana puede registrar **postboot_https_health_failed** antes de que la aplicación esté disponible. En B, el servicio arrancó solo y el comprobador oficial manual posterior pasó; los 50 clientes persistieron. Conserva ambos resultados. Si el comprobador manual también falla, no declares la instalación verificada.
20. Ya puedes usar la instalación de pruebas. Configura tu autenticador desde **Tu cuenta** si lo deseas. Rige la gracia de45 días y la exención del administrador global; nadie copia tu factor. Para acceso desde otros equipos, importa únicamente la CA pública según el manual de confianza, nunca una clave privada. Restore48 y cambio automático de red48 siguen deshabilitados; la adopción productiva final sigue pendiente.

La prueba de B ejecutó preparación y broker oficial de forma automatizada. El resumen del paso10 se documentó por inspección del código nativo; no se afirma una prueba de todos los clics de esa GUI.

## English

Use a fresh **Windows Server 2025 x64 with Desktop Experience**, administrator access and Internet; domain controllers are excluded. Download the ZIP, its externalSHA256 and this guide from the private [Release](https://github.com/was-car/RackClick/releases/tag/windows-online19-schema48). Create **C:\RackClick_Instalar19**, open **Start → Windows PowerShell → Run as administrator**, verify with `Get-FileHash` and extract with `Expand-Archive` using the commands above.

Open **Extraido19 → RackClick-Windows-Online-19 → 00-LEEME.html**, then run **INICIAR-RACKCLICK.cmd** as administrator. Review provider terms, including the [Windows .NET Library agreement](https://dotnet.microsoft.com/en-us/dotnet_library_license.htm), and confirm **ADQUIRIR**. Exact dependencies download directly from official providers. No compilation or manualSDK/Node/Python installation is required.

In **RackClick 19 - Preparar instalacion en servidor de aplicaciones**, check the empty-server summary and choose **Conservar anteriores e instalar**. This button is the confirmation; no extra phrase is required. If blocked, preserve the report. Select **New**, review your own address/subnet, ports5443/55441, Systemhaus, administrator, service and standard Windows account, then **Revisar e instalar**. Windows networking is not changed. Fresh credentials appear locally under **Acceso privado**.

To reproduce W02-A's full inventory, run **CARGAR-50-CLIENTES\CARGAR-50-CLIENTES.cmd** once on the empty server. Enter its newHTTPSURL, global administrator and private credentials/TOTP; confirm **CARGAR 50 CLIENTES SINTETICOS**. Require **demo50_loaded_verified**. Expect50customers/180racks/1563devices/20665ports/2207connections, with17English/17German/16Spanish company names. Authentication data is not imported. On rejection or uncertainty do not retry.

Create a backup, restart Windows manually and use the desktop **RackClick-VERIFICAR-19-… → Verificar instalacion**. Require **postboot_verified** and check persistent data. **Known observation:** the early automatic checker reported HTTPSfailure in B, while automatic service startup, the later official manual verifier and all50customers passed. Preserve both outcomes. Restore48/network48 and final production acceptance remain pending. MFA is available with the45-day policy/global-admin exemption; enrol your own authenticator.

## Deutsch

Neuer **Windows Server 2025 x64 mit Desktopdarstellung**, Administratorkonto und Internetzugang; keinDomänencontroller. ZIP, externeSHA256 und Anleitung aus dem privaten [Release](https://github.com/was-car/RackClick/releases/tag/windows-online19-schema48) herunterladen. **C:\RackClick_Instalar19** erstellen; **Start → Windows PowerShell → Als Administrator ausführen**. Mit den obigen Befehlen `Get-FileHash` prüfen und mit `Expand-Archive` entpacken.

**Extraido19 → RackClick-Windows-Online-19 → 00-LEEME.html** öffnen, anschließend **INICIAR-RACKCLICK.cmd** als Administrator starten. Anbieterbedingungen einschließlich [Windows .NET Library](https://dotnet.microsoft.com/en-us/dotnet_library_license.htm) prüfen und **ADQUIRIR** bestätigen. Abhängigkeiten kommen mit festen Hashes direkt von Anbietern; keineKompilierung odermanuelleSDK/Node/PythonInstallation.

Im Fenster **RackClick 19 - Preparar instalacion en servidor de aplicaciones** die Zusammenfassung des leeren Servers prüfen und **Conservar anteriores e instalar** wählen. DieserButton bestätigt; es gibt keine zusätzliche Texteingabe. BeiBlockierern denBericht aufbewahren. **New** wählen, eigeneIP/Subnetz, Ports5443/55441, Systemhaus, Administrator, Dienst undStandardkonto prüfen; **Revisar e instalar**. WindowsIP/DNS werden nicht geändert. Neue Zugangsdaten lokal über **Acceso privado** lesen.

Für das vollständige Inventar einmal **CARGAR-50-CLIENTES\CARGAR-50-CLIENTES.cmd** auf dem leeren Server starten. NeueHTTPSURL, globalenAdministrator undvertraulicheZugangsdaten/ggf.TOTP eingeben; **CARGAR 50 CLIENTES SINTETICOS** bestätigen. **demo50_loaded_verified** erwarten:50Kunden,180Racks,1563Geräte,20665Ports,2207Verbindungen.17englische/17deutsche/16spanischeFirmennamen bleiben unverändert. KeineBenutzer oderMFA-Faktoren werden übernommen. BeiFehler oderUnklarheit nicht erneut ausführen.

DanachSicherung erstellen, Windows manuell neu starten und Desktopzugang **RackClick-VERIFICAR-19-… → Verificar instalacion** öffnen. **postboot_verified** sowie persistenteDaten prüfen. **BekannteBeobachtung:** diefrüheautomatischePrüfung meldete inB einenHTTPSFehler; derDienst starteteautomatisch, diemanuelleoffiziellePrüfung undalle50Kunden bestanden. BeideErgebnisse aufbewahren. Restore48/Netzänderung48 undProduktionsabnahme bleiben offen. MFA mit45TagenFrist/AusnahmefürglobaleAdministratoren ist verfügbar; eigenenAuthenticator registrieren.
