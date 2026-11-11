# C2 · elegibilidad observada · cierre de tanda

25.10.2026, Windows/LEAO. Implementación/coordinación Codex y [revisión distinta](REVISION.md). [Alcance](../../../docs/C2-REVISION-PERMISOS-25-10-2026.md), [coordinación Claude](../../../docs/MENSAJE-PARA-CLAUDE-C2-ELEGIBILIDAD-25-10-2026.md).

Sólo dos archivos de producto cambiados: `InventoryPanel.jsx` transmite la revisión máxima observada y la autoridad actual; `OperationDialog.jsx` comprueba elegibilidad antes del primer envío y explica/bloquea el borrador obsoleto. La intención ya registrada conserva identidad, cuerpo, clave y revisión. Consulta/cancelación no reciben la restricción de revisión de un borrador nuevo. El servidor conserva siempre la decisión de autorización. Frontend privado compilado desde RC9 validada; CSS/dependencias conservados. Sin .NET, backend, MFA, SQL, W-02, paquetes, instalación, QA/VM ni commits.

## Ejecuciones nuevas

| Ejecución | Resultado |
|---|---|
| Fuente anterior con seis casos nuevos del diálogo |12 PASS/5 FAIL esperados, exit1; uno de los seis es contraprueba de recuperación que ya pasaba. [Fuente](OperationDialog.before-eligibility.fixture.txt). |
| Fuente corregida, diálogo |17/17PASS, exit0. |
| Regresión focal final |42/42PASS,0omitidas,exit0,362,5091ms. Incluye17del diálogo; no otros17adicionales. [Resumen](NODE.json). |
| Revisor distinto |5/5propiosPASS;3controlesFAILesperados contra original. Primer regexfallido del observador conservado en su informe. No ejecutó Edge/SQL. |
| Edge/HTTP/PG17.11, elegibilidad |PASS31,27s. [Resultado](EDGE-PG.json), [navegador](NAVEGADOR.json). |
| Edge/HTTP/PG17.11, regresión contexto |PASS20,45s. [Resultado](REGRESION-CONTEXTO.json), [navegador](NAVEGADOR-REGRESION.json). |

Escenario nuevo: otro usuario real confirma `rack.update` con el valor existente, avanzando revisión/auditoría sin cambiar datos del rack. El canal observado invalida el Deshacer abierto; botón bloqueado y submit programático sin journal/POST. Otro administrador revoca realmente la membresía del primero, conservando un administrador activo; la denegación del canal bloquea su diálogo. Se intenta además una escritura HTTP directa que el servidor rechaza. La membresía se restaura en el laboratorio y una edición normal limpia el puerto sintético añadido.

Ambos escenarios usan Edge real, IndexedDB, HTTP y cluster PostgreSQL nuevo; nueve tablas de inventario exactamente iguales a la fixture inicial, incluidos extremos/fechas. Reinicio del proceso servidor y lectura posterior comprobados. No es reinicio Windows ni servicio SCM. Lab/procesos detenidos, entradas intactas. Revocación de membresía afecta sólo a cuentas sintéticas; no se toca la QA. Los eventos del navegador son controlados, no QA manual ni corte de red imprevisible. Se inspeccionaron [revisión bloqueada](revision-blocked.png) y [autoridad bloqueada](authority-blocked.png).

## Repetición

Node24.21.0/Python3.12/Edge/PG17.11 ya presentes; sin instalar dependencias. Artefactos privados: frontend98086c07…/CSS50dd8567… yDLLC2reutilizada5eb1abcf… . [Fuentes y build](FUENTES.json). El runner Python añade el escenario eligibility a una lista cerrada y conserva status como predeterminado. No hay reproducción completa de entrega desde clon limpio: faltan los artefactos privados.

```powershell
& .local/node-v24.21.0-win-x64/node.exe --test development/frontend/tests/operation-dialog-context.test.mjs development/frontend/tests/inventory-operation-status.test.mjs development/frontend/tests/group-growth-compensation.test.mjs development/frontend/tests/group-reduction-compensation.test.mjs development/frontend/tests/inventory-compensation.test.mjs development/frontend/tests/inventory-compensation-power.test.mjs
& .local/node-v24.21.0-win-x64/node.exe --test evidence/s1-20261025/c2-eligibility-codex/review-eligibility-negative.test.mjs
& C:/Python312/python.exe -X utf8 -B development/server/tests/test_inventory_operation_status_gui.py --dll C:/RackClick_SVR/.local/c2-reduction-20261025-3936b00ab633/app/RackClick.Server.dll --frontend C:/RackClick_SVR/.local/c2-eligibility-20261025T113806Z-454d2eb6/frontend/dist --output C:/RackClick_SVR/.local/C2-ELEGIBILIDAD-REPETICION-NUEVA --scenario eligibility
```

Regresión: otra salida nueva y `--scenario context`. Negativo inicial: establecer `RACKCLICK_DIALOG_SOURCE` en la ruta absoluta de la fixture anterior, ejecutar sólo `operation-dialog-context.test.mjs`, capturar exit y retirar la variable; se esperan5FAIL/exit1. El runner sólo admite artefactos/salida privados explícitos y crea nuevas bases y secretos; no usar bases QA. Node conserva el aviso MODULE_TYPELESS_PACKAGE_JSON; no se cambia package.json para ocultarlo.

## Cierre y límites

QA116planned,115casos y demás metadatos intactos, guías regeneradas sin resultados personales/snapshot. [Control](CONTROLES.json). Capacidad de escritura local inventory.edit y pérdida del canal comprobadas; no cubre toda capacidad específica ni detección inmediata de revocación. Vía instant/matriz completa y candidata coordinada/aceptación pendientes. No se anuncia MFA listo.

I-01.03parcial; [crédito](CREDITO-I0103.json) delta0: **3,57/100puntos del pendiente,8/280subpasos,1/50resultados**, alcance/pesos intactos. No porcentaje global. [Plan previo](PLAN-ANTES-I0103.json). [SHA256SUMS](SHA256SUMS.txt) verificado; escaneo acotado al contenido público nuevo, sin afirmar historial limpio.
