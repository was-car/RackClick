# Revisión independiente · edición de objetos de sala · 25.10.2026

Revisor: agente `room_edit_review`, perfil QA, distinto de Claude. Encargo acotado del coordinador; sólo lectura de producto/pruebas/evidencia pública. Único archivo escrito por este agente: este informe.

## Dictamen

El foco entregado acredita cuatro comandos GUI aceptados, lectura posterior y los rechazos/persistencia registrados en el ensayo de Claude. **No acredita todo I-06 ni roles de energía.** Hay un defecto P2 del comparador que impide aceptar, sólo con esa prueba, la afirmación de conservación completa de las propiedades no editadas. No se ha demostrado un fallo del producto mediante este hallazgo.

El quinto evento de auditoría es compatible con el cambio de idioma realizado por el escenario. La atribución exacta de esa fila requiere el desglose que hará el coordinador en su ensayo; las respuestas públicas no incluyen método ni acción de auditoría.

## Archivos y símbolos consultados

- `AGENTS.md`, `docs/BRIEFING-MAESTRO.md`: S1 autorizado, revisión distinta, fixtures aislados y límites de esta tarea.
- `development/server/tests/test_room_object_edit_gui.py`: `check_database` (línea30), `canonical`, `rows_by_id`, `main`, contadores antes/después y negativos. SHA256 de bytes originales: `e6a0093bcd4ec1cc31ee47bff31888fb6d38c65c84b976fa10947ae67adf090c`.
- `development/frontend/tests/browser-room-object-edit.mjs`: `stripDevice`, `editDevice`, `setPortStatus`, elección de idioma, escrituras observadas y lecturas de segunda cuenta/recarga. SHA256: `8570d08565f318d86ffe8ecfa8d2adbb9c30af39aad7f7fb4da0d57c86d70fdd`.
- `development/server/tests/test_room_device_move_gui.py`: fixture inicial de Dose/final, sus notas y puertos RJ45.
- `development/frontend/tests/browser-client-changes-support.mjs`: selección `es` en login y composición de sesiones.
- `development/server/src/RackClick.Server/UserPreferences.cs`: `Set` y registro de auditoría en líneas229–231, acción `user.preference.set`.
- `development/server/src/RackClick.Server/InventoryDevices.cs`: comprobación `power_role_invalid`, líneas142–143.
- `docs/C2-OBJETOS-SALA-CLAUDE-25-10-2026.md`, `evidence/s1-20261025/c2-room-object-claude/RESULTADO-NAVEGADOR.json`, `SALIDA-HARNESS.txt`: resultados y límites comunicados por Claude, no nuevas ejecuciones del revisor.

## Hallazgos

### P2 · propiedades no editadas fuera del comparador

`check_database` excluye `properties` completo de la comparación de las dos filas editadas; sólo exige que coincidan `notes.sn` y `notes.text` con los valores nuevos. `stripDevice` hace la misma exclusión en el navegador. Color, preset/propiedades adicionales y otras notas podrían perderse o cambiar sin que fallen estas aserciones.

**Prueba propia en memoria:** se extrajeron mediante AST los cuatro constantes y las tres funciones públicas, sin importar el harness ni sus utilidades de laboratorio. Sobre nueve colecciones sintéticas se comprobó un estado válido, y se aplicaron seis mutaciones indebidas individualmente. Las seis fueron aceptadas por el comparador:

1. Cambiar `properties.color`.
2. Borrar una propiedad sentinel del dispositivo final.
3. Cambiar `notes.model`.
4. Borrar `notes.ip`.
5. Cambiar `notes.firmware`.
6. Añadir una propiedad arbitraria.

Como controles de sensibilidad, cuatro mutaciones en campos sí comparados fueron rechazadas correctamente: nombre editado erróneo, grupo cambiado, otro atributo del puerto alterado y extremo de cable modificado. El control válido pasó. Esto distingue un hueco concreto de cobertura de un comparador que no se ejecutase.

Para completar la afirmación de conservación, el esperado debe derivar del estado anterior y aplicar sólo cambios previstos, comparando las propiedades completas. La fixture actual sólo proporciona `notes.sn/text`: el formulario ofrece cinco notas, por lo que puede añadir `model/ip/firmware` vacíos. Esa normalización debe distinguirse de cambiar un atributo previamente existente; no imponer una compactación o semántica nueva al producto para satisfacer el test.

### P3 · etiquetas antiguas de «rol» en una prueba de estado

El docstring Python y la bandera `databaseEditsOnlyNameNotesAndPortRole` todavía dicen rol de energía; el escenario final realmente cambia `status` a `reserved`. Los documentos de entrega y los comandos reflejan correctamente ese límite. Es corrección de redacción/etiqueta de prueba, no motivo para cambiar la regla del producto ni afirmar que se probó `powerRole`.

El rechazo de un rol no `unspecified` en un puerto distinto de `power` concuerda con la condición explícita del servidor (`power_role_invalid`). No ejecuté ese rechazo; lo atribuyo al primer intento informado y a la fuente consultada.

## Cuatro comandos y cinco eventos

Hechos públicos contrastados:

- El informe del navegador contiene exactamente cuatro respuestas200 a `/commands`.
- El escenario selecciona `es` en `.rc-settings select` antes de tomar su snapshot base y editar los objetos.
- Hay seis respuestas200 de `/api/v1/me/preferences` entre las distintas sesiones/lecturas. El informe sólo publica path/status, no método HTTP.
- `UserPreferences.Set` registra `user.preference.set` además de las operaciones de inventario.
- El harness mide el contador global de `audit_event`, no sólo acciones `inventory.*`, antes de abrir el escenario.

Por tanto, una preferencia de idioma es una explicación fundada del evento adicional; no corresponde afirmar por esos seis response records cuál fue la fila exacta. El coordinador puede cerrar la atribución mediante acciones/request IDs medidos. No hay evidencia aquí de un quinto cambio de inventario ni de un fallo de atomicidad.

## Pruebas y límites

- **Ejecutadas por este revisor:** un control válido, seis mutaciones ciegas y cuatro controles rechazados, en memoria Python sobre las funciones reales extraídas; lectura de hashes originales y respuestas públicas.
- **No ejecutadas:** Edge, HTTP, PostgreSQL, migraciones, instalador, cuentas, servicios, VM, QA, compilaciones o suites generales. No accedí a `.local`, contraseñas o credenciales.
- El PASS25,968s/PostgreSQL17.11 corresponde a Claude. No se presenta como ejecución nueva propia.
- Sólo español, un puerto RJ45 por objeto y edición de su estado. Potencia, edición masiva, todas las propiedades/roles y todo I-06 permanecen fuera de este foco.
- No se modifican métricas ni se propone un porcentaje global. La eventual evidencia adicional del coordinador complementará este dictamen sin cambiar retrospectivamente qué ejecutó el revisor.

## Adenda · refuerzo de los comparadores por el coordinador

El coordinador conservó los tests originales en esta carpeta y reforzó únicamente sus comprobaciones y fixture, sin modificar el producto. Se revisó la nueva fuente estable: Python SHA256 `e9552f01438ea7035b7e1d268cc6ac446da135b2a694d058e88ea28aa52c1d0e`.

**P2 de cobertura resuelto en los tests.** `check_database` parte de una copia del estado anterior, aplica únicamente nombre, `notes.sn/text`, normalización vacía de las tres notas conocidas que estuvieran ausentes, y el estado de los dos puertos previstos. Compara las nueve tablas completas. El escenario de navegador usa `editedDevice` y también compara el objeto completo, incluidas sus propiedades.

Nueva sensibilidad propia en memoria contra esa función real: control válido PASS, estado anterior sin mutar, segundo control de notas conocidas ausentes normalizadas a vacío PASS y **6/6 rechazos** de las mismas mutaciones que antes pasaban (color, sentinel, model, ip, firmware y propiedad arbitraria). La fixture reforzada añade además propiedades ajenas y notas no vacías para evitar una conservación vacua.

**P3 de etiquetas corregido:** docstring y bandera del harness ahora dicen estado del puerto (`databaseEditsOnlyNameNotesAndPortStatus`). No se presenta como prueba de roles de energía.

La contabilidad nueva exige expresamente dos `inventory.device.update`, dos `inventory.ports.update` y un `user.preference.set`, cuatro filas `operation` y revisión de inventario `+4`. Los negativos comparan el estado completo de cliente, operaciones y auditoría mediante `atomic_state`, además de las tablas de inventario. Esas son aserciones inspeccionadas; la confirmación mediante ejecución corresponde al ensayo independiente del coordinador, pendiente de contrastar aquí cuando publique su recibo.

No repetí Edge, HTTP o PostgreSQL ni modifiqué tests/producto. Esta adenda no convierte la ejecución original de Claude en una ejecución nueva del revisor.

## Adenda final · ensayo independiente del coordinador contrastado

**Dictamen vigente: conforme aceptar el foco de edición de Dose/dispositivo final, con el comparador reforzado.** El P2 inicial queda resuelto en las pruebas; el quinto evento ya está explicado por medición. No se necesita otra repetición de este foco ni se acredita todo I-06.

Se leyeron `EDGE-PG-INDEPENDIENTE.json` y `EDGE-BROWSER-INDEPENDIENTE.json`, correspondientes a una ejecución nueva del coordinador: **PASS27,656s**, PostgreSQL17.11, entradas inmutables, laboratorio y servidores propios detenidos. Se comprobaron mediante aserciones propias sobre esos recibos:

- Cuatro respuestas HTTP200 de comandos; cuatro operaciones de inventario y revisión `+4` exigida por el escenario.
- Acciones añadidas medidas en PostgreSQL: `inventory.device.update=2`, `inventory.ports.update=2`, **`user.preference.set=1`**. El quinto registro corresponde a la preferencia de idioma, no a un quinto comando de inventario.
- Comparación exacta de nueve tablas con la fixture de metadatos/notas reforzada; sólo cambios previstos de nombre/notas/estado del puerto.
- Rechazos403/404/422, revisión y `atomic_state` íntegros; recarga/otra sesión y persistencia tras reiniciar el proceso; navegador sin excepciones JS registradas.
- `inputs==finalInputs`, `inputsUnchanged=true`, `labStopped=true` y `serversStopped=true`.

Hashes leídos: `EDGE-PG-INDEPENDIENTE.json` = `5e09757143f93ab1cacf5dc0f05984f3171b752236d674a605156c9807dedecf`; `EDGE-BROWSER-INDEPENDIENTE.json` = `9b1fba33608a832fdf9c02df4334b4d01dc1f1f7d283265df4a51f6a7fb5b93d`.

La ejecución real es del coordinador, distinta de la ejecución original de Claude. Este revisor ejecutó sólo las sensibilidades en memoria y las aserciones de lectura de recibos; no repitió Edge/PG/HTTP ni accedió a VM o privados. Se mantienen los límites de español, un puerto/estado por objeto y ausencia de cobertura de roles de energía, edición masiva o todo I-06. Sin modificación del producto ni métricas.
