# RackClick Windows Service — C4

Host SCM real .NET 10; `AddWindowsService` de Microsoft.Extensions.Hosting.WindowsServices **10.0.12**, restauración cerrada por `packages.lock.json` y SDK **10.0.401/disable**. No sustituye el backend ni instala PostgreSQL.

## Contrato

`RackClick.WindowsService.exe --config C:\ruta\service-config.json`

Sólo acepta ejecución bajo SCM; para pruebas locales explícitas añadir `--console`. En consola con stdin redirigido, la línea exacta `stop` solicita parada. No hay autodetección que convierta un error SCM en consola.

serviceName admite `RackClick` o `RackClick-Recovery-` seguido de8a32hexadecimalesminúsculos, para recuperación paralela.

JSON schemaVersion1, propiedades exactas (sin desconocidas ni duplicadas):

```json
{
  "schemaVersion": 1,
  "serviceName": "RackClick",
  "runtimeScriptPath": "C:\\RackClick\\operators\\Invoke-RackClickServerRuntime.ps1",
  "serverManifestPath": "C:\\RackClick\\server-profile.json",
  "serverManifestSha256": "SHA256_REAL_DE_64_HEXADECIMALES",
  "logDirectory": "C:\\RackClick\\runtime\\logs"
}
```

Rutas absolutas locales, sin ADS/UNC ni reparse en ningún ancestro. Configuración, manifiesto y directorio de logs exigen owner SID actual o SYSTEM y DACL cuyos Allow sólo sean SID actual/SYSTEM, con lectura para la identidad actual. En SCM, runtimeScriptPath y su directorio inmediato son código protegido: owner Administradores o SYSTEM; los únicos escritores admitidos son esos dos SID. La cuenta estándar sólo lee/ejecuta. El instalador debe proteger también los ancestros del árbol de código. En --console explícito, exclusivamente para fixtures, runtimeScriptPath usa la misma ACL privada SIDactual/SYSTEM y puede pertenecer al usuario estándar; esa excepción nunca se aplica bajo SCM. El instalador debe preparar esas ACL y una cuenta estándar existente. Este host no crea cuentas ni transmite contraseñas.

Inicia exclusivamente Windows PowerShell del directorio System32 del sistema, con `-NoProfile -NonInteractive -ExecutionPolicy Bypass -File ... -Operation Start -ManifestPath ... -ExpectedManifestSha256 ... -RunId GUID`. Stop usa los mismos argumentos, operación Stop y mismo RunId. No lanza PostgreSQL directamente ni reinicia Start automáticamente.

Cada proceso arranca suspendido, se asigna al Job KILL_ON_JOB_CLOSE antes de reanudar; hijos quedan contenidos. Salida inesperada de Start, incluso código0, provoca fallo del host. Stop espera confirmación0 del runtime Stop y salida0 del runtime Start; timeout90s, host110s. Ante fallo elimina el Job y retorna fallo; no declara parada limpia. No confundir estado SCM Running con readiness HTTPS: el instalador debe comprobar Verify/readiness por separado. El directorio de logs se valida; el host escribe un archivo privado `host-<RunId>.jsonl`, sólo timestamp/code/runId/exitCode, sin argumentos, stdoutPS ni secretos. Las trazas operativas corresponden al runtime. Los errores de consola sólo contienen clase, sin mensaje sensible.

## Construcción reproducible

Desde esta carpeta, usando `.local/dotnet-10.0.401/dotnet.exe` por ruta absoluta:

```powershell
dotnet restore RackClick.WindowsService.csproj --locked-mode --configfile ..\..\NuGet.Config
dotnet build RackClick.WindowsService.csproj --no-restore
```

No exige cambiar global.json, paquetes del servidor o perfil del usuario. Publicación framework-dependent: requiere que el instalador resuelva explícitamente el runtime .NET fijado (no depender de PATH/perfil). No instalar el SDK en el servidor de producción.

## Pruebas reales y límites

`C:/Python312/python.exe -B development/windows-service/test_host.py` desde raíz. Crea exclusivamente fixtures nuevas bajo `.local`; no instala SCM/CRT, no abre firewall, no lanza PostgreSQL ni toca QA. Nueve casos: salida temprana con marcador real, SCM obligatorio, propiedad desconocida, schema distinto, hash incorrecto, DACL pública, Stop limpio con mismo RunId, Stop fallido y junction rechazada. Fixtures privadas por SID y SYSTEM; el entorno inyecta un Allow LogonSession que la fixture elimina explícitamente para evitar falsos positivos. Resultado final ejecutado19.10.2026: `.local/rackclick-service-bad9hzwq/result.json`,9/9PASS.

Fallos de desarrollo corregidos antes de ese resultado: dos errores de compilación; fixture ACL inicial inadecuada; primera prueba de falloStop detectó espera pendiente por Dispose prematuro de Process, corregido. La fixture mata sólo su host al vencer su timeout. No se ejecutaron instalación/Start/Stop reales mediante SCM ni reinicio bajo cuenta de servicio: pendientes de ensayo independiente con elevación en servidor. Revisión independiente a cargo del coordinador, no del implementador.

Fuentes oficiales: [paquete Microsoft](https://www.nuget.org/packages/Microsoft.Extensions.Hosting.WindowsServices/10.0.12), [Windows Services .NET](https://learn.microsoft.com/en-us/dotnet/core/extensions/windows-service), [Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects). Dependencias Microsoft.Extensions bajo MIT; [licencia dotnet/runtime](https://github.com/dotnet/runtime/blob/main/LICENSE.TXT). Ningún binario descargado de terceros fuera de NuGet oficial.


Revisión posterior: carrera Start/Stop corregida con runtimeLock compartido; parada recibida antes de iniciar el worker impide Launch. DisposeJob atómico. Fixture focal adicional `test_host.py --focus-immediate`:5iteraciones PASS, `.local/rackclick-service-nq3mdgjt/result.json`; copia TEST-IMMEDIATE.json. No se repitió suite amplia ni se ensayó ACL de código protegido real SCM con elevación.

Publicación final06 tras normalizar únicamente EOL/EOF: `.local/service-host-c4-publish-06/`,38archivos (35raíz+3runtimes). DLL SHA256 `130e9cc3959d414a0e00759a2e3323a0fc004d76113df56c250f319d38065c61`. PublishRelease conSDK401/locksinvariantes pasó; no repetición de suite9casos por cambios sólo de espacios. Publicaciones anteriores son históricas.
