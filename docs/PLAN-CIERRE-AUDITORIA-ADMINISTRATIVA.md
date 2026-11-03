# Plan acotado · cierre de auditoría administrativa

**Ampliación54-B implementada en desarrollo:** `user.state.set`/`.cancel` capturan contexto transaccional y objetivo usuario/intención mediante006 aditiva, sin editar005; junto a alta/cancelación son4/21formas,17pendientes. [Contrato de estado](API-ADMIN-AUDITORIA-ESTADO-CONTEXTO-S1.md), [cierre54](../evidence/s1-20261017/tres-tandas-54/CIERRE.md). Mismo GET/DTO/46/50; replay no añade contexto ni backfill. No enumera sesiones indirectas, no GUI de contexto ni QA real actualizado. La migración adicional corrige la restricción de005 que no admitía user/intendedTarget; schema6 es explícito. Planes/resultados siguientes históricos; no auditoría completa ni administración15/15.

**Actualización52-B:** primer par implementado y revisado: user.create/.cancel,005aditiva y GETcontext tipado;2/21acciones. [Contrato real](API-ADMIN-AUDITORIA-CONTEXTO-S1.md), [cierre52](../evidence/s1-20261017/tres-tandas-52/CIERRE.md). Otras19capturas y GUI de contexto pendientes. No se implementan nombre histórico ni sesiones indirectas. QA real no migra; ampliar familias requiere contrato/pruebas y migración aditiva si cambia el esquema, preservando los digest de005 y anteriores. Lo siguiente conserva el plan51 histórico; no atribuirle implementación de todas sus filas.


Tanda51-B,17.10.2026; base `8b0a2cb`. **Propuesta implementable a revisar, no alcance aprobado de005/DTO ni implementación de un parche.** Alcance: los21 eventos conocidos de46/50, captura futura y lectura honesta del histórico. Se mantienen53/100 estimado y administración14/15; no hay pruebas nuevas PostgreSQL/Windows ni intervención en QA real.

## Base contractual y hallazgos

- `CONTRATO-SERVIDOR-v0.1.md:74` exige actor, cliente, comando, objetos, horaUTC, revisiones, resultado y petición;113/117 exigen transacción e idempotencia.21/139 exigen panel y ausencia de contraseñas/tokens en auditoría.
- **P2, cobertura pendiente conocida:** `database/001-foundation.sql:61` sólo persiste actorID/House/request/action/resource/JSON/hora; faltan contexto tipado, revisiones administrativas explícitas y resultado terminal independiente de `operation`. Los escritores no satisfacen todavía toda esa atribución.
- **P3, semántica que debe conservarse:** `AdminAudit.cs:7,55` y `AdminAuditDetail.cs:73`/`AdminAuditAdministrativeDetail.cs:186` usan nombre ACTUAL mediante JOIN. No es nombre histórico. El contrato literal pide actor, ya identificado por UUID; capturar también su nombre al ejecutar es la decisión propuesta de trazabilidad, no un requisito literal adicional oculto.
- No se detectó ni reprodujo un defecto nuevo de autorización/commit. Se consultó evidencia50, sin volver a ejecutar sus pruebas.

Los nombres de fuente C#/SQL citados abajo son relativos a `development/server/src/RackClick.Server/` y `development/server/database/`; las líneas son de la base indicada.

## Campos finitos del contexto nuevo

| Campo | Existe hoy | Captura propuesta, en la MISMA transacción de comando/operación/evento |
|---|---|---|
| eventId,House,actorId,requestId,action,resourceId,occurredAt | Sí, columnas de `audit_event` | Reutilizar; timestamp PostgreSQL. No crear otro request ni alterar el evento en replay. |
| actorUserNameAtExecution (mejora propuesta) | No; sólo nombre actual al leer | Snapshot literal del actor autorizado, separado de `event.actor.userName` actual. Decisión barata de ingeniería; el mínimo contractual identifica actor por UUID y no depende de este nombre histórico. |
| scopeKind/scopeId y customerId | Parcial en payload de miembros/grants; no columna | `systemhaus` para administración global; `customer` con ID directo; `customerGroup` con ID de grupo. `customerId=null` explícitamente no aplica en global/grupo, sin inventar un cliente único. |
| objects: kind,id,relation | Un resourceId y algunos IDs en JSON | Mínimo: referencias tipadas de objetivos DIRECTOS, miembro, grant y ámbito; sesión dirigida exacta en revoke por UUID público. Distinguir `target` de `intendedTarget` en cancelación. |
| revisionScope,revisionBefore,revisionAfter | Sólo nombres46 tienen parte; resultado de operation contiene próxima revisión | Administración usa Systemhaus observado bajo su lock: commit r→r+1; cancelación durable r→r, aunque If-Match original sea antiguo. No sustituir r por expected. |
| customerRevisionBefore/After | Nombres cliente46 sí guardan parte | Sólo create/rename de cliente cuando exista esa revisión; create: antes no aplica/después1. Registrar además Systemhaus anterior/posterior realmente incrementado. |
| outcome | Implícito en action/resultado de operation | Enum `committed`/`cancelled`; committed incluye no-op válido con revisión incrementada. Nunca confundir cancelación con deshacer ni replay con nueva ejecución. |

**Mínimo del cierre:** actorUUID, objetivos directos tipados, ámbito/cliente cuando aplica, revisiones, resultado y petición. `scopeKind` no enumera clientes afectados transitivamente. **Mejora opcional aparte:** enumerar todas las sesiones eliminadas indirectamente por reset/desactivación mediante `DELETE … RETURNING id`, con colección/continuación si se necesita. Esa exhaustividad y su paginación no son requisito contractual explícito ni condición de cierre administrativo; nunca incluir token/hash.

## Eventos y lugares de captura pendientes

| Eventos finitos | Objetos/contexto adicional | Símbolo y punto existente |
|---|---|---|
| `user.create`, `.cancel` | Usuario creado; cancel sin UUID creado conserva House, no inventar cuenta; actor/r/r'/outcome global | `AdminUsers.cs:58 CancelUserCreation`,94 INSERT;102 `CreateUser`,145 INSERT. |
| `userGroup.create`, `customerGroup.create` y ambas `.cancel` | Grupo creado/tipo; cancel con House; contexto global | `AdminGroupWrites.cs:62` rama cancel,76 próxima revisión,84 INSERT (`CreateOrCancelGroup`). |
| `userGroup.member.set`, `.cancel` | Grupo+usuario; cancel registra IDs de intención recibidos y validados, no membresía ficticia | `AdminGroupMembers.cs:25 SetOrCancelGroupMember`,70 before,95 INSERT. |
| `customerGroup.member.set`, `.cancel` | Grupo+cliente directo; cancel sólo intención, sin consultar existencia para bloquear petición perdida | `AdminCustomerGroupMembers.cs:41 SetOrCancelCustomerGroupMember`,86 before,100 INSERT. |
| `userGroup.grant.set`, `.cancel` | Grupo+grant+capacidad+scope/target; distinguir cliente/grupo/global | `AdminGrantWrites.cs:39 SetOrCancelGrant`,101 before,136 INSERT. |
| `user.state.set`, `.cancel` | Usuario y estado; cancel sin efecto. Enumeración de sesiones indirectas opcional | `AdminUserState.cs:25 SetOrCancelUserState`,79 DELETE,98 INSERT. |
| `user.password.reset`, `.cancel` | Usuario+indicador passwordReset, jamás contraseña/digest; sesiones indirectas opcionales | `AdminUserPassword.cs:27 ResetOrCancelUserPassword`,91 DELETE,101 INSERT. |
| `user.session.revoke`, `.cancel` | Usuario+sesión pública; conservar wasCurrent histórico; cancel no revoca | `AdminUserSessionRevocation.cs:24 RevokeOrCancelUserSession`,52 before,74 DELETE,85 INSERT. |
| `systemhaus.rename`, `customer.create`, `customer.rename` | Completar mismo contexto de actor/resultado/House; cliente y revisión propios sólo donde aplican | `PostgresStore.cs:238 Mutate`: cliente279/291; House319; evento325. No tocar proyección46. |

En cancelaciones nuevas se puede registrar intención segura recibida aunque el objetivo ya no exista; no añadir un lookup/FK a objetivo vivo que impida la cancelación. Nombres inválidos que hoy permiten una valla no pasan a ser valores históricos válidos. No reconstruir intención de cancelaciones antiguas desde requestHash o recursos actuales.

## Migración y contrato compatibles propuestos

1. Propuesta a revisar: nueva `005-audit-context.sql` aditiva; conservar bytes001–004. Contexto con eventId PK/FK, versión de captura y columnas mínimas tipadas; referencias directas por evento con kind/id/relation. Tabla hija es una opción de diseño, no requisito aprobado; omitir colección de sesiones indirectas del primer parche. Sin FK a objetivos eliminables; House derivado del evento. Checks de enums, UUID no cero y revisiones positivas/coherentes.
2. Sin backfill: ausencia de fila = `notRecorded` para este contexto, no “sin cambio”. No copiar nombre actual del actor ni revisión de `operation` como si fueran una instantánea completa. Los detalles históricos seguros46/50 siguen visibles por sus rutas actuales.
3. Helper de escritura explícito recibe conexión/tx/eventId/contexto validado; llamado después de comprobar replay y antes de CommitAsync. Un fallo en contexto revierte mutación, revisión, operation y audit_event. Capturar r del lock ya tomado; no abrir otra transacción ni consulta posterior al commit.
4. `SchemaMigrations.cs:8–34` requiere registrar005, mantener digest/historia y actualizar LatestVersion; no permite rollback sólo de DLL4 sobre esquema5 (`Program.cs:121–122`). Ensayar copia/restauración nueva antes de cualquier futura activación real; no migrar QA por este plan.
5. Ruta adicional/DTO a revisar `GET /api/v1/admin/audit/{eventId}/context`: `status=available|notRecorded`, nulos explícitos donde no aplica y objetivos directos de cardinalidad acotada por cada acción. No incorporar paginación de sesiones a esta base mínima. Mantener DTO/lista38–43, nombres46 y administrative-detail50; sus ETag siguen siendo actuales, no revisión histórica.
6. GLOBAL `security.manage` vigente antes de UUID/lookup, House del actor, RepeatableRead,404 indistinguible para ajeno/ausente; mismos límites estrictos de identificadores. Publicar sólo allowlist tipada, nunca JSON bruto/operation/requestHash/secretos; validar correspondencia del contexto con acción/objeto del evento. No filtrar información a lector ni a permiso sólo de cliente.

## Límites de eventos de seguridad e inventario

`CONTRATO…:99,139` obliga login/logout seguros, límite de intentos, revocación y auditoría sin secretos; no enumera eventos de login/logout/fallos como requisito de registro. `PostgresStore.cs:83 Login` sólo persiste contador/sesión;128 `Logout` borra sesión sin audit_event. Se propone su auditoría como **mejora opcional separada**, no condición añadida silenciosamente al cierre de estos21 eventos. Exigirla requeriría contrato específico para actor desconocido, privacidad, límites/retención y fallo de registro: audit_event actual exige actorId no nulo/FK. Tampoco convertir cada401/403/422/rollback en commit de auditoría administrativa.

Inventario/importación/exportación/backup mantienen sus obligaciones propias del contrato74/105/113. Sus objetos, revisiones por cliente y diferencias completas se completan en sus bloques; este plan no los certifica ni añade nuevas acciones inexistentes.

## Primer parche pequeño y pruebas afectadas propuestas

**Primero, propuesta acotada a revisar:**005 mínima+helper+captura exclusivamente `user.create`/`user.create.cancel`+GET de contexto, sin GUI ni activar QA. Publicar `notRecorded` para filas previas y escritores aún no integrados; no llamarlo cobertura completa. No añadir sesiones indirectas/paginación. Después incorporar pares por familia con pruebas focales; GUI/QA manual cuando la captura administrativa mínima esté revisada.

- PostgreSQL nuevo: migración4→5, repetición, instalación1→5 y fallo inducido sin migración parcial; comparar datos/cuentas/sesiones preexistentes y digest001–004. Restauración de copia4 a destino nuevo como recuperación ensayada, sin bajar esquema destructivamente.
- Create/cancel HTTP reales: actorUUID, r→r+1/r→r, objetivo real/intención y outcome; snapshot literal sólo si se incluye esa mejora; cancel con expected viejo; sin divulgar password/hash. Segunda sesión y reinicio leen mismo evento/contexto.
- Idempotencia: replay devuelve mismo resultado sin nueva fila de evento/contexto ni revisión; misma clave con cuerpo distinto409; cancelar ya confirmado devuelve resultado original; crear después de cancelación409. Histórico previo a005 queda byte-igual/notRecorded.
- Rollback: trigger que rechaza contexto revierte también usuario/operación/evento/revisión; fallo en tabla de objetos revierte todo. Reintento de esa misma petición después de retirar trigger produce exactamente un commit completo.
- GET:401/403, permiso sólo cliente, otro House404, UUID inválido/no cero, revocación/caducidad durante espera; redacción y coherencia; regresión puntual lista+detalles46/50 y ETag/DTO intactos. Si se incluye snapshot de nombre, fixture cambiando nombre actual demuestra que no se reescribe.

**Cierre verificable del subbloque:** los21 eventos nuevos tienen contexto MÍNIMO indicado, cancelaciones/no-ops honestos, objetivos directos tipados (sesión exacta en revoke), histórico sin invenciones, atomicidad/replay/aislamiento PostgreSQL probados, lectura GUI y guion QA/revisión independiente registrados. Nombre histórico propuesto y sesiones indirectas exhaustivas son mejoras diferenciadas, no bloquean este criterio contractual. No concede15/15 por sí solo: siguen árbol administrativo y aceptación de Wascar. Pruebas propuestas, ninguna ejecutada en51-B.
