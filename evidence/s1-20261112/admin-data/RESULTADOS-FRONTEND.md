# Panel de datos y copias de inventario · frontend

12.11.2026. Tarea2 del plan `docs/superpowers/plans/2026-11-12-admin-data.md`, en el worktree separado `feature/admin-data-20261112`. Implementación frontend; revisión independiente, compilación conjunta y ensayo PostgreSQL asignados al coordinador. Sin commits, push, instalaciones, cambios VM, backend, dependencias ni locks.

## Resultado implementado

- Administración muestra Datos y copias de inventario sólo con las dos capacidades globales `systemhaus.manage` y `security.manage`. Exportar exige además lectura/exportación global; importar, creación de clientes/edición global. El servidor conserva la autoridad definitiva.
- Tres tarjetas RC9 EN/DE/ES: cargar Demo50 sólo en vacío y con confirmación, crear/descargar copia global de inventario, seleccionar JSON/previsualizar/restaurar sólo en vacío con confirmación. La leyenda excluye expresamente cuentas, claves, permisos, sesiones, MFA, preferencias y plantillas; distingue la copia de inventario de PostgreSQL y Windows. No se traduce ningún nombre guardado o nombre de archivo.
- Fases con `progress` indeterminado y texto de la tarea real; sin porcentajes estimados. Recuentos, revisión y recibo de commit visibles. SHA256 y longitud se verifican mediante WebCrypto antes de habilitar la descarga; nombre ligado al UUID de la operación.
- Límite32MiB comprobado antes de leer/asignar bytes; base64 validado antes de decodificar. Archivo y Blob sólo en memoria. Journal IndexedDB durable sólo con intención pequeña ligada a origen/Systemhaus/actor, UUID, acción, revisión y SHA/longitud si restore. Escritura confirmada antes del POST; comparación transaccional antes de sustituir o eliminar.
- Una sola transmisión por acción. Pérdida de respuesta, `notRecorded`,403 y412 conservan el journal. La recarga consulta el recibo original; nunca repite la mutación. Cancelación explícita añadida sólo después de confirmar el endpoint real con el coordinador: conserva acción/SHA/revisión/requestId y sólo limpia tras `cancelled` confirmado o commit original validado. Un recibo de commit conocido no puede convertirse después en cancelación.
- Los otros controles de Administración quedan deshabilitados mientras esta sección carga, trabaja o conserva una intención. Se preservan borradores de los componentes existentes. Cambio de actor/generación impide actualizar estado antiguo.403/401 oculta recuentos/descarga/recibo visible y conserva la intención.

## Archivos y símbolos

Nuevos: `src/AdminInventoryData.jsx` (`AdminInventoryData`, `InventoryDataCounts`); `src/admin-inventory-data.ts` (`inventoryDataAllowed`, `prepareInventoryDataIntent`, `readInventoryData`, `readInventoryDataFile`, `previewInventoryData`, `confirmedInventoryData`, `sendInventoryData`, `inventoryDataStatus`, `cancelInventoryData`, `verifyInventoryDataArchive`, `inventoryDataJournal`, `executeInventoryDataIntent`, `completeInventoryDataIntent`); `src/admin-inventory-data-words.ts` (`inventoryDataWords`); tres pruebas `tests/admin-inventory-data.test.mjs`, `tests/browser-admin-inventory-data-journal.mjs`, `tests/browser-admin-inventory-data.mjs`.

Integraciones asignadas: `src/AdminUsers.jsx` (`AdminUsers`, bloqueo de controles) y `src/AdminSectionNavigation.jsx` (`AdminSectionNavigation`, acceso condicionado). Se preservaron CRLF y los cambios concurrentes ajenos.

Consultados: `AGENTS.md`, `docs/BRIEFING-MAESTRO.md`, documentos de esta entrega/plan y continuidad/progreso; `api.ts` (`RackClickApi.request/sendMutation`, `allows`, `ApiError`, `Session`); `admin-user-state.ts` (`stateJournal`, `stateStatus`), `admin-users.ts`, `user-preferences-journal.ts`, `AdminUserState.jsx`, `AdminUsers.jsx`, `AdminSectionNavigation.jsx`, `AdminGroups.jsx`, `server.css`; patrones `browser-quince-support.mjs`, `browser-admin-navigation.mjs`, `run_frontend_smoke.py`, `admin-user-state.test.mjs`, `test_admin_group_receipt1449.mjs`, `test_admin_user_onboarding.mjs`; `build.mjs` y `package.json` sólo lectura.

## Investigación y decisión

Reutilizados React global RC9 y `RackClickApi`, patrón journal propio de IndexedDB y runner Edge/CDP existente. Sin nueva biblioteca ni cambio de versión/licencia. Node24.21.0 y esbuild0.25.10 ya existentes. Se aplicaron `react-best-practices`, TDD/`writing-good-tests` y verificación antes del cierre.

Fuentes primarias consultadas el12.11.2026: [WebCrypto digest](https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/digest), [Blob.arrayBuffer](https://developer.mozilla.org/en-US/docs/Web/API/Blob/arrayBuffer), [IndexedDB.transaction/durability](https://developer.mozilla.org/en-US/docs/Web/API/IDBDatabase/transaction), [React: efectos](https://react.dev/learn/you-might-not-need-an-effect). APIs nativas compatibles con Edge; digest requiere contexto seguro (loopback admitido en los ensayos). Documentación React actual no motivó actualizar el React adoptado.

## Pruebas ejecutadas

Windows, Node24.21.0, Edge nativo headless/CDP; sin instalar herramientas.

1. Rojo inicial:14/14 fallos explícitos por adaptador aún ausente; verde14/14 tras implementarlo. Ampliación de cancelación:14PASS/2FAIL por endpoint adaptador ausente →16/16PASS. No se contó un error de import como rojo: las pruebas capturaron módulo ausente y emitieron una aserción deliberada.
2. Regresión pertinente final: `node --test` con `admin*.test.mjs`, `api.test.mjs`, `test_admin_user_onboarding.mjs`, `test_admin_group_receipt1449.mjs`: **411/411PASS**,0omitidas. Salida íntegra sanitizada en `frontend-node.log`. Aviso heredado `MODULE_TYPELESS_PACKAGE_JSON`; package sin cambios por ownership.
3. `browser-admin-inventory-data-journal.mjs`: **PASS**, cinco comprobaciones con IndexedDB real: write/read durable, separación de actor/house/origen, rechazo de reemplazo/eliminación ajenos/material completo, persistencia tras `Page.reload`, dos transacciones competidoras con una sola intención admitida. Resultado en `frontend-journal-browser.json`.
4. Esbuild aislado `bundle:true,write:false` de `AdminUsers.jsx`: PASS. No generó `dist` ni ejecutó buildfrontend final. `node --check tests/browser-admin-inventory-data.mjs`: PASS; `git diff --check` de las dos integraciones: PASS.

## No ejecutado y límites

- El guion **preparado pero no ejecutado por este implementador** `browser-admin-inventory-data.mjs` necesita el build conjunto/DLL y un laboratorio PostgreSQL vacío del coordinador. Cubre idiomas, cancelación real tras aborto preenvío, Demo50 con respuesta perdida después de commit y recuperación por recarga, segunda sesión/cuentas/permisos/nombres, descarga real con hash, selección/previsualización y bloqueo de restore poblado, foco/móvil390px. No presentarlo como PASS por existir o por `node --check`.
- Restore GUI sobre otro Systemhaus vacío, negativas backend y recuperación operativa deben acreditarse por sus ensayos propios; no se deducen del adaptador ni de IndexedDB. Sin ensayo instalado/VM/QA/adopción de Wascar.
- El bloqueo visual de otras mutaciones comprende Administración; navegación a clientes sigue disponible. La exclusión/concurrencia de otras sesiones y áreas depende de las guardias del servidor.
- No se modificaron `CONTINUIDAD`, `CHANGELOG`, catálogo QA, guía ni manifiestos: son propiedad del cierre conjunto del coordinador. No se incrementa métrica: referencia actual26,63/100 del cierre restante; no es porcentaje global nuevo del producto.

## Hallazgos con gravedad

- **P1 controlado:** respuesta incierta o journal no durable podía permitir duplicar/importar sin recuperar; se bloquea POST hasta journal confirmado y sólo se consulta el UUID original. Pruebas de pérdida de respuesta, actor/destino distintos y recibos malformados.
- **P1 controlado:** archivo alterado o excesivo no debe descargarse/asignarse; límite previo, digest/longitud y nombre exacto comprobados, sin guardar material en storage.
- **P2 resuelto por contrato ampliado:**412 seguido de `notRecorded` carecía de una salida segura con el contrato inicial sin cancelación. Coordinador/backend confirmaron cancelación explícita; se añadió con pruebas rojo/verde. No se inventó rollback a partir de `notRecorded`.
- **Pendiente de acreditación:** GUI completa contra PostgreSQL y revisión independiente del lote. Los verdes anteriores sólo demuestran el alcance descrito.

## Adenda · correcciones F01/F02 de revisión independiente

12.11.2026, ronda1. Se aplicaron `receiving-code-review` y `systematic-debugging`: primero reproducción sobre los bytes entregados y luego una corrección por fallo. La reproducción del revisor se copió a un destino propio, sin modificar sus informes. Confirmó ambos hallazgos con el mismo setHash original de ocho fuentes: `b2c7412a011b4b7de4ca93482e1b5bc925b7c129a6a880947443ec7e01365a95`. Snapshot íntegro, diff previo y manifiesto conservados en `.local/admin-data-review-fixes-01/`.

**F01 · bloqueo general por fallo local del journal, corregido.** La causa era `!ready` en el aviso de bloqueo a `AdminUsers`: un `indexedDB.open` fallido dejaba ese indicador falso aunque no existiera intención ni POST. Se eliminó esa condición sólo del bloqueo externo. Trabajo en curso o intención pendiente siguen bloqueando los otros controles; un fallo local sin intención bloquea únicamente las mutaciones de Datos, con diagnóstico visible. `ready` continúa siendo requisito antes de enviar cualquier operación de inventario.

**F02 · backup confirmado con archivo corrupto, corregido.** La verificación del archivo se ejecutaba dentro de la retirada del journal, antes de borrar una intención que el servidor ya había confirmado. SHA incorrecto hacía que check/cancel-committed repitieran el mismo bloqueo. Se separaron hechos: primero se valida y recuerda el recibo, se retira su intención y se actualiza el estado; después se verifica el archivo para habilitar descarga. Un SHA incorrecto conserva el recibo de commit y el diagnóstico, no ofrece descarga y libera Administración. No repite el POST. Demo50 y restore sin confirmar no usan esta salida y conservan su intención original.

Cambios de producto: sólo `src/AdminInventoryData.jsx` (`useLayoutEffect` de bloqueo y `committed`). Nuevo guion propio `tests/browser-admin-inventory-data-recovery.mjs`, adaptado a partir de las reproducciones independientes. **Sin cambios de contrato, backend, dependencias, build final o VM.**

Verificación:

- Reproducción original: F01 y F02 reproducidos con fuentes inmutadas.
- Guion de regresión con expectativas correctas: rojo por F01 → corregido F01, rojo por F02 → corregido F02, verde final.
- Edge157.0.4341.46/React adoptado/IndexedDB real: **9/9 controles PASS**. Incluye diario inaccesible sin intención y después de refresh; backup recuperado y POST directo con SHA incorrecto; ausencia de descarga/reenvío; cancelación expresa; Demo50 y restore retenidos después de `notRecorded` y403; respuesta tardía de otro actor; nombre literal y ausencia de material completo en storage.
- Una regresión pertinente final Node24.21.0: **411/411PASS**,0omitidas, en `frontend-node-review01.log`. `node --check` del nuevo guion y `git diff --check` de las integraciones: PASS.
- El ensayo Edge usa dobles de la frontera API para reproducir fallos controlados, con React e IndexedDB reales. **No acredita PostgreSQL, GUI integrada ni QA de Wascar.** Esos ensayos siguen siendo del coordinador/revisión independiente.

Evidencia sanitizada: `frontend-review01-before-hashes.json`, `frontend-review01-after-hashes.json`, `frontend-review01.patch`, `frontend-review01-browser.json`, `frontend-review01-red-F01.log`, `frontend-review01-red-F02.log`. SetHash de las mismas ocho fuentes tras corregir: `9098f445d7d199e6c2f6e881353c8d61d3177c0a3e3f09163098336d714c66d7`; SHA256 de `AdminInventoryData.jsx` corregido: `e483661b4aba860a7ec451f02e1da688c3bcc9f244c13825c643fd5a91fadab8`. El manifiesto posterior añade por separado el nuevo guion. La métrica permanece sin cambio.

## Adenda · integración del listado después de importar

12.11.2026, ampliación de ownership por el coordinador a `ServerApp.jsx`, exclusivamente callback de datos. **P2 reproducido y corregido:** una importación Demo50 normal obtenía commit y retiraba el journal, pero la navegación conservaba0clientes hasta una recarga. El enlace global `.ir-all-clients` sólo cambiaba la página; no consultaba clientes/casa de nuevo. La prueba anterior con respuesta perdida más `Page.reload` ocultaba ese defecto.

Primero se corrigieron dos errores del guion de integración, sin cambiar producto: idioma se selecciona en Settings de Clientes y luego se vuelve a Administración; la comprobación de seguridad compara identidad y capacidades globales. `permissions.customers` crece legítimamente después de importar por la proyección de concesiones globales, y no demuestra un cambio de grants. La invariancia SQL se acredita en las pruebas backend, no con esa comparación incorrecta.

Antes del cambio funcional, `browser-admin-inventory-data-root.mjs` ejecutó **ServerApp, AdminUsers, AdminInventoryData, RackClickApi, React adoptado e IndexedDB reales** contra una frontera HTTP sintética: rojo explícito **0≠50** en enlaces de clientes después del commit normal, sin recarga. Snapshot/hash de las tres fuentes y salida roja preservados. El primer arranque del arnés tenía un prefijo API incorrecto y terminó en timeout; se corrigió el arnés antes de registrar el rojo significativo, manteniendo ambos intentos privados.

Cambios:

- `ServerApp.jsx`: `inventoryChanged` relee primero `/me` para obtener permisos efectivos de los clientes nuevos; después `api.house` sólo con `systemhaus.read` vigente y `api.customers` en paralelo. Comprueba generación de autenticación y actor antes/después de esperar y actualiza Session/casa/clientes/selección sin mutar objetos existentes.
- `AdminUsers.jsx`: prop opcional `onInventoryChanged` hacia la sección asignada.
- `AdminInventoryData.jsx`: una notificación por UUID de operación confirmada Demo50/restore en el ámbito actual. No notifica backups, cancelaciones ni resultados desconocidos. La notificación no reenvía ninguna mutación, se conserva incluso si falla la limpieza local y no se vuelve a emitir al consultar el mismo recibo. Su ámbito se liga a API/origen/actor/casa/CSRF/capacidades globales; renovar sólo la proyección de permisos por cliente conserva el recibo, mientras retirar capacidades globales o cambiar CSRF/actor invalida respuestas antiguas.
- Guiones: recorrido de idiomas y comparación de seguridad corregidos; nuevo `browser-admin-inventory-data-root.mjs`; recuperación ampliada con comprobación de emisión única/ausencia de emisión.

La primera solución mantenía Session sin renovar `/me`; una nueva prueba mostró otro rojo significativo: listado50 pero cliente nuevo sin controles de edición, porque `allows(customerId)` usa `permissions.customers`. Esa versión se descartó y su salida/hash/diff se conservan bajo `frontend-root-refresh-list-only-*`; no representa el producto final. Se sustituyó la aserción de detalle `/me sólo1` por abrir un cliente recién importado y comprobar su control de edición real, sin recargar.

Verificación final del implementador: **411/411 Node PASS**,0omitidas; **4/4 controles Edge del root real PASS** (listado50, tarjetas y edición del cliente nuevo sin recargar, recibo conservado al renovar proyección, respeto de HouseRead, respuesta tardía tras logout descartada); **11/11 controles Edge de recuperación PASS**, incluida una sola notificación cuando falla cleanup y se consulta otra vez el recibo, revocación global y respuesta con CSRF obsoleto. `node --check` de guiones y `git diff --check`: PASS. Esbuild sólo `write:false` dentro de las pruebas; no buildfrontend final ni cambio backend/paquete.

Evidencia vigente: `frontend-root-refresh-before-hashes.json`, `frontend-root-refresh-after-hashes.json`, `frontend-root-refresh.patch`, `frontend-root-refresh-red.log`, `frontend-root-permissions-red.log`, `frontend-root-refresh-browser.json`, `frontend-root-refresh-recovery.json`, `frontend-node-root-permissions.log`. Las corridas GUI contra PostgreSQL pertenecen al coordinador; estos verdes no se presentan como PostgreSQL ni QA de Wascar. Métrica sin cambio.
