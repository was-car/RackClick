# Cobertura de los modelos elegidos

Fecha de conciliación: 2026-11-02. [Lista original fija](../development/hardware/selected-models-506.json) · [Estado por modelo JSON](COBERTURA-MODELOS-ELEGIDOS.json) · [CSV de los 506](COBERTURA-MODELOS-ELEGIDOS.csv).

| Alcance | Con perfil en desarrollo | Pendientes |
|---|---:|---:|
| Objetivo de al menos 500 modelos comerciales | 861 | 0 para alcanzar 500 |
| Los 506 modelos concretos de la selección original | 506 | **0** |

Las tandas ampliaron la cartera con **355 modelos adicionales** que no coinciden con la selección original. Por eso llegar a 500 en total y completar los 506 elegidos son resultados distintos. La cobertura de identidades de aquella selección es 100,00%; esto no es el porcentaje global del proyecto ni de aceptación QA.

La conciliación anterior sólo por nombres registraba 44 coincidencias. Se añaden siete vínculos de SKU revisados explícitamente en [selected-profile-links.json](../development/hardware/selected-profile-links.json), sin crear duplicados, y los perfiles curados por grupos (17 de selected506a, 50 de selected506b, 50 de selected506c, 50 de selected506d, 50 de selected506e, 50 de selected506f, 50 de selected506g, 6 de selected506h, 5 de selected506i, 13 de selected506j, 52 de selected506k, 62 de selected506l). No se introduce un alias general HPE→Aruba. Los límites de consola, RPS y revisiones físicas se conservan.

Hay 861 perfiles comerciales en desarrollo. El resto de perfiles sintéticos se excluye del conteo. Las coincidencias conservan `+`, modelo y SKU; se normalizan sólo formato y alias de fabricante cerrados. Un modelo vecino, otra RAM, una referencia de familia o una foto no sustituyen el perfil seleccionado. Las coincidencias de modelo no certifican todas las revisiones físicas.

## Qué queda de la selección original

| Categoría | Sin perfil correspondiente |
|---|---:|

Los 0 pendientes están identificados en JSON/CSV. Las siguientes tandas deben salir de esa lista fija; cualquier incorporación fuera de ella se registra por separado. Algunos modelos requieren ampliar antes el contrato de puertos, módulos, alimentación o montaje: no se deben inventar combos independientes, QSFP como SFP, conexiones SAS/FC, capacidad eléctrica o accesorios para completar el dibujo.

El lote 05 histórico aporta cien modelos. Su visor `VER-100-MODELOS-05.html` está disponible en el repositorio completo y en su propio ZIP, fuera de los paquetes de revisión de la selección. Conserva fuentes y vistas sin confirmar explícitas. Revisión visual de Wascar, variantes pendientes y candidata instalada siguen separadas del conteo. La lista original incluye modelos con sólo material de referencia; no declara plantillas instaladas.

Reproducción: `C:/Python312/python.exe -X utf8 -B tools/build_hardware_coverage.py --check --as-of 2026-11-02`. El auxiliar verifica hashes de los manifiestos de desarrollo y no cambia DB, VM, resultados QA ni pesos del ledger. Índice del cierre restante: 9,76/100, sin nuevo porcentaje global por contar modelos.
