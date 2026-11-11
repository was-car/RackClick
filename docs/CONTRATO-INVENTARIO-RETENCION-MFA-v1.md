# Inventario y conservación de versiones MFA · v1

09.11.2026 · Diseño de F-06.02, continuación del [protocolo F-06.01](PROTOCOLO-ROTACION-MFA-v1.md). D y E no se operan. Se reutilizan el anillo, RCKEY/RCKPAY y sus validaciones; no se cambia SQL014, el coste del sobre, la política45 o el manifiesto de backup histórico.

## Fronteras de este lote

Implementar un inventario de dependencias y una decisión conservadora de **candidata sin referencias**, no una autorización de borrado. El lector PostgreSQL sólo cuenta factores; el inspector de sobres sólo devuelve identidad/versiones/huella tras autenticar y desechar material. Ninguna API de este lote borra archivos, publica un anillo existente, modifica factores o ejecuta servicios. El coordinador/fence/guard/publicador de F-06.03 sigue siendo necesario para usar la decisión sin una carrera con nuevos factores/backups.

El paso se contrasta como componente técnico de retención e inclusión de inventario. Si su revisión no permite acreditar el criterio completo, se mantendrá F-06.02 pendiente con el avance explícito, sin atribuir una retirada de producción. Una decisión sobre metadatos nunca prueba que la base, el dump o el catálogo sean auténticos/actuales.

## Datos y formatos

1. **Factores:** inventario por instalación y versión con recuentos `pending`, `active`, `disabled`. Cero filas es un censo válido; se incluyen todas las filas de la DB, sin filtrar por estado o Systemhaus visible. Versiones1..1000000; estados desconocidos, conteos negativos/overflow, duplicados o exceso de64versiones rechazan. Lectura dentro de transacción explícita read-only RepeatableRead/Serializable; no lee ciphertext, contraseñas, usuarios o TOTP. La vinculación de esa conexión a la instalación se valida por el futuro coordinador; el GUID del parámetro no autentica una DB.
2. **Sobre:** abrir RCKEYv1 y RCKPAYv1 con las piezas existentes; validar instalación esperada y recuperar sólo el listado completo de versiones y su activa, junto al SHA256 del sobre cifrado. Borrar plaintext/copias con los contenedores existentes. No devolver claves, rutas o contraseña. No cambia la forma del sobre: el anillo y sus versiones ya están autenticados dentro de él.
3. **Backup:** inventario lateral nuevo `RackClick.MfaBackupKeyInventory`, versión1, con instalación/backupUUID, hashes SHA256 de manifiestoSQL/dump/sobre, versiones de factores y versiones/activa del sobre. Las versiones requeridas se derivan como unión de las de factores y la activa del sobre: incluso un backup sin factores conserva la clave para arrancar el anillo importado. El sobre debe cubrir todas las requeridas.

El JSON del inventario lateral es acotado a64KiB, campos exactos, UUID no vacíos, hashes hexlowercase64, versiones únicas/ordenadas/rango válido y una activa contenida. La escritura genera forma canónica y copia colecciones del llamador. El parser exige además el SHA256 esperado del propio inventario **procedente de un registro privado de confianza separado**, y los hashes esperados de manifiesto/dump/sobre e instalación. No vale recalcular un checksum desde el mismo archivo alterado. Estos enlaces son condiciones de integridad, no una firma ni una prueba automática de que el dump corresponde al censo.

`RackClick.Backup.ps1` sólo admite `manifest.json` y `data.dump`, con ocho campos cerrados del manifiesto. El inventario MFA va **fuera de esa carpeta histórica**, junto al registro privado del coordinador o en un contenedor nuevo explícito. No se añade una tercera entrada ni un campo opcional al backup existente. El sobre externo y su contraseña siguen separados del servidor/backups; el registro conserva únicamente su referencia/huella. La escritura/publicación del contenedor nuevo y su adopción en los operadores quedan para la integración del coordinador.

## Regla de elegibilidad

Sobre anillo validado, censo de factores y lista completa de backups retenidos del mismo ámbito:

- Una activa o versión desconocida nunca es candidata a retirada.
- Cualquier factor, también disabled/pending, conserva su versión.
- Cualquier backup retenido conserva sus versiones requeridas. Un backup antiguo sin inventario verificado se representa como catálogo incompleto y bloquea la decisión; lista vacía no significa inventario completo por defecto.
- Un ámbito distinto, dependencia ausente del anillo, copia dudosa, versiones inválidas o censo incompleto bloquean. No se elimina una versión para liberar cupo64 ni se reusa su número.
- Sólo si no hay referencias conocidas **y** el catálogo está completo se devuelve `CandidateUnreferenced`. Se devuelven motivos constantes, no datos secretos ni una ruta de borrado. No se reduce el anillo, no se pierde la copia anterior y no se invoca el writer.

Antes de una retirada real F-06.03 deberá tomar la exclusión/fence del protocolo, volver a censar y comprobar el registro de backups/sobres, validar objetos/material, publicar el anillo de forma recuperable y conciliar cortes. Un backup pendiente de exportación o una escritura concurrente cuentan como dependencia incierta. Expirar un backup requiere la política/confirmación de retención correspondiente; no lo hace este componente.

## Plan de implementación y verificación acotado

- `MfaKeyRetention.cs`: modelos cerrados de inventario, inspección autenticada de sobre, JSON lateral ligado y guarda conservadora; sin IO o Npgsql.
- `MfaFactorKeyInventoryReader.cs`: SELECT agregado y read-only en transacción explícita; sin SQL de escritura o identificadores dinámicos.
- Pruebas nuevas separadas: guardas activas/referencias/ámbito/catálogo desconocido, negativos de formato/integridad, inventario real del sobre y compatibilidad con el payload anterior. PostgreSQL17 nuevo sólo para estados/recuentos/cancelación/rol restringido; nunca D/E.
- Primera prueba antes de implementación, luego foco pertinente y una regresión de sobre/payload/anillo. Binlogs privados y SDK fijado. No modificar Program, endpoints, proveedor/writer aprobados, SQL, locks, csproj, instaladores o paquetes.
- Revisión independiente antes de cualquier crédito; pruebas de componente no equivalen a retiro seguro del almacén vivo o inclusión nativa de metadatos en el instalador.

## Investigación y decisión

Se contrastaron el protocolo19, D2, SQL014, `MfaKeyRecoveryPayload`, `WindowsMfaKeyRecovery.Export` y `Get-LockedBackup`. La alternativa de ampliar silenciosamente el manifiesto rompe su contrato cerrado; un nuevo formato RCKEY duplica innecesariamente un inventario ya autenticado. Se elige inventario lateral enlazado y reutilización de parsers, sin bibliotecas o versiones nuevas.

Fuentes primarias consultadas09.11.2026: [PostgreSQL17, aislamiento de transacciones](https://www.postgresql.org/docs/17/transaction-iso.html), para la instantánea de lectura; [OWASP Key Management](https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html), para ciclo de vida/backup/conservación. La consistencia con dump y archivos requiere el coordinador de RackClick: no se deduce sólo del nivel de aislamiento PostgreSQL. Esta investigación no adopta dependencias ni atribuye a las fuentes una implementación propia del protocolo.
