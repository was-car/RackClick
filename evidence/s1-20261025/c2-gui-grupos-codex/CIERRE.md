# C2 · candidato y confirmación estructural en GUI · 25.10.2026

[Alcance y contrato](../../../docs/C2-GUI-GRUPOS-25-10-2026.md), [revisión distinta](REVISION.md), [mensaje de coordinación](../../../docs/MENSAJE-PARA-CLAUDE-C2-GUI-25-10-2026.md). Implementación de Codex. Sin QA/VM, cuentas/servicios, instaladores, paquetes, backend/MFA, SQL de producto, commits ni push modificados.

## Resultados ejecutados, separados

| Comprobación | Resultado |
|---|---|
| Node24.21.0 | [27/27,11nuevos+16regresiones](NODE.json),0omisiones. |
| GUI estructural Edge156/HTTP/PostgreSQL17.11 | [PASS22,27s](EDGE-PG-GRUPOS.json); crecimiento/reducción, casilla, Cancelar, respuesta comprometida perdida, reload/replay, otra sesión y Lector. [Cuatro comprobaciones del escenario](NAVEGADOR-GRUPOS.json), sin excepcionesJS. |
| Persistencia | Nueve tablas SQL exactas al estado inicial, incluidos UUID/atributos/fechas/extremos; persistencia tras reiniciar el proceso. No reinicio Windows/SCM. |
| Regresión GUI de atributos | [Primer intento no acreditado](REGRESION-PRIMER-INTENTO.json): observador usa posición20 dehooks, que ya corresponde a otro estado. Diagnóstico corregido con control positivo y aserciones finales conservadas. [Repetición focal PASS21,30s](REGRESION-ATRIBUTOS.json), ámbito404 y persistencia. |
| Revisión distinta | [5/5 negativos propios y adenda estática](REVISION.md); sin atribuirse Node27/Edge/PG del autor. |
| Guías manual/restaurada | [111casos anteriores conservados](GUIAS-QA.json), QA112/113planned/no disponibles. Storage/observaciones/resultados originales sin cambios. |

Screenshots inspeccionadas del laboratorio sintético: [retirar añadidos](ALCANCE-CRECIMIENTO.png) y [restaurar grupo/puerto/cable](ALCANCE-RESTAURACION.png). No contienen credenciales ni datos reales.

## Repetir

Los runners requieren DLL/frontend explícitos bajo `.local`, herramientas existentes fijadas y directorio de resultado nuevo; crean su propio PostgreSQL/roles/claves/Edge. No reutilizan QA ni bases existentes. El job del coordinador limita descendientes300s; cada escenario Edge usa su job180s y perfil separado.

```powershell
& '.local/node-v24.21.0-win-x64/node.exe' --test development/frontend/tests/group-compensation-candidate.test.mjs development/frontend/tests/group-growth-compensation.test.mjs development/frontend/tests/group-reduction-compensation.test.mjs development/frontend/tests/inventory-compensation.test.mjs development/frontend/tests/inventory-compensation-power.test.mjs
& 'C:/Python312/python.exe' -X utf8 -B development/server/tests/test_group_compensation_gui.py --dll C:/RackClick_SVR/.local/C2-ARTIFACT/RackClick.Server.dll --frontend C:/RackClick_SVR/.local/FRONTEND/dist --output C:/RackClick_SVR/.local/NEW-GROUP-GUI
& 'C:/Python312/python.exe' -X utf8 -B development/server/tests/test_inventory_compensation_gui.py --dll C:/RackClick_SVR/.local/C2-ARTIFACT/RackClick.Server.dll --frontend C:/RackClick_SVR/.local/FRONTEND/dist --output C:/RackClick_SVR/.local/NEW-ATTRIBUTE-GUI --focal-cancel
& 'C:/Python312/python.exe' -B tools/windows/qa_guide.py
& 'C:/Python312/python.exe' -B tools/windows/qa_guide.py --profile rc9
```

Sustituir rutas de artefactos por copias propias identificadas; no provisiona un clon limpio. Este ensayo usó DLL5eb1abcf… reutilizada, no compiló.NET ni creó otro bundle. Build frontend privado mediante `node build.mjs`, referencia RC9/esbuild fijados. Se conservaron logs privados y los dos intentos de regresión bajo la ruta señalada por `.local/c2-gui-groups-current.txt`.

## Crédito y límites

[Cambio de crédito](CREDITO-I01.json): I-01.01/02/04 añaden15/14puntos; total25/7≈**3,57/100del pendiente**,8subpasos.1/50resultados completos; I-01 no cerrado. Denominador/huella/pesos intactos. [Estado anterior](PLAN-ANTES-I01.json), [integridad](SHA256SUMS.txt).

No se acredita integración con candidataMFA/instalador07, todas las invalidaciones de I-01.03, QA de Wascar, diseño accesible integral, servicioWindows/reinicio o adopción. Dosen/finales y cambios mixtos no se excluyen. Se actualizan continuidad/progreso/changelog conservando sus cuerpos anteriores. El contexto estructural no se transforma en `changedIds`; no se envía un snapshot inverso ni se guarda en el journal.
