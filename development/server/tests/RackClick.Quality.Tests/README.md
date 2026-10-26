# Pruebas focales de calidad rev4

Proyecto xUnit adicional; conserva el ejecutable nativo `RackClick.Domain.Tests` y
los arneses HTTP/PostgreSQL existentes. No sustituye QA ni aceptación del servidor.

## Dependencias fijadas

SDK del repositorio: **10.0.401** (`development/server/global.json`). El proyecto
usa el framework `Microsoft.AspNetCore.App` y referencia el servidor real, sin EF
ni sustitutos de PostgreSQL. Npgsql **10.0.3** llega del proyecto del producto.
La tanda de fundamento del **21.10.2026** no modificó su proyecto ni su lock.
Después, el **23.10.2026**, M2 añadió **Otp.NET [1.4.1]** al proyecto del producto
y actualizó los locks del servidor y de estas pruebas; ver
[resultados de M2](../../../../docs/MFA-M2-RESULTADOS.md). Esa dependencia es de
producto, no exclusiva de pruebas. Esta aclaración no cambia paquetes ni locks,
ni acredita por sí sola MFA integrado o una nueva ejecución de sus pruebas.

| Paquete exclusivo de pruebas | Versión | Fuente oficial comprobada el 21.10.2026 |
| --- | --- | --- |
| Microsoft.NET.Test.Sdk | 18.0.1 | <https://www.nuget.org/packages/Microsoft.NET.Test.Sdk/18.0.1> |
| xunit.v3 | 3.2.2 | <https://www.nuget.org/packages/xunit.v3/3.2.2> |
| xunit.runner.visualstudio | 3.1.5 | <https://www.nuget.org/packages/xunit.runner.visualstudio/3.1.5> |
| Testcontainers.PostgreSql | 4.16.0 | <https://api.nuget.org/v3-flatcontainer/testcontainers.postgresql/index.json> |

`packages.lock.json` fija transitivos y hashes NuGet. El primer intento con
Testcontainers **4.10.0** fue rechazado por NU1903: arrastraba SSH.NET **2025.1.0**
con [GHSA-mggc-4xg6-vcxf](https://github.com/advisories/GHSA-mggc-4xg6-vcxf) y
[GHSA-q939-rpr3-3284](https://github.com/advisories/GHSA-q939-rpr3-3284).
Se eligió 4.16.0, publicado en NuGet el 08.10.2026, que resuelve SSH.NET **2026.0.0**.
No se desactivó ni silenció la auditoría NuGet.

## Ejecución Windows desde la raíz

```powershell
. ./tools/windows/Use-Toolchain.ps1
dotnet --version
dotnet restore development/server/tests/RackClick.Quality.Tests/RackClick.Quality.Tests.csproj --locked-mode --source https://api.nuget.org/v3/index.json
dotnet test development/server/tests/RackClick.Quality.Tests/RackClick.Quality.Tests.csproj --configuration Release --no-restore
```

Diez casos HTTP ejercitan `HttpSecurityHeaders.Apply`: respuestas correctas y de
error, CSP y CSP Report-Only preservadas, sin habilitar CORS, HSTS exactamente de
un día sin subdominios/preload, IP IPv4/IPv6, loopback, HTTP real/configurado,
modo de desarrollo y cabeceras Host/forwarded incapaces de activar HSTS.

## Adaptador PostgreSQL opcional con Docker Linux

Un caso lleva `[Trait("RequiresDocker", "true")]`. Primero consulta
`docker info --format '{{.OSType}}'`, sin iniciar el motor. CLI ausente, motor
inaccesible, plataforma Windows o timeout producen **Skipped**, con causa finita;
no acreditan ninguna operación PostgreSQL. Un fallo al descargar/crear/arrancar
el contenedor o en el código del producto produce **Failed**, nunca Skipped.

Para exigir ejecución real y prohibir que la falta de Docker pase por omisión:

```powershell
$env:RACKCLICK_REQUIRE_DOCKER = '1'
dotnet test development/server/tests/RackClick.Quality.Tests/RackClick.Quality.Tests.csproj --configuration Release --no-restore --filter 'RequiresDocker=true'
Remove-Item Env:RACKCLICK_REQUIRE_DOCKER
```

En Linux se usa el mismo proyecto con SDK 10.0.401 y un motor Docker local de
contenedores Linux ya preparado; `Use-Toolchain.ps1` es específico de Windows.
La prueba no instala Docker ni cambia su configuración. Su contenedor nuevo usa
la imagen oficial **postgres:17.11**, puerto aleatorio limitado a `127.0.0.1`,
base y contraseñas nuevas, sin volúmenes de host ni reutilización. La limpieza
pertenece al contenedor creado; no recibe una cadena de conexión externa.

El flujo ejecuta `PostgresStore.Bootstrap` (no hay una clase
`PostgresStoreBootstrap` en el producto), sus migraciones reales, login con 100
escalares Unicode y sesión leída mediante otro pool. Comprueba versión 17.11,
historial de migraciones, nombre literal, hashes de sesión/CSRF y rechazo de una
contraseña errónea con contador persistido, sin crear otra sesión. No demuestra
instalación Windows, ámbito multiusuario, concurrencia ni paridad completa RC9.

Ejecución real Windows/LEAO del 21.10.2026: **10 Passed, 0 Failed, 1 Skipped**,
salida0. Docker CLI está ausente; ninguna operación PostgreSQL de este adaptador
se ha ejecutado allí. La prueba negativa con `RACKCLICK_REQUIRE_DOCKER=1`
terminó con **0 Passed, 1 Failed, 0 Skipped**, salida1 esperada.
El informe saneado vive en `.local/rev4-quality-tests.json`; los TRX privados en
`.local/rev4-quality-results/`.
