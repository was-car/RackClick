# C2 · permiso de edición y conciliación I-01.03

## Cambio y resultado

Se añadió `development/frontend/tests/browser-inventory-write-permission.mjs` y la opción cerrada `write-permission` al runner `development/server/tests/test_inventory_operation_status_gui.py`. No hay cambios de producto, compilación ni modificación de la candidata de Claude.

El ensayo retira y devuelve únicamente `inventory.edit` mediante la API administrativa, conservando lectura. Comprueba el diálogo abierto, IndexedDB, permisos efectivos, consulta, cancelación denegada, reintento exacto y recuperación de una confirmación con respuesta perdida. [Matriz y alcance](../../../docs/C2-MATRIZ-RECUPERACION-25-10-2026.md).

## Ejecuciones nuevas en LEAO / Windows

| Ejecución | Resultado | Interpretación |
|---|---|---|
| `permissions-first` | FAIL, 16,44 s | El observador aceptaba un aviso ya existente antes del evento de red esperado. [Resultado](PRIMER-ENSAYO.json), [diagnóstico](OBSERVADOR.json). |
| `permissions-final` | PASS, 21,83 s | Espera explícita de la cancelación 403 y del fin del estado ocupado. Cero cambios de producto entre intentos. [Runner](EDGE-PG.json), [navegador](NAVEGADOR.json). |

Comando, ejecutado con dos salidas privadas nuevas, primero `permissions-first` y después `permissions-final`:

```powershell
C:/Python312/python.exe -X utf8 -B development/server/tests/test_inventory_operation_status_gui.py --dll C:/RackClick_SVR/.local/c2-reduction-20261025-3936b00ab633/app/RackClick.Server.dll --frontend C:/RackClick_SVR/.local/c2-instant-20261025T122334Z-da4af7d2/frontend/dist --output C:/RackClick_SVR/.local/c2-write-permission-20261025T130543Z-29b58781/permissions-final --scenario write-permission
```

La primera versión del script se conserva en el directorio privado como `browser-first.mjs`; su hash está en PRIMER-ENSAYO. La versión final y el runner están fijados en FUENTES y SHA256SUMS. PostgreSQL 17.11 real, clúster nuevo y datos sintéticos; nueve tablas de inventario exactas al terminar, persistencia tras reiniciar el proceso y laboratorio/servidores detenidos. Las capturas [pendiente sin edición](read-without-edit-pending.png) y [confirmación consultada con lectura](readonly-original-committed.png) fueron inspeccionadas por coordinador y revisor. No se ejecutó otra suite Node ni build en esta tanda.

## Revisión y crédito

[Revisión independiente](REVISION-I0103.md): lectura de test, fuentes, resultados, capturas y matriz acumulada; no se presenta como segunda ejecución de Edge/PostgreSQL. Las pruebas de consulta, contexto, elegibilidad y edición rápida son históricas y conservan sus propios resultados/revisiones.

La conciliación permite cerrar técnicamente **I-01.03**, sin exigirle el permiso ajeno de borrado ni la integración/QA que corresponden a I-01.05/06/07. Sus textos y pesos no cambian. [Crédito](CREDITO-I0103.json): +5/14, de 25/7 a 55/14 puntos (**3,93/100** del trabajo restante), 9/280 subpasos y 1/50 resultados completos. I-01 permanece parcial.

## Conservación y próximo paso

Frontend privado `0df395a6…`, CSS `50dd8567…` y DLL C2 `5eb1abcf…` reutilizados. Las 109 fuentes del frontend coinciden byte a byte con la copia de aquel build; ello no prueba recompilación binaria reproducible. InventarioPanel, OperationDialog y adaptador no cambiaron. Catálogo de 117 casos QA, guías y resultados personales conservados; no hay cambio visible que habilitar. [Controles](CONTROLES.json), [fuentes](FUENTES.json), [escaneo](ESCANEO.json), [manifiesto](SHA256SUMS.txt).

Sin commits, push, instalación, servicios reales, cuentas del host, cambios de red, SQL de producto, MFA, paquetes, QA o VM. W-02 conserva crédito cero hasta recibir y revisar las pruebas de las VM de Claude. Próximo: integrar C2 con la candidata coordinada cuando esté disponible y probar los mismos bytes antes de habilitar QA; no reconstruir ni adoptar la edición 07 por este cierre.
