# Revisión independiente del frontend de datos y copias de inventario

12.11.2026. Revisor distinto del implementador, por encargo del coordinador. Worktree `C:\RackClick_SVR\.local\github-installable-20261112\worktree`, base `98ad43582dcf08b3227f16873175625048dc09bd`, cambios aún sin commit. No se modificaron producto ni pruebas del autor, backend, dependencias, VM o instalaciones; sin commit/push, subagentes ni compilación .NET.

## Dictamen

**Contrato principal conforme por lectura y focos aislados, con aceptación integrada pendiente. Calidad: requiere corrección de dos P2 antes de cerrar el frontend.** Ambos hallazgos se reproducen con React, Edge e IndexedDB reales y dobles de API sintéticos; afectan la disponibilidad de los controles de Administración. No se encontró en el conjunto revisado un P0/P1 reproducible de autorización, ejecución de HTML o persistencia del archivo en storage. Esto no certifica el backend ni la candidata instalada.

Las 411 pruebas del informe del implementador son evidencia atribuida a éste. No se repitieron ni se contabilizan como ejecuciones del revisor. La presente revisión aporta **dos defectos reproducidos y siete comprobaciones positivas propias**.

## Hallazgos reproducibles

### F01 · P2 · Un fallo del journal nuevo inutiliza controles de cuentas y grupos aunque no exista operación de inventario

Archivos: `development/frontend/src/AdminInventoryData.jsx:20`, `:22`, `:45`, `:54`; `development/frontend/src/AdminUsers.jsx:23`, `:76`.

`onBlockedChange` permanece verdadero cuando `ready` es falso. Un error al abrir/leer el journal deja `ready=false`; el nuevo `fieldset` aplica ese estado a todos los controles administrativos anteriores, incluidos grupos, cuentas y métodos de autenticación. Esta dependencia se activa al entrar en Administración, antes de que se solicite una operación de inventario.

Reproducción independiente F01:

1. Montar el `AdminUsers` real con sesión global válida, respuesta válida de usuarios y el resto de IndexedDB funcionando.
2. Hacer que únicamente `indexedDB.open('RackClick.AdminInventoryData.v1')` falle con `SecurityError`.
3. Comprobar que aparece el error del journal, no hay intención pendiente y no hubo POST.
4. `document.querySelector('[data-admin-account-controls]').disabled` da `true`.
5. Pulsar «Actualizar estado del inventario»: el error y el bloqueo continúan.

Efecto: un problema local de almacenamiento de esta función impide mantener usuarios/permisos desde la misma página aun sin una mutación por conciliar. Reentrar con el mismo navegador no elimina la causa. El texto sólo explica que no puede enviarse una operación nueva; no ofrece salida para seguir administrando cuentas. Se considera P2 por el impacto sobre funciones existentes, aunque el bloqueo general aparezca descrito en la evidencia del autor.

Resultado esperado: conservar la prohibición de enviar inventario sin journal y la protección de cualquier intención desconocida, con una salida que permita usar las operaciones administrativas independientes que sigan siendo seguras. No se propone borrar un journal desconocido ni afirmar rollback.

### F02 · P2 · La verificación fallida de un archivo mantiene Administración bloqueada después de reconocer el commit de la copia

Archivos: `development/frontend/src/AdminInventoryData.jsx:24`, `:26`, `:28`, `:30`, `:34`, `:55`, `:56`; `development/frontend/src/admin-inventory-data.ts:167`, `:174`, `:175`; integración del `fieldset` en `AdminUsers.jsx:76`.

`completeInventoryDataIntent` reconoce el recibo y llama a `remember`, pero la función de eliminación del journal verifica primero el archivo. Si falla SHA, base64, UTF-8 o WebCrypto, no alcanza `inventoryDataJournal('remove', ...)` ni `clear`. Queda una intención pendiente y el bloqueo administrativo permanece. Consultar o cancelar, si devuelve el commit ya realizado, repite la misma verificación fallida.

Reproducción independiente F02:

1. Persistir una intención pequeña `backup`, revisión7 y UUID original.
2. Montar el `AdminUsers` real y devolver a la consulta un recibo de commit estructuralmente válido para ese UUID/revisión, con archivo de2bytes `e30=` y SHA `000…000`.
3. Se muestra el error de integridad y la descarga está ausente, lo cual es correcto. También permanece la intención y `fieldset.disabled=true`.
4. «Consultar resultado original» devuelve el mismo commit: no libera el journal.
5. Confirmar «Cancelar solicitud pendiente» y responder con el commit original, como corresponde cuando ya se confirmó: vuelve al mismo error y sigue el mismo UUID en IndexedDB.

Efecto: un fallo de integridad de un artefacto de exportación pasa a impedir administrar cuentas y grupos. La interfaz reconoce el commit, pero presenta simultáneamente una petición pendiente sin salida normal. La persistencia del journal hace sobrevivir la causa a la recarga. No se afirma que el backend actual produzca un archivo corrupto: esta es una prueba de manejo frontend de una respuesta/artefacto defectuoso, precisamente una ruta que la UI contempla.

Resultado esperado: distinguir el commit de la validez de su archivo; tras un recibo de copia correctamente vinculado, conservar error/descarga bloqueada y permitir terminar su conciliación sin reenviar automáticamente la copia. Importaciones realmente inciertas deben seguir protegidas. No se recomienda aceptar un recibo mal vinculado ni permitir descargar bytes no verificados.

## Cumplimiento y seguridad del conjunto

- **Ámbitos y API:** `inventoryDataAllowed` usa únicamente concesiones globales mediante `allows(session, capability)` sin cliente; requiere ambas capacidades administrativas y las adicionales de cada acción. La navegación y el panel siguen esas condiciones. Los controles ocultos no sustituyen el servidor. Se contrastaron las siete rutas reales de `InventoryDataAdministrationEndpoints.MapInventoryDataAdministration` con los paths/cuerpos del adaptador.
- **Origen, actor y Systemhaus:** `InventoryDataContext`, `sameContext`, `requireContext` y `validInventoryDataIntent` vinculan el journal a origen/Systemhaus/actor y conservan requestId/revisión. La API usa URL relativa, cookies de mismo origen, CSRF y actor para mutaciones. El navegador aporta Origin; se leyó su validación y la del CSRF en `Program.cs:250` y `:269`. No se probó aquí el rechazo HTTP real ni revocación SQL. El control C02 confirma que una lectura tardía después de cambiar el actor no publica el estado.
- **Intención antes de enviar:** `executeInventoryDataIntent` espera la escritura durable antes del único envío. `notRecorded` no elimina la intención. Consulta y cancelación conservan UUID/acción/revisión/digest, sin reimportación automática. C01 comprobó una cancelación confirmada que sí libera el journal. Los conflictos/403 mantienen intención; una pérdida permanente de autoridad puede también bloquear controles independientes por la misma integración general descrita en F01, sin acreditar ese escenario como ejecución propia.
- **Archivo sólo en memoria:** lectura, base64, recibo y Blob viven en memoria. `inventoryDataJournal` acepta un esquema pequeño y cerrado, no contenido del archivo ni cuentas/tokens. La lectura está acotada antes de `arrayBuffer`. C04 comprobó que seleccionar y calcular hash no crea ningún registro en el journal real. No se encontró uso nuevo de localStorage/sessionStorage, HTML directo o evaluación dinámica en el producto revisado.
- **Integridad y límites:** nombre exacto ligado a operationId, longitud/base64 canónico, SHA y UTF-8 se comprueban antes de crear la descarga. C05 ensayó un Blob real de exactamente32MiB con texto multibyte y verificación completa; C06/C07 rechazaron UTF-8 inválido y base64 no canónico aun con los bytes/digest correspondientes. La cuenta de filas/clientes y los montajes pertenecen al archivo/validador servidor: el frontend presenta sus recuentos y exige preview/digest/revisión, sin reinterpretar ni transformar la topología. No se certifican relaciones/montajes o100000filas/500clientes mediante estos focos.
- **React/XSS:** textos, nombres de archivo y recuentos se renderizan como datos React. C03 conservó literalmente un nombre `<img ... onerror=...>.json`, sin nodo img ni ejecución. Los efectos usan una generación de alcance para descartar trabajo antiguo; el bloqueo general añadido es el problema de calidad señalado, no una necesidad demostrada para todas las funciones de Administración.
- **Texto y alcance:** EN/DE/ES explican que es copia de inventario, excluyen seguridad/preferencias/plantillas y distinguen PostgreSQL/Windows. Demo y restore requieren confirmación y destino vacío; no anuncian fusión, sobrescritura, progreso porcentual ni persistencia por guardar localmente el archivo. No se vio secreto literal nuevo; el guion de aplicación usa credenciales de entorno y descargas bajo `.local`. Esta lectura no sustituye un escaneo de todo el historial/repositorio.

## Pruebas realmente ejecutadas

Entorno: Windows, Node24.21.0, Edge157.0.4341.46 headless/CDP; React adoptado y esbuild0.25.10 existentes. Ninguna dependencia instalada.

Artefactos privados en `C:\RackClick_SVR\.local\admin-data-20261112\review-frontend\`:

- `review-browser.mjs`, ejecutado con Node: F01/F02 **REPRODUCED**, C01–C04 **PASS**. Monta componentes reales y usa IndexedDB real, con dobles de API sintéticos. Resultado íntegro `review-browser.json` y `browser-attempt04.log`, exit0. Bundle `write:false`, sin cambiar `dist`.
- `review-boundaries.mjs`, ejecutado con Node: C05–C07 **3/3 PASS**, exit0. Resultado `review-boundaries.json` y `boundaries.log`. Aviso conocido `MODULE_TYPELESS_PACKAGE_JSON`, sin cambiar package.
- `git diff --check -- development/frontend/src/AdminUsers.jsx development/frontend/src/AdminSectionNavigation.jsx`: sin salida/errores.
- Relectura y hash de los ocho archivos al terminar el ensayo Edge: **todos idénticos a su entrada**, `filesUnchanged:true`. El manifiesto completo está en `frontend-input-hashes.json`.

Los tres primeros intentos del arnés propio constan en la salida de herramientas y los logs02/03, y no se presentan como producto fallido ni como batería verde: import ESM por ruta Windows, necesidad de habilitar await en CDP y espera explícita del Promise de lectura IDB. Se corrigió únicamente el arnés privado. El cuarto intento completo produjo el resultado citado.

## Archivos y símbolos consultados

Conjunto frontend revisado:

| Archivo | Símbolos/foco |
| --- | --- |
| `development/frontend/src/AdminInventoryData.jsx` | `AdminInventoryData`, `InventoryDataCounts`, `current`, `report`, `load`, `committed`, `refresh`, `check`, `cancel`, `selectFile`, `previewFile`, `run`, `saveFile`, efectos de alcance/bloqueo |
| `development/frontend/src/admin-inventory-data.ts` | tipos/contexto, `inventoryDataAllowed`, `validInventoryDataIntent`, `prepareInventoryDataIntent`, `readInventoryData`, `readInventoryDataFile`, `previewInventoryData`, `confirmedInventoryData`, `verifyInventoryDataArchive`, `sendInventoryData`, `inventoryDataOutcome`, `inventoryDataStatus`, `cancelInventoryData`, `inventoryDataJournal`, `executeInventoryDataIntent`, `completeInventoryDataIntent` |
| `development/frontend/src/admin-inventory-data-words.ts` | `inventoryDataWords` EN/DE/ES |
| `development/frontend/src/AdminUsers.jsx` | `AdminUsers`, `inventoryDataBlock`, `dataLock`, `save`, `recover`, integración del `fieldset` |
| `development/frontend/src/AdminSectionNavigation.jsx` | `AdminSectionNavigation`, `adminNavigationSections` |
| `development/frontend/tests/admin-inventory-data.test.mjs` | evidencia y expectativas del autor; no ejecutado por este revisor |
| `development/frontend/tests/browser-admin-inventory-data-journal.mjs` | arnés y cobertura IDB del autor; no ejecutado por este revisor |
| `development/frontend/tests/browser-admin-inventory-data.mjs` | escenario integrado preparado; no ejecutado por este revisor |

Contexto leído: `api.ts` (`RackClickApi.request/sendMutation`, `allows`, `ApiError`), `admin-users.ts` (`userJournal`, `readUsers`), `browser-quince-support.mjs` (runner), `ServerApp.jsx` (integración de Administración), `package.json`; `InventoryDataAdministrationEndpoints.cs` (`MapInventoryDataAdministration`, `Actor`), `InventoryDataAdministration.cs` (`DataAuthority`, `ReadInventoryDataAdministration`, `PreviewInventoryData`, `StoredDataResult`, `InventoryDataOperation`) y `InventoryDataAdministrationCancellation.cs` (`CancelInventoryData`) sólo para contrato. No constituye auditoría backend general.

Documentos: AGENTS real, BRIEFING-MAESTRO, contrato de esta entrega, RESULTADOS-FRONTEND, EQUIPO-Y-SKILLS, encabezados vigentes de continuidad/inicio/contrato/mapa/aceptación/README y PROGRESO-GLOBAL. Skills leídos/aplicados: `vercel-react-best-practices` y su regla de dependencias, `systematic-debugging` para reproducción sin editar producto y `verification-before-completion`; `using-superpowers` se excluye expresamente para un subagente encargado de tarea concreta.

## Identidad del conjunto y límites

SHA256 del diff exacto recibido: `d395ccbb86bd4637c56bd8eb3cf573947eac8962dea32e2099933e8443cd4e07`.

**SHA256 conjunto de los ocho archivos frontend revisados:** `b2c7412a011b4b7de4ca93482e1b5bc925b7c129a6a880947443ec7e01365a95`.

Método: SHA256 UTF-8 de la concatenación ordenada del manifiesto privado, una línea por archivo `ruta_relativa + TAB + sha256_bytes + LF`; incluye las dos integraciones, tres fuentes nuevas y tres pruebas nuevas. El orden exacto y los hashes individuales están en `frontend-input-hashes.json`. Un cambio posterior requiere nuevo hash y contraste de los focos afectados.

No ejecutado: 411 pruebas del autor, guion GUI con PostgreSQL, servidor HTTP real, restauración a otro Systemhaus vacío, inyección de fallos/rollback/concurrencia SQL, revocación real, montajes/datos Demo50, lector de pantalla, aceptación visual completa, empaquetado, descarga instalada, VM/reinicio o QA de Wascar. Esos ensayos corresponden al cierre integrado del coordinador; no se deducen de Node, Edge aislado ni de la lectura del contrato.

La revisión no modifica el progreso: permanece la referencia26,63/100 del cierre restante de PROGRESO-GLOBAL; no es un nuevo porcentaje global del producto. Próximo paso: corregir F01/F02, repetir únicamente sus reproducciones y ejecutar la GUI/PG integrada pendiente.

**Contraste de salida y trabajo concurrente:** después del ensayo y de emitir el informe se detectó que el dueño de implementación había cambiado `AdminInventoryData.jsx` a SHA256 `e483661b4aba860a7ec451f02e1da688c3bcc9f244c13825c643fd5a91fadab8`; los otros siete archivos seguían iguales. Este dictamen y sus reproducciones corresponden al conjunto original `b2c7412a…`, no acreditan todavía esa corrección. Se conserva el manifiesto original y no se sobrescribe el trabajo concurrente. La comprobación adicional de PowerShell tuvo dos errores del arnés de verificación antes de listar correctamente las ocho identidades; no se atribuyen al producto.
