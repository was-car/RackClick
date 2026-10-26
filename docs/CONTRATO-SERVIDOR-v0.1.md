# RackClick · Contrato del servidor v0.1

**Implementación180–185:** [compensaciónPoE/watts](API-COMPENSACION-POE-S1.md) amplía exclusivamente último ports.update propio. Inversa exacta por fila de seis campos y aliasRJ45 derivado, incluidas combinaciones legacy; familia/roles/properties/cables inmutables. Misma autorización/revisión/igualdad completa y validaciónpower. [GUI/QA59](GUI-COMPENSACION-POE-S1.md), [pruebas](../evidence/s1-20261017/seis-tandas-180-185/CIERRE.md). Undo/redo general sigue pendiente. Registros siguientes históricos.

**Implementación174–179:** [renombrar metadatos privados](API-RENOMBRAR-PLANTILLA-S1.md), exclusivamente activa propia y con definición inmutable; autorización vigente, revisión personal y recuperación/auditoría del journal privado. Sin avisos de inventario ni DDL. [GUI/QA58](GUI-RENOMBRAR-PLANTILLA-S1.md), [cierre](../evidence/s1-20261017/seis-tandas-174-179/CIERRE.md). S-26 sigue parcial; editor libre/compartición/publicación pendientes. Registros siguientes históricos.

**Implementación159–173:** [plantillas PRIVADAS](API-PLANTILLAS-PRIVADAS-S1.md), definición inmutable por actor en SQL009 y creación transaccional con UUID nuevos/configuración de grupos y puertos, libres/sin cables. Captura/retiro con revisión personal y recuperación propias; creación con revisión/auditoría/avisos del inventario. [GUI/QA55–57](GUI-PLANTILLAS-PRIVADAS-S1.md), [cierre y límites](../evidence/s1-20261017/quince-tandas-159-173/CIERRE.md). S-26 sigue parcial: edición libre/compartición/publicación pendientes. No nuevos permisos ni cambiosBASE/CSS/adoptada/versiones. Registros siguientes históricos.

**Implementación144–158:** [SVG pasivo de rack](API-INFORME-RACK-SVG-S1.md), frontal/trasera e idiomas con rack UUID, revisión fuente, lectura+reports.export vigentes, replay/consulta propios y auditoría transaccional. Todos los IDs incidentes conservados; gráfica documental adaptada de reglasRC9, no montaje U/circuitos inventados. [GUI/QA52–54](GUI-INFORME-RACK-SVG-S1.md), [pruebas/revisión y límites](../evidence/s1-20261017/quince-tandas-144-158/CIERRE.md). Sin DDL/esquema8 ni cambios CSV/HTML/capacidades/CSS/adoptada. Plantillas privadas/compartidas, formatos restantes y paquete/adopción siguen pendientes. Registros siguientes históricos.

**Implementación129–143:** [favoritos BASE personales](API-FAVORITOS-PERSONALES-S1.md) persistidos por usuario, revisión propia y propietario derivado de sesión; `inventory.read` actual en cliente contexto para lectura/SET/replay/consulta/cancelación, también para Lector. No se conceden permisos de crear equipos. GUI RC9 conserva borradores/Click-Click y añade consulta/estrellas/filtro; SQL008 aditiva, nueva copia Windows8 con origen7 y recuperación7 conservados. [GUI y QA49–51](GUI-FAVORITOS-PERSONALES-S1.md), [evidencia y límites](../evidence/s1-20261017/quince-tandas-129-143/CIERRE.md). Esto cubre sólo favoritos BASE personales de S-26; plantillas editables privadas/compartidas y publicación siguen pendientes, igual que instalación/adopción final. Notas siguientes históricas.

**Actualización de implementación114–128,17.10.2026:** el catálogo BASE RC9 de referencia se concreta en [API-CATALOGO-BASE-S1.md](API-CATALOGO-BASE-S1.md): lectura por cliente y revisión (`GET /api/v1/customers/{id}/catalog?language=en|de|es`) y comando `device.createFromCatalog` con DTO cerrado, autorización de lectura+edición vigente y creación atómica de equipo/grupos/puertos con identidades nuevas. Son33presets efectivos en7categorías y3idiomas; sus atributos iniciales proceden de la RC9 adoptada. Es referencia inmutable del programa, no un catálogo editable: favoritos y plantillas privadas/compartidas de S-26 mantienen su requisito de persistencia y permisos futuros. [GUI y límites](GUI-CATALOGO-BASE-S1.md); pruebas, revisión y disponibilidad real se atribuyen al [cierre114–128](../evidence/s1-20261017/quince-tandas-114-128/CIERRE.md). Las notas siguientes conservan sus fechas y no sustituyen esa evidencia; la instalación completa y la adopción final siguen pendientes.

**Ampliación autorizada por Wascar04.10.2026:** guía QA actualizable con pasos precisos/ubicaciones/resultados/observaciones y disponibilidad por snapshot; cuentas separadas administrador/técnicos/lector; restauración de su backupRC9 completo a laboratorio/base nuevos; avisos al usuario autorizado cuando otra cuenta modifica el mismo rack/puertos, solo después de commit y sin perder borradores/Click-Click. [Requisitos, alcance y estados](QA-COLABORACION-Y-RESTAURACION.md). Guía/cuentas de laboratorio implementadas; importador/restauración y canal de avisos pendientes. No se equiparan utilidades QA con instalador ni panel administrativo completos.

Fecha: 28.09.2026 · Windows primero · instalación limpia.

**Actualización S1 tras contraste R0:** Wascar confirmó la transición el28.09.2026. El fundamento implementado se concreta en [API-FUNDAMENTO-v0.1.md](API-FUNDAMENTO-v0.1.md): rutas auth canónicas, DTO /me con permisos, OpenAPI ejecutable, Unicode y escritura idempotente. Las secciones de inventario/administración/operación siguientes conservan su alcance completo; no se declaran realizadas por esta actualización.

## Instrucción de entrega de Wascar · 28.09.2026 05:13 Europe/Berlin

Esta instrucción precisa el método de trabajo y prevalece sobre cualquier referencia posterior a entregar por separado un bloque S1, S2 o un parche. Los bloques siguen siendo hitos internos de desarrollo; Wascar recibirá builds completas de instalación del sistema, con versión, alcance y evidencia, no una secuencia de carpetas sueltas que deba fusionar. No se considera entrega usable un documento, un frontend aislado o una API sin su GUI conectada.

Cada candidata para QA debe permitir recorrer desde cero: comprobar la VM y dependencias; instalar únicamente lo ausente o incompatible mediante versiones fijadas; crear base, identidad de servicio, secretos y administrador nuevos; iniciar el servicio; probar la aplicación; respaldar/restaurar y desinstalar o reiniciar la instancia de laboratorio. Las dependencias de ejecución forman parte del paquete o de su instalador guiado con verificación de integridad; si una descarga es necesaria, debe declararse antes, sin fingir una instalación offline completa. El manual no debe omitir un paso por haber sido ejecutado en una sesión anterior.

Reinicio limpio de QA: operación independiente de actualización y reparación. Detiene el servicio de la instancia identificada, muestra base/rutas/secretos que se reiniciarán, pide confirmación explícita de ese destino y crea credenciales nuevas. No borra otras bases, instalaciones PostgreSQL compartidas, servicios ajenos ni copias externas. No se realiza ninguna eliminación en la VM de Wascar desde esta instrucción; solo define la futura función del instalador.

Orden funcional obligatorio de arriba hacia abajo: nombre/configuración Systemhaus → clientes → sedes/edificios/salas → racks → catálogo/plantillas/favoritos → dispositivos → puertos/estados/PoE/caras → conexiones/notas/colores → búsqueda/reportes/exportes → panel administrativo y operación. Autenticación, autorización y transacciones están presentes desde el primer dato persistido; el orden visual no justifica aplazar esas protecciones.

Persistencia completa: todos los datos compartidos deben proceder de la base; preferencias y favoritos pertenecen al usuario adecuado. Los tooltips se forman a partir de los datos persistidos actuales, no de copias estáticas con información desfasada. El texto derivado, como número de conexiones, se calcula sobre esos datos con consultas/selectores coherentes; no se almacena como una segunda verdad independiente. Se permite cache temporal con invalidación, nunca inventario maestro paralelo en localStorage. Reiniciar navegador, sesión y servicio debe conservar la información confirmada y mostrarla al segundo usuario autorizado.

Panel administrativo como parte del sistema completo: usuarios, contraseñas/restablecimiento, grupos de usuarios, grupos de clientes, roles, ámbitos, permisos efectivos, sesiones y auditoría. Debe entregarse integrado y probado antes de presentar la candidata completa como apta para la QA global solicitada. Los hitos internos incompletos no se presentan como producto terminado.

Formato de entrega: un paquete de instalación completo con binarios, GUI, dependencias gestionadas, scripts PowerShell, diez clientes sintéticos opcionales, manual visual desde cero, matriz de alcance, evidencias, hashes, licencias y procedimiento de rollback. Los tests internos pueden avanzar por bloques; una entrega a Wascar no depende de instalar la candidata anterior. Este cambio de proceso no equivale a tener implementado el instalador ni el servidor.

**Estado actualizado: diseño técnico elaborado; implementación S1 inicial y compilación Linux disponibles. Integración PostgreSQL/GUI, Windows y revisión independiente del producto pendientes.** No es una build, un contrato comercial ni una afirmación de compatibilidad ya probada. Las decisiones de ingeniería aquí propuestas se toman bajo la delegación de Wascar; cualquier cambio visible respecto a RC9 debe quedar identificado antes de su adopción.

## 1. Objetivo y bases exactas

Conservar la experiencia aprobada de RC9 y darle almacenamiento compartido, autorización y edición concurrente mediante una API. La aplicación offline permanece operativa e independiente. El servidor no será un HTML offline incrustado que siga guardando inventario en localStorage.

La instalación nueva parte de cero: Systemhaus configurable, cuenta administradora nueva y base nueva. Las bases y cuentas de R3 son material de laboratorio; migrarlas no es condición de entrega. No se borran automáticamente. Importar un JSON elegido sigue siendo parte del producto.

Base visual y funcional: `RackClick-v0.9.0-rc9-Offline.html`, SHA-256 `63a60c4b52360211e1ae90b2e38541dc76bf372007219868e7c203af9223ea96`, confirmado de nuevo en esta revisión. Su código está en el ZIP de referencia. Base de aprendizaje del backend: R3 del ZIP enviado por Wascar. No se equipara R3 a RC9 ni se publica R3 como servidor productivo.

## 2. Hallazgos que cambian el trabajo de integración

| ID | Observación reproducida | Consecuencia |
|---|---|---|
| S0-01 | El fixture RC9 de diez clientes se acepta por R3: 68 racks se insertan en un único cliente y una única sala de destino. | Su importador es de destino único. No se reutiliza sin adaptación para backups multi-cliente. El original se conserva, pero la organización consultable cambia. |
| S0-02 | `project_view` devuelve puertos con id/number/status/watts/portColor/label; no devuelve type ni rackclickFace. | RC9 no puede representar fielmente caras y conectores usando esa proyección. Los datos originales conservados no bastan si la API no los expone. |
| S0-03 | El golden de doble ocupación de RC9 es rechazado con `port used by multiple connections`. | El contrato debe conservar el original y explicar la incompatibilidad antes de confirmar una importación; no elegir un cable arbitrariamente. |
| S0-04 | El código de RC9 se construye combinando el JSX base y módulos de patches; todavía no tiene un adaptador de persistencia de servidor. | Extraer comandos y acceso a datos con pruebas de paridad; cambiar solo la URL de carga no integra las escrituras. |
| S0-05 | R3 implementa login/logout, lectura, importación y descarga de original; `inventory.edit` está reservado. | Crear las operaciones reales de escritura y su autorización. El botón habilitado no acredita persistencia. |

Las 25 pruebas heredadas pasan en Linux. Son evidencia de R3 dentro de su alcance original, no evidencia de que la API ya cubra RC9. Los tres primeros hallazgos se reproducen con `tools/audit_bridge.py`; S0-04/05 proceden de inspección de código. No se ha vuelto a ejecutar toda la batería visual RC9 en esta entrega.

## 3. Decisión técnica para el servidor nuevo

**Dirección elegida: C# / ASP.NET Core sobre .NET 10 LTS, PostgreSQL 17 y frontend compilado reutilizando los componentes y estilos de RC9.** PostgreSQL sustituye como objetivo al SQLite del documento R3: la instalación limpia permite tomar esta decisión antes de acumular datos de producción. Su razón es concentrar la coordinación transaccional de varios técnicos en un servicio de base de datos, sin desarrollar dos backends SQL a la vez. SQLite no se declara incapaz: permanece válido para el piloto y como referencia histórica.

Se elige PostgreSQL 17 para mantener Windows Server 2019 dentro del objetivo de validación del instalador; la matriz publicada de instaladores Windows lista 2019/2022 para esa rama. El parche concreto se fijará en el manifiesto de la primera build, tras su validación. No se promete soporte de una versión de Windows solamente por poder arrancar.

Un monolito modular: identidad/autorización, inventario, intercambio, informes y operación, con una base por Systemhaus instalado. Clientes separados por IDs, ámbito y restricciones, no una base por cliente en la primera entrega. Sin microservicios, Kubernetes ni dependencia de hosting LWS.

El código React/JSX de RC9 se conserva primero; TypeScript se usa en contratos y nuevos módulos. No se promete una conversión instantánea de todo el JSX ni se redibuja el rack. HTML/CSS/SVG y fuentes siguen locales. La versión servidor tendrá identidad propia, propuesta `RackClick Server 0.1.0-alpha1`, sin alterar el hash del offline adoptado.

Publicación Windows autocontenida: runtime .NET incluido y frontend compilado. En el equipo de Wascar no será necesario instalar Python, Node, npm, Visual Studio ni el SDK para usar el servidor final. PostgreSQL sí es una dependencia de instalación, con cuenta de servicio y datos separados. El desarrollo y CI requieren SDK .NET y herramientas frontend; son responsabilidades de construcción, no requisitos del técnico usuario.

Actualización de entorno: se instaló SDK 10.0.401 y se compiló la base ASP.NET en Linux; ver INICIO-IMPLEMENTACION-S1.md y logs. PostgreSQL nativo sigue sin probarse por restricciones del entorno remoto. Windows y la GUI conectada no están verificados. No sustituir silenciosamente el backend por un piloto Python.

## 4. Modelo de datos y compatibilidad

| Entidad | Identidad / relaciones / datos obligatorios |
|---|---|
| Systemhaus | UUID estable, nombre editable, revisión y configuración. Una instancia inicial. |
| Cliente | UUID, Systemhaus, nombre, técnico documental, logo, metadatos de proyecto y revisión del inventario. |
| Standort / edificio / sala | UUID y padre inequívoco. Cliente heredado y FK compuesta; nombre vacío no se transforma silenciosamente en una sede real. |
| Rack | UUID, cliente, sala opcional, nombre, ubicación libre legacy, tamaño, revisión y extensiones. |
| Dispositivo | UUID, rack, orden de montaje y posición según datos reales RC9; altura, preset, nombre, color, inventario técnico, notas, grupos, presupuesto PoE. No inventar una U física a partir de la mera posición de un array. |
| Puerto | UUID, dispositivo, tipo, gn, prefijo/etiqueta, estado, configuración PoE, watts, color, face explícita o automática y rol de alimentación. `gn` puede repetirse entre tipos; no es la clave. |
| Conexión / extremo | UUID, dos puertos de un mismo cliente, color explícito, nota y estado de patch. Local/cross-rack se deriva de los racks actuales. |
| Catálogo / plantilla / favorito | Plantilla compartida o privada con propietario y permiso específico; favorito personal. Persistir distribución front/rear y atributos de puertos soportados. |
| Identidad / grupos / concesiones | Usuarios estables, grupos de usuarios, grupos de clientes, roles de capacidades y concesiones por ámbito. |
| Operación / auditoría / revisión | Actor, cliente, tipo de comando, objetos, hora UTC, revisiones, resultado e identificador de petición. Auditoría transaccional. |
| Importación / paquete de campo | Original exacto, digest, manifiesto, plan de mapeo, validaciones y decisiones explícitas. |

Se almacenan los campos RC9 conocidos y extensiones desconocidas para no destruirlos. Las extensiones se validan por tamaño/tipo y no adquieren autoridad sobre permisos. Los IDs del servidor y los IDs exportables legacy tienen mapeo explícito estable. Dos clientes con el mismo nombre no se fusionan. Renombrar un cliente no cambia su identidad.

Puertos: la cara es presentación sobre una única identidad lógica, igual que RC9. No crea automáticamente un segundo terminal trasero, un paso IDC interno ni un circuito eléctrico. No confundir PoE con alimentación AC. Preservar conexiones y watts al editar grupos; una reducción enumera exactamente lo que se elimina antes de confirmar.

Topología nueva: no se conecta entre clientes; cross-rack dentro de un cliente sí. Reserved solicita la confirmación conocida; disabled/faulty se bloquean. El color elegido expresamente prevalece sobre la regla automática. La reconexión mueve un extremo en una operación atómica; cancelar conserva el cable.

Doble ocupación heredada: se conserva el fichero completo en staging y se presenta el conjunto completo en previsualización con avisos, sin guardarlo parcialmente como inventario normal. La importación no se declara confirmada hasta que el administrador resuelva cada colisión o mantenga el lote pendiente. El offline RC9 sigue abriendo ese fichero tal como lo hace hoy. Ampliar el modelo a terminales y pasos internos será una decisión separada, no una reparación inventada por el importador.

## 5. Separación de UI y persistencia

Se introduce un adaptador con `readCustomer`, `executeCommand`, `previewImport`, `commitImport`, `exportCustomer`, `readPreferences` y `writePreferences`. El offline mantiene su adaptador local; servidor usa HTTP y no escribe inventario como copia maestra en localStorage.

Los handlers observados de RC9 se convierten en comandos o selectores. Una función de transformación pura puede reutilizarse, pero el servidor revalida y autoriza siempre. El informe obtiene una instantánea coherente del cliente autorizado; no combina racks de varias respuestas con revisiones incompatibles.

Estados de guardado: Sin cambios / Guardando / Guardado por el servidor / Error / Conflicto. Solo se muestra Guardado después del commit confirmado. Ante respuesta perdida se consulta o reintenta la misma operación idempotente; no se envía una creación nueva. No habrá edición offline silenciosa dentro del navegador servidor durante una caída. Se conserva el borrador en memoria y se ofrece recuperación; la captura sin red usa el offline aprobado mediante un paquete de campo controlado.

## 6. API inicial y concurrencia

Prefijo propuesto `/api/v1`. Mismo origen para interfaz y API; cookies de sesión HttpOnly/Secure y protección CSRF para cambios. No almacenar tokens de sesión en localStorage. Límites de tamaño, tipos válidos, errores estructurados y mensajes traducidos por código.

| Operación | Ruta propuesta | Condición |
|---|---|---|
| Iniciar / cerrar sesión | POST `/auth/login`, `/auth/logout` | Límite de intentos y revocación |
| Identidad y permisos | GET `/me` | Datos de la sesión vigente |
| Listar clientes | GET `/customers` | Solo clientes autorizados |
| Leer proyecto de cliente | GET `/customers/{id}/project` | Snapshot coherente y ETag |
| Modificar inventario | POST `/customers/{id}/commands` | If-Match, Idempotency-Key y permiso de la operación |
| Previsualizar / confirmar importación | POST `/imports/preview`, `/imports/{id}/commit` | Plan de clientes explícito, original exacto, revisión del destino |
| Exportar / crear paquete de campo | POST `/customers/{id}/exports`, `/customers/{id}/field-packages` | Permiso de transferencia, revisión y auditoría |
| Resolver retorno de campo | POST `/field-packages/{id}/preview`, `/field-packages/{id}/commit` | Comparación base/retorno/servidor y decisiones de conflicto |
| Usuarios, grupos, roles y ámbitos | `/admin/users`, `/admin/user-groups`, `/admin/customer-groups`, `/admin/roles`, `/admin/grants` | Lectura/administración explícitas |
| Auditoría y permisos efectivos | GET `/admin/audit`, `/admin/users/{id}/effective-permissions` | Permisos administrativos |
| Backup / estado de tareas | POST `/admin/backups`, GET `/admin/jobs/{id}` | Operación restringida, sin secreto en respuesta |

Es catálogo de rutas y semántica, no un OpenAPI ejecutable ya validado. El OpenAPI completo con schemas se genera y prueba en S1 antes de conectar la UI.

Primer control de concurrencia: revisión agregada por cliente, deliberadamente conservadora. Cada comando valida la revisión esperada, bloquea la fila de revisión del cliente dentro de la transacción, comprueba autorización y pertenencia de todos los objetos, aplica cambios, escribe auditoría e incrementa revisión. Clientes diferentes pueden editarse en paralelo; cambios dentro del mismo cliente se serializan y un borrador antiguo produce conflicto. Se acepta más conflicto visible para evitar pérdida silenciosa; granularidad por rack se evaluará con evidencia posterior.

ETag ausente en escritura: 428. Revisión desfasada: 412. Conflicto de dominio o reutilización de clave con otra petición: 409. Datos inválidos: 422. Falta de login: 401. Operación prohibida sobre recurso ya visible: 403; un objeto no visible responde 404 sin revelar su existencia. La UI mantiene el borrador y permite revisar diferencias; no hay botón que sobrescriba sin volver a validar.

La idempotencia liga usuario, cliente, clave, comando y digest. Un reintento ya confirmado devuelve el mismo resultado; una carga distinta con la misma clave se rechaza. El resultado se guarda en la misma transacción que los cambios. Retención inicial de operaciones 30 días; el contrato advierte que un reintento tras caducidad necesita consultar el estado antes de repetir. No se confía en timestamps del navegador para ordenar escrituras.

Undo/redo: compensación autorizada de la operación propia, condicionada a las revisiones afectadas. Nunca reponer un snapshot completo de cliente sobre cambios de otro técnico. La nueva semántica se explica en el manual; el historial local de 30 niveles de RC9 no puede copiarse literalmente a colaboración.

## 7. Permisos y administración

Modelo inspirado en la separación de grupos de usuarios y recursos de AD, con autorización propia. No son GPO ni permisos NTFS. No hay anidamiento de grupos en la primera entrega; concesiones positivas se unen y la ausencia de permiso deniega. No introducir reglas Deny con precedencia implícita. AD/OIDC queda previsto mediante mapeo explícito, fuera de la primera build.

| Capacidad | Admin Systemhaus | Técnico asignado | Lector asignado |
|---|---|---|---|
| Leer inventario | Sí | Sí, su ámbito | Sí, su ámbito |
| Editar / conectar / mover dentro de cliente | Sí | Sí, si concedido | No |
| Eliminar rack/equipo | Sí | Solo concesión separada | No |
| Importar / exportar originales y paquetes | Sí | No por defecto | No |
| Generar descargas de informes y etiquetas | Sí | Solo `reports.export` concedido | No por defecto |
| Gestionar usuarios y concesiones | Sí | No | No |
| Backup / restauración | Sí, capacidad específica | No | No |

`inventory.read` no impide que una persona copie o fotografíe datos visibles. Los permisos de exportación controlan las funciones de transferencia ofrecidas por el producto; no prometen evitar toda extracción desde un navegador autorizado.

Los técnicos conservan etiquetas de perfil editables; la palabra Technician no concede nada por sí sola. Panel muestra permisos efectivos y de qué grupo provienen. Cambiar membresía, desactivar cuenta o restablecer contraseña invalida sesiones/permiso cacheado. Las mutaciones de permisos y escrituras coordinan una revisión de autorización: una escritura validada antes de una revocación puede terminar; las autorizadas después no se aceptan. Tests fijan ese orden.

Protección del último administrador activo, reinicio seguro de credenciales, caducidad de sesiones, limitación de login, contraseña robusta con componente ASP.NET Identity y auditoría sin contraseñas/tokens. Un futuro cliente externo requiere publicación de campos; el lector interno no se reutiliza como portal externo sin filtrado.

## 8. Instalación Windows limpia y operación

Acceso confirmado por Wascar el19.10.2026: todos los usuarios trabajan desde el navegador; no se instala RackClick, PostgreSQL ni un agente en sus equipos para usar la web. Windows11 y WindowsServer son opciones para alojar el servidor, donde sí se instalan la aplicación y su base. Windows11 no implica un cliente instalado ni un rol fijo «cliente3». El inventario de preparación sólo se exige para el equipo que vaya a alojar el servidor; los navegadores acceden al origenHTTPS configurado y la autorización se aplica en el servidor.

Objetivo principal de QA: Windows 11 x64 en la VM de Wascar. Server 2019, 2022 y 2025 son objetivos adicionales de matriz, no sistemas ya certificados. Linux se pospone sin acoplar el núcleo a rutas o APIs exclusivas de Windows.

Propuesta de instalación: binarios versionados bajo Program Files, datos/configuración/logs bajo ProgramData y base PostgreSQL local. Servicio con cuenta de mínimo privilegio; identidad del técnico distinta de identidad del servicio. PostgreSQL escucha en loopback, sin puerto público. Servicio web con HTTPS y nombre estable de la VM; certificado de CA interna en entorno de empresa o certificado de laboratorio importado explícitamente como confiable. El certificado de desarrollo .NET no se da por apto para servicio Windows.

El instalador futuro hará comprobación previa, instalación/configuración de DB, inicialización, primera cuenta por canal local de un solo uso, registro de servicio y prueba de salud. No imprimirá una contraseña común para todos ni la incluirá en el ZIP. Firewall limitado a la subred autorizada; ningún reenvío de Internet en el piloto. IIS y Docker no son requisitos del diseño.

PowerShell será el punto de entrada para instalar, consultar estado, detener, respaldar, restaurar y actualizar. Los scripts deberán detenerse ante errores, registrar resultados y ser idempotentes sin reinicializar datos por accidente. En S0 estos scripts de instalación todavía no existen; los de `reference/r3` son históricos.

Backup: tarea diaria inicialmente, retención propuesta 7 diarios + 4 semanales. Destino configurable local/USB/UNC; cuenta con permiso mínimo. Crear dump consistente mediante pg_dump, incluir blobs/originales y configuración recuperable, manifiesto/hashes, cifrado con clave recuperable separada y prueba de lectura. Primero guardar local y después copiar al destino; un NAS no disponible produce alerta y no borra el último backup válido. No copiar el directorio vivo de PostgreSQL como si fuese un JSON.

Restaurar siempre en base nueva y validar esquema, conteos, referencias, usuarios/permisos y acceso de prueba antes del cambio de servicio. Las sesiones anteriores se revocan tras restauración. Certificados/claves protegidos por Windows requieren procedimiento explícito de recuperación; no suponer que un secreto ligado a una VM funcionará en otra. La identidad de la app de DB y los roles necesarios se recrean mediante instalación, no solo con el dump.

RPO inicial propuesto de 24 h para backup diario; RTO objetivo de 2 h en laboratorio, a medir. Veeam/Synology pueden respaldar el conjunto, pero una copia existente no sustituye el ensayo de restauración. Actualización con backup previo y migración versionada; si el esquema no es compatible hacia atrás, rollback mediante restauración a base nueva, no arrancando binarios viejos sobre tablas nuevas.

## 9. Entregas y estimación de esfuerzo

Jornadas técnicas orientativas, no promesa de calendario ni ejecución autónoma fuera de las sesiones. Se revisan con los resultados de cada bloque. Incluyen desarrollo y pruebas del bloque, no espera por acceso/QA del usuario.

| Bloque | Alcance | Estimación | Salida |
|---|---|---|---|
| S0 | Contrato y diagnóstico; revisión separada y schemas pendientes | 2–3 | Diseño consistente y backlog verificable |
| S1 | Servicio, DB nueva, login, ámbitos y primer recorrido RC9 persistido | 6–9 | Cliente → rack → editar un dispositivo → conectar → recargar; 2 usuarios y conflicto probado |
| S2 | Resto de operaciones de inventario, plantillas, reportes e import/export | 10–15 | Matriz de paridad del alcance servidor con evidencia |
| S3 | Panel administrativo, grupos de clientes, sesiones y auditoría consultable | 5–8 | Permisos efectivos comprobados por UI/API |
| S4 | Instalador limpio, backup/restore, actualización y piloto LAN | 6–9 | VM nueva restaurada, servicio automático y QA de Wascar |
| S5 | Paquete de campo con retorno y conflictos | 5–8 | Ida/vuelta sin sobrescritura silenciosa |

Orden interno S0 → S1 → S2 → S3 → S4; S5 después de tener revisión/exportación estables. Total orientativo S0–S4: 29–44 jornadas; con S5: 34–52. S1 es un hito técnico interno, no una entrega parcial para que Wascar integre componentes. La siguiente candidata completa para su QA global debe incluir la GUI persistida del alcance acordado, panel administrativo e instalación limpia. Seguridad mínima, auditoría y conflictos se incorporan en S1, no se aplazan a S3. El cambio de formato de entrega no acorta por sí solo el esfuerzo de implementación.

## 10. Gobierno y próxima acción concreta

No se repiten las 57/69 comprobaciones offline como puerta artificial del servidor. Se reutilizan como casos de paridad; las nuevas pruebas son persistencia, roles, concurrencia, instalación y recuperación. RC9 queda adoptada con su hash. R3 queda archivado como laboratorio. S0 elaborado. S1 iniciado: primera base C# compilada y pruebas de dominio/HTTP de fallo ejecutadas; integración PostgreSQL y GUI pendientes. S2–S5 pendientes. Ver INICIO-IMPLEMENTACION-S1.md para el alcance comprobado.

Siguiente trabajo de implementación: construir la base ASP.NET/DB y el adaptador HTTP en una carpeta de desarrollo independiente; conectar el primer recorrido RC9 con guardado real. Antes de entregar, compilar el binario, probar en entorno definido y separar lo verificado en Linux de lo verificado en Windows. No basta servir el HTML sin CDN para afirmar que trabaja con DB.

Revisión independiente pendiente de este contrato y después de cada candidata. Ninguna corrección queda validada solo por quien la implementa. Wascar evalúa navegación y flujo real; desarrollo/QA prueban backend y seguridad. La autorización de trabajo ya existe; adopción final requiere su confirmación expresa.

## Fuentes oficiales consultadas

- Microsoft, Windows Service y publicación autocontenida: https://learn.microsoft.com/en-us/aspnet/core/host-and-deploy/windows-service?view=aspnetcore-10.0
- Microsoft, versiones y soporte .NET: https://learn.microsoft.com/de-de/dotnet/core/releases-and-support
- PostgreSQL, instaladores Windows y matriz publicada: https://www.postgresql.org/download/windows/
- PostgreSQL 17, pg_dump y consistencia: https://www.postgresql.org/docs/17/app-pgdump.html

Estas fuentes justifican opciones de plataforma; no prueban el código de RackClick ni la instalación de la VM de Wascar.


## Diferencias de implementación y puerta de recepción

El código inicial recibido usaba /api/v1/login y /logout; en S1 Windows se alineó a /api/v1/auth/login y /auth/logout. /me incluye permisos efectivos y GET /api/v1/openapi.json describe el fundamento. Ver API-FUNDAMENTO-v0.1.md y evidencia nueva. La jerarquía inicial aún serializa mediante Systemhaus; revisión de inventario por cliente, retención30días, revocación administrativa coordinada y panel completo siguen pendientes. R0 ya fue contrastado; no reabrir su pausa. Adopción del servidor únicamente después de QA final.
