# Recuperación administrativa offline · S1

17.10.2026, tandas308–317 del grupo308–337. Implementación en `RecoveryAdministrator.cs`, selección CLI en `Program.cs`. Este documento define el contrato del componente; la compilación, las pruebas PostgreSQL nuevas y la revisión independiente del grupo se registran por separado en su cierre. No acredita instalación completa, adopción ni ejecución sobre QA de Wascar. El progreso global de referencia continúa en73/100 provisional hasta el cierre del coordinador.

## Autoridad y destino

`RackClick.Server.dll --recover-admin` es un comando local para una **instancia NUEVA**, con su base ya restaurada y la aplicación detenida. No crea clúster, base, esquema ni una ruta HTTP. Es mutuamente exclusivo con `--bootstrap` y `--migrate`, y termina antes de construir el host HTTP.

La conexión debe autenticar exactamente como `rc_owner_<UUID32minúsculas>`, propietario de `rc_db_<mismoUUID32>`. El UUID no puede ser cero. `current_database()` debe coincidir exactamente con `Recovery:ExpectedDatabase`. La contraseña del owner permanece en el entorno privado del proceso. Esta autoridad equivale al control administrativo que ya concede PostgreSQL sobre esa base; no concede acceso anónimo en la API. Quien controle el owner puede cambiar tablas, auditoría y comentarios por SQL: las guardas evitan errores operativos, no defienden contra ese propietario.

Antes del restore, el creador nativo de la base nueva escribe un comentario de fase exacto:

```text
RackClickRecoveryPending:<UUID-formato-D-minúsculas>:<SHA256-manifestJSON-minúsculas>
```

`Recovery:BackupSha256` es el SHA256 externo del archivo **manifest.json exacto**, previamente verificado por el comando nativo. No es el digest de `database.dump`. La CLI sólo compara y registra esa referencia; no lee ni valida el archivo de backup. El creador/restaurador verifica el dump contra ese manifiesto y no modifica el origen. Una instalación normal no tiene el comentario de fase y queda rechazada.

## Entrada y resultado

Configuración admitida por el proveedor habitual de ASP.NET:

|Clave|Contrato|
|---|---|
|`ConnectionStrings:RackClick` / `ConnectionStrings__RackClick`|Conexión privada del owner nuevo; nunca en argumentos ni evidencia pública.|
|`Recovery:User` / `Recovery__User`|Nombre NUEVO; `UserNames.Normalize`, igual que Login/Bootstrap: trim, validación de1–100 escalares Unicode y minúsculas invariantes, sin traducción ni NFC nueva.|
|`Recovery:ExpectedDatabase` / `Recovery__ExpectedDatabase`|Nombre exacto `rc_db_` seguido de32 dígitos hexadecimales minúsculos; determina UUID y owner.|
|`Recovery:BackupSha256` / `Recovery__BackupSha256`|64hex del manifiesto JSON; se canoniza a minúsculas antes de comparar el comentario y registrar auditoría.|
|stdin redirigido|Contraseña nueva generada por el operador nativo,16–1024 unidades UTF-16, seguida opcionalmente por LF o CRLF y EOF. Ninguna segunda línea. No se acepta configuración/argumento de contraseña ni se imprime prompt.|

El productor debe cerrar stdin; la lectura espera EOF y reserva como máximo1027caracteres. El comando aplica longitud, no intenta deducir si una cadena fue generada aleatoriamente. El productor nativo genera una contraseña nueva con aleatoriedad criptográfica. La CLI limpia su buffer mutable; el hash y las cadenas de .NET no implican borrado forense de memoria.

Tras commit confirmado, stdout contiene una única línea JSON y el código de salida es0:

```json
{"status":"committed","action":"deployment.recover","instanceId":"<UUID>","systemhausId":"<UUID>","createdUserId":"<UUID>","createdGroupId":"<UUID>","auditEventId":"<UUID>","requestId":"<UUID>","revokedSessions":0,"systemhausRevision":2}
```

Los UUID/revisión/conteo son resultados reales de la transacción. El nombre normalizado se obtiene por `createdUserId` si el llamador lo necesita; no se deduce de una búsqueda por nombre. No hay contraseña, hash de contraseña, token, CSRF, conexión ni contenido stdin en la respuesta.

Un rechazo esperado produce `{"status":"rejected","error":"<código>"}`, salida1. Un error no clasificado produce `{"status":"failed","error":"recovery_failed"}`, salida1, sin mensaje SQL ni stack trace. Si falla la comunicación durante COMMIT, la confirmación puede ser incierta: conservar la base nueva y consultar su auditoría/comentario antes de decidir. No interpretar toda salida1 como rollback acreditado ni borrar la candidata por ese motivo.

## Validaciones y transacción

La CLI abre una transacción y fija `search_path=pg_catalog,public`. Adquiere el advisory lock81726201 compartido con Bootstrap/Migrate, verifica base/owner y bloquea en SHARE el historial de esquema. Exige nueve entradas consecutivas, exactamente1..9, sin extras ni huecos; sólo entonces llama `SchemaMigrations.Apply` para comparar todos los digests con los archivos SQL de la distribución. Al estar completos y bloqueados, no puede ejecutar una migración pendiente. No acepta base vacía, esquema antiguo/nuevo, historial incompleto ni digest alterado. Esta comprobación de historial no es una certificación exhaustiva de toda alteración que pudiera efectuar el owner fuera de las migraciones.

Bloquea el único Systemhaus con `FOR UPDATE` y exige UUID/revisión positivos. Rechaza cualquier evento previo `deployment.recover` de ese Systemhaus cuyo `after_json.instanceId` sea el UUID de destino; los eventos heredados con **otro** UUID permanecen y permiten recuperar un backup de una instancia ya recuperada en una tercera instancia nueva. Después verifica el comentario de fase exacto y que el nombre normalizado no exista, incluso como cuenta inactiva.

Dentro de la misma transacción:

1. Crea un usuario activo, un grupo nuevo `Recovered Systemhaus Administrators`, su membresía y las nueve concesiones globales `Capabilities.FoundationAdmin` vigentes.
2. Borra **todas** las filas de `app_session` copiadas, incluidas sesiones vencidas/inactivas, y registra el conteo eliminado. El proceso permanece offline; no garantiza impedir un nuevo login posterior de una cuenta copiada cuya contraseña válida se conserva.
3. Incrementa únicamente la revisión de Systemhaus en1. No cambia revisiones de clientes/inventario, contraseñas/estado/permisos de usuarios copiados ni operaciones previas del journal.
4. Inserta `audit_event` canónico y consume el comentario mediante `COMMENT ON DATABASE <nombre-validado> IS NULL`.
5. Hace COMMIT; sólo después devuelve el resultado de éxito.

La acción auditada es exactamente `deployment.recover`; el actor es el usuario NUEVO, el recurso es el Systemhaus, `before_json` es NULL y `after_json` contiene exactamente:

```text
origin = localRecovery
instanceId = UUID nuevo derivado del nombre de la base
sourceBackupManifestSha256 = SHA256 externo del manifiesto JSON
revokedSessions = conteo de sesiones eliminadas
createdUserId = UUID del administrador nuevo
createdGroupId = UUID del grupo nuevo
```

El evento lleva UUID/requestId propios. No se añade una operación interactiva al journal. No se introduce DDL de esquema ni una nueva versión SQL. La captura tipada `audit_context` y los detalles administrativos actuales tienen listas cerradas que no admiten esta acción; se conserva el evento/metadata y el JSON anterior, **sin declarar contexto tipado o detalle GUI disponibles** ni etiquetarlo falsamente como un login HTTP. Ampliar esa proyección es trabajo separado.

La repetición sobre el mismo destino devuelve `recovery_already_initialized`, antes de crear cuentas o borrar sesiones nuevas; no vuelve a mostrar ni sustituye la contraseña. Un error previo a commit revierte conjuntamente cuentas/grupo/grants/sesiones/revisión/evento/comentario al disponer la transacción. El borrado de sesiones y la nueva cuenta nunca se confirman por separado.

## Códigos de rechazo

|Código|Condición|
|---|---|
|`cli_mode_conflict`|Más de un modo bootstrap/migrate/recover.|
|`recovery_stdin_required`|La invocación CLI no redirige stdin.|
|`username_invalid`|Nombre fuera de la política compartida.|
|`recovery_database_invalid`|Nombre esperado no canónico/UUID cero.|
|`recovery_backup_sha256_invalid`|Referencia del manifiesto no es64hex.|
|`recovery_connection_required`|No se configuró conexión del owner.|
|`password_length`|Contraseña fuera de16..1024 o stdin por encima del límite.|
|`recovery_password_input_invalid`|Contenido con CR/LF interior o línea adicional.|
|`recovery_database_mismatch`|Conexión a otra base.|
|`recovery_owner_required`|current_user o propietario distintos del owner esperado.|
|`recovery_schema_required`|Base no inicializada, versión/historial fuera de exactamente1..9.|
|`migration_digest_mismatch`|SQL distribuido e historial tienen digests distintos.|
|`recovery_systemhaus_required`|No hay exactamente un Systemhaus válido.|
|`recovery_already_initialized`|Ya existe evento de recuperación para este UUID de destino.|
|`recovery_pending_marker_required`|Comentario ausente o distinto de UUID/hash exactos.|
|`recovery_username_exists`|El nombre normalizado ya está ocupado.|

Errores del driver, SQL alterado/faltante, restricciones, E/S, overflow de revisión y confirmación incierta no exponen su detalle: `recovery_failed`. El entorno/configuración de ASP.NET debe poder cargarse antes de seleccionar el componente; errores del arranque del framework previos a esa selección no son una ejecución de recuperación confirmada.

## Verificación y límites de esta entrega

El implementador inspeccionó fuentes, contrato/esquema, comandos previos y ejecutó `git diff --check`; no compiló ni inició PostgreSQL, por encargo del coordinador para realizar una sola integración. La revisión independiente y las pruebas reales se atribuyen a sus ejecutores en `evidence/s1-20261017/treinta-tandas-308-337/`. Ninguna ejecución histórica del grupo278–307 cuenta como prueba nueva de esta CLI.

Pendientes de verificación del grupo: guardas de CLI/base/owner/fase/esquema/digests/usuario, normalización Unicode, éxito/login/permissions, sesiones copiadas rechazadas, repetición conservando una sesión nueva, nueva recuperación desde backup recuperado con otro UUID y rollback completo mediante restricción de auditoría sólo en fixture. No se habilita un caso de QA visible por existir este código; no se modifica la GUI, SQL001–009 ni el QA real. La recuperación completa/servicio/PKI/instalación en Windows limpio y adopción final permanecen según el criterio global del coordinador.
