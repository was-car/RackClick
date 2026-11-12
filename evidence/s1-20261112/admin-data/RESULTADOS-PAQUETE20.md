# Edición Windows20 · administración de inventario

12.11.2026. Implementación del productor en el worktree aislado `feature/admin-data-20261112`, base `98ad435`. No se ejecutan instaladores, no se modifican VM, servicios, cuentas ni instalaciones existentes. Esta evidencia sólo acredita los comandos indicados; la aceptación instalada corresponde a Wascar.

## Investigación y decisión previa

Se revisaron el contrato `docs/ADMIN-DATOS-COPIAS-INVENTARIO-12-11-2026.md`, tarea3 del plan, `build_server_distribution.py`, `package_offline_bundle.py`, los dos productores nativos y la reconstrucción online19. El productor19 extrae operadores históricos del ZIP18 y fija la aplicación48 anterior: no sirve como origen de los operadores de esta entrega.

Se reutilizan los algoritmos de empaquetado reproducible y sus límites, validadores de rutas, licencias y pins oficiales vigentes. El productor20 recibe distribución, servicio y Demo50 explícitos y toma los operadores del worktree actual. El servicio se comprueba con inventario completo de37 archivos, DLL `130e9cc3959d414a0e00759a2e3323a0fc004d76113df56c250f319d38065c61` y digest del árbol `7f94e7d25966e8ddb3a534ab66d7be73e2ee59d513a84bc04aa6f66e16f09b63`; no lleva apphost. La copia Demo03 conserva su pin `d7ab9469d4929af703285b0cc7eddcf13e9f245f43828cfcaee95c0e2d2e9215`.

Se reutilizan las fuentes primarias y consultas válidas de19, sin cambio de versiones, descargas adicionales ni nuevas dependencias: [.NET10.0.401](https://builds.dotnet.microsoft.com/dotnet/Sdk/10.0.401/dotnet-sdk-10.0.401-win-x64.zip), [PostgreSQL17.11-4](https://get.enterprisedb.com/postgresql/postgresql-17.11-4-windows-x64-binaries.zip), [VC++](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist), [Python3.12.3](https://www.python.org/downloads/release/python-3123/), [Npgsql](https://github.com/npgsql/npgsql/tree/d3768398c17877b3a916c3c4d87e8e11698991fc), [Otp.NET](https://github.com/kspearrin/Otp.NET/tree/83b39e1f2a5bfc87b6d1af15b91bffc6f1638429). Los locks fijan bytes y hashes. La caché privada existente se verifica antes de usarla. .NET/PG/CRT/Python se adquieren del proveedor en destino con HTTPS/SChannel; Python sólo consume la caché completa verificada y carece de fallback de red.

El nuevo perfil `schema48-admin-data-01` mantiene58 archivos servidor,18 frontend y las mismas48 migraciones. No hay DDL nuevo. Los perfiles previos permanecen. El ZIP público20 omite `CARGAR-50-CLIENTES`: su cargador antiguo fija la aplicación anterior. La vía de carga20 es el panel web; el ZIP Demo03 puede conservarse dentro de Core como fuente sintética auditada. Los57 archivos de consulta `DATOS-DEMO50` quedan disponibles sin ejecutar el cargador anterior.

El `00-LEEME.md`03 también remitía a ese cargador. Sólo en la copia exterior20 se adapta al panel EN/DE/ES y se recalculan las sumas de la carpeta; los JSON, visor y demás datos conservan sus bytes. El ZIP fuente03 dentro de Core permanece idéntico. El montador20 verifica su hash y no extrae el cargador histórico en el directorio privado de preparación.

Por la petición de cuenta genérica, el campo editable de administrador nuevo propone `RackClickAdmin`. No se modifican credenciales existentes. El único cambio de GUI nativa es ese valor inicial en `Show-RackClickInstaller.ps1`.

## Pruebas ejecutadas antes de fijar la aplicación

Entorno: Windows del desarrollo, Python3.12 y Windows PowerShell5.1; fixtures temporales controlados, sin instalar el producto.

Comprobación del intérprete: Python3.12.3 y zlib1.3.1, coincidentes con el ensamblador temporal fijado.

- `C:/Python312/python.exe -B -m unittest tools.tests.test_distribution48_admin_data -v`: rojo por ausencia de perfil nuevo y verde tras añadirlo;1caso.
- `C:/Python312/python.exe -B -m unittest tools.tests.test_installer20_packaging -v`: rojo por inventarioSQL de edición20 no reconocido; verde tras las ramas20. Comprueba26operadores SQL,37archivos de servicio sin apphost, avisosMIT y manual20 en ambos envoltorios.
- `C:/Python312/python.exe -B -m unittest tools.tests.test_online_installer20 tools.tests.test_online_installer20_windows -v`:28casos,115,686s,OK. Incluye integridad de archivos/metadatos, extras/ausentes/duplicados, rutas y dispositivos Windows, caché y hashes, HTTP/hosts/redirects/tamaños, límites de procesos, host/DC/cuentas/servicios existentes y falta de elevación/confirmación sin cambios.
- Prueba añadida de la exclusión del cargador anterior: roja por función inexistente y verde; sólo los57datos consultables salen del ZIP Demo03.
- `C:/Python312/python.exe -B -m unittest tools.tests.test_distribution48_admin_data tools.tests.test_installer20_packaging tools.tests.test_online_installer20 tools.tests.test_online_installer19 tools.tests.test_installer_edition_guard -v`:27casos,40,313s,OK. Regresión pertinente del productor19 y rechazos tempranos de ediciones/hash, sin reconstruir ni sustituir su entrega.
- `C:/Python312/python.exe -B -m unittest tools.tests.test_installer20_default_admin -v`: rojo por `Wascar`, verde tras proponer `RackClickAdmin`. Construye el plan New con los campos y la expresión real de la interfaz y lo valida mediante `Read-SetupPlan`; también acepta la edición del campo a `MyInventoryAdmin`. No abre la GUI ni ejecuta instalación.
- El CLI20 rechaza `--reference18` sin crear salida. Los seis archivos de referencia comprobados (guardia de instalación48, permisos de instancia, perfil48 histórico, productor19, montador19 y launcher19) coinciden por bytes con HEAD. Los EOL de los archivos existentes modificados se conservan.

## Congelación y artefactos

La aplicación estabilizada proporcionada por el coordinador es `schema48-admin-data-01`,76archivos (58+18),35919405bytes de contenido. Se comprobaron sus tres metadatos y los79archivos completos. Las48SQL coinciden byte por byte con HEAD. Los lectores Python, `Test-ServerDistribution.ps1` y `RackClick.OfflineBundle.ps1` añaden sólo la asociación exacta nueva; el mapa de perfiles anteriores se contrastó íntegro con el de HEAD y coincide.

| Artefacto | SHA256 | Bytes |
| --- | --- | ---: |
| Aplicación · manifest.json | `f7b971f31dd5f424dbce35c9c18a4c6c75c8968f31d10c5df8bbfe215e5b8a53` | — |
| Aplicación · inventory.json | `f20f311fcba7ffe6d37cdc4980efa26aeebaa50d6a0e42443ab365bafcd7efff` | — |
| Aplicación · SHA256SUMS.txt | `d3d7b25a4543b976884a7294d11daaa21b7640c7db2b5a87e2d4dd873a6bac9b` | — |
| RackClick-Bundle-48-20.zip · privado | `c69a82210a4f221058c088d01e5b70a13c4ec1855386692c44774cc6ee28efea` | 120035617 |
| RackClick-Payload-20.zip · privado | `df4cef5142a3eb7eac302bd3a4d058bfc2092bb258b4332280a2301253bb669a` | 120237171 |
| RackClick-Servidor-20.zip · privado | `532e966250a0a54e07aac8f3b2812813c7782c9e5872d6f0630b7eae66f53043` | 120265531 |
| RackClick-Core20.zip | `b514876ed664a6a3ae7b733993e2522a70dc752651865cb7564c0a04cc5f1577` | 9630869 |
| RackClick-Windows-Online-20.zip | `2644dc115ed03086a5a1d60b5e6418989350ebaf08942e8c07d81a5bdda813fb` | 11555659 |

Salidas exclusivas bajo `.local/admin-data-package20/build01/`. Sidecar externo `RackClick-Windows-Online-20.zip.sha256`. No se incluyó el manualMD con el hash exterior para evitar una referencia circular. Los dosHTML20 incluidos aclaran descarga pública sin login en ES/EN/DE; el banner del CMD nuevo indica20. Se corrigió esta observación de revisión antes de generar Core/native/ZIPexterior; no existe una entrega20 anterior distribuida ni sobrescrita.

Core20 contiene201archivos y el exterior63. `FILES.json`, `payload.json`, `PAQUETE.json`, `ENTREGA.json` y las sumas fijan los inventarios correspondientes. Se comprobaron los archivos y bytes contra esas listas, los50JSON contra la fuente03 y la ausencia del cargador anterior, apphost de servicio y runtimes oficiales en el transporte exterior/Core.

## Reconstrucción y comprobación final

- Perfil nuevo: rojo nativo `manifest_distribution_unsupported` antes de registrar su hash exacto; después8/8pruebas de distribución PASS, sin skips. Incluyen76archivos reales, hash externo incorrecto, manifiesto rehasheado, cruce al perfil anterior, DLL alterada, SQL48ausente y apphost extra.
- `tools/package_offline_bundle.py` con manifiesto nuevo, lock14 y cachés oficiales verificadas:2021archivos,307158166bytes sin comprimir; bundleprivado c69a… . `Test-RackClickOfflineBundle.ps1` con ruta absoluta devuelve `bundle_verified`,2021archivos,48/10.0.12/17.11. El intento inicial con ruta relativa fue rechazado por `path_invalid`; no cambió archivos y se corrigió la invocación.
- Dos ejecuciones explícitas de `build_online_installer20.py --application … --service-publish … --demo …` produjeron Coreidéntico. Dos ejecuciones de `--core … --native …` produjeron el exterioridéntico.
- Se verificó elZIPoficial de Python3.12.3por tamaño/SHA y se extrajo en una carpeta privada nueva. Su `python.exe -I -B core/assemble.py --core-root … --work-root … --cache …` reconstruyó bundle, payload y native. Los tres se compararon byte por byte con los productores directos y coinciden. El montador no descargó ni instaló nada y no expandió el cargadorDemo03. Recibo `reconstructed/assembly-report.json`.
- Entrada generada `Install-RackClickOnline.ps1 -Mode Check`: en el host de desarrollo devuelve `host_not_supported`,exit2,`installed:false`. El mismo script y Core reales, sustituyendo únicamente las dos barreras de inventario de host por fixtures y haciendo fallar cualquier petición/escritura de stage, devuelven `online_checked`,sin descargas ni instalación. Es verificación de artefactos; no acredita soporte/instalación real de WindowsServer2025. Recibo `POWERSHELL-CHECK.json`.
- El helperpuro `Assert-SetupPayload` leyó la copia extraída del payload auténtico y verificó121entradas. Tras alterar sólo la DLL del servicio en esa copia de fixture rechazó `setup_payload_hash_mismatch`. LosZIPrelease permanecen intactos. Recibo `NATIVE-PAYLOAD-CHECK.json`.
- Inventarios, hashes y comprobaciones de exclusividad/reproducción: `.local/admin-data-package20/build01/RELEASE-AUDIT.json`. Salida de regresión focal: `PACKAGING-TESTS.log` en ese mismo directorio.
- Regresión final: `C:/Python312/python.exe -B -m unittest tools.tests.test_distribution48_admin_data tools.tests.test_installer20_packaging tools.tests.test_installer20_default_admin tools.tests.test_online_installer20 tools.tests.test_online_installer20_windows tools.tests.test_online_installer19 tools.tests.test_installer_edition_guard -v`:56/56PASS,113,909s,sin skips. Incluye los negativos de Python/WindowsPowerShell5.1, perfil nuevo real, reproducción/rechazo de ediciones e históricos, cuenta genérica editable y guía/datos públicos sin el cargador anterior. No se amplía la afirmación a suites ajenas al empaquetado ni a instalación.

## Límites y siguiente paso

Esta tanda acredita integridad, reconstrucción y rechazos del empaquetado. No ejecutó instaladores, no probó una instalación WindowsServer ni modificó VM, cuentas o servicios. No publicó ni adoptó el producto. Las guardias Restore48 permanecen byteidénticas. Revisión independiente final, escaneo de fuentes/activos, publicación y comprobación de la descarga corresponden al coordinador; QA instalada/adopción corresponden a Wascar. El porcentaje global no se incrementa por generar archivos ni publicar código.
