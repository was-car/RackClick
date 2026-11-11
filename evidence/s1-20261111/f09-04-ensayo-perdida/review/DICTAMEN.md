# Revisión independiente F-09.04 · paso32

## Dictamen vigente final · 11.11.2026

**Favorable al cierre técnico de F-09.04, con el alcance y límites siguientes.** No se encontraron nuevos bloqueantes P1/P2 tras leer la secuencia nativa final y contrastarla con sus fuentes y pines. El criterio de pérdida simulada de todo el material de claves disponible, arranque rechazado, recuperación local explícita y regreso mediante enrolamiento restringido está suficientemente respaldado en la instancia sintética propia de E. El coordinador decide la conciliación del ledger; este dictamen no acredita F-09.05, los seis hitos completos de F-09 ni adopción productiva.

### Evidencia final contrastada

| Condición de F-09.04 | Evidencia realmente leída | Evaluación |
|---|---|---|
| Base real antes de pérdida | Baseline551fe16e exit0, recibo con TLS/pin, único global con MFA activo v1, inventario sintético, sesión/desafío y diez códigos guardados privadamente. SHA256 del recibo `613121b1cad71f2291b23547c0c3d6de8843aeddc9f3b4e65f6786cf2f8e64d6` coincide con el pin usado al disparar la pérdida. | Cumplida en ese fixture; no es la DB de D ni el conjunto50clientes. |
| Pérdida de todas las claves de ese anillo | StopApp27f8d410 y RemoveKey1-13c883c0 exit0; fuente exige sólo ring+keyv1 y recibo Baseline fijado. loss-trigger declara lostVersions=[1], sin copia del material, ring conservado. | Cumplida para material v1, con metadatos fiables conservados. |
| Arranque normal rechazado | StartApp61ab8c4b solicita arranque; no se confunde su exit0 con readiness. FailedStart7427ad8b exit0 exige servicio Stopped, cero listener y último stderr exactamente `mfa_keystore_version_missing`, proveedor habilitado. | Cumplida antes del listener. |
| Autoridad y transición explícitas | Prepare245fff9f, Exporte6cc6b06, Apply6fa8f6b5, Publish38bf48ab y Complete18af25d7, todos parent/child/task0; misma operación, nueva versión2, fichero externo de297bytes con SHA256 fijado, fases fenced→committed→published→released. Todas declaran sessionGranted=false y serviceVerified=false. | Cumplida bajo SYSTEM real por tarea acotada; no se presenta como positivo Admin de mantenimiento. |
| Host y administración recuperados | StartApp66ebafaa y Recovered-a09e55f8 exit0; TLS/servicio Running, sesión anterior y solicitudes con código/desafío anteriores rechazados, cero seguridad pendiente anterior por SQL, inventario sentinel igual, API denegada antes del TOTP nuevo, factor activo2 y sesión/CSRF nuevos. Fuente comprueba witness Windows/local con factores/sesiones/desafíos/códigos revocados, y que el cliente vuelve a leer el sentinel por API. | Cumplida por servidor nativo/PG17/DPAPI con cuenta estándar real y cliente HTTP Admin. |
| Conservación y cierre de laboratorio | StopAppa20535a0/StopOwnDatabasee4fedc93 exit0; observación final de E conserva las dos instalaciones previas Running y deja sólo los dos servicios propios Stopped, puertos propios cerrados e intento antiguo archivado. Recibo final: cero tareas temporales propias pendientes. | Cumplida según observación final y recibos del coordinador. No hubo apagado/reversión VM por el revisor. |

Se leyeron los recibos de `native/collected/` (provision/baseline/loss-trigger/failed-start/recovered/catalog y las cinco respuestas CLI, todas de metadatos) y los16resultados de fases finales. Los14lanzamientos SYSTEM registran taskRegistered/taskStarted/completed/taskRemoved=true, timedOut=false y parent/child/task exit0. Las dos fases HTTP Admin tienen parent0 y stdout baseline_verified/recovered_verified. La cuenta Windows cliente, la autoridad local de mantenimiento y la identidad de ejecución del servidor son distintas y quedan nombradas como tales.

### Qué ejecutó y qué no ejecutó este revisor

Revisión independiente de fuentes/cambios y recibos: sí. La revisión independiente de componentes anterior registró40/40PASS sobre el freeze48 inmutable con PG nuevo; se leyó y se reutiliza con su atribución original, no como ejecución de este agente de revisión nativa. Focos propios de host PS5.1: pines/parser; Common02retorno3frenteaCommon03retorno1/exit7rechazado; lectura PID compartida/ausencia2/bloqueo32/tamañoexcesivo. Todos con resultados privados conservados y alcance detallado en las secciones históricas.

**No ejecutó E/VM, servicios/cuentas Windows, SQL o HTTP nativos, tareas SYSTEM, copia de claves ni los pasos nativos finales.** Las378pruebas de regresión del coordinador y su ensayo nativo se atribuyen al coordinador. No se abrió http-state, credenciales, checkpoint en claro, initstdout con secretos ni sobre de recuperación para esta revisión final. No se recompiló ni se alteró el producto o la DLL d9366dbe9be377d4147417fd8c51e40aaa302b82c8d3bd9b830c67d68980b909.

### Límites que permanecen

- El fixture pierde toda su clave v1, conservando ring/catálogo/identidad. No demuestra pérdida de todos los metadatos, namespace nuevo, robo de claves ni recuperación tras apagón físico.
- Cinco CLI ensayadas como SYSTEM; el positivo de mantenimiento Admin sin esa ruta y su manual/automatización final siguen pendientes de F-09.05. El cliente HTTP Admin no cierra ese pendiente.
- Sobre cifrado externo al SCMroot/backups pero en el mismo disco de E y con custodio sintético; custodia física fuera del servidor, contraseña por medio separado y aceptación de Wascar no se acreditan aquí.
- Se verifica inventario sentinel de cliente/rack/dispositivo del fixture, no todas las relaciones del ejemplo50 ni datos de D. No hay nueva QA GUI ni resultado manual de Wascar.
- Los cortes lógicos del protocolo/guards pertenecen a los40focos/componentes de la revisión independiente anterior; el ensayo nativo final no es una prueba de durabilidad ante corte eléctrico ni reinicio real del sistema.
- La retirada posterior a pérdida y una segunda pérdida tras completion no se ensayaron en este tramo; sus límites conocidos deben conservarse en la continuidad, sin atribuirlos como cerrados por el primer recorrido.
- El harness es privado y tuvo fallos de preparación/cliente registrados abajo (pipes, retorno PS5.1, lectura PID, contexto Scheduler y timeout HTTP). Se conservaron intentos y datos parciales y se conciliaron antes de continuar. El resultado completo no se presenta como primer intento íntegramente verde. La causa universal de los timeouts del cliente SYSTEM no quedó resuelta.
- Instalador48, candidata completa, distribución/redistribución, F-09.05 y aceptación/adopción siguen pendientes. D quedó fuera del bridge de ejecución; las observaciones finales sobre E no prueban por sí solas el contenido histórico de D.

## Historial de la revisión y sus gates parciales

Las secciones siguientes conservan el estado y los hallazgos de cada fase. Sus frases de «pendiente» o «dictamen parcial» describen aquel momento; el dictamen vigente es el anterior. No se convierten pruebas fallidas o gates estáticas en ejecuciones aprobadas retrospectivamente.


11.11.2026. **Dictamen parcial favorable a los componentes repetidos sobre review48-01; no aprobación de cierre F-09.04.** Repetición propia40/40 PASS,0FAIL/0omitidas, con pines inmutables y PostgreSQL nuevo. El ensayo nativo de autoridad/SID/SCM/HTTPS y el retorno administrativo del host perdido siguen pendientes. Las secciones provisionales siguientes conservan la secuencia de hallazgos y su atribución; el resultado ejecutado definitivo de esta revisión parcial se detalla al final.

Revisor distinto del implementador. Propiedad exclusiva de este dictamen y auxiliares `.local/f0904-review-*`; no se editan producto, pruebas ni metadatos compartidos. Sin D/E, VM, servicios/cuentas Windows, instalaciones, commits o push. El revisor no recompiló ni hizo restore; ejecutó directamente VSTest sobre la copia sellada, con clúster/roles/cuentas app sintéticos propios.

## Contrato y reutilización

El criterio congelado de F-09.04 exige «Ensayar pérdida simulada total, arranque fallido explícito, recuperación local y vuelta mediante enrolamiento restringido». D2§2.2/§4 exige mantenimiento exclusivo, autoridad Windows real, ámbito vinculado, conservación del material anterior, transacción/revocación/testigo, publicación autenticada, comprobación offline y sólo entonces retirada del fence para un arranque controlado. Servicio recuperado y recuperación individual son hechos distintos.

Se reutilizan los resultados y dictámenes F0902/F0903: Prepare/Export/Apply/Publish, censo fiable, versión superior al máximo, archivo cifrado privado, pending/revocación, witness dedicado y pin inmutable del sobre. Las pruebas históricas no se presentan como propias ni repetidas. El baseline recibido tiene232fuentes de producto/esquema47; la CLI todavía devuelve transition_unavailable y Publish conserva el fence. No es aún un recorrido de servicio.

## Mínimos y riesgos concretos previos a la implementación

| Gravedad | Riesgo/condición observada | Comprobación necesaria |
|---|---|---|
| P1 de composición | El guard de rotación actual exige active/factores iguales a la última rotación46. Ejecutarlo sin arbitraje tras una pérdida47 legítima bloquearía el host; omitirlo globalmente abriría incoherencias. | Seleccionar y validar la operación vigente por modo/versión/UUID con recibo propio loss-reset. Conservar comprobación de rotaciones que sean posteriores y rechazar versiones/modos/recibos incompatibles. No fabricar un recibo rotate para pérdida. |
| P1 de autorización de datos | Runtime no tiene USAGE/SELECT sobre rackclick_private. Un guard nuevo no debe resolverlo abriendo el archivo de factores ni DML del witness. | Lectura mínima de metadata para el guard, con grants explícitos y prueba runtime de rechazo de SELECT del archivo y de INSERT/UPDATE/DELETE/DDL. Sin autoridad owner en el servicio. |
| P1 de arranque | El fence es hoy la barrera duradera. Retirarlo sólo por retorno de Publish, proceso muerto, nombre de archivo o recibo sin binding permitiría un arranque incompleto. | Recibo loss vinculado a instalación/DB/Systemhaus/UUID, witness, versión, plan, sobre y material publicado; autenticación de todos los factores retenidos y relectura de objetos. DB no disponible, ausencia/alteración de recibo o publicación parcial deben cerrar antes del listener. |
| P1 de interfaz local | La nueva composición CLI procesará datos que antes ni leía. No debe convertir un seam de fixture, configuración, claims o variables en autoridad Windows. | Autorizar antes de leer stdin/config/SQL; entrada cerrada y acotada, conexión de mantenimiento separada, servicio vinculado detenido en cada etapa. No endpoint HTTP de emergencia ni fallback a recover-admin/CreateInitialStore. |
| P2 de conciliación | Un commit DB incierto o caída entre key/ring/recibo/fence no equivale a rollback; una repetición podría duplicar o destruir estado. | Reentrada por el mismo UUID basada en witness y objetos retenidos; hacia delante tras commit, sin repetir revisiones/revocaciones. Recibo/fence ajenos, reemplazados o modificados bloquean. Fence retenido/repuesto si falla el arranque controlado. |
| P2 de evidencia | Backend enroll ya probado no acredita servicio Windows, identidad/SID efectivo, HTTPS ni vuelta administrativa del host perdido. | Atribuir cada ejecución: componentes propios sobre PG nuevo frente a ensayo VM elevado/servicio del coordinador. Contraseña válida sólo enroll; sin sesión/API hasta TOTP nuevo; credenciales antiguas rechazadas, cuenta/inventario/gracia preservados. |
| P2 de secretos | Export devuelve sobre en memoria; una CLI puede filtrarlo junto con contraseña/owner connection en stdout/stderr, argumentos o errores. | Salidas cerradas de metadata, entrada privada por stdin y material externo tratado con límites; errores no imprimen payload/secretos. Logs/TRX/binlogs privados, sin sobre/contraseña de custodia versionados. |

Los P1 anteriores describen condiciones de integración pendientes, no vulnerabilidades confirmadas en una instalación adoptada. La revisión inicial no pide rehacer codecs, login, portabilidad, rotación ni pruebas ya acreditadas.

## Archivos y símbolos consultados

- Gobierno y evidencia: AGENTS, BRIEFING-MAESTRO, inicio vigente de CONTINUIDAD-CODEX y PROGRESO-GLOBAL; EQUIPO-Y-SKILLS; consulta pertinente de INICIO-IMPLEMENTACION-S1, CONTRATO-SERVIDOR-v0.1, MAPA-RC9-R3, ACEPTACION y README del servidor. D2§2.2/§4, criterio F0904 en PLAN-PENDIENTES-NUMERADO, plan F0903. RESULTADOS y review/DICTAMEN F0902/F0903.
- `MfaLossResetCoordinator.cs`: entradas nativas/Native, RunCore/RunExclusiveCore, Exclusive, RequirePlan/RequireWitness, AuthenticateRetained y VerifyEnvelope.
- `WindowsMfaMaintenanceStore.Loss.cs`: PrepareLoss, ReadLossJournal, Inspect/RequireLossMaterial, Pin/RequireLossEnvelope y PublishLoss; conservación del fence y originales.
- `MfaRotationStartupGuard.cs`: ValidateAsync completo; selección de último witness46, binding/active/factores, recibo y control del fence.
- `MfaEmergencyRecoveryCommand.cs`: Run, AuthorizationFailure, WindowsAuthorityFailure y política DenialForToken. `Program.cs`: despacho previo al host y admisión/guard antes del listener.
- SQL047 completo: testigo metadata y archivo factor_row separados, schema privado sin permisos runtime. `WindowsMfaMaintenanceService.cs`: RequireStopped y binding identificado del servicio.

## Pruebas y límites provisionales

Ejecutado: lecturas estáticas y `git status --short` inicial. Sin cambios de producto y sin prueba ejecutable propia aún. No se usó grafo ni se afirma cobertura de indexación. Se espera entrega de freeze/binarios/manifiesto/pins para una repetición acotada sin recompilar, con PG17 nuevo y roles sintéticos propios; el resultado sustituirá este estado provisional.

No se ejecutaron elevación/SYSTEM positivos, SCM/SID efectivo, CLI funcional, arranque/servicio recuperado, HTTPS, confirmación de usuario, cortes, reinicio/apagón, custodia física o durabilidad universal. D/E y resultados de Wascar se preservan. F0904/.05 y los seis hitos completos no se acreditan por esta revisión. Índice recibido26,13/100 del cierre restante, sin incremento y sin porcentaje global nuevo.

## Segunda inspección parcial · fase A

Recibida fase A con14/14 del coordinador en `extended-sanitized.json`; son evidencia ajena, no ejecuciones propias. Inspeccionados `MfaLossStartupGuard.ValidateIfLatestAsync`, `WindowsMfaMaintenanceStore.LossStartup` completo, migración048 y adaptaciones de coordinator/ReadStartupWitness/guard de rotación/rutas Win32. La proyección enumera19campos y usa GROUP BY; el archivo privado no se expone. Recibo loss de8campos y completion privado enlazan witness/material/journal/objetos. Retirada del fence mediante handle con identidad retenida. Guarda sólo lectura: exige proyección con esquema48 y contempla ambas ordenaciones loss/rotate sin exigir snapshot de seguridad inmutable después del enrolamiento.

**Hallazgo P2 funcional, pendiente de corrección/verificación:** en esta fase Complete no consulta la proyección pública antes de publicar el recibo y retirar fence. El adaptador admite47; completar una pérdida47 o eliminar la vista48 antes de Complete puede devolver data_verified_released aunque el siguiente arranque rechace por projection_missing. No se encontró por ello un bypass del listener: la guarda posterior falla cerrada. Incumple la comprobación previa a liberar fence y anunciar data_verified. Comunicado al coordinador, quien informó un rojo discriminante propio por ausencia del rechazo; ese rojo no fue ejecutado por el revisor. Pendiente comprobar corrección y permisos SELECT del runtime asignado.

**Incidencia de entrega, sin pruebas ejecutadas:** el canario de pins de `.local/f0904-review-run.py` detuvo la preparación antes de toolchain/Lab/PostgreSQL/MSBuild. Server y copia de testServer coincidían con0b840919…, pero tests esperado2a5bdb… difería de2ba4197b… en la copia y92a89f76… en el freeze consultado inmediatamente después. El coordinador confirmó un freeze aún mutable por compilación concurrente y ordenó detener. No se usa esa copia mezclada como evidencia de producto ni se recompila para hacer coincidir hashes. Directorio propio preservado `.local/f0904-review-7b82e84f`; no contiene un ensayo ejecutado. Se espera una copia binaria sellada final independiente del freeze de implementación.

## Tercera inspección parcial · CLI y corrección de proyección

Inspección estática de `MfaLossRecoveryCommand` completo, `ExportToFileAsync`, `ApplyFromFileAsync`, `RequireExternalEnvelopeFolder`, `RequireStartupProjection` y despacho de Program. Sin ejecución sobre el freeze mutable.

La corrección de Complete exige esquema48/vista presente, USAGE/SELECT del rol runtime concreto y igualdad del witness proyectado con el privado antes de recibo/fence. Es adecuada por inspección para el hallazgo P2; su estado ejecutado sigue pendiente de repetición propia. El coordinador informa rojo discriminante y focos verdes, que no se atribuyen al revisor.

CLI autoriza nativamente antes de leer stdin; parser cerrado con duplicados/campos desconocidos rechazados, profundidad/límites y confirmación específica de instalación/UUID/fase. Las cinco acciones mantienen identidad de mantenimiento separada y SCM parado/vinculado. Export entrega metadata y archivo externo protegido; Apply conserva una instantánea acotada de sus bytes y exige hash/autenticación, con borrado de esa copia. Se rechaza sobre dentro de root SCM/raíces de backup o en sus ancestros; se reutilizan comprobaciones de ACL/ruta/identidad de los componentes previos. No se encontró una ruta HTTP, seam de configuración/autorización ni salida de contraseña/connectionString/sobre. `data_verified_released` declara expresamente `sessionGranted=false,serviceVerified=false`.

Observación menor comunicada: Limit65536 se mide en unidades UTF-16, y GetByteCount sólo valida Unicode; por tanto no es un límite exacto de64KiB UTF-8. Documentar64Ki caracteres o aplicar el límite de bytes si se promete KiB. No es lectura ilimitada ni bloqueante de seguridad en este alcance.

## Revisión estática previa a Provision nativo

Consultados `.local/f0904-793425ee/native/CONTRATO-NATIVE48.md`, `Common48.ps1`, `Initialize48.ps1`, `Operator48.ps1`, `Runtime48.ps1`, `prepare.py` y `Exercise48.ps1`. Sólo lectura: no ejecución propia de esos scripts ni contacto con E. Se contrastaron también `development/windows-service/Program.cs` (ServiceConfig.Load/CheckPath/CheckCode), `WindowsMfaMaintenanceService.RequireStopped/HoldPhysicalFile`, `MfaMaintenanceCoordinator.RequireRootAuthority`, `MfaBackupCatalog.Open`, `SqlSecretConnection`, lector Windows, CLI init, NativeShutdown y constraints SQL002/016/017 pertinentes.

La propuesta fija UUID/hostname de E, instalaciónUUID nueva y recursos explícitos; rechaza colisiones antes de mutar, prepara cuentas estándar/servicios propios Manual, owner/runtime PG separados, proveedor MFA/SQL habilitados y TLS sin importar raíz global. La copia/ensamblador host no opera la VM. El token de shutdown va por canal privado; runtime conserva pines de todos los archivos de código. Estos son controles inspeccionados, no ejecución nativa acreditada.

**Gate todavía no favorable a Provision; bloqueos operativos comunicados:**

- **P1 operativo, ACL de binding SCM:** `service-config.json` se sella ownerSYSTEM, Allow sóloSYSTEM+reader. El shim exige esa ACL, pero `WindowsMfaMaintenanceService.HoldPhysicalFile` usa FileStream con FileAccess.Read desde el operador Admin elevado, sin ACE de lectura ni activación de privilegio de backup. CatalogInitialize y loss fallarían al retener el config. Añadir Administradores a ese archivo contradice `ServiceConfig.CheckPath`; la resolución debe preservar su contrato y atribuir la autoridad realmente ensayada.
- **P1 operativo, lectura de raíz de catálogo:** Initialize crea `runtime/backups` sóloSYSTEM+readerFA. El operador Admin debe leer su descriptor y enumerarla mediante RequireRootAuthority/Open; esos derechos no están concedidos al operador. El catálogo admite Administradores como autoridad, por lo que su ACL puede prepararse expresamente sin abrir el archivo privado de factores.
- **P2 operativo, observación del arranque fallido:** Exercise/FailedStart enumera y lee `runtime/logs` desde Admin; la carpeta es sóloSYSTEM+readerFA y `ServiceConfig.CheckPath` tampoco permite añadir Administradores ahí. Usar lectura privilegiada acotada o identidad autorizada, manteniendo el contrato del shim.
- **P2 de evidencia:** Recovered reutiliza realmente la sesión vieja y comprueba conteos SQL, pero todavía no usa el verifyChallenge/código viejo que Baseline guarda. No presentar esas dos credenciales como rechazadas por HTTP hasta ejecutar solicitudes discriminantes sin sesión emitida. La evidencia backend F0903 puede citarse con su alcance original.

No se identificó una operación de borrado amplio, control de energía VM o actualización de D/instalaciones históricas en estos scripts. Timeout conserva resultado inconcluso y prohíbe retry; queda necesaria observación explícita del proceso propio antes de continuar. Fuentes/binarios nativos definitivos, staging autenticado, correcciones de ACL y resultados reales siguen pendientes; esta lectura no acredita F0904 ni el gate nativo.

## Repetición propia definitiva de componentes · review48-01

Entrega `.local/f0904-793425ee/review48-01`, manifiesto PINS SHA256 `16e57ef88178b5b0cf01eb507f979f85514c634b5d98df7a1169cb0936641161`. Se verificaron **514fuentes y577archivos binarios**, tanto en la entrega como en la copia propia, antes y después de ejecutar. Ninguno cambió. Copia propia `.local/f0904-review-final-d0520bb4/s`.

| Artefacto | SHA256 |
|---|---|
| Server y copia cargada desde directorio de tests | `d9366dbe9be377d4147417fd8c51e40aaa302b82c8d3bd9b830c67d68980b909` |
| Tests | `f15ec85332b379819c6a6462ab24a20dab7bfe45409f56e354fd6e7463c7e829` |

Comparación propia con FUENTES de F0903:221/232archivos de producto idénticos,11modificados y ninguno ausente. Los cambios son coordinator/database loss, parciales Loss/Store, guard de rotación, writer, Program, SchemaMigrations, compatibilidad de coordinadores mantenimiento/rotación y comentario del helper de autoridad. Cuatro nuevos: migración048, MfaLossRecoveryCommand, MfaLossStartupGuard y WindowsMfaMaintenanceStore.LossStartup. De las diez pruebas previas focales F0903, sólo MfaLossResetTests cambia para fijar explícitamente el escenario histórico47; se conserva su aserción47. MfaWindowsHostHttpTests usa ahora migraciones reales con su historial actual: no se relajó el rechazo del guard para aceptar historia vacía. SQL001–047 y dependencias previas del manifiesto permanecen iguales.

Comando ejecutado directamente, sin MSBuild/build/restore:

```text
dotnet vstest <copia propia>/tests/RackClick.Quality.Tests/bin/Release/net10.0/RackClick.Quality.Tests.dll
  /TestCaseFilter:FullyQualifiedName~MfaLossStartupTests|FullyQualifiedName~MfaLossRecoveryCommandTests
  /Logger:trx;LogFileName=<privado>/independent.trx
  /ResultsDirectory:<privado>/results
```

Driver propio `.local/f0904-review-final-run.py`. Windows, dotnet fijado SDK10.0.401/VSTest18.7, PostgreSQL17.11 nativo nuevo, owner/runtime separados, DPAPI/ACL reales con SID/trust de fixture; no cuenta efectiva de un servicio instalado. Entrada de PG sólo mediante variables privadas explícitas, sin fallback a una instancia existente. Se limpiaron variables heredadas RACKCLICK_/PG; diagnósticos de runtime deshabilitados.

**40ejecutadas/40PASS/0FAIL/0omitidas, exit0:**17casos de MfaLossStartupTests y23de MfaLossRecoveryCommandTests. Duración comunicada por VSTest43s. La repetición acredita:

- Pérdida de ambos archivos de claves1/7 con anillo fiable, factores active/pending retirados y pending conservado: publicación continúa fenced; Complete explícito retira fence y runtime guard acepta. Originales físicamente ausentes no se recrean. Reentrada de Complete y guard sin duplicar transición.
- Cuatro interrupciones lógicas antes/después del recibo y antes/después de liberar fence, con reentrada por UUID y objetos propios. Son excepciones de checkpoint, no Kill/reboot/apagón.
- Modos rotate→loss y loss→rotate: material de la operación más reciente, ambos historiales conservados; recibo loss alterado sigue rechazándose después de rotación. Recibo/witness/key alterados bloquean.
- Proyección metadata de19campos: SELECT runtime permitido, UPDATE/DELETE rechazados55000 incluso ante grant público amplio; SELECT del archivo cifrado rechazado42501. Complete rechaza vista ausente o SELECT runtime revocado **antes de retirar fence**. Se comprueba también historia vacía con error constante; actividad de enrolamiento posterior no invalida una pérdida ya completada.
- Layout nativo SCM separado de securityRoot; writer/mantenimiento sobre rutas profundas conservan ACL y lectura de identidad.
- Parser de cinco fases sin abrir SQL/archivos/servicio; rechaza duplicados, campos/case/confirmación/rutas/Unicode inválidos, tamaño, lector/custodio reservado, UUID cero, listas y hash inválidos. Sobre no solapa SCMroot/backup roots, incluidos sus ancestros. Token Windows estándar observado rechaza sin leer stdin ni usar configuración como autoridad.

**Hallazgo P2 de proyección cerrado dentro de este foco:** los negativos propios de vista/permisos y sus fences intactos pasan sobre los binarios fijados. No se ejecutó rojo/mutación por el revisor. Los378/378 finales y rojos/fixtures del coordinador fueron leídos como evidencia ajena, no se atribuyen como repetición propia ni como suite completa del revisor.

Salida privada `.local/f0904-review-final-d0520bb4/independent-sanitized.json`, SHA256 `44321c7c6be49a1253760b9435dd8defe42997d17c17b6b55eafd721649d2e3f`; TRX SHA256 `08fccb7d59ccf87ccd4c272fbbf64abbe52f60fd580f980afcea4aea305dca83`. No hay binlog porque `dotnet vstest` directo no invoca MSBuild. Clúster propio `.local/labs/f0904-review-final-03df9885aca64a83a8e976ade560161c` detenido y sin postmaster.pid; fixtures privados conservados. La incidencia de pins mutable anterior no se convirtió en una corrida ni se oculta.

## Límites vigentes y recomendación parcial

Favorable sólo a la composición técnica de arranque/recibo/finalización/parser repetida sobre review48-01. **F0904 no es elegible a done por estos40casos solos:** faltan autoridad positiva nativa/SYSTEM, SID efectivo, CLI operativa sobre servicio vinculado, publicación/host/HTTPS reales y recuperación administrativa del host perdido. El harness nativo corregido con lanzador SYSTEM aún no fue inspeccionado/ejecutado por el revisor. No se ensayaron custodia física externa, corte de alimentación/reinicio, namespace nuevo sin censo fiable, instalación/Restore48 ni adopción/QA de Wascar.

Observación de compatibilidad comunicada, estática y fuera de los40: el recibo loss fija el ring completo. Una retirada F06 posterior de una versión retenida, sin nueva rotación, podría dejar el ring distinto del recibo loss y hacer fallar el arranque cerrado. La compatibilidad de rotación posterior sí se repitió; no se declara ensayada la retirada posterior a loss. No se ha abierto otra implementación por esta observación.

Sin cambios D/E ni porcentaje global nuevo. Índice recibido26,13/100 del cierre restante, sin crédito propio. F0904/.05 y hitos operativos/aceptación mantienen su estado hasta conciliación con evidencia nativa suficiente.

## Gate concreta Stage/Provision · scripts SYSTEM revisados

**Favorable a efectuar el primer Stage y Provision del harness privado revisado**, sujeto al contraste de los pins definitivos de scripts/plan/archivo contra los bytes preparados. No es aprobación de cierre F0904 ni afirmación de que Provision ya funciona. El revisor no ejecutó E. Se releen RunSystem48/SystemJob48 completos, ajustes Common/Operator y drive/Exercise; se compara Server publicado con d9366d… de la entrega repetida.

Los bloqueos ACL anteriores quedan resueltos **para este ensayo SYSTEM**: Provision se ejecuta como Admin elevado, con inicialización bajo la cuenta estándar nueva y grupo Users; se sella el padre instance para impedir DELETE_CHILD sobre peers inmutables. Backup root permite BA por contrato del catálogo. Mantenimiento/observación posteriores se ejecutan comoSYSTEM, que lee config/logs sin cambiar sus ACL estrictas. Sigue pendiente el positivo operativo de mantenimiento desde Admin; no se acredita por el ensayoSYSTEM.

RunSystem48 limita kind/fase y vincula VM/instalación/SCM, scripts/plan/job/petición mediante hashes y handles de sólo lectura. Crea una única tarea con nombreUUID propio, principalSYSTEM/logonServiceAccount, DACLBA/SY, sin triggers/restart y comando exacto. Contrasta definiciónXML completa normalizada y settings efectivos antes/durante ejecución. SystemJob vuelve a comprobar SID18, ámbito, pins, permisos y fase permitida; hijo y salida se ligan aUUID/requestHash y exit real. PT0S evita terminación de Scheduler por límite; el launcher espera540s y conserva task/proceso incierto, sin retry. Sólo retira tarea propia si está idle/sin instancias y conserva el fingerprint; no borra ni altera tareas ajenas.

**Corrección de staging contrastada estáticamente:** inicialmente drive copiaba plan.json y después extraía un ZIP que también lo contenía, con colisión sinForce. Tras comunicarlo, usa plan.expected.json pineado, extrae a destino nuevo sinForce y valida plan.json extraído con el mismo hash. No se ejecutó el intento defectuoso en E según el coordinador.

**Prueba propia adicional:** copia privada `.local/f0904-review-system-check-01` de RunSystem48 y Check-System48-Local; ejecución local con WindowsPowerShell5.1:16/16 PASS, exit0,0mutaciones de tareas y0contactoVM. Crea definiciones Scheduler sólo en memoria y consulta un nombre nuevo ausente. Comprueba equivalencias permitidas de defaults/SYSTEM y rechazos de identity/logon/policy/argumentos/trigger/timeout/duplicados/booleanos; cambios de settings adicionales alteran el fingerprint. Hash del launcher copiado `82e93ca8036002a4cd9d6e7ab85ca16d909c945a7b0537062e2931e5c060d396`; resultado local SHA256 `02f87fe2df28158a8d251ae9f3f13e2b90120fe7954230fcbbf109efdb1ba37d`. No es un positivo real de tareaSYSTEM.

Exercise ahora usa un código viejo con verifyChallenge/CSRF viejo en /recover y requiere rechazo sin Session; además hace una petición /verify con código inválido sobre el desafío viejo, separada de los conteosSQL. Esta última no prueba rechazo de un TOTP viejo válido; describirla como petición sobre desafío viejo. ConfirmaciónTOTP/nueva sesión/CSRF e inventario permanecen condicionados a ejecución real.

Se recomienda continuar sólo con Stage/Provision exclusivos y sus recibos, verificar que ambos servicios propios quedan parados y conservar cualquier fallo parcial para conciliación. No eleva los40casos de componentes ni los16XML a evidencia de SCM/HTTPS/recuperación nativa; F0904 sigue pendiente hasta ese resultado y su revisión.

**Sello final de helpers contrastado:** `native/review-scripts-pins.json` SHA256 `d37f067c7fd671973f95f60f40f5463019fe5b74705556c4fb5d911777acadf7`,13/13archivos coincidentes en comprobación propia. RunSystem final `a4e2295def412f272b636288a40e70257aa432c35cd1c6e1971b1acbd56b8f39`; SystemJob `b2067c6c2e06b5b961e9ffa4aacdfe924e13b6439716d9ce9478ffe4d639af43`. El único delta RunSystem frente a la copia XML propia82e93 añade paréntesis a dos rutas permitidas del autovínculo; las funciones XML repetidas no cambian. Otros deltas finales inspeccionados: diagnósticos privados type/line/HResult sin texto de excepción, carpetas admitidas antes de escribirlos y agrupación correcta de tres rutas TLS en el array de PowerShell. Drive controla padreW02 por owner/DACL/reparse sin cambiar ACL ajena y mantiene plan.expected/extraer sinForce/pin extraído. Se mantiene gate favorable limitado a Stage/Provision, con archivo/plan final autenticados; ningún resultado nativo se presupone. Recibo de contraste propio `.local/f0904-review-native-seal.json` conserva también hashes de Exercise/drive, excluidos expresamente del manifiesto del worker.

**Vínculo propio del paquete final:** plan SHA256 `71a23a87ef455321297e05acbd32888317c835842a8ceba94f59e0060ea38d3c`, ZIP SHA256 `4d84d91c1d958e95d37651091510a97de38ee55eb56639093e9de768f238f018`. Se leyeron sus2014entradas únicas:2013archivos coinciden por bytes/hash con el plan y plan.json embebido coincide con el pin externo. Los seis helpers del worker incluidos en payload coinciden con el manifiesto final d37f…; SetupSecurity/SqlSecrets tienen sus propios hashes en el plan. No se extrajo ni ejecutó en E por el revisor. El ensamblado anterior con helpers desfasados permanece como prepared-unexecuted01 según el coordinador; no es el paquete revisado ni una ejecución nativa.

**STOP94 de Stage, atribución del coordinador:** primer staging se detuvo porque C:\W02 no existía; no se creó el stage ni cuentas/servicios/DB. Revisión estática de driver variante02 SHA256 `832559b3bf4e30f0f6eee09eb07dcae5b693da6e53a13372b37c0126081d2e53`: permite crear sólo ese padre ausente con DACL privada desde creación, valida inmediatamente owner/writes/reparse y conserva el rechazo de un padre existente inseguro sin cambiar su ACL. Nuevos recibos de intento porUUID. Gate mantenida para repetición manual acotada de Stage con causa identificada; no se atribuye como retry automático ni como resultado favorable de Provision.

## Provision nativo interrumpido y gate StopOnly02

El coordinador informa Provision01 inconcluso por EOF de pipes heredados tras pg_ctl: initdb exit0, pg_ctl ya terminado sin recibo de salida, PostgreSQL propio57484 activo e inicializador estándar4276 vivo, sin JSONstate final. No es un PASS ni un defecto de MFA demostrado. El revisor no ejecutó ni observó directamente E; conserva la atribución al coordinador. Fuentes/bins de producto d9366d… no cambian. Harness02/Resume y archivo de datos todavía no están aprobados por esta revisión.

**Gate favorable exclusiva a Check y Stop condicionado al proof** de `native/p02/StopOwnedPg02.ps1` SHA256 `d6439dae256f4301ba1896e74717317efaf7f6284c70a5286870270e02e2fd02`, leído completo. Check no muta: vincula VM/hostname, id/rutas/plan exactos, token estándar del reader, hashes de postgres/pg_ctl/Initialize, recibos initdb/start antes del primer SQL, inicializador porPID/SID/EXE/cmdline y PG porPID/SID/EXE/starttime/datadir/port/listener. Stop reobserva todo y exige igualdad de cada campo frente a la pruebaCheck con hash fijado. Sólo ejecuta pg_ctl -D<datadirpropio> -mfast -w -t40 stop, sinKill; espera proceso/EOF con límites50s+5s y comprueba ausencia de postmaster.pid y puerto libre. Resultados inciertos se conservan sinretry.

El proof de metadata debe estar legible por la cuentaSTD en una ruta controlada. Stop sólo declara parada de PG; **no autoriza archivar ni reanudar**. Antes de un archivo posterior debe probarse salida del inicializador estándar y reconfirmar recibos/ausencia de DB/roles app/claves/config/SCM después de desbloquear EOF: el inicializador podría continuar al siguiente paso SQL. Un clúster recién inicializado tiene sus catálogosPG; no describirlo como carpeta vacía ni inferir ausencia de app exclusivamente de una observación anterior. Stage/Provision fallidos, Check/Stop y un futuro Resume son resultados separados. F0904 sigue sin cierre técnico operativo ni crédito adicional.

**Check02 rechazado, según coordinador:** `stop02_not_before_first_sql`, sin mutaciones. La observación actual encontró cuatro recibos: initdb0, pg_ctl start0, psql y pg_ctl cleanup con exit-1073741502/0xC0000142. El historial inicial de dos recibos había cambiado; no se debilitó la guarda anterior ni se convirtió el rechazo en PASS. Ausencia de SQLapp aún no acreditada por catálogo.

**Gate favorable sólo Check/Stop de revisión02B:** fuente completa y SHA256 `163a4a4550d29efcf8a1dc555d0b3ac88995cff4a46984f1f538b660442bf32e` contrastados. Admite exclusivamente el historial medido de cuatro recibos y sus exits/hashes, conserva targetPG propio/VM/id/SID/PID/EXE/data/port/start/pins y compara de nuevo toda observación contra proof fijado. Si el inicializador anterior sigue visible, exige EXE/SID/cmdline/start; si terminó, lo declara. Usa `beforeFirstSql=false,sqlCatalogNotYetVerified=true`, sin afirmar vacío de datos. Mantiene paradafast sinKill, timeouts y ausencia de retry. No modifica producto ni autoriza archivo/Resume; OldInitEXIT y catálogo offline son gates posteriores. No ejecución propia de E por el revisor.

## Gate Check de catálogo parado · p02

Fuente completa/hash de `ReadStoppedCatalog02.ps1` (`04d6108660f29779c1c357d70a1cb5e648cf8bea926e03670645522d407545cf`) y `Common02.ps1` (`0de294179d27f28ce3ce0fd0571119b0a5a637758efbb013b1cffa4a4cdaae5d`) contrastados. **No se encontró bloqueante concreto de Check; gate favorable exclusiva a esa fase. Archive sigue pendiente del Check real y su proof.**

Request cerrado/pineado, ámbito E/id/plan/readerSTD y parentProvision exit1; requiere OldInit/PID/puerto/procesosPGpropios/SCMpropios ausentes, cuatro recibos exactos y DACL privada. ControlData pineado debe indicar shut down y systemIdentifier estable. Single-user PostgreSQL ejecuta SELECT constante con default_transaction_read_only=on; rechaza DB/roles rc_* o tablas de aplicación previstas y exige un único marcador en framing cerrado. Reconfirma parada/identidad tras salir. InvokeOneShot02 registra salida del proceso antes de drenar stdout/stderr, acota ambos con deadline y conserva inconclusos, sinKill/retry.

Precisar el alcance de sólo lectura: lo es la consultaSQL; Check crea diagnósticos privados y el arranque/cierre single-user puede actualizar pg_control/estado interno del clúster. No es inspección inmutable por bytes ni prueba de ausencia universal de datos fuera del catálogo consultado. La migración/bootstrapping de la aplicación permanecen sin ejecutar por esta fase.

Diseño Archive inspeccionado: vuelve a comprobar todas las precondiciones y proof pin/historia/control, repite consulta, exige origen/target hijos exactos de la única instancia, destino ausente, Move sin borrado y conserva hashes control/PG_VERSION tras mover. **No se concede todavía su ejecución ni Resume**: se revisará primero el resultado real Check. Sin contacto E ni ejecución offline por el revisor.

**Resultado real Check, atribuido al coordinador:** rechazado con catalog02_not_clean_shutdown en ControlData antes del SELECT single-user; referencia privada std02-3d0ea809. No se acredita catálogo vacío ni se informa como PASS. El coordinador propone preservar íntegro el intento propio no adoptado bajo destino nuevo pgdata-attempt01-preserved, con catálogo unknown/estado unclean explícitos, sinSQL/pg_resetwal, eliminación ni declaración de vacío.

El revisor acepta ese replanteo como diseño de conservación: **no hace falta demostrar catálogo vacío para preservar sin descartar bytes una carpeta propia exacta**. La condición de catálogo sólo respaldaba la premisa anterior de reutilización/recreación con estado conocido. La nueva fuente debe fijar VM/id/plan/SID/rutas/DACL, PG17, ausencia de procesos/Init/puerto/servicios propios, destino exclusivo y hashes antes/después del Move dentro del mismo padre. La gate ejecutable de esa conservación queda pendiente de leer la fuente final; no se exige reparar catálogos para conservarlos. No autoriza aún Resume ni modifica la evaluación de los componentes de producto.

**Fuente de conservación revisada y gate concedida:** `ArchiveOwnAttempt02.ps1` SHA256 `a3f3299455917437b3a69e3b0c743ace24b318254c8895f4e2baacec392584db`, completa y coincidente. Favorable a Check y, sólo si Check real pasa y se fija su proof sin cambios, Archive exclusivo de ese intento. No se ejecuta SQL, postgres, stop/start ni reparación. Recaptura VM/id/plan/parentFailure, STD/SID, rutas y DACL privadas, PG17/control8192 y ausencia de Init/PID/PG/puerto/SCM; proof liga hashes, ACL/fecha de directorio, fuente/Common/parent/plan. Antes del Move reobserva; exige origen/target absolutos exactos bajo mismo padre y destino ausente. Tras Move verifica origen ausente, target privado y hashes control/PG_VERSION conservados. Declara sqlCatalogVerified=false/uncleanPreserved=true; no se acredita vacío, recuperabilidad ni Resume. El revisor no opera E.

## Revisión de reanudación P02 · 11.11.2026

Se retoma la revisión en nueva sesión; no se heredan procesos/herramientas en ejecución. Se releen AGENTS/BRIEFING, estado privado, dictamen previo, Common02, InitializeResume02, OperatorFinish02, tracker y gate reutilizados, Common48/Operator48 y el recibo real de Archive comunicado por el coordinador. La conservación consta como archived=true, uncleanPreserved=true, sqlCatalogVerified=false, stopPerformed=false: **no se convierte en prueba de catálogo vacío ni de recuperabilidad**.

**Gate favorable y acotada a la reanudación de esta instancia propia en E**, bajo los pines siguientes y las precondiciones actuales que debe volver a observar el coordinador. No autoriza repetir Provision01, Archive, consulta single-user ni reparar el clúster preservado. No autoriza operar D, instalaciones anteriores ni VM power/snapshots.

- InitializeResume02.ps1: `45061bd130ff41fa9fb52ece2c6b2339f73e87c725b69aab2698a76677133eac`.
- OperatorFinish02.ps1: `f3b9153a1e6db5f4db1ec1c9930c433f0f4528a6aef80f5d4fa04f29c3a90e10`.
- Manifiesto p02-pins.json: `e084ebe75648e758fdc17c2a9a7e29a0f59379c1b56219d544bd637c0a2513a1`.
- Common02 y tracker/gate se conservan byte a byte conforme a ese manifiesto.

El inicializador valida request/plan/fuentes, binding E/instalación/cuenta estándar y hash del recibo real de archivado. Requiere antiguo proceso/puerto/servicios ausentes, destino pgdata nuevo y fases posteriores ausentes; preserva íntegro pgdata-attempt01-preserved y no lo abre para SQL. Genera credenciales nuevas y checkpoint DPAPI CurrentUser privado antes del daemon. PostgreSQL directo pertenece a un OwnedJob; espera readiness vinculado y detiene sólo el PG propio tras bootstrap48 y grants runtime. OneShot02 registra exit antes de EOF y acota ambas esperas, evitando el patrón pg_ctl start/pipe heredado del intento anterior. Se revisaron las variables empleadas tras StrictModeLatest: no se halló una variable sin inicializar concreta por inspección.

Finish sólo ejecuta la parte posterior a inicialización. Exige recibo final exacto y hash, cleanStop declarado, nombres de DB/roles internos, identidad/cuenta y credential vinculadas; rechaza servicios/fases posteriores existentes y puertos/PID propios vivos. Retira la propiedad y lectura del servicio sobre el checkpoint (propietario SYSTEM; ACL SYSTEM/Administradores) **antes** de persistir state y registrar SCM. No crea cuentas, no copia payload y no inicializa otro clúster. Sella código/SQL/profile/TLS por el helper privilegiado aprobado; conserva runtime/logs/pgdata y el intento archivado sin enumeración recursiva. Registra exclusivamente los dos servicios propios Manual/Stopped y comprueba binding. El hash del profile viene del recibo del inicializador estándar pineado: no se presenta como relectura Admin, que no tiene derecho de lectura en su descriptor final.

**Ejecutado por el revisor aquí:** contraste SHA256 de las cinco fuentes del manifiesto y parser Windows PowerShell 5.1 (5.1.26100.9711), cero errores de sintaxis; salida propia privada `review-resume/parser-pins-own.json`. Lectura estática de fuentes y recibo archivado. No hubo restore/build/tests de producto nuevos, ni E/VM, cuentas/servicios/SQL o comprobaciones DPAPI propias; la regresión anterior 40/40 se conserva con su atribución y no se repite como resultado nuevo.

**Límites de la gate:** las condiciones reales actuales de E se atribuyen al coordinador, quien informa ambas instalaciones previas Running, propios ausentes, puertos libres y pgdata nuevo todavía ausente. El parent deberá esperar suficientemente al inicializador (el coordinador propone 600s), sin Kill/retry automático. En cierre PG indeterminado StopOwnDirect02 conserva deliberadamente el job y espera: **no se afirma acotación universal de ese camino**. Los catch/recibos y las credenciales son privados, sin transcribirlos aquí. La prueba nativa funcional aún no se ha ejecutado en esta revisión. F-09.04 sigue sin cerrar hasta pérdida, guard real, CLI, retorno HTTPS/enrolamiento/TOTP nuevo y revisión de sus recibos. F-09.05 y adopción siguen pendientes.

### Resultado real de InitializeResume02 y replanteo P03

El coordinador ejecutó el inicializador P02 bajo la cuenta estándar y obtuvo exit1. Su diagnóstico de sólo metadatos, leído por este revisor, registra initdb0, pg_isready0 y el primer psql0; la parada propia registra pg_ctl0, cleanStop=true, ownedJobExited=true y forcedKill=false. El error es PropertyNotFoundException en la lectura `.stdout` de InvokeOneShot02. No se infiere ausencia de SQL: **la creación de los dos roles sí terminó con0**. El clúster nuevo se conserva parado; no se concede repetir initdb, Archive o CREATE ROLE por esta observación.

El coordinador reprodujo localmente que PowerShell5.1 emite dos VoidTaskResult por las llamadas GetAwaiter().GetResult() de CopyToAsync, además del Hashtable de retorno: `.stdout` sobre ese conjunto falla con StrictMode. La inspección previa de variables no ejecutó este camino ni lo detectó; la gate estática anterior no equivale a prueba semántica. Es un defecto del harness privado, sin cambio ni atribución a la DLL de producto48. Fuentes y recibos anteriores se conservan.

Se prepara Common03 separado y continuación P03 del mismo clúster con checkpoint DPAPI propio, comprobación de los dos roles y ausencia de base app antes de continuar. **Gate P03 pendiente de fuente/pines y foco ejecutable**, sin autorización de reintento del inicializador anterior.

### Revisión P03 · continuación del clúster propio limpio

**Gate favorable acotada a CompleteInitialization03 y, exclusivamente tras su recibo final0/hash nuevo, Finish02 ya revisado.** Se contrastaron las fuentes completas y el manifiesto:

- Common03.ps1: `5b8828eb2019f23bb65bfaf4312119653653d4513ac8fedf227cb0246950ab9b`.
- CompleteInitialization03.ps1: `a9e84e68d68b282a2b2bebb8bb3ddfc7f2013a922e5ceda0a830f22fc42b2b56`.
- p03-pins.json: `68150ecc17f1fa13647e34535d3c076e941f1d9836ca13a09cb7c6db11a748f6`.

Request cerrado de11campos liga checkpoint/control/stop/archivo/plan/fuentes, con E y cuenta estándar propias. Exige hash de pg_control, PG17, PID ausente, recibo de parada propio, puertos/servicios/fases posteriores ausentes y metadatos archivados conservados. Lee únicamente el checkpoint DPAPI de este intento y valida formato/identidad de sus cinco secretos antes de usarlos; no genera contraseñas de sustitución. Comprueba controldata shut down antes del arranque PGdirecto controlado. Antes de la primera mutación SQL exige exactamente las tres DB de sistema, los dos roles previstos con login y sin privilegios superiores, cero memberships y autenticación con ambas contraseñas del checkpoint. Sólo entonces crea la DB propia y continúa bootstrap/grants/SQLsecret/TLS/profile. No ejecuta initdb ni CREATE ROLE, ni toca el intento archivado. La parada final exige gateExit0 y controldata shut down, además de PID ausente, antes de informar cleanStop.

**Foco propio ejecutado con Windows PowerShell5.1.26100.9711:** child ComSpec exit0 en Common02 emite3objetos (dos VoidTaskResult y un Hashtable); Common03 emite únicamente un Hashtable. Child exit7 es rechazado por su código y conserva los recibos de salida0/7. Las cinco fuentes del manifiesto coinciden por SHA256 y pasan parser sin errores. Resultado propio `review-resume/p03-own-*/result.json`, pass=true,0operacionesVM/0ejecucionesproducto/0PostgreSQL. No se recompiló ni se repitió la suite de servidor.

No se halló un bloqueante concreto nuevo en esta continuación acotada. Se mantienen los límites de timeout con conservación deliberada del job, identidad/custodia de laboratorio y fuente48 no instalable por el paquete histórico. El resultado0 eventual de P03 no cambia retroactivamente el exit1 de P02: el recibo debe conservar completedP03=true y rolesRecreated=false/clusterRecreated=false. F0904 sigue pendiente de pérdida/guard/CLI/HTTPS/TOTP real y revisión final de recibos nativos. El revisor no ha operado E.

### P03 rechazado antes de SQL; revisión del delta P04

La ejecución real P03 del coordinador salió1 durante readiness (`ReadAllLines(postmaster.pid)`, MethodInvocationException). El diagnóstico privado de metadatos leído por el revisor registra únicamente controldata0, cleanup pg_ctl0 y controldata posterior0, con cleanStop=true; no registra psql ni pg_isready para esa fase. El innererror original no se capturó: **no queda probado que su causa fuera exactamente sharing32**. El clúster y los dos roles de P02 se conservan, sin volver a ejecutar creación/archivado.

Revisado el delta completo03→04: request schema4/p04pin y recibo de parada actualizado a P03, prefijos/etiquetas propios, ReadPid04 y diagnóstico innerHResult. Common03, manifiesto P03 y Finish02 permanecen intactos; P04 exige también el manifiesto P03 aceptado y fija sus fuentes nuevas en el manifiesto04. Catálogo/checkpoint/SCM/SQL/stop/grants no relajan sus compuertas.

**Gate favorable acotada a CompleteInitialization04 una vez y sólo tras exit0/recibo nuevo a Finish02.** Fuentes:

- CompleteInitialization04.ps1: `f95d493d6f6ab932ce1d682f0085c125c030e80b2246fddbfe26faf6ef1d1ca2`.
- p04-pins.json: `5c72afd06eea0fb70cf30e7845ad5c435df9b9fb48215cb9f36d80bb410e4a2e`.

ReadPid04 abre para lectura con FileShare.ReadWrite|Delete; sólo inner IOException con código2/32/33 permite otra observación dentro del poll readiness de40s. Conserva binding PID/job/puerto/ready y pg_isready. Retiene como máximo32detalles de transitorios y conserva previousOuterExceptionCause=unmeasured. Otros errores se propagan; no hay retry de SQL/creación/wholephase ni de producto.

**Ejecutado por este revisor en host privado, PowerShell5.1.26100.9711:** función exacta extraída por AST, sin ejecutar el script completo de E. ReadAllLines previo falla con un writer abierto; la función nueva lee el mismo archivo. Ausencia2 y bloqueo exclusivo32 devuelven observación vacía; archivo8193bytes rechaza. Pines de las cinco fuentes coinciden y parser0errores. Resultado `review-resume/p04-own-*/result.json`, pass=true,0VM/0producto/0PG. El33 y el caso ACL del worker no se atribuyen como ejecuciones propias. F0904 sigue pendiente del ensayo funcional final y sus recibos; ninguna gate estática anterior se reetiqueta como éxito real.

### Inicialización04/Finish02 y launcher SYSTEM49

El coordinador informa Complete04exit0 y Finish02exit0, con dos servicios propios Stopped. No se reetiquetan los intentos anteriores. CatalogInitialize mediante launcher48 falló antes de registrar/arrancar tarea o ejecutar el hijo; no hay por ese intento catálogo inicializado ni app arrancada. Su diagnóstico TASK_VALIDATE_ONLY (flag1) mide las tres variantes SID/SDDL/nombre SYSTEM con el mismo0x80041319 (missing node). Ese resultado no demuestra una causa en contraseña o SDDL. Al añadir sólo Actions.Context=SystemPhase a la definición, un segundo diagnóstico del coordinador registra validated=true/flags1/0tasksRegistered/0tasksRun/0SQL/0keys; XML fijado332d331105f5a158a77166aca832b60653b82fad87ca4c29d00a1d80d78d7159. El revisor leyó este último resultado, sin ejecutarlo.

Leído el delta completo RunSystem48→RunSystem49: selfpin externo obligatorio y ruta exclusiva codeRoot/harness/p02/RunSystem49.ps1, verificación adicional del launcher48 original contra el manifiesto histórico; contexto explícito SystemPhase de la acción; cadena acotada de HRESULT en diagnóstico privado, sin mensajes/secretos. Permanecen las compuertas Kind/fase/VM/plan/SCM/target/Common/Job, archivos retenidos, ACL/XML efectivos antes/durante/después, tareas exclusivas, ausencia de trigger/retry, conservación por timeout y limpieza sólo propia idle.

**Gate favorable acotada a CatalogInitialize mediante RunSystem49** SHA256 `b21eb47524fb4e477b45584681253ef76ba17f89c96efe9b83efb0b4b661e1a6`, con su pin externo y plan/prepared/profile48 sin reescribir. Es un auxiliar nuevo; no se presenta como si el manifiesto48 histórico contuviera ese hash. La asignación de Actions.Context corresponde al Principal.Id ya fijado; no se elimina ValidateOnly ni se relajan sus rechazos. El coordinador conserva la fallida fase48 y obtiene un recibo49 nuevo.

**Ejecutado por el revisor:** hash del archivo49 y parser PS5.1.26100.9711 sin errores (`review-resume/launcher49-parser-pin.json`), lectura estática de delta y diagnóstico. Cero operaciones VM, registros/Run de tareas, SQL o producto propias. Los diagnósticos ValidateOnly usan la API RegisterTaskDefinition con flag1 (validación sintáctica sin registro), y sí escriben XML privados nuevos; no son inspección inmutable por bytes. F0904 continúa pendiente del recorrido nativo completo y su revisión final; F0905/adopción sin crédito.

### Baseline HTTP y cliente de ensayo TLS1.2

CatalogInitialize49 y StartApp49 pasan según los recibos del coordinador; el listener propio está presente. La primera fase Baseline devuelve child1. La línea52 corresponde al helper Http48 compartido: por sí sola no identificaba la petición ni probaba0SQL. El coordinador contrastó después el intervalo de esa fase con sus metadatos de procesos: cero child-start de psql y sin http-state/baseline publicados. La fuente ejecuta su primer seed SQL antes del login; con ese contraste se conserva el intento fallido y se permite una nueva Baseline sin duplicar ese seed. No se reconstruye ningún recibo anterior.

El diagnóstico GET del coordinador, bajo Administrador explícito, mide SecurityProtocol0 con callback/pin verdaderos y Timeout; al fijar TLS1.2(3072) devuelve HTTP200, callback/pin verdaderos y sólo error de cadena4 admitido por el pin. El protocolo original se restaura. No se leyó cuerpo ni se enviaron cookies/credenciales. **No es una medición ejecutada bajo SYSTEM ni demuestra por sí sola la causa universal del timeout anterior.**

**Gate favorable acotada a la variante del cliente Exercise48** SHA256 `cfbb1318628b2c75e4e5d4c3317598b883178c3cadeaa460de0fd7057be6919f`: contraste propio contra el original7598cbad5fb04383294d09d77b3a2af051b9aa6d43a853520f19b9395a83cc56 preservado en exercise-reference-01 muestra exactamente dos líneas añadidas (comentario y ServicePointManager.SecurityProtocol=Tls12). Parser PS5.1 propio0errores. Los controles de pin DER/nombre y las solicitudes/aserciones no cambian. Se fija sólo el proceso cliente del fixture; no Windows, servidor, TLS de otros procesos o confianza global.

Exercise está fuera de las ocho entradas harness del plan48, que el revisor comprobó; launcher49 recibe el nuevo hash externo y mantiene su comprobación de propietario/ACL/archivos retenidos. No se reescriben plan/profile/Job/binarios para fingir que el hash antiguo sigue vigente. La Baseline nueva y las fases posteriores necesitan recibos propios; F0904 aún no se acredita. El revisor no ha operado E ni ejecutado HTTP nativo.

### Separación de autoridad del cliente HTTP y diagnóstico Ready

La repetición Baseline bajo SYSTEM con el clienteTLS1.2 también falló. El coordinador volvió a contrastar cero metadatos de procesos SQL y ninguna publicación http-state/baseline; se conserva como fallo, sin declarar HTTP SYSTEM válido. F0904 exige servicio real con cuenta estándar y mantenimiento Windows autorizado, pero no exige que el cliente HTTP sea SYSTEM. Se acepta separar cliente Administrador de Windows de mantenimiento SYSTEM: el usuario de RackClick sigue obteniendo sesión exclusivamente por contraseña/desafío/TOTP mediante API real.

Leído el delta de Exercise `1090cdd0553f0e9be26c1f4b45bdd1a21d4926252e226e272ca65213ed8ced1e`: Baseline/Recovered exigen Administrador distinto de SYSTEM y binding SCM; recibos distinguen clientAuthority=Administrator y maintenanceAuthority=SYSTEM. FailedStart y las CLI siguen SYSTEM por las ACL estrictas. El driver directo retiene source/Common/adjacentCommon/plan por lectura, rehace hashes/NoReparse/ReadPlan/SCM antes del hijo y conserva pin externo. La primera lectura halló que esa nueva ruta no depuraba el entorno del hijo como SystemJob: se pidió y se añadió CleanEnvironment48 antes de Start. Driver contrastado después `0289c064c83671c944b00ef1a7640680c6aed8dbed78e7ccad032ece41538097`. No se autoriza su rama heredada Provision/Stage por esta gate.

Ese primer Baseline Admin también salió1 en Send; **su progreso SQL no se presupone vacío** hasta conciliarlo. No se autoriza repetir seed ni POST por dicho fallo. El diagnóstico Admin previo sólo había leído cabeceras200, no el cuerpo del helper completo; su PASS no cubría ese recorrido.

Se revisa el nuevo delta de diagnóstico Exercise `b10db2dec9434e2c333580740e8155e9d7f28a31ca10eaee11f7e08825204c5c`: añade Ready, metadata estática LastStep/LastMethod/LastPath, conserva innerWebException y escribe sólo Type/HResult/WebStatus en cadena máxima5, sin Message/cuerpo/tokens. **Gate favorable sólo a Ready**: un GET fijo de salud, lectura de su cuerpo y HTTP200, con salida antes de SQL del cliente o cualquier POST. Mantiene Administrador/binding SCM y pin DER/nombre; el driver conserva holds/entorno depurado. Own hash/parser PS5.1: correctos,0errores. Ninguna ejecución E/HTTP propia del revisor. No se amplía la gate a Baseline/Recovered en la nueva fuente hasta medir y conciliar el estado parcial.

### Ready acotado y autorización de la primera Baseline con datos

El diagnóstico Ready de b10db2 devuelve timeout en get_response GET/health/ready, sin haber llegado a read_body. No se infiere un fallo MFA de esa observación. El coordinador consultó después, en sólo lectura y con binding a la DB propia, siete recuentos: clientes/racks/dispositivos/sesiones/factores/desafíos/códigos=0. Este revisor leyó `db-counts-e94dcc2a.json`: readOnlySql/databaseBound=true y esos siete ceros. Eso concilia el estado parcial sin borrar/recrear nada; no se deduce de la mera ausencia de un receipt.

Delta revisado de Exercise `8573a92b2a98a03e9fff746dbe989aa6237fb8a189823001c5b4d2bd1efa776d`: WaitReady48 permite como máximo tres GETs fijos de salud, repitiendo únicamente innerWebExceptionStatus.Timeout y registrando cada observación privada. No reintenta otros errores/HTTPstatus, POST, autenticación, seed o comandos SQL. El reloj/esperas de cada GET siguen acotados por el cliente; no se demuestra la hipótesis de que el primer GET de todo proceso falle. Own hash/parser PS5.1: correctos,0errores. Se concedió primero gate sólo Ready.

**Resultado real Ready actual leído:** `exercise-Ready-a0ddb638.result.json` exit0 y stdout `http_ready_verified`, clientAuthority=Administrator, sqlClientCommands=0. La fuente usa el mismo Send, pin DER/nombre y lectura de cuerpo que Baseline, antes de cualquier branch de mutación. Se conserva el Ready anterior fallido, sin convertirlo en PASS. Es una ejecución del coordinador en E, no del revisor.

**Gate favorable a una única Baseline con esta fuente8573**, ahora que Readiness real pasó y la DB propia quedó conciliada vacía en las relaciones indicadas. La regla de no retry de mutaciones continúa; cualquier fallo posterior debe conciliarse antes de otra acción, sin repetir automáticamente el seed ni regenerar credenciales. No se acredita F0904 por Ready o por esta gate: aún faltan Baseline MFA, pérdida, arranque rechazado, cinco CLI, retorno y comprobaciones posteriores. No se han operado E/SQL/HTTP por el revisor.

## Clasificación independiente del hallazgo de escaneo · cierre documental

El coordinador informa gitleaks8.30.1 sobre268archivos públicos: salida nativa10 (configurada mediante --exit-code10), salida1 del wrapper del coordinador y un hallazgo generic-api-key en `development/server/tests/RackClick.Quality.Tests/MfaWindowsHostHttpTests.cs:33`. **Clasificación acotada: reviewed_synthetic_fixture. Se conservan el hallazgo y ambas salidas (gitleaks10; wrapper1); no se informa0hallazgos ni escaneo limpio.**

Se leyó el código con el valor del literal redactado antes de mostrarlo: Password es private const de la clase de pruebas. Sus usos son el login sintético (líneas67/95) y Secrets.PasswordHash para el usuario nuevo (385). Harness.CreateAsync337 crea una DB `rc_mfa_host_<GUIDnuevo>` desde la conexión administrativa de laboratorio suministrada por el runner; DatabaseConnection fija esa DB nueva, WebApplicationFactory usa el origen rackclick.test y CreateUserAsync genera un UUID de usuario propio. El literal no es el password de conexión PostgreSQL, un token de proveedor ni una clave API en ese recorrido. El test project es IsTestProject/IsPackable=false y referencia al servidor; el proyecto de servidor no referencia las pruebas. El plan nativo48 no contiene la clase ni el ensamblado Quality.Tests. La inicialización nativa usa Secret48 con32bytes aleatorios nuevos, por un camino separado de esa constante.

No se editan test, valor, reglas o exclusiones de escaneo para ocultar el finding. No se abrió el fichero privado de credenciales, initstdout, el checkpoint ni conexiones reales de VM. Esta clasificación no es un barrido histórico de todas las cuentas/DB de D/E ni afirma que cualquier coincidencia futura sea inocua. Simplemente el contexto completo de este finding es un fixture sintético de pruebas y **no aporta evidencia de una credencial real publicada o sembrada en las instalaciones existentes**. No se halló un bloqueo nuevo que invalide F0904 o exija rotación por conjetura.

No se ejecutó aquí otro gitleaks ni una nueva suite; se inspeccionaron fuente/csproj/plan y se conserva la atribución del escaneo al coordinador. El sellado final debe incorporar esta adenda y su SHA256 vigente.
