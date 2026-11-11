# C2 · inversa de reducción pura de grupos

25.10.2026 · Codex. Tanda de desarrollo en paralelo con Claude; global aproximado 78 %.

Propiedad de esta tanda: `InventoryCompensation.cs` (despacho), nuevo `InventoryGroupReductionCompensation.cs`, nuevo `test_group_reduction_compensation.py`, actualización de expectativa activa en `test_group_edit_evidence.py`, adaptador `development/frontend/src/inventory-api.ts` y test nuevo `group-reduction-compensation.test.mjs`. Documentos/evidencia propios; continuidad/changelog sólo al cerrar. No tocar MFA, Program, PostgresStore, SQL, instaladores, paquetes, QA/VM ni GUI visual. Sin commits/push. La inversa de crecimiento ya revisada se conserva.

Objetivo: restaurar grupos/puertos y cables eliminados por una edición propia que no haya añadido filas ni modificado supervivientes. UUID, atributos, propiedades y fecha original del cable deben proceder de evidencia completa del servidor. No se recibe un snapshot anterior del navegador, no hay UPSERT y no se desconecta nada actual para facilitar la restauración.

Precondiciones: misma casa/cliente/actor, última revisión, estado posterior exacto tras esperar/bloquear y autorización vigente. Los puertos remotos deben existir en ese cliente, seguir libres y pasar las reglas de conexión existentes. Sin consentimiento nuevo para reservados, esas restauraciones se rechazan. Las modificaciones mixtas/reordenamientos y la GUI quedan fuera de la tanda. No se inventa compatibilidad física entre familias que el producto no comprueba actualmente.

Estado: implementación y pruebas focales terminadas, dictamen independiente favorable acotado. La integración en una futura candidata será coordinada con Claude; no reemplaza su distribución congelada.

## Contrato y condiciones

Se mantiene `POST /api/v1/customers/{customerId}/commands`, `type: "operations.compensate"` y payload cerrado `{ "operationId": "UUID de la edición original" }`, con sesión, Origin/CSRF, actor, If-Match e Idempotency-Key habituales. Sólo operación propia `inventory.device.editPortGroups`, evidencia completa v1 y última revisión.

La edición original debe tener `createdIds=[]`. Los grupos/puertos supervivientes y sus cables/extremos permanecen idénticos; las únicas diferencias son eliminaciones demostradas. El conjunto de puertos eliminados debe coincidir exactamente con `removedIds`. Se admiten 1–256 puertos, hasta 32 grupos, máximo combinado de puertos/grupos 256 y como máximo un cable eliminado por puerto. La respuesta conserva el sobre común y emplea esta variante cerrada de `result`:

```json
{
  "resourceId": "UUID del dispositivo",
  "compensationKind": "groupReduction",
  "restoredPortIds": ["UUID original de puerto"],
  "restoredGroupIds": ["UUID original de grupo"],
  "restoredConnectionIds": ["UUID original de cable"],
  "compensatedOperationId": "UUID de la edición original"
}
```

Los arrays se ordenan por UUID; grupos y conexiones pueden estar vacíos. El adaptador exige identidades/revisión correctas, campos exactos, límites y conjuntos disjuntos, también en replay y cancelación comprometida. No acepta esta variante si existe una expectativa de la antigua compensación de atributos. No se habilita candidato estructural en GUI.

Tras bloquear cliente, dispositivo, grupos y puertos actuales, se bloquean también los extremos remotos supervivientes por UUID. Se compara de nuevo el estado posterior original y se rechazan IDs ya ocupados, incluso si se reutilizaron en otro dispositivo. Se insertan grupos → puertos → conexiones → ambos extremos con SQL literal, parámetros y listas explícitas de columnas; `connector_family` sigue generado por PostgreSQL. Sin UPSERT, UUID nuevos, fechas nuevas ni eliminación de cables actuales. Se recaptura y exige igualdad completa con el `before` del servidor antes del commit.

Cada cable restaurado pasa `Pair` y `ConfirmReserved` existentes. Un extremo remoto desaparecido, ocupado, disabled/faulty, reservado sin consentimiento nuevo o eléctricamente incompatible provoca 409 `compensation_state_conflict` y rollback de la restauración completa. No se altera ese extremo para hacerla posible. `Pair` actualmente no exige igualdad general de familias de datos ni presupuesto PoE agregado: este bloque reutiliza sus reglas y no presenta esa matriz como completada.

La autorización sigue siendo `inventory.edit`, coherente con el editor de grupos, junto con lectura/sesión vigentes. Se repite tras esperas, antes de insertar y antes del commit. Otra revisión impide la inversa; CSRF, actor, cliente e idempotencia siguen verificados por el servidor. La auditoría conserva evidencia estructural; contexto/detalle del feed siguen no disponibles, sin inventar actualizaciones de puertos.

## Pruebas reales y evidencia

Windows, SDK fijado 10.0.401, Npgsql 10.0.3, PostgreSQL 17.11 y Node 24.21.0. Publicación privada con restore locked y binlog. DLL **`5eb1abcf9d2f91d293bae8f1b01e94f0352ca254c0387aaa45de1c35b2a97585`**; no se incorpora al paquete de Claude.

- **12 casos PostgreSQL distintos comprobados**, nueve nuevos y tres regresiones, en laboratorios nuevos y detenidos. La ejecución principal tuvo 10 conformes y un error de fixture: faltaba transacción al crear un cable sintético. Corregido el test, se ejecutaron sólo los dos focos afectados (2/2), más el caso nuevo de alimentación/todos los grupos (1/1). No se afirma una segunda suite conjunta de doce ni se oculta el primer error; la DLL se mantuvo igual.
- Se verifican filas/UUID/propiedades/NULL/cero/decimales/fechas/extremos exactos, cables supervivientes, restauración sin grupos/cables adicionales, todos los grupos eliminados, replay/cancelación/reinicio, evidencia corrupta, edición mixta, revisión/estado/UUID en conflicto, actor/cliente/CSRF/permisos, sesión caducada durante espera, rollback de auditoría y concurrencia. Las tres regresiones cubren la captura activa de reducción, la inversa de crecimiento y la compensación anterior PoE/watts.
- **16/16 Node**, cuatro nuevos y doce regresiones del adaptador. No es ejecución visual del navegador. Se conserva el aviso preexistente de tipo de módulo.
- **1/1 PostgreSQL independiente**: un puerto remoto pasa a faulty mientras la inversa espera su lock; al continuar devuelve 409 sin restauración parcial, revisión ni auditoría/operación nuevas. Revisor distinto, sin editar producto; no se atribuye los doce casos del autor.
- Control negativo contra la DLL anterior `40bc8098…`: el recorrido positivo nuevo recibía 422 `compensation_unsupported`. Ejecutado después de escribir el cambio, sin afirmar fase roja previa/TDD.

Se actualizó la expectativa activa de `test_group_edit_evidence.py`: su reducción pura ahora restaura la evidencia, en vez de exigir el rechazo anterior. Los informes, snapshots y resultados históricos no se reescriben. El resto de fixtures cambiados después del snapshot y sus ejecuciones focales están identificados aparte.

[Cierre, comandos, resultados, revisión y hashes](../evidence/s1-20261025/c2-inversa-reduccion-codex/CIERRE.md).

## Pendientes

GUI de compensación estructural con confirmación y recuperación de incertidumbre; cambios mixtos/reordenamientos y consentimiento de reservados; matriz física completa según RC9; integración y regresión en una candidata futura coordinada con Claude. Este bloque no cambia disponibilidad QA, no regenera guías ni instala nada en QA/VM. Dosen/finales mantienen D5. C2/S-14/S-30 siguen parciales; instalación/MFA/recuperación y QA/adopción final pendientes. **Global aproximado: 78 %, sin incremento automático.**
