# C2 · contexto de envío y cancelación · cierre de tanda

25.10.2026, Windows/LEAO. Implementador/coordinador Codex; revisión distinta `rackclick_qa`, terminada y documentada en [REVISION.md](REVISION.md). Sin commits, push, instalación, QA, VM, W-02 ni cambios de MFA/backend/SQL/paquetes. Laboratorios PostgreSQL nuevos y secretos generados localmente; nunca se incluyen credenciales en esta evidencia.

## Resultado

El borrador conserva API/actor/cliente de origen. Se comprueban tras las esperas de preview, journal, envío/cancelación, limpieza y callbacks; desmontaje o contexto perdido impiden encadenar confirmaciones/cierres en otra vista. La invalidación observada A→B→A es permanente para ese diálogo. El inventario se monta por actor y cliente. Incertidumbre conserva el registro original; resultado definitivo sólo permite limpiar ese registro. Un callback ya iniciado puede continuar internamente: no se promete cancelación universal.

Sólo dos archivos de producto cambiados en esta tanda: `development/frontend/src/OperationDialog.jsx` y la clave del panel en `development/frontend/src/ServerApp.jsx`. API, estilos y dependencias conservados. Prueba Node y escenario Edge nuevos; el runner Python añade una selección cerrada `status/context`, predeterminado `status`.

## Ejecuciones nuevas del coordinador

| Ejecución | Resultado |
|---|---|
| Harness final contra fuente anterior a esta tanda | 4 PASS / 7 FAIL esperados, exit 1. [Fuente preservada](OperationDialog.before-context.fixture.txt). |
| Primera repetición de la corrección | 9 PASS / 2 FAIL: defecto del harness al asignar una referencia DOM a todos los hooks nulos, incluido AbortController. Corregido el harness; no se declara corrida válida final. |
| Harness corregido y producto final | 11/11 PASS; regresión focal final 36/36 PASS, 0 omitidas, exit 0, 229,0301 ms. [Resumen](NODE.json). |
| Primera corrida Edge contexto | FAIL, 32,11 s. Espera del observador exigía botones habilitados al volver al propietario con journal pendiente; ese bloqueo era correcto. Espera corregida; [resultado conservado](PRIMER-ENSAYO.json), [diagnóstico](OBSERVADOR.json). |
| Edge contexto final | PASS, 20,81 s, Edge 156 / PG17.11; [resultado](EDGE-PG-CONTEXTO.json), [HTTP/navegador](NAVEGADOR-CONTEXTO.json). |
| Edge regresión de consulta | PASS, 24,52 s, mismo frontend final; [resultado](REGRESION-CONSULTA.json), [navegador](NAVEGADOR-REGRESION.json). |

La corrida Edge retiene en CDP respuestas reales 200 de enviar y cancelar, cambia la cookie de cuenta mediante login real y llama al Actualizar de la cabecera. React desmonta el panel anterior. Liberar la respuesta no borra la intención incierta del propietario ni confirma la vista del nuevo usuario. Volver al propietario y consultar recupera committed/cancelled exactos sin reenviar la escritura. IndexedDB real. Una edición normal final devuelve el inventario inicial: nueve tablas SQL comparadas exactamente y dato persistente tras reiniciar el proceso servidor. Ambos clusters y todos los procesos servidor detenidos; entradas de laboratorio sin alterar.

Se inspeccionaron las capturas [otro usuario después de respuesta tardía](actor-after-late-submit.png) y [propietario con cancelación confirmada](original-actor-cancellation.png). Datos sintéticos. No hay QA manual, gesto físico, corte de red no controlado, servicio Windows ni reinicio del sistema operativo acreditados. Las respuestas enumeran rutas/estados, no cookies/tokens/cuerpos de login.

El revisor reprodujo R-C2-CTX-01, un rechazo que escapaba del `catch` al limpiar tras error definitivo. Fuente intermedia exacta preservada por él. Corregido por el coordinador; dos negativos fallan en esa fuente, 9/9 propios pasan en la final. Su repetición de 11/11 no se suma como once casos distintos. No ejecutó Edge/SQL/build y así lo declara.

## Repetición

Herramientas ya existentes: Node24.21.0, Python3.12, Edge local y PG17.11 nativo. Sin instalación de herramientas/dependencias ni cambio de versiones. El frontend se compiló con `node build.mjs` en una copia privada del frontend, preservando la referencia RC9. [BUILD.json](BUILD.json) identifica salida y DLL reutilizada; [FUENTES.json](FUENTES.json) fija fuentes ensayadas. El build no publica nada y no habilita QA.

Desde `C:\RackClick_SVR`:

```powershell
& .local/node-v24.21.0-win-x64/node.exe --test development/frontend/tests/operation-dialog-context.test.mjs development/frontend/tests/inventory-operation-status.test.mjs development/frontend/tests/group-growth-compensation.test.mjs development/frontend/tests/group-reduction-compensation.test.mjs development/frontend/tests/inventory-compensation.test.mjs development/frontend/tests/inventory-compensation-power.test.mjs
& .local/node-v24.21.0-win-x64/node.exe --test evidence/s1-20261025/c2-context-codex/review-context-negative.test.mjs
```

Negativo inicial: establecer `RACKCLICK_DIALOG_SOURCE` en la ruta absoluta de `OperationDialog.before-context.fixture.txt`, ejecutar sólo `operation-dialog-context.test.mjs`, capturar `$LASTEXITCODE` y retirar la variable con `Remove-Item Env:\RACKCLICK_DIALOG_SOURCE`. Se esperan siete fallos y exit1. No usar esa copia histórica en el producto.

```powershell
& C:/Python312/python.exe -X utf8 -B development/server/tests/test_inventory_operation_status_gui.py --dll C:/RackClick_SVR/.local/c2-reduction-20261025-3936b00ab633/app/RackClick.Server.dll --frontend C:/RackClick_SVR/.local/c2-context-20261025T111054Z-21ee5c0c/frontend/dist --output C:/RackClick_SVR/.local/c2-context-repeticion-NUEVA --scenario context
```

Para repetir la regresión usar otra carpeta nueva y `--scenario status`. El runner comprueba hashes, crea un cluster/base independiente con cuentas sintéticas, arranca sólo sus procesos y los detiene al acabar; requiere artefactos privados locales que no se incluyen en un clon limpio. No se anuncia reproducibilidad completa de entrega. No ejecutar sobre las bases de QA.

## QA, métrica y límites

QA-115 **planned**; 114 casos anteriores y metadatos conservados. Ambas guías regeneradas, snapshot y resultados personales sin cambios. [Control](GUIAS-QA.json). Pendiente candidata integrada antes de habilitar el caso. Reautenticación/MFA no modificados ni aceptados; quedan invalidaciones generales por revisión/permisos y vías heredadas. I-01.03 sigue pendiente/parcial, y no se modifica el peso ni se fragmenta para ganar puntos.

[Crédito](CREDITO-I0103.json): delta0, **3,57/100 puntos del trabajo restante, 8/280 subpasos y 1/50 resultados completos**, baseline intacta. Porcentaje global del producto sin afirmar. [Plan previo](PLAN-ANTES-I0103.json), [controles](CONTROLES.json). W-02 corresponde a Claude y a un ensayo Windows Server limpio; esta tanda no lo ejecuta ni lo acepta.

[Alcance](../../../docs/C2-CONTEXTO-OPERACION-25-10-2026.md) · [Mensaje de coordinación](../../../docs/MENSAJE-PARA-CLAUDE-C2-CONTEXTO-25-10-2026.md) · [Manifiesto final](SHA256SUMS.txt).
