# Revisión independiente · I04-GUI-01

25.10.2026. Revisor distinto del implementador. Git inspeccionado; cambios ajenos conservados. Propiedad propia: `development/frontend/tests/inventory-delete-permission.test.mjs`, este informe y las dos salidas privadas nuevas autorizadas por el coordinador. Sin editar producto, backend, MFA, W-02, QA/VM, plan o métricas.

**Dictamen: conforme en las fuentes y pruebas propias para la corrección de I04-GUI-01.** No se reprodujo un defecto nuevo. Se elimina la exigencia adicional de EDIT en apertura y permiso del diálogo de borrado, conservando el ámbito, bloqueo y autorización real del servidor. No se da por terminada I-04.05 completa ni la candidata/QA por esta corrección focal.

## Lectura y comprobaciones

- `inventory-operation-permission.ts`, `inventoryWriteCapability`: borradores ordinarios requieren EDIT; DELETE necesita una declaración explícita. Recuperación prevalece sobre la etiqueta/hint del borrador y clasifica el JSON original. Los seis tipos cerrados son `site.delete`, `building.delete`, `room.delete`, `rack.delete`, `device.delete` y `devices.delete`. JSON/tipo malformado o `.delete` desconocido devuelve null. Esta función selecciona el permiso GUI; no sustituye la validación del comando en servidor.
- `InventoryPanel.jsx`, `open`: función real extraída sin JSX; se comprueba READ+DELETE sin EDIT, READ+EDIT sin DELETE, edición ordinaria, ámbito de otro cliente y `blocked`. `removeEntity` real declara DELETE para sede/edificio/sala/rack/equipo y conserva exactamente su tipo/payload y preview sólo para rack/equipo.
- Lectura de `removeSelectedDevices`: declara DELETE, conserva selección explícita, límite y preview. Lectura de los cinco contenedores JSX: se muestran si `canEdit || canDelete`, con botones de edición y borrado separados; clases/estilo existentes conservados. Es inspección de código, no montaje DOM propio.
- `dialogCapability` usa `inventoryWriteCapability(draft,recovery)`; `OperationDialog.writeAllowed` comprueba esa capacidad con `allows(session,...,customer.id)`. Se conserva `authorityLost`, revisión máxima y las guardas del diálogo. Consulta y cancelación de la intención original no se convierten en una nueva escritura de edición.
- `api.ts`, `allows`, y `pending-journal.ts` se consultaron para el ámbito y el formato original. No se cambian ni se presentan como probadas aquí todas las vías de autenticación o persistencia.

## Pruebas realmente ejecutadas por el revisor

Windows/PowerShell, Node local 24.21.0. Cinco grupos propios en el archivo asignado: hint ordinario/destructivo; seis borrados y seis variantes de edición recuperadas sin mutar sus bytes; recuperación malformada/tipo delete desconocido; apertura real con permisos/ámbito/bloqueo; cinco borradores individuales reales.

| Fuente del panel | Resultado |
|---|---|
| Copia anterior `before/.../InventoryPanel.jsx`, con módulo ya existente | **3 PASS / 2 FAIL esperados**, 0 omitidas, exit 1, 164,4811 ms. Fallan apertura READ+DELETE y creación del borrador real. No es un fallo por módulo ausente. |
| Fuente final | **5/5 PASS**, 0 omitidas, exit 0, 200,8525 ms. |

Comando final: `.local/node-v24.21.0-win-x64/node.exe --test development/frontend/tests/inventory-delete-permission.test.mjs`. El rojo usa `RACKCLICK_DELETE_PANEL_SOURCE` apuntando a la copia anterior; se capturó/propagó `$LASTEXITCODE` y se retiró la variable. Salidas nuevas: `.local/c2-delete-permission-20261025T135722Z-e69491f3/reviewer-red.stdout` y `reviewer-green.stdout`. Aviso `MODULE_TYPELESS_PACKAGE_JSON` conservado; sin cambiar dependencias.

## Identidad y límites

| Archivo | SHA256 |
|---|---|
| `InventoryPanel.jsx` final | `fe340de2c1ef82fde0ec06b7922065fac63f8e565e5c4af350522c0a797abf70` |
| `inventory-operation-permission.ts` | `ad61bc8d9afe7c6ea24c8505d2816c3b37b0364ce8eb0b70df8c282d7bd0b215` |
| Prueba propia | `f0fe8f8d67ef6ed9190e61d9949701a1b2f0df362d98a52342dd8476c98627d9` |

## Resultados del coordinador contrastados al cierre

Sin más ejecuciones propias: se leyeron el escenario final `browser-inventory-delete-permission.mjs`, sus resultados/diagnósticos y QA-118. La fuente del panel y el módulo conservan los hashes anteriores. Escenario final SHA256 `0811052740e44c1c1373a53a2207554da07da40bbce689e41f0a01e85ecea9b2`; frontend privado reutilizado por los ensayos `c8c099a82866ca0001954f81d0843869067f7c65c64f963821d104205e25a38a`, DLL C2 `5eb1abcf…` sin build .NET nuevo.

| Ensayo del coordinador, no del revisor | Resultado contrastado |
|---|---|
| GUI anterior | [FAIL 18,67 s](ORIGINAL.json), exit 1: [falta real del control individual para DELETE sin EDIT](ORIGINAL-DIAGNOSTICO.json), sin excepciones JS. |
| Primera GUI corregida | [FAIL 33,83 s](OBSERVADOR-ENSAYO.json), exit 1: [espera del observador](OBSERVADOR-DIAGNOSTICO.json) exigía botones habilitados mientras existía un journal pendiente. Se corrigió sólo `recover` del escenario, sin cambiar producto. |
| Edge/PostgreSQL final | [PASS 23,08 s](EDGE-PG.json), exit 0; [tres ciclos documentados](NAVEGADOR.json), sin excepciones JS, nueve tablas exactas, persistencia tras reiniciar el proceso y laboratorio/servidores detenidos, entradas intactas. |
| Regresión READ sin EDIT | PASS 20,17 s sobre el mismo frontend; se leyó `edge-regression-edit/result.json` privado. Nueve tablas exactas/reinicio del proceso/cierre e inputs intactos. [Evidencia pública del cierre](CIERRE.md). |
| Regresión Node pertinente | El [cierre del coordinador](CIERRE.md) registra 36/36 PASS, sin omitidas; no se suman a los cinco grupos propios ni se repiten aquí. |

El escenario confirma DELETE sin EDIT para borrado individual y ubicaciones vacías; revocación con preview abierto sin dispatch; lote de objetos de sala recuperado tras reload; EDIT sin DELETE rechazado por GUI y POST 403; GET notRecorded sigue permitido por READ. Restituir sólo DELETE reenvía cuerpo/actor/clave/ETag originales. Una respuesta de borrado ya committed perdida se recupera por GET sin repetir el borrado. Estos ensayos sí respaldan la corrección funcional focal de I04-GUI-01; no completan toda I-04.05.

**QA-118:** leído como `planned`, explícitamente no disponible; exige cuentas y objetos ficticios preparados, preview/cancelación/confirmación/recarga y segunda cuenta sin DELETE. Separa los fallos de red/revocación automáticos de la prueba manual y no pide tocar datos ajenos ni cortar la VM. No identifiqué un error grave en ese guion. La conservación de los 117 casos y regeneración de guías se atribuyen al cierre del coordinador; no se repitió aquí el control completo ni se modificaron resultados personales.

Sin builds, PostgreSQL, Edge/DOM, instalación o pruebas adicionales ejecutados por este revisor. Los cinco grupos propios por sí solos no prueban HTTP/SQL, revocación real o IndexedDB; esas partes se atribuyen arriba al coordinador. Sin nuevo porcentaje global ni modificación de crédito; integración coordinada, QA y adopción de Wascar siguen sus puertas propias.
