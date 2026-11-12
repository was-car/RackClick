# Revisión independiente F03 · refresco después de importar

12.11.2026. Ampliación acotada del coordinador a `ServerApp.jsx`, `AdminUsers.jsx` y `AdminInventoryData.jsx`. Complementa las revisiones F01/F02 sin sobrescribir su evidencia. Se toman los tres hashes definitivos comunicados por el coordinador y la adenda «integración del listado después de importar» de `RESULTADOS-FRONTEND.md`.

## Dictamen

**F03: ADDRESSED. Especificación y calidad favorables para esta ampliación.** La importación confirmada refresca clientes y permisos efectivos sin recargar la página, y conserva el recibo al cambiar únicamente la proyección por cliente. No se encontró un defecto nuevo en el alcance probado. F01/F02 siguen corregidos en el componente actualizado.

**16/16 comprobaciones Edge PASS ejecutadas por el revisor:** cinco del root real y once del componente/recuperación. React, RackClickApi e IndexedDB reales; frontera HTTP sintética/controlada. No son pruebas PostgreSQL ni GUI instalada/VM/QA de Wascar. No se repitieron411 ni se modificó producto o pruebas del implementador.

## Archivos y símbolos revisados

- `ServerApp.jsx:148`, `inventoryChanged`: captura generación de autenticación/actor, acepta sólo commits de Demo50/restore, relee `/me` y después casa autorizada/clientes en paralelo. Vuelve a comprobar vigencia antes de reemplazar Session/casa/clientes/selección. La consulta de permisos es necesaria: el contrato existente `allows(customerId)` consume la proyección por cliente y ésta crece legítimamente tras importar. No equivale a cambiar concesiones persistidas. Se conserva la guardia `systemhaus.read` y se propaga el callback por `AdminUsers`.
- `AdminUsers.jsx:20`: prop opcional `onInventoryChanged` y paso al panel; el resto de la ampliación funcional es ese enlace.
- `AdminInventoryData.jsx:12`–`:18`: ámbito ligado a instancia API, actor, Systemhaus, CSRF API/Session, capacidades globales y origen. Una nueva identidad de objeto Session o una nueva proyección de clientes por sí solas no reinician recibo/trabajo. Cambios de autoridad global/actor/CSRF invalidan el ámbito antiguo.
- `AdminInventoryData.jsx:27`–`:39`: una notificación por UUID confirmado de Demo50/restore en el ámbito; no se emite para copia, cancelación o `notRecorded`. El refresco no reenvía una mutación. El conjunto de operaciones notificadas evita duplicarla cuando falla cleanup y se consulta de nuevo el mismo recibo. La separación commit/integridad de F02 y el bloqueo externo corregido de F01 se conservan.
- Se leyeron `browser-admin-inventory-data-root.mjs` y la ampliación de `browser-admin-inventory-data-recovery.mjs`, el diff acotado de ServerApp/AdminUsers, la adenda y los helpers de `reload`/`refresh`/`forget`/`logout` para comprobar que el error de recarga tiene una salida real.

## Comprobaciones ejecutadas

Se copiaron los dos guiones a un directorio privado nuevo; al de root se añadió exclusivamente allí una sonda propia R04. Bundle esbuild `write:false`; sin cambiar `dist`. Node24.21.0 y Edge157.0.4341.46 existentes, sin instalar dependencias.

Root5/5:

1. Commit normal Demo50: navegación0→50, tarjetas50 y controles de edición del cliente recién abierto, sin Page.reload; el recibo sobrevive a renovar la proyección.
2. Reabrir Administración no repite la importación ni la consulta de sesión de la notificación anterior.
3. **R04 propia:** un503 controlado de `/me` durante la recarga posterior al commit deja el diagnóstico visible y ninguna intención pendiente. «Volver a clientes» ejecuta el refresco normal, recupera50clientes/permisos de edición y quita el error. El POST de importación sigue siendo exactamente uno.
4. Sin `systemhaus.read`, el refresco de clientes autorizado funciona y no consulta casa.
5. Respuestas de casa/clientes retenidas hasta después del logout no publican la sesión anterior ni los nombres de clientes.

Recuperación11/11: F01, F02 recuperado y por POST directo; cancelación confirmada; Demo50 y restore realmente inciertos preservados después de `notRecorded`/403; notificación única incluso con error al retirar journal; proyección de clientes conserva recibo; retirar capacidades globales lo oculta; respuesta tardía de otro actor o CSRF obsoleto se descarta; nombre de archivo literal y ningún contenido de archivo en journal/localStorage.

Comandos ejecutados desde `development/frontend` con `RACKCLICK_TEST_OUTPUT` distinto para cada salida y Node existente:

```powershell
& 'C:\RackClick_SVR\.local\node-v24.21.0-win-x64\node.exe' 'C:\RackClick_SVR\.local\admin-data-20261112\recontrast-f03-01\root-probe.mjs'
& 'C:\RackClick_SVR\.local\node-v24.21.0-win-x64\node.exe' 'C:\RackClick_SVR\.local\admin-data-20261112\recontrast-f03-01\recovery-probe.mjs'
```

Ambos exit0. Evidencia privada nueva en `C:\RackClick_SVR\.local\admin-data-20261112\recontrast-f03-01\`: guiones copiados, `root-execution.log`, `root/root-browser.json`, `recovery-execution.log`, `recovery/recovery-browser.json`, `before-hashes.json` y `final-hashes.json`. Comparación final: **cinco de cinco entradas idénticas antes/después**, incluidos los dos guiones fuente. `git diff --check` de ServerApp/AdminUsers: sin errores. No se sobrescribió la evidencia anterior.

## Identidad y límites

Tres fuentes funcionales finales:

| Archivo | SHA256 |
| --- | --- |
| `ServerApp.jsx` | `a1bc9bb6f1aa460491be0c68abdb1d0fddac79d1cd90d610dbd889d45c70fad2` |
| `AdminUsers.jsx` | `260f522e88e4b6f02a8585a738ad8fd27234427caef2e065e405cf97496855e5` |
| `AdminInventoryData.jsx` | `52a7dd73f07adf8a30e2b7108189aa8ddbecad97a04c4f048cb76088ae5fa31b` |

**Conjunto de estas tres fuentes:** `a00ad439a68c64980e8b8facb02a8bff4908d4a62b5fa5f6b493cc046d2d8035`.

**Conjunto de cinco entradas, añadiendo los guiones root/recovery:** `ad1bde60d7ebbfcfd1576bcb2a73988eb1ddf3af40a1d6f8a20a4336b5d06485`.

Método habitual: SHA256 de las líneas `ruta + TAB + hash_bytes + LF` en el orden del manifiesto privado. Los hashes coinciden exactamente con los comunicados por coordinación.

Límites: frontera HTTP sintética, no PostgreSQL del frontend; el componente completo de recuperación prueba la rama común Demo50/restore, mientras el ensayo root5 usa Demo50. No se acredita por él un restore GUI real ni invariancia SQL de seguridad. La suite411 y los rojos0→50/permisos del implementador sólo se atribuyen a su evidencia. No se revisa funcionalidad ajena a estas tres fuentes ni se exige evitar la renovación de `/me` necesaria para los clientes nuevos.

Progreso sin incremento:26,63/100 del cierre restante, sin porcentaje global nuevo. Continúa pendiente el ensayo GUI con snapshot backend768 del coordinador y la aceptación de la candidata.
