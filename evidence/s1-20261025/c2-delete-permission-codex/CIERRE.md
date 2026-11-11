# C2 · corrección I04-GUI-01

## Cambio y revisión

[Alcance y comportamiento](../../../docs/C2-PERMISOS-BORRADO-25-10-2026.md). Producto cambiado: `InventoryPanel.jsx` y módulo nuevo `inventory-operation-permission.ts`. Se separan controles/apertura de edición y borrado; la recuperación toma la capacidad del comando original. No cambia `OperationDialog`, backend, SQL, MFA ni autorización del servidor.

Pruebas añadidas: escenario `browser-inventory-delete-permission.mjs`, opción cerrada `delete-permission` en el runner existente y test independiente `inventory-delete-permission.test.mjs`. [Revisión distinta](REVISION.md): el revisor no editó producto; sus cinco grupos propios y su lectura se distinguen de los ensayos Edge/PG del coordinador.

## Ejecuciones nuevas

| Ensayo / autor | Resultado | Evidencia |
|---|---|---|
| Edge, frontend anterior / coordinador | FAIL 18,67 s, falta real de controles de borrado | [ORIGINAL.json](ORIGINAL.json), [diagnóstico](ORIGINAL-DIAGNOSTICO.json). |
| Primera ejecución con frontend corregido / coordinador | FAIL 33,83 s, espera de infraestructura incompatible con journal pendiente | [OBSERVADOR-ENSAYO.json](OBSERVADOR-ENSAYO.json), [diagnóstico](OBSERVADOR-DIAGNOSTICO.json). Sólo se corrigió la espera del test. |
| Edge/PostgreSQL 17.11 final / coordinador | PASS 23,08 s | [EDGE-PG.json](EDGE-PG.json), [NAVEGADOR.json](NAVEGADOR.json). |
| Regresión de edición con el mismo frontend / coordinador | PASS 20,17 s | [REGRESION-EDICION.json](REGRESION-EDICION.json). |
| Node, consulta/contexto/edición rápida / coordinador | 36/36 PASS, 0 omitidas, 310,6423 ms | [NODE.json](NODE.json). |
| Node, panel anterior / revisor distinto | 3 PASS / 2 FAIL esperados, exit 1 | [REVISION.md](REVISION.md). Módulo presente; no es un fallo de importación. |
| Node, cinco grupos propios finales / revisor distinto | 5/5 PASS, 0 omitidas, exit 0 | Mismo informe; salidas privadas preservadas. |

El escenario final usa dos contextos reales de navegador, cambios de concesiones por API administrativa y sólo datos sintéticos. El usuario de borrado no recibe edición en el cliente; el de edición sin borrado no puede reenviar una eliminación, aunque pueda consultar `notRecorded`. Reintento tras recargar conserva cuerpo/actor/clave/ETag; una confirmación perdida se recupera por GET. Nueve tablas originales de inventario quedan exactas al final; lectura tras reiniciar el proceso servidor y cierre del laboratorio/procesos comprobados en ambos PASS. No es reinicio Windows.

Capturas inspeccionadas: [edición sin borrado no reintenta una eliminación](edit-without-delete-recovery.png), [estado final de cuenta de borrado](delete-only-complete.png). No contienen credenciales ni resultados de Wascar.

Comandos ejecutados, desde la raíz salvo Node:

```powershell
C:/Python312/python.exe -X utf8 -B development/server/tests/test_inventory_operation_status_gui.py --dll C:/RackClick_SVR/.local/c2-reduction-20261025-3936b00ab633/app/RackClick.Server.dll --frontend C:/RackClick_SVR/.local/c2-delete-permission-20261025T135722Z-e69491f3/frontend/dist --output C:/RackClick_SVR/.local/c2-delete-permission-20261025T135722Z-e69491f3/edge-final-fix1 --scenario delete-permission
```

La regresión usa el mismo comando con `--output .../edge-regression-edit --scenario write-permission`. El original usa frontend privado `c2-instant-20261025T122334Z-da4af7d2/frontend/dist` y salida `edge-original`; el primer ensayo corregido usa `edge-final`. Las salidas son nuevas y privadas. El script anterior se conserva como `browser-first.mjs`.

```powershell
# Ejecutado en development/frontend:
C:/RackClick_SVR/.local/node-v24.21.0-win-x64/node.exe --test tests/inventory-operation-status.test.mjs tests/operation-dialog-context.test.mjs tests/inventory-instant-context.test.mjs
```

## Identidad, QA y límite de cierre

Frontend privado construido una vez con Node 24.21.0 y esbuild 0.25.10, reutilizando la referencia RC9 verificada. `app.js` c8c099a8…; CSS 50dd8567… exacto al anterior. DLL C2 5eb1abcf… reutilizada, sin build .NET. [FUENTES.json](FUENTES.json) fija hashes completos y comparación de fuentes con el build. No acredita reproducción binaria en clon limpio ni candidata MFA coordinada.

QA-118 `planned`, 117 casos/metadatos previos conservados salvo revisión del catálogo; guías regeneradas con `qa_guide.py` y `--profile rc9`. No se seleccionó build en QA, ni se abrieron resultados/observaciones personales. No hay nuevos Pass manuales.

Hallazgo focal corregido, I-04.05 todavía pendiente por su alcance completo. El plan sólo añade evidencia/estado parcial: no cambian estados de subpasos, texto, pesos ni otras tareas. **Delta 0: 4,29/100 (30/7), 10/280 subpasos, 1/50 resultados completos; sin porcentaje global nuevo.** W-02 y pruebas de VM de Claude no reciben crédito aquí.

Sin commits, push, instalación, servicios/cuentas/red del host, bases existentes, QA, VM, paquetes o MFA modificados. Siguiente: completar la matriz de impacto/cancelación/borrado e integrar la candidata coordinada antes de habilitar QA. [Controles](CONTROLES.json), [escaneo](ESCANEO.json), [manifiesto](SHA256SUMS.txt).
