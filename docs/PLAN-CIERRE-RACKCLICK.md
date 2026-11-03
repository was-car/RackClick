# RackClick · inventario completo y plan de cierre medible

Base **RC-CIERRE-20261103-v3**, 2026-11-03. El inventario inicial se creó mediante conciliación documental. Los avances posteriores y sus pruebas se acreditan en los subpasos, con evidencias propias; no se convierten en aceptación de QA.

**El 78 % anterior queda retirado como indicador vigente.** Sus 7 puntos pendientes funcionales eran 2 de fundamento, 3 de inventario, 1 de administración y 1 de paridad: no eran 7 tareas. El inventario actual distingue 7 bloques, con trabajo concreto y evidencia.

**Cierre de este trabajo restante: 14,76/100 puntos.** No significa que el producto esté al 0 %. Lo ya construido se reconoce abajo. No se conoce aquí un nuevo porcentaje global del producto y no se utiliza 78+22×cierre.

El inventario tiene **53 entradas: 50 resultados ponderados y 3 decisiones/controles sin doble puntuación; 280 subpasos**. No son jornadas, pruebas nuevas ni nuevas funciones. Los 55 criterios S1–S4 están trazados; S-50/retorno de campo pertenece a S5.

## Cómo se calcula y qué cambia desde hoy

Cada bloque recibe un peso de cierre explícito. Es una propuesta de prioridad/riesgo, no una estimación objetiva de horas o créditos. Dentro de cada bloque se reparte el peso entre sus resultados únicos; cada subpaso conserva una fracción fijada antes de ejecutarlo.

`Puntos cerrados = suma del peso de los subpasos terminados y respaldados por evidencia.`

Un subpaso implementado/probado puede dar avance parcial; cerrar la tarea completa exige su comprobación final y revisión independiente. La aceptación de Wascar se pide sólo donde corresponde, no como permiso para desarrollar. Una decisión pendiente no se presenta como ausencia de código ni obliga a rehacer lo ya probado.

El denominador inicial es 100. No aumenta por bugs, ZIPs, pruebas repetidas o subdivisiones. Un resultado reabierto pierde crédito; un requisito realmente nuevo/omitido exige una versión explicada del inventario, conservando la anterior. La huella fija también títulos, criterios, cierre y texto de subpasos: reducirlos no puede aparentar avance. Los hitos históricos done/pending/unknown del JSON son informativos y no suman otra vez al cierre pendiente.

| Bloque | Peso del cierre | Cerrado | Resultados con peso |
|---|---:|---:|---:|
| F · Fundamento, seguridad y MFA | 25 | 7,62 | 10 |
| I · Jerarquía, inventario y colaboración | 15 | 3,63 | 6 |
| A · Usuarios, grupos y administración | 5 | 0,00 | 4 |
| P · Paridad funcional y visual RC9 | 15 | 0,00 | 11 |
| W · Instalación y operación Windows | 15 | 3,50 | 6 |
| R · Backup, recuperación y actualización | 15 | 0,00 | 6 |
| E · Paquete, manual, rendimiento y aceptación | 10 | 0,00 | 7 |

**Ejemplo:** W-01 tiene 2,50 puntos, repartidos en 5 subpasos. Terminar y acreditar el primero mueve el cierre pendiente 0,50 puntos; repetir la misma prueba no lo vuelve a sumar. Es un ejemplo del reparto real de esta base, no una ejecución nueva.

## Lista resumida de todos los resultados pendientes

| ID | Resultado | Tipo de pendiente | Puntos de cierre |
|---|---|---|---:|
| F-01 | Clasificar hallazgos de secretos y tratar sólo credenciales reales | archivado administrativamente con incertidumbre residual | 2,50 |
| F-02 | Cifrar configuración SQL y recuperar sus secretos en otra instancia | cerrado técnicamente con revisión independiente | 2,50 |
| F-03 | Registrar decisión de custodia y ubicación definitiva D2 | decisión de custodia/recuperación confirmada; concreción técnica pendiente | 0,00 |
| F-04 | Implementar proveedor TOTP Windows bajo la identidad real del servicio | Proveedor real integrado en candidata10; F-04.03 cerrado, ACL/otros tokens y cierre total pendientes | 2,50 |
| F-05 | Implementar sobre portable autenticado y restauración de claves | implementación | 2,50 |
| F-06 | Cerrar rotación y recuperación coherente entre anillo y PostgreSQL | implementación | 2,50 |
| F-07 | Completar enrolamiento restringido cuando MFA sea exigible | F-07.01 a .04 cerrados técnicamente en laboratorio; candidata, custodia real integrada y cierre .05 pendientes | 2,50 |
| F-08 | Implementar códigos de recuperación y reenrolamiento restringido | implementación | 2,50 |
| F-09 | Implementar recuperación local cuando no quedan clave, sobre ni códigos | implementación | 2,50 |
| F-10 | Completar panel/política MFA por usuario y obligatoriedad antes de producción | implementación | 2,50 |
| F-11 | Integrar segundo paso y todos los formularios de reautenticación | integración | 2,50 |
| F-12 | Acreditar MFA y fundamento sobre la candidata completa por HTTP/HTTPS | integración HTTP de L1 revisada; matriz final de seguridad pendiente | 0,00 |
| I-01 | Ofrecer e integrar Deshacer de crecimiento/reducción pura de grupos | parcial; candidato y confirmación GUI revisados en laboratorio | 2,50 |
| I-02 | Cerrar alcance restante de compensación colaborativa y Rehacer | definición finita e implementación | 2,50 |
| I-03 | Cerrar matriz RC9 de conector, cara, rol eléctrico y presupuesto PoE | cobertura y corrección sólo de defectos reproducidos | 2,50 |
| I-04 | Cerrar variantes de jerarquía, racks, equipos y orden ya implementados | parcial; catálogo, variantes de rack y duplicado revisados en laboratorio | 2,50 |
| I-05 | Cerrar variantes de Click-Click, lotes, reconexión y cables | cobertura y aceptación | 2,50 |
| I-06 | Completar verificación de Dosen y finales ya soportados en sala | edición, puertos, roles y borrado GUI verificados técnicamente; matriz restante pendiente | 2,50 |
| I-07 | Decidir modelo de terminales y pasos internos de Dose/panel | decisión física y diseño condicional | 0,00 |
| A-01 | Cerrar atribución técnica C1 S-38 a S-42 en la candidata vigente | probado_acotado | 1,25 |
| A-02 | Completar aceptación visual del recorrido administrativo existente | aceptación | 1,25 |
| A-03 | Conciliar y cerrar atribución de auditoría fuera de las21formas administrativas | integración | 1,25 |
| A-04 | Cerrar retención operativa, correlación y recuperación de operaciones antiguas | implementación | 1,25 |
| P-01 | Convertir restauración RC9 de laboratorio en importación normal | implementación API/GUI | 1,36 |
| P-02 | Previsualizar inválidos y doble ocupación sin perder enlaces | staging y pruebas | 1,36 |
| P-03 | Exportar JSON actual y original exacto como funciones distintas | implementación API/GUI | 1,36 |
| P-04 | Demostrar round-trip JSON y preservar extensiones | integración y compatibilidad | 1,36 |
| P-05 | Cerrar lista de herramientas RC9 restantes y sus equivalentes | definición finita e implementación condicional | 1,36 |
| P-06 | Persistir identidad documental del cliente y branding RC9 | modelo/API/GUI | 1,36 |
| P-07 | Cerrar formatos existentes y resolver obligación PDF | cobertura y decisión | 1,36 |
| P-08 | Concluir aceptación de plantillas/favoritos/preferencias existentes | integración final y aceptación | 1,36 |
| P-09 | Cerrar compatibilidad y aceptación de avisos multiusuario | cobertura/integración/aceptación | 1,36 |
| P-10 | Auditar EN/DE/ES, temas y literalidad de datos | cobertura/correcciones | 1,36 |
| P-11 | Completar teclado, lector, contraste y paridad visual funcional | auditoría/correcciones | 1,36 |
| W-01 | Corregir parada D14-07 y validación de edición del generador | cerrado con revisión independiente | 2,50 |
| W-02 | Instalar desde cero en Windows limpio y declarar la matriz soportada | New10 en C verificado tras reinicio; W-02.01/.02 cerrados, matriz restante pendiente | 2,50 |
| W-03 | Cuenta mínima, servicio Windows y arranque automático reales | pendiente de cierre | 2,50 |
| W-04 | HTTPS, certificados, red y acceso casa/trabajo en la edición final | pendiente de cierre | 2,50 |
| W-05 | Repetición, cancelación, mantenimiento y diagnóstico del instalador | pendiente de cierre | 2,50 |
| W-06 | Recorrido completo de persistencia y concurrencia del servidor instalado | pendiente de cierre | 2,50 |
| R-01 | Backup programado local y retención comprobada | pendiente de cierre | 2,50 |
| R-02 | Destinos USB y UNC con copia local previa y tolerancia a fallos | pendiente de cierre | 2,50 |
| R-03 | Backup cifrado de instalación y recuperación de material privado | pendiente de cierre | 2,50 |
| R-04 | Recuperación completa en otro Windows y activación controlada | pendiente de cierre | 2,50 |
| R-05 | Actualización y rollback compatibles con datos posteriores | pendiente de cierre | 2,50 |
| R-06 | Reset y recuperación administrativa delimitados | pendiente de cierre | 2,50 |
| E-01 | Candidata final única con fuentes y componentes compatibles | pendiente de cierre | 1,43 |
| E-02 | Aprovisionamiento y construcción repetibles desde fuentes oficiales | pendiente de cierre | 1,43 |
| E-03 | Inventario de dependencias, avisos y redistribución | pendiente de cierre | 1,43 |
| E-04 | Manual autónomo de instalación, uso y operación | pendiente de cierre | 1,43 |
| E-05 | QA manual por módulos sobre candidata identificada | pendiente de cierre | 1,43 |
| E-06 | Medir carga real de diez usuarios y demo completa | pendiente de cierre | 1,43 |
| E-07 | Revisión final y adopción explícita de Wascar | pendiente de cierre | 1,43 |

## Trabajo existente que se conserva

Las referencias acreditan sus builds/entornos originales y límites; no se convierten en pruebas nuevas de la candidata final. Esta lista no vuelve a cero ni recibe otro peso por copiarla al plan.

- **Toolchain y laboratorio Windows repetibles**: Git local, SDK10.0.401 fijado, PG17.11 nativo, frontend y laboratorios nuevos/secretos privados; no instalar de nuevo por inercia. Referencia: [docs/S1-FUNDAMENTO.md](S1-FUNDAMENTO.md), [docs/SOLUCION-CONSOLA-VSCODE.md](SOLUCION-CONSOLA-VSCODE.md).
- **Bootstrap/login password y sesión nueva**: Primera cuenta local/Unicode/límites, login correcto/incorrecto, limitación/bloqueo, sesión/CSRF nuevos, logout y estado básico. No equivale a MFA listo. Referencia: [docs/S1-FUNDAMENTO.md](S1-FUNDAMENTO.md), [docs/REVISION-M3-CORRECCIONES-CODEX.md](REVISION-M3-CORRECCIONES-CODEX.md).
- **Ámbitos/grupos/concesiones/efectivos y revocación**: Capacidades propias del servidor, unión de vías, tipos de grupo separados y API/panel existentes. No se necesita AD/GPO ni nuevo cálculo autoritativo React. Referencia: [docs/C1-CONCILIACION-S38-S42.md](C1-CONCILIACION-S38-S42.md), [docs/REVISION-M3-CORRECCIONES-CODEX.md](REVISION-M3-CORRECCIONES-CODEX.md).
- **Persistencia, conflicto, replay y atomicidad del fundamento**: PostgreSQL real con recarga/otra sesión/reinicio; revisión e idempotencia, auditoría/operation/mutación en misma transacción y rollback. No afirma todos los escritores del producto. Referencia: [docs/S1-FUNDAMENTO.md](S1-FUNDAMENTO.md), [docs/REVISION-M3-CORRECCIONES-CODEX.md](REVISION-M3-CORRECCIONES-CODEX.md).
- **Migraciones SQL y separación DB owner/runtime**: Runner SQL001..014 con hashes/orden/rechazo de alteraciones; migración13→14 real; runtimeDML sinCREATE17.11. No sustituir por EF/DbUp. Referencia: [docs/REVISION-M3-CORRECCIONES-CODEX.md](REVISION-M3-CORRECCIONES-CODEX.md), [docs/REVISION-D14-05-CODEX.md](REVISION-D14-05-CODEX.md).
- **Origin/CSRF/cookies y cabeceras de seguridad existentes**: Origin exacto, CSRF ligado a sesión, HttpOnly/Strict/Secure fuera de Development, rate limiter; nuevas cabeceras/HSTS acotado DNSHTTPS. Secure navegador final tras MFA requiere F-12/C4. Referencia: [docs/IMPLEMENTACION-REV4.md](IMPLEMENTACION-REV4.md), [evidence/s1-20261021/rev4-fundamento/CIERRE.md](../evidence/s1-20261021/rev4-fundamento/CIERRE.md).
- **Panel, sesiones y auditoría21formas**: Altas guiadas, relacionesUUID, efectivos/origen, cierre por sesión pública y contexto mínimo21/21 con GUI, legacy notRecorded. Falta aceptación integral/cobertura fuera21. Referencia: [docs/C1-CONCILIACION-S38-S42.md](C1-CONCILIACION-S38-S42.md), [docs/INTEGRACION-ALTA-GRUPOS-WINDOWS-QA-S1.md](INTEGRACION-ALTA-GRUPOS-WINDOWS-QA-S1.md).
- **Núcleo backend MFA parcial**: Otp.NET/TOTP/cifrado;014; gate password→desafío y verify transaccional; reset/política/CSRF/caducidad corregidos. Scope excluye enrolamiento, códigos, D2provider, panel y GUI. Referencia: [docs/MFA-M2-RESULTADOS.md](MFA-M2-RESULTADOS.md), [docs/REVISION-M3-CORRECCIONES-CODEX.md](REVISION-M3-CORRECCIONES-CODEX.md).
- **Systemhaus/clientes; sitios/edificios/salas; racks/equipos; UUID, homónimos, permisos, revisión, idempotencia y persistencia.**: Implementado y probado por bloques; no rehacer CRUD ni iniciar otro piloto. Variantes y aceptación integral final aún pendientes. Referencia: [docs/MATRIZ-INVENTARIO-PENDIENTE.md](MATRIZ-INVENTARIO-PENDIENTE.md), [evidence/s1-20261017/quince-tandas-55-59/CIERRE.md](../evidence/s1-20261017/quince-tandas-55-59/CIERRE.md).
- **Movimiento/orden52, duplicado remapeado53 y borrado atómico1..64 equipos61.**: Implementado, probado y revisado. Drag/táctil y algunas variantes de duplicado no quedan acreditadas por esos recorridos. Referencia: [evidence/s1-20261017/tres-tandas-52/CIERRE.md](../evidence/s1-20261017/tres-tandas-52/CIERRE.md), [evidence/s1-20261017/tres-tandas-53/CIERRE.md](../evidence/s1-20261017/tres-tandas-53/CIERRE.md).
- **Edición de grupos +2/reducción con impacto; lotes por UUID/grupo/tipo; PoE OFF conserva watts; cara conserva identidad.**: Implementado y probado; no seleccionar lotes por gn ambiguo. No equivale a matriz completa de conectores/caras/roles. Referencia: [docs/C2-CONCILIACION-INVENTARIO.md](C2-CONCILIACION-INVENTARIO.md), [evidence/s1-20261017/tres-tandas-54/CIERRE.md](../evidence/s1-20261017/tres-tandas-54/CIERRE.md).
- **Click-Click/cross-rack, GUI lote57, reconexión, nota/color/cinco patch/desconexión58.**: Implementado y probado con un comando/commit atómico para lotes. La antigua ausencia de GUI lote en fila15 ya está cerrada. Referencia: [docs/GUI-LOTE-CONEXIONES-57.md](GUI-LOTE-CONEXIONES-57.md), [docs/QA-CONEXIONES-EDICION-58.md](QA-CONEXIONES-EDICION-58.md).
- **Atributos de puertos/PoE/watts; evidencia v1 y API inversas puras crecimiento/reducción.**: Atributos integrados históricamente; API C2 nueva probada/revisada acotadamente, adaptador incluido. Faltan GUI estructural e integración en candidata14; no undo/redo general. Referencia: [docs/API-COMPENSACION-POE-S1.md](API-COMPENSACION-POE-S1.md), [docs/C2-EVIDENCIA-GRUPOS-25-10-2026.md](C2-EVIDENCIA-GRUPOS-25-10-2026.md).
- **Dose/final en sala, puertos y cables sin rack/U ficticios; traslado entre salas62.**: Implementado, probado y revisado. No representa continuidad interna de toma pasante. Referencia: [evidence/s1-20261017/tres-tandas-62/CIERRE.md](../evidence/s1-20261017/tres-tandas-62/CIERRE.md), [docs/CONTRATO-INVENTARIO-S1.md](CONTRATO-INVENTARIO-S1.md).
- **Búsqueda, consultas puertos/cables y resumen PoE documental.**: Implementado, probado y revisado. Consulta no es export JSON ni backup. Referencia: [docs/API-CONSULTAS-INVENTARIO-S1.md](API-CONSULTAS-INVENTARIO-S1.md), [evidence/s1-20261017/quince-tandas-69-83/CIERRE.md](../evidence/s1-20261017/quince-tandas-69-83/CIERRE.md).
- **BASE33/7; favoritos BASE personales; privadas captura/retiro/rename/editor; publicación compartida por cliente y uso por otros.**: Implementado, probado y revisado, compartidas integradas Windows/QA10 históricamente. S-26 requiere aceptación completa; no crear publicación global ni acceso a privadas ajenas. Referencia: [docs/API-CATALOGO-BASE-S1.md](API-CATALOGO-BASE-S1.md), [docs/API-EDITOR-PLANTILLA-PRIVADA-S1.md](API-EDITOR-PLANTILLA-PRIVADA-S1.md).
- **Idioma/tema; paleta personal10tipos y28parejas de categorías.**: Implementado, probado/revisado e integrado históricamente Windows/QA11–13. Auditoría integral EN/DE/ES y accesibilidad pendiente. Referencia: [docs/INTEGRACION-ESQUEMA11-WINDOWS-QA-S1.md](INTEGRACION-ESQUEMA11-WINDOWS-QA-S1.md), [docs/INTEGRACION-PALETA-TIPOS-WINDOWS-QA-S1.md](INTEGRACION-PALETA-TIPOS-WINDOWS-QA-S1.md).
- **CSV/XLSX/HTML imprimible/SVG/XLS-HTML RC9; avisos multiusuario descriptivos.**: Implementado, probado/revisado e integrado históricamente. No sustituye export JSON/PDF nativo ni acredita carga10sesiones/aceptación final. Referencia: [docs/API-XLS-HTML-RC9-S1.md](API-XLS-HTML-RC9-S1.md), [docs/INTEGRACION-XLS-WINDOWS-QA-S1.md](INTEGRACION-XLS-WINDOWS-QA-S1.md).
- **Conversión/restauración RC9 en laboratorio con10clientes y original exacto.**: Implementado, probado y revisado. 10clientes/68racks/311equipos/5408puertos/623cables. No upload/preview/commit normal desde GUI/API. Referencia: [evidence/s1-20261004/rc9-restauracion-12/CIERRE.md](../evidence/s1-20261004/rc9-restauracion-12/CIERRE.md), [evidence/s1-20261020/arranque-y-datos-rc9/CIERRE.md](../evidence/s1-20261020/arranque-y-datos-rc9/CIERRE.md).

## F. Fundamento, seguridad y MFA · 25 puntos del cierre

### F-01 · Clasificar hallazgos de secretos y tratar sólo credenciales reales

**Situación:** F-01.01/.03 conservan su clasificación/registro técnico. F-01.02/.04 cerrados administrativamente por decisión expresa de Wascar03.11 y enmienda limitadav3: antecedente25.10 indeterminado y salida perdida, sin falso positivo, prueba de revocación ni cambios deD. Reabrir ambos y retirar5/4 si aparece evidencia concreta; no es higiene global ni aceptación de exposiciones futuras.

**Qué falta:**

- [x] F-01.01 · Clasificar candidatos e indeterminados privados con trazabilidad por ruta/commit y sin publicar valores.
- [x] F-01.02 · Si una credencial es real, coordinar revocación/rotación con la instancia afectada; corregir exposición y volver a verificar cambios/artefactos relevantes. Para el antecedente run-1 del25.10.2026 sin salida conservada, se admite sólo el archivo administrativo expreso documentado, con incertidumbre y reapertura obligatoria; no clasifica como falso positivo ni prueba revocación.
- [x] F-01.03 · Registrar falsos positivos y criterio específico sin supresiones amplias; reescritura de historial no está autorizada por defecto.
- [x] F-01.04 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Cada candidato/indeterminado tiene clasificación y resolución verificables; credenciales reales expuestas revocadas/rotadas de forma coordinada; comprobación focal de fuentes/paquete sin exposición. Excepción limitada al antecedente run-1 del25.10.2026 sin salida conservada: archivo administrativo expreso del titular con clasificación indeterminada y reapertura obligatoria si aparece evidencia concreta. No equivale a falso positivo, ausencia de exposición o revocación demostrada.

**Responsable:** Desarrollo: Clasificación, correcciones y verificación saneada; Wascar: Coordinar sólo una rotación que afecte instalaciones/credenciales bajo su control; Entorno: Acceso local privado a hallazgos; no enviar secretos al chat. **Dependencias:** Sin dependencia previa nueva identificada.

**Tipo de pendiente:** archivado administrativamente con incertidumbre residual. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** rev4 C.0; rev4 C.6; AGENTS: nunca versionar secretos/diagnósticos privados.

**Evidencia existente:** [docs/IMPLEMENTACION-REV4.md](IMPLEMENTACION-REV4.md), [evidence/s1-20261021/rev4-fundamento/CIERRE.md](../evidence/s1-20261021/rev4-fundamento/CIERRE.md), [evidence/s1-20261102/f01-01-clasificacion/RESULTADOS.md](../evidence/s1-20261102/f01-01-clasificacion/RESULTADOS.md). Todas las referencias e hitos separados están en elJSON.

### F-02 · Cifrar configuración SQL y recuperar sus secretos en otra instancia

**Situación:** F-02.01–.04 cerrados: postboot13, Restore14-r2 desde backup sintético LEAO hacia E con cuenta/SID/roles/material nuevos,20clientes SQL/API,operadores/ficha/diagnóstico/backup reales y reanudación sin regeneración. Windows no se reinició tras Restore14; ese pendiente sigue en los criterios Windows, sin adopción global. D se conserva y F01 tiene disposición administrativa posterior03.11, separada del cierre técnico.

**Qué falta:**

- [x] F-02.01 · Diseñar e integrar protección compatible con cuenta/instancia reales y canal mínimo de lectura para el servicio; conservar separación owner/migración/runtime.
- [x] F-02.02 · Actualizar operadores/fichas de acceso, diagnóstico y backup para no filtrar la clave ni depender de copiar un secreto ligado al host antiguo.
- [x] F-02.03 · Ensayar reanudación y Restore en destino nuevo con identidad/roles/claves nuevos; error explícito ante clave ausente/incorrecta.
- [x] F-02.04 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** El secreto SQL no queda en claro en el archivo entregado/configuración recuperable; servicio estándar arranca y Restore nuevo funciona mediante procedimiento documentado, sin secretos en logs/paquetes.

**Responsable:** Desarrollo: Implementación y pruebas; Wascar: Custodia operativa si el diseño necesita material de recuperación de su responsabilidad; Entorno: Windows destino nuevo y SID real de servicio. **Dependencias:** Coordinación C4/C5: cuenta de servicio y procedimiento de recuperación

**Tipo de pendiente:** cerrado técnicamente con revisión independiente. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** rev4 C.6; S-45; S-56.

**Evidencia existente:** [docs/IMPLEMENTACION-REV4.md](IMPLEMENTACION-REV4.md), [docs/RECUPERACION-DESPLIEGUE-WINDOWS-S1.md](RECUPERACION-DESPLIEGUE-WINDOWS-S1.md), [docs/REVISION-INSTALADOR14-06-CODEX.md](REVISION-INSTALADOR14-06-CODEX.md). Todas las referencias e hitos separados están en elJSON.

### F-03 · Registrar decisión de custodia y ubicación definitiva D2

**Situación:** Wascar confirmó25.10 la custodia externa del sobre/contraseña en medios separados, ubicación mfa-keys por instancia y recuperación restringida. Precisión técnica de KDF/publicación/ACL-SID e implementación siguen en el equipo; no hay otra autorización de arranque pendiente.

**Qué falta:**

- [x] F-03.01 · Wascar confirma responsable/medio del sobre y de su contraseña por canales privados, y ubicación definitiva del almacén mfa-keys.
- [ ] F-03.02 · Desarrollo concreta las condiciones técnicas de la revisión: recuperación restringida sin clave, límites/cabecera autenticada del KDF y publicación recuperable entre disco/DB.
- [ ] F-03.03 · Registrar límites de amenaza: DPAPI LocalMachine no aísla del administrador local ni del proceso de servicio comprometido.

**Se cierra cuando:** Decisión de Wascar identificada y especificación D2 final sin ambigüedad sobre responsables, almacén, pérdida total, recuperación y límites; revisión técnica separada de la aceptación operativa.

**Responsable:** Desarrollo: Cerrar especificación técnica revisable sin inventar la decisión de Wascar; Wascar: Confirmar custodia/ubicación definitivas; nunca enviar contraseña por el chat; Entorno: Ninguna ejecución necesaria para registrar la decisión. **Dependencias:** Sin dependencia previa nueva identificada.

**Tipo de pendiente:** decisión de custodia/recuperación confirmada; concreción técnica pendiente. **Peso:** 0,00 puntos. DecisiónD2: desbloquea F-04/F-05; sin crédito separado por aprobar desarrollo.

**Criterios:** rev4 C.5; rev4 C.6; AUTENTICACION-MFA-S1: custodia/restauración.

**Evidencia existente:** [docs/DECISION-D2-CUSTODIA-CLAVE-TOTP.md](DECISION-D2-CUSTODIA-CLAVE-TOTP.md), [docs/REVISION-D2-CODEX.md](REVISION-D2-CODEX.md), [docs/PLAN-MFA-Y-FRENTES-C1-C5.md](PLAN-MFA-Y-FRENTES-C1-C5.md). Todas las referencias e hitos separados están en elJSON.

### F-04 · Implementar proveedor TOTP Windows bajo la identidad real del servicio

**Situación:** En C Windows Server2025 limpia, candidata10 instala almacén dedicado e inicia proveedor Windows DPAPI bajo cuenta estándar SCM. Enrolamiento y nuevo login TOTP por HTTPS verificados antes y después del reinicio. Negativos de pérdida de clave/versión y arranque cerrado conciliados con las fuentes actuales. No se cierra la recuperación portable ni todos los negativos de ACL/otros tokens.

**Qué falta:**

- [ ] F-04.01 · Crear almacén separado de management con ACL seguras desde el primer instante y escrituras atómicas por instalador/operador.
- [ ] F-04.02 · Dar sólo lectura al SID efectivo del servicio y mantener management cerrado; comprobar padres, herencia y reparse.
- [x] F-04.03 · Conectar proveedor real al producto sólo tras D2; rechazar claves/versiones ausentes sin regeneración silenciosa ni password-only.
- [ ] F-04.04 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Servicio real lee/descifra y verifica factores; otra cuenta no lee, servicio no escribe ni modifica ACL, management no se amplía; negativos y revisión independiente registrados.

**Responsable:** Desarrollo: Proveedor, instalador, validadores y pruebas; Wascar: Aceptación de la custodia acordada; Entorno: Cuenta/SID estándar reales Windows; no basta roundtrip en proceso de desarrollador. **Dependencias:** F-03; C4: identidad estándar del servicio disponible

**Tipo de pendiente:** Proveedor real integrado en candidata10; F-04.03 cerrado, ACL/otros tokens y cierre total pendientes. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** rev4 C.5; rev4 C.6; S-43; S-45.

**Evidencia existente:** [development/server/src/RackClick.Server/Program.cs](../development/server/src/RackClick.Server/Program.cs), [development/server/src/RackClick.Server/MfaStore.cs](../development/server/src/RackClick.Server/MfaStore.cs), [development/server/src/RackClick.Server/MfaSecretCipher.cs](../development/server/src/RackClick.Server/MfaSecretCipher.cs). Todas las referencias e hitos separados están en elJSON.

### F-05 · Implementar sobre portable autenticado y restauración de claves

**Situación:** Formato RCKEY/PBKDF2/AES-GCM diseñado, no implementado/ensayado. Backup y Restore PostgreSQL existentes no prueban portabilidad del secreto TOTP.

**Qué falta:**

- [ ] F-05.01 · Validar magia/versión/algoritmo, tamaños, codificación canónica y límites min/max de iteraciones antes de KDF; autenticar cabecera completa como AAD.
- [ ] F-05.02 · Medir coste del parámetro propuesto600000 en Windows antes de fijarlo; no adoptarlo por silencio.
- [ ] F-05.03 · Probar contraseña errónea, alteración, truncado, datos extra, versión/algoritmo desconocidos y coste/tamaño fuera de rango.
- [ ] F-05.04 · Recuperar anillo en otra instancia Windows preservando AAD Systemhaus/usuario/versión o mediante reenvoltura explícita; sobre y contraseña separados del dump.
- [ ] F-05.05 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Restore nuevo verifica factores usando clave recuperada; sin material/contraseña correctos falla explícitamente, sin emitir sesión insegura; negativos y revisión independiente.

**Responsable:** Desarrollo: Formato, operadores y ensayos portables; Wascar: Custodia y aceptación del procedimiento; Entorno: Otro host/instancia Windows nuevo con identidad de servicio. **Dependencias:** F-03; F-04

**Tipo de pendiente:** implementación. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** rev4 C.5; rev4 C.15; S-45; M6.

**Evidencia existente:** [docs/DECISION-D2-CUSTODIA-CLAVE-TOTP.md](DECISION-D2-CUSTODIA-CLAVE-TOTP.md), [docs/REVISION-D2-CODEX.md](REVISION-D2-CODEX.md), [docs/AUTENTICACION-MFA-S1.md](AUTENTICACION-MFA-S1.md). Todas las referencias e hitos separados están en elJSON.

### F-06 · Cerrar rotación y recuperación coherente entre anillo y PostgreSQL

**Situación:** Anillo versionado/rotación propuestos; atomicidad de un archivo no cubre publicación de claves más commit DB.

**Qué falta:**

- [ ] F-06.01 · Especificar fases: persistir/verificar clave nueva antes de usarla, conservar versiones requeridas, reenvolver factores y publicar anillo coherente.
- [ ] F-06.02 · Retirar una versión sólo si ningún factor ni backup retenido la necesita; incluir inventario de versiones en backup/sobre.
- [ ] F-06.03 · Inyectar caída antes/después de cada publicación y commit; reinicio/Restore deben identificar estado y recuperar sin perder factores.
- [ ] F-06.04 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Cada punto de interrupción tiene estado recuperable demostrado; todos los factores/backups retenidos siguen descifrables con versiones conservadas y faltantes se rechazan explícitamente.

**Responsable:** Desarrollo: Implementación, protocolo y prueba; Wascar: Operación/custodia según D2; Entorno: Laboratorio Windows/PG con fallos controlados. **Dependencias:** F-04; F-05

**Tipo de pendiente:** implementación. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** rev4 C.5; rev4 C.6; D2 §5; S-45; S-46.

**Evidencia existente:** [docs/DECISION-D2-CUSTODIA-CLAVE-TOTP.md](DECISION-D2-CUSTODIA-CLAVE-TOTP.md), [docs/REVISION-D2-CODEX.md](REVISION-D2-CODEX.md). Todas las referencias e hitos separados están en elJSON.

### F-07 · Completar enrolamiento restringido cuando MFA sea exigible

**Situación:** Dashboard45 y enrolamiento integrados en candidata10 instalada de laboratorio C. Proveedor Windows real, enrolamiento/confirmación y siguiente login verificados por HTTPS antes y después del reinicio. QA visual de Wascar, recuperación portable y cierre total F-07.05 pendientes; QA anterior y producción sin adoptar.

**Qué falta:**

- [x] F-07.01 · Después de password válido emitir desafío enroll de finalidad fija, hash/CSRF propio, cinco minutos y consumo único; sin app_session/autoridad API.
- [x] F-07.02 · Presentar secreto/QR sólo al usuario durante proceso, sin URL/log/auditoría/historial; confirmar primer TOTP antes de activar factor.
- [x] F-07.03 · Emitir sesión/CSRF nuevos y confirmar factor/consumir desafío en una sola transacción; revalidar cuenta/política/caducidad después de locks.
- [x] F-07.04 · Alta nueva conserva45días desdecreación y cuenta existente desdeactivación persistida; administrador globalSystemhaus exento; el servidor exige enrolamiento al vencer o al activar/exigirMFA; probar código erróneo/caducado/repetido, reintento/respuesta perdida y dos confirmaciones concurrentes.
- [ ] F-07.05 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Usuario nuevo completa primer factor y obtiene única sesión nueva sólo al confirmar; desafío/enrolamiento incompleto no acceden a /me, clientes ni mutaciones; negativos concurrentes y revisión independiente.

**Responsable:** Desarrollo: API, estado de alta, transacciones y pruebas; Wascar: QA posterior del primer inicio; Entorno: PostgreSQL real y navegador para integración. **Dependencias:** F-04 para producto; proveedor sintético aislado puede permitir desarrollo/pruebas previas

**Tipo de pendiente:** F-07.01 a .04 cerrados técnicamente en laboratorio; candidata, custodia real integrada y cierre .05 pendientes. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** rev4 C.5; D3; M3; S-04; S-05; S-43.

**Evidencia existente:** [docs/MFA-M3-RESULTADOS.md](MFA-M3-RESULTADOS.md), [docs/AUTENTICACION-MFA-S1.md](AUTENTICACION-MFA-S1.md), [docs/MFA-M2-RESULTADOS.md](MFA-M2-RESULTADOS.md). Todas las referencias e hitos separados están en elJSON.

### F-08 · Implementar códigos de recuperación y reenrolamiento restringido

**Situación:** Tabla app_mfa_recovery_code existe; generación/entrega/consumo y transición posterior no demostrados como flujo de producto.

**Qué falta:**

- [ ] F-08.01 · Generar y mostrar una sola vez códigos por usuario; almacenar sólo hashes con sal conforme D2, sin dependencia de clave TOTP.
- [ ] F-08.02 · Concretar e implementar si password+código concede sólo recuperación restringida hasta reenrolar; no dejar frase ambigua que emita sesión normal antes de nuevo factor.
- [ ] F-08.03 · Consumir transaccionalmente, invalidar sesiones/desafíos/códigos anteriores según contrato y probar consumo concurrente/replay/rollback/secretos.
- [ ] F-08.04 · Garantizar vía administrativa de recuperación con códigos válidos sin bloquear último administrador.
- [ ] F-08.05 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Cada código sirve una sola vez incluso en concurrencia; recuperación no abre API antes del estado autorizado; reenrolamiento y revocación/auditoría sin secretos probados por revisor distinto.

**Responsable:** Desarrollo: Transición, código y pruebas; Wascar: Custodia privada de códigos y QA; Entorno: PG real/navegador y cuentas sintéticas. **Dependencias:** F-07; F-10

**Tipo de pendiente:** implementación. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** rev4 C.5; D2 §3a; M4; S-05; S-41; S-42.

**Evidencia existente:** [development/server/database/014-mfa.sql](../development/server/database/014-mfa.sql), [docs/DECISION-D2-CUSTODIA-CLAVE-TOTP.md](DECISION-D2-CUSTODIA-CLAVE-TOTP.md), [docs/REVISION-D2-CODEX.md](REVISION-D2-CODEX.md). Todas las referencias e hitos separados están en elJSON.

### F-09 · Implementar recuperación local cuando no quedan clave, sobre ni códigos

**Situación:** La recuperación CLI actual revoca sesiones y desafíos; D14-05 lo acredita. No equivale al flujo local de emergencia de pérdida total MFA.

**Qué falta:**

- [ ] F-09.01 · Autorizar sólo operador local SYSTEM/Administradores; sin web anónima ni bypass password-only.
- [ ] F-09.02 · Permitir preparar anillo nuevo explícitamente, conservar material anterior recuperable, retirar factores ilegibles del uso y marcar enrolamiento pendiente sin borrar DB.
- [ ] F-09.03 · Revocar sesiones/desafíos y registrar auditoría sin secretos, preservando recuperación de último administrador.
- [ ] F-09.04 · Ensayar pérdida simulada total, arranque fallido explícito, recuperación local y vuelta mediante enrolamiento restringido.
- [ ] F-09.05 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Administrador recupera acceso mediante enrolamiento nuevo después de pérdida total simulada; no se borra inventario ni se reactivan sesiones; ninguna ruta remota permite eludir factor.

**Responsable:** Desarrollo: CLI/protocolo/tests y manual; Wascar: Responsable operativo/custodia y QA; Entorno: Host Windows nuevo y permisos locales controlados. **Dependencias:** F-03; F-04; F-07

**Tipo de pendiente:** implementación. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** rev4 C.5; D2 §3b y §6; M6; S-40; S-41; S-45; S-56.

**Evidencia existente:** [docs/REVISION-D14-05-CODEX.md](REVISION-D14-05-CODEX.md), [docs/DECISION-D2-CUSTODIA-CLAVE-TOTP.md](DECISION-D2-CUSTODIA-CLAVE-TOTP.md), [docs/REVISION-D2-CODEX.md](REVISION-D2-CODEX.md). Todas las referencias e hitos separados están en elJSON.

### F-10 · Completar panel/política MFA por usuario y obligatoriedad antes de producción

**Situación:** SQL de política y gate de login existen. No hay interruptor/reset MFA M4 de producto; excepción del administrador es temporal de QA. MFA para todos antes de producción ya está decidido.

**Qué falta:**

- [ ] F-10.01 · Implementar API/panel de activar/desactivar y reset MFA con capacidad global vigente, revisión/idempotencia, auditoría y protección del último administrador.
- [ ] F-10.02 · Cambios revocan sesiones/desafíos y no permiten elevar una sesión password-only tras nueva concesión; probar cambios concurrentes y rollback.
- [ ] F-10.03 · Concretar transición de cuentas existentes y altas nuevas; registrar cómo se elimina excepción D7.
- [ ] F-10.04 · Antes de producción aplicar MFA a todos, incluidos lector/admin, revocar password-only y comprobar que no hay alternativa de login inseguro.
- [ ] F-10.05 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Panel y servidor cumplen política por usuario con sesiones/revisión/último admin protegidos; transición de producción obliga factor a todos y sus negativos están revisados. No pedir otra decisión sobre la obligatoriedad ya confirmada.

**Responsable:** Desarrollo: Panel, APIs, política y pruebas; Wascar: QA/aceptación del comportamiento y cierre de excepción de pruebas; Entorno: PG real y candidata coherente. **Dependencias:** F-07; F-08; F-09; F-11

**Tipo de pendiente:** implementación. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** rev4 C.5; D3; D7; M4; S-38; S-40; S-41; S-42.

**Evidencia existente:** [docs/PLAN-MFA-Y-FRENTES-C1-C5.md](PLAN-MFA-Y-FRENTES-C1-C5.md), [docs/METODOLOGIA-PARA-CLAUDE.md](METODOLOGIA-PARA-CLAUDE.md), [docs/IMPLEMENTACION-REV4.md](IMPLEMENTACION-REV4.md). Todas las referencias e hitos separados están en elJSON.

### F-11 · Integrar segundo paso y todos los formularios de reautenticación

**Situación:** RackClickApi.login sigue password→csrf→me; no gestiona202 como desafío. La GUI RC9 vigente no ofrece MFA.

**Qué falta:**

- [ ] F-11.01 · Coordinador de autenticación termina login/enrolamiento/verificación/recuperación antes de entregar Session al resto de la GUI.
- [ ] F-11.02 · Integrar reauth de operaciones inciertas, usuarios/password/estado/sesiones, favoritos, plantillas, preferencias y paletas; continuar sólo mismo actor.
- [ ] F-11.03 · Conservar borradores/journal/intención y no reenviar escritura bajo otra identidad; tratar pérdida de respuesta, caducidad/recarga y segunda sesión.
- [ ] F-11.04 · Mantener aspecto RC9 y EN/DE/ES; catálogo con pasos exactos y estado no disponible hasta integración real, regenerar guía cuando corresponda sin alterar observaciones.
- [ ] F-11.05 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Login y cada familia de reauth completan factor para mismo actor, conservan borrador y recuperan respuesta sin duplicar; navegador/ENDEES revisados antes de habilitar QA.

**Responsable:** Desarrollo: Adaptador, UI, pruebas navegador y guía; Wascar: QA funcional de login/reauth; Entorno: Navegador real y candidata/instancia identificadas. **Dependencias:** F-07; F-08; F-10

**Tipo de pendiente:** integración. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** rev4 C.5; M5; S-05; S-25; S-27; S-28; S-47.

**Evidencia existente:** [development/frontend/src/api.ts](../development/frontend/src/api.ts), [docs/AUTENTICACION-MFA-S1.md](AUTENTICACION-MFA-S1.md), [docs/PLAN-MFA-Y-FRENTES-C1-C5.md](PLAN-MFA-Y-FRENTES-C1-C5.md). Todas las referencias e hitos separados están en elJSON.

### F-12 · Acreditar MFA y fundamento sobre la candidata completa por HTTP/HTTPS

**Situación:** HTTP y GUI MFA/gracia45 revisados en laboratorio15; Browser8etapasPASS y Quality378PASS/1Dockeromitida. Proveedor sintético de DI separado, no custodia productiva final/HTTPS de la candidata. F-12.03/.04/.05 pendientes.

**Qué falta:**

- [ ] F-12.01 · Fijar conjunto aplicación/SQL/frontend/dependencias/operadores y un proveedor de laboratorio controlado explícitamente separado de custodia productiva D2; no bloquear pruebas sintéticas por decisión de custodia aún abierta.
- [ ] F-12.02 · Comprobar por HTTP desafío202 sin sesión, finalidad/rutas exactas, CSRF/Origin/rate/cookies, intentos/replay/concurrencia/caducidad tras última espera y reset/política/restore.
- [ ] F-12.03 · Con proveedor real final comprobar HTTPS/Secure en navegador y regresión afectada después de MFA, sin trasladar pruebas por similitud de DLL.
- [ ] F-12.04 · Revisión final acotada por rutas: SQL externo parametrizado/identificadores cerrados, datos hostiles literales DOM/SVG/reportes, autorización lectura/escritura, secretos y roles runtime DML sin DDL. SAST complementa, no sustituye pruebas negativas.
- [ ] F-12.05 · Actualizar guiones/evidencias de candidata y obtener revisión independiente antes de habilitar MFA en QA.

**Se cierra cuando:** Evidencia identifica bytes/esquema/proveedor/entorno y demuestra flujos positivos/negativos MFA completos más controles afectados; ninguna omisión pasa por éxito, sin anunciar QA/producción por pruebas del almacén.

**Responsable:** Desarrollo: Composición, matriz de rutas, regresiones pertinentes y revisión independiente; Wascar: QA/adopción posterior; Entorno: PG17 real, HTTPS/navegador y laboratorio Windows nuevo. **Dependencias:** F-04 para producción; proveedor sintético permite ensayo previo; F-07; F-08; F-09; F-10; F-11; C4/C5: corregir y ensayar cadena de instalador/runtime

**Tipo de pendiente:** integración HTTP de L1 revisada; matriz final de seguridad pendiente. **Peso:** 0,00 puntos. Regresión transversal: se acredita una sola vez en los subpasos técnicos afectados y E-07.

**Criterios:** rev4 C.0; rev4 C.5; rev4 C.13; rev4 C.17; S-04; S-05; S-06; S-07; S-21; S-27; S-28; S-29; S-42; S-43; S-49.

**Evidencia existente:** [evidence/s1-20261023/distribucion14-decision/CIERRE.md](../evidence/s1-20261023/distribucion14-decision/CIERRE.md), [docs/REVISION-M3-CORRECCIONES-CODEX.md](REVISION-M3-CORRECCIONES-CODEX.md), [docs/REVISION-D14-05-CODEX.md](REVISION-D14-05-CODEX.md). Todas las referencias e hitos separados están en elJSON.


## I. Jerarquía, inventario y colaboración · 15 puntos del cierre

### I-01 · Ofrecer e integrar Deshacer de crecimiento/reducción pura de grupos

**Situación:** I-01.01/02/03/04 completos técnicamente en laboratorio. Consulta, reintento y cancelación originales; invalidación por revisión, permiso, cuenta y cliente con vías de diálogo/edición rápida protegidas. Ensayo READ sin EDIT con Edge/PostgreSQL 17.11 PASS 21,83 s y revisión distinta de la matriz acumulada. I-01.05/06/07 pendientes: candidata coordinada, QA disponible y cierre del resultado completo.

**Qué falta:**

- [x] I-01.01 · Crear candidato desde operación confirmada propia, actor/cliente/revisión; ningún before del navegador.
- [x] I-01.02 · Mostrar alcance/confirmación de retirar/restaurar grupos/puertos/cables y límites de evidencia completa1..256puertos/32grupos/256IDs combinados.
- [x] I-01.03 · Integrar consulta/reintento/cancelación originales ante incertidumbre e invalidación tras otra revisión/permiso/cuenta/cliente.
- [x] I-01.04 · Decidir presentación de contexto estructural: hoy notAvailable explícito; no rotular puertos eliminados como changedIds.
- [ ] I-01.05 · Congelar candidata coordinada con MFA/instalación y probar API+GUI sobre sus bytes; revisión distinta.
- [ ] I-01.06 · Añadir guiones por botón/campo, habilitados sólo en candidata seleccionada real; conservar resultados.
- [ ] I-01.07 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Ambas inversas puras funcionan en GUI con UUID/atributos/fechas/extremos exactos; conflictos/revocación/replay/rollback sin pérdida ni éxito falso; build/hash, prueba, revisión distinta y QA registrados.

**Responsable:** Responsables: Backend/frontend; Revisor independiente para cierre técnico; Wascar para aceptación. **Dependencias:** Candidata14/MFA estable coordinada

**Tipo de pendiente:** parcial; candidato y confirmación GUI revisados en laboratorio. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-13; S-14; S-30; CRev4 C.0/C.10.

**Evidencia existente:** [docs/C2-EVIDENCIA-GRUPOS-25-10-2026.md](C2-EVIDENCIA-GRUPOS-25-10-2026.md), [docs/C2-INVERSA-CRECIMIENTO-25-10-2026.md](C2-INVERSA-CRECIMIENTO-25-10-2026.md), [docs/C2-INVERSA-REDUCCION-25-10-2026.md](C2-INVERSA-REDUCCION-25-10-2026.md). Todas las referencias e hitos separados están en elJSON.

### I-02 · Cerrar alcance restante de compensación colaborativa y Rehacer

**Situación:** implementacion: Existen atributos seis campos/aliasRJ45 y API puras de grupos. No undo general/redo; mixtos/reordenamientos, roles/properties, mover/borrar/conexiones carecen de inversa general.; integracion: Atributos integrados históricamente; puras fuera de14.; prueba: Rechazos seguros y pruebas acotadas no cumplen inversas faltantes.; revision: Sin revisión de catálogo completo de compensaciones.; qa: QA36/59 atributos; no aceptación del contrato general.

**Qué falta:**

- [ ] I-02.01 · Fijar catálogo finito y semántica de Rehacer; no copiar historial offline30niveles ni suponer cualquier inversa de cualquier comando.
- [ ] I-02.02 · Definir evidencia/consentimiento nuevo para grupos mixtos/reordenados y extremos reservados hoy rechazados.
- [ ] I-02.03 · Por cada inversa incluida: comparar after completo/estado actual, identidad, revisión, autorización y locks; no UPSERT ni desplazar cables actuales.
- [ ] I-02.04 · Implementar alcance contractual pendiente. Un recorte requiere decisión expresa de Wascar.
- [ ] I-02.05 · Probar cambios ajenos, reutilización UUID, evidencia corrupta, concurrencia/replay/rollback; integrar GUI/manual y revisión distinta.
- [ ] I-02.06 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Tabla completa soportado/no soportado y motivo; toda inversa prometida tiene prueba de cambios ajenos y QA; un rechazo422 nunca se cuenta como undo cumplido.

**Responsable:** Responsables: Producto/arquitectura; Backend/frontend; Revisor independiente; Wascar para recortes y aceptación. **Dependencias:** I-01; Decisión expresa si se propone limitar Undo/Redo

**Tipo de pendiente:** definición finita e implementación. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-14; S-30; CONTRATO §6 Undo/redo.

**Evidencia existente:** [docs/CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md), [docs/C2-CONCILIACION-INVENTARIO.md](C2-CONCILIACION-INVENTARIO.md), [docs/API-COMPENSACION-POE-S1.md](API-COMPENSACION-POE-S1.md). Todas las referencias e hitos separados están en elJSON.

### I-03 · Cerrar matriz RC9 de conector, cara, rol eléctrico y presupuesto PoE

**Situación:** implementacion: UUID/grupo/tipo, PoE OFF/null≠0, cara única, roles AC y resumen agregado ya existen. Pair no exige igualdad universal de familias de datos ni presupuesto agregado.; integracion: Integradas históricamente QA13; combinación14 final sin acreditar.; prueba: 54-C/23.10 casos concretos;63–68 resumen. Sin matriz completa de presets/conectores/caras/roles.; revision: Favorable acotada; no matriz integral.; qa: QA27/35/59; S-23 visual parcial.

**Qué falta:**

- [ ] I-03.01 · Enumerar combinaciones realmente soportadas por RC9adoptada: tipo/grupo, auto/front/rear, inlet/outlet/unspecified y presets.
- [ ] I-03.02 · Marcar soporte/rechazo/límite; no imponer compatibilidad física nueva por intuición.
- [ ] I-03.03 · Cubrir grupos gn repetidos, conservación al editar y revalidación de enlaces al cambiar rol.
- [ ] I-03.04 · Presupuesto nulo/cero/límite/excedido y watts heterogéneos/desconocidos, OFF/AC excluidos. No nueva restricción de suministro sin contrato.
- [ ] I-03.05 · Recorrido frontal/trasera persistente sobre candidata final, errores atómicos y revisión distinta.
- [ ] I-03.06 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Matriz finita sin huecos para combinaciones prometidas, ligada a evidencia o límite explícito; identidad/cables persisten. No certificación de circuito/medio/transceptor/suministro.

**Responsable:** Responsables: Network/producto; Backend/frontend si hay defectos; Revisor distinto y Wascar. **Dependencias:** Referencia RC9 inmutable; Candidata integrada

**Tipo de pendiente:** cobertura y corrección sólo de defectos reproducidos. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-13; S-22; S-23; CRev4 C.0/C.10.

**Evidencia existente:** [docs/C2-CONCILIACION-INVENTARIO.md](C2-CONCILIACION-INVENTARIO.md), [docs/CONTRATO-INVENTARIO-S1.md](CONTRATO-INVENTARIO-S1.md), [evidence/s1-20261017/tres-tandas-54/CIERRE.md](../evidence/s1-20261017/tres-tandas-54/CIERRE.md). Todas las referencias e hitos separados están en elJSON.

### I-04 · Cerrar variantes de jerarquía, racks, equipos y orden ya implementados

**Situación:** I-04.01–05 completos técnicamente en laboratorio. Borrado individual de final conectado y lote Dose+equipo: cinco conjuntos de impacto exactos, cancelaciones SQL/operaciones/auditoría intactas, dos commits y cable ajeno conservado. Regresión de lote, permisos/replay/conflicto y persistencia comprobados. I-04.06/07 pendientes: candidata final integrada, revisión y aceptación.

**Qué falta:**

- [x] I-04.01 · Cerrar lista de controles/comandos existentes y reutilizar prueba; no rehacer lotes ni CRUD por tabla51.
- [x] I-04.02 · Focos de editar/reasignar rack, reducciónU con ocupación, equipo/metadatos/presets y tooltips por UUID/homónimos.
- [x] I-04.03 · Duplicado sin/con cables y reserved confirmado válido; conservar negativos existentes.
- [x] I-04.04 · Flechas/drag/táctil según controles ofrecidos; orden documental y local/cross sin inventar posiciónU.
- [x] I-04.05 · Borrado individual/conjunto con objetos de sala y cables incidentes: commit único, impacto/cancelación exactos.
- [ ] I-04.06 · Repetir sólo focos afectados en candidata final con segunda cuenta/reinicio; revisión y guiones faltantes.
- [ ] I-04.07 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Cada operación ofrecida tiene trayectoria positiva/negativos pertinentes por versión; huecos de evidencia cerrados sin declarar funciones inexistentes; QA visible de Wascar.

**Responsable:** Responsables: Inventario/frontend y QA; Revisor independiente; Wascar. **Dependencias:** I-06; Candidata estable

**Tipo de pendiente:** parcial; catálogo, variantes de rack y duplicado revisados en laboratorio. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-08; S-09; S-10; S-11; S-12; S-24; S-25; S-27; S-28; S-29.

**Evidencia existente:** [docs/MATRIZ-INVENTARIO-PENDIENTE.md](MATRIZ-INVENTARIO-PENDIENTE.md), [evidence/s1-20261017/tres-tandas-52/CIERRE.md](../evidence/s1-20261017/tres-tandas-52/CIERRE.md), [evidence/s1-20261017/tres-tandas-53/CIERRE.md](../evidence/s1-20261017/tres-tandas-53/CIERRE.md). Todas las referencias e hitos separados están en elJSON.

### I-05 · Cerrar variantes de Click-Click, lotes, reconexión y cables

**Situación:** implementacion: Todas las familias existen, incluida GUI57 de pares atómicos y cinco patch/nota/color/desconexión58.; integracion: Históricamente QA29/30; combinación14 no probada por esas ejecuciones.; prueba: PG competencia/uncommit/ámbitos; GUI incertidumbre/reserved/412 y edición. No matriz visual completa cross/roles/carreras/reconexión reservada/cancelar.; revision: Acotada y con atribución de recorridos realmente repetidos.; qa: Casos disponibles históricos no equivalen a aprobación.

**Qué falta:**

- [ ] I-05.01 · Matriz local/cross/sala y reserved positivo/negativo con origen revalidado.
- [ ] I-05.02 · Reconexión cancelada y a ocupado/disabled/faulty/reserved/ajeno conserva UUID/atributos/extremo previo.
- [ ] I-05.03 · Dos técnicos en GUI: un éxito y conflicto explicado sin borrador perdido; aprovechar prueba API existente.
- [ ] I-05.04 · Precedencia color manual y literalidad de notas/labels en UI e informes EN/DE/ES.
- [ ] I-05.05 · Corregir sólo fallos reproducidos y registrar build/pruebas/revisión/QA.
- [ ] I-05.06 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Todas las variantes prometidas conservan extremos/identidad/atributos, atomicidad y Click-Click; pruebas/revisión y QA visibles vinculados a versión.

**Responsable:** Responsables: Backend/frontend/network; Revisor QA distinto; Wascar. **Dependencias:** I-03; P-10; Candidata final

**Tipo de pendiente:** cobertura y aceptación. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-15; S-16; S-17; S-18; S-19; S-20; S-21; S-23; CRev4 C.0.

**Evidencia existente:** [docs/GUI-LOTE-CONEXIONES-57.md](GUI-LOTE-CONEXIONES-57.md), [docs/QA-CONEXIONES-EDICION-58.md](QA-CONEXIONES-EDICION-58.md), [evidence/s1-20260928/impacto-reconexion-04/CIERRE.md](../evidence/s1-20260928/impacto-reconexion-04/CIERRE.md). Todas las referencias e hitos separados están en elJSON.

### I-06 · Completar verificación de Dosen y finales ya soportados en sala

**Situación:** I-06.02 cerrado técnicamente: Edge/PG17.11 PASS32,719s,16 commits para todos los campos ofrecidos en Dose/final, roles power en puertos sin cable, gn repetido por grupo/ID, metadatos/cables exactos,7 rechazos atómicos y persistencia. Regresión edición nueva PASS27,562s. Revisión distinta3focos/13mutaciones. Borrado individual/conjunto con impacto aceptado en I-04.05, evidencia anterior identificada. No completa soporte/plantillas/AP, rutas/informes/revocación, ocupación lógica, integración o QA de I-06.

**Qué falta:**

- [ ] I-06.01 · Relacionar soporte real por operación/plantilla/AP y conservarlo.
- [x] I-06.02 · Cerrar edición/renombrado/puertos/roles/borrado con impacto de objetos de sala ofrecidos por GUI.
- [ ] I-06.03 · Verificar extremos/rutas en consultas, informes y avisos tras mover y revocar permisos.
- [ ] I-06.04 · Documentar una ocupación por puerto lógico y separar I-07.
- [ ] I-06.05 · Si se propone aplazar, decisión expresa de Wascar; no inferirla del PLAN contradictorio.
- [ ] I-06.06 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Operaciones externas de Dose/final probadas como objetos de sala con topología/ámbitos exactos y QA; cualquier aplazamiento tiene decisión expresa.

**Responsable:** Responsables: Network/producto; Backend/frontend; Revisor independiente; Wascar. **Dependencias:** I-03; I-04; I-05; P-06/P-07

**Tipo de pendiente:** edición, puertos, roles y borrado GUI verificados técnicamente; matriz restante pendiente. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-07; S-21; S-23; S-24; CONTRATO Dose/final.

**Evidencia existente:** [docs/CONTRATO-INVENTARIO-S1.md](CONTRATO-INVENTARIO-S1.md), [docs/GUI-TRASLADO-SALA-S1.md](GUI-TRASLADO-SALA-S1.md), [evidence/s1-20261017/tres-tandas-62/CIERRE.md](../evidence/s1-20261017/tres-tandas-62/CIERRE.md). Todas las referencias e hitos separados están en elJSON.

### I-07 · Decidir modelo de terminales y pasos internos de Dose/panel

**Situación:** implementacion: No modelo acordado/implementado de entrada fija+salida latiguillo simultáneas; face no crea terminal.; integracion: No integrado por falta de contrato físico explícito.; prueba: Conexiones externas no demuestran continuidad interna.; revision: Sin diseño pasante adoptado.; qa: No anunciado/disponible como ruta completa.

**Qué falta:**

- [ ] I-07.01 · Acordar ejemplos físicos requeridos, separando datos/PoE/AC.
- [ ] I-07.02 · Definir identidades de terminal/paso, ocupación y Click-Click antes de código.
- [ ] I-07.03 · Decidir si la primera entrega promete ruta pasante o límite expreso; separado de Dose/final ya requerido.
- [ ] I-07.04 · Sólo si incluido: diseño/migración y pruebas dos enlaces externos+paso interno sin doble ocupación ambigua; revisión network/arquitectura.

**Se cierra cuando:** Decisión trazable soporte/límite revisada. Si incluida, implementación/pruebas/QA propias. No deducir continuidad por una cara ni bloquear automáticamente CRUD externo.

**Responsable:** Responsables: Wascar para necesidad/límite; Network/arquitectura; Equipo sólo para alcance acordado. **Dependencias:** Decisión física de Wascar

**Tipo de pendiente:** decisión física y diseño condicional. **Peso:** 0,00 puntos. Modelo físico interno no confirmado paraS1–S4; investigación/decisión registrada fuera de los100puntos.

**Criterios:** CONTRATO §4; CONTRATO-INVENTARIO incertidumbre Dose; S-23 si se promete ruta pasante.

**Evidencia existente:** [docs/CONTRATO-INVENTARIO-S1.md](CONTRATO-INVENTARIO-S1.md), [docs/CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md), [docs/C2-CONCILIACION-INVENTARIO.md](C2-CONCILIACION-INVENTARIO.md). Todas las referencias e hitos separados están en elJSON.


## A. Usuarios, grupos y administración · 5 puntos del cierre

### A-01 · Cerrar atribución técnica C1 S-38 a S-42 en la candidata vigente

**Situación:** API y panel ya existen, con pruebas históricas y regresión C1 10/10 M3 db5aa9. No está demostrado un defecto nuevo de esos mecanismos; tampoco se transfieren a app03/VM por defecto.

**Qué falta:**

- [ ] A-01.01 · Registrar candidata/DDL/GUI/instancia y relación de fuentes con pruebas C1 existentes.
- [ ] A-01.02 · Después de cambios MFA ejecutar sólo focos afectados: misma sesión tras retirar última vía, unión de concesiones, último admin y suplente activo/global, password/reset/desactivación/reactivación, revocación de tokens/desafíos y replay que conserva sesión nueva.
- [ ] A-01.03 · Mantener commit conjunto/revisión/operation/audit y negativos de fallo; comprobar logs capturados con marcadores sintéticos tras añadir factor/recuperación.
- [ ] A-01.04 · Revisión distinta y matriz criterio→ejecución/build/resultado/límite; no forzar fallos de último admin en cuentas reales.
- [ ] A-01.05 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** S-38..42 tienen atribución actual y regresión pertinente posterior a cambios, conservando límites. Logs stdout/stderr ya ensayados no se declaran universalmente ausentes de secretos.

**Responsable:** Desarrollo: Identidad de fuentes y validación focal/revisión; Wascar: No sustituye aceptación visual A-02; Entorno: Laboratorio nuevo con cuentas sintéticas; no credenciales reales. **Dependencias:** F-10; F-11; F-12

**Tipo de pendiente:** probado_acotado. **Peso:** 1,25 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-38; S-39; S-40; S-41; S-42.

**Evidencia existente:** [docs/C1-CONCILIACION-S38-S42.md](C1-CONCILIACION-S38-S42.md), [docs/REVISION-M3-CORRECCIONES-CODEX.md](REVISION-M3-CORRECCIONES-CODEX.md), [evidence/s1-20261023/c1-logs-d2/REVISION.md](../evidence/s1-20261023/c1-logs-d2/REVISION.md). Todas las referencias e hitos separados están en elJSON.

### A-02 · Completar aceptación visual del recorrido administrativo existente

**Situación:** Alta guiada, grupos de personas/clientes separados, relaciones UUID, efectivos con origen, sesiones y auditoría ya implementados/integrados históricamente. Preview administración-arbol no certifica producto ni sustituye estos recorridos.

**Qué falta:**

- [ ] A-02.01 · Wascar recorre usuario→pertenencias→efectivos y grupo→miembros/concesiones; ambas clases de grupo, homónimos y varios padres explícitos sin herencia AD.
- [ ] A-02.02 · Comprobar retiro con sesión abierta y actualización de lectura/escritura sin logout; S-38 no exige push universal que borre todo dato ya renderizado.
- [ ] A-02.03 · Recorrer reset/estado/sesiones/auditoría y altas/navegación; registrar lugar exacto donde haya pérdida de contexto, legibilidad o accesibilidad, versión y navegador.
- [ ] A-02.04 · Conservar resultados previos y marcar cambios de versión; corregir sólo observaciones concretas y repetir focos. Probar teclado/voz habitual en su ámbito sin rediseñar RC9.
- [ ] A-02.05 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Resultados por caso/build conservados y observaciones administrativas resueltas/aceptadas expresamente por Wascar. Disponible no equivale a Pass; relación/árbol no se reinventa como AD.

**Responsable:** Desarrollo: Preparar guiones/cuentas, corregir defectos y documentar disponibilidad; Wascar: Ejecutar/aceptar recorrido visual y observaciones; Entorno: Instancia/browsers concretos; no trasladar cuentas preparadas de LEAO a VM. **Dependencias:** A-01; F-11; C4: candidata/instancia QA seleccionada y guiones disponibles

**Tipo de pendiente:** aceptación. **Peso:** 1,25 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-38; S-39; S-41; S-42; S-47; rev4 C.19.

**Evidencia existente:** [docs/C1-CONCILIACION-S38-S42.md](C1-CONCILIACION-S38-S42.md), [docs/UX-ADMINISTRACION-ARBOL.md](UX-ADMINISTRACION-ARBOL.md), [docs/INTEGRACION-ALTA-GRUPOS-WINDOWS-QA-S1.md](INTEGRACION-ALTA-GRUPOS-WINDOWS-QA-S1.md). Todas las referencias e hitos separados están en elJSON.

### A-03 · Conciliar y cerrar atribución de auditoría fuera de las21formas administrativas

**Situación:** 21formas ya capturan contexto mínimo y tienen GUI tipada. El mapa mantiene parcial cobertura/atribución de otras acciones, especialmente inventario/intercambio/operación; no hay autorización para rellenar histórico ausente.

**Qué falta:**

- [ ] A-03.01 · Enumerar acciones actuales fuera21 y contrastar actorUUID, cliente/ámbito cuando aplica, objetos directos, horaUTC, revisiones, outcome y request contra lo realmente capturado/publicado.
- [ ] A-03.02 · Registrar diferencia concreta por acción; implementar sólo atribución mínima faltante con fallo que revierta mutation/operation/audit, sin JSON arbitrario/secretos.
- [ ] A-03.03 · Verificar lectura honesta y aislamiento/rollback/replay de familias afectadas; contexto antiguo ausente permanece notRecorded.
- [ ] A-03.04 · Coordinar con C2/C3/C5 para que cada familia conserve su evidencia y sólo se contabilice una vez.
- [ ] A-03.05 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Cada acción contratada actual tiene cobertura mínima o limitación explícita sin inventar histórico; cambios y registro atómicos probados y lectura administrativa entendible.

**Responsable:** Desarrollo: Matriz de cobertura, correcciones demostradas y revisión; Wascar: QA de lectura administrativa cuando se integre; Entorno: PG real y candidata identificada. **Dependencias:** C2/C3/C5: inventario/import-export/backup que producen esos eventos; A-01

**Tipo de pendiente:** integración. **Peso:** 1,25 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-42; CONTRATO §4 operación/auditoría/revisión; rev4 C.14.

**Evidencia existente:** [docs/API-ADMIN-AUDITORIA-CONTEXTO-21-S1.md](API-ADMIN-AUDITORIA-CONTEXTO-21-S1.md), [evidence/s1-20261017/quince-tandas-55-59/CIERRE.md](../evidence/s1-20261017/quince-tandas-55-59/CIERRE.md), [docs/GUI-AUDITORIA-CONTEXTO-55.md](GUI-AUDITORIA-CONTEXTO-55.md). Todas las referencias e hitos separados están en elJSON.

### A-04 · Cerrar retención operativa, correlación y recuperación de operaciones antiguas

**Situación:** Operaciones y auditoría durables existentes; consulta administrativa paginada y contexto ya implementados. No hay política completa de purga/caducidad; marcas canceladas no se purgan para evitar reejecución antigua.

**Qué falta:**

- [ ] A-04.01 · Concretar retención30d de resultados y tratamiento de peticiones/replays después de caducidad; proteger cancelaciones/tombstones y compensaciones que dependan de evidencia.
- [ ] A-04.02 · Definir retención/correlación de auditoría/logs y procedimiento operativo de consulta/exportación saneada; no suponer que debe añadirse Serilog o un endpoint nuevo si lo existente cubre el uso.
- [ ] A-04.03 · Ensayar frontera temporal, petición antigua/cancelada y evidencia ausente: no reejecutar silenciosamente ni reconstruir desde el navegador.
- [ ] A-04.04 · Documentar qué se conserva/borra y qué recuperación/compensación deja de estar disponible; vincular request/event/trace sin secretos.
- [ ] A-04.05 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Política explícita y comprobada en frontera30d, sin resucitar operaciones canceladas ni afirmar éxito incierto; auditoría/logs consultables/correlacionables sin secretos y manual fiel.

**Responsable:** Desarrollo: Política técnica, implementación y prueba; Wascar: Validar necesidades operativas si afectan conservación acordada; Entorno: Laboratorio con reloj/fechas de fixture y destinos privados. **Dependencias:** A-03; C5: retención y respaldo operativo

**Tipo de pendiente:** implementación. **Peso:** 1,25 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** CONTRATO §6: retención inicial30d/idempotencia; S-27; S-28; S-42; rev4 C.14.

**Evidencia existente:** [docs/CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md), [docs/OPERACIONES-PENDIENTES.md](OPERACIONES-PENDIENTES.md), [docs/API-ADMIN-AUDITORIA-S1.md](API-ADMIN-AUDITORIA-S1.md). Todas las referencias e hitos separados están en elJSON.


## P. Paridad funcional y visual RC9 · 15 puntos del cierre

### P-01 · Convertir restauración RC9 de laboratorio en importación normal

**Situación:** implementacion: rc9_restore.py analiza/importa v0.8 a lab nuevo, conserva propiedades/original y mapea UUID. No rutas imports/preview/commit ni GUI upload localizadas.; integracion: Conversión/Restore de datos existente no es flujo normal de producto.; prueba: 04.10 y20.10:10clientes/68racks/311equipos/5408puertos/623cables; comparación10tablas y restorePGnuevo. Sin import normal autenticado.; revision: Conversión/restauración revisadas; flujo nuevo aún no.; qa: QA11 inspecciona copia, no preview/commit de usuario.

**Qué falta:**

- [ ] P-01.01 · Clasificar backup multicliente frente JSON cliente/rack por formato/versión, sin aplanar ni fusionar nombres.
- [ ] P-01.02 · Plan explícito destino/creación/mapeo por identidad y permisos; original exacto antes de confirmar.
- [ ] P-01.03 · API staging/preview/commit con revisión/actor/CSRF/idempotencia/auditoría y capacidad de transferencia vigente.
- [ ] P-01.04 · Reutilizar análisis validado; no convertir SQL generado por herramienta lab en entrada externa. Contrastar grupos/campos no soportados.
- [ ] P-01.05 · GUI archivo→compatibilidad/plan→confirmación→commit→recarga y recuperación de incertidumbre.
- [ ] P-01.06 · E2E10clientes, revocación/fallo mitad y revisión distinta.
- [ ] P-01.07 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Usuario capacitado importa archivo desde GUI/API con diez clientes/jerarquía/topología correctos, sin aplanamiento ni restos; evidencia/version/revisión/QA.

**Responsable:** Responsables: Backend/database/frontend; Revisor independiente; Wascar. **Dependencias:** P-02; P-03 para original; Autenticación MFA estable

**Tipo de pendiente:** implementación API/GUI. **Peso:** 1,36 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-31; S-32; S-07; CRev4 C.0.

**Evidencia existente:** [docs/RESTAURACION-QA-RC9.md](RESTAURACION-QA-RC9.md), [tools/windows/rc9_restore.py](../tools/windows/rc9_restore.py), [evidence/s1-20261004/rc9-restauracion-12/CIERRE.md](../evidence/s1-20261004/rc9-restauracion-12/CIERRE.md). Todas las referencias e hitos separados están en elJSON.

### P-02 · Previsualizar inválidos y doble ocupación sin perder enlaces

**Situación:** implementacion: Conversor lab rechaza connection_occupied; no UI staging que conserve y muestre ambos enlaces incompatibles completos.; integracion: Sin preview de colisiones de producto localizado.; prueba: Golden RC9 justifica requisito; rechazo no es preview íntegro.; revision: No revisión de staging/resolución completo.; qa: No habilitado.

**Qué falta:**

- [ ] P-02.01 · Preservar original/hash íntegros también si no se normaliza; límites de tamaño/tipo.
- [ ] P-02.02 · Mostrar todos los objetos/enlaces/ocupaciones e IDs/extremos; nunca elegir cable arbitrario.
- [ ] P-02.03 · Resolver explícitamente o dejar pendiente; nunca falso committed de import incompatible/parcial.
- [ ] P-02.04 · Revisión/actor/permiso cambiados invalidan plan; revalidar al commit.
- [ ] P-02.05 · JSON inválido, duplicados/dangling/grupos ambiguos/doble ocupación y fallo mitad/auditoría: cero efectos y original intacto.
- [ ] P-02.06 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Se ven ambos enlaces y el original se conserva; ningún commit normal sin resolver, fallos sin restos, revisión distinta y QA.

**Responsable:** Responsables: Backend/frontend; QA/revisor distinto; Wascar. **Dependencias:** P-01

**Tipo de pendiente:** staging y pruebas. **Peso:** 1,36 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-32; S-33; CRev4 C.0.

**Evidencia existente:** [docs/CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md), [docs/ACEPTACION.md](ACEPTACION.md), [tools/windows/rc9_restore.py](../tools/windows/rc9_restore.py). Todas las referencias e hitos separados están en elJSON.

### P-03 · Exportar JSON actual y original exacto como funciones distintas

**Situación:** implementacion: GETproject es consultaSQL, no exportRC9. Original/mapeos archivados por herramienta lab; no rutas/UI exportJSON/original localizadas en producto. R3 histórico es distinto.; integracion: Sin flujo producto actual/original identificado.; prueba: Preservación original y reportes exactos no prueban exportJSONnormal.; revision: Sin revisión de ese flujo.; qa: No disponible como exportJSONnormal.

**Qué falta:**

- [ ] P-03.01 · Contrato export cliente/rack/backup acordado con revisión fuente y mapeo serverUUID↔IDexportable estable.
- [ ] P-03.02 · Exportar estado actual desde snapshot autorizado, no archivo importado/localStorage.
- [ ] P-03.03 · Descargar original byteidéntico desde procedencia persistida segura, rotulado distinto.
- [ ] P-03.04 · Permiso transferencia/ámbito/actor/CSRF/revisión/recibo/auditoría y recuperación sin filtrar ajenos.
- [ ] P-03.05 · Validación/tamaño/hash/descarga segura; escritura→actual cambiado→originalSHAigual; revocación/replay/reinicio/revisión/QA.
- [ ] P-03.06 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Actual refleja commits vigentes y original conserva hash; funciones separadas respetan permisos, prueba/revisión/QA por versión.

**Responsable:** Responsables: Backend/frontend; Revisor independiente; Wascar. **Dependencias:** P-01; P-04

**Tipo de pendiente:** implementación API/GUI. **Peso:** 1,36 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-34; S-35; S-37; CRev4 C.0.

**Evidencia existente:** [docs/CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md), [docs/MAPA-RC9-R3.md](MAPA-RC9-R3.md), [tools/windows/rc9_restore.py](../tools/windows/rc9_restore.py). Todas las referencias e hitos separados están en elJSON.

### P-04 · Demostrar round-trip JSON y preservar extensiones

**Situación:** implementacion: properties/rc9OriginalId conservan parte de datos; metadata global no modelada sólo archivada. Sin exportactual→reimport completo.; integracion: Depende de P-01/P-03.; prueba: Comparación conversión10tablas no es round-trip sin cambios.; revision: Conversión sí; round-trip completo no.; qa: No caso producto completo aceptado.

**Qué falta:**

- [ ] P-04.01 · Matriz formato/versión JSON soportado; CSV/XLS de informes no son backups.
- [ ] P-04.02 · Fixtures homónimos, grupos gn repetido, legacyIDs, extensiones anidadas y metadata global.
- [ ] P-04.03 · Export sin cambios→lab nuevo→import→export y comparación de conocidos/IDs/extensiones/semántica; no exigir igualdad byte si no contractual.
- [ ] P-04.04 · Precisar metadatos hoy sólo archivados y conservarlos en ida/vuelta; ninguna pérdida silenciosa.
- [ ] P-04.05 · Editar conocidos sin borrar desconocidos; límites/atomicidad y revisión independiente del comparador/resultados.
- [ ] P-04.06 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Cada formato prometido tiene ida/vuelta reproducible, diferencias permitidas documentadas y sin pérdida de campos/IDs/extensiones, con revisión.

**Responsable:** Responsables: Backend/database y QA compatibilidad; Revisor distinto; Wascar para límites. **Dependencias:** P-01; P-03; P-06

**Tipo de pendiente:** integración y compatibilidad. **Peso:** 1,36 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-35; S-31; S-32; CRev4 C.0.

**Evidencia existente:** [docs/ACEPTACION.md](ACEPTACION.md), [docs/CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md), [docs/RESTAURACION-QA-RC9.md](RESTAURACION-QA-RC9.md). Todas las referencias e hitos separados están en elJSON.

### P-05 · Cerrar lista de herramientas RC9 restantes y sus equivalentes

**Situación:** implementacion: Referencias loadJSON/importRackJSON/mergeProject/importCSV/irAppendProject y saveSnapshot/restoreSnapshot/irDownloadCurrentRescue; equivalentes completos de producto no localizados. No afirmar ausencia sólo por un nombre histórico.; integracion: BackupPG operativo es C5, no estas herramientas de inventario.; prueba: No ejecución servidor actual de esas familias acreditada.; revision: Lista de equivalencias/restantes por revisar.; qa: Sin guiones de equivalencia identificados.

**Qué falta:**

- [ ] P-05.01 · Contrastar artefacto RC9 transformado y definir exactamente cada operación y pertenencia S1–S4.
- [ ] P-05.02 · Separar import cliente/rack/append/merge/CSV de P-01; por cada una equivalente/reutilización/límite explícito.
- [ ] P-05.03 · Separar snapshot/rescate por ámbito de backup/restorePG. Restaurar inventario requiere plan/revisión/permiso, nunca snapshot ciego sobre otro técnico.
- [ ] P-05.04 · Implementar faltantes contractuales con identidad/atomicidad/recuperación; pruebas/guiones por operación y revisión.
- [ ] P-05.05 · Decisión expresa para aplazamientos; S-50return permanece S5.
- [ ] P-05.06 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Desaparece rótulo genérico herramientasrestantes: lista cerrada, equivalentes/diferencias aceptadas y pruebas/revisión/QA de incluidas; S5/backup separados.

**Responsable:** Responsables: Producto/arquitectura; Backend/frontend; Revisor distinto; Wascar para alcance. **Dependencias:** P-01–P-04; I-02 si restaura estado

**Tipo de pendiente:** definición finita e implementación condicional. **Peso:** 1,36 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-31; S-32; S-34; S-35; S-30 si restaura estado; MAPA-RC9.

**Evidencia existente:** [docs/MAPA-RC9-R3.md](MAPA-RC9-R3.md), [docs/CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md), [docs/CIERRE-RESTANTE.md](CIERRE-RESTANTE.md). Todas las referencias e hitos separados están en elJSON.

### P-06 · Persistir identidad documental del cliente y branding RC9

**Situación:** implementacion: ReportesHTML omiten Systemhaus/logo/técnico; XLSHTML Technician vacío porque no hay campo persistido/importado. No usar actor como técnico documental.; integracion: Reportes existen; identidad documental completa no integrada.; prueba: Formatos probados, no metadata/logo nuevos.; revision: Acotada formatos existentes.; qa: S-36 identidad parcial.

**Qué falta:**

- [ ] P-06.01 · Contrastar campos RC9 cliente/Systemhaus/logo/técnico/metadata y permisos.
- [ ] P-06.02 · MigraciónSQL/Npgsql/API/GUI y su import/export; técnico documental independiente del actor.
- [ ] P-06.03 · Validar formato/tamaño del logo y render pasivo sin HTML/URL activa.
- [ ] P-06.04 · Añadir identidad real a reportesrack/cliente/etiquetas/XLS según referencia, conservando estilos/familias existentes.
- [ ] P-06.05 · Hostiles/Unicode, ámbitos, persistencia, impresión/comparación visual y revisión distinta/QA.
- [ ] P-06.06 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Campos RC9 prometidos persistidos/editables/importables/exportables y renderizados con identidad aprobada sin contenido activo; evidencia y QA.

**Responsable:** Responsables: Backend/database/frontend; UX; Revisor seguridad/QA distinto; Wascar. **Dependencias:** P-03/P-04; P-07

**Tipo de pendiente:** modelo/API/GUI. **Peso:** 1,36 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-21; S-35; S-36; CRev4 C.0.

**Evidencia existente:** [docs/CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md), [docs/API-INFORMES-IMPRIMIBLES-S1.md](API-INFORMES-IMPRIMIBLES-S1.md), [docs/API-XLS-HTML-RC9-S1.md](API-XLS-HTML-RC9-S1.md). Todas las referencias e hitos separados están en elJSON.

### P-07 · Cerrar formatos existentes y resolver obligación PDF

**Situación:** implementacion: CSV, XLSX tabular, HTML rack/cliente/etiquetasrack, SVGfront/rear y XLSHTML Devices/Connections/Summary existen. PDFRC9=impresión del navegador; no PDF nativo servidor.; integracion: Formatos integrados históricamente hastaQA13, no prueba de combinación14 final.; prueba: XLSHTML832 Excel16.0:87valores exactos/sinfórmulas, tablas enDevices, no3hojas pobladas. No compatibilidad universal ni PDFnuevo.; revision: Distintas por formato; PDFnuevo no.; qa: QA40–45/52–54/60–62/75–77 existentes; impresión/aceptación total pendiente.

**Qué falta:**

- [ ] P-07.01 · Lista exacta RC9/equivalentes: CSV≠XLSX≠XLSHTML, PDF/impresión, etiquetasrack sin inventar otras.
- [ ] P-07.02 · Resolver D4 contradictorio sin suprimir obligación por propuesta; si nativo requerido especificar/desarrollar, si impresión equivalente registrar decisión explícita.
- [ ] P-07.03 · Comparar candidata final con referencia/brandingP-06, extremos cross/sala, Unicode/hostiles y permisos en generación/replay/status/genéricas.
- [ ] P-07.04 · Probar impresión/guardarPDF y etiquetas en entorno objetivo; no prometer tres hojas XLSHTML. Foco real lectorXLSX acordado si ofrecido.
- [ ] P-07.05 · Registrar bytes/hash/capturas/pruebas/revisión/QA sin rehacer exportadores ya cubiertos.
- [ ] P-07.06 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Todos formatos prometidos tienen salida/lector/impresión y permisos verificados; PDF tiene decisión y evidencia; diferencias aceptadas, no eliminadas por plan ambiguo.

**Responsable:** Responsables: Producto/Wascar para D4; Backend/frontend/UX; Revisor distinto; Wascar. **Dependencias:** P-06; Candidata final; DecisiónD4

**Tipo de pendiente:** cobertura y decisión. **Peso:** 1,36 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-21; S-36; S-37; D4 pendiente; CRev4 C.0/C.10.

**Evidencia existente:** [docs/API-INFORMES-CSV-S1.md](API-INFORMES-CSV-S1.md), [docs/API-INFORMES-IMPRIMIBLES-S1.md](API-INFORMES-IMPRIMIBLES-S1.md), [docs/API-INFORME-RACK-SVG-S1.md](API-INFORME-RACK-SVG-S1.md). Todas las referencias e hitos separados están en elJSON.

### P-08 · Concluir aceptación de plantillas/favoritos/preferencias existentes

**Situación:** implementacion: BASE33/7, favoritos personales, privadas+rename+editor nuevaUUID, publicar/retirar/usar compartidas, idioma/tema y paletas10tipos/28parejas existen.; integracion: Windows/QA8–13 históricos; no volver a declarar compartir/editor/paletas pendientes por notas viejas.; prueba: PG/Node/Edge por bloques; no aceptación total S-26/S-47.; revision: Distinta por bloque; combinación finalMFA requiere foco.; qa: QA46–51/55–58/66–74/79–84 históricos, no Pass automático.

**Qué falta:**

- [ ] P-08.01 · Conservar código y conciliar notas obsoletas; no nueva función presupuesta.
- [ ] P-08.02 · Relacionar S-26 con BASE/privada/compartida/favorito y lector/editor/publicador/ajeno; identificar sólo huecos reales.
- [ ] P-08.03 · Preferencias por dueño y precedencia manual→pareja→null al crear, sin recolor histórico.
- [ ] P-08.04 · Foco pérdida respuesta/cambioactor/recarga/reauthMFA sobre combinación final.
- [ ] P-08.05 · QA con cuentas distintas y resultados por versión; preferencias no sustituyen aceptaciónS-26.
- [ ] P-08.06 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Cada familia S-26/S-47 probada/aceptada por actor en candidata final; sin privadas ajenas/éxitos falsos, revisión y QA, sin recrear funciones.

**Responsable:** Responsables: Producto/frontend/backend; Revisor distinto; Wascar. **Dependencias:** Candidata final/MFA; P-10/P-11

**Tipo de pendiente:** integración final y aceptación. **Peso:** 1,36 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-26; S-47; S-20; CRev4 C.18/C.10.

**Evidencia existente:** [docs/API-CATALOGO-BASE-S1.md](API-CATALOGO-BASE-S1.md), [docs/API-FAVORITOS-PERSONALES-S1.md](API-FAVORITOS-PERSONALES-S1.md), [docs/API-PLANTILLAS-PRIVADAS-S1.md](API-PLANTILLAS-PRIVADAS-S1.md). Todas las referencias e hitos separados están en elJSON.

### P-09 · Cerrar compatibilidad y aceptación de avisos multiusuario

**Situación:** implementacion: Polling5s visible, cursor/gaps, permisos actuales, borradores/Click-Click y detalle antes/después existen. Fuente actual incluye31acciones con createFromSharedTemplate; contrato428–472 describía30.; integracion: Detalle472 y extensión compartidas integrados históricamente; estructuralesC2 nuevos contexto notAvailable explícito.; prueba: 60/428–472/compartidas prueban commit/replay/rollback/aislamiento/reconexión/escala acotada; no capacidad10sesiones por ello.; revision: Distinta acotada, no combinación14MFA+C2.; qa: QA10/63–65 históricos; aceptación pendiente.

**Qué falta:**

- [ ] P-09.01 · Conciliar31acciones y contexto finito por acción frente documentos30/26; no reconstruir historia.
- [ ] P-09.02 · Foco final dos actores mismo cliente/rack, lector y ajeno, MFA caducada/revocación/cambio cliente/respuesta tardía.
- [ ] P-09.03 · Nombres históricos vs actorCurrent/etiquetasvista rotulados, no completar con tablas actuales.
- [ ] P-09.04 · Un aviso por commit, ninguno por replay/rollback; gap explícito, reconexión y borrador intacto.
- [ ] P-09.05 · Coordinar escala10sesiones conC6 sin doble tarea/métrica; QA y guion después de cambios reales.
- [ ] P-09.06 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Autor/acción/IDs/extremos correctos con autoridad actual; revocación detiene/limpia y borrador se conserva; límites explícitos, revisión y QA.

**Responsable:** Responsables: Backend/frontend; Revisor distinto; Wascar. **Dependencias:** I-01; MFA final; C6 para rendimiento

**Tipo de pendiente:** cobertura/integración/aceptación. **Peso:** 1,36 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** QA-UI-002; S-07; S-27; S-29; CRev4 C.0/C.18.

**Evidencia existente:** [docs/API-AVISOS-CLIENTE-S1.md](API-AVISOS-CLIENTE-S1.md), [docs/API-AVISOS-DESCRIPTIVOS-S1.md](API-AVISOS-DESCRIPTIVOS-S1.md), [docs/GUI-AVISOS-CLIENTE-S1.md](GUI-AVISOS-CLIENTE-S1.md). Todas las referencias e hitos separados están en elJSON.

### P-10 · Auditar EN/DE/ES, temas y literalidad de datos

**Situación:** implementacion: Tres idiomas, códigos backend localizados y preferencia idioma/tema existen. Falta auditoría integral; separador literal ? de Editar grupos sigue enInventoryPanel.; integracion: Preferencias históricasQA11/paletasQA13; nuevasGUI deben cubrirse.; prueba: Módulos EN/DE/ES/390px por bloques; no recorrido exhaustivo.; revision: UX/DOM acotadas, no lingüística integral.; qa: S-47 total pendiente.

**Qué falta:**

- [ ] P-10.01 · Enumerar login/MFA/reauth, inventario, plantillas/preferencias, avisos/errores/conflictos, admin/reportes.
- [ ] P-10.02 · Contrastar todas claves/rótulos/ayudas/errores en3idiomas; cabeceras inglesas XLSHTML como adaptación declarada.
- [ ] P-10.03 · Corregir faltas reales incluido ? visible si se toma ese cambio; sin traducir nombres/etiquetas del usuario.
- [ ] P-10.04 · Dark/light,390px/desktop, texto largo/Unicode y ordenación explícita; no migrar collation por intuición.
- [ ] P-10.05 · Reportes/conflictos/recuperaciónMFA y QA por versión con revisión distinta.
- [ ] P-10.06 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Matriz3idiomas/2temas sin texto prometido ausente/incoherente; datos intactos y capturas reales; QA deS-47 no sustituida por persistencia de idioma.

**Responsable:** Responsables: Frontend/writer/UX; Revisor distinto; Wascar. **Dependencias:** I-01; P-06; MFAinterfaz; P-11

**Tipo de pendiente:** cobertura/correcciones. **Peso:** 1,36 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-21; S-47; CRev4 C.18/C.0.

**Evidencia existente:** [docs/IMPLEMENTACION-REV4.md](IMPLEMENTACION-REV4.md), [docs/API-PREFERENCIAS-PERSONALES-S1.md](API-PREFERENCIAS-PERSONALES-S1.md), [docs/INTEGRACION-ESQUEMA11-WINDOWS-QA-S1.md](INTEGRACION-ESQUEMA11-WINDOWS-QA-S1.md). Todas las referencias e hitos separados están en elJSON.

### P-11 · Completar teclado, lector, contraste y paridad visual funcional

**Situación:** implementacion: GUIRC9/Click-Click/SVG, ARIA/foco y status persistente848/849 existen; no auditoría integral.; integracion: 849 históricoWindows/QA11; nuevaGUI posterior debe integrarse.; prueba: Edge/AX/teclado390px/DOM acotados; voz Narrador/NVDA no acreditada. Falta flujo completo front/rear/tooltips/inspector/contraste.; revision: DOM localizadas, no certificación ni aceptaciónvisualtotal.; qa: QA78 sin lector habitual debe Bloqueado, nunca Pass automático.

**Qué falta:**

- [ ] P-11.01 · Matriz Tab/ShiftTab/Enter/Escape/foco para rack/puerto, alternativa Click-Click, diálogos/recovery, plantillas/avisos/admin/MFA.
- [ ] P-11.02 · Lector real con status/alert/nombres/relaciones/cambios dinámicos; foco/borrador tras412/reauth.
- [ ] P-11.03 · Contraste dark/light, zoom/390px; tooltips/inspector accesibles y datos actuales tras rename/move.
- [ ] P-11.04 · Capturas contra RC9adoptada front/rear/presets/estados/PoE/reportes, literales hostiles y sin clienteanterior.
- [ ] P-11.05 · Corregir reproducibles y repetir foco; revisión independiente y QA con límites voz/DOM explícitos.
- [ ] P-11.06 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Matriz completa con resultados reales por versión, problemas resueltos/límites aceptados, conservando GUI/Click-Click. Voz no inferida de AX; QA de Wascar.

**Responsable:** Responsables: UX/frontend; QA/revisor distinto; Wascar. **Dependencias:** I-03; P-08; P-10; MFA y GUI estructural finales

**Tipo de pendiente:** auditoría/correcciones. **Peso:** 1,36 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-21; S-23; S-47; CRev4 C.19/C.10.

**Evidencia existente:** [docs/ACCESIBILIDAD-RELACIONES-GRUPOS-S1.md](ACCESIBILIDAD-RELACIONES-GRUPOS-S1.md), [docs/INTEGRACION-AVISO-GRUPOS-WINDOWS-QA-S1.md](INTEGRACION-AVISO-GRUPOS-WINDOWS-QA-S1.md), [docs/IMPLEMENTACION-REV4.md](IMPLEMENTACION-REV4.md). Todas las referencias e hitos separados están en elJSON.


## W. Instalación y operación Windows · 15 puntos del cierre

### W-01 · Corregir parada D14-07 y validación de edición del generador

**Situación:** Edición07: runtimef084 integrado y presente en el payload. Guardas tempranas de edición/pins verificadas. Cierre técnico W-01 acreditado; instalación limpia/SCM/reinicio Windows permanecen pendientes en sus tareas.

**Qué falta:**

- [x] W-01.01 · Integrar publicación atómica de stop-request en el runtime de producto, conservando identidad/ACL y el caso de dos Stop concurrentes.
- [x] W-01.02 · Validar edición y nombres finales antes de escribir payload/envoltorio; rechazar traversal y combinaciones de pins incoherentes sin salidas.
- [x] W-01.03 · Ejecutar focos de carrera original/corregida, negativos de edición y Start/Backup/Stop/reinicio del runtime corregido.
- [x] W-01.04 · Revisar los cambios y registrar hashes; no reabrir D14-05/D14-06 ya corregidos ni modificar paquetes congelados.
- [x] W-01.05 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Runtime y generador de producto corregidos con negativos y revisión; ningún éxito falso de parada o paquete inseguro.

**Responsable:** Responsables: Desarrollo; revisión independiente; Wascar sólo para aceptación o dato operativo propio. **Dependencias:** Sin dependencia previa nueva identificada.

**Tipo de pendiente:** cerrado con revisión independiente. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-02; S-03; S-49; S-51; S-56.

**Evidencia existente:** [docs/HALLAZGO-D14-07-PARADA-RUNTIME.md](HALLAZGO-D14-07-PARADA-RUNTIME.md), [docs/REVISION-INSTALADOR14-06-CODEX.md](REVISION-INSTALADOR14-06-CODEX.md), [docs/REVISION-INSTALADOR14-07-CODEX.md](REVISION-INSTALADOR14-07-CODEX.md). Todas las referencias e hitos separados están en elJSON.

### W-02 · Instalar desde cero en Windows limpio y declarar la matriz soportada

**Situación:** 29oct: instalaciónNew10 en snapshot limpio confirmado sin cuentas/servicios RackClick previos. Wrapper verificado y operador oficial con plan de la función GUI en ensayo headless; CRT14.40→14.51, runtime/PG incluidos, sin SDK/Node/Python real instalado. Reinicio de Wascar, SCM automático, HTTPS15 y MFA persistente verificados. Primer postboot adelantado falló y se conserva; verificación oficial posterior manual pasó. No acredita clics del asistente, Namespacecleanup ni toda la matriz de hosts.

**Qué falta:**

- [x] W-02.01 · Preparar otra VM limpia Windows Server2025 sin AD DS y registrar imagen/versión, cuentas, discos y red; conservar la VM QA.
- [x] W-02.02 · Ejecutar la entrega completa sin SDK/Node/Python previos; comprobar detección/instalación de runtime, PostgreSQL17 y CRT, incluido reinicio requerido.
- [ ] W-02.03 · Repetir con dependencias compatibles presentes; comprobar rechazo concreto de versión incompatible, puertos ocupados y DC antes de mutaciones.
- [ ] W-02.04 · Conciliar S-01 con Windows11 como posible host: ensayar todo sistema que se declare soportado. Windows11 usado sólo como cliente requiere navegador, sin servidor instalado.
- [ ] W-02.05 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Recorrido nuevo de instalación completo en los hosts declarados, con versiones y resultados reales; ausencia de soporte no probado indicada explícitamente.

**Responsable:** Responsables: Desarrollo; revisión independiente; Wascar sólo para aceptación o dato operativo propio. **Dependencias:** W-01; E-01

**Tipo de pendiente:** New10 en C verificado tras reinicio; W-02.01/.02 cerrados, matriz restante pendiente. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-01; S-51; S-52.

**Evidencia existente:** [docs/ACEPTACION.md](ACEPTACION.md), [docs/CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md), [docs/REVISION-INSTALADOR14-06-CODEX.md](REVISION-INSTALADOR14-06-CODEX.md). Todas las referencias e hitos separados están en elJSON.

### W-03 · Cuenta mínima, servicio Windows y arranque automático reales

**Situación:** Host C# y scripts existen. Foreground PS1 no acredita SCM, inicio bajo SID real, permisos instalados ni reinicio Windows.

**Qué falta:**

- [ ] W-03.01 · Instalar/verificar cuenta estándar y derecho de servicio, ACL de código/datos/claves y separación de identidades SQL runtime/migración.
- [ ] W-03.02 · Arrancar y detener por SCM; comprobar señalización, tiempos, diagnósticos, cierre limpio y fallo del hijo sin estado falso Running.
- [ ] W-03.03 · Reiniciar Windows y verificar arranque automático, readiness14, inventario persistido y tareas operativas.
- [ ] W-03.04 · Comprobar credenciales iniciales privadas y acceso administrativo recuperable, sin introducir contraseña universal.
- [ ] W-03.05 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Servicio y PostgreSQL funcionan bajo identidad mínima tras reinicio real; logs/estados y acceso privado son verificables.

**Responsable:** Responsables: Desarrollo; revisión independiente; Wascar sólo para aceptación o dato operativo propio. **Dependencias:** W-02; F-04

**Tipo de pendiente:** pendiente de cierre. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-02; S-04; S-43; S-55.

**Evidencia existente:** [development/windows-service/Program.cs](../development/windows-service/Program.cs), [docs/CIERRE-ORDENADO-SERVIDOR-S1.md](CIERRE-ORDENADO-SERVIDOR-S1.md), [docs/REVISION-INSTALADOR14-06-CODEX.md](REVISION-INSTALADOR14-06-CODEX.md). Todas las referencias e hitos separados están en elJSON.

### W-04 · HTTPS, certificados, red y acceso casa/trabajo en la edición final

**Situación:** Cambio de red fue confirmado en la instalación histórica y existen herramientas automáticas. No se traslada esa aceptación automáticamente al payload14 nuevo.

**Qué falta:**

- [ ] W-04.01 · Fijar nombre/IP de aplicación, SAN, puerto y subred autorizada; no cambiar IP/DNS Windows por inferencia.
- [ ] W-04.02 · Instalar y verificar cadena HTTPS; distribuir sólo CA pública a navegadores clientes y comprobar otra sesión desde otro equipo.
- [ ] W-04.03 · Comprobar firewall limitado a la red elegida y PostgreSQL sólo local; CSRF/Origin/cookies bajo HTTPS real.
- [ ] W-04.04 · Ensayar cambio casa/trabajo de la edición nueva, detección y recuperación de fallo, conservando datos/cuentas.
- [ ] W-04.05 · Documentar y probar renovación/caducidad del certificado y recuperación de su clave; no considerar certificado de laboratorio una PKI productiva aceptada.
- [ ] W-04.06 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Acceso LAN confiable y cambio de red con datos conservados; renovación y errores documentados, sin exponer claves privadas.

**Responsable:** Responsables: Desarrollo; revisión independiente; Wascar sólo para aceptación o dato operativo propio. **Dependencias:** W-03; E-01

**Tipo de pendiente:** pendiente de cierre. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-43; S-49; S-55.

**Evidencia existente:** [docs/RACKCLICK-CASA-Y-TRABAJO.html](RACKCLICK-CASA-Y-TRABAJO.html), [docs/CONTINUIDAD-CODEX.md](CONTINUIDAD-CODEX.md), [docs/CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md). Todas las referencias e hitos separados están en elJSON.

### W-05 · Repetición, cancelación, mantenimiento y diagnóstico del instalador

**Situación:** Hay preflights, archivo/retirada por identidad y reportes automáticos; experiencias históricas no equivalen a ensayo completo14 de estos recorridos.

**Qué falta:**

- [ ] W-05.01 · Repetir instalación contra una existente: no reinicializar base, crear admin duplicado ni tomar una carpeta ajena.
- [ ] W-05.02 · Cancelar antes de aplicar y durante fases recuperables; comprobar estado final y posibilidad de continuar sin borrar evidencias.
- [ ] W-05.03 · Ensayar retirada/archivo sólo de instancias/cuentas atribuidas, conservar SID y bases; tratar elementos sin atribución con informe concreto.
- [ ] W-05.04 · Comprobar informe automático, errores y códigos de salida, y que Acceso privado abre bajo la identidad esperada sin filtrar secretos.
- [ ] W-05.05 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Cada fallo/cancelación tiene estado veraz y procedimiento repetible; programas/bases ajenos y cuentas manuales permanecen intactos.

**Responsable:** Responsables: Desarrollo; revisión independiente; Wascar sólo para aceptación o dato operativo propio. **Dependencias:** W-02

**Tipo de pendiente:** pendiente de cierre. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-03; S-51; S-52; S-53; S-54.

**Evidencia existente:** [docs/INICIO-IMPLEMENTACION-S1.md](INICIO-IMPLEMENTACION-S1.md), [docs/REINICIO-LIMPIO-SERVIDOR.html](REINICIO-LIMPIO-SERVIDOR.html), [docs/REVISION-INSTALADOR14-06-CODEX.md](REVISION-INSTALADOR14-06-CODEX.md). Todas las referencias e hitos separados están en elJSON.

### W-06 · Recorrido completo de persistencia y concurrencia del servidor instalado

**Situación:** Hay pruebas reales por bloques y New/Restore privados. Falta el recorrido integral sobre la candidata final instalada con dos sesiones y reinicio.

**Qué falta:**

- [ ] W-06.01 · Desde Systemhaus y cliente crear/editar jerarquía, rack, equipo y nota de puerto con cuenta autorizada.
- [ ] W-06.02 · Guardar, cerrar navegador, reiniciar servicio y verificar desde segunda cuenta; comparar IDs y relaciones. Verificar admin/técnico/lector y ámbitos en el mismo conjunto instalado.
- [ ] W-06.03 · Provocar conflicto simultáneo, pérdida de respuesta y reintento; confirmar una sola operación/auditoría sin éxito fantasma.
- [ ] W-06.04 · Usar los mismos resultados para cubrir los criterios compartidos de otros bloques; no repetir esta corrida por cada documento.
- [ ] W-06.05 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** S-55 reproducido completo y conflictos/recuperación coherentes sobre build/DB/host identificados.

**Responsable:** Responsables: Desarrollo; revisión independiente; Wascar sólo para aceptación o dato operativo propio. **Dependencias:** W-03; I-01; P-01

**Tipo de pendiente:** pendiente de cierre. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-10; S-15; S-17; S-27; S-28; S-29; S-55; S-06.

**Evidencia existente:** [docs/ACEPTACION.md](ACEPTACION.md), [docs/REVISION-INSTALADOR14-06-CODEX.md](REVISION-INSTALADOR14-06-CODEX.md). Todas las referencias e hitos separados están en elJSON.


## R. Backup, recuperación y actualización · 15 puntos del cierre

### R-01 · Backup programado local y retención comprobada

**Situación:** pg_dump, manifiesto, verificación y tarea diaria existen. El contrato propone7 diarios+4 semanales; no hay cierre integral de retención operativa acreditado.

**Qué falta:**

- [ ] R-01.01 · Comprobar tarea bajo cuenta mínima después del reinicio y registrar ejecución/errores sin contraseñas.
- [ ] R-01.02 · Implementar o completar retención configurable con valores documentados; nunca borrar la última copia válida por un fallo.
- [ ] R-01.03 · Ensayar backups concurrentes, falta de espacio, corte de escritura y copia incompleta; verificar que no se publican como válidos.
- [ ] R-01.04 · Medir duración y tamaño con demo; documentar RPO24h/RTO2h como objetivos propuestos, no garantías ya medidas.
- [ ] R-01.05 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Ejecución programada real, política de retención y fallos comprobados; sólo copias completas verificadas quedan elegibles.

**Responsable:** Responsables: Desarrollo; revisión independiente; Wascar sólo para aceptación o dato operativo propio. **Dependencias:** W-03

**Tipo de pendiente:** pendiente de cierre. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-44; S-56.

**Evidencia existente:** [docs/CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md), [docs/BACKUP-RESTAURACION-WINDOWS-S1.md](BACKUP-RESTAURACION-WINDOWS-S1.md), [docs/REVISION-INSTALADOR14-06-CODEX.md](REVISION-INSTALADOR14-06-CODEX.md). Todas las referencias e hitos separados están en elJSON.

### R-02 · Destinos USB y UNC con copia local previa y tolerancia a fallos

**Situación:** El operador básico exige disco fijo local; copiar manualmente desdeUSB/UNC no cierra el flujo operativo. D6 de aplazarUSB no está confirmada inequívocamente.

**Qué falta:**

- [ ] R-02.01 · Completar copia local consistente y después copia verificada a destino USB/UNC autorizado, con identidad y permisos mínimos.
- [ ] R-02.02 · Ensayar NAS ausente, permisos denegados, unidad retirada, disco lleno y archivo alterado: alerta y última copia válida conservada.
- [ ] R-02.03 · Restaurar desde cada destino mediante staging local privado y referencia de hash confiable.
- [ ] R-02.04 · Mantener USB en el alcance final mientras no haya decisión expresa de aplazamiento; documentar D6 sin recortar silenciosamente.
- [ ] R-02.05 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Local/USB/UNC tienen prueba de copia, fallo y restauración con límites y permisos registrados.

**Responsable:** Responsables: Desarrollo; revisión independiente; Wascar sólo para aceptación o dato operativo propio. **Dependencias:** R-01

**Tipo de pendiente:** pendiente de cierre. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-44; S-45.

**Evidencia existente:** [docs/ACEPTACION.md](ACEPTACION.md), [docs/METODOLOGIA-PARA-CLAUDE.md](METODOLOGIA-PARA-CLAUDE.md), [docs/BACKUP-RESTAURACION-WINDOWS-S1.md](BACKUP-RESTAURACION-WINDOWS-S1.md). Todas las referencias e hitos separados están en elJSON.

### R-03 · Backup cifrado de instalación y recuperación de material privado

**Situación:** Dump de DB y ACL privadas no equivalen a backup cifrado portable de configuración, assets, certificados y claves.

**Qué falta:**

- [ ] R-03.01 · Definir manifiesto de recuperación de datos/roles/configuración/assets/certificados y referencias de claves; separar material de recuperación y paquete público.
- [ ] R-03.02 · Cifrar y autenticar backup con clave recuperable y parámetros versionados; fallo explícito por clave errónea o integridad alterada.
- [ ] R-03.03 · Integrar la protecciónSQL de F-02 y sobreTOTP de F-05; reutilizar sus resultados sin desarrollar otro cifrado para lo mismo.
- [ ] R-03.04 · Ensayar acceso mínimo, diagnóstico saneado y recuperación en otro Windows/SID, sin copiar secretos ligados al host antiguo como solución.
- [ ] R-03.05 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Copia completa cifrada y recuperable en otro host con procedimiento/material independiente; ausencia de clave no provoca fallback inseguro.

**Responsable:** Responsables: Desarrollo; revisión independiente; Wascar sólo para aceptación o dato operativo propio. **Dependencias:** F-02; F-05; W-03

**Tipo de pendiente:** pendiente de cierre. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-44; S-45; S-56; rev4 C.6; rev4 C.15.

**Evidencia existente:** [docs/IMPLEMENTACION-REV4.md](IMPLEMENTACION-REV4.md), [docs/DECISION-D2-CUSTODIA-CLAVE-TOTP.md](DECISION-D2-CUSTODIA-CLAVE-TOTP.md), [docs/RECUPERACION-DESPLIEGUE-WINDOWS-S1.md](RECUPERACION-DESPLIEGUE-WINDOWS-S1.md). Todas las referencias e hitos separados están en elJSON.

### R-04 · Recuperación completa en otro Windows y activación controlada

**Situación:** Restore13→14/14→14 y revocación de desafíos/sesiones están probados en laboratorios; New/Restore offline14 producen recibos reales. Falta recuperación integral del host instalado.

**Qué falta:**

- [ ] R-04.01 · Restaurar en VM limpia con base/roles/claves/identidad nuevos, usando backup de confianza; conservar origen sin sobrescribirlo.
- [ ] R-04.02 · Verificar conteos, referencias, grupos/permisos, assets, configuración y acceso; demostrar cookies/desafíos anteriores revocados y MFA recuperable.
- [ ] R-04.03 · Resolver frescura del backup y cambio de servicio/URL con origen quieto; declarar qué ocurre con escrituras posteriores al snapshot.
- [ ] R-04.04 · Comprobar HTTPS, login, escritura, segunda sesión, backup nuevo y reinicio real del recuperado; medir tiempo de recuperación.
- [ ] R-04.05 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Servicio recuperado completo y operativo en otro host con identidad nueva, integridad y revocación comprobadas; origen conservado.

**Responsable:** Responsables: Desarrollo; revisión independiente; Wascar sólo para aceptación o dato operativo propio. **Dependencias:** R-03; W-03

**Tipo de pendiente:** pendiente de cierre. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-45; S-55.

**Evidencia existente:** [docs/REVISION-D14-05-CODEX.md](REVISION-D14-05-CODEX.md), [docs/REVISION-INSTALADOR14-06-CODEX.md](REVISION-INSTALADOR14-06-CODEX.md), [docs/RECUPERACION-DESPLIEGUE-WINDOWS-S1.md](RECUPERACION-DESPLIEGUE-WINDOWS-S1.md). Todas las referencias e hitos separados están en elJSON.

### R-05 · Actualización y rollback compatibles con datos posteriores

**Situación:** Hay migraciónSQL y ensayos de copias/retornos privados. No es actualización en sitio probada del servicio ni retorno libre después de nuevas escrituras.

**Qué falta:**

- [ ] R-05.01 · Definir recorrido de actualización identificado con backup previo y versiones/esquemas compatibles.
- [ ] R-05.02 · Ensayar fallo antes/durante/después de migración y publicación; mantener estado inequívoco y último conjunto recuperable.
- [ ] R-05.03 · Restaurar a base nueva cuando el esquema no permita binario antiguo; no sustituir sólo DLL sobre DB nueva.
- [ ] R-05.04 · Probar que actividad/escrituras posteriores impiden rollback silencioso; conmutación y necesidad de recuperación quedan explícitas.
- [ ] R-05.05 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Upgrade y fallos con vuelta compatible comprobados en instalación real, sin perder escrituras ni seleccionar binarios incompatibles.

**Responsable:** Responsables: Desarrollo; revisión independiente; Wascar sólo para aceptación o dato operativo propio. **Dependencias:** R-04; E-01

**Tipo de pendiente:** pendiente de cierre. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-46; S-03; S-49.

**Evidencia existente:** [docs/RECUPERACION-DESPLIEGUE-WINDOWS-S1.md](RECUPERACION-DESPLIEGUE-WINDOWS-S1.md), [docs/CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md), [docs/REVISION-D14-05-CODEX.md](REVISION-D14-05-CODEX.md). Todas las referencias e hitos separados están en elJSON.

### R-06 · Reset y recuperación administrativa delimitados

**Situación:** Hay herramientas de reset/archivo y recuperación administrativa. MFA/emergencia está en F-08/F-09; no es necesario rehacerlas en este bloque.

**Qué falta:**

- [ ] R-06.01 · Ensayar reinicio de laboratorio sólo sobre GUID elegido con base/roles/secretos/admin nuevos, sin tocar Windows ni otras bases.
- [ ] R-06.02 · Cancelar y repetir exigen confirmar otra vez el destino; conservar datos/cuentas/SID atribuidos y un informe recuperable.
- [ ] R-06.03 · Integrar el procedimiento de emergencia de F-09 con último administrador, revocación de sesiones/desafíos y auditoría.
- [ ] R-06.04 · Comprobar manual y canales privados para volver a acceder sin credencial universal ni extracción de secretos a logs.
- [ ] R-06.05 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Reset acotado y recuperación de acceso operativos y documentados; cancelar no modifica datos ni deja acceso omitido.

**Responsable:** Responsables: Desarrollo; revisión independiente; Wascar sólo para aceptación o dato operativo propio. **Dependencias:** F-09; W-05

**Tipo de pendiente:** pendiente de cierre. **Peso:** 2,50 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-40; S-41; S-53; S-54.

**Evidencia existente:** [docs/RECUPERAR-ADMINISTRADOR-S1.md](RECUPERAR-ADMINISTRADOR-S1.md), [docs/ACEPTACION.md](ACEPTACION.md), [docs/REVISION-D14-05-CODEX.md](REVISION-D14-05-CODEX.md). Todas las referencias e hitos separados están en elJSON.


## E. Paquete, manual, rendimiento y aceptación · 10 puntos del cierre

### E-01 · Candidata final única con fuentes y componentes compatibles

**Situación:** Hay candidataM3 limpia03, C2 revisado aparte y instalador06 interno. No hay una única entrega final que integre todo el alcance.

**Qué falta:**

- [ ] E-01.01 · Seleccionar fuentes revisadas de MFA/C2/GUI/operadores, con manifiesto de procedencia; conservar candidatas históricas sin mezclarlas.
- [ ] E-01.02 · Integrar componentes estables y construir una vez el conjunto coordinado; evitar otro build o ZIP por una corrección sólo documental.
- [ ] E-01.03 · Comprobar rutas/DTO/esquema/recursoslocales, app/bundle/payload/wrapper/CMD y sus pins; sin fuentes/secretos/diagnósticos privados en entrega.
- [ ] E-01.04 · Congelar versión/hashes/inventario y repetir sólo regresión pertinente tras cambios; asociar QA y manual a esos mismos bytes.
- [ ] E-01.05 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Una sola candidata completa trazable y coherente, sin depender de archivos de entregas anteriores ni aceptar una mezcla no revisada.

**Responsable:** Responsables: Desarrollo; revisión independiente; Wascar sólo para aceptación o dato operativo propio. **Dependencias:** W-01; I-01; F-11

**Tipo de pendiente:** pendiente de cierre. **Peso:** 1,43 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-49; S-56.

**Evidencia existente:** [docs/REVISION-INSTALADOR14-06-CODEX.md](REVISION-INSTALADOR14-06-CODEX.md), [docs/REVISION-D14-05-CODEX.md](REVISION-D14-05-CODEX.md), [docs/CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md). Todas las referencias e hitos separados están en elJSON.

### E-02 · Aprovisionamiento y construcción repetibles desde fuentes oficiales

**Situación:** SDK/PG/frontend están fijados y los generadores existen. Las copiasS1/S2/S3 dependen de herramientas/artefactos y hardlinks de.local.

**Qué falta:**

- [ ] E-02.01 · Documentar y automatizar obtención oficial y verificación de SDK fijado, PostgreSQL17, frontend, runtime yCRT; sin cambiar pins silenciosamente.
- [ ] E-02.02 · Construir desde checkout/entorno nuevo con locks, sin rutas privadas preexistentes ni fuentes contaminadas por trabajo paralelo.
- [ ] E-02.03 · Comprobar hashes de contenidos/manifiestos y reproducibilidad declarada; explicar PDB/rutas y diferencias no deterministas.
- [ ] E-02.04 · Producir distribución, bundle e instalador con comandos públicos completos; un cliente navegador no instala SDK/Node/DB.
- [ ] E-02.05 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Otra persona puede reproducir la candidata mediante el procedimiento y entradas pinadas, sin copiar.local del desarrollador.

**Responsable:** Responsables: Desarrollo; revisión independiente; Wascar sólo para aceptación o dato operativo propio. **Dependencias:** E-01

**Tipo de pendiente:** pendiente de cierre. **Peso:** 1,43 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-01; S-49; S-51; S-56.

**Evidencia existente:** [docs/REVISION-INSTALADOR14-06-CODEX.md](REVISION-INSTALADOR14-06-CODEX.md), [docs/REVISION-D14-05-CODEX.md](REVISION-D14-05-CODEX.md), [development/toolchain.lock.json](../development/toolchain.lock.json). Todas las referencias e hitos separados están en elJSON.

### E-03 · Inventario de dependencias, avisos y redistribución

**Situación:** AvisoMIT completo de Otp.NET ya incorporado. La revisión general de redistribución sigue abierta; no falta añadir de nuevo ese aviso.

**Qué falta:**

- [ ] E-03.01 · Inventariar componentes exactos de app/runtime/PG/CRT/frontend/fuentes y origen/hash/versión/licencia de cada uno.
- [ ] E-03.02 · Contrastar avisos y condiciones de redistribución con sus fuentes/licencias oficiales; distinguir tener un aviso de tener todo el permiso resuelto.
- [ ] E-03.03 · Resolver ausencias/condiciones y conservar decisiones; no publicar o redistribuir como entrega final antes de cerrar los puntos reales.
- [ ] E-03.04 · Verificar contenido final e informe de vulnerabilidades conocido para las versiones seleccionadas, sin cambios de versión silenciosos.
- [ ] E-03.05 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Manifiesto y avisos completos, condiciones aplicables documentadas y cuestiones de redistribución resueltas.

**Responsable:** Responsables: Desarrollo; revisión independiente; Wascar sólo para aceptación o dato operativo propio. **Dependencias:** E-01

**Tipo de pendiente:** pendiente de cierre. **Peso:** 1,43 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-49; S-56.

**Evidencia existente:** [docs/REVISION-BUNDLE14-02-CODEX.md](REVISION-BUNDLE14-02-CODEX.md), [docs/REVISION-INSTALADOR14-06-CODEX.md](REVISION-INSTALADOR14-06-CODEX.md), [development/offline-bundle14.sources.json](../development/offline-bundle14.sources.json). Todas las referencias e hitos separados están en elJSON.

### E-04 · Manual autónomo de instalación, uso y operación

**Situación:** Hay manuales/guías por bloques y HTML de instalación. Falta un recorrido final autónomo verificado sobre la misma edición final.

**Qué falta:**

- [ ] E-04.01 · Escribir pasos00→último: requisitos/cuentas/instalación/certificados/navegador/primerloginMFA, con ubicaciones y botones exactos para Wascar.
- [ ] E-04.02 · Documentar usuarios/grupos/permisos, Click-Click, guardado/conflictos, import/export, informes y límites de Dosen/Undo.
- [ ] E-04.03 · Incluir credenciales mediante acceso privado local por instancia, nunca contraseñas en manual/ZIP público; explicar conexiónSQL autorizada y mínimo privilegio.
- [ ] E-04.04 · Incluir red casa/trabajo, backup/retención/USB/UNC, restore, upgrade/rollback, emergenciaMFA, diagnóstico y recuperación.
- [ ] E-04.05 · Seguir el manual desde un host nuevo y corregir cada paso implícito; capturas reales y vocabulario de GUI EN/DE/ES sin traducir nombres del usuario.
- [ ] E-04.06 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** El recorrido completo funciona siguiendo sólo manual+paquete final, sin pedir archivos antiguos ni instrucciones ocultas.

**Responsable:** Responsables: Desarrollo; revisión independiente; Wascar sólo para aceptación o dato operativo propio. **Dependencias:** E-01; R-04

**Tipo de pendiente:** pendiente de cierre. **Peso:** 1,43 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-56; S-43; S-44; S-45; S-46.

**Evidencia existente:** [docs/MANUAL-PAQUETE-WINDOWS-S1.md](MANUAL-PAQUETE-WINDOWS-S1.md), [docs/INSTALACION-SERVIDOR-DESDE-CERO.html](INSTALACION-SERVIDOR-DESDE-CERO.html), [docs/QA-COLABORACION-Y-RESTAURACION.md](QA-COLABORACION-Y-RESTAURACION.md). Todas las referencias e hitos separados están en elJSON.

### E-05 · QA manual por módulos sobre candidata identificada

**Situación:** Catálogo111 casos y guías existen; hay resultados anteriores de Wascar. Disponible no equivale a aprobado, ni Pass de versión vieja a candidata nueva.

**Qué falta:**

- [ ] E-05.01 · Vincular casos disponibles a build/hash, rol y ámbito reales; actualizar pasos exactos y resultado esperado, sin habilitar por código de desarrollo.
- [ ] E-05.02 · Conciliar resultados antiguos por fecha/versión y pedir sólo repetición afectada; conservar Pass/NotPass/observaciones originales y su exportJSON.
- [ ] E-05.03 · Preparar cuentas ficticias administrador/técnico/lector con ámbitos distintos y acceso privado, y sesiones de navegador separadas.
- [ ] E-05.04 · Ofrecer guiones pequeños por módulo para una sola persona; registrar fallos/bloqueos porID y confirmar correcciones con prueba concreta.
- [ ] E-05.05 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Casos críticos y recorridos pactados tienen resultados atribuibles; ningún resultado del usuario sobrescrito ni aprobado por el desarrollador.

**Responsable:** Responsables: Desarrollo prepara/corrige; Wascar ejecuta a su ritmo y decide aceptación; revisor técnico independiente. **Dependencias:** E-01; W-06

**Tipo de pendiente:** pendiente de cierre. **Peso:** 1,43 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-01; S-04; S-05; S-38; S-39; S-40; S-41; S-47; S-55; S-56.

**Evidencia existente:** [docs/QA-CASOS-WASCAR.json](QA-CASOS-WASCAR.json), [docs/QA-COLABORACION-Y-RESTAURACION.md](QA-COLABORACION-Y-RESTAURACION.md), [docs/QA-POR-SESIONES-WASCAR.md](QA-POR-SESIONES-WASCAR.md). Todas las referencias e hitos separados están en elJSON.

### E-06 · Medir carga real de diez usuarios y demo completa

**Situación:** No hay resultado final de rendimiento identificado para diez usuarios y demo68racks en el host candidato. No se ha demostrado un cuello de botella concreto.

**Qué falta:**

- [ ] E-06.01 · Preparar demo sintética prevista y diez sesiones autorizadas, combinando lectura/escritura/conflictos con ámbitos y roles.
- [ ] E-06.02 · Medir latencias por operación, errores/conflictos, memoria/CPU y consultas durante carga y recuperación; registrar entorno/duración.
- [ ] E-06.03 · Definir antes del ensayo los umbrales de aceptación prácticos y documentar límites; no inventar garantías de producción.
- [ ] E-06.04 · Corregir sólo problemas medidos y repetir el foco; no introducir Redis/índices/caché de permisos por suposición.
- [ ] E-06.05 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Informe reproducibleS-48 demuestra datos consistentes y comportamiento aceptable con carga declarada; regresiones medidas resueltas.

**Responsable:** Responsables: Desarrollo; revisión independiente; Wascar sólo para aceptación o dato operativo propio. **Dependencias:** E-01; W-03

**Tipo de pendiente:** pendiente de cierre. **Peso:** 1,43 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-48; rev4 C.3.

**Evidencia existente:** [docs/ACEPTACION.md](ACEPTACION.md), [docs/IMPLEMENTACION-REV4.md](IMPLEMENTACION-REV4.md), [docs/CIERRE-RESTANTE.md](CIERRE-RESTANTE.md). Todas las referencias e hitos separados están en elJSON.

### E-07 · Revisión final y adopción explícita de Wascar

**Situación:** Servidor histórico funciona según Wascar, pero la entrega final nueva no está adoptada. No corresponde anunciar100% por generar un ZIP.

**Qué falta:**

- [ ] E-07.01 · Conciliar los55 criteriosS1–S4 y requisitos producto de revisión4 con evidencia, límites y casos pendientes; S-50 queda enS5.
- [ ] E-07.02 · Cerrar defectos bloqueantes y revisar seguridad/contenido/recuperación del mismo conjunto final, reutilizando pruebas válidas no afectadas.
- [ ] E-07.03 · Entregar paquete/manual/evidencias/hashes y recuperación; registrar aceptación o excepciones explícitas de Wascar.
- [ ] E-07.04 · Dejar lista separada de roadmap, soporte y decisiones futuras, sin convertir propuestas no aprobadas en cierre alcanzado.
- [ ] E-07.05 · Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

**Se cierra cuando:** Conjunto final completo revisado, recorrido instalado/recuperado acreditado y confirmación de adopción de Wascar registrada.

**Responsable:** Responsables: Desarrollo; revisión independiente; Wascar sólo para aceptación o dato operativo propio. **Dependencias:** E-03; E-04; E-05; E-06; R-04

**Tipo de pendiente:** pendiente de cierre. **Peso:** 1,43 puntos. Resultado único de cierre; no sumar sus referencias cruzadas como otras tareas.

**Criterios:** S-49; S-56.

**Evidencia existente:** [docs/ACEPTACION.md](ACEPTACION.md), [docs/CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md), [docs/CONTINUIDAD-CODEX.md](CONTINUIDAD-CODEX.md). Todas las referencias e hitos separados están en elJSON.

## Lo definido que no se vuelve a discutir

- ASP.NET Core/.NET 10, Npgsql directo, migraciones SQL y PostgreSQL 17; no SQLite ni otro piloto.
- Los usuarios trabajan en navegador. Instalar el servidor no significa instalar la aplicación en cada Windows 11 cliente.
- RC9 y Click-Click son la referencia; IDs/grupo/tipo dirigen lotes, no un gn ambiguo. Permisos y confirmación del guardado se resuelven en servidor.
- MFA obligatorio para todos antes de producción. Excepciones temporales de QA no lo revocan.
- Laboratorios y restauraciones en destinos nuevos, sin borrar bases ajenas. Desarrollo ya autorizado; adopción final por Wascar.

## Decisiones y aspectos todavía por concretar

No son nuevas autorizaciones de arranque. Desarrollo prepara diseños/ensayos; Wascar decide custodia, necesidades operativas y cualquier reducción explícita del alcance. No se le traslada diseñar la criptografía.

- ID: D2; Responsable: Wascar; Por concretar: Custodia de contraseña/sobre y ubicación definitiva de almacén; no confirmar por inferencia.; Trabajo que puede continuar: Pruebas con proveedor sintético aislado y preparación técnica de las cuatro condiciones de revisión.
- ID: D2-technical; Responsable: Desarrollo con revisión independiente; Por concretar: Transición recuperación restringida, límites KDF/cabeceraAAD, fases disco/DB y acceso SID real.; Nota: No pedir a Wascar que diseñe detalles de implementación; presentar resultado concreto para su custodia operativa.
- ID: D3/D7; Responsable: Decisiones funcionales de Wascar ya registradas según plan; Por concretar: Implementar comportamiento existente/reset y retirada de excepción QA; obligatoriedad universal preproducción firme.; Nota: No pedir nuevo arranque ni nuevo GO universal.
- ID: D4/D5/D6; Responsable: Wascar si se modifica alcance contractual; Por concretar: Propuestas de aplazar PDFnuevo/Dosen-finales/USB no autorizan quitar paridad/entidades/destinos contratados.; Nota: Para conciliación global; pertenecen a C2/C3/C5 y no se cuentan aquí como decisión MFA.
- ID: D4; Tema: PDF; Estado: unknown; Referencia: docs/PLAN-MFA-Y-FRENTES-C1-C5.md; docs/METODOLOGIA-PARA-CLAUDE.md; Conflicto: PLAN-MFA tabla D4 dice incluir sólo formatos RC9 y PDF nuevo fuera del primer cierre; METODOLOGIA §10 D4 dice «Pendiente» y que PDF nuevo después es una propuesta.; Tratamiento: No excluir una obligación por propuesta. exportPDF RC9 usaba impresión del navegador; distinguir esa equivalencia de PDF nativo servidor. Resolver en P-07.
- ID: D5; Tema: Dosen/dispositivos finales; Estado: unknown; Referencia: docs/PLAN-MFA-Y-FRENTES-C1-C5.md; docs/METODOLOGIA-PARA-CLAUDE.md; docs/CONTRATO-INVENTARIO-S1.md; Conflicto: PLAN-MFA tabla D5 dice fuera del primer cierre; METODOLOGIA §10 D5 dice que aplazarlos es una propuesta pendiente y que el modelo Dose/final es requisito explícito.; Tratamiento: No retirar Dose/final del alcance ni rehacer su soporte existente. I-06 cubre lo externo ya soportado; I-07 separa el modelo físico interno aún no acordado.
- ID: D6; Responsable: Wascar sólo si se aplaza USB; Por concretar: Local/USB/UNC permanecen en alcance; aplazamientoUSB del plan23 es propuesta no confirmada.; Trabajo que puede continuar: Implementar y probar destinos actuales enR-02.
- ID: operacion; Responsable: Desarrollo propone; Wascar valida necesidades de su entorno; Por concretar: Concretar host/nombre/CA/subred, retención y objetivosRPO/RTO/latencias; no pedir al usuario diseñar criptografía.; Trabajo que puede continuar: Preparar valores editables/documentados y ensayos acotados.
- date: 2026-10-29; Estado: Confirmado por Wascar:45días, existentes desde activación y exención del administrador global. Sustituye configure-first-login inmediato; resto de negativos y pesos intactos. No implica MFA disponible en QA.; Referencia: docs/DECISION-MFA-GRACIA-45-DIAS-29-10-2026.md

## Investigación o prueba técnica todavía necesaria

Son preguntas acotadas con salida verificable, no tareas indefinidas de estudiar ni nuevas funciones por defecto:

| Qué falta determinar | Cómo se resuelve | Resultado al que pertenece |
|---|---|---|
| Acceso de la cuenta estándar a claves y transición disco/DB al rotarlas | Proveedor real, fallos forzados, ACL y recuperación en otro SID | F-04 a F-06 |
| Portabilidad de secretos/PKI y cifrado de backup | Restore en otro Windows con clave correcta, incorrecta y ausente | F-02, F-05, R-03, R-04 |
| Comportamiento real de SCM y del CRT cuando requiere reinicio | Instalación limpia, parada, fallos y reinicio del host | W-02, W-03 |
| Copia USB/UNC con NAS ausente o disco lleno | Copia local previa, verificación, retención y restauración por destino | R-01, R-02 |
| Mapeo de extensiones RC9, doble ocupación e identidad documental | Fixtures acotados de importación/exportación y round-trip | P-01 a P-06 |
| Límites de latencia/memoria con diez usuarios | Fijar umbrales antes de medir; optimizar sólo cuellos demostrados | E-06 |
| Reproducción limpia y rutas de PDB | Aprovisionamiento pinado y construcción desde entorno nuevo | E-02 |
| PDF nativo y circuitos internos Dose | Resolver alcance explícitamente; no retirar impresión/modelo ya contratados | P-07, I-07, D4/D5 |

## Herramientas y fases futuras: separadas del cierre del producto

No tener un plugin no es por sí solo un fallo del producto. La siguiente relación conserva propuestas y trabajo técnico sin convertir cada herramienta en función obligatoria:

- Tema: PostgreSQL MCP restricted/rol sólo lectura; Estado: Propuesta rev4 C.2 pendiente en laboratorio dedicado; Tratamiento: Herramienta de desarrollo; no requisito funcional adicional. Nunca conectar MCP con runtimeQA de escritura ni a datos reales por inercia.
- Tema: pg_stat_statements/hypopg/Redis/índices/caché; Estado: C.2/C.3: necesidad y soporte no medidos; Tratamiento: Medir primero. Carga10sesiones/S-48 es cierre producto asignado a C6; herramienta/caché no obligatoria, no cachear autorización privada.
- Tema: xUnit/Testcontainers/PostgreSql; Estado: Proyecto/locks existentes; PG contenedorizado omitido en LEAO por Docker ausente; Tratamiento: Obligación de veracidad de pruebas: ejecutar en host adecuado si se cierra esa adopción de tooling y hacer fallar CI si falta Docker. No invalida ni sustituye PG nativo17 ya ejecutado; no añadir Docker al instalador del usuario.
- Tema: SAST/Strix; Estado: SAST pendiente; Strix diferido a sandbox aislado con backup probado; Tratamiento: Revisión SQLi/XSS/seguridad final es producto. Herramienta concreta Strix y Docker no son requisito de runtime ni autorizan escanear VM/red/dominio. Resultados y falsos positivos se clasifican.
- Tema: CI local/manual, CodeQL/Dependabot; Estado: Workflow local preparado; remoto/licencia/publicación no autorizados; Tratamiento: Puede consolidarse CI local; no exigir GitHub/publicación para completar producto Windows.
- Tema: Skills/agents externos, Playwright, Serilog, DbUp, EF Core; Estado: Skills.NET individuales instaladas; perfiles RackClick existentes; E2E Edge/Node/PG vigentes; Tratamiento: No son funciones pendientes del producto por ausencia de otra herramienta. No introducir EF Core ni reemplazar runner/CSRF/auditoría/RC9.
- Tema: AD/OIDC/Entra/GPO/grupos anidados/S5; Estado: Fuera de primera build o etapa posterior contractual; Tratamiento: No incorporar como cierre obligatorio S1–S4. Mantener seguimiento separado. No convertir lector interno en portal externo sin contrato.

Roadmap y condiciones de alcance:

- Tema: S-50 paquetes de campo con retorno; Referencia: docs/CIERRE-RESTANTE.md; docs/CONTRATO-SERVIDOR-v0.1.md; Motivo: S5 posterior a S1–S4; no confundir con import/export JSON normal.; desglose: Definir el paquete de trabajo de campo, la identidad de la base y su revisión de salida.; Delimitar clientes/capacidades que se pueden llevar y devolver; excluir secretos de sesión.; Comparar los cambios de campo con las revisiones actuales y mostrar conflictos sin sobrescribirlos.; Validar y aplicar el retorno de forma transaccional e idempotente, con auditoría.; Ensayar desconexión, paquete alterado, conflicto y retorno duplicado antes de ofrecerlo al operador.
- Tema: AD/OIDC, forest/GPO/grupos anidados; Referencia: docs/CIERRE-RESTANTE.md; docs/CONTRATO-SERVIDOR-v0.1.md; Motivo: Fuera de primera build; autorización local por grupos y MFA permanecen.; desglose: Si se solicita federación real, elegir protocolo/proveedor y reglas de vinculación de cuentas.; Definir revocación, grupos externos, fallback y relación con MFA local sin eliminar autorización por cliente.; Diseñar migración y pruebas sólo tras incorporar formalmente ese alcance; el árbol visual de administración local no depende de integrar Active Directory.

## Fuentes antiguas que no deben generar otra vez trabajo cerrado

- old: AUTENTICACION-MFA-S1/IMPLEMENTACION-REV4: no existe migración014, librería TOTP ni endpoints; esquema13.; current: 014/Otp.NET/TOTP/cifrado/login gate/verify y esquema14 existen en desarrollo. Lo correcto es MFA incompleto y sin proveedor/GUI de producción, no inexistente.; Referencia: docs/REVISION-M3-CORRECCIONES-CODEX.md; docs/REVISION-D14-05-CODEX.md
- old: M3-01/02/03/05 siguen abiertos: migración, reset pendiente, política y CSRF de desafío.; current: Corregidos en alcance probado por revisión M3 posterior; no volver a implementarlos. Falta integrar/verificar conjunto final y completar M3/M4/M5/M6.; Referencia: docs/REVISION-M3-CORRECCIONES-CODEX.md
- old: M3-04 caducidad tras bloqueo de política sigue abierta.; current: Corregida y acreditada independientemente11/11 sobre DLLf11, con esperas reales por usuario/política/desafío. Mantener fecha/build; no trasladar como HTTP final.; Referencia: evidence/s1-20261023/distribucion14-decision/CIERRE.md
- old: C1-11 no hay test que lea secretos en logs y sólo hay evidencia durable.; current: test_c1_log_secrets lee stdout/stderr real; revisión independiente10/10 baseline43e490 y C1 repetido10/10 db5aa9. Queda cobertura de cambios MFA/candidata actual y canal de servicio real, no una fuga probada.; Referencia: docs/C1-CONCILIACION-S38-S42.md; evidence/s1-20261023/c1-logs-d2/REVISION.md; docs/REVISION-M3-CORRECCIONES-CODEX.md
- old: D2 v1 no aprobada por ACL y bloqueo de recuperación; D2v2 aún no revisada.; current: V1 superada; v2 tiene revisión favorable condicionada. Custodia/ubicación final Wascar y proveedor/transiciones/ensayos reales siguen pendientes.; Referencia: docs/DECISION-D2-CUSTODIA-CLAVE-TOTP.md; docs/REVISION-D2-CODEX.md
- old: Auditoría administrativa mínima sólo4/21; faltan17capturas y GUI.; current: 21/21formas y GUI tipada implementadas/probadas/revisadas17oct. Plan4/21 es histórico; no queda rehacer17capturas ni inventar backfill.; Referencia: docs/API-ADMIN-AUDITORIA-CONTEXTO-21-S1.md; docs/GUI-AUDITORIA-CONTEXTO-55.md; evidence/s1-20261017/quince-tandas-55-59/CIERRE.md
- old: Paquete sólo transporta aplicación13 y todos los operadores rechazan14.; current: App03/schema14 e9/DLL19c y operadores14 existen. Bundle14-07/instalador06 ejecutan preparation New/Restore privados; cadena actual no es la13 antigua. Persisten D14-07 y edition; SCM/Windows limpio y entrega final pendientes.; Referencia: docs/REVISION-D14-05-CODEX.md; docs/REVISION-INSTALADOR14-06-CODEX.md
- old: D14-05 conserva desafíos MFA en Restore; D14-06 rompe13→13.; current: Ambos cerrados en sus alcances: Restore13→14/14→14 revoca desafíos/sesiones con auditoría; operadorlegacy13→13 corregido/revisado. No acredita canje MFA HTTP ni custodia.; Referencia: docs/REVISION-D14-05-CODEX.md
- old: No se ha ejecutado instalación alguna de14.; current: Preparación privada real New/Restore14 ejecutada. Sigue sin ejecutarse instalador de servicios/SCM, cuenta Windows real ni reboot en nueva WindowsServer para candidata actual.; Referencia: docs/REVISION-INSTALADOR14-06-CODEX.md
- old: Obligatoriedad MFA para todos antes de producción sigue por decidir.; current: Confirmada21oct. D3/D7 son control por usuario/excepción temporal QA; falta implementar transición, no volver a decidir obligación.; Referencia: docs/IMPLEMENTACION-REV4.md; docs/METODOLOGIA-PARA-CLAUDE.md
- old: No hay runner SQL/CSRF/auditoría/rate limiter ni autorización/panel; habría que añadir DbUp/EF/Serilog/AD.; current: Esas bases existen. Mantener Npgsql directo/migraciones SQL y controles actuales; cierres se hacen con evidencia y huecos concretos, sin sustituciones por herramienta.; Referencia: docs/IMPLEMENTACION-REV4.md; docs/C1-CONCILIACION-S38-S42.md
- MATRIZ-TRANSFERENCIA.csv y la tabla R3 de MAPA-RC9-R3.md son históricas: describen ausencias ya implementadas.
- La tabla51 de MATRIZ-INVENTARIO-PENDIENTE.md se corrige con sus actualizaciones52–185 y C2 del25.10.
- MAPA-ENTREGA.json contiene notas antiguas contradictorias, por ejemplo compartir/paletas pendientes junto a sus integraciones posteriores.
- No localizar prueba de una variante no demuestra ausencia de su código. No usar un rechazo seguro como prueba de cumplimiento de una función faltante.

## Orden de ejecución y reparto

1. Cerrar W-01 y preparar una edición coherente de ensayo. Reutilizar el bundle si sus bytes no cambian; no reconstruir los históricos05 como requisito nuevo.
2. En paralelo independiente: MFA/proveedor/enrolamiento y GUI C2/importación. Un solo propietario por archivo; revisión distinta sobre cambios ya estabilizados. Las pruebasHTTP de laboratorio no tienen que esperar a la decisión de custodia productivaD2.
3. Integrar una candidata coordinada, no una publicación por cada documento. Reutilizar pruebas válidas no afectadas y correr regresión pertinente una vez.
4. Instalar en otra VM limpia; servicio, HTTPS, reinicio, backup/restore y recuperación. Después QA por módulos a ritmo de Wascar y adopción.

Las pruebas del usuario no son el único trabajo pendiente: la mayoría de los pasos de este inventario corresponde a desarrollo, integración, operación y revisión.

## Mantener el cálculo

Fuente editable: [PLAN-CIERRE-RACKCLICK.json](PLAN-CIERRE-RACKCLICK.json). Al cambiar un subpaso, registrar estado y evidencia; no marcar done por existir código o generar un ZIP. El último subpaso de cada tarea exige referencia de revisión distinta.

```powershell
& 'C:/Python312/python.exe' -X utf8 -B tools/progress_report.py --write
```

Comprobar coherencia sin modificar los informes:

```powershell
& 'C:/Python312/python.exe' -X utf8 -B tools/progress_report.py --check
```

El generador valida alcance fijado, pesos, IDs, cobertura de criterios y existencia de evidencias; no puede decidir que una prueba fue suficiente ni ejecuta pruebas del producto. El cierre se revisa por una persona/agente distinto del implementador. Regenera también CIERRE-METRICA.json y MAPA-ENTREGA.json; el mapa anterior está archivado como histórico.
