# W-02 · cierre de revisión · Codex · 25.10.2026

**Resultado:** R1/R2 reproducidos en comprobaciones previas del auxiliar. Corregir antes de Execute. No cambian el envoltorio congelado 07 ni el cierre W-01. [Dictamen](../../../docs/REVISION-W02-CODEX.md), [tanda para Claude](../../../docs/MENSAJE-PARA-CLAUDE-W02-25-10-2026.md).

## Ejecutado por Codex en LEAO

- `C:/Python312/python.exe -X utf8 -B -m unittest tools.tests.test_w02_trial_plan`: 9/9 PASS, 0 omisiones. Son pruebas estáticas; no detectan los dos defectos. [Resumen](NUEVE-ESTATICAS.json).
- Helper recibido, **Mode Check**, puertos 47997/47996, directorio privado nuevo: exit 1, `os_not_server_2025`, esperado en este host. [Resumen sanitizado](CHECK-NATIVO.json). No se invocó Execute ni Plan.
- [Foco nativo](reproduce_binding.ps1), PowerShell 5.1: conserva hashes de entrada, extrae por AST función y fragmentos exactos, crea fixtures nuevos privados. Original aceptado; cambio de archivo sin manifiesto rechazado; cambio coordinado y extra declarado aceptados. Plan sin informe rechazado; hoja inválida para esquema más informe coincidente aceptada. [Resultado](FOCO-VINCULACION.json).

El foco **no ejecuta** el helper completo, Check, VerifyOnly ni INICIAR; no modifica servicios, cuentas, bases, firewall o certificados. El cambio de INICIAR es un comentario inocuo. Exit 0 significa que se reprodujeron los fallos esperados de las compuertas. No demuestra ejecución de código modificado ni instalación con parámetros inválidos en VM.

Reproducción del foco desde la raíz, indicando un directorio de salida nuevo dentro de `.local` y el ZIP 07 original:

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File .\evidence\s1-20261025\w02-vm-limpia-07-codex\reproduce_binding.ps1 -RunnerPath .\evidence\s1-20261025\w02-vm-limpia-07-codex\RUNNER-RECIBIDO.ps1 -OfficialArchive .\.local\instalador-07\entrega\RackClick-Servidor-07.zip -OutputDirectory C:\RackClick_SVR\.local\w02-replay-nuevo
```

`RUNNER-RECIBIDO.ps1` es copia histórica byte a byte, **no un lanzador aprobado**. Se conserva para repetir el test aunque Claude corrija la fuente. ZIP y diagnósticos completos permanecen privados; la reproducción requiere ese artefacto local, no se afirma portable a un clon limpio. [Hashes recibidos](RECEPCION.json).

## Revisión distinta y límites

Un revisor distinto leyó procedimiento, scripts del payload y límites del foco; [informe](REVISION-PROCEDIMIENTO.md). No ejecutó ni repitió el foco. Confirma correcciones de UUID, reinicio manual y Restore completo, además del hash documental desactualizado. No se atribuyen a Codex las pruebas de Claude ni un ensayo del instalador.

No se editó producto, helper, pruebas de Claude, procedimiento recibido ni paquetes. Sólo evidencia/documentación y conciliación del estado del plan. Sin instalaciones, QA, VM, SQL, commits o publicación. No cambio visible para usuarios; no se alteró disponibilidad del catálogo QA.

## Conciliación

W-02 mantiene cinco subpasos pendientes, **0/2,50**; fuente previa del plan conservada en `PLAN-ANTES-W02.json`. [Crédito](CREDITO-W02.json): delta 0, cierre del pendiente **25/7 = 3,57/100**, 8/280 subpasos, 1/50 resultados. Alcance, pesos y huella normativa intactos. El porcentaje global del producto permanece sin cálculo; 78 es histórico retirado.

Siguiente: corrección acotada de helper/documentos y revisión; luego ensayo New/Restore/reinicio en VM limpia no DC, con resultados reales por intento. Evidencia y manifiesto nuevos separados de los históricos.

## Comprobación del cierre documental

`tools/progress_report.py --write` y `--check` conservan la huella normativa y el crédito. `git diff --check` del alcance documental termina sin errores. [Controles](CONTROLES-CIERRE.json): las cuatro fuentes recibidas no cambiaron, los cuerpos anteriores de los cuatro documentos de continuidad se conservan byte a byte y los 13 enlaces locales seleccionados existen.

Gitleaks 8.30.1 sobre copia privada de estos archivos públicos y sólo las entradas nuevas de continuidad: exit 0, sin hallazgos. No es un barrido nuevo de todo el historial ni certificación de ausencia de secretos. Diagnósticos completos privados. `SHA256SUMS.txt` fija la evidencia y los documentos vigentes al cierre; se verifica con `tools/verify_hashes.py` desde la raíz.
