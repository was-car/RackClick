# I-06.02 · evidencia de campos y roles de objetos de sala

25.10.2026. Navegador nuevo implementado por `room_fields_browser`; fixture/harness y ejecuciones por coordinador. `room_port_fields_explore` inspeccionó el contrato por lectura. Revisión independiente por `room_fields_review`, en sus tres archivos. Sólo dos tests nuevos, sin cambios de producto, soporte compartido, MFA, dependencias o artefactos.

## Ejecuciones reales nuevas

- `EDGE-PG.json` y `EDGE-BROWSER.json`: **PASS32,719s**, Windows/Edge/PostgreSQL17.11. Dos editores de sala, nombre/presupuesto/cinco notas, seis atributos RJ45 y un rol de puerto power por objeto. `DETALLES-CAMPOS.json` registra16 comandos sin cookies/CSRF; revisiones contiguas, dos `device.update` y catorce `ports.update`, todos200. `CAMPOS-FINAL.png` muestra el estado final sintético.
- `PROYECTO-INICIAL.json` / `PROYECTO-ESPERADO.json`: mismo inventario salvo las modificaciones previstas. La validación SQL compara nueve tablas de filas completas, incluidos metadatos anidados, UUID, pertenencias, gn, puertos vecinos, cables y extremos. No obtiene el esperado del resultado del comando.
- Power y RJ45 comparten gn=1 en grupos distintos. Cada edición envía grupo/tipo/ID de puerto explícitos. Roles outlet/inlet sólo en power sin cable; PoE activado y desactivado sólo en familia RJ45. Se vacían vatios/color/etiqueta y se conservan las diferencias entre null, cero y texto vacío.
- Cinco reglas/ámbitos inválidos y dos cuentas sin autorización producen422/404/403 según el caso. Cada rechazo preserva nueve tablas, cliente/revisión, operaciones y filas de auditoría. El lote con primer puerto válido y segundo de otro grupo no deja un cambio parcial.
- Recarga y segunda cuenta autorizada leen el proyecto completo y los controles con valores guardados. Nombres/notas Unicode con apariencia de HTML permanecen texto literal. Tras reiniciar el proceso servidor, ambas cuentas leen el estado exacto; entradas iguales y procesos propios detenidos.
- `REGRESION-PG.json` / `REGRESION-BROWSER.json`: ejecución nueva **PASS27,562s** de la prueba de edición básica ya existente, con idénticos artefactos. Cuatro operaciones, auditoría2device+2ports+1preferencia de español,403/404/422 atómicos y persistencia. No se recicla una ejecución anterior.
- `REVISION-INDEPENDIENTE.md` / `FOCOS-REVISION.json`: tres focos puros propios, control esperado válido y trece mutaciones indebidas rechazadas. El revisor también contrastó los recibos por lectura; no ejecutó PostgreSQL, Edge, compilación, VM o QA.

## Reproducción y límites

`ENTORNO.json` fija rutas, hashes, versiones y comandos. Las dos pruebas requieren DLL/frontend explícitos y directorios de salida nuevos bajo `.local`, crean bases/cuentas sintéticas independientes y detienen sus propios procesos. Herramientas: Python3.12, Node24.21, Edge y PostgreSQL17.11 de la toolchain del proyecto. La DLL5eb1 y el frontend04f4 son privados; no existen en un clon limpio. No sustituirlos por un build del árbol compartido que mezcle MFA u otro trabajo.

La prueba cubre español y un puerto seleccionado de cada familia por objeto, no todas las combinaciones/idiomas, hardware, circuito eléctrico ni reinicio de Windows. No accede a VM, instalador, QA ni bases existentes. No contiene credenciales del laboratorio ni tokens de sesión.

La evidencia anterior de edición (`c2-room-object-codex`) y borrado individual/conjunto con impacto (`c2-delete-impact-codex`) se referencia por el alcance ya revisado, sin presentarla como ejecución nueva. El foco actual completa los campos/roles que faltaban en I-06.02; no acredita todo I-06, la integración en la candidata ni aceptación de Wascar.

## Cierre y métrica

I-06.02 pasa de in_progress a done tras revisión distinta. Peso fijo5/12; cierre del inventario pendiente pasa de87/14 a557/84, **6,21→6,63/100**,17/280subpasos done. No es un porcentaje global del producto. `LEDGER-ANTES.json` conserva la referencia y `CREDITO-I0602.json` explica el delta; textos, pesos, alcance y huella estructural permanecen fijados. Otros subpasos I-06 conservan sus pendientes.

Se actualizan continuidad, progreso y CHANGELOG sin modificar entradas históricas. Catálogo/guías QA permanecen iguales porque no hay funcionalidad visible nueva ni candidata habilitada. Codebase Memory refrescado:944archivos curados; es navegación, no un build integrado. Wascar informa que Claude continúa MFA-L1; este bloque no modifica su zona. C permanece cerrado y apagado según Wascar. Sin commits/push, adopción o paquete nuevo.

La primera generación del informe de progreso se detuvo porque este CIERRE todavía no existía; no escribió un informe válido. Se conserva el diagnóstico y se repite después de crear la evidencia requerida. La validación final de métrica y manifiesto se registra al terminar el bloque.

Comprobaciones finales: `progress_report.py --write` y `--check` pasan con557/84 y la huella estructural fijada. Gitleaks8.30.1 devuelve0 hallazgos en los dos tests, evidencia pública y cambios documentales seleccionados; no se examinó todo el historial ni se cierra la auditoría general de secretos. Fuentes de las pruebas y artefactos coinciden con los hashes de la ejecución. `SHA256SUMS.txt` fija el estado documental de este cierre; su informe se genera con el verificador del proyecto, sin reutilizar un manifiesto histórico.
