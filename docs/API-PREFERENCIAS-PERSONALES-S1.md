# Preferencias personales: idioma y tema ·653–712

Estado inicial: desarrollo autorizado; base133ed63, global78/100 estimado. GUI/QA592 y paquete652 de esquema10 se conservan. El bloque desarrolla idioma y tema en esquema11 sin cambiar CSS, Click-Click o RC9 adoptada. S-26 no se declara completo por esta función.

## Propiedad y valores

El propietario procede exclusivamente de la sesión vigente: Systemhaus+actor. Cualquier usuario autenticado activo, también lector o sin clientes visibles, gestiona sólo sus preferencias. Ninguna ruta selecciona usuario o cliente ajenos; no se exige ni concede inventory.edit. Las operaciones revalidan sesión/estado tras esperas y antes del commit/retorno.

Sólo dos claves: `language` con en|de|es y `theme` con dark|light. Ausencia de fila equivale a revisión0 y ambos valores null (sin selección personal explícita). GET no inserta filas. Un campo null mantiene la selección anónima de este navegador; el primer login no escribe automáticamente. Los nombres/datos del inventario no se traducen.

## Rutas y DTO

GET `/api/v1/me/preferences`, sin query/cuerpo: `{kind:"userPreferences",ownerId,revision,language,theme}`. ETag personal exacto `"preferences-N"`, N entero0..9007199254740991. No usar ETag de inventario.

POST a la misma ruta: exactamente `{key:"language",value:"es"}` o `{key:"theme",value:"light"}`. No body parcial ambiguo, extra/duplicados, null, otros valores ni dueño/cliente aportados. Obliga If-Match original, Idempotency-Key UUID no vacío, X-RackClick-Actor UUID original, Origin y CSRF. Cambia únicamente la clave explícita; evita pisar otra preferencia tras conflictos. Resultado confirmado: `{kind:"userPreferences",ownerId,revision,requestId,operationId,result:{key,value,changed}}`; el ETag es la revisión del resultado histórico. No aplica un resultado histórico como snapshot actual: después de commit/replay se recarga GET.

GET `/api/v1/me/preferences/operations/{requestId}` y POST de esa ruta más `/cancel`: `{state:"committed"|"notRecorded"|"cancelled",ownerId,revision,requestId,operation:null|<resultado original>}`. Status sin query. Cancel requiere el body, ETag, actor y clave originales, incluso si revisión cambió. Fence terminal duradero para una petición no registrada; cancel no deshace commit. Cancel repetido/replay no duplica auditoría. Late POST tras fence devuelve409 operation_cancelled; misma clave con otro cuerpo/revisión409 request_id_reused. notRecorded no es éxito ni cancelación. Reautenticar el mismo actor permite consultar/reintentar/cancelar; cambiar actor nunca envía su intención.

No-op explícito se registra/audita una vez sin incrementar revisión, también en el máximo seguro. Nueva intención con revisión vieja devuelve412 aunque valor coincida. Conflictos no rebasan/reintentan con una revisión nueva automáticamente. Si un cambio necesita incrementar la revisión máxima devuelve409 sin escritura; replay/cancelación siguen disponibles. DTO rechaza tipos, formatos ETag/UUID y estructuras ambiguos, incluidos query inesperada y cuerpo en GET.

## Persistencia, auditoría y atomicidad

SQL011 aditiva: `user_preferences` (Systemhaus+owner, revisión, language/theme nullable con CHECK enum) y `user_preference_operation` (request/result/fence terminal personal). FK compuesta a app_user; resultado JSON/version/digest estrictos. SQL001–010 intactas. Las tablas nuevas son maestras; no inventario.properties, historial de auditoría o localStorage.

ReadCommitted. Advisory petición `RackClick/user-preference-operation/{house:D}/{actor:D}/{request:D}` antes de agregado `RackClick/user-preferences/{house:D}/{actor:D}`; GET/status agregado compartido, POST/cancel exclusivo. Digest canónico de familia, Systemhaus, actor, key/value y revisión original. Preferencias, revisión, auditoría y recibo se confirman en la misma transacción. Auditoría `user.preference.set` y `user.preference.set.cancel`, resourceId=owner, sólo metadatos de esos valores públicos, sin contexto de cliente. No incrementa revisión de cliente/Systemhaus, ni emite aviso de inventario. Un fallo revierte todo; fences sin purga inventada.

401 sesión inválida;403 Origin/CSRF;409 actor cambiado/clave reutilizada/fence/revisión agotada;412 conflicto;422 entrada/ETag/UUID inválidos;428 If-Match ausente. No usar404 por falta de cliente: es configuración propia, no lectura de inventario.

## GUI y recuperación

Reutilizar Settings actual, selector EN/DE/ES y botón dark/light. Antes de autenticación se conserva fallback anónimo en las dos claves locales existentes. Un cambio autenticado no escribe esas claves globales. Tras logout/switch se vuelve al fallback anónimo, sin heredar la preferencia del actor anterior. Cargar/releer sólo aplica valores no-null del dueño/generación vigentes. Toda respuesta tardía se descarta si cambió actor o generación.

Mientras se carga no guardar contra revisión desconocida. Tras selección explícita mostrar Guardando y aplicar sólo snapshot confirmado por servidor; fallo/conflicto conserva el valor confirmado y explicación. Diario compacto propio por actor, únicamente key/value/revisión/requestId, sin inventario/secretos; no mezclar con favoritos o diarios anteriores. Ante respuesta incierta Consultar/Reintentar original/Cancelar original; no duplicar ni rebasar intención. Si persiste pendiente, no iniciar otra preferencia. Mantener controles/orden/CSS y EN/DE/ES; accesibilidad de estado/recuperación por teclado.

Informes, paletas, filtros/caras temporales, datos documentales del cliente, preferencias de inventario y opciones nuevas quedan fuera. La GUI no promete sincronizar automáticamente dos sesiones abiertas: recarga/reautenticación lee PostgreSQL; edición concurrente produce conflicto recuperable.

## Evidencia y límites del bloque

Previsto: migración10→11 de fixture nueva poblada/constraints y tablas antiguas exactas; sesión/CSRF/actor/validación; dos propietarios sin clientes/lector; no-op/replay/fence; concurrencia/revisión/límite; revocación durante espera/rollback/auditoría; reinicio/login y backup/restore de datos35tablas en otra base. Node foco de DTO/journal/cambio actor, Edge nuevo multisesión/idioma/tema/errores con fixture aislada, revisión independiente separada. CLI de recuperación fija11 explícitamente; no ampliar silenciosamente operadores/ZIP10. Build congelada712 de desarrollo, nuevos casos QA pendientes de selección compatible, QA manual/adopción de Wascar sin alterar.


Resultado: implementado y comprobado/revisado en [cierre653–712](../evidence/s1-20261018/sesenta-tandas-653-712/CIERRE.md), candidata712 FINAL02. Nuevos QA72–74 no disponibles en QA592/10. Instalación/recuperación de aplicación/CLI11 y selecciónQA11 pendientes; backup/restore ejecutado sólo de datos en base aislada.
