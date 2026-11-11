# C2 · Consulta de operación pendiente · Codex · 25.10.2026

[Alcance](../../../docs/C2-CONSULTA-PENDIENTE-25-10-2026.md), [revisión distinta](REVISION.md), [coordinación con Claude](../../../docs/MENSAJE-PARA-CLAUDE-C2-CONSULTA-25-10-2026.md). Sólo frontend, pruebas y documentación propias. Sin commits, despliegue, instalación, QA/VM, cambios de servicios/cuentas Windows ni bases existentes. PostgreSQL y datos sintéticos nuevos; procesos/clústeres de prueba detenidos.

## Ejecuciones separadas

- [Node](NODE.json): 25/25, 9 nuevas y 16 regresiones, sin omisiones. Primer intento antes de implementación falló por export `readPendingCommand` ausente; no fue una reproducción semántica del P2.
- [Ensayo final Edge/HTTP/PG](EDGE-PG-FINAL.json): PASS 25,77 s; [cuatro comprobaciones](NAVEGADOR-FINAL.json), sin excepciones JS. GET committed sin POST; notRecorded conserva journal y reintento exactos; cancelación externa del mismo actor se reconoce sin alterar inventario; POST tardío bloqueado. Otro actor no obtiene el recibo y ámbito de lector se comprueba en servidor.
- [Regresión estructural](REGRESION-GRUPOS.json): PASS 21,78 s sobre los bytes finales; [navegador](NAVEGADOR-REGRESION.json). Nueve tablas exactas y persistencia tras reiniciar proceso en ambos ensayos.
- [Primer intento de navegador](PRIMER-ENSAYO.json): FAIL de contador del observador, no defecto de producto acreditado; [causa](OBSERVADOR-PRIMER-ENSAYO.json). El fetcher ya estaba capturado; se cambió sólo el test a CDP Network. [Ensayo intermedio](ENSAYO-ANTES-CORRECCION.json) pasó antes del arreglo de contexto y no acredita los bytes finales.
- Revisor distinto: [8/8 propios finales y P2 cerrado](REVISION.md). [Prueba](review-negatives.mjs), [original exacto](OperationDialog-before-query-fix.fixture.txt). Original: 1 FAIL esperado, callbacks bajo otro actor; final: guardas de contexto tras esperas. No atribuir al revisor las ejecuciones Edge/PG del coordinador.
- [Build](BUILD.json): frontend privado, referencia RC9 verificada, sin .NET. Primer snapshot omitió `rc9-reference/.../evidence/integrated-source.jsx`; error conservado privado y copia completada antes del build satisfactorio. CSS inmutable.
- [QA](GUIAS-QA.json): 113 casos anteriores conservados; QA-114 planned, guías regeneradas. No resultados personales sobrescritos ni disponibilidad de candidata añadida.

Capturas del laboratorio inspeccionadas: [sin resultado registrado](SIN-RESULTADO.png), [cancelación confirmada](CANCELADA.png). Fixtures ficticios; sin secretos ni datos reales.

## Repetir sin acceder a QA

Desde la raíz; sustituir las rutas de DLL/frontend por copias privadas propias identificadas y usar salida nueva:

```powershell
& '.local/node-v24.21.0-win-x64/node.exe' --test development/frontend/tests/inventory-operation-status.test.mjs development/frontend/tests/group-growth-compensation.test.mjs development/frontend/tests/group-reduction-compensation.test.mjs development/frontend/tests/inventory-compensation.test.mjs development/frontend/tests/inventory-compensation-power.test.mjs
& '.local/node-v24.21.0-win-x64/node.exe' --test evidence/s1-20261025/c2-query-codex/review-negatives.mjs
& 'C:/Python312/python.exe' -X utf8 -B development/server/tests/test_inventory_operation_status_gui.py --dll C:/RackClick_SVR/.local/C2-APP/RackClick.Server.dll --frontend C:/RackClick_SVR/.local/FRONTEND/dist --output C:/RackClick_SVR/.local/NEW-QUERY-TEST
& 'C:/Python312/python.exe' -X utf8 -B development/server/tests/test_group_compensation_gui.py --dll C:/RackClick_SVR/.local/C2-APP/RackClick.Server.dll --frontend C:/RackClick_SVR/.local/FRONTEND/dist --output C:/RackClick_SVR/.local/NEW-GROUP-REGRESSION
& 'C:/Python312/python.exe' -B tools/windows/qa_guide.py
& 'C:/Python312/python.exe' -B tools/windows/qa_guide.py --profile rc9
```

Los runners crean laboratorio/roles/claves y Edge propios; DLL/frontend explícitos bajo `.local`, no proceden de una instalación. Cada navegador usa Job Object 180 s y el coordinador limita el conjunto a 240 s. Diagnósticos completos, fuentes previas y copia de build bajo el puntero `.local/c2-query-current.txt`. Herramientas y artefactos locales son prerrequisitos; no se afirma reproducción desde clon limpio.

Frontend final `72d970f0…`, DLL reutilizada `5eb1abcf…`; [fuentes revisadas](FUENTES.json). El backend actual del árbol compartido y la candidata MFA/07 no se compilan, sustituyen ni adoptan por esta tanda.

## Estado del cierre

I-01.03 permanece pendiente. Consulta terminada y P2 cerrado no equivalen a completar todas las invalidaciones de revisión/permisos/cuenta/cliente, ni las vías heredadas submit/cancel. Candidata integrada y QA siguen pendientes. [Conciliación sin crédito](CREDITO-I0103.json): **delta 0; 25/7 = 3,57/100**, 8/280 subpasos, 1/50 resultados; alcance/pesos/huella conservados. El porcentaje global del producto sigue sin calcularse.

`SHA256SUMS.txt` fija archivos nuevos/fuentes/documentos del cierre y se verifica desde la raíz con `tools/verify_hashes.py`. El escaneo de contenido público nuevo no sustituye el barrido histórico pendiente. Revisiones y resultados anteriores se conservan separados.

[Controles del cierre](CONTROLES-CIERRE.json): generador de métrica `--check` y diff sin errores; 23 enlaces locales seleccionados válidos, fuentes revisadas iguales a las del build final y cuerpos anteriores de continuidad conservados byte a byte. Gitleaks 8.30.1 sobre copia privada de archivos públicos propios y sólo entradas nuevas de continuidad, con resultado registrado en ese control; no se escanea de nuevo todo el historial ni se certifica su limpieza.
