# D2 · Condiciones técnicas de recuperación y publicación MFA

> **Fe de erratas de unidad · 03.11.2026 · F-05.02.** La frase histórica «57–62ms por derivación» del apartado3 se precisa así: son duraciones publicadas por xUnit de seis casos `Open`, cada uno con una derivación, GCM, limpieza y aserciones; no un cronometraje aislado de PBKDF2. Corresponden al laboratorio Windows del26.10, no a D ni a cualquier CPU. Se conserva expresamente el perfil600000 y el resto del documento. [Medida, decisión y límites](PASO-015-COSTE-PBKDF2-MFA.md).


03.11.2026 · Especificación de F-03.02, paso9. Complementa la decisión de custodia confirmada; no vuelve a solicitarla. **Define el contrato técnico; no declara implementados el operador de pérdida total, la rotación o el Restore portable.** D y E se conservan sin operaciones.

Precedencia: [custodia confirmada](DECISIONES-MFA-CONFIRMADAS-25-10-2026.md) y [gracia45/exención global](DECISION-MFA-GRACIA-45-DIAS-29-10-2026.md), precisadas aquí en las tres condiciones de la [revisión D2](REVISION-D2-CODEX.md). El cuerpo de [D2v2](DECISION-D2-CUSTODIA-CLAVE-TOTP.md) es histórico donde difiere de estas decisiones. F-03.03, implementación y aceptación operativa conservan sus pasos propios.

## 1. Autoridades e invariantes

El almacén permanece en `%ProgramData%\RackClick\Instances\<installationId>\mfa-keys`, fuera de PostgreSQL y de `management`. SYSTEM/Administradores gestionan; el SID estándar real del servicio sólo lee. El servicio no crea, rota ni repara claves. El sobre y su contraseña quedan fuera del servidor/backups, en los medios separados que custodia Wascar. No se incorporan secretos al journal, auditoría o informes.

Una contraseña válida, un código de recuperación, una autorización local o `enrollment_pending` **no conceden sesión API** durante la recuperación. La prioridad de reenrolamiento se mantiene también para un administrador global exento de gracia45. La exención ordinaria no cancela una recuperación pendiente; al terminarla se conserva la política45 y sus fechas, sin conceder otro plazo.

No regenerar una clave ausente, reutilizar una versión con otro material ni desactivar `MfaKeyStore:Enabled` como reparación. Si falta material requerido, el host normal falla cerrado. Recuperación local significa un operador de mantenimiento separado y explícito; no levantar un servidor web sin protección.

## 2. Recuperación restringida sin la clave perdida

### 2.1 Código de recuperación con el host disponible

Se reutiliza `MfaStore.RedeemRecoveryCode`: exige el desafío de contraseña vigente de finalidad `verify`, CSRF, cuenta habilitada, política/revisión y límites de intentos. No descifra el TOTP. En la misma transacción consume el juego anterior completo de códigos, deshabilita el factor anterior, fuerza `mfa_required=true,enrollment_pending=true`, revoca sesiones/desafíos y audita. Devuelve sólo otro desafío `enroll` de cinco minutos. Confirmar un TOTP nuevo consume ese desafío y emite sesión/CSRF nuevos tras las revalidaciones del servidor.

El endpoint actual necesita un host/proveedor disponible. **No resuelve por sí solo la ausencia total de `mfa-keys`**, porque el arranque cerrado ocurre antes del listener. No se amplía esta ruta a acceso anónimo ni a una sesión de recuperación con permisos de inventario.

### 2.2 Pérdida del almacén, sin sobre útil

El operador local de emergencia, pendiente en F-09, debe realizar esta secuencia bajo mantenimiento exclusivo:

1. Autorizar por token Windows local elevado de SYSTEM/Administradores, sin exigir el factor perdido. Identificar instalación, DB/Systemhaus y SID estándar reales. No depender de una sesión web ni de la nueva cuenta que se pretende recuperar. Comprobar primero el alcance y dejar un plan con operaciónUUID.
2. Detener y bloquear el arranque del servicio identificado. Conservar DB y material anterior, aunque sea opaco, en archivo privado atribuido; inventario, cuentas y permisos existentes se preservan. Determinar todos los usuarios/factores afectados por versiones ilegibles, incluidos factores pendientes, administradores globales y administradores de clientes; no limitarse al último administrador visible.
3. Preparar y verificar material nuevo mediante el protocolo del apartado4. En una instalación que ya tuvo factores **no se reutiliza sin más `CreateInitialStore`/versión1**. La versión nueva debe superar el máximo autoritativo de factores de cualquier estado, anillos/journal y backups retenidos. Rango del parser:1..1000000; máximo64versiones por anillo. Si no puede determinarse un máximo fiable o se agota el perfil, se detiene la operación: sólo una recuperación explícita a un espacio de instalación nuevo, con vínculo de origen/destino y retiro de factores antiguos, puede resolverlo; nunca una colisión o descarte silencioso.
4. En una transacción PostgreSQL, retirar del uso los factores ilegibles sin destruir la copia anterior, fijar reenrolamiento obligatorio de los afectados, incrementar revisión de política individual, revocar sus sesiones/desafíos y retirar sus códigos viejos. Mantener usuarios, capacidades, ámbitos y fechas de gracia. Registrar la autoridad local real, alcance y marcador de commit, sin claves/ciphertext/códigos/contraseñas. Si la auditoría o cualquier escritura falla, todo ese cambio DB retrocede.
5. Completar la publicación y sus comprobaciones antes de desbloquear el host. Con contraseña válida, el afectado recibe sólo un desafío `enroll`; no se autentica con el factor ilegible ni obtiene acceso completo por ser global exento. La confirmación del nuevo factor es la única transición a una sesión nueva. Una contraseña también perdida requiere su procedimiento explícito; no se omite la comprobación de contraseña.

El login actual ya prioriza `enrollment_pending`; se reutiliza. **`--recover-admin` es recuperación de administrador para Restore, no este operador:** no prepara anillo, no retira todos los factores/códigos ni fuerza esa transición. Tampoco la autorización local equivale a que la cuenta del servicio tenga privilegios de administración Windows o PostgreSQL.

### 2.3 Sobre útil

Recuperar su material conserva versiones y claves, autentica origen y exige adaptación explícita de `installationId` para DPAPI del destino. No cambiar silenciosamente `systemhausId`, `userId` o `key_version`: los factores usan AAD `rackclick-mfa-v<keyVersion>|<systemhausId:D>|<userId:D>`. Cambiar esos IDs exige descifrar/autenticar y recifrar cada factor con sus identidades destino en la transacción prevista; adaptar sólo el anillo de Windows no lo hace.

Los backups deben identificar las versiones requeridas y el sobre externo correspondiente. Una versión ausente o una identidad incompatible bloquea Restore antes de adoptar el destino; no produce una instalación parcialmente autenticable. Esta integración sigue pendiente en F-05/R-04.

## 3. Perfil RCKEYv1 cerrado

Se conserva el codec revisado; no se crea otro formato ni se cambia el coste silenciosamente.

| Campo | Contrato exacto |
|---|---|
| Sobre | Mínimo60bytes; máximo1048576bytes, antes de PBKDF2 |
| Magia y versión | Bytes0..4=`RCKEY`; byte5=1 |
| Algoritmos | Byte6=1:PBKDF2-HMAC-SHA256; byte7=1:AES-256-GCM |
| Iteraciones | Bytes8..11,uint32big-endian, **exactamente600000**; mínimo=máximo del perfil. Cualquier otro valor se rechaza antes de derivar |
| Sal | Longitud16 enbyte12;16bytes aleatorios en13..28 |
| Nonce | Longitud12 enbyte29;12bytes aleatorios en30..41 |
| Tag | Longitud16 enbyte42;16bytes en43..58 |
| AAD | **Bytes0..42 completos**,43bytes: incluye magia, versión, algoritmos, coste, longitudes, sal y nonce; excluye tag/ciphertext |
| Ciphertext | Desde59hastaEOF; longitud1..1048517. Añadir bytes/otro sobre no se ignora: altera la autenticación |
| Derivación |32bytes de salida; contraseña12..256puntos de códigoUnicode, UTF-8 estricto, sin normalización; sustitutos sin pareja rechazados |
| Contenido | `RCKPAY`v1: anillo canónico≤65536bytes,1..64versiones, registros ascendentes únicos y32bytes de clave por versión; identidad origen explícita y fin exacto |

El operador debe acotar la lectura de entrada antes de materializarla: archivo≤1MiB y contraseña≤512unidadesUTF-16, seguida de la validación12..256puntos de código; no truncar ni normalizar. No hay negociación de algoritmos ni lectura de una cifra de iteraciones arbitraria como instrucción de trabajo. Cambiar el perfil exige versión y revisión nuevas.

Una operación administrativa por instancia, sin trabajos KDF concurrentes ni reintentos automáticos. No se publica este descifrador como endpoint anónimo. La medición histórica57–62ms por derivación corresponde sólo al Windows de laboratorio del26.10; no es SLA ni medida actual de D. Un límite de tiempo del operador no hace cancelable la llamada síncrona PBKDF2: una interrupción obliga a conciliar el estado del proceso, no a lanzar otro trabajo solapado.

Formato/parámetros/longitud inválidos se rechazan antes del KDF con su categoría. Con cabecera y contraseña bien formadas, contraseña incorrecta o autenticación alterada producen `AuthenticationFailed`, sin revelar payload o clave; no se afirma igualdad universal de tiempos/errores. El llamador borra plaintext y copias de claves cuando termina. Una contraseña `string` y copias internas del runtime no ofrecen borrado físico universal.

## 4. Publicación recuperable entre disco y DB

Un rename local y una transacción PostgreSQL **no forman una transacción conjunta**. Se adopta mantenimiento exclusivo con journal y conciliación; no se introduce un coordinador distribuido ni `PREPARE TRANSACTION` para hacer pasar un archivo por participante transaccional.

### 4.1 Contrato del coordinador pendiente

- Una sola operación para la instalación/DB. El operador toma exclusión local y bloqueo de mantenimiento DB; servicio detenido y **fence duradero de arranque**, comprobado antes de aceptar listeners también después de reiniciar Windows. El fence no se retira por antigüedad o porque el proceso anterior murió.
- Journal privado fuera de `mfa-keys`, creado con DACL privada desde su primera escritura: operaciónUUID, tipo, instalación/origen/destino/Systemhaus/DB, SID lector/operador, fase, conjunto de versiones y hashes/identidades del material anterior/preparado/final. No guarda contraseña, claves en claro, connectionString, TOTP ni códigos. No amplía el acceso del servicio a `management`; el fence usa un marcador separado que el guard de arranque pueda leer sin conceder ese acceso.
- El commit DB se acredita mediante un **registro de mantenimiento local dedicado**, ligado por operaciónUUID única a esos IDs y hashes. Se inserta en la misma transacción que el recifrado/retiro/revocación: no se deduce del exit del padre, de un nombre de archivo o de la ausencia de logs. Su contrato incluye tipo de autoridad `windows-local`, SID real, fecha y resultado; la migración/adaptador se implementa en F-06/F-09, no existe hoy. Creación/migración con identidad separada; runtime sólo SELECT para su guard, sin INSERT/UPDATE/DELETE/DDL sobre ese registro.
- `audit_event.actor_id` exige un usuario de aplicación existente. No se inventa una sesión/appactor para satisfacerlo: el registro dedicado audita la autoridad Windows; la auditoría web conserva su actor real. Si se agrega una proyección al historial común, deberá identificar expresamente la autoridad local, sin suplantar al afectado.
- Se valida ACL, propietario, reparse, identidad/ruta final y bytes sobre identificadores retenidos donde corresponda. Material ajeno/preexistente no se sobrescribe ni se limpia por nombre. Residuos propios no retirables quedan declarados. Escritura/flush/rename y relectura no se presentan como prueba de durabilidad ante corte eléctrico.

### 4.2 Orden obligatorio y caídas

El journal fija el modo antes de escribir: `rotate`, `portable-restore` o `loss-reset`; no se cambia por un error posterior. **Los materiales exigidos dependen de ese modo:**

- `rotate`/`portable-restore`: se conservan y autentican todas las versiones que requieren factores usables y backups retenidos del alcance. Si falta una, se detiene; no se transforma el fallo en pérdida autorizada.
- `loss-reset`: la autorización local y el plan identifican expresamente las versiones irrecuperables, todos los factores/usuarios afectados y los backups cuyo MFA deja de ser recuperable. Se conservan sus copias/material opaco, pero **no se finge disponer de claves anteriores**. Se preparan sólo claves nuevas y un sobre nuevo para ellas; en la transacción se retira del uso todo factor que dependa de las perdidas y se fuerza su reenrolamiento. El anillo vivo final sólo necesita las versiones nuevas y las anteriores que sí sigan siendo recuperables/usadas. Los backups anteriores afectados no pasan a ser restaurables con el nuevo sobre: se mantienen marcados con ese límite, sin borrarlos ni anunciar recuperaciónMFA integral.

La comprobación de cobertura se hace contra el conjunto vivo **posterior a la transacción** y la lista de backups recuperables declarada. Una pérdida no incluida expresamente en `loss-reset`, un afectado omitido o una dependencia desconocida impiden continuar. La conservación de copias opacas no cuenta como cobertura criptográfica.

| Fase | Hecho antes de avanzar | Conciliación si se interrumpe |
|---|---|---|
| `planned` | Identidades, permisos, inventario de versiones/backups y copia privada previa contrastados; fence/journal duraderos | Sin commit DB: conservar/copiar pruebas, verificar que nada usa material nuevo; no arrancar por defecto |
| `material_ready` | Material destino preparado y lector aprobado/DPAPI/SID contrastados. Rotación: anillo aditivo conserva todas las anteriores y su activa. Restore: importa las mismas claves/versiones/activa con reprotección DPAPI, sin rotación implícita. Pérdida: candidato nuevo separado y material anterior opaco preservado. Sobre externo cubre las versiones recuperables exigidas por el modo antes de que DB dependa del material destino | DB sigue anterior. Puede reanudarse por operaciónUUID; no se borra ni sustituye material a ciegas |
| `db_committed` | Una transacción acredita el Restore autenticado, reenvuelve factores o aplica la pérdida explícita según el modo, revoca lo previsto y registra marcador/auditoría; no altera inventario. Restore con AAD conservada no recifra TOTP; siempre invalida sesiones/desafíos restaurados antes de servir | Consultar marcador porUUID e identidades. Commit incierto no significa rollback: no repetir ni restaurar el anillo anterior como única copia |
| `ring_published` | Publicar anillo final con la activa prevista (la importada en Restore, sin exigir versión nueva) y las versiones legibles requeridas por el modo; verificar el objeto publicado y conjunto vivo requerido por DB | Con DB comprometida se termina la publicación hacia delante usando material ya preparado; no se elimina una clave viva referenciada. En pérdida no se exige descifrar el material retirado |
| `data_verified` | Comprobación offline de claves usadas por todos los factores que deben seguir usables (activos o pendientes no retirados), identidades/AAD/ACL y SID correctos, copia externa/versiones coherentes | Único punto que permite retirar el fence para intentar el arranque controlado; conservar journal y exclusión. No equivale a servicio o usuario recuperados |
| `service_resumed` | Arranque normal y HTTPS/health correctos, guard de coherencia DB/disco antes del listener; las cuentas afectadas siguen en enrolamiento restringido | Si falla, detener y reponer fence; conservar el commit/material, sin rollback automático ni éxito. No bloquear el reenrolamiento manteniendo el host apagado |
| `verified` | Servicio contrastado y recibo final de la operación de claves; residuos/estado de usuarios declarados | Cerrar journal/liberar exclusión. La recuperación de cada usuario sólo termina al confirmar su nuevo factor; no convertir `service_resumed` en acceso API ni en ese éxito individual |

Para preparar una rotación con el formato actual, la versión nueva puede figurar legible como `retired` junto a la activa anterior; ese estado sólo permite descifrado, no la elige para nuevos enrolamientos. El journal explica que es material preparado; no se inventa un tercer estado del parser. Tras commit se publica como activa. Toda versión usada antes/durante/después debe estar disponible; no afirmar que la clave anterior sola descifra factores ya recifrados.

El nuevo publicador debe conservar la identidad verificada y no reemplazar material ajeno. `WindowsMfaKeyStoreWriter` actual sólo crea un almacén nuevo: **no acredita reemplazo seguro de un anillo existente**. Antes de aceptar `material_ready` en producción deben estar ensayadas la persistencia requerida y recuperación ante cortes; ante durabilidad no acreditada o sobre externo no confirmado, se detiene antes de cambiar DB. No basta `Directory.Move`/`Flush` para prometerla.

La exportación para backup/rotación debe tomar la misma exclusión y una instantánea estable de todo el anillo/material, con retención/verificación de sus objetos, no sólo dos lecturas de `ring.json`. El exportador actual admite la limitación ABA; no se acredita esa consistencia global todavía. Las claves `retired` no se borran mientras un factor **o cualquier backup retenido** las necesite; un inventario de dependencias desconocido bloquea su retirada. La retención temporal/RPO/RTO se concreta en R-01, sin rebajar esta dependencia.

## 5. Evidencia reutilizada y trabajo separado

| Área | Lo reutilizable | Lo que no se declara resuelto |
|---|---|---|
| Sobre | [Revisión L2d](REVISION-MFA-L2D-CODEX-26-10-2026.md):26casos+8controles independientes; AAD aislada y límites antes de derivar | Nueva plataforma, duración universal, secretos ausentes de toda memoria |
| Payload/recuperación | [L2f](REVISION-MFA-L2F-CODEX-26-10-2026.md), [archivos L2g corregidos](REVISION-MFA-L2G-CORRECCION-CODEX-26-10-2026.md); identidad explícita y publicación exclusiva | Snapshot global, durabilidad de directorio, RestoreDB/host portable |
| Login/códigos | `PostgresStore.Authentication`, `MfaStore.Recovery`, confirmación y política45 existentes | Operador local de pérdida total, recuperación del último administrador completa |
| Disco/DB | Escritor/lector y transacciones de aplicación como piezas ya revisadas | Registro DB/fence/journal/reconciliador/publicador de rotación y sus ensayos |

F-04 cierra SID/ACL/fallos del proveedor y su integración; F-05 el sobre y recorrido portable; F-06 rotación/rewrap/caídas; F-08 códigos; F-09 emergencia; R-03/R-04 backups/Restore completos. No se cierran por este documento. F-03.03 conserva la revisión específica de amenazas. Sólo F-03.02 es elegible como especificación tras revisión independiente.

Pruebas de implementación exigidas en esos pasos: contraseña/código inválidos y replay; sesión/API ausentes hasta confirmar; pending aun con exención global y ante acciones administrativas `disable`/`reset` o activación de política (ninguna puede cancelar la recuperación sin nuevo factor); pérdida de una/todas las versiones; KDF fuera de perfil sin derivación; AAD/tag/bytes extra; origen/adaptación/AAD incompatibles; cuenta ajena/servicio sin escritura; operación concurrente; corte antes/después de cada fila de la tabla anterior; commit incierto con marcador presente/ausente/DB no disponible; restaurar backup anterior y posterior con todo su material; fallo de auditoría y namespace/versión colisionados. Son criterios pendientes, no ejecuciones nuevas; la prioridad existente en login no acredita todas esas mutaciones administrativas.

## 6. Investigación y decisión de reutilización

Se contrastaron primero las decisiones de Wascar, revisiónD2 y los codecs/operadores/pruebas existentes. Se reutilizan sin nuevas librerías ni versiones. Consulta oficial03.11.2026: [.NET10 AES-GCM/AAD](https://learn.microsoft.com/en-us/dotnet/api/system.security.cryptography.aesgcm.decrypt?view=net-10.0), [PBKDF2](https://learn.microsoft.com/en-us/dotnet/api/system.security.cryptography.rfc2898derivebytes.pbkdf2?view=net-10.0), [PostgreSQL17/2PC](https://www.postgresql.org/docs/17/two-phase.html). La elección del journal/fence es decisión arquitectónica de RackClick; las fuentes explican las primitivas, no certifican el protocolo propuesto.

Esta tanda sólo inspecciona fuentes/evidencia y concreta condiciones. Hashes, trazabilidad y revisión se conservan en [el lote F-03.02](../evidence/s1-20261103/f03-02-condiciones/RESULTADOS.md). No hay código, migración, ensayo nuevo de claves, operaciónVM ni crédito ponderado por escribir esta especificación.


## Adenda de revisión 8–18 · 03.11.2026 · ruta efectiva del almacén

La ruta abreviada del apartado 1 omite un nivel de aislamiento del perfil Windows existente. Se precisa aquí sin mover, regenerar ni modificar claves o instalaciones:

- El componente recibe una raíz explícita `MfaKeyStore:InstancesRoot` y localiza el almacén en `<InstancesRoot>\<installationId>\mfa-keys`.
- El perfil nativo actual fija esa raíz en `C:\ProgramData\RackClick\Instances\<installationId>\security`. Por tanto, su ruta efectiva es `C:\ProgramData\RackClick\Instances\<installationId>\security\<installationId>\mfa-keys`.
- Este identificador es el de instalación MFA del plan/perfil (`setupPlan.id`), no un UUID deducido del nombre de una base. La raíz configurable del componente no autoriza a sustituir la ruta fijada por el perfil nativo ni a ampliar sus permisos.

Contraste de fuentes: `tools/windows/server-install/RackClick.MfaRuntime.ps1`, `Get-ServerMfaProfile` (líneas47–55), y `development/server/src/RackClick.Server/MfaWindowsHostComposition.cs`, `Compose`/`Validate` (líneas94–108 y135–136). Se mantienen almacén fuera de PostgreSQL y de `management`, propietario de confianza y lectura del SID del servicio. Es una corrección documental de la descripción, sin cambios de código, custodia, política45, criterios, pesos o datos. La versión anterior y la revisión separada se conservan en [la auditoría8–18](../evidence/s1-20261103/revision-pasos08-18/).
