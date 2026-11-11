# Revisión independiente — I-04.04 orden y cancelación táctil

25.10.2026. Revisión distinta de implementación y autoría de tests. Único archivo escrito por el revisor: este informe. Estado Git inspeccionado, cambios ajenos conservados. Sin edición de producto/tests, builds, suites generales, DB, navegador, VM, QA ni acceso a artefactos privados/credenciales. Se usaron únicamente los ejecutables Node/Python ya autorizados y fuentes/recibos públicos.

## Dictamen y gravedad

**Conforme acreditar I-04.04 (`5/14`) en su alcance técnico comprobado.** Texto exacto: «Flechas/drag/táctil según controles ofrecidos; orden documental y local/cross sin inventar posiciónU.» Sin bloqueantes nuevos en el cambio final. Esta recomendación no acredita uso con ratón físico, hardware táctil ni paridad/accesibilidad global; no modifica ledger ni afirma porcentaje global.

**P2 de producto anterior, corregido:** después de arrastrar con touchStart/touchMove y touchCancel, la referencia retenía `source/target`. Un toque posterior fuera del asa terminaba ese arrastre antiguo y enviaba un reorder accidental. El recibo original registra **FAIL 18,641 s**, cambio de orden a/b y revisión 1→2 en el assert «Ordinary tap after cancellation cannot commit a retained drag». Las entradas permanecieron intactas y laboratorio/servidores detenidos. Es un fallo del comportamiento real, no un import ausente ni un test que omite los controles.

**Fallo intermedio del observador, conservado y corregido:** `CORREGIDO-INTENTO1-*` registra **FAIL 20,0 s** porque esperaba compactar `a.sortOrder` a 0 al mover `b`. Ya pasaban cancelación, flechas, DOM drag y CDP touch. `InventoryDevices.Device`/`NextOrder` sólo asignan al equipo movido el siguiente orden del destino; no compactan otros equipos del origen. El test final exige `a=1`, `b→rackB/0`, `c=1`. No se modificó el backend para satisfacer la expectativa incorrecta ni se inventó posiciónU.

## Archivos y símbolos consultados

- `docs/PLAN-CIERRE-RACKCLICK.json`: criterio I-04.04 y fracción existente.
- `InventoryPanel.original.jsx` público y `development/frontend/src/InventoryPanel.jsx`: contenedor `div.ir-layout`, `touchDrag`, callbacks `onTouchDragStart/Move/End`, `reorder`, `drop`, `moveDevice`.
- `development/frontend/generated/rc9.jsx`: `IntegratedPhysicalRack`; fila `draggable`, `DataTransfer`, bloqueo de inicio desde `[data-vport]`, asa `.ir-drag`, flechas y terminación táctil ofrecidas por el producto.
- `development/server/src/RackClick.Server/InventoryDevices.cs`: `Device`, `NextOrder`, validación del conjunto de UUID para `device.reorder` y actualización de ubicación al mover.
- `development/frontend/tests/browser-order-variants.mjs`: `drag`, `touch`, `noop`, `changes`, `committed`, payloads/ETags, recargas, cancelaciones y observación de eventos.
- `development/server/tests/test_order_variants_gui.py`: `assert_order_sql`, `inputs`, `main`, conteos, permisos y reinicio; comparador completo de nueve tablas derivado de `before`, sin copiar atributos de `after`.
- Recibos públicos original, intermedio, final, detalles, build y regresión citados abajo. No se abrieron capturas ni artefactos privados.

## Cambio y pruebas propias ejecutadas

**Foco Node/esbuild en memoria: PASS, exit 0.** PowerShell here-string enviado por stdin a Node v24.21.0 con `--input-type=module`; esbuild 0.25.10 existente. Sin crear fixture adicional por el límite de propiedad del encargo.

Se comprobó igualdad byte a byte entre el JSX actual y la copia original después de retirar exclusivamente:

```jsx
 onTouchCancelCapture={()=>{touchDrag.current=null}}
```

No se cambian otros controles, guardas, estilos, comandos ni callbacks de esos archivos. El foco transforma el carrier JSX real de cada versión con un sustituto mínimo de `React.createElement` y evalúa el `onTouchDragEnd` real. Verifica:

```json
{"sourceOnlyExpectedProp":true,"originalRetainedEndDrops":true,"cancelThenEndDrops":false,"validEndStillDrops":true,"duplicateCancelSafe":true,"result":"PASS"}
```

Es una comprobación pura del callback, no una simulación que se presente como prueba de propagación React/DOM. La propagación real capture queda cubierta por el ensayo Edge del coordinador.

**Sensibilidad SQL propia en memoria: 3/3 PASS, exit 0, 0,004 s.** PowerShell here-string enviado a `C:/Python312/python.exe -B -`. Se extrae por AST únicamente `assert_order_sql`, con `json` y un canonicalizador puro; no se importan dependencias ni se arranca el runner. Matriz artificial propia de nueve tablas, con jerarquía no vacía, dos racks/tres equipos/grupos/puertos/cable/extremos y metadatos literales.

1. El caso exacto a1/bB0/cB1 pasa; todos los argumentos permanecen iguales.
2. Rechaza cambios individuales de sizeU, nombre, UUID, metadatos, prefijo de grupo, power_role de puerto y la compactación inventada a0.
3. Rechaza color de cable alterado, UUID u ordinal de extremo alterado y una fila extra de rack.

Salida real: `Ran 3 tests in 0.004s / OK`. Los guiones se ejecutaron en memoria; este informe conserva las condiciones y resultados, sin añadir archivos fuera de su propiedad.

## Integración contrastada, ejecutada por el coordinador

- `ORIGINAL-EDGE-PG.json`/`ORIGINAL-FALLO-TACTIL.json`: reproducción negativa real descrita arriba; frontend original `c357d447…0990e`, no un árbol mutilado para forzar error.
- `CORREGIDO-INTENTO1-EDGE-PG.json`/`CORREGIDO-INTENTO1-EXPECTATIVA-ORDEN.json`: fallo conservado del observador, con cuatro focos previos PASS y entradas intactas.
- `EDGE-PG.json`: **PASS 26,875 s**, PostgreSQL 17.11, browser exit 0; nueve tablas exactas, **5 operaciones y 5 auditorías: 4 reorder + 1 move**. Dos usuarios sin permiso de edición en ese ámbito reciben 403 y lectura externa 404 sin cambiar `atomic_state`. Reinicio del proceso servidor conserva snapshot/ETag en ambas cuentas y las nueve tablas; lecturas/reinicio no añaden revisión/operación/auditoría. `inputsUnchanged`, `labStopped`, `serversStopped`, `serverRestartPersistence` y `atomicReadRestartUnchanged` verdaderos.
- `EDGE-BROWSER.json`: seis focos PASS, `jsExceptions=[]`. Incluye cancel→toque sin POST, flechas de límite, puerto no arrastrable, drop sobre sí mismo, arrastre válido, traslado cross y cancelación de traslado, órdenes/documentación/payloads exactos y dos sesiones con recarga.
- `DETALLES-ORDEN.json`: DOM `dragstart/dragenter/dragover/drop/dragend` usa `DataTransfer` poblado por el handler del producto. CDP entrega touchstart/move/cancel/end con `isTrusted=true` al asa real; el test no escribe `touchDrag` ni llama directamente `drop`. Declara expresamente drag DOM, no ratón físico, y emulación CDP, no pantalla táctil física.
- `BUILD.json`: sólo overlay `InventoryPanel.jsx`; app `04f4ef02…81101`, CSS `50dd8567…67ec3` y DLL `5eb1abcf…97585`. Comparé los hashes CSS/DLL de recibos original/final: iguales. No build ni modificación RC9 adoptada por este revisor; sin paquete/selección QA nuevos en el recibo.
- `REGRESION-MOVIMIENTO.json`/`REGRESION-BROWSER.json`: **PASS 22,813 s**, PG17.11; conflicto 412 conserva borrador/destino y snapshot; movimiento/flechas local/cross, permisos 403/404, recarga de dos actores y persistencia tras reinicio. Entradas intactas y laboratorio/servidores detenidos. Ejecutada por el coordinador, no repetida por el revisor.

## Huellas y límites

| Fuente | SHA256 |
| --- | --- |
| InventoryPanel.original.jsx | `03cc6de0ee9b1e9881b2761801c8cb0025817804b4b382c3bbf96cac03579ebd` |
| InventoryPanel.jsx final | `aca789e7576c10e69f40929add0638afc932d9426b4d76968e4ec6819144146b` |
| browser-order-variants.mjs | `a67b521968a0921cb03fa87c0f800085b2a81b6361f2159947f6a5e61f613488` |
| test_order_variants_gui.py | `02c1f15f887d17a54218ea25eb2ae5b82566a34e76027940253df7084d427a45` |

La evidencia distingue controles DOM/CDP de hardware: no se probaron ratón físico, touchscreen real, multitouch, matriz de dispositivos/gestos o reboot Windows. Tampoco teclado/lector de pantalla, contraste/zoom/responsive, inspección de píxeles/capturas, QA de Wascar ni candidata final. Las tablas site/building/room están vacías en el laboratorio nativo; mi matriz pura contiene datos de jerarquía. El alcance acredita orden documental/ubicación por UUID y conserva cables; no acredita posiciónU física persistida ni toda la paridad RC9.
