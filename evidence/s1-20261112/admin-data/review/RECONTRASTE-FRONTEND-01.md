# Recontraste independiente F01/F02 · ronda1

12.11.2026. Encargo acotado del coordinador: comprobar las dos correcciones y las regresiones nuevas que puedan introducir. Este documento complementa `REVISION-FRONTEND.md` y conserva sus reproducciones y hashes originales; no transforma sus rojos históricos en verdes.

## Dictamen vigente

**F01: ADDRESSED. F02: ADDRESSED.** Contrato: conforme en las rutas afectadas. Calidad: favorable para estas correcciones, sin hallazgos nuevos en su alcance. Quedan pendientes los ensayos GUI/PostgreSQL integrados y la aceptación de la candidata; no se acredita backend, instalación o QA de Wascar.

**12/12 comprobaciones Edge PASS ejecutadas por este revisor**, exit0, con componentes React e IndexedDB reales y dobles de API sintéticos. Se verificó que los ocho archivos de entrada no cambiaron durante el ensayo. Sin editar producto/pruebas del autor, repetir411, compilar.NET, usar PostgreSQL, VM, commits, push, instalaciones o subagentes.

## Cambios contrastados y resultado

- **F01 · P2 previo, ADDRESSED:** `development/frontend/src/AdminInventoryData.jsx:20` elimina `!ready` sólo del bloqueo externo. Un fallo del journal sin intención conocida mantiene su error e impide iniciar inventario, pero ya permite usar cuentas/grupos después de asentarse la operación y también después de refresh. `ready` sigue siendo obligatorio en `run` y en sus controles. Se montó el `AdminUsers` real, se hizo fallar únicamente el IndexedDB de esta función y se comprobó ausencia de intención y de POST.
- **F02 · P2 previo, ADDRESSED:** `AdminInventoryData.jsx:24` y `:27` concilian el recibo validado y eliminan su intención antes de verificar el archivo en `:32`. Tanto al recuperar como tras POST directo, SHA incorrecto conserva el recibo y el diagnóstico, no muestra descarga, libera Administración y no repite la mutación. No se acepta un recibo incorrectamente vinculado para liberar el journal.

El diff contra el snapshot anterior sólo cambia esos dos puntos del componente. No cambian el adaptador, el contrato ni el mecanismo de escritura durable anterior al POST. Se leyó completo el nuevo `tests/browser-admin-inventory-data-recovery.mjs` y la adenda F01/F02 de `RESULTADOS-FRONTEND.md`, además de los manifiestos/snapshot suministrados en `.local/admin-data-review-fixes-01`.

## Ejecución independiente

Se copió el nuevo guion de recuperación del autor a un destino privado nuevo y se añadieron allí tres sondas propias, sin modificar su archivo fuente. La copia reutiliza las expectativas correctas de F01/F02 y controles de regresión; las tres sondas nuevas prueban efectos adyacentes de la corrección.

| Comprobación | Resultado observado |
| --- | --- |
| F01 | Journal inaccesible sin intención: sólo Datos impide mutar; Administración disponible antes/después de refresh, diagnóstico visible,0POST |
| F02 | Recibo recuperado de copia con SHA erróneo: recibo visible, journal eliminado, sin descarga, Administración liberada,0POST |
| F02-POST | Mismo resultado tras el POST directo; refresh no lo reenvía,1POST total |
| C01 | `notRecorded` conserva intención; cancelación explícita confirmada la retira, sin reenviar importación |
| UNCONFIRMED-demo50 | `notRecorded` y403 mantienen UUID/intención y bloqueo,0POST |
| UNCONFIRMED-restore | `notRecorded` y403 mantienen UUID/digest/intención y bloqueo,0POST |
| C02 | Una respuesta tardía de otro actor no publica el estado |
| C03 | Nombre de archivo malicioso permanece literal, sin HTML ejecutado/localStorage |
| C04 | Seleccionar/calcular hash de archivo no persiste su contenido en IDB |
| **R01 propia** | Recibo de copia con revisión incorrecta conserva intención y bloqueo; no ofrece recibo ni descarga |
| **R02 propia** | Error de limpieza del journal después del commit conserva intención original/recibo y bloqueo;1POST, sin descarga ni reenvío |
| **R03 propia** | Copia con SHA correcto sigue habilitando descarga verificada y libera Administración; journal vacío y1POST |

Comando ejecutado desde `development/frontend`, con Node24.21.0 existente:

```powershell
$env:RACKCLICK_TEST_OUTPUT='C:\RackClick_SVR\.local\admin-data-20261112\recontrast-frontend-01'
& 'C:\RackClick_SVR\.local\node-v24.21.0-win-x64\node.exe' 'C:\RackClick_SVR\.local\admin-data-20261112\recontrast-frontend-01\recontrast-browser.mjs'
```

Edge157.0.4341.46/Windows, React adoptado, esbuild0.25.10 `write:false`. Salidas nuevas en `C:\RackClick_SVR\.local\admin-data-20261112\recontrast-frontend-01\`: `recontrast-browser.mjs`, `independent-browser.log`, `recovery-browser.json`, `frontend-input-hashes.json` y `frontend-nine-hashes.json`. La evidencia original de revisión permanece en `review-frontend` sin sobrescribir.

Se ejecutó también `git diff --check` sobre las dos integraciones, sin errores. Las411PASS y el rojo→verde del implementador se leyeron en su adenda como evidencia atribuida; este revisor no los volvió a ejecutar ni los suma a sus12 comprobaciones.

## Identidades y límites

Conjunto original de ocho archivos ya revisado y conservado: `b2c7412a011b4b7de4ca93482e1b5bc925b7c129a6a880947443ec7e01365a95`.

**Mismos ocho archivos después de la corrección:** `9098f445d7d199e6c2f6e881353c8d61d3177c0a3e3f09163098336d714c66d7`.

**Conjunto de nueve, añadiendo el nuevo guion de recuperación:** `80013811946dde4b9bf25e24816ad03f78af6f161651ba0289f697404e86eae2`.

- `AdminInventoryData.jsx`: `e483661b4aba860a7ec451f02e1da688c3bcc9f244c13825c643fd5a91fadab8`.
- `browser-admin-inventory-data-recovery.mjs`: `7f790022be11f0df65369d905f7518a84e8e44a727a07583c7c13fe097cfd523`.

Método idéntico al primer informe: SHA256 de las líneas `ruta + TAB + hash_bytes + LF` en el orden del manifiesto. Los restantes siete archivos conservan exactamente sus hashes anteriores. El guion concurrente `browser-admin-inventory-restore.mjs`, de otro encargo, queda fuera de estos conjuntos y del recontraste.

No se amplió la auditoría: sin repetir límites32MiB,411pruebas o ensayos PostgreSQL; sin probar revocación SQL, restauración GUI, montaje/topología, descarga instalada, reinstalación o QA. Este recontraste no aumenta el progreso: referencia26,63/100 del cierre restante, sin crear porcentaje global nuevo. Siguiente paso: ensayo integrado del coordinador sobre los bytes finales.
