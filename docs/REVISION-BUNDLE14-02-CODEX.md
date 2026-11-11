# Revisión independiente: bundle 14-02

25.10.2026 · Implementación: Claude. Revisión y ensayos: Codex.

**Favorable para continuar la propagación interna.** Se repitieron **58/58 pruebas, sin fallos, errores ni omisiones**, y se verificó la integridad del ZIP 02, incluida la licencia. Sigue **no instalable**: Stage/runtime/migración/Restore pendientes y dos operadores embebidos anteriores a los scripts externos actuales. No es adopción ni autorización de despliegue en QA.

## Pruebas y hashes contrastados

Los siete SHA256 del informe de Claude coinciden con los archivos; quedan registrados en [BASELINE.json](../evidence/s1-20261025/distribucion14-bundle02-codex/BASELINE.json). Se revisaron el colector, lock 14, lector, guardia de instalación, matriz literal y cambios de expectativas de las pruebas.

Copias nuevas en `.local/bundle14-02-review-20261025-f61fc30d57/tree`: publicación, candidata, frontend, herramientas, fuentes de licencias, cuatro fixtures históricos y tres ZIP. Se repitió la misma selección de cuatro módulos: 18 casos de matriz/aviso, 16 de la suite conciliada, 9 de colector y 15 de distribución. **58 correctos, cero omitidos**, 92,687 segundos; Windows real, PowerShell 5.1 y Python 3.12.3.

La matriz es literal, no deriva los esperados de la función del producto. El digest desconocido conserva su negativo propio. Los cuatro manifiestos históricos y sus archivos siguen comprobándose; el lock anterior conserva SHA `76f39955…`. Los negativos de aviso ausente, alterado, pins cambiados y locks cruzados pasan. La revisión complementaria `bundle02_native_review` fue sólo lectura; no duplicó suites ni editó archivos.

## ZIP 02 verificado sin extracción

| Dato | Resultado propio |
|---|---|
| SHA256 ZIP | `191acd6fc1932f74ad2db9cd5d953ab629dc7a5621bea03df03cad2488155a51` |
| SHA256 `bundle.json` | `4f8d2894c988015e55bf5f84b00451d4e48cda4efbb14f0a8dc7f021213aea25` |
| bundleId recalculado | `431daa46-c0da-55c6-b152-ded6ddc7884a` |
| Entradas / registros | 1.986 /1.985 |
| ZIP, bytes | 117.163.166 |
| Bytes descomprimidos, incluido `bundle.json` | 278.439.817 |
| Payload sin `bundle.json`, bytes | 278.074.042 |

Todos los registros coinciden por tamaño/SHA256, con CRC de lectura; se comprobaron nombres únicos y sin enlaces/cifrado/rutas de escape. Las **42 entradas de aplicación y tres auxiliares** son idénticos a la candidata `2ec91056…`; DLL `f11a689e…`, esquema 14, sin apphost. Aviso `licenses/Otp.NET-LICENSE.txt`: **1.070 bytes**, SHA `0bc32be0ce13330ba88d208548582a641f95b1f66bb19be91f5acc1436c52472`, idéntico a la copia fijada. D14-01/D14-02 permanecen cerrados. Bundle 01 y evidencias anteriores intactos.

## Lector e instalación: alcance exacto

Las pruebas nativas ejecutadas desde el snapshot confirman:

- 02: `bundle_verified`, 1.986 archivos, dos metadatos y un aviso.
- 01: rechazo `layout_counts_invalid` por falta del aviso.
- Bundle real histórico 13: `bundle_verified`, cero metadatos/avisos. Para 9–12 se contrasta la matriz, sin afirmar ZIP reales probados.
- Instalar 02 mediante **el script externo actual**: exit 2, `preflight_schema14_install_not_propagated`; no existe destino ni archivos en el directorio de sondeo. La guardia precede a escritura de estado/contenido y ejecución de componentes. Su posición también cubre Restore por lectura del flujo; no se ejecutó una restauración.

### D14-03 · P2 de entrega: dos operadores embebidos no coinciden

La comparación adicional de los 25 operadores encontró **23 coincidentes y dos diferentes**. Por tanto, la frase del informe que los describe como los archivos actuales necesita esta precisión:

| Operador | SHA256 dentro de 02 | SHA256 del fuente revisado |
|---|---|---|
| `Install-RackClickOfflineBundle.ps1` | `1550828b6457b26493c5c27ae85e068896a058b135c00bc6f4ee372606ea5f64` | `2b94f5c8780598c33e7acbfedf2634555d02548a91e4b8fc3001d96b3bf816cc` |
| `RackClick.OfflineBundle.ps1` | `f440b3731c3faf5c1df15b9246b0a540a633de3d9f20d9240ebadb3bfe7bb5b1` | `34f35a54d698b20e32191453e3505b44c3942f7731d3de56b0011340f697397c` |

El lector embebido no contiene el perfil `2ec91056…`; el instalador embebido no contiene la nueva guardia. Las pruebas externas son válidas, pero **no acreditan esos comportamientos usando los scripts transportados**. Esto no invalida los bytes de aplicación/licencia ni impide continuar Stage; impide declarar cerrado el recorrido del paquete. Al congelar el próximo bundle, comprobar los 25 hashes contra la fuente congelada y ejecutar la verificación desde sus operadores transportados en un área aislada.

### D14-04 · P3: comparación de mayúsculas en auxiliares

En `RackClick.OfflineBundle.ps1:172` y `:176`, `ContainsKey` de hashtables acepta variantes de mayúsculas. Un ensayo propio de **`Assert-OfflineBundleLayout`**, con el manifiesto real y descriptores de entradas sintéticos, acepta `application/Inventory.json` y `licenses/otp.net-license.txt` conservando los hashes. No se fabricó ni verificó un ZIP alterado para este ensayo.

El 02 real usa nombres canónicos correctos; el hallazgo no altera el dictamen de integridad. Ajustar la comparación a claves ordinales/sensibles a mayúsculas y añadir negativos al tocar el lector en la próxima tanda. Es un seguimiento menor de exactitud del contrato, no motivo para reconstruir ahora los 42 archivos.

## Próxima tanda y registro

Claude puede continuar **Stage → runtime → migración 13→14 con grants separados → Restore**, con pruebas de cada camino y conservación de rechazos previos a escritura donde falte soporte. Incorporar D14-03/D14-04 al mismo cierre del recorrido. Agrupar la próxima regeneración del bundle al terminar esa propagación; conservar 02 como evidencia, sin pedir una reconstrucción parcial sólo por esta revisión. Wrapper/CMD e instalación limpia siguen después del recorrido coherente.

Se añade el registro de 02 al perfil sin reemplazar el de 01. Distingue lector externo verificado de lector embebido pendiente. No se editaron los siete archivos de Claude, ZIP, locks, fuentes MFA, QA, VM o servicios; sin staging/commits. Evidencia y perfil previo conservados en [el cierre](../evidence/s1-20261025/distribucion14-bundle02-codex/CIERRE.md). Continuidad/CHANGELOG compartidos se coordinan al cerrar la construcción, según el reparto vigente.

No se ejecutaron MFA/HTTP/C1/PG, Stage, runtime, migración, Restore, instalación completa ni reinicio real. La revisión general de redistribución sigue abierta. Las entradas `.local` estuvieron presentes aquí; las omisiones de un clon limpio no acreditan una entrega. **Avance global aproximado: 78 %, sin incremento.** Se valida licencia, lector externo y regresión de herramientas; recuperación e instalación completas y QA/adopción de Wascar siguen pendientes.
