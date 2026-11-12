# Recontraste independiente backend · ronda1

12.11.2026. Complementa `REVISION-BACKEND.md`; sus rojos y archivos privados permanecen intactos. Encargo acotado B01/B02 y bordes de las correcciones, sobre el snapshot NUEVO `worktree/.local/admin-data-gui/server-02`; `server-01` se conserva.

## Dictamen

**B01: ADDRESSED. B02: ADDRESSED. Especificación y calidad favorables en el alcance corregido.** No aparecen defectos nuevos en las tres sondas propias. No es aprobación de GUI, instalación, MFA de producción o QA/adopción de Wascar.

Se ejecutó PostgreSQL17.11/HTTP-Kestrel real sobre un clúster nuevo con tres bases nuevas y roles independientes. **3/3 sondas PASS**, con varios negativos/positivos de frontera por sonda. DLL y nueve archivos producto/pruebas sin cambios durante la ejecución. El clúster y sus servidores quedaron detenidos. Sin modificar producto, fixtures del autor, SQL, dependencias, VM o instalaciones; sin recompilar.NET, repetir18/Quality, commits/push o subagentes.

## Correcciones leídas

- `InventoryDataAdministrationArchive.cs:23`, `:33`: `InventoryDataMaximumRevision=9007199254740991` y `DataRevision` rechazan fuera de1…MAX_SAFE. El control se aplica a preview, restore y formación de copias. El consumidor existente del JSON no cambia.
- `InventoryDataAdministrationArchive.cs:40`: `DataRowNullability` valida las filas persistidas con una lista interna de columnas SQL anulables y se llama al construir los conjuntos. No usa los defaults de comandos vivos para aceptar null obligatorio. El null dentro de propiedades libres queda fuera de ese control de columnas, como corresponde.
- `InventoryDataAdministration.cs:165`: la nueva importación rechaza `inventory_revision_exhausted` si el siguiente incremento de Systemhaus no sería seguro; el replay se resuelve antes de esa guardia. Backup no incrementa. No se alteran mutaciones históricas ajenas al lote ni DDL.
- Leídos los siete casos nuevos de límites y la matriz de46campos obligatorios en `InventoryDataAdministrationTests`, además de `RESULTADOS-BACKEND.md` y `REVISION-R1-BACKEND.json`. Los otros seis archivos de su conjunto conservan sus bytes.

## Ejecución propia y efectos observados

Guion NUEVO privado `C:\RackClick_SVR\.local\admin-data-20261112\recontrast-backend-01\backend-recontrast.py`. Reutiliza sólo el prefijo de helpers del guion anterior, sustituyendo en su copia el destino y el pin/DLL antes de ejecutarlo; no ejecuta ni sobrescribe la batería roja anterior.

| Sonda | Resultado real |
| --- | --- |
| B01 | `poe:null`: preview422 y restore422;0clientes/0recibos, estado `notRecorded`, seguridad comparada sin cambios |
| B01, control adyacente | `poe:false`, watts/color nulos y null dentro de propiedades: preview200/restore200/backup200; copia igual al archivo de entrada |
| B01, borde de incremento | Systemhaus MAX_SAFE-1 avanza aMAX_SAFE; replay de la misma restauración recupera el recibo original antes de la guardia de agotamiento |
| B02 | Revisión2^53 rechazada en preview y restore con422, sin filas ni recibos |
| B02, borde válido | Revisión MAX_SAFE aceptada; el JSON real de GETclientes es aceptado por `RackClickApi.customers` sin modificarlo |
| R01 | Systemhaus ya enMAX_SAFE: restore409/`inventory_revision_exhausted`,0clientes/0recibos/revisión intacta; backup sigue devolviendo200 sin incrementar |

Las tres sondas compararon las mismas tablas de seguridad del primer informe: usuarios, sesiones, miembros, concesiones y factores. No había un factor criptográfico activo propio; `MfaKeyStore__Enabled=false` sólo en este laboratorio. Las claves aleatorias/conexiones permanecen en entorno/archivos privados con permisos restringidos. No se accedió a credenciales ni instalaciones VM.

Comando: `C:\Python312\python.exe -B C:\RackClick_SVR\.local\admin-data-20261112\recontrast-backend-01\backend-recontrast.py`, desde el worktree, con salida a su `execution.log`. Exit0. Resultado completo `backend-recontrast.json`, manifiesto `input-hashes.json`, respuesta sintética no secreta del listado real `safe-revision-customer-list.json` y control consumidor `safe-revision-adapter.log`, todos privados en ese destino nuevo.

## Identidad y límites

**DLL ensayada:** `768df75ea0db5afa349d4d8a4191856cd83b29a19b35ab4d1541b3b5f3f177bf`.

**Conjunto actual de nueve archivos producto/pruebas:** `778b5e989cdf9acec8fc66281ed86d55ce6b8a8af776c5adf15f85d2b2db3289`.

Mismo orden/método del primer informe: SHA256 de `ruta + TAB + hash_bytes + LF`, manifiesto privado completo. El conjunto previo `1e013276…` y la DLL a80 permanecen identificados en el informe original. Este recontraste corresponde a768 y no convierte el Quality anterior en una ejecución contra768.

No ejecutado: los18casos focales del implementador, Quality, matrices físicas completas, carreras/revocación, GUI/instalación, recuperación SQL/Windows o MFA de producción. La adenda del autor declara18/18 focales; se leyó como evidencia suya, sin sumarla a nuestras tres sondas. Se mantiene la distinción de107SKIP/8exclusiones del Quality previo y no se amplía trabajo sobre código intacto.

Progreso sin incremento:26,63/100 del cierre restante como referencia, sin porcentaje global nuevo. Próximo paso: ensayo integrado del coordinador con los bytes finales.
