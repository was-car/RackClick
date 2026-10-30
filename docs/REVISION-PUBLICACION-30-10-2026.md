# Revisión independiente de la actualización privada — 30.10.2026

## Dictamen de esta revisión

La actualización **privada de fuentes, documentación y ejemplo sintético seleccionado** puede prepararse para revisión de contenido. Este dictamen todavía no aprueba una selección final ni una publicación: el coordinador la entregará para un contraste acotado.

La candidata de instalación 10 existe, coincide con los hashes de su perfil y tiene documentación de un ensayo Windows anterior. **Esta revisión no da por resuelta su redistribución como activo binario de GitHub**: E-03 sigue abierto y hay condiciones concretas de Microsoft que deben conciliarse. No se ha demostrado una infracción; tampoco se ha demostrado que todas esas condiciones estén satisfechas.

No se ha instalado, compilado ni ejecutado RackClick en esta revisión. No se han usado credenciales ni modificado VM, QA, paquetes históricos, código de producto, commits o remoto.

## Artefacto real comprobado

Lectura directa del ZIP y de sus dos ZIP internos, sin ejecutar ni extraer programas:

| Pieza | Bytes | SHA256 |
|---|---:|---|
| `RackClick-Servidor-10.zip` | 117893199 | `8c74b3b52d8b65f22473408ea9e23820898de9005628d6a0b14d3894cbd89e4c` |
| `Servidor.zip` interno | 117866143 | `990b97c0fc52176c02c1cb2023d46a8516ecc34c20fdfd8c59fb9688f247e85d` |
| `RackClick.zip` interno | 117591714 | `29927a6581fb1229163b75af66dd8d0924be0199b239052a164da096f0aef9ce` |

El exterior tiene 5 entradas; el payload, 117; el bundle, 1987. La medición registra los avisos encontrados por nombre/directorio de licencias, con tamaño y SHA256, en [MEDICIONES-INSTALADOR10.json](../evidence/s1-20261030/github-update-review/MEDICIONES-INSTALADOR10.json). Ese inventario de avisos no sustituye el análisis de todas las obligaciones de cada DLL.

El perfil indica esquema 15, runtime .NET 10.0.12, PostgreSQL 17.11 y VC++ 14.51.36247.0. Registra instalación New, comprobación posterior al reinicio y lectura MFA bajo servicio verificadas anteriormente; revisión visual completa y recuperación portable MFA siguen pendientes. Son datos del perfil y de la evidencia previa, **no pruebas repetidas por este revisor**.

## Hallazgos

### PUB-01 — P1: condiciones de redistribución de VC++ sin acreditar

El bundle transporta `prerequisites/vc_redist.x64.exe`, 18731856 bytes, SHA256 `843068991daaa1f73ad9f6239bce4d0f6a07a51f18c37ea2a867e9beca71295c`, igual al pin. No se encontró un aviso separado de sus términos en esa carpeta.

Microsoft limita la distribución del redistribuible a usuarios de Visual Studio licenciados y a los términos aplicables. Los artefactos revisados no acreditan esa habilitación. Un repositorio privado limita el acceso, pero no demuestra que se satisfagan las condiciones de distribución. Antes de subir el ZIP íntegro hay que documentar la habilitación y las obligaciones aplicables, o preparar otra edición con adquisición directa desde Microsoft por el operador. [Microsoft: redistribución de Visual C++](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files?view=msvc-170).

### PUB-02 — P2: referencia de licencia incoherente en el servicio Windows

`LICENSES/service-host-NOTICE.txt` identifica las dependencias Microsoft como MIT y remite a `dotnet-LICENSE.txt`. Pero el fichero remitido contiene **Microsoft .NET Library**, 9519 bytes, SHA256 `7f6839a61ce892b79c6549e2dc5a81fdbd240a0b260f8881216b45b7fda8b45d`; no contiene la licencia MIT indicada.

La ficha oficial de `Microsoft.Extensions.Hosting.WindowsServices` 10.0.12 declara MIT. Debe preservarse el texto aplicable a ese paquete y sus dependencias, sin confundirlo con el contrato del runtime. Corregirlo requiere una edición nueva con nuevos hashes; no editar el ZIP 10 conservado. [Ficha oficial del paquete](https://www.nuget.org/packages/Microsoft.Extensions.Hosting.WindowsServices/10.0.12).

### PUB-03 — P2: E-03 continúa abierto; tener avisos no cierra todas las condiciones

El runtime conserva su contrato y `ThirdPartyNotices.txt`. El contrato binario permite distribución condicionada de código objeto y contiene requisitos que deben conciliarse con la entrega. El MIT del código fuente de `dotnet/runtime` no debe presentarse como sustituto del contrato transportado. [Licencia de las fuentes .NET 10.0.12](https://github.com/dotnet/runtime/blob/v10.0.12/LICENSE.TXT).

PostgreSQL conserva su licencia y cuatro avisos originales adicionales del paquete Windows. Su licencia permite distribución conservando sus textos; eso no resuelve por sí solo las obligaciones de componentes de terceros seleccionados. [Licencia oficial de PostgreSQL](https://www.postgresql.org/about/licence/).

Npgsql y Otp.NET llevan los textos completos de 903 y 1070 bytes respectivamente, con hashes coincidentes con `offline-bundle14.sources.json`. El frontend conserva cinco archivos de licencias: React, React DOM y tres fuentes. No se volvió a realizar el análisis completo de sus versiones, dependencias transitivas o vulnerabilidades. El propio `licenses/README.txt` mantiene abierta la revisión general. No se acredita E-03 ni se cambia su peso/estado.

### PUB-04 — P2 operativo: el ZIP no cabe como archivo Git normal

El instalador mide aproximadamente 112,43 MiB. GitHub bloquea archivos de más de 100 MiB en Git normal. Si se resuelve su distribución, corresponde un activo de Release privado marcado de prueba, con SHA256 y notas de límites, no incorporarlo como blob del repositorio. La cota por activo de Release es inferior a 2 GiB, por lo que su tamaño sí cabe allí. [Archivos grandes](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github), [Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).

## Entrega usable propuesta

1. Actualizar primero el repositorio privado con una selección revisada de fuentes, locks, scripts, manual y datos sintéticos. Excluir `.local`, credenciales, registros privados, binlogs, bases, sobres MFA, repositorios descargados y evidencias sin sanear.
2. Documentar en la raíz la instalación New y los requisitos Windows, con el estado real de MFA: enrolamiento/login ensayados en laboratorio; gracia de 45 días y exención global según decisión vigente; recuperación portable de factores pendiente. No etiquetar esta candidata como servidor final adoptado.
3. Añadir el ejemplo como JSON sintético revisado y procedimiento explícito de importación. No subir un dump con usuarios, sesiones o secretos del laboratorio como si fuera un ejemplo público.
4. Mantener el instalador 10 privado local mientras se cierran PUB-01/PUB-02 y las condiciones concretas de E-03. La alternativa de descarga oficial de prerrequisitos exige construir y probar una edición nueva; el simple hecho de documentarla no convierte un clon limpio en instalador completo.
5. Si después se autoriza el activo binario, publicar por separado una prerelease privada con sus hashes y manual exactos. Conservar los ZIP anteriores intactos. Los lectores del repositorio podrán acceder a la Release; una etiqueta de prueba no modifica las licencias ni equivale a QA final. [Gestión de Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository).

## Recuperación y límites operativos

El manual de la edición 10 cubre New en Windows limpio, recomienda guardar la entrega y evidencias fuera de la VM y explica la reversión al snapshot por Wascar. Advierte que el dump PostgreSQL no contiene las claves MFA y que Restore con factores se rechaza con `recovery_mfa_envelope_required`. Es un límite explícito; no una recuperación portable ensayada. Esta revisión no ha repetido ni el rollback ni Restore.

## Archivos y símbolos consultados

- `AGENTS.md`, `docs/BRIEFING-MAESTRO.md`, `docs/PLAN-CIERRE-RACKCLICK.json`: tarea `E-03` y sus cinco checkpoints.
- `.local/installer15-current.json` y `.local/github-private-current.json`: solo punteros/metadatos; el segundo no acredita por sí mismo el estado remoto actual.
- `docs/INSTALADOR10-PERFIL.json`, `docs/INSTALADOR10-ENSAYO-MFA.md`, `docs/PASOS-COMPLETOS-INSTALADOR10-WASCAR.md`, `development/offline-bundle14.sources.json`.
- ZIP exterior, payload y bundle identificados arriba; sus avisos y `licenses/README.txt`.
- Git local: árbol con numerosos cambios concurrentes; no se ha incorporado ni revertido ninguno. No se revisaron símbolos funcionales de producto: el alcance es publicación y entrega.

## Pruebas ejecutadas y no ejecutadas

- **Ejecutado:** Git status de lectura; cálculo SHA256/tamaños; apertura de ZIPs anidados; enumeración de avisos y comparación con pins; contraste documental y consulta oficial de términos y límites GitHub.
- **No ejecutado:** build, tests de producto, instalador, scripts del ZIP, procesos de servicio, Windows/PG/MFA/rollback, revisión de vulnerabilidades completa, escaneo exhaustivo de secretos/historial, revisión legal/comercial íntegra o comprobación del remoto. No se ha declarado todo ello cubierto por leer un manifiesto.
- **Métrica:** sin crédito nuevo. El perfil de la edición 10 registra 9,755952/100 de cierre del trabajo pendiente; no es un porcentaje global del producto. La selección final requiere una adenda de revisión independiente.

## Adenda: selección de fuentes y demostración desde GitHub

El coordinador ha retirado los binarios de instalación del alcance de publicación. Esta adenda revisa la selección preparada en un clon aislado, todavía sin commit ni push al medirla. Los hallazgos PUB-01/PUB-02 y E-03 siguen abiertos para el instalador y **no se trasladan como un bloqueo genérico a las fuentes propias**.

**Dictamen estático: favorable a esta selección de fuentes.** No se ha localizado un bloqueo concreto adicional en el helper, el manual o el inventario. La comprobación de ejecución del helper corresponde al coordinador y se registrará separadamente; este revisor no ha arrancado otro laboratorio ni compilado sobre sus salidas.

### Contraste independiente ejecutado

- Los **99 archivos** de `development/server/src` y los **122 archivos** de `development/frontend/src` coinciden byte a byte con los snapshots congelados señalados por `installer15-current.json`; no se publicó por accidente el árbol compartido concurrente de desarrollo.
- Los cuatro cambios de `PUBLICATION-TRANSFORMS.json` coinciden con sus hashes de origen/exportación. El diff sólo sustituye las contraseñas constantes de cuatro fixtures por material generado mediante `RandomNumberGenerator`; no cambia el código de producto.
- `development/examples/demo-original.inventory.json`, 2865746 bytes, coincide con `cbfe4b43a0148299f6f4c24a21dfcb5e21a8efd5ca2d08d552119ac0cd292bd7`. Tiene diez tablas de inventario, incluidos 10 clientes, 68 racks, 311 equipos, 5408 puertos, 623 conexiones y 1246 extremos. No contiene tablas de usuarios, sesiones o MFA. El recorrido estructural no encontró campos con nombres de contraseña, secreto, credencial o clave privada. Es una comprobación limitada del ejemplo canónico, no un escaneo universal de texto libre o historia Git.
- La selección existente al medirla tenía 991 archivos y 22087578 bytes. No había candidatos con extensiones DLL/EXE/PFX/KEY/DUMP/BINLOG/TRX, ni archivos bajo `.local`. El único ZIP era la referencia RC9 adoptada de 5721817 bytes; no el instalador ni un backup de laboratorio.
- `tools/start_demo.py` analiza correctamente con el parser Python. Se revisaron `build`, `validate`, `start`, `load_inventory`, `environment` y el `DemoLab` que reutiliza `pg_support.py`. El helper exige Windows y sesión no elevada, valida el hash del ejemplo, genera credenciales locales, crea un clúster nuevo, usa la identidad PostgreSQL de ejecución separada y detiene sus procesos en `finally`. El servidor y PostgreSQL se configuran para loopback; MFA queda desactivado explícitamente en esa demo.
- El helper restaura con locks y construye las fuentes: no adquiere por sí mismo credenciales remotas ni servicios del Windows instalado. El manual explica primero la herramienta oficial de descarga fijada, el requisito VC++ obtenido de Microsoft, la compilación, el smoke, el acceso privado y la parada. Sus enlaces relativos existen.
- README y manual distinguen demostración desde fuentes, instalación nativa con HTTPS y aceptación final pendiente. No prometen persistencia entre ejecuciones del helper: conservan el clúster anterior, pero crean otro en el siguiente arranque. Tampoco anuncian MFA activo en la demo ni recuperación portable de factores terminada.

### Huellas de esta lectura

| Archivo | SHA256 revisado |
|---|---|
| `tools/start_demo.py` | `020c58dca78d376e748521ae1ab6ee297f292d5ec4c14e9181c8a951499c0790` |
| `docs/INSTALACION-DESDE-GITHUB.md` | `16f0942063d5ffcb75a41c56d074e4ee83f353f93894064b47c289c4bf098be9` |
| `PUBLICATION-TRANSFORMS.json` | `34cbbb926183e7c0c94cf07d358d4c22a8c186beda573e1f35b0ba619fb3c051` |

Más medidas y el hash del README revisado: [REVISION-SELECCION-FUENTE.json](../evidence/s1-20261030/github-update-review/REVISION-SELECCION-FUENTE.json). Cualquier corrección posterior del helper requiere comprobar el nuevo diff/hash; no se atribuye automáticamente a esta lectura.

**Límites restantes de esta adenda:** no se ha ejecutado la instalación de prerrequisitos en un Windows sin herramientas, ni smoke, navegador, test de producto, escaneo completo de secretos/historial o CI. La publicación de fuentes no cierra los pendientes de recuperación, instalación, paridad o QA y no añade puntos por sí misma.

### Ejecución del coordinador, separada de la revisión

Después de la lectura anterior, el coordinador informó de estas ejecuciones en el clon seleccionado, con `start_demo.py` sin cambios respecto al hash revisado:

- Restauración bloqueada y publicación de servidor/cargador, más `Build-Frontend.ps1`: terminadas correctamente. Binlogs privados, fuera de la selección.
- Smoke PostgreSQL real: salida 0, `success=true`, `customers=10`, `ports=5408`, `frontend=served`, `mfaEnabled=false`, `inventoryCommitted=true`. El laboratorio detuvo sus procesos y conservó sus archivos. El campo `runtimeDmlOnly` del recibo es coherente con la identidad/grants del fixture leído; no sustituye una prueba independiente de todos los permisos.
- Seis pruebas nuevas de `test_source_demo.py`: pasaron. Este revisor leyó sus casos (hash/tablas del seed, aislamiento del entorno y rechazos de salidas modificadas/ausentes/extras) pero no volvió a ejecutarlos.
- El generador maestro pasó `--check` tras incorporar los documentos de contexto necesarios, sin modificar el índice de cierre.

Estas son **pruebas del implementador comunicadas al revisor**, no ejecuciones propias del revisor. La suite completa de calidad seguía ejecutándose al comunicar esos resultados; no se cuenta como pasada ni se convierten sus omisiones Docker/navegador en Pass.

**Dictamen de la adenda:** favorable a incorporar y publicar la selección de **fuentes, ejemplo sintético y documentación** en el repositorio privado autorizado, conservando la exclusión de instaladores binarios, material de laboratorio y secretos. No se ha encontrado un bloqueo concreto al recorrido de demo revisado. La aceptación productiva, E-03, la recuperación MFA portable y la QA final continúan pendientes.

### Precisión posterior: seis transformaciones de fixtures

El escaneo del coordinador encontró dos constantes sintéticas adicionales en `MfaActiveKeyTests.cs` y `MfaWindowsHostHttpTests.cs`. Este revisor contrastó ambas con sus snapshots: cada diff sustituye solamente la constante de contraseña por `RandomNumberGenerator.GetBytes(24)` y no cambia aserciones ni producto. Los seis pares de hashes origen/exportación del manifiesto son correctos. README ya describe **seis**, y `start_demo.py` conserva el hash revisado.

La nueva huella de `PUBLICATION-TRANSFORMS.json` es `8bd9db6fd75696f320ebe1971c9a93c58e2c5ff5395c11a386622c910c0066f8`; la de README, `f1c0c3529e2ceacc2bf2796c07a79a39365a417a76d5818d827f0347eafef763`. La tabla anterior conserva la medición previa de cuatro cambios; la presente precisión la actualiza sin eliminar su historia. Evidencia: [REVISION-SEIS-TRANSFORMACIONES.json](../evidence/s1-20261030/github-update-review/REVISION-SEIS-TRANSFORMACIONES.json).

También se leyó el listado de 21 rutas de contexto incorporadas para el generador maestro, incluidas dos matrices JSON de paridad. Se identificaron las rutas, sin afirmar una revisión íntegra nueva del contenido de todos esos documentos.

El coordinador comunicó que interrumpió el primer intento de regresión de su propio proceso porque el lanzador privado heredaba `MfaKeyStore__Enabled=false` de la demo y anulaba la configuración de un negativo de arranque. Conservó ese intento y corrigió sólo el entorno de su lanzador. La repetición seguía en curso al registrar esta precisión: no se declara completa ni se atribuye ese incidente a un fallo corregido de producto. Este revisor no repitió suites. El dictamen favorable de fuentes se mantiene.

### Resultado de servidor y correcciones de portabilidad de pruebas frontend

El coordinador comunicó después **378 Pass, 0 Fail y 3 omitidas** en la regresión final del servidor: una requiere Docker y dos GUI requieren navegador no configurado. El arnés de dominio terminó con salida 0. Se registran como ejecuciones del implementador; este revisor no las repitió ni cuenta las omisiones como Pass.

La primera batería frontend dio 798 Pass y 3 Fail. Se revisaron las tres correcciones antes de su repetición, sin cambiar producto:

1. **Catálogo y finales de línea.** El JSON publicado vuelve a los bytes LF canónicos del workspace, SHA256 `764aa2d016057bc8232f86d4b82a5ef7c156667e906460d1b6bdef51ffcfcd92`, sin CRLF. `.gitattributes` marca `/development/**`, `/tools/**` y `/reference/**` como `-text`. `git check-attr` confirma texto desactivado para catálogo/helper/referencia incluso con `core.autocrlf=true`; no se eliminó la prueba de integridad ni se cambió su pin para tolerar otros bytes. No equivale a haber repetido todos los comandos en un clon nuevo sin herramientas.
2. **Diez capacidades reales.** `Domain/Infrastructure.cs` ya incluye `TemplatesPublish` y el adaptador tiene diez capacidades. `inventory-reports.test.mjs` pasa de esperar nueve a comparar literalmente las diez, con unicidad y etiquetas no vacías en las posiciones ocho y nueve. El diff conserva el resto de las verificaciones; corrige una expectativa desfasada en vez de relajarla a un rango abierto.
3. **Referencia histórica autocontenida.** El test de colores deja de ejecutar un Git privado bajo `.local` contra un commit que no existe necesariamente en otro clon. Lee `reference/historical/UserPortColors-port969.jsx`, 9008 bytes, y comprueba SHA256 `cddc4ed099943c0b5cfa1e5c51481885e1eec7f32b375239a9a48ce50a70ca3e` antes de la misma comparación de evolución. Este revisor confirmó los bytes contra `git show eb97a85:development/frontend/src/UserPortColors.jsx`. El diff contra el test congelado cambia sólo la adquisición/verificación de esa entrada, no la aserción de evolución.

Se volvió a contrastar el producto: **99 archivos del servidor y 122 del frontend siguen idénticos** a los snapshots congelados, sin diferencias. Evidencia y hashes de los cinco archivos pertinentes: [REVISION-PORTABILIDAD-FRONTEND.json](../evidence/s1-20261030/github-update-review/REVISION-PORTABILIDAD-FRONTEND.json).

Las tres soluciones son adecuadas y no introducen un bloqueo a la publicación de fuentes. La nueva ejecución frontend y la del cargador seguían pendientes/en curso al registrar esta revisión; no se declara aún su resultado final. Continúan intactas las limitaciones de instaladores binarios, E-03, MFA portable y aceptación productiva.
