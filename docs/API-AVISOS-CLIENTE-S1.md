# API de avisos por cliente ·60-A

**Ampliación428–472:** este endpoint y sus8campos no cambian. El código actual admite30acciones:7con contexto de puertos/cables y23con nueva descripción en el endpoint opt-in `/changes/details`; la cifra26 anterior estaba desactualizada. [Contrato vigente de detalles](API-AVISOS-DESCRIPTIVOS-S1.md). Sin reconstruir historia de eventos antiguos ni actualizar QA185 por esta edición.

`GET /api/v1/customers/{id}/changes?afterRevision=12&limit=50` consulta cambios confirmados de un cliente autorizado. Es un feed de avisos para pedir una actualización explícita del proyecto; no aplica cambios automáticamente ni sustituye auditoría completa, backup o resolución de conflictos. No usa DDL nueva: esquema7 y SQL001–007 se conservan.

La cookie se autentica en middleware. El lector comprueba inventory.read antes de validar cursor/limit; cliente ausente, House ajeno o permiso ausente devuelven404 indistinguible. Después bloquea la fila del cliente con FOR SHARE en ReadCommitted, revalida sesión con el helper existente y inventory.read, valida el cursor y lee/proyecta eventos. Repite sesión/permiso justo antes del commit de lectura. El helper comprueba clock_timestamp después de esperar locks. El orden cliente→actor/sesión coincide con Execute; se descartó antes de compilar una llamada inicial al helper que habría retenido actor/sesión antes del cliente. Fue una corrección de diseño preventivo, no un deadlock reproducido. No se añaden locks de House.

FOR SHARE mantiene estable la revisión de cliente y bloquea los escritores que la incrementan. El snapshot de eventos se obtiene mientras se conserva ese lock; no se usa un snapshot antiguo de permisos. Cada poll exige la autoridad actual. Una revocación que confirma mientras el lector espera la fila de cliente se observa antes de proyectar. La respuesta no muta inventario, auditoría, operaciones ni identidades. ETag contiene currentRevision; Cache-Control es no-store.

Parámetros: afterRevision opcional, entero decimal positivo1..9223372036854775807; limit opcional1..100, por defecto50. Valor vacío, repetido, negativo, fraccionario o fuera de rango devuelve422 request_invalid sólo después de autorizar. Sin afterRevision, inicia en la revisión actual, sin devolver historia anterior. Para cubrir la carrera entre cargar proyecto y comenzar polling, se envía la revision obtenida por GET project como afterRevision.

La respuesta tiene exactamente estas seis claves:

```json
{
  "customerId":"UUID cliente",
  "currentRevision":14,
  "nextRevision":14,
  "hasMore":false,
  "refreshRequired":false,
  "events":[{
    "id":"UUID audit_event/operationId",
    "actor":{"id":"UUID histórico","userNameCurrent":"nombre actual o null"},
    "action":"inventory.ports.update",
    "resourceId":"UUID recurso directo o null",
    "revisionBefore":13,
    "revisionAfter":14,
    "occurredAt":"2026-10-17T10:00:00Z",
    "context":{
      "status":"captured",
      "beforePorts":[{"id":"UUID puerto","deviceId":"UUID equipo","groupId":"UUID grupo","type":"rj45","gn":1}],
      "afterPorts":[{"id":"UUID puerto","deviceId":"UUID equipo","groupId":"UUID grupo","type":"rj45_poe","gn":1}],
      "beforeConnections":[],
      "afterConnections":[]
    }
  }]
}
```

Los UUID se serializan en formato D. resourceId conserva audit_event.resource_id, que puede identificar equipo, conexión u otro recurso; nunca se sustituye por el cliente. Un resource UUID vacío no se publica y se representa null. id es el ID del evento y operationId del comando original; no se consulta operation ni se publica requestId/requestHash. Actor.id es histórico, userNameCurrent se resuelve con la cuenta actual y puede ser null; no es un snapshot de nombre. occurredAt es informativo: now() de auditoría puede reflejar inicio de transacción, no orden de commit. No se usa fecha/UUID como cursor.

El cursor es exclusivamente revisión de cliente. Las páginas contienen revisiones contiguas ascendentes, con al menos limit+1 posiciones verificadas cuando existen. nextRevision es la última publicada; hasMore indica continuación. currentRevision es la revisión del cliente estable durante la consulta. Ambos wrappers del evento deben ser objetos con el mismo customerId de la ruta, revisión numérica positiva y after=before+1 dentro del snapshot. Sólo se aceptan26 acciones literales:

- inventory.site.create/update/delete; inventory.building.create/update/delete; inventory.room.create/update/delete.
- inventory.rack.create/update/assignRoom/delete/duplicate.
- inventory.device.create/update/move/reorder/delete/editPortGroups.
- inventory.ports.update.
- inventory.connections.create/createBatch/update/disconnect/reconnect.

Se excluye explícitamente operation.cancel antes de seleccionar la ventana: puede guardar customerId y revisión vigente, pero no incrementa inventario. Replay y rollback tampoco producen otra revisión confirmada. Un renombrado de cliente incrementa su revisión sin wrapper inventory y aparece como laguna; no se inventa un evento inventory. Laguna, duplicado, acción desconocida, wrapper incompatible o cursor adelantado devuelven events=[], hasMore=false, refreshRequired=true y nextRevision=currentRevision. Esto pide recargar proyecto; no afirma cobertura completa ni reconstruye datos ausentes.

context siempre contiene status y las cuatro listas. Sólo ports.update y las cinco acciones de conexiones pueden usar status=captured. Las otras20 acciones y cualquier contexto inválido usan notAvailable con las cuatro listas vacías; el evento válido puede seguir notificándose. No se buscan objetos actuales para completar historia.

- Puerto: exactamente id/deviceId/groupId/type/gn; por lista1..256, IDs no vacíos y únicos. Ambas listas conservan orden, IDs, deviceId, groupId y gn, un solo equipo/grupo por evento, deviceId=resourceId. type pertenece a rj45,rj45_poe,sfp,sfp28,qsfp,mgmt,console,power,usb_a,usb_c. Sólo rj45/rj45_poe comparten familia; la familia no cambia. gn es int32 positivo, no identidad ni número único entre grupos. La pertenencia House/cliente se valida contra la fila capturada sin exponer esos campos adicionales. Conexiones vacías.
- Conexión: exactamente id/fromPortId/toPortId; IDs y extremos no vacíos/distintos, sin IDs o extremos repetidos en un mismo lote, máximo128 por lista. create tiene antes vacío/después1; createBatch antes vacío/después1..128 y primerid=resourceId. disconnect antes1/después vacío. update/reconnect tienen antes1/después1, mismoid=resourceId; update conserva extremos, reconnect conserva al menos un extremo en su posición, incluido no-op válido. Puertos vacíos. Se valida House/cliente capturado; no se inventa grupo/tipo/gn de extremos.

La consulta SQL reduce los datos a campos finitos y escalares antes de leerlos en .NET. Nunca salen JSON bruto, notas, labels, propiedades, nombres de racks/equipos, contraseñas/tokens/CSRF, requestHash u operaciones completas. Los datos de la vista actual que la GUI use para rotular un UUID deben identificarse como actuales, sin fingir contexto histórico.

El arnés `development/server/tests/test_inventory_changes.py` exige DLL/frontend explícitos y directorio de evidencia nuevo. Seis grupos focales cubren commit/replay/cancel/rollback y sólo lectura/persistencia; paginación/fechas/carrera y snapshot concurrente; lagunas/incoherencia/límites; lector/aislamiento/autoridad antes del cursor; revocación/expiración tras esperas; puertos/conexiones/redacción/OpenAPI. Las alteraciones de auditoría, límites sintéticos y triggers se identifican como fixtures SQL, separados de comandos HTTP reales. Una regresión existente de idempotencia de inventario se ejecuta al estabilizar. Resultados y hashes reales en `evidence/s1-20261017/tres-tandas-60/backend/`; este documento no declara una ejecución antes de que exista su reporte.

Sólo laboratorios nuevos, secretos privados.local, sin QA real, instalación, adopción ni nueva DDL. Este bloque es API; interfaz y revisión independiente se atribuyen por separado. Referencia global56/100 provisional, sin incremento por preparar el contrato.
