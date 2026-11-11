# C2: inversa del crecimiento puro de grupos

25.10.2026 · Codex. Lote separado del trabajo de instalación/MFA de Claude.

Propiedad: `InventoryCompensation.cs` (despacho de la variante), nuevo `InventoryGroupGrowthCompensation.cs`, nuevo `test_group_growth_compensation.py`; validador `development/frontend/src/inventory-api.ts` y pruebas propias nuevas del adaptador. Documentación/evidencia propias; sin tocar Program, PostgresStore, Mfa, migraciones, instaladores, paquetes, QA/VM o GUI visual. Sin commits.

Objetivo: invertir únicamente altas probadas de grupos/puertos de una edición propia, con evidencia v1 completa. Los grupos/puertos anteriores deben permanecer idénticos y las conexiones/extremos iguales; quedan fuera reducción, renombres, reordenamientos y otros cambios mixtos. Se comprobarán revisión, ámbito, actor, estado actual tras bloquear y permisos vigentes. La inversa no borrará cables para facilitar el borrado.

Se mantiene `operations.compensate` con payload cerrado `{operationId}`. La respuesta estructural tendrá variante cerrada propia de IDs eliminados; los avisos indicarán contexto no disponible en lugar de describir puertos eliminados como actualizados. La GUI todavía no ofrecerá esta variante.

Estado: implementación y pruebas focales terminadas, con dictamen independiente favorable acotado. Global aproximado **78 %**, sin incremento automático. Evidencia base histórica: `C2-EVIDENCIA-GRUPOS-25-10-2026.md`.

## Contrato de esta variante

- Comando existente: `POST /api/v1/customers/{customerId}/commands`, `type: "operations.compensate"`, payload cerrado `{ "operationId": "UUID de la edición original" }`. Conserva sesión, Origin/CSRF, actor, If-Match e Idempotency-Key del contrato vigente.
- Sólo operación propia `inventory.device.editPortGroups`, mismo Systemhaus/cliente/dispositivo y última revisión. Debe tener evidencia completa v1 generada por el servidor; no se aceptan valores anteriores aportados por el navegador.
- Grupos y puertos anteriores, incluidos orden, prefijo y atributos, permanecen idénticos en la edición original. Las conexiones y ambos extremos también. Sólo se eliminan IDs realmente añadidos, comprobados contra `createdIds`: entre 1 y 256 puertos, hasta 32 grupos, máximo combinado 256 IDs. Crecimientos mayores siguen siendo válidos como edición, pero esta inversa los rechaza.
- Se bloquean cliente, dispositivo, grupos, puertos y conexiones/extremos; se compara el estado posterior original con el actual después de esperar. Se revisan sesión/lectura/edición de nuevo, se borran primero puertos y después grupos añadidos, y se comprueba el estado anterior exacto antes del commit.
- Capacidad: `inventory.edit`, igual que el editor original, que ya puede reducir grupos/puertos; no se introduce una política de permisos distinta en esta tanda. La autorización se aplica en el servidor.

El sobre de respuesta conserva `customerId`, `revision`, `requestId` y `operationId`. Su `result` es una variante cerrada distinta de la compensación de atributos:

```json
{
  "resourceId": "UUID del dispositivo",
  "compensationKind": "groupGrowth",
  "removedPortIds": ["UUID de puerto añadido"],
  "removedGroupIds": ["UUID de grupo añadido"],
  "compensatedOperationId": "UUID de la edición original"
}
```

Los IDs se devuelven ordenados; `removedGroupIds` puede estar vacío. El adaptador valida variante, identidad, revisión y conjuntos disjuntos también en replay/cancelación comprometida. No interpreta estos puertos como `changedIds`. Una expectativa de la antigua compensación de atributos rechaza esta respuesta.

Rechazos sin escritura: 422 `compensation_unsupported` para evidencia ausente/incompleta/corrupta o edición mixta; 409 `compensation_not_latest` para otra revisión; 409 `compensation_state_conflict` para filas/cables distintos tras esperar. Los controles comunes siguen produciendo 404 de ámbito/actor, 403 de permiso/CSRF y 412 de If-Match obsoleto. La auditoría de la inversa guarda objetos estructurales; el feed devuelve contexto `notAvailable` y arrays vacíos, sin inventar actualizaciones de puertos eliminados. El detalle de compensaciones continúa no disponible.

## Verificación de desarrollo

- Windows, SDK 10.0.401 fijado, Npgsql 10.0.3 y PostgreSQL 17.11. Publicación en snapshot privado, con restauración locked y binlog privado; sin sustituir herramientas ni dependencias fijadas.
- DLL de este lote: `40bc80987afe647e9f460fb72a5ed04c127aeb0f33485748debaecd1879148d2`. No reemplaza la candidata de Claude `f11a689e…` ni su manifiesto `2ec91056…`.
- Suite principal PostgreSQL: **10/10**, siete casos nuevos y tres regresiones de evidencia y compensación de atributos/PoE. Bases y cuentas nuevas por caso; clúster nuevo detenido. Incluye conservación exacta, cable previo, restart, replay/cancelación, actor/cliente/CSRF/permisos, revocación tras espera, corrupción, estado/revisión, concurrencia y rollback por fallo de auditoría.
- CLI reproducible del test comprobada en dos ejecuciones focales adicionales. La segunda refuerza aislamiento: mismo actor autorizado en dos clientes no puede compensar en el cliente equivocado. No se suman como casos funcionales distintos de la suite principal.
- Node 24.21.0: **12/12**, cuatro casos nuevos del adaptador y ocho regresiones. Se conserva el aviso preexistente `MODULE_TYPELESS_PACKAGE_JSON`; no se cambió el paquete para silenciarlo.
- Control negativo con la DLL anterior `e3a217cc…`: el caso positivo nuevo falla con 422 `compensation_unsupported`, como se esperaba. Se ejecutó después de escribir el cambio; no se presenta como TDD previo.
- Revisor distinto: **1/1 PostgreSQL** adicional. Durante la espera del dispositivo reconectó un cable preexistente a un puerto añadido; la inversa rechazó con 409, conservando filas, revisión, auditoría y operación. El primer diseño de su fixture se bloqueó por FK; está conservado y separado del resultado válido. No repitió las diez pruebas del implementador.

Resultados, comandos, entradas y revisión distinta: [cierre](../evidence/s1-20261025/c2-inversa-crecimiento-codex/CIERRE.md).

## Continuación y límites

1. Resolver reducción/eliminación con su evidencia completa y pruebas propias. No reconstruir cables o atributos que no estén demostrados.
2. Integrar un candidato estructural en GUI con confirmación, recuperación de incertidumbre y QA por botones. Actualmente la GUI sigue ofreciendo sólo la compensación de atributos admitida antes.
3. Integrar estos cambios en una futura candidata identificada, tras coordinar con Claude; repetir los controles relevantes sobre ese artefacto. Esta DLL privada no se incorpora a un ZIP instalado.

No se tocó servidor QA/VM, servicios, bases existentes, GUI visual, MFA, migraciones, paquetes ni instaladores. Sin commits/push. No se habilitan casos manuales ni se regeneran guías porque no cambió la disponibilidad visible. Dosen/finales y D5 se conservan. S-14/S-30 y C2 siguen parciales; instalación/recuperación, MFA y QA/adopción final siguen abiertos. **Global aproximado: 78 %.**
