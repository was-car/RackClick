# Revisión independiente de la candidata 08

25.10.2026. **Conforme con la receta y la identidad de los cuatro paquetes internos revisados, tras corregir la guarda de ruta del reproductor.** No encontré cambios incidentales en la aplicación/servicio ni fuera de las sustituciones verificadas. No significa instalación Windows aprobada, cierre de C2/MFA, derechos de redistribución resueltos ni adopción del servidor.

## Identidades

Entrega revisada: `.local/instalador-08-codex/entrega/`.

| Archivo | SHA256 |
|---|---|
| `RackClick-Bundle-M3-14-08.zip` | `a26856cb2bf3b9ed76384ebfe40fcc1587075708d3383e6b515246bfebb6da6f` |
| `RackClick-Servidor-08-payload.zip` | `f1988ba75ef8f278b5d64b81d7a8fb02d99a3be451e8ce70e2f97a4452538da4` |
| `RackClick-Servidor-08.zip` | `2855898161ed94ff36fba73b11ac2bb02e9b4d9702e4af6976e946a7307561ae` |
| `RackClick-Cambiar-IP-08.zip` | `c070fa06cf40808e0d43197da743bed52c00361ce05f45549ff6498b3a36c6c8` |

La aplicación conserva el manifiesto `e9c58c0c67500afc09c1ac979a7433830c96f94c2a2e4501d81286796d65d74d`. La receta inicial leída fue `.local/build_installer08_codex.py`, hash `6b45bc24979b7605b689f0c9466e9a45791ba19dce5024de26a93a3f5249bbc0`.

## Receta y contenido comprobados

- La receta valida bundle/payload 07 y los manifiestos congelados S4/S5 antes de crear su salida. Extrae aplicación y operadores de esos archivos, y usa siete overlays con hashes de sus revisiones independientes: tres del diagnóstico de recuperación y cuatro del estado postboot. No enumera el árbol actual de C#/MFA/C2 ni ejecuta compilación/instalación. Los dos archivos vendor enlazados se entregan como entradas de lectura al colector; no se escriben sus bytes en la receta.
- Mi auditoría verificó **seis pins de entrega, cuatro entradas históricas y 77 archivos de fuentes de la copia**. Los siete overlays coinciden con los hashes aprobados anteriormente. El helper R3 de Claude no forma parte de estos cambios.
- Leí todos los miembros de los cuatro ZIP 07 y 08, comprobando CRC al leer, ausencia de nombres duplicados/rutas peligrosas y hashes/tamaños de los manifiestos. Inventarios 08: **1986 / 114 / 5 / 65** miembros para bundle/payload/envoltorio/IP.
- **45 archivos de aplicación, incluidos tres metadatos, son idénticos byte a byte a 07; 38 del servicio también.** El bundle conserva 25 operadores: sólo cambia `operators/New-RackClickRecoveredInstance.ps1` al hash revisado `65b44ccc…88a12`, además del manifiesto del bundle. Dependencias, licencias, manuales y el resto de miembros del bundle permanecen iguales.
- Los doce miembros modificados del payload son exactamente el bundle interno, siete overlays, Setup/Prerequisite por el nuevo pin, el texto de edición y payload.json. Prepare lleva sus dos reemplazos de pin sobre los bytes revisados; Setup y Prerequisite, uno cada uno. Comparé la transformación exacta, no sólo nombres. El envoltorio cambia únicamente Servidor.zip, el pin de INICIAR y PAQUETE.json.
- En el companion IP, los operadores copiados coinciden con los del payload 08. El motor sólo cambia el pin de payload.json; lanzador/orquestador reciben sus pins correspondientes, y LEEME cambia edición. Comprobé esos cuatro miembros mediante sustituciones exactas respecto a 07, las sumas del paquete y el payload.json idéntico al del payload. Los tres scripts de red quedan fuera del payload para evitar un hash autorreferente; los cambios de pin posteriores se aplican a la copia y al companion.
- Los hashes del envoltorio/IP históricos 07 siguen intactos. Las etiquetas H3 antiguas 05 que el coordinador decidió preservar no se corrigen ni se presentan aquí como nuevas. No amplié esta comprobación a una auditoría legal o funcional del contenido heredado.

## Hallazgo de la receta reproductora y corrección

Al añadir `--output-root`, la versión `7178004d94b97d3115b7e31582e80dfa16092b0b3dacb275b00981c95c33b7a6` comprobaba pertenencia léxica tras `.absolute()`. Un destino `C:/RackClick_SVR/.local/../../OutsideLocal-New08` superaba esa condición aunque su ubicación resuelta era `C:/OutsideLocal-New08`. No ejecuté main ni creé tal destino. Los paquetes originales y la segunda construcción con ruta legítima no quedan invalidados por ese contraejemplo.

El coordinador corrigió `checked`: rechaza `..`, inspecciona ancestros mediante lstat y rechaza reparse incluso colgante, valida la pertenencia resuelta y devuelve ruta resuelta. **Receta final revisada:** `9e18832daeb24724eec7797c9d1e4f695f26b902a3d4d8f48726bcacd77f37dc`. Importé las dos recetas sin main y ejecuté sólo esa función: el original reproduce la aceptación, el final rechaza `path_outside_fixed_root`; un destino normal propio queda aceptado sin crearlo. El hallazgo queda cerrado en ese alcance. No se modificaron los 77 archivos ni los ZIP por esta corrección privada de la receta.

## Ejecución propia y atribución

Fixtures propios: `.local/installer08-review-peer-3a6cb9618c314d55a13f3f99af2abebf/`. Comandos Python con `C:/Python312/python.exe -I -B`:

| Observador / resultado | SHA256 del resultado |
|---|---|
| `audit08.py` → `result.json`, exit 0 | `5cc8e650f53409a04d962ba048eb44fafdb5a34ba2096bb12d1562c1a4b73032` |
| `companion_exact.py` → `companion-result.json`, exit 0 | `d510cce3d5ac0820da0bebb9238f1375f519d83418d6ad700eebf082aa993e1b` |
| `path_guard.py` → `path-guard-result.json`, exit 0 | `0cd5d570d31558f312ceaf2e84b78ff3fcf4a94a534eaaa57cbfeecf7ef3f725` |

Observadores respectivos: `aba1f1afd10dc9112fb267bdec5e85c43a8217802fc2a2f40472fcc18acaa7e5`, `2aad45cd0eb4f5ee72653330497d6730e03de6874c397d7f881a196976e24ac7`, `6afcce5eec60fd5814b4a65fe1ca66ed022352de78d78aaf02da8d4d9260fe04`.

Comparé además los tres ZIP externos originales con las salidas repetidas del coordinador: payload/envoltorio/IP son idénticos. **No reconstruí esos paquetes.** La segunda construcción completa, incluido bundle, todavía no se acredita por este apartado.

Leí los dos resultados nativos del coordinador, no los ejecuté: `native-bundle.stdout.json` (`6a440cbf99d9d88ffd5040a1db2a9c9076285321a07cc69d94623953cec22f53`) informa bundle_verified, 1986 archivos, esquema 14 y manifiesto e9c58; `native-wrong-hash.stdout.json` (`8f7db1e6eac36d15373bfa95cabe13fbc9080de4cc086ef8be4858712b3c9f7c`) informa archive_hash_mismatch/exit 2 con el pin equivocado. No repetí el lector ni las nueve inspecciones del autor comunicadas.

Una consulta preliminar de estructura JSON asumió lista donde bundle.files es diccionario; falló sin modificar archivos y se corrigió sólo esa consulta. No se contabiliza como prueba del producto. Las auditorías anteriores finalizaron completas con sus resultados propios.

Única escritura pública: este informe. No ejecuté instalador, INICIAR/VerifyOnly, procesos de producto, SQL, GUI, servicios, cuentas, privilegios ni acciones Windows/VMware. Sin modificaciones de fuentes de producto, paquetes, QA, ledger, commits o publicación. La candidata sigue siendo interna: requiere recorrido revisado y ensayo limpio realizado por Wascar; esta revisión no cierra R3b ni la auditoría C2 pendiente.

## Adenda · reconstrucción completa posterior

Leí `REPRODUCIBILIDAD.json`, SHA256 `673cd2bc1ec072b378dbbb39720051ab6bd677353fbf9be4acdbe8d06c8ed8feb`. El coordinador registra dos construcciones completas en raíces independientes, `.local/instalador-08-codex` y `.local/instalador-08-codex-repro`: los cuatro archivos de entrega conservan exactamente los hashes de la tabla inicial. La igualdad se refiere a esos ZIP; las rutas absolutas de los recibos/fuentes de cada ejecución pueden diferir.

**Comprobación propia adicional de sólo lectura:** medí el SHA256 del bundle en ambas entregas; los dos dan `a26856cb2bf3b9ed76384ebfe40fcc1587075708d3383e6b515246bfebb6da6f`, coincidiendo con la prueba publicada. La copia pública de la receta `CONSTRUIR-08.py` conserva el hash final corregido `9e18832daeb24724eec7797c9d1e4f695f26b902a3d4d8f48726bcacd77f37dc`.

No ejecuté ninguna construcción. La segunda ejecución y su finalización pertenecen al coordinador. El recibo `BUILD-08.json` permanece correctamente como evidencia de la primera etapa con `bundleRepeated=false`; esta prueba posterior añade la segunda construcción completa, sin reescribir el dato histórico. La guarda se corrigió después de iniciar el segundo build con un destino legítimo dentro de `.local`, sin cambiar los archivos de aplicación/operadores ni los ZIP.

Queda acreditada en ese entorno la igualdad de los cuatro paquetes reconstruidos. Sigue siendo candidata interna: no acredita clon limpio autosuficiente, instalación en Windows Server, R3c, custodia D2, revisión legal, auditoría C2 ni adopción. Se mantiene la ausencia de acciones de producto/VM por este revisor. La única escritura de esta adenda es el presente archivo.
