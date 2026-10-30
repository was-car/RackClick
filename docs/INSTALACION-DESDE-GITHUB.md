# Instalar y probar desde GitHub privado

30.10.2026. Esta guía permite compilar las fuentes y abrir un laboratorio con los **10 clientes sintéticos originales**. Cada arranque crea una base independiente y contraseñas nuevas. No toca tu servidor instalado ni restaura cuentas o factores MFA ajenos.

## Elegir el recorrido

- **Probar las fuentes en este Windows:** seguir los pasos 1–7. Funciona en el navegador del mismo equipo, mientras la consola permanece abierta.
- **Instalar un servicio Windows con HTTPS para otros equipos:** usar la candidata nativa y su [manual completo de edición 10](PASOS-COMPLETOS-INSTALADOR10-WASCAR.md). Ese ZIP se conserva en la entrega privada local de Wascar; no está alojado en GitHub mientras se cierran sus condiciones de redistribución. Esta guía de fuentes no sustituye ese instalador.

No se anuncia una versión final adoptada. La demostración local desactiva explícitamente el proveedor MFA y usa HTTP sólo en `127.0.0.1`; no sirve para exponerla a una red. El código publicado sí incluye panel, enrolamiento, verificación y custodia MFA de la candidata 10.

## 1. Requisitos

- Windows x64; Windows Server 2025 con escritorio es el entorno nativo ensayado. El laboratorio necesita una sesión normal, **sin ejecutar como administrador**.
- [Git para Windows](https://git-scm.com/downloads/win) y acceso autorizado a `was-car/RackClick`.
- [Python 3.12 o posterior](https://www.python.org/downloads/windows/), con el lanzador `py`. No instalar paquetes Python: el auxiliar usa la biblioteca estándar.
- Acceso HTTPS a los proveedores oficiales, NuGet y npm durante la preparación.
- Redistribuible [Visual C++ x64 oficial de Microsoft](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170) para los binarios Windows de PostgreSQL. La candidata nativa se ensayó con 14.51.36247.0; la revisión general de redistribución sigue abierta. Instálalo desde Microsoft, acepta su licencia y reinicia si lo pide. El repositorio no transporta ese ejecutable.
- Espacio para SDK, PostgreSQL, Node, paquetes y un clúster nuevo en cada ejecución. No se precisa una base PostgreSQL ni usuarios Windows preexistentes.

Versiones fijadas: SDK **10.0.401**, runtime **10.0.12**, PostgreSQL **17.11**, Node **24.21.0**, npm **11.19.0**, esbuild **0.25.10**, Npgsql **10.0.3**, Otp.NET **1.4.1**, esquema **15**. Los JSON y locks del repositorio son la referencia. No editar `global.json` para hacerlo coincidir con otro SDK instalado.

## 2. Abrir PowerShell y descargar

Pulsa **Inicio**, escribe **Windows PowerShell** y abre la aplicación con un clic normal. No selecciones «Ejecutar como administrador» para este laboratorio.

Elige una carpeta nueva, por ejemplo `C:\Trabajo\RackClick`. En PowerShell:

```powershell
New-Item -ItemType Directory -Path 'C:\Trabajo' -Force | Out-Null
Set-Location -LiteralPath 'C:\Trabajo'
git clone https://github.com/was-car/RackClick.git RackClick
if ($LASTEXITCODE -ne 0) { throw 'La descarga no termino correctamente.' }
Set-Location -LiteralPath 'C:\Trabajo\RackClick'
py -3 --version
```

Si Git solicita acceso, inicia sesión en GitHub con una cuenta autorizada. No pongas tokens en la URL ni en archivos del proyecto. Si `RackClick` ya existe, elige otro nombre y ajusta los pasos; no borres la carpeta existente.

## 3. Preparar herramientas oficiales

En esa misma PowerShell, dentro de `C:\Trabajo\RackClick`:

```powershell
& .\tools\windows\Initialize-Toolchain.ps1 -Component @('dotnet','postgresql','node')
```

Si la política local impide cargar el script, usa sólo en esta consola:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
& .\tools\windows\Initialize-Toolchain.ps1 -Component @('dotnet','postgresql','node')
```

El script descarga las versiones fijadas de los proveedores oficiales, comprueba hashes y extrae en `.local`. No crea bases, servicios ni reglas de cortafuegos. Si detecta una carpeta parcial o un hash distinto, se detiene: conserva el diagnóstico y no cambies los pins para evitar el error.

## 4. Compilar

```powershell
py -3 -B .\tools\start_demo.py --build-only
if ($LASTEXITCODE -ne 0) { throw 'La compilacion no termino correctamente.' }
```

Se restauran dependencias con locks, se publica el servidor sin apphost, se compila el cargador y se construye el frontend RC9 con npm ci. El ZIP RC9 de `reference/` es una entrada de fuentes, no el instalador del servidor. Los registros y binlogs quedan privados en `.local\source-demo\logs`; no los subas a GitHub ni los envíes completos sin revisarlos.

El mensaje final debe decir **«Compilacion lista»**. El auxiliar conserva hashes de las salidas y rechaza arrancar si cambian después.

## 5. Comprobación automática breve

```powershell
py -3 -B .\tools\start_demo.py --smoke
if ($LASTEXITCODE -ne 0) { throw 'La comprobacion no paso.' }
```

El resultado debe indicar `success: true`, `customers: 10`, `ports: 5408`, `frontend: served` y `mfaEnabled: false`. La prueba crea su propio laboratorio, inicia sesión, comprueba los datos y detiene sus procesos. Los archivos quedan conservados bajo `.local\labs`.

## 6. Abrir la interfaz con todos los ejemplos

```powershell
py -3 -B .\tools\start_demo.py
```

Espera al resultado correcto. La consola muestra una dirección como `http://127.0.0.1:puerto` y la ruta de **ACCESO-PRIVADO.json**. Abre el archivo de esa ejecución con el Explorador y el Bloc de notas: contiene la dirección, el usuario `demo-admin` y su contraseña aleatoria. No publiques ni copies su contenido en tickets.

Abre la dirección indicada en Edge o Chrome del mismo Windows. Inicia sesión y entra en **Clientes**: deben aparecer los 10 clientes. Selecciona uno y recorre sitios, edificios, salas y racks. Cambia una nota sintética, guarda, recarga y comprueba que se conserva durante esta ejecución. Los permisos se siguen comprobando en el servidor.

Contenido original: 10 clientes, 15 sitios, 25 edificios, 68 salas, 68 racks, 311 equipos, 633 grupos de puertos, 5408 puertos, 623 conexiones y 1246 extremos. Es un inventario de prueba; **no es un dump PostgreSQL ni un full backup de seguridad**.

## 7. Terminar y recuperar el trabajo

Vuelve a PowerShell y pulsa **Ctrl+C** una vez. Espera el mensaje de procesos detenidos. Sólo se detienen el servidor y PostgreSQL creados por esta ejecución. No se borran sus archivos ni otras bases.

Cada nueva ejecución crea **otro laboratorio desde el ejemplo original**. Este auxiliar no ofrece reapertura de una base anterior ni exportación de sus cambios: conserva sus archivos para inspección. Para QA duradero, servicio automático, HTTPS, backup/restore y MFA real usa el recorrido nativo de edición 10. No confundir el ejemplo JSON con una copia de recuperación.

## MFA: alcance real

El panel y login MFA de la candidata 10 se probaron en Windows y Wascar confirmó su cuenta administrativa. Se mantiene la política confirmada: 45 días de gracia para cuentas ordinarias y exención del administrador global; no se sustituyen ámbitos por nombres de rol. Quedan recuperación portable, códigos/emergencia, rotación y aceptación completa.

La activación real exige un almacén nuevo fuera de PostgreSQL, con clave protegida DPAPI, ACL e identidad del servicio correctas. Las claves y sus sobres no se incluyen en este repositorio. No actives MFA copiando configuraciones de otro equipo ni mediante el auxiliar demo. El manual nativo identifica las comprobaciones de cuenta, arranque y custodia.

## Problemas frecuentes

| Resultado | Acción |
|---|---|
| Git muestra 404 o pide acceso | Verificar la cuenta autorizada: el repositorio es privado. |
| Falta `py` | Instalar Python oficial con lanzador; reabrir la consola. |
| SDK no encontrado | Ejecutar el paso 3 desde este clon; mantener `global.json`. |
| Error al arrancar PostgreSQL | Revisar requisito Visual C++, reinicio y el log privado del laboratorio. No usar otra base para salir del paso. |
| Compilación o hash de salida inválido | Leer el log privado y repetir el paso 4 tras corregir la causa. |
| Dirección deja de responder | La consola debe seguir abierta; el puerto cambia con cada ejecución. |
| Se necesita probar desde otro PC | Usar el instalador nativo con HTTPS; no abrir el puerto de esta demo. |

Registrar código, comando y resultado observado. No declarar Pass sólo porque compiló. El comando heredado `npm run test:build` aún apunta a un archivo ausente; no forma parte de este recorrido verificado. Los tests unitarios de adaptadores se ejecutan desde `Build-Frontend.ps1`.
