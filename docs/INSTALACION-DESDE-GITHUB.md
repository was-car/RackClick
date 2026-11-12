# Compilar y probar RackClick desde GitHub

**[English](GETTING-STARTED.en.md) · [Deutsch](GETTING-STARTED.de.md) · [Español](INSTALACION-DESDE-GITHUB.md)**

Actualizado el 12 de noviembre de 2026 · esquema de fuentes **48**.

Este recorrido crea un **laboratorio local de desarrollo nuevo**, con el inventario sintético original de diez clientes. No modifica un servidor RackClick instalado. Cada arranque crea otra base y credenciales aleatorias; los laboratorios anteriores se conservan en disco. No reabre ni exporta cambios de un laboratorio anterior.

La demo usa **HTTP sólo en loopback** y desactiva explícitamente el proveedor MFA. No la expongas a la red. Instalación como servicio Windows, HTTPS, backups programados y MFA real son otro recorrido. Para un servidor nativo utiliza la [Release Windows Online20](https://github.com/was-car/RackClick/releases/tag/windows-online20-schema48-admin-data) y su [manual completo](INSTALACION20-PASO-A-PASO.md). Adquiere dependencias oficiales con pins e incluye el cargador opcional Demo50. Este recorrido desde fuentes continúa siendo un laboratorio local; Restore48 permanece deshabilitado.

## 1. Requisitos

- Windows x64 y una sesión normal, **sin PowerShell elevada como administrador**.
- [Git para Windows](https://git-scm.com/downloads/win), acceso HTTPS a `was-car/RackClick` y [Python 3.12 o posterior](https://www.python.org/downloads/windows/) con lanzador `py`. No se necesitan paquetes Python.
- Acceso HTTPS a los proveedores oficiales, NuGet y npm; espacio para herramientas, paquetes y un clúster PostgreSQL nuevo por ejecución.
- Redistribuible [Visual C++ x64 oficial de Microsoft](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170), necesario para los binarios PostgreSQL de Windows. Instálalo desde Microsoft bajo su licencia y reinicia si lo solicita. El entorno nativo se ensayó con 14.51.36247.0; ese ejecutable no se incluye aquí.
- No se necesita una base PostgreSQL ni una cuenta de servicio Windows preexistentes.

Versiones fijadas: **SDK .NET 10.0.401**, runtime **10.0.12**, **PostgreSQL 17.11**, **Node 24.21.0**, **npm 11.19.0**, **esbuild 0.25.10**, **Npgsql 10.0.3** y **Otp.NET 1.4.1**. Los locks del repositorio son la referencia. No edites `global.json` para ajustarlo a otro SDK instalado.

## 2. Abrir PowerShell y descargar

Abre Inicio, escribe **Windows PowerShell** y ábrela con un clic normal. Elige una carpeta nueva; este ejemplo usa `C:\Work\RackClick`:

```powershell
New-Item -ItemType Directory -Path 'C:\Work' -Force | Out-Null
Set-Location -LiteralPath 'C:\Work'
git clone https://github.com/was-car/RackClick.git RackClick
if ($LASTEXITCODE -ne 0) { throw 'La descarga fallo.' }
Set-Location -LiteralPath 'C:\Work\RackClick'
py -3 --version
```

La descarga del repositorio público no requiere iniciar sesión en GitHub. No escribas tokens en la URL ni en archivos del proyecto. Si la carpeta ya existe, elige otro nombre y ajusta los comandos; no la borres.

## 3. Preparar herramientas oficiales

En la misma consola, desde la raíz del repositorio:

```powershell
& .\tools\windows\Initialize-Toolchain.ps1 -Component @('dotnet','postgresql','node')
```

Si la política de ejecución bloquea el script, aplica lo siguiente **sólo a esta consola** y repite el comando:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

El auxiliar descarga archivos oficiales fijados, comprueba sus hashes y extrae en `.local`. No crea bases, servicios ni reglas de cortafuegos. Una carpeta parcial o un hash distinto es motivo para detenerse y conservar el diagnóstico, sin cambiar pins.

## 4. Compilar

```powershell
py -3 -B .\tools\start_demo.py --build-only
if ($LASTEXITCODE -ne 0) { throw 'La compilacion fallo.' }
```

Se restauran dependencias con locks, se publica el servidor sin apphost, se compila el cargador de inventario y se construye el frontend RC9 con `npm ci`. El ZIP de `reference/` es la referencia offline adoptada para compilar, no un instalador Windows. Los registros y binlogs quedan privados en `.local\source-demo\logs`; no los subas sin revisión.

Espera **«Compilacion lista»**. Se registran hashes de las salidas; cambiar o añadir archivos de salida hace fallar la validación al arrancar.

## 5. Comprobación automática breve

```powershell
py -3 -B .\tools\start_demo.py --smoke
if ($LASTEXITCODE -ne 0) { throw 'La comprobacion fallo.' }
```

Debe indicar `success: true`, `customers: 10`, `ports: 5408`, `frontend: served` y `mfaEnabled: false`. Crea su propio laboratorio, inicia sesión, comprueba datos y detiene sus procesos. Los archivos quedan bajo `.local\labs`.

## 6. Abrir la interfaz

```powershell
py -3 -B .\tools\start_demo.py
```

La consola muestra una URL como `http://127.0.0.1:puerto` y la ruta de **ACCESO-PRIVADO.json**. Abre localmente en Bloc de notas el archivo de esa ejecución: contiene la URL, el usuario `demo-admin` y su contraseña aleatoria. No publiques su contenido.

Abre la URL indicada en Edge o Chrome del mismo Windows. Tras entrar, abre Clientes: deben aparecer diez. Recorre sitios, edificios, salas y racks. Cambia una nota sintética, guarda y recarga para comprobar la persistencia durante esta ejecución.

El ejemplo contiene 10 clientes, 15 sitios, 25 edificios, 68 salas, 68 racks, 311 equipos, 633 grupos de puertos, 5408 puertos, 623 conexiones y 1246 extremos. Es **sólo inventario**, no un dump PostgreSQL, cuentas instaladas, sesiones, factores MFA ni un full backup de recuperación.

## 7. Terminar

Vuelve a PowerShell y pulsa **Ctrl+C** una vez. Espera el mensaje de procesos detenidos. Sólo se detienen el servidor y PostgreSQL creados por esta ejecución. Los archivos y las demás bases se conservan.

Para un despliegue Windows persistente utiliza su paquete nativo revisado por separado y su guía de operador correspondiente. El auxiliar de demostración no es una herramienta de backup/restore ni de activación MFA.

## 8. Problemas frecuentes y alcance MFA

| Resultado | Acción |
|---|---|
| GitHub muestra 404 o solicita acceso | Comprueba la URL pública, la conexión y el proxy; la descarga no necesita una cuenta. |
| Falta `py` | Instala Python oficial con lanzador y reabre PowerShell. |
| Falta el SDK | Prepara las herramientas fijadas de este clon y conserva `global.json`. |
| PostgreSQL no arranca | Revisa Visual C++, reinicio solicitado y log privado del laboratorio. No utilices otra base para eludirlo. |
| Falla compilación o hash de salida | Lee el log privado, corrige la causa y repite el paso 4. |
| La URL deja de responder | Mantén la consola abierta; cada ejecución usa otro puerto. |

Enrolamiento/login MFA y dashboard nativos se probaron por separado. Política: 45 días de gracia para cuentas ordinarias, técnicos y administradores de clientes; cuentas existentes desde activación de política y nuevas desde creación. Sólo están exentos los administradores globales del Systemhaus con ambas capacidades globales de administración. Quitar un factor no reinicia el plazo. Recuperación, emergencia/pérdida y rotación tienen implementaciones internas revisadas y ensayos de laboratorio acotados; la aceptación productiva y los escenarios pendientes permanecen abiertos. Ver [estado actual y límites](PUBLICACION-GITHUB-12-11-2026.md).

MFA real necesita un almacén protegido separado de PostgreSQL, configuración DPAPI/ACL correcta e identidad del servicio. Las claves y sobres de recuperación no se incluyen en GitHub. No copies configuraciones de otro equipo ni actives MFA mediante esta demo.
