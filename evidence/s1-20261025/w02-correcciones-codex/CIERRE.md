# Revisión W-02 corregido · Codex · 25.10.2026

[Dictamen](../../../docs/REVISION-W02-CORRECCIONES-CODEX.md), [mensaje para Claude](../../../docs/MENSAJE-PARA-CLAUDE-W02-CORRECCIONES-25-10-2026.md), [revisión distinta](REVISION-PROCEDIMIENTO.md). R2 cerrado; inventario R1 corregido, R1b pendiente en la vinculación al lanzamiento. Procedimiento requiere identificar el acceso de verificación posterior. No nueva instalación ni crédito.

## Ejecutado por Codex

- [16/16 estáticas](ESTATICAS.json), sin omisiones.
- [Foco nativo](FOCOS-NATIVOS.json): 12 observaciones esperadas; Plan válido con validador oficial, H1, tres informes falsos rechazados y registrados fail, exclusión del host, original aceptado, alteración coordinada/extra/junction rechazados. No se atribuyen como propias las 18 observaciones de Claude.
- R1b adicional: Execute original con Plan/Check y procesos controlados. Dos llamadas simuladas; primera con bytes auténticos, segunda con comentario inocuo añadido. No detección antes de la segunda llamada. El resultado no prueba ejecución de archivo modificado en VM.
- [Cuatro hashes oficiales 07](ARTEFACTOS-07.json) coinciden. No paquetes modificados ni reconstruidos.

## Repetir el foco

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File .\evidence\s1-20261025\w02-correcciones-codex\reproduce_corrections.ps1 -RunnerPath .\evidence\s1-20261025\w02-correcciones-codex\RUNNER-RECIBIDO.ps1 -OutputDirectory C:\RackClick_SVR\.local\W02-CORRECTIONS-REPLAY-NUEVO
C:/Python312/python.exe -X utf8 -B -m unittest tools.tests.test_w02_trial_plan
```

El [script](reproduce_corrections.ps1) fija hash del helper recibido; usa sus declaraciones/funciones extraídas por AST y nunca su entrypoint. R2 usa el validador oficial del payload fijado. Exclusiones/Check/procesos se controlan sólo en focos específicos; no se altera producción. La limpieza de Plan se intercepta, comprueba su destino y preserva los cuatro stages: cero borrados recursivos. Extractos/variantes/junction quedan exclusivamente bajo una salida nueva de `.local` validada antes de escribir.

RUNNER-RECIBIDO.ps1 conserva los bytes revisados para reproducir después de nuevas correcciones; es evidencia histórica, no un lanzador aprobado.

**Exit 0 del foco confirma las observaciones, incluido el defecto R1b; no aprueba instalación.** Cero lanzamientos reales del envoltorio, servicios, cuentas, bases, QA o VM. Prerrequisito: artefactos 07 locales; no se afirma reproducción desde clon limpio. Primer intento del arnés propio falló por usar Clone sobre OrderedDictionary de WinPS; se corrigió sólo el arnés y se repitió en salida nueva. Código anterior y diagnósticos privados conservados bajo `.local/w02-corrections-review-current.txt`.

El revisor distinto leyó procedimiento, launcher y el foco/resultado; no repitió pruebas. Confirmó reapertura por verificador y alcance del testigo R1b. La batería Bash de Claude no se ejecutó: reutiliza directorios existentes y su estado final no agrega fallos de todos los casos; se registra como problema de evidencia, no refutación de sus observaciones.

## Conciliación y límites

W-02.01–05 pendientes, **0/2,50**. [Crédito sin cambio](CREDITO-W02.json): delta 0, **25/7 = 3,57/100 del pendiente**, 8/280 subpasos, 1/50 resultados; huella/alcance/pesos intactos. [Plan anterior](PLAN-ANTES-W02.json). El porcentaje global permanece sin calcularse.

No se editan fuentes/helper/pruebas/procedimiento/evidencia de Claude ni paquetes. Se añaden dictamen, evidencia y conciliación documental conservando los cuerpos anteriores. Sin QA/VM, SQL, instalaciones o commits. H1 oficial/H2/H3 quedan con el tratamiento del dictamen. Siguiente: los tres ajustes del mensaje y después ensayo real en VM limpia.

`SHA256SUMS.txt` fija archivos de este cierre y se verifica desde la raíz con `tools/verify_hashes.py`. Escaneo acotado a contenido público nuevo, sin presentar el historial como limpio.

[Controles](CONTROLES-CIERRE.json): seis fuentes recibidas de Claude sin cambios, cinco cuerpos anteriores conservados byte a byte, enlaces locales seleccionados válidos y comprobaciones de métrica/diff sin errores. El resultado del escáner se registra en ese control.
