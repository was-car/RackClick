# Condiciones concretas de distribución · ZIP18

12.11.2026 · Revisión independiente acotada. Sólo lectura de artefactos, metadatos y fuentes primarias; sin cambiar aplicación, ZIP, VM, servicios, Git ni publicación. No constituye un dictamen jurídico general.

**Resultado:** PUB-02 sigue reproducido en el ZIP18. Su corrección documental está identificada y no exige cambiar versiones. Continúan pendientes la habilitación aplicable a VC++, el tratamiento de las bibliotecas LGPL de PostgreSQL y las condiciones de entrega del runtime Windows. No se acredita todavía una Release instalable aprobada.

## Artefacto medido

` .local/install18-20261111/entrega-final/RackClick-Windows-Completo-18.zip` — 144.203.012 bytes, SHA256 `512fcaf6aa255e6ff6ae9610daa722f8b9d135972d33d5a249b9d42ad90625ed`.

- Exterior: 73 entradas; `Servidor.zip`: 117; `RackClick.zip`: 2021. Sin entradas duplicadas.
- Payload SHA256: `9ce1f7258affda57065ab14bd3a3c2a45aea8e30e44d88bf94cddb42d60ac613`.
- Bundle SHA256: `098392ebfc62f2fe5ec9f79909ea3bdbecbf3c565286747a5a9d9507fccd8d40`.
- Servicio: **38 archivos**, incluidos 30 DLL de paquetes en raíz, tres DLL específicas de Windows y cinco artefactos de RackClick/apphost/configuración. Lock: **30 paquetes**, todos10.0.12, SHA256 `c4675f230703580660730a69f9d56a2fbef016fbd429942f82db0d0cc235f98e`.
- Runtime seleccionado: 339 archivos, .NET/ASP.NET Core10.0.12. PostgreSQL: 1568 archivos de17.11-4; no se auditó individualmente cada uno.

Medición reproducible privada: `.local/github-installable-20261112/review/inventory.py` e `inventory.json`. Referencia comparada: [revisión del30.10](../../../../docs/REVISION-PUBLICACION-30-10-2026.md).

## PUB-02 · P2 · corrección documental identificada

`LICENSES/service-host-NOTICE.txt` (316 bytes; SHA256 `21aee7ffa0bd422172025695578e486cb592da05b5d3d86a45dce4f8cdb23d80`) dice MIT y remite a `dotnet-LICENSE.txt`. El destino contiene **Microsoft .NET Library**, 9519 bytes, SHA256 `7f6839a61ce892b79c6549e2dc5a81fdbd240a0b260f8881216b45b7fda8b45d`: no es el texto MIT indicado.

Comprobé los `.nuspec` de los30 paquetes: todos declaran `license type="expression" = MIT`, proceden del repositorio `dotnet/dotnet`, commit `95017c711e6afc1085133d440e42b4bd78155701`. No llevan un archivo LICENSE; todos incluyen el mismo `THIRD-PARTY-NOTICES.TXT`, 78041 bytes, SHA256 `6d15e10a101c6bfff2ab4429ed061bf76c456fc4b23ad6b03e0d0f8377148a21`.

Inventario por familias, todos con versión10.0.12:

| Familia | Paquetes |
|---|---|
| Microsoft.Extensions.Configuration | Base, Abstractions, Binder, CommandLine, EnvironmentVariables, FileExtensions, Json, UserSecrets (8) |
| Microsoft.Extensions.DependencyInjection | Base, Abstractions (2) |
| Microsoft.Extensions.Diagnostics | Base, Abstractions (2) |
| Microsoft.Extensions.FileProviders | Abstractions, Physical (2) |
| Microsoft.Extensions.FileSystemGlobbing | Base (1) |
| Microsoft.Extensions.Hosting | Base, Abstractions, WindowsServices (3) |
| Microsoft.Extensions.Logging | Base, Abstractions, Configuration, Console, Debug, EventLog, EventSource (7) |
| Microsoft.Extensions.Options | Base, ConfigurationExtensions (2) |
| Microsoft.Extensions.Primitives | Base (1) |
| System | Diagnostics.EventLog, ServiceProcess.ServiceController (2) |

**Acción concreta para una edición posterior:** conservar el lock/inventario; añadir el MIT completo del commit anterior y su aviso de copyright, conservar también el ThirdPartyNotices exacto de los paquetes y corregir la referencia del NOTICE. Mantener separada la licencia del runtime Windows. El MIT descargado de la [fuente fijada](https://raw.githubusercontent.com/dotnet/dotnet/95017c711e6afc1085133d440e42b4bd78155701/LICENSE.TXT) mide1115 bytes, SHA256 `ae48df11a335dc1a615f4f938b69cba73bcf4485c4f97af49b38efb0f216353b`; está privado en `review/dotnet-package-MIT-pinned.txt`. Las fichas oficiales de [WindowsServices10.0.12](https://www.nuget.org/packages/Microsoft.Extensions.Hosting.WindowsServices/10.0.12) y [EventLog10.0.12](https://www.nuget.org/packages/System.Diagnostics.EventLog/10.0.12) corroboran MIT. No se modifica el ZIP18 conservado: una corrección de avisos necesita nueva edición y hashes.

## Hash NuGet · no es indicio de alteración

La comparación inicial SHA512 del archivo `.nupkg` completo contra `contentHash` del lock no coincide. **No son la misma magnitud para paquetes firmados.** NuGet guarda el hash del archivo completo en `.nupkg.sha512`; el ContentHash de `.nupkg.metadata` excluye metadatos de firma. Comprobé que **30/30 ContentHash de metadata coinciden con el lock**, con origen `https://api.nuget.org/v3/index.json` y firma presente en los paquetes. No se ejecutó una nueva validación criptográfica de todas las firmas. La distinción está documentada en la [especificación oficial NuGet](https://github.com/NuGet/Home/wiki/Nupkg-Metadata-File) y en [PackageArchiveReader](https://github.com/NuGet/NuGet.Client/blob/dev/src/NuGet.Core/NuGet.Packaging/PackageArchiveReader.cs).

## Runtime Windows · conservar términos distintos de MIT

El bundle conserva `dependencies/dotnet/LICENSE.txt` (9519 bytes, pin anterior) y `ThirdPartyNotices.txt` (78887 bytes; SHA256 `deb4427a295e1ed474b0d81c5a0d972c1b550b9a715cda939cdfa9236b1b418f`). Este último no es idéntico al de los paquetes; no se deben intercambiar por similitud del nombre.

El apartado3 del contrato transportado permite distribución de código objeto con condiciones: funcionalidad propia principal, términos protectores para distribuidores/usuarios externos, aviso de copyright válido y las obligaciones de distribución allí indicadas. **Añadir archivos de licencia no acredita por sí solo esas condiciones.** Falta fijar titular/aviso y términos concretos de entrega de RackClick y comprobar su correspondencia con el contrato transportado. No deduzco que se necesite Visual Studio para distribuir todo .NET: esa cuestión es distinta de VC++. Microsoft distingue expresamente [distribuciones Windows y paquetes MIT](https://github.com/dotnet/core/blob/main/license-information.md) y exige los avisos aplicables en su [modelo de licencias de activos](https://github.com/dotnet/runtime/blob/main/docs/project/licensing-assets.md).

## PostgreSQL · LGPL concreta pendiente

El ZIP conserva la licencia PostgreSQL y cuatro avisos originales adicionales del paquete EDB. `server_license.txt` mide1388 bytes, SHA256 `39294f3f5b41533b307e118ee37c356f32cbc7746fc97e8b91f1b49a9068a24e`. La [licencia PostgreSQL](https://www.postgresql.org/about/licence/) permite distribución conservando sus textos. El origen Windows17.11-4 está fijado en `development/toolchain.lock.json`; el [proveedor confirmó su SHA256](https://github.com/EnterpriseDB/edb-installers/issues/706#issuecomment-5774581917). Esto no sustituye las condiciones de bibliotecas incluidas.

Confirmé físicamente en el bundle `bin/libiconv-2.dll` y `bin/libintl-9.dll`. Sus bytes coinciden con los archivos locales cuya información de versión leí: **libiconv1.15** y **libintl0.19.8**. El aviso `commandlinetools_3rd_party_licenses.txt` (64980 bytes; SHA256 `67181bbd5ddb5a0094aa9c82b97536a27811461a3b61c3c11588a2731cfc7b3b`) incluye expresamente gettext/libiconv y LGPL2.1. Por tanto, no es una precaución hipotética sobre una biblioteca ausente.

**Pendiente concreto:** identificar y conservar las fuentes correspondientes, modificaciones y materiales necesarios de esas bibliotecas para los binarios EDB exactos, y documentar la modalidad de cumplimiento aplicable a su distribución binaria. No quedó acreditada una entrega de fuentes/oferta correspondiente por conservar sólo el texto LGPL. Para un mecanismo basado en biblioteca reemplazable también hay que contrastar esa condición con las verificaciones de integridad del instalador; esta tanda no las cambia ni resuelve jurídicamente su alcance. La versión de archivo no demuestra que un tarball genérico sea la fuente correspondiente del build EDB.

También está `libwinpthread-1.dll`: metadatos MingW-W64, versión1.0.0.0, y bytes contrastados con el ZIP. El encabezado genérico de “pthreads” del aviso no basta para atribuir automáticamente la misma licencia a ese binario: falta su mapeo preciso de procedencia/licencia. No extiendo LGPL a RackClick entero ni declaro una infracción.

## VC++ · P1 externo aún abierto

El ZIP18 incluye `prerequisites/vc_redist.x64.exe`, 18731856 bytes, SHA256 `843068991daaa1f73ad9f6239bce4d0f6a07a51f18c37ea2a867e9beca71295c`, versión fijada14.51.36247.0. Microsoft limita su redistribución a usuarios de Visual Studio licenciados y a sus términos aplicables. Falta la habilitación/términos concretos del distribuidor; no se necesitan claves por chat y el repositorio privado no acredita esa condición. [Microsoft Learn](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files?view=msvc-170).

## Alternativa factible, no implementada

Una entrega nativa podría distribuir RackClick y adquirir **directamente de Microsoft/EDB los terceros exactos fijados**, con consentimiento, verificación de hashes y conservación de avisos. Así no se subiría nuestra copia de VC++/runtime/PG como activo propio. Esto no equivale a la demo10, ni obliga a quitar MFA, catálogo o Demo50. Faltaría implementar y medir esa adquisición, tratamiento de fallos/offline y reinicio, fijar los términos del operador y probar la instalación completa en otra VM limpia. Si cambia el archivo de descarga, hace falta un nuevo pin verificado; no se sustituye una versión automáticamente. La [página oficial PostgreSQL Windows](https://www.postgresql.org/download/windows/) contempla los binarios ZIP para integradores.

## Ejecuciones y límites

Ejecuté apertura de ZIPs anidados, tamaños/SHA256, inventario de38 archivos de servicio, lectura de30 nupkg/nuspec/metadata y lock, inventario de avisos, comparación de TPN y descarga de un texto MIT fijado, lectura de metadatos de versión y comprobación de bytes de las tres DLL señaladas y del CRT. Probes privados: `inventory.py`, `inventory.json`, `notice-comparison.json`, `pg-versions.json`, `bounded-component-check.json`, bajo `.local/github-installable-20261112/review/`.

**No ejecutado:** build/tests de producto, instalación, DLL/EXE del ZIP, VM, servicios, PostgreSQL, MFA, rollback ni publicación. No se auditó jurídicamente todo el árbol PG ni se cambió una dependencia. La instalación limpia equivalente continúa pendiente; A es New17 más finalización, sin acreditar coldNew18. Sin nueva métrica: **26,63/100 del cierre restante**; no es porcentaje global ni aceptación final.
