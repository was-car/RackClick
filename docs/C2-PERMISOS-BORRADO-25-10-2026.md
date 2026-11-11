# C2 · borrado sin conceder edición

25.10.2026 · Corrección de I04-GUI-01, detectado en el catálogo de I-04.01. Implementación y pruebas en laboratorio; no incorporada a la candidata de las VM ni al QA de Wascar.

## Qué cambia

Una cuenta con `inventory.read` + `inventory.delete` podía borrar según el servidor, pero la interfaz añadía la exigencia de `inventory.edit`. Ahora los controles de borrado, su apertura y el permiso del diálogo usan borrado, mientras los controles de edición mantienen edición. No se conceden capacidades nuevas.

[InventoryPanel.jsx](../development/frontend/src/InventoryPanel.jsx) separa ambas capacidades en cinco grupos de botones: sede, edificio, sala, rack y objeto de sala. Los borradores de borrado individual y conjunto declaran `inventory.delete`. La recuperación usa [inventory-operation-permission.ts](../development/frontend/src/inventory-operation-permission.ts): clasifica el JSON original, con prioridad sobre etiquetas del cuadro o del borrador. Los seis tipos de borrado son cerrados; JSON/tipo inválido o borrado desconocido no permite reintentar.

La selección de capacidad sólo gobierna la GUI. El servidor sigue comprobando sesión, lectura, capacidad de la operación, cliente, revisión, impacto y confirmación vigentes. Se conservan Click-Click, RC9, clases/CSS, límites de lote, guardas de contexto, journal e identidad de la solicitud. `OperationDialog.jsx`, API/backend, SQL y MFA no cambiaron.

## Pruebas y resultado

- **Antes:** el navegador real reproduce la falta de controles para lectura+borrado sin edición. FAIL 18,67 s. La prueba independiente del panel anterior falla también en dos grupos semánticos, con el módulo presente.
- **Después:** Edge y PostgreSQL 17.11, PASS 23,08 s. Borrado individual y lote de Dose/final, rack y ubicaciones vacías; permiso retirado con preview abierto; edición sin borrado denegada por HTTP; recarga y recuperación original con cuerpo/actor/clave/ETag exactos; confirmación con respuesta perdida resuelta por consulta. Nueve tablas originales de inventario exactas y persistencia tras reiniciar el proceso servidor.
- **Regresión de edición:** mismo frontend nuevo, Edge/PostgreSQL PASS 20,17 s. Retirar sólo edición conserva lectura, bloquea replay/cancelación y permite consultar el resultado original. Nueve tablas exactas y persistencia tras reiniciar proceso.
- **Node:** 36/36 pruebas existentes pertinentes de consulta/contexto/edición rápida; revisor distinto añade 5/5 grupos propios de selección de capacidad, apertura, ámbito y recuperación.
- Primer ensayo de la GUI corregida: FAIL 33,83 s por una espera del test que exigía botones habilitados aunque había una operación pendiente. Se corrigió sólo esa espera; se conserva el fallo y no se atribuye al producto.

Una compilación frontend privada, sin restaurar dependencias ni compilar .NET. CSS exacto al anterior; DLL C2 anterior identificada. Todos los laboratorios y procesos propios quedaron detenidos. [Evidencia y comandos](../evidence/s1-20261025/c2-delete-permission-codex/CIERRE.md), [revisión independiente](../evidence/s1-20261025/c2-delete-permission-codex/REVISION.md).

## QA y pendientes

**QA-118** describe botones, ubicaciones, dos perfiles y resultado esperado. Está `planned`: no se habilita hasta integrar y seleccionar una candidata compatible y preparar las cuentas ficticias. Los 117 casos anteriores y sus resultados personales se conservan; ambas guías se regeneran desde el catálogo.

El hallazgo I04-GUI-01 queda corregido en desarrollo. I-04.05 sigue parcial: esta prueba focal no acredita todas las variantes de impacto, cancelación y cables incidentes ni la candidata final. I-04.06/07, integración MFA/instalador, Windows limpio/reinicio y aceptación de Wascar siguen pendientes. No se incorpora C2 automáticamente a la edición 07.

**Métrica sin cambio: 4,29/100 del trabajo restante, 10/280 subpasos y 1/50 resultados completos.** Se resolvió un fallo dentro de un subpaso aún pendiente; no se inventa una fracción nueva ni un porcentaje global del producto.
