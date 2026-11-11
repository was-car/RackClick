# I-04.04 · orden y cancelación táctil

25.10.2026. Producto: `InventoryPanel.jsx`, una prop `onTouchCancelCapture` en el contenedor del rack para descartar el arrastre cancelado. Prueba browser: worker `c2_order_browser`; fixture/harness/corrección/ejecuciones: coordinador; revisión distinta: `rack_choices_review`.

## Evidencia de ejecución

- `ORIGINAL-EDGE-PG.json`, `ORIGINAL-FALLO-TACTIL.json`, captura y `InventoryPanel.original.jsx`: FAIL real 18,641 s; cancel→tap provoca revisión y orden inesperados. Entradas sin cambio; todos los procesos propios detenidos.
- `CORREGIDO-INTENTO1-*`: FAIL 20,000 s del esperado del observador, después de superar cancel/flechas/drag/touch. El movimiento no compacta el orden numérico del origen; se corrigió el esperado, no el producto. Fuentes iniciales preservadas en la salida privada identificada en ENTORNO.json.
- `EDGE-PG.json`, `EDGE-BROWSER.json`, `DETALLES-ORDEN.json` y capturas: PASS 26,875 s, PostgreSQL 17.11 y Edge en Windows. Comparación exacta de nueve tablas; cinco operaciones/auditorías; dos roles denegados y persistencia tras reiniciar proceso. Sin SQLite/Docker ni datos reales.
- `REGRESION-MOVIMIENTO.json`, `REGRESION-BROWSER.json`: ejecución nueva PASS 22,813 s de la prueba existente; flechas, movimiento entre racks, conflicto 412, permisos 403/404 y reinicio. No es un log histórico renombrado.
- `BUILD.json`: app nueva; CSS y DLL conservados. Árbol privado derivado del frontend congelado anterior y un único overlay de producto; sin compilación .NET ni integración en instalador.
- `REVISION.md`: focos propios y lectura independiente de fuente, pruebas y recibos; distingue drag DOM, táctil CDP y hardware no ensayado.

## Reproducción

Con los artefactos privados explícitos recogidos en ENTORNO.json, desde la raíz del repositorio:

```powershell
C:/Python312/python.exe -X utf8 -B development/server/tests/test_order_variants_gui.py --dll <DLL-C2> --frontend <frontend-dist> --output <directorio-nuevo-dentro-de-.local>
C:/Python312/python.exe -X utf8 -B development/server/tests/test_inventory_movement_gui.py --dll <DLL-C2> --frontend <frontend-dist> --output <otro-directorio-nuevo>
```

Cada prueba crea su PostgreSQL/base/cuentas ficticios, exige salidas nuevas y detiene su laboratorio. No ejecutarlas contra C, A/B o QA. Las claves se generan en el laboratorio y no son argumentos de esos comandos. Prerrequisitos: toolchain Windows ya preparada por el proyecto, incluida Edge y las dependencias de pg_support. Los artefactos locales exactos no están en un clon limpio; no contar una omisión como PASS ni sustituir el build por otro.

## Límite y cierre

El orden probado es `sortOrder`, no posición U física. La preparación usa SQL y las mutaciones bajo prueba usan GUI. Drag mediante eventos DOM DataTransfer y táctil mediante CDP `isTrusted`; no se ensayó hardware táctil o ratón físico. No se ejecutó Windows reboot ni la candidata completa. El ensayo C sigue cerrado y Wascar informa que apagó su VM; este bloque no consulta ni opera VMware.

QA-123 planned y guías regeneradas; los 122 casos/metadata anteriores se preservan. I-04.04 se acredita técnicamente con su peso fijo 5/14 tras el dictamen independiente; I-04.05–07 permanecen pendientes. No cambia alcance/denominador ni se deduce un porcentaje global del producto. Cierre exacto y hashes en CREDITO-I0404.json/SHA256SUMS.txt. Sin commits, push, paquetes o adopción.

## Verificaciones de cierre

Dictamen independiente conforme: I-04.04 acreditado **5/14**. Cierre del pendiente **5,50→5,86/100** (41/7), 14/280 subpasos, 1/50 resultados. W-02 sigue 0,50/2,50 y C cerrado. El porcentaje global del producto continúa sin recalcular.

`VALIDACIONES.json`: catálogo previo conservado (122 casos y metadatos), QA-123 planned, ambas guías generadas y comprobadas, métrica validada sin cambiar la huella de alcance. `SECRET-SCAN.json`: Gitleaks 8.30.1, cero hallazgos en archivos cambiados/evidencias públicas seleccionados; no acredita todo el historial.

Codebase Memory refrescado con 935 archivos de la copia curada; estado `ready`. Persisten los límites conocidos del parser (69 parciales y un SQL inutilizable), sin asumir un mapa exhaustivo. Claves, dumps y la VM no se indexaron; salidas del helper privadas bajo el directorio de ENTORNO.json. Claude tiene el siguiente lote separado en `docs/MENSAJE-PARA-CLAUDE-C2-SALA-25-10-2026.md`; no se presume que lo esté ejecutando por existir ese mensaje.
