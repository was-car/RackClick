# Rotación MFA · protocolo de fases v1

09.11.2026 · Especificación del paso **19 / F-06.01**. Desarrolla el modo `rotate` de [D2, apartados 4.1–4.2](D2-CONDICIONES-TECNICAS-F03-02.md). No implementa un rotador, una migración o un comando administrativo. D y E se conservan sin operaciones. La custodia confirmada y la política de 45 días/exención global siguen vigentes.

## 1. Decisión y alcance

Se conserva la decisión D2: **mantenimiento exclusivo, material verificado antes del commit, una transacción de recifrado y publicación final hacia delante con conciliación**. No se adopta rotación online por lotes: hoy no hay coordinación de múltiples escritores ni un publicador de anillo existente. Tampoco se usa `PREPARE TRANSACTION`: PostgreSQL no convierte un archivo DPAPI en participante de una transacción distribuida.

Rotar significa cambiar la clave que cifra el secreto TOTP, **sin cambiar ese secreto ni el autenticador del usuario**. No es restablecer MFA, recuperar una pérdida, cambiar identidades AAD, restaurar la base ni retirar versiones. Cada operación fija `mode=rotate`; un fallo no la convierte en `loss-reset` o `portable-restore`.

Este contrato cierra únicamente la especificación de fases. Inventario operativo/retirada corresponde a F-06.02; implementación y caídas reales a F-06.03; cierre integral a F-06.04. Las dependencias operativas F-04/F-05 y R-04 no quedan aceptadas por escribirlo.

## 2. Objetos y condiciones comunes

Notación: `a` es la versión activa inicial; `n` la nueva; `K` las versiones que ya conserva el anillo; `U` las versiones de **todos los factores persistidos**, incluidos `pending`, `active` y `disabled`; `B` las requeridas por backups retenidos. Las claves de `K ∪ U ∪ B` deben ser auténticas y legibles. Una dependencia desconocida, versión ausente o clave incompatible bloquea `rotate`; no autoriza borrar el factor o el backup. Este lote no implementa el censo de B.

- `n` debe superar el máximo autoritativo conocido de anillo, factores de cualquier estado, operaciones conservadas y backups retenidos. Límites existentes: versiones 1..1000000 y 64 entradas por anillo. Si el censo no es fiable, hay colisión o el anillo aditivo excede 64, detenerse. No reutilizar números ni eliminar una clave para hacer espacio.
- Material inicial `R0`: activa `a`. Anillo aditivo `R+`: mismas versiones y bytes de clave, más `n` como **`retired`**, conservando `a` activa. Anillo final `Rf`: mismas claves que R+, `n` activa y `a` retirada; las demás conservan su estado. En el parser, `retired` significa disponible para descifrado; no significa borrada, ilegible o criptográficamente destruida. No se añade un estado `prepared` al formato.
- Instalación MFA, Systemhaus y usuarios no cambian. AAD existente: `rackclick-mfa-v<keyVersion>|<systemhausId:D>|<userId:D>`. Una adaptación de identidad pertenece a otro procedimiento.
- La ruta se obtiene del perfil verificado: `<InstancesRoot>\<installationId>\mfa-keys`. En el perfil Windows actual, `InstancesRoot` ya incluye `...\Instances\<installationId>\security`, por lo que hay un segundo nivel `<installationId>` antes de `mfa-keys`. No se deduce otra ruta de un nombre de servicio o base.
- SYSTEM/Administradores operan; el SID estándar real del servicio sólo lee. No se amplían permisos de `management`, del almacén o del rol PostgreSQL de ejecución. No se cambia `MfaKeyStore:Enabled` como reparación.

## 3. Exclusión, journal y testigo de commit

Antes de preparar material se adquieren la exclusión local por instalación y un bloqueo de mantenimiento PostgreSQL ligado a la DB explícita del perfil. Un bloqueo consultivo sólo coordina participantes que lo respetan: **no sustituye** detener los escritores ni los bloqueos SQL del recifrado. La conexión que mantiene la exclusión DB se conserva durante toda la operación; perderla obliga a parar y conciliar, nunca a seguir con el bloqueo supuesto.

Se detiene el servicio identificado, se comprueba su parada y se drenan o rechazan sus transacciones pendientes. También se bloquean arranques alternativos, tareas de backup/exportación y otros operadores que puedan alterar DB/anillo. Un **fence persistente de arranque**, creado antes de la primera publicación, impide abrir listeners tras un reinicio o muerte del operador. La muerte del proceso libera locks de proceso, pero no demuestra que sea seguro retirar el fence.

El journal privado se crea con DACL segura desde el primer byte, fuera de `mfa-keys`. El fence es un marcador separado legible por el guard; no concede al servicio acceso al journal o a `management`. Identifica operación UUID, modo, instalación, Systemhaus, vínculo DB, SID de operador/lector, fase confirmada, activa anterior/nueva, versiones, objetos/hashes anteriores/preparados/finales y referencia del sobre externo verificado. Ningún campo contiene claves en claro, TOTP, contraseña, códigos, connectionString o ciphertext de factores. Los recibos públicos sólo exponen fase/códigos/recuentos.

Se exige un **testigo DB dedicado**, insertado en la misma transacción que el recifrado: operación UUID única, `rotate`, autoridad `windows-local`/SID real, vínculo de instalación/DB/Systemhaus, versiones `a/n`, hashes esperados de material/anillo final, recuento de factores y fecha PostgreSQL. Su UUID no se puede reaprovechar para otros parámetros. El contrato/adaptador y su migración siguen pendientes; no existe una tabla de rotación utilizable en esquema 45. Runtime sólo podrá consultarlo para el guard; las escrituras son de mantenimiento, con identidad separada y sin DDL para runtime.

No se inventa un usuario o sesión de aplicación para `audit_event.actor_id`: la autoridad local se registra en ese testigo dedicado. Una futura proyección web debe identificarla como local. El exit del padre, el journal, una marca de tiempo o la ausencia de logs **no prueban el commit**. Todo dato de un journal se contrasta con su vínculo y con DB/material; un archivo por sí solo no autentica esos hechos.

## 4. Fases y puertas de avance

| Fase | Hecho necesario para avanzar | Estado DB / anillo vivo |
|---|---|---|
| `planned` | Identidades, autorización local, versiones/factores/backups y copia privada previa contrastados; exclusión, journal y fence comprobados. No hay claves ni factores modificados. | DB inicial; R0, activa a. |
| `key_staged` | Crear exclusivamente material nuevo n en staging atribuido, con ACL desde creación. Proteger DPAPI LocalMachine con entropía instalación/versión; abrir, autenticar y comparar 32 bytes en memoria. Validar identidades/rutas/ACL/bytes retenidos y material R+/Rf. No escribir sobre objetos preexistentes. | DB inicial; R0. Ningún factor puede referir n. |
| `additive_published` | Persistir primero el archivo de n, luego publicar R+ mediante el futuro publicador seguro de anillos existentes. Reabrir y verificar objeto publicado, claves, ACL y lectura bajo el SID efectivo del servicio. Conservar R0 y las versiones anteriores. | DB inicial; R+, activa a; GetKey(n) disponible, GetActiveKey() aún a. |
| `material_ready` | Completar instantánea estable y sobre externo que cubra K ∪ U ∪ B ∪ {n}; abrir/autenticar y verificar el sobre, sin dejarlo en servidor/backups. Confirmar custodia y material duradero exigido antes de permitir dependencias DB. Fijar hashes y condiciones del recifrado. | DB inicial; R+. Todavía no se permite cifrar factores con n. |
| `db_committed` | Una única transacción verifica y recifra todos los factores, conserva metadatos funcionales, revoca sesiones/desafíos previstos e inserta testigo/auditoría local. Confirmar commit por testigo DB vinculado, incluso si se perdió la respuesta. | Todos los factores persistidos usan n; R+ aún puede tener a activa, pero host fenced y todas las claves disponibles. |
| `ring_published` | Publicar Rf únicamente sobre la identidad anterior validada; verificar el objeto final y su coincidencia con testigo/journal. No borrar ninguna clave anterior. | DB comprometida; Rf, n activa y a retirada. |
| `data_verified` | Con DB sin escritores, abrir/autenticar todos los factores con versión/identidades correctas; contrastar conjunto de versiones, cobertura de backups/sobre, ACL/SID, testigo y material final. Ninguna fila se omite por estar disabled. | DB/Rf coherentes, aún sin listener. |
| `service_resumed` | Registrar la puerta de arranque autorizada y retirar el fence sólo tras data_verified. El guard de coherencia valida vínculo/testigo/anillo antes del listener; comprobar servicio, HTTPS/health y ruta MFA. Conservar exclusión/journal hasta terminar. | Enrolamientos nuevos usan n; los factores anteriores conservan su TOTP. |
| `verified` | Registrar resultado final y residuos, cierre del mantenimiento y liberación de exclusión. La recuperación tras reinicio y el recibo del arranque siguen verificables. | Operación terminada; las versiones anteriores siguen conservadas. |

```mermaid
flowchart LR
    P[Plan y fence] --> K[Clave nueva verificada]
    K --> A[Anillo aditivo: activa antigua]
    A --> S[Sobre externo y material listo]
    S --> C[Commit DB con testigo]
    C --> R[Anillo final: activa nueva]
    R --> V[Verificación offline]
    V --> H[Guard y arranque controlado]
```

Las fases adicionales precisan el orden D2; no cambian su modo ni agregan puntos al ledger. Escritura, flush, rename y relectura **no demuestran por sí solos durabilidad ante pérdida eléctrica**. La implementación debe demostrar su requisito de persistencia/recuperación en el destino antes de habilitar `material_ready`; de lo contrario se para antes del recifrado. Los escritores actuales de creación exclusiva no son el publicador de un `ring.json` existente.

## 5. Contrato de la transacción de recifrado

La transacción se ejecuta sólo desde `material_ready`, con la misma exclusión y todas las claves retenidas. Tras obtener los bloqueos SQL, se repite el censo: si difiere del plan, falla el avance, sin publicar la activa nueva. Las tablas/identificadores SQL son una lista interna cerrada; valores externos por parámetros Npgsql. El plan de implementación fijará el orden común de locks y sus timeouts con el resto del coordinador; no se permite afirmar exclusión global por bloquear sólo las filas ya existentes.

1. Bloquear el conjunto de factores y los conjuntos de seguridad afectados con protección contra escrituras/factores nuevos; comprobar usuarios/Systemhaus/versiones y ausencia de un testigo contradictorio. Un testigo coincidente preexistente manda conciliar, **no repetir** el recifrado.
2. Para cada fila de `app_mfa_factor`, incluidos pending/active/disabled, abrir `secret_ciphertext` con su `key_version` y AAD originales mediante `MfaSecretCipher.Open`. Error de autenticación o versión desconocida aborta toda la transacción.
3. Sellar **el mismo secreto** con la clave n, nonce nuevo aleatorio de 12 bytes por `Seal`, tag de 16 y AAD de la versión n, manteniendo Systemhaus/user. Verificar en memoria el roundtrip antes de actualizar. Cambiar sólo `secret_ciphertext` y `key_version` del factor; borrar las copias de claves y plaintext al terminar/abortar, sin prometer borrado universal del runtime.
4. Conservar estado del factor, `last_time_step`, intentos/bloqueo y fechas. No reactivar disabled, no reiniciar el contador antirreplay, no regenerar TOTP, códigos de recuperación, contraseña o política, ni reiniciar la gracia de 45 días o la exención global.
5. Revocar las sesiones y consumir los desafíos pendientes de las cuentas con factor incluidas en esta operación, dentro de la misma transacción. No se emiten sesiones nuevas, no se consume un código de recuperación ni se fuerza reenrolamiento por una rotación normal. Usuarios/capacidades/ámbitos e inventario se conservan. El próximo login verifica el mismo autenticador.
6. Contrastar recuentos y escribir el testigo/auditoría local en esa transacción. Si falla cualquiera de esas escrituras, no se aplica ninguna actualización. El caso cero factores sigue necesitando testigo y publicación coherentes, y no libera claves de backups.

Un commit incierto nunca se trata como rollback. Con conexión restablecida se adquiere la exclusión y se comprueba que la transacción anterior ya no está en curso; después se consulta el testigo por UUID y vínculo en la DB primaria autoritativa. Si la DB no responde, la consulta es ambigua o el vínculo no coincide, se mantiene el fence y no se repite ni revierte nada.

## 6. Conciliación por hechos y límites del retroceso

| Hechos contrastados después de parar | Acción permitida |
|---|---|
| Sin testigo, transacción anterior terminada y DB igual a la inicial | Reanudar la misma operación desde su material verificado, o abortar explícitamente antes de commit. Para volver a R0, probar que ningún factor usa n, ninguna operación concurrente lo publicó y R0 satisface todo el conjunto requerido. Conservar material/evidencia; no borrar por nombre. No retirar fence sólo por faltar el testigo. |
| Testigo exacto presente; journal quedó anterior al commit | Tratar DB como comprometida. Completar Rf hacia delante con el material ya preparado; no recifrar otra vez ni reinstalar R0 como única copia. |
| Testigo exacto presente y Rf publicado; journal retrasado | Revalidar material/ACL/factores, reconstruir sólo el estado derivable y continuar por data_verified. No fabricar una ejecución o un recibo de proceso. |
| Testigo ausente pero DB alterada, testigo incompatible o material sustituido | Estado incoherente: detenerse, conservar evidencia/residuos y exigir diagnóstico. No declarar rollback/éxito ni elegir otra instalación. |
| Cualquier clave requerida ausente o ilegible, censo B desconocido, sobre no comprobado o persistencia no acreditada | No avanzar a DB; si ya hubo commit, mantener fence y recuperar el material previsto mediante su procedimiento explícito. No degradar MFA ni convertir rotate en pérdida autorizada. |
| Servicio/guard/HTTPS falla después de retirar el fence | Detener y reponer fence, conservar commit/material y declarar fallo. No deshacer DB/disco automáticamente para conseguir un health positivo. |

La ausencia del testigo sólo permite retroceder cuando se han probado **también** el fin de la transacción y el estado anterior. Una copia DB antigua junto al anillo final no es automáticamente un rollback: todo Restore vuelve a validar versiones/AAD/material y su propia operación. La retirada de a u otras versiones requiere F-06.02; este protocolo no la ejecuta al terminar `verified`.

## 7. Reutilización y componentes que siguen faltando

| Pieza actual | Reutilización y límite |
|---|---|
| `MfaKeyRing.Parse`, `RequireEntry` | Formato y límites, una activa y versiones retiradas legibles. No añade estados ni publica anillos. |
| `WindowsMfaKeyProvider.GetActiveKey/GetKey` | Nuevos enrolamientos toman la activa; lecturas usan su versión explícita. No selecciona una nueva versión ni registra mantenimiento. |
| `MfaSecretCipher.Open/Seal` | AES-256-GCM y AAD existentes. No interpreta una rotación ni actualiza PostgreSQL. |
| `WindowsMfaKeyStoreWriter` | Creación exclusiva/revisada de almacén nuevo y material importado. No reemplaza anillos vivos. |
| `WindowsMfaKeyRecovery.Export`/archivos | Codec/sobre y publicación de archivo revisados. Sus dos lecturas del anillo no constituyen instantánea estable; el coordinador debe cerrar ABA/retención de objetos. |
| SQL014 y MFA de esquema45 | Factor versionado, estados y límites existentes; sin tabla/testigo/fence/CLI/coordinador de rotación. Migraciones históricas intactas. |
| F-05.04/.05 | Evidencia portable/token real y DB45/TOTP anteriores, útil para material/AAD. No demuestra una rotación, cortes o durabilidad de este protocolo. |

## 8. Entrega posterior e investigación

No se crea un piloto nuevo ni se repiten codecs. F-06.02 debe concretar el registro de dependencias de factores/backups/sobres y el criterio de retirada, conservando este orden. F-06.03 debe implementar el coordinador, testigo/migración, fence/guard y publicador, con un plan de archivos y negativos propios antes de modificar producto: corte antes/después de cada publicación y commit, commit incierto, auditoría fallida, n/cupo agotados, escritura concurrente, factor disabled/pending, cero factores, falta de versión y arranque con fence. F-06.04 revisa el recorrido integrado; aceptar este contrato no acredita esos ensayos.

Investigación proporcional: se reutilizaron D2 y las revisiones L2h/L2i/F04/F05, contrastándolas con las fuentes actuales. Consulta oficial 09.11.2026:

- [PostgreSQL17 · PREPARE TRANSACTION](https://www.postgresql.org/docs/17/sql-prepare-transaction.html): primitiva de 2PC para coordinador externo; no resuelve la publicación ordinaria de archivos de este producto. Se mantiene la elección D2 de conciliación.
- [PostgreSQL17 · bloqueos explícitos/consultivos](https://www.postgresql.org/docs/17/explicit-locking.html): duración de bloqueos y participación voluntaria; el fence persistente y el guard son requisitos de RackClick, no propiedades de un advisory lock.
- [Microsoft · AES-GCM Decrypt y AAD](https://learn.microsoft.com/en-us/dotnet/api/system.security.cryptography.aesgcm.decrypt?view=net-10.0): autenticación al abrir con el contexto correspondiente; el recifrado entre versiones es responsabilidad del protocolo de RackClick.
- [OWASP · Key Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html): ciclo de vida, inventario y disponibilidad del material para recuperar datos; no es una implementación adoptada ni una certificación del diseño.

No se copia código, instala una biblioteca o cambia una dependencia. Las decisiones de secuencia/contrato son desarrollo de la especificación existente, no capacidades ya ejecutadas de esas fuentes externas. [Evidencia y revisión del paso](../evidence/s1-20261109/f06-01-fases/RESULTADOS.md).
