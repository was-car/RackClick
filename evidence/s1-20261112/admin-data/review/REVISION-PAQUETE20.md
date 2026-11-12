# Revisión independiente del empaquetado Windows20

12.11.2026. Revisor separado del productor. Worktree `feature/admin-data-20261112`, base `98ad43582dcf08b3227f16873175625048dc09bd`. Encargo limitado a fuentes, contrato, contenido, integridad, licencias y transporte de la edición20. Backend y frontend tienen revisores propios.

## Estado

**Favorable para el transporte Outer20 identificado abajo, dentro del alcance de esta revisión. Sin P1/P2 abiertos reproducibles en las fuentes y artefactos examinados.** Se completó el contraste independiente de Core/Native/Outer congelados. La publicación corresponde al coordinador y la prueba instalada New20 sigue pendiente de Wascar. Sin instalación ni adopción. Las pruebas de B19 no se atribuyen a New20.

## Hallazgos

- **P2, documentación de descarga, corregido y verificado en los ZIP finales.** Los dos manuales20 remitían a una Release privada en ES/EN/DE, incompatible con la descarga pública Windows20 sin autenticación. Se informó al coordinador y el productor corrigió las seis instrucciones antes de la congelación exterior. Archivos: `docs/INSTALADOR20-ONLINE.html`, `docs/INSTALADOR20-SQL-PROTEGIDO.html`, pasos de descarga. Outer y Native contienen los bytes corregidos actuales. No se solicitó ni se cambió visibilidad del repositorio privado de fuentes.
- **P3, identificación visual, corregido y verificado en Outer final.** El nuevo `tools/windows/online-install20/INICIAR-RACKCLICK.cmd` mostraba `online19`. Corregido a20 por el productor; el launcher19 histórico sigue idéntico.
- No se identificaron otros P1/P2 reproducibles en las fuentes examinadas. Esta conclusión tiene el alcance y límites descritos abajo.

## Aplicación y fuentes examinadas

La aplicación coincide por inventario completo, SHA256 y longitudes: 76 archivos, 58 servidor +18 frontend, **35.919.405 bytes**. Manifiesto `f7b971f31dd5f424dbce35c9c18a4c6c75c8968f31d10c5df8bbfe215e5b8a53`; DLL `768df75ea0db5afa349d4d8a4191856cd83b29a19b35ab4d1541b3b5f3f177bf`. Se comprobaron también las sumas, `inventory.json` y los pins exactos del productor. El perfil nuevo se añade con identidad `schema48-admin-data-01`.

Los 48 SQL del artefacto coinciden byte a byte con `HEAD:development/server/database/*`; el perfil48 histórico sigue idéntico. Locks de servidor, frontend, servicio, toolchain y fuentes14 también coinciden con HEAD. El cambio del `.csproj` incorpora los JSON Demo50 y su manifiesto como recursos; conserva Npgsql10.0.3 y Otp.NET1.4.1.

Los tres lectores contienen la asociación cerrada del manifiesto nuevo y conservan el manifiesto48 anterior: `package_offline_bundle.py`, `RackClick.OfflineBundle.ps1` y `Test-ServerDistribution.ps1`. La validación de distribución real en Windows PowerShell5.1 devuelve `artifacts_verified`, 76/76. Las guardias `schema48_restore_not_available` permanecen en el instalador nativo y en `Install-RackClickOfflineBundle.ps1`; ambos archivos son idénticos a HEAD. No se amplía restauración48 por añadir la copia JSON de inventario.

La lectura comprobó límites/rutas del productor, rechazo de junctions antes de resolverlas, inventarios de aplicación/servicio, nombres de ZIP y colisiones Windows, creación exclusiva de outputs, pins cerrados de receta/Core/Native, fuente actual de operadores, lectura bloqueada de Core, relectura de receta, caché completa verificada y descarga en Windows con HTTPS/TLS1.2 sin cambiar validación de certificados. La lista de destinos/redirecciones está separada por proveedor; Python no tiene fallback de red. El entorno hijo elimina prefijos Python/.NET/profiler y fija PATH/TEMP/TMP. El ensamblador rechaza un work existente y conserva su marcador; no recupera ni borra stagings ajenos.

`RackClickAdmin` es el valor inicial del campo editable `bootstrapUser` del formulario nativo. La expresión real del plan toma su `.Text`; no se observa sustitución posterior por un usuario fijo. Los manuales20 remiten la carga al panel web y distinguen copia de inventario de recuperación PostgreSQL/Windows: sin cuentas, permisos, sesiones, factores ni plantillas privadas/compartidas; sólo destino vacío, sin sobrescritura ni fusión.

## Dependencias, fuentes y licencias

Se reutilizan las versiones y pins preexistentes del toolchain, fuentes14 y receta19: archivo SDK10.0.401 como fuente de runtime10.0.12, PostgreSQL17.11-4, CRT14.51.36247.0 y Python embebido3.12.3 temporal. No se cambia versión ni se incorpora biblioteca. Las fuentes URL, tamaños y SHA256/SHA512 se comparan en los locks y la receta; no se acredita una descarga de Internet por leerlos.

Se examinan los avisos íntegros fijados de Npgsql (903bytes), Otp.NET (1070bytes), servicio MIT y avisos de terceros, junto con los cinco archivos de licencia frontend. Se contrastó la omisión de runtime.NET/PG/CRT/Python del transporte público Outer y su Core. Native y bundle privados contienen dependencias runtime y **quedan fuera de publicación**. Esta revisión de contenido no autoriza redistribuir esos paquetes privados ni sustituye la aceptación de las condiciones del proveedor en destino.

## Artefactos congelados contrastados

Raíz privada de construcción: `.local/admin-data-package20/build01/`. Se leyeron los ZIP, sus inventarios internos y contenido; los hashes no se toman sólo del recibo del autor.

| Artefacto | Bytes | Miembros | SHA256 |
|---|---:|---:|---|
| `RackClick-Windows-Online-20.zip` (Outer público previsto) | 11.555.659 | 63 | `2644dc115ed03086a5a1d60b5e6418989350ebaf08942e8c07d81a5bdda813fb` |
| `RackClick-Core20.zip` (incluido en Outer) | 9.630.869 | 201 | `b514876ed664a6a3ae7b733993e2522a70dc752651865cb7564c0a04cc5f1577` |
| `RackClick-Servidor-20.zip` (Native privado) | 120.265.531 | 5 | `532e966250a0a54e07aac8f3b2812813c7782c9e5872d6f0630b7eae66f53043` |
| `RackClick-Bundle-48-20.zip` (privado) | 120.035.617 | 2021 | `c69a82210a4f221058c088d01e5b70a13c4ec1855386692c44774cc6ee28efea` |

Todos los miembros de Core201, payload122 y bundle2021 se contrastaron con sus inventarios (set exacto, tamaño y SHA256); las sumas exteriores cubren los otros62 miembros. Los operadores de Core/payload/bundle y las79 entradas de aplicación coinciden con el worktree actual. El árbol de servicio37 coincide con el digest fijado `7f94e7d25966e8ddb3a534ab66d7be73e2ee59d513a84bc04aa6f66e16f09b63`, DLL `130e9cc3959d414a0e00759a2e3323a0fc004d76113df56c250f319d38065c61`, sin apphost. Receta canónica `7b47bf9d6bda91bbbfb6ec1aa177a2c8f2cae14b0db86374fb4008d0c1ea226e` idéntica al archivo actual y al pin del launcher.

Los57 archivos exteriores `DATOS-DEMO50` tienen sumas recalculadas;55 contenidos conservan los bytes de la fuente03 y sólo cambian README/sumas. El ZIP fuente03 se conserva exacto dentro de Core: `d7ab9469d4929af703285b0cc7eddcf13e9f245f43828cfcaee95c0e2d2e9215`. No hay cargador histórico exterior. La guía `INSTALACION20-PASO-A-PASO.md` está fuera del ZIP, evitando circularidad al fijar el SHA exterior.

Se compararon byte a byte los archivos Core reproducido y Native reconstruido existentes con los congelados. **La reconstrucción la ejecutó el productor**; este revisor verificó sus bytes y no se atribuye esa ejecución. El recibo exterior declara `thirdPartyRuntimeBinariesIncluded=false` y `productionAdopted=false`, consistente con su contenido. Las fuentes19 y el perfil48 original permanecen conservados para identificación/retorno; no se ensayó rollback instalado.

## Pruebas propias ejecutadas

Entorno: Windows de desarrollo, Python3.12, Windows PowerShell **5.1.26100.9818**. Sin `dotnet build/test/publish`, instalaciones, servicios, cuentas, VM ni publicación.

Comando privado principal: `C:/Python312/python.exe -B C:/RackClick_SVR/.local/admin-data-20261112/review-package20-probes.py`. Sondas propias, sin repetir la suite55 del productor:

1. Inventario/hash/sumas/perfil cerrado de la aplicación real, positivo.
2. 48 migraciones byte a byte contra HEAD y perfil anterior, positivo.
3. 12 fuentes históricas, guardias, locks y toolchain sin cambios, positivo.
4. Ocho nombres inseguros, tres colisiones, cinco ediciones inválidas y pin equivocado, rechazados.
5. Junctions rechazadas por productor, empaquetador nativo y ensamblador; destino intacto.
6. Siete destinos de descarga rechazados y filtrado del entorno hijo en WinPS5.1.
7. Validación read-only de la distribución48 real en WinPS5.1, 76/76.
8. Staging existente rechazado, marcador y contenido conservados.
9. Inventario Core de fixture: válido aceptado, mismo tamaño con bytes alterados/extra/duplicado rechazados.
10. Seis ZIP inseguros rechazados antes de crear el destino, incluyendo backslash crudo en cabeceras central y local.
11. Receta inicialmente válida y modificación sólo de whitespace: el siguiente acceso vuelve a comprobar el pin y rechaza.

Primera corrida:8/8. Corrida ampliada:10/11 por error de fixture en la sondaZIP: `zipfile` en Windows normalizó `a\\b` a `a/b` antes de escribir. Se confirmó leyendo los bytes, se corrigió sólo el fixture para inyectar la barra cruda en ambas cabeceras y se repitió sólo esa sonda:1/1, seis rechazos. No se modificó producto por ese fallo. Resultados privados: `.local/admin-data-20261112/package20-independent-xgk00rn_/results.json`, `package20-independent-qqvv0ck4/results.json`, `package20-independent-ulgmj0rq/results.json`. No se cuentan las repeticiones como cobertura adicional.

Después de congelarse los pins y corregirse los manuales, se repitió el conjunto propio completo contra las fuentes finales: **11/11 PASS**, exit0. Resultado privado final: `.local/admin-data-20261112/package20-independent-rtdheqcq/results.json`. La repetición confirma el estado congelado; no añade puntos ni funciones.

Comprobaciones finales propias adicionales, ambas PASS:

- `C:/Python312/python.exe -B C:/RackClick_SVR/.local/admin-data-20261112/review-package20-artifacts.py <build01> <resultado-privado>`: contraste de las capas y licencias descrito arriba, todos los hashes/tamaños y comparación contra fuentes actuales. Resultado: `.local/admin-data-20261112/review-package20-artifacts-result.json`.
- `C:/Python312/python.exe -B C:/RackClick_SVR/.local/admin-data-20261112/review-package20-check.py`: launcher exacto extraído del Outer fijado, **sólo Mode Check**. El host real de desarrollo es rechazado con `host_not_supported`, exit2, `installed=false`. Con descubrimiento de host sustituido por facts válidos aislados (Server2025, role2, x64, no dominio), conservando el lector y ZIP Core reales: `online_checked`, `installed=false`. Tripwires impiden crear staging, confirmar o descargar; los dos archivos extraídos mantienen los hashes. No demuestra compatibilidad instalada en Server2025. Resultado: `.local/admin-data-20261112/review-package20-check-result.json`.

## Archivos y símbolos consultados

- Instrucciones: `AGENTS.md`, `docs/BRIEFING-MAESTRO.md`, continuidad/S1/contrato/mapa/aceptación, `docs/EQUIPO-Y-SKILLS.md`, `development/server/README.md`.
- Contrato y evidencia: `docs/ADMIN-DATOS-COPIAS-INVENTARIO-12-11-2026.md`, `RESULTADOS-PAQUETE20.md`, diff privado pre-pins y diff Git actual. El diff pre-pins no se usa como artefacto final.
- `tools/build_online_installer20.py`: `read_tree`, `members`, `verify_application`, `verify_service`, `verify_recipe`, `collect`, `write_zip`, `public_demo_files`, `package` y constantes de pins.
- `tools/online-install/assemble20.py`: `safe_name`, `no_reparse`, `verify_core`, `check_url`, `verify_provider`, `acquire`, `require_new_work`, `extract_new`, `assemble`.
- `tools/windows/online-install20/Install-RackClickOnline.ps1`: `Assert-OnlineHostFacts`, `Assert-OnlineFreshHost`, `Test-OnlinePreviousTransport`, `New-OnlineStage`, `Open-OnlineCore`, `Get-OnlineProviders`, `Receive-OnlinePython`, `Receive-OnlineProvider`, `Assert-OnlineProviderCache`, `Assert-OnlineZipRawNames`, `Expand-OnlineZip`, `Set-OnlineChildEnvironment`, `Invoke-OnlineAssembly`, `Assert-OnlineExtractedTree`, `Invoke-OnlineNativeLauncher`, `Invoke-OnlineInstall` y auxiliares de hash/URI/pins.
- `tools/package_offline_bundle.py`: `APPLICATION_PROFILES`, `application_schema`, `operator_names`, `strict_json`, `safe_name`, `validate_names`, `clean_path`, `collect_application`, locks/avisos y selección de runtime.
- `tools/package_server_installer.py`: `checked_edition`, `checked_path`, `safe_name`, `build`; `tools/package_clean_server_installer.py`: `clean_build`.
- `tools/build_server_distribution.py`: `load_profile`, `exact_match`, `build`; `tools/windows/Test-ServerDistribution.ps1`; `tools/windows/RackClick.OfflineBundle.ps1`: perfiles/nombres/esquema.
- Guardias: `tools/windows/server-install/Install-RackClickServer.ps1`, `tools/windows/Install-RackClickOfflineBundle.ps1`, `tools/windows/RackClick.Instance.ps1`; formulario `Show-RackClickInstaller.ps1`: `$fields.bootstrapUser` y construcción de `$plan`.
- Manifiesto, inventario, sumas y79 archivos de la carpeta `.local/distribution48/admin-data-01`; perfiles48 antiguo/nuevo; `.csproj`, `packages.lock.json`, `package-lock.json`, locks de toolchain/servicio/fuentes14, receta20, manualesHTML20, CMD20 y pruebas de empaquetado/default/navegadorWindows como evidencia del productor.
- Fuentes19 preservadas: `tools/build_online_installer19.py`, `tools/online-install/assemble.py`, `tools/windows/online-install/Install-RackClickOnline.ps1`; licencias fijadas del servicio y archivos de licencia frontend.
- Artefactos de la tabla, inventarios `FILES.json`, `PAQUETE.json`, `payload.json`, `bundle.json`, `ENTREGA.json`, sumas exteriores y de Demo50, y salida reconstruida privada del productor.

## No ejecutado y límites

No New20 nativo, instalación limpia, reinicio, servicio/HTTPS instalado, backups operativos instalados, recuperación/restauración completa, ensayo de red real de descargas TLS/redirecciones, autenticación GitHub ni publicación. No se atribuyen a esta revisión las suites del autor, pruebas PostgreSQL/backend/UI de otros revisores ni las pruebas de B19. Los probes modificaron sólo fixtures privados; el único archivo de evidencia asignado al revisor es este informe. La evidencia técnica no es adopción de Wascar ni aumenta la métrica de cierre.
