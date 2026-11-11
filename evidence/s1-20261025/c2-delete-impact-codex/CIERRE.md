# I-04.05 · evidencia de borrado e impacto

25.10.2026. Dos pruebas nuevas: browser implementado por worker `delete_impact_browser`; fixture/harness y ejecuciones por coordinador. Revisión independiente por `rack_choices_review`, sólo en su informe. Producto/MFA/backend, GUI, DLL, CSS e instaladores sin cambios.

## Ejecuciones reales nuevas

- `EDGE-PG.json`, `EDGE-BROWSER.json`, `DETALLES-BORRADO.json` y capturas: PASS35,891s, Windows/Edge/PostgreSQL17.11. Final conectado eliminado individualmente y Dose+equipo de rack en lote, con previews exactos de cinco conjuntos. Cuatro barreras de archivos sincronizan el navegador con las mediciones SQL sin añadir endpoints auxiliares.
- Las dos cancelaciones preservan exactamente nueve tablas de inventario más cliente/operaciones/auditoría. Dos confirmaciones producen sólo dos operaciones, revisión+2 y auditorías `inventory.device.delete=1` / `inventory.devices.delete=1` respecto al inicio observado.
- Ocho denegaciones preview/commit403/404 sin cambios, proyecto exacto tras recarga/otra sesión/reinicio del proceso. Cable no incidente y extremos/atributos de todos los objetos conservados exactos. Entradas inmutables; procesos propios detenidos.
- `REGRESION-LOTE.json`, `REGRESION-BROWSER.json`: ejecución nueva PASS27,984s de test_delete_batch_gui, mismo frontend/DLL. EN/DE/ES, preview/cancel, selección obsoleta412, lote completo, respuesta200 perdida/replay sin commit extra y persistencia. No es copia de un log histórico.
- `REVISION.md`: tres focos propios del revisor y contraste de las ejecuciones atribuidas al coordinador. No repitió Edge/PG ni operó VM/QA. Incidencia de su lector PowerShell resuelta usando el intérprete existente; no modifica el resultado del producto.

## Reproducción

Con la toolchain local del proyecto (Windows, Edge, PostgreSQL17.11 y Node) y las entradas explícitas de `ENTORNO.json`:

```powershell
C:/Python312/python.exe -X utf8 -B development/server/tests/test_delete_impact_variants_gui.py --dll <DLL5eb1> --frontend <dist04f4> --output <directorio-nuevo-en-.local>
C:/Python312/python.exe -X utf8 -B development/server/tests/test_delete_batch_gui.py --dll <DLL5eb1> --frontend <dist04f4> --output <otro-directorio-nuevo>
```

La primera prueba exige artefactos y salida separados bajo `.local`; crea su base/cuentas sintéticas y detiene su laboratorio. No usar C, QA o bases existentes. Cada barrera `*-state.json` espera la respuesta `*-continue.json`; si la verificación SQL falla, el navegador recibe valid=false y aborta. La lectura espera JSON completo para no confundir la creación del archivo con la escritura terminada. El trabajo de navegador queda en el JobObject existente y tiene timeout global.

Los artefactos exactos viven en `.local`; no están en un clon limpio. No llamar PASS a una omisión ni sustituirlos por un build del árbol compartido. No se publican tokens, cookies, CSRF o contraseñas; los detalles sólo guardan presencia de confirmación y cuerpos sin ese token.

## Cierre

Se completa técnicamente I-04.05 (peso5/14), sin ampliar alcance ni afirmar candidata final/QA. El foco complementa las pruebas previas de impacto, permisos y API, que mantienen su fecha/atribución. I-04.06/07 siguen pendientes. No hay hardware táctil, Windows reboot, instalación o adopción probados en este bloque.

Métrica exacta en `CREDITO-I0405.json`; hashes vigentes en `SHA256SUMS.txt`. Documentación: `docs/C2-BORRADO-IMPACTO-25-10-2026.md`. Wascar informa que Claude empezó MFA-L1; no se presume una ejecución adicional ni se altera su zona. Sin commits/push, builds, paquetes, QA o VM.

Verificación final: métrica y huella de alcance validadas; fuentes de pruebas coinciden con sus hashes ejecutados. Gitleaks8.30.1: cero hallazgos en el conjunto nuevo seleccionado (no historial completo). Codebase Memory refrescado,941archivos curados; el índice es navegación y no una candidata compilada. Cierre exacto87/14=6,21/100 del pendiente,16subpasos done; porcentaje global sin recalcular.
