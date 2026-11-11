# Contexto mínimo · contrato final21formas, tandas55–59

Decisión coordinada: DTO ampliado **aditivamente** con `customerRevisionBefore/After`. Se conservan rutas, campos52/54, captureVersion1, 46/50 y revisiones históricas de House; no se reinterpretan las cuatro formas anteriores.001–006 conservan bytes/digests.007 añade columnas/checks/enum finitos para todas las familias, sin backfill. La captura se integra por familia, con evidencia y DLL congelada separadas:55password/sesión→8/21;56grupos→12;57membresías→16;58grants→18;59nombres→21. Esas cifras sólo se declaran realizadas al pasar su prueba correspondiente.

```json
{
  "revision": 12,
  "event": {"id":"UUID","occurredAt":"UTC","actor":{"id":"UUID","userName":"nombre actual"},"requestId":"UUID","action":"customer.rename","resourceId":"UUID cliente"},
  "context": {
    "status":"available","captureVersion":1,"actorId":"UUID histórico",
    "scopeKind":"customer","scopeId":"UUID cliente","customerId":"UUID cliente",
    "revisionScope":"systemhaus","revisionBefore":7,"revisionAfter":8,
    "customerRevisionBefore":2,"customerRevisionAfter":3,"outcome":"committed",
    "objects":[{"kind":"customer","id":"UUID cliente","relation":"target"}]
  }
}
```

`revision`/ETag son actuales de Systemhaus. `revisionScope` es siempre `systemhaus`; revisionBefore/After registran el House realmente observado bajo lock: committed r→r+1, también no-op válido; cancelled r→r, también con If-Match original antiguo. Sólo customer.create/rename usan scopeKind=`customer`, scopeId=customerId=recurso y los extras históricos de cliente: create null→1 (sin inventar0), rename positivo→+1. Administración/membresías/grants mantienen ámbito de comando Systemhaus, scopeId=House, customerId/extras nulos; clientes o grupos relacionados se identifican en objetos. Esto no cambia la exigencia GLOBAL de lectura del contexto.

Objetos **sin `position` público**, exactamente en este orden. Kinds finitos: `systemhaus,user,userGroup,customerGroup,customer,grant,session`; relaciones finitas: `target,intendedTarget,member,intendedMember,scope,intendedScope`. Máximo3objetos.

| Formas literales | Objetos normales | Objetos de `.cancel` |
|---|---|---|
| user.create + cancel | user/recurso/target | systemhaus/House/intendedTarget; no UUID de cuenta inventado |
| user.state.set + cancel | user/recurso/target | user/UUID recibido/intendedTarget |
| user.password.reset + cancel | user/recurso/target | user/UUID recibido/intendedTarget |
| user.session.revoke + cancel | user/userId/target; session/sessionId público exacto/target | mismos dos IDs/orden, ambas relaciones intendedTarget |
| userGroup.create + cancel | userGroup/recurso/target | systemhaus/House/intendedTarget; no grupo inventado |
| customerGroup.create + cancel | customerGroup/recurso/target | systemhaus/House/intendedTarget; no grupo inventado |
| userGroup.member.set + cancel | userGroup/groupId/target; user/userId/member | mismo orden: intendedTarget; intendedMember |
| customerGroup.member.set + cancel | customerGroup/groupId/target; customer/customerId/member | mismo orden: intendedTarget; intendedMember |
| userGroup.grant.set + cancel | userGroup/groupId/target; grant/grantId/target; objeto ámbito/scope | mismo orden: intendedTarget; intendedTarget; intendedScope |
| systemhaus.rename | systemhaus/House/target | no existe esta cancelación |
| customer.create, customer.rename | customer/recurso/target | no existen estas cancelaciones |

El objeto ámbito de grant es systemhaus/House si scope de la concesión es global, customer/targetId o customerGroup/targetId según input validado. grantId es el UUID explícito recibido, incluso al cancelar; nunca se busca/infiere otro. Cancelaciones de miembros/grants/sesión conservan IDs de intención conocidos aunque los recursos ya no existan; no confirman pertenencia/existencia ni efectos. Cancelar un alta sin UUID creado usa sólo House. No se infieren nombres o IDs desconocidos desde requestHash/JSON/recursos vivos.

En GET, cookie/permiso GLOBAL/House vigentes antes de UUIDestricto/lookup, RepeatableRead,404 ajeno/ausente idéntico y ausencia de mutación conservan52. Metadata de actor muestra **nombre actual** y UUID histórico; sin snapshot de nombre. Los payloads tipados46/50 siguen en sus rutas, sin JSON arbitrario en contexto. No se enumera una lista exhaustiva de sesiones indirectas eliminadas por estado/password.

Captura/objetos/command/revisiones/outcome incoherentes o ausentes: status=`notRecorded`; todos los campos nullable, incluidos los dos extras nuevos, son null y objects=[]. Significa sin contexto publicable compatible, no ausencia de acción/cambio. Contextos válidos anteriores de cuatro formas mantienen sus datos, con extras nuevos null. Replays previos no crean eventos, objetos, revisiones ni backfill. Nunca se reconstruye histórico desde operation; los escritores insertan en su misma tx después de replay y antes del commit. Fallo en contexto u objeto revierte la mutación, operation, evento y revisión conjunta.

Cada familia tiene su prueba focal PostgreSQL con DLL/frontend explícitos, lab nuevo, secretos/logs privados y cierre propio en `evidence/s1-20261017/quince-tandas-55-59/backend/`. Capturas SQL de prueba se distinguen de escrituras HTTP reales. No activar ni migrar QA real a schema7 ni declarar candidata/adopción. Cierre21/21 de esta lista no equivale a administración15/15, auditoría de fallos/login/logout o inventario, ni entrega completa. Referencia global53/100 (~55%), sin aumento automático por número de tandas.
