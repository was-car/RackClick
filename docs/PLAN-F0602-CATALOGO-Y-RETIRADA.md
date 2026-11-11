# Catálogo y retirada MFA · plan de implementación

09.11.2026. Continuación solicitada expresamente por Wascar de F-06.02. D/E y los instaladores se conservan. Diseño desarrolla el protocolo existente; no vuelve a decidir custodia/política MFA.

**Objetivo:** catálogo privado de todos los backups retenidos dentro de las raíces declaradas por el operador autorizado y retirada lógica de una versión no activa, sin referencias, bajo mantenimiento exclusivo y recuperación ante interrupción.

**Arquitectura:** catálogo inmutable por generación, ligado a instalación y declaración explícita de cobertura del operador Windows elevado. Se verifica cada backup/recibo/inventario y el conjunto exacto de directorios de las raíces; un desconocido, parcial, desaparecido o alterado bloquea. Coordinador con exclusión local, lock consultivo PostgreSQL exclusivo y ACCESS EXCLUSIVE sobre factores; nuevo censo después de adquirir locks. Fence persistente previo a publicación y guard antes del listener. Se reduce el anillo conservando el archivo DPAPI y anillo anterior; no es borrado criptográfico. Journal permite terminar hacia delante si el anillo es el inicial o el final previstos; cualquier tercer estado mantiene el fence.

**Tech Stack:** .NET10.0.401, PG17.11/Npgsql10.0.3, SQL45 y primitivas Windows existentes. No dependencias nuevas, DDL, recifrado/rotación ni cambios de política45.

**Spec:** PROTOCOLO-ROTACION-MFA-v1.md, CONTRATO-INVENTARIO-RETENCION-MFA-v1.md, D2 vigente. Retirada no escribe factores: no necesita inventar un testigo de commit SQL de rotación. El testigo dedicado y recifrado permanecen F-06.03.

## Decisiones y límites de autoridad

- Un escaneo no descubre medios externos desconectados ni demuestra que no existan otras copias. El operador debe declarar TODAS las raíces retenidas y confirmar cobertura; queda su SID/fecha/declaración en el catálogo protegido. No hay booleano `complete=true` configurable sin contrastar objetos/raíces. La integridad del catálogo se fija además por SHA256 externo. Omitir deliberadamente una raíz por un administrador queda fuera de la confianza local, no se presenta como probado por software.
- Los backups históricos sin inventario, exportaciones pendientes e INCOMPLETE bloquean. No se expiran, borran ni ocultan. Una generación nueva conserva las anteriores y requiere la misma confirmación de cobertura.
- Se conservan el archivo DPAPI de la versión retirada y los anillos/journal anteriores para recuperación. `GetKey(version)` deja de entregarla porque no está en el anillo; no se afirma destrucción física o criptográfica.
- Locks consultivos compartidos del host/CLI de backup y exclusivo de mantenimiento, con connection pooling desactivado para su duración. No se detiene un proceso/servicio por búsqueda de nombre; mantenimiento rechaza un host activo. ACCESS EXCLUSIVE impide factores nuevos y snapshots de pg_dump durante el recenso/publicación.
- File.Replace publica con copia anterior y flush/relectura, sin promesa de durabilidad universal frente a pérdida eléctrica. Fence y journal preceden la publicación. Pruebas de corte de proceso son distintas de corte eléctrico real.

## Tareas / propiedad

- [x] Catálogo: `MfaBackupCatalog.cs`, `MfaBackupCatalogTests.cs`, agente backend. Formato exacto/acotado con IDs/raíces/entradas/pines/autoridad; carga y verificación del conjunto exacto, handles de lectura retenidos de cada backup. Produce snapshot IDisposable con `Backups`, `Digest`, `CatalogId`, `InstallationId`. Reutiliza ParseBackupInventory, no codecs nuevos.
- [x] Almacenamiento Windows: `WindowsMfaMaintenanceStore.cs`, `WindowsMfaMaintenanceStoreTests.cs`, agente Windows. ACL privada desde creación, lock local, catálogo nuevo exclusivo, fence, journal preparatorio y publicación/conciliación del anillo existente por hashes. Sólo métodos internos usados bajo coordinador. No borrar archivos de claves o material ajeno. Puntos de corte internos, no configuración productiva.
- [x] Coordinador: `MfaMaintenanceCoordinator.cs`, `MfaMaintenanceCommand.cs`, `MfaMaintenanceAdmission.cs`, pruebas y harness PG, coordinador principal. Identidad owner/UUID/PG17.11/SQL45, try-lock exclusivo, transaction ReadCommitted + ACCESS EXCLUSIVE + censo de todas filas, EvaluateCandidate y validación del resto del material. CLI local elevada por stdin; guard normal antes listener y lease compartido para backup. Comandos initialize-catalog/check/retire/resume; no endpoint HTTP.
- [x] Revisión independiente acotada del conjunto, negativos antes de aceptar; evidencias, CHANGELOG, continuidad/ledger y métricas sólo según el resultado realmente contrastado.

## Focos y pruebas

Activa, unknown, pending/disabled/active referenciado, backup retenido, catálogo incompleto/alterado/ID ajeno/nuevo directorio, permiso de operador, escritor concurrente, host compartido en marcha, nueva sesión de backup, doble mantenimiento, fence previo, sustitución de anillo, corte antes/después publicación, reanudación idempotente. Comparar todas las filas persistidas y todas las claves anteriores; no sólo contar. Probar GetKey retirado rechazado y activa legible tras reapertura. Build aislado con binlogs privados; ningún secreto/dump/binlog se versiona.

Investigación09.11: se reutilizan las pruebas115/138 y componentes del paso20. [PG17 locks](https://www.postgresql.org/docs/17/explicit-locking.html), [File.Replace](https://learn.microsoft.com/en-us/dotnet/api/system.io.file.replace?view=net-10.0). El reemplazo de un fichero no hace transaccionales DB/disco; por eso retirada sin mutación SQL se concilia mediante hechos y fence, sin simular 2PC.
