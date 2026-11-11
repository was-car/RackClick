# C2 · instant · cierre de tanda

25.10.2026, Windows/LEAO. Coordinador implementa; [revisor distinto](REVISION.md) comprueba cinco focos propios. [Alcance](../../../docs/C2-EDICIONES-RAPIDAS-25-10-2026.md).

Único archivo de producto modificado: `InventoryPanel.jsx`. Origen/contexto vivo para `instant`, `refreshPending`, `refresh` y `committed`; guardas tras esperas y en la continuación de reconexión. Comprobación de revisión/autoridad antes del dispatch; mutex síncrono e intención pendiente retenida hasta resolver el journal. Preparación dentro del try, limpieza de terminal sólo para su propietario y epoch en error de lectura. No se elimina una intención incierta al cambiar de vista. El propio pendiente no se usa como impedimento del primer envío.

Sin cambios en OperationDialog, backend, MFA, SQL, instalador, W-02 o paquetes. Sin .NET, dependencias, servicios, bases existentes, QA/VM, commits o publicación. Pruebas PostgreSQL exclusivamente en clusters nuevos con datos y secretos sintéticos. El trabajo en dos VM comunicado por Wascar no se convierte en una ejecución de esta evidencia.

## Ejecuciones nuevas del coordinador

| Ejecución | Resultado |
|---|---|
| Primeros9casos sobre fuente inicial |1PASS/8FAIL esperados,exit1. [Fuente preservada](InventoryPanel.before-instant.fixture.txt). |
| Primera corrección |9/9PASS. |
| Décimo caso sobre fuente intermedia |1FAIL esperado: dos envíos después de respuesta incierta y antes del siguiente render. [Intermedia preservada](InventoryPanel.before-pending-guard.fixture.txt). |
| Corrección de guarda pendiente |10/10PASS,exit0. |
| Regresión pertinente final |52/52PASS,0omitidas,exit0,316,7874ms. [Resumen](NODE.json). |
| Edge/HTTP/PG17.11 · instant |PASS21,34s. [Resultado](EDGE-PG.json), [navegador](NAVEGADOR.json). |
| Edge/HTTP/PG17.11 · elegibilidad |PASS28,34s. [Resultado](REGRESION-ELEGIBILIDAD.json), [navegador](NAVEGADOR-REGRESION.json). |

El revisor ejecutó cinco pruebas propias y negativos iniciales/intermedios: detalles y fallos de su observador, si los hubo, en su informe. No repitió los diez casos del autor ni ejecutó HTTP/PostgreSQL. No se cuentan repeticiones como casos distintos.

El navegador reordena un equipo mediante Bajar y retiene la respuesta200 real. Login controlado de otra cuenta y Actualizar de cabecera desmontan la instancia original. Liberar la respuesta conserva exactamente el journal original, no lo muestra al nuevo usuario y no marca su vista como guardada. El propietario vuelve y consulta el recibo, sin otro POST de inventario. Luego restaura el orden con Subir.

Otro intento de Bajar se detiene antes de llegar al servidor: journal original conservado y datos sin cambio. Recuperación/cancelación confirma la terminal en servidor y libera el bloqueo de intención del mismo panel. Nuevos Bajar/Subir funcionan. Las nueve tablas de inventario terminan exactamente como al principio, incluidos IDs/extremos/fechas. Reinicio del proceso servidor y lectura posterior comprobados; no reinicio Windows ni servicio SCM.

La regresión conserva bloqueo de borrador por revisión remota y revocación real de membresía, incluida escritura HTTP directa rechazada por servidor. Ambos labs/procesos detenidos y entradas intactas. Eventos programáticos, no gesto manual de Wascar, corte imprevisible o instalación. Se inspeccionaron [otro usuario tras respuesta tardía](late-instant-other-actor.png) y [panel liberado después de cancelación](instant-after-cancellation.png).

## Repetición

Node24.21.0, Python3.12, Edge yPG17.11 existentes. Copia privada de frontend compilada con `node build.mjs`, referencia RC9 validada y CSS conservado. [Fuentes/build](FUENTES.json). DLLC2reutilizada5eb1abcf…; frontend0df395a6… . No receta de clon limpio: requiere esos artefactos privados.

```powershell
& .local/node-v24.21.0-win-x64/node.exe --test development/frontend/tests/inventory-instant-context.test.mjs development/frontend/tests/operation-dialog-context.test.mjs development/frontend/tests/inventory-operation-status.test.mjs development/frontend/tests/group-growth-compensation.test.mjs development/frontend/tests/group-reduction-compensation.test.mjs development/frontend/tests/inventory-compensation.test.mjs development/frontend/tests/inventory-compensation-power.test.mjs
& .local/node-v24.21.0-win-x64/node.exe --test evidence/s1-20261025/c2-instant-codex/review-instant-negative.test.mjs
& C:/Python312/python.exe -X utf8 -B development/server/tests/test_inventory_operation_status_gui.py --dll C:/RackClick_SVR/.local/c2-reduction-20261025-3936b00ab633/app/RackClick.Server.dll --frontend C:/RackClick_SVR/.local/c2-instant-20261025T122334Z-da4af7d2/frontend/dist --output C:/RackClick_SVR/.local/C2-INSTANT-REPETICION-NUEVA --scenario instant
```

Regresión: otra salida nueva y `--scenario eligibility`. El runner amplía su lista cerrada de escenarios; status continúa predeterminado. Para controles, `RACKCLICK_PANEL_SOURCE` apunta a la fixture histórica pertinente. Sobre la intermedia ejecutar sólo `--test-name-pattern 'uncertain result blocks'`: espera exit1. Capturar `$LASTEXITCODE` y retirar la variable. Node mantiene el aviso MODULE_TYPELESS_PACKAGE_JSON; no se alteran paquetes para ocultarlo.

## Conciliación y límites

QA117planned,116casos y metadatos anteriores intactos; guías regeneradas sin modificar resultados personales o snapshot. [Controles](CONTROLES.json). No prueba cada caller de instant ni toda capacidad específica; autorización/revisión/persistencia siguen comprobándose en servidor. Matriz completa, integración coordinada y aceptación pendientes. No MFA habilitado ni promoción a07.

I-01.03parcial. [Crédito](CREDITO-I0103.json) delta0, **3,57/100puntos del pendiente,8/280subpasos,1/50resultados**, alcance/pesos intactos; no porcentaje global. [Plan anterior](PLAN-ANTES-I0103.json). [SHA256SUMS](SHA256SUMS.txt) fija bytes finales; escaneo público acotado, sin afirmar historial limpio.
