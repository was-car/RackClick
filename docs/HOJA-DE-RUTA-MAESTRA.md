# Hoja de ruta maestra de RackClick

30.10.2026 · Entrada única para continuar el proyecto. Integra el cierre existente, las peticiones de Wascar, la comparación RC10 y el catálogo de fabricantes. No declara implementado lo que sólo está investigado.

**Abrir este documento al planificar.** [Registro completo JSON](REGISTRO-REQUISITOS-MAESTRO.json) · [Trazabilidad de las 302 acciones](TRAZABILIDAD-RC10-MAESTRA.csv) · [Conciliación de documentos](CONCILIACION-PLANES-30-10-2026.md).

## Estado que se conserva

El servidor 10 funciona con PostgreSQL 17, servicio Windows/HTTPS y MFA real probado por Wascar. Los 10 clientes originales ya se cargaron con su inventario y la seguridad conservada. Hay jerarquía, Click-Click, grupos/permisos, plantillas/favoritos y varios formatos de exportación. Faltan resultados de integración, recuperación, variantes y aceptación; no se comienza otro piloto.

El cierre cuantificado mantiene 53 resultados (50 con peso y 3 controles), 280 subpasos y 23 acreditados. Son comprobaciones de cierre, no 280 funciones que haya que escribir. Las 302 acciones RC10 son detalle trazado; el catálogo nuevo es una ampliación diferenciada.

## Qué falta, por bloques

| Bloque | Trabajo que falta cerrar |
|---|---|
| F · Seguridad/MFA | Clasificación de hallazgos reales; configuración SQL y secretos recuperables; custodia/ACL finales; sobre portable, rotación, códigos y emergencia del último administrador; reautenticación y matriz final. Conservar panel/login/gracia de 45 días ya construidos. |
| I · Inventario y colaboración | Variantes de conectores/caras/PoE, reconexión y lotes por IDs/grupo/tipo; compensación/rehacer seguro, concurrencia GUI, Dosen/finales y decisión separada sobre terminales internos. |
| A · Administración | Recorrido más visual de usuarios/grupos/ámbitos, aceptación de C1 vigente, auditoría fuera de las21 formas y retención/correlación. La autorización sigue en servidor. |
| P · Paridad RC9/RC10 | Import/export JSON normal y merge/round-trip; branding/técnico/logo; PNG y cierre de formatos; herramientas/atajos; racks primero, detalles plegables, avisos, EN/DE/ES y accesibilidad. |
| W · Windows y red | Matriz soportada y negativos de cuenta/servicio; red/certificados casa-trabajo sencillos; repetición/cancelación/diagnóstico y recorrido instalado completo. New10/postboot ya probado se conserva. |
| R · Backup y recuperación | Retención, destinos local/USB/UNC, cifrado y secretos/MFA, restore completo en otro Windows, actualización/rollback y reset delimitado. Integrar operación en dashboard. |
| E · Entrega | Candidata única, build repetible, licencias/SBOM/avisos, manual final y QA por módulos, carga de 10 usuarios con demo completa y adopción. |
| C-HW · Fabricantes | Convertir investigación en catálogo curado: contrato/variantes, conectores, caras/geometría/licencias, selector, pruebas por modelo, publicación y mantenimiento. Primeros 100 perfiles es propuesta. |
| FUT · Después | Descubrimiento SNMP/LLDP/API, paquetes de campo S5 y federación AD/OIDC real; mantienen su alcance posterior. |

Rendimiento requiere medición en la candidata con datos/usuarios representativos. La lista no demuestra un fallo de PostgreSQL ni exige cambiar de base. Las mejoras se decidirán sobre resultados reproducidos.

## Peticiones de Wascar registradas

- **REQ-UX-01 · Racks primero, información secundaria plegable** → P-11 (relacionados:I-04). Rack/frontal/trasera visibles al llegar; PoE y datos extensos desplegables sin ocultar errores o cambios pendientes. Estado:pendiente_de_implementacion.
- **REQ-UX-02 · Administración de usuarios y grupos más visual** → A-02 (relacionados:P-11, F-10). Lista/búsqueda, usuario seleccionado, pertenencias, ámbitos y métodos claros; distinguir global/cliente/técnico/lector sin otorgar derechos por nombre de rol. Estado:pendiente_de_mejora_y_aceptacion.
- **REQ-UX-03 · Barra compacta de informes y exportaciones** → P-07 (relacionados:P-11). Acciones agrupadas por rack/cliente; controles técnicos extensos bajo demanda; formato de cada descarga identificado correctamente. Estado:pendiente_de_presentacion.
- **REQ-UX-04 · Datos sintéticos completos y repetibles para QA** → E-05 (relacionados:P-01, E-06). Mantener los10clientes originales en C y preparar carga opcional verificable para futuros laboratorios sin reemplazar cuentas ni MFA. Estado:carga_actual_hecha_facilidad_repetible_pendiente.
- **REQ-UX-05 · Exportar/importar inventario y backup desde dashboard** → R-04 (relacionados:R-01, R-03, P-01, P-03, F-05). Separar intercambio JSON de copia PostgreSQL/secretos. Acceso administrativo, progreso, integridad, destino nuevo y recuperación MFA comprobada; no sobrescribir una base silenciosamente. Estado:pendiente_de_integracion.
- **REQ-UX-06 · Operación sencilla entre casa y trabajo** → W-04 (relacionados:W-05, E-04). Nombre/origen/red/certificado coherentes y mantenimiento guiado, sin otra secuencia manual de editar varios archivos; no modificar la IP de Windows sin instrucción. Estado:herramientas_existentes_cierre_facilidad_pendiente.
- **REQ-UX-07 · Acceso privado del operador y datos de conexión DB** → E-04 (relacionados:F-02, W-03). Indicar cómo obtener credenciales locales autorizadas de cada instancia y usar HeidiSQL cuando proceda; nunca incluir contraseñas en manuales públicos o ZIP documental. Estado:conciliar_documentacion_y_acceso_privado.
- **REQ-UX-08 · MFA propio y administrativo con política confirmada** → F-10 (relacionados:F-07, F-08, F-09, F-11). Conservar gracia de 45 días/exención global/avisos, control servidor y ausencia de secretos ajenos; cerrar recuperación, últimos administradores y reautenticación. Estado:implementado_parcial_cierre_y_recuperacion_pendientes.
- **REQ-UX-09 · Avisos multiusuario comprensibles** → P-09 (relacionados:I-05, A-03). Otro usuario ve qué cambió y dónde, sin perder su borrador ni inventar contexto histórico; ámbitos y revocación vigentes. Estado:implementacion_existente_matriz_final_pendiente.
- **REQ-UX-10 · QA y manual paso a paso para una sola persona** → E-05 (relacionados:E-04, E-07). Ubicación/botón/campo, resultado esperado, rol, disponibilidad y candidata; conservar Pass/NotPass/observaciones y exportación de Wascar. Estado:proceso_existente_mantener_por_candidata.

## Catálogo de fabricantes: ampliación trazada

[Alcance completo](ALCANCE-CATALOGO-FABRICANTES.md) · [Visor de consulta](../CATALOGO-HARDWARE.html). 12.008definiciones comunitarias y144 racks no son12.152plantillas aprobadas. 195 registros primarios pueden solaparse;19 tienen campos físicos parciales. Fechas/revisiones desconocidas se conservan. No se instala PacketTracer ni se copian fotos por estar publicadas.

- **C-HW-01 · Inventario de fabricantes, modelos y fuentes** — investigacion_entregada_no_plantillas_integradas. Conservar12.008definiciones/144 racks/195 registros primarios con su procedencia y límites.
- **C-HW-02 · Contrato y normalización de catálogo de fabricantes** — pendiente. Identidad/SKU/revisión, conectores, cara/geometría, montaje, módulos, puertos combo y mapeos rechazados explícitamente.
- **C-HW-03 · Selección y validación del primer catálogo curado** — propuesto_100_perfiles_no_implementado. Propuesta100 perfiles: 12 Sophos,16 Fortinet,12 Palo Alto,20 Cisco,12 Aruba,8 Synology,8 QNAP,6 racks,6 UPS/PDU; no es el total del mercado ni cantidad aprobada lista.
- **C-HW-04 · Selector por marca/familia/modelo y vistas físicas** — pendiente. Reutilizar catálogo/favoritos/plantillas; frontal/trasera y puertos clicables con recursos propios o licencia comprobada.
- **C-HW-05 · Prueba por modelo y revisión independiente** — pendiente. Comparar con manuales, crear instancias UUID distintas, conservar cables, recargar/otra sesión y probar negativos de ámbito/combo/modular.
- **C-HW-06 · Publicación y actualización del catálogo** — pendiente. Versión/manifiesto/digest, compatibilidad y rollback sin alterar instancias existentes; incluir en candidata y guía QA.
- **C-HW-07 · Ampliación y mantenimiento de cobertura** — planificado_sin_censo_total_acreditado. Ventana objetivo2018–2026 y equipos históricos instalados; fechas desconocidas nulas, nuevos modelos por el mismo proceso, búsqueda/rendimiento medidos.

## Evolución posterior y referencias

- **FUT-01 · Descubrimiento de red e integración de recolectores** — evolucion_posterior. Evaluar SNMPv3, LLDP/CDP y API/LibreNMS/Netdisco/GLPI/Lansweeper; observaciones separadas de documentación y aprobación de cambios. Sin escanear redes ni deducir cableado pasivo.
- **FUT-02 · Trabajo de campo offline y retorno con conflictos** — S5_posterior. Paquetes por cliente/revisión/capacidad, sin secretos de sesión; merge de cambios, conflictos, transacción e idempotencia. No confundir con importar JSON normal.
- **FUT-03 · Federación real AD/OIDC y grupos externos** — fuera_de_primera_entrega. Sólo si se incorpora esa ampliación: vinculación de identidad, grupos, revocación y fallback. La presentación tipoEntra no implica implementar un forest/GPO.

Las alternativas investigadas también quedan registradas, con su disposición. No se implementa cada repositorio como una función obligatoria:

- **REF-01 · REA y Codebase Memory.** Mapa/búsqueda de código para el equipo; no funcionalidad de documentación de red para el usuario.
- **REF-02 · Patchdocs y Pathfinder.** Ideas funcionales/de presentación y condiciones de acceso; no dependencia ni instalador integrado.
- **REF-03 · LibreNMS, Netdisco, GLPI Agent, NetXMS y Lansweeper.** Evaluar API, compatibilidad y licencia antes de elegir una integración; no instalar todos los productos.
- **REF-04 · NetBox, DeviceType Library, RackScope y demás biblioteca local.** Reutilizar definiciones/conceptos compatibles con fuentes/licencias; catálogo concreto enC-HW y sin sustituir el servidor RackClick.
- **REF-05 · ESEngine y otros proyectos descargados.** Conservar procedencia/decisión; no convertir cada repositorio en una función que hay que implementar.
- **REF-06 · Skills, plugins y herramientas de pruebas.** Usar herramientas detectadas y pertinentes; no falta instalar más por defecto ni se puntúa su número.
- **OPS-01 · Continuidad del repositorio privado y publicaciones revisadas.** Repositorio was-car/RackClick privado. Actualizacion seleccionada de fuentes congeladas de candidata 10, inventario sintetico original sin seguridad, guia de fuentes oficiales y arranque de laboratorio reproducible. Sin binarios del instalador por condiciones de redistribucion abiertas; sin despliegue en QA. No puntua el cierre de producto por publicar codigo.

## Cómo queda integrada la información

| Documento | Papel |
|---|---|
| HOJA-DE-RUTA-MAESTRA.md | Punto de entrada humano y orden de trabajo. |
| REGISTRO-MAESTRO-CONFIG.json | Contexto vigente, peticiones y frentes; se edita aquí la parte manual. |
| REGISTRO-REQUISITOS-MAESTRO.json | Registro generado:53 resultados/280 subpasos,302correspondencias y ampliaciones/referencias. |
| PLAN-CIERRE-RACKCLICK.json | Ledger congelado de pesos, estados acreditados y evidencias. No se cambia por subdividir. |
| Matriz/plan RC10 | Definición detallada de acciones; cada O-ID se vincula a un resultado existente. |
| Alcance/catálogo de fabricantes | Fuentes, modelos y aceptación del frente C-HW; separado del catálogo instalado. |
| Protocolo de evolución | Investigación futura; conserva lo hablado sin convertirlo en dependencia de entrega. |
| QA-CASOS-WASCAR.json y guías | Casos ejecutables por candidata, roles y disponibilidad; resultados de Wascar separados/conservados. |

Una decisión explícita más reciente de Wascar prevalece sobre resúmenes históricos. La custodia está confirmada; MFA45/exención global rigen la ejecución. F-05 y F-10 tienen resúmenes antiguos en el ledger; el contexto vigente se muestra en este registro. Antes de acreditar criterios incompatibles se debe conciliar la versión del ledger, preservando pesos y evidencia. No se pide de nuevo una decisión ya tomada.

## Procedimiento para cada trabajo

1. Abrir esta hoja, elegir resultado existente o identificador de ampliación y anotar el problema/resultado concreto. Un bug o variante se adjunta a su resultado; no genera puntos nuevos.
2. Definir archivos/responsable, dependencias y aceptación; aprovechar código/investigación existente. Separar implementador y revisor. No asignar a dos personas el mismo archivo sin coordinación.
3. Implementar en laboratorio independiente y probar el cambio afectado. Registrar fuente/build/hash/entorno, negativo cuando corresponda y resultado; una prueba histórica conserva su fecha.
4. Integrar sólo la revisión aceptada en una candidata compatible. Actualizar QA visible con ubicación/botón/campo/resultado y disponibilidad real. No reemplazar notas o PASS de Wascar.
5. Acreditar sólo el subpaso comprobado, actualizar continuidad/changelog y regenerar esta hoja. Informar ID, qué avanzó, prueba, qué falta y si cambió o no la métrica.
6. Si un requisito es realmente nuevo y se incorpora al compromiso de entrega, explicar corte/alcance y versionar la base antes de ponderarlo. El catálogo y la investigación futura no alteran automáticamente100 puntos.

Regeneración documental desde la raíz: C:/Python312/python.exe -B tools/build_master_roadmap.py --write. Para verificar: mismo comando con --check. Sólo escribe los tres artefactos generados; no instala, cambia el ledger, DB, VM, GUI o QA.

## Siguiente grupo propuesto

- **SIG-01 · Racks primero e informes compactos** (REQ-UX-01, REQ-UX-03, P-11, P-07). Cambio GUI acotado, prueba de navegador con datos originales, revisión distinta y guion QA.
- **SIG-02 · Contrato del catálogo por fabricante** (C-HW-02). Esquema/mapeos/variantes y selección inicial trazada; sin importar miles de YAML automáticamente.
- **SIG-03 · Cerrar recuperación portable MFA de la instalación** (F-05, F-06, R-03, R-04). Recorrido técnico end-to-end reutilizando componentes existentes; revisar primero el corte seguro y las pruebas necesarias.

Estas tres salidas pueden prepararse con archivos/responsables separados; sus dependencias se revisan antes de implementar. Este bloque sólo consolida documentos; no inicia esas tres tandas, instalaciones o ensayos VM.

Después:intercambio JSON/backup desde dashboard, administración visual, paridad restante y primera selección de modelos; finalmente integración Windows/restore/carga/QA/adopción. Seguridad y recuperación necesarias para producción siguen siendo condiciones de entrega.

## Lista completa de resultados base

A continuación están los53 resultados existentes con su avance acreditado, contexto y cierre. Los280 subpasos literales y evidencias están en el JSON maestro; los criterios que necesitan conciliación se señalan. «Sin crédito» no significa que no exista código.

### F · Fundamento, seguridad y MFA

#### F-01 · Clasificar hallazgos de secretos y tratar sólo credenciales reales

- **Cierre acreditado:** 0/4 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Escáner Gitleaks/hook fijados y revisados; no falta instalar otro escáner. El barrido guardó coincidencias, no un historial limpio.
- **Resultado que falta cerrar:** Cada candidato/indeterminado tiene clasificación y resolución verificables; credenciales reales expuestas revocadas/rotadas de forma coordinada; comprobación focal de fuentes/paquete sin exposición.
- **Fuentes:** [IMPLEMENTACION-REV4.md](IMPLEMENTACION-REV4.md); [CIERRE.md](../evidence/s1-20261021/rev4-fundamento/CIERRE.md)

#### F-02 · Cifrar configuración SQL y recuperar sus secretos en otra instancia

- **Cierre acreditado:** 0/4 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Connection string runtime permanece en archivo privado protegido por ACL y texto plano. DPAPI de otros secretos del instalador no acredita cifrado de ésta.
- **Resultado que falta cerrar:** El secreto SQL no queda en claro en el archivo entregado/configuración recuperable; servicio estándar arranca y Restore nuevo funciona mediante procedimiento documentado, sin secretos en logs/paquetes.
- **Fuentes:** [IMPLEMENTACION-REV4.md](IMPLEMENTACION-REV4.md); [RECUPERACION-DESPLIEGUE-WINDOWS-S1.md](RECUPERACION-DESPLIEGUE-WINDOWS-S1.md); [REVISION-INSTALADOR14-06-CODEX.md](REVISION-INSTALADOR14-06-CODEX.md)

#### F-03 · Registrar decisión de custodia y ubicación definitiva D2

- **Cierre acreditado:** 1/3 subpasos; 0,00/0,00 puntos. Estado:parcial_acreditado.
- **Lo que hay:** La custodia y recuperación fueron confirmadas por Wascar el25.10. No pedirlas de nuevo; falta completar su concreción y comprobación técnica.
- **Resultado que falta cerrar:** Decisión de Wascar identificada y especificación D2 final sin ambigüedad sobre responsables, almacén, pérdida total, recuperación y límites; revisión técnica separada de la aceptación operativa.
- **Fuentes:** [DECISIONES-MFA-CONFIRMADAS-25-10-2026.md](DECISIONES-MFA-CONFIRMADAS-25-10-2026.md)

#### F-04 · Implementar proveedor TOTP Windows bajo la identidad real del servicio

- **Cierre acreditado:** 1/4 subpasos; 0,62/2,50 puntos. Estado:parcial_acreditado.
- **Lo que hay:** En C Windows Server2025 limpia, candidata 10 instala almacén dedicado e inicia proveedor Windows DPAPI bajo cuenta estándar SCM. Enrolamiento y nuevo login TOTP por HTTPS verificados antes y después del reinicio. Negativos de pérdida de clave/versión y arranque cerrado conciliados con las fuentes actuales. No se cierra la recuperación portable ni todos los negativos de ACL/otros tokens.
- **Resultado que falta cerrar:** Servicio real lee/descifra y verifica factores; otra cuenta no lee, servicio no escribe ni modifica ACL, management no se amplía; negativos y revisión independiente registrados.
- **Fuentes:** [Program.cs](../development/server/src/RackClick.Server/Program.cs); [MfaStore.cs](../development/server/src/RackClick.Server/MfaStore.cs); [MfaSecretCipher.cs](../development/server/src/RackClick.Server/MfaSecretCipher.cs); [DECISION-D2-CUSTODIA-CLAVE-TOTP.md](DECISION-D2-CUSTODIA-CLAVE-TOTP.md); [REVISION-D2-CODEX.md](REVISION-D2-CODEX.md)

#### F-05 · Integrar y cerrar la recuperación portable de claves MFA

- **Cierre acreditado:** 0/5 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Existen codec, payload, lector/escritor y exportación/recuperación por componentes L2d–L2g revisados. Falta el recorrido completo de recuperación de la instalación y coherencia con sus backups; no reimplementar el codec desde cero.
- **Resultado que falta cerrar:** Restore nuevo verifica factores usando clave recuperada; sin material/contraseña correctos falla explícitamente, sin emitir sesión insegura; negativos y revisión independiente.
- **Fuentes:** [REVISION-MFA-L2D-CODEX-26-10-2026.md](REVISION-MFA-L2D-CODEX-26-10-2026.md); [REVISION-MFA-L2F-CODEX-26-10-2026.md](REVISION-MFA-L2F-CODEX-26-10-2026.md); [REVISION-MFA-L2G-CORRECCION-CODEX-26-10-2026.md](REVISION-MFA-L2G-CORRECCION-CODEX-26-10-2026.md)

#### F-06 · Cerrar rotación y recuperación coherente entre anillo y PostgreSQL

- **Cierre acreditado:** 0/4 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Anillo versionado/rotación propuestos; atomicidad de un archivo no cubre publicación de claves más commit DB.
- **Resultado que falta cerrar:** Cada punto de interrupción tiene estado recuperable demostrado; todos los factores/backups retenidos siguen descifrables con versiones conservadas y faltantes se rechazan explícitamente.
- **Fuentes:** [DECISION-D2-CUSTODIA-CLAVE-TOTP.md](DECISION-D2-CUSTODIA-CLAVE-TOTP.md); [REVISION-D2-CODEX.md](REVISION-D2-CODEX.md)

#### F-07 · Completar enrolamiento restringido cuando MFA sea exigible

- **Cierre acreditado:** 4/5 subpasos; 2,00/2,50 puntos. Estado:parcial_acreditado.
- **Lo que hay:** Enrolamiento, login MFA, GUI y gracia de 45 días tienen trabajo acreditado; Wascar probó MFA administrativo en candidata 10. Falta el cierre integral del resultado y sus escenarios pendientes, no crear otra pantalla de login.
- **Resultado que falta cerrar:** Cuando se exige MFA o se inicia enrolamiento, el desafío no concede acceso API; confirmar un factor válido emite una única sesión nueva, con negativos de concurrencia y revisión. Respetar la gracia de 45 días y exención global confirmadas, sin bloquear de golpe todas las cuentas nuevas.
- **Fuentes:** [MFA-DASHBOARD-GRACIA-45-29-10-2026.md](MFA-DASHBOARD-GRACIA-45-29-10-2026.md); [RESULTADOS.md](../evidence/s1-20261029/installer10-vm-codex/RESULTADOS.md)

#### F-08 · Implementar códigos de recuperación y reenrolamiento restringido

- **Cierre acreditado:** 0/5 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Tabla app_mfa_recovery_code existe; generación/entrega/consumo y transición posterior no demostrados como flujo de producto.
- **Resultado que falta cerrar:** Cada código sirve una sola vez incluso en concurrencia; recuperación no abre API antes del estado autorizado; reenrolamiento y revocación/auditoría sin secretos probados por revisor distinto.
- **Fuentes:** [014-mfa.sql](../development/server/database/014-mfa.sql); [DECISION-D2-CUSTODIA-CLAVE-TOTP.md](DECISION-D2-CUSTODIA-CLAVE-TOTP.md); [REVISION-D2-CODEX.md](REVISION-D2-CODEX.md); [PLAN-MFA-Y-FRENTES-C1-C5.md](PLAN-MFA-Y-FRENTES-C1-C5.md)

#### F-09 · Implementar recuperación local cuando no quedan clave, sobre ni códigos

- **Cierre acreditado:** 0/5 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** La recuperación CLI actual revoca sesiones y desafíos; D14-05 lo acredita. No equivale al flujo local de emergencia de pérdida total MFA.
- **Resultado que falta cerrar:** Administrador recupera acceso mediante enrolamiento nuevo después de pérdida total simulada; no se borra inventario ni se reactivan sesiones; ninguna ruta remota permite eludir factor.
- **Fuentes:** [REVISION-D14-05-CODEX.md](REVISION-D14-05-CODEX.md); [DECISION-D2-CUSTODIA-CLAVE-TOTP.md](DECISION-D2-CUSTODIA-CLAVE-TOTP.md); [REVISION-D2-CODEX.md](REVISION-D2-CODEX.md); [RecoveryAdministrator.cs](../development/server/src/RackClick.Server/RecoveryAdministrator.cs)

#### F-10 · Cerrar política y administración MFA conforme a gracia de 45 días

- **Cierre acreditado:** 0/5 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** El panel propio/por usuario y la política de 45 días ya se implementaron. La regla vigente es45 días, cuentas existentes desde activación y exención del administrador global Systemhaus; administradores de cliente no están exentos. El resumen y dos criterios congelados del ledger contienen redacción anterior: conciliarlos formalmente antes de acreditar F-10, sin reabrir una decisión de Wascar.
- **Resultado que falta cerrar:** Panel y servidor aplican gracia de 45 días a usuarios/técnicos/administradores de cliente, fecha de activación para existentes y exención del administrador global; protegen sesiones, reautenticación, métodos ajenos y recuperación/último administrador, con negativos y revisión independiente.
- **Fuentes:** [DECISION-MFA-GRACIA-45-DIAS-29-10-2026.md](DECISION-MFA-GRACIA-45-DIAS-29-10-2026.md); [MFA-DASHBOARD-GRACIA-45-29-10-2026.md](MFA-DASHBOARD-GRACIA-45-29-10-2026.md)
- **Conciliar redacción antes de acreditar:** F-10.03, F-10.04; aplicar la decisión45 días/exención global vigente.

#### F-11 · Integrar segundo paso y todos los formularios de reautenticación

- **Cierre acreditado:** 0/5 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** RackClickApi.login sigue password→csrf→me; no gestiona202 como desafío. La GUI RC9 vigente no ofrece MFA.
- **Resultado que falta cerrar:** Login y cada familia de reauth completan factor para mismo actor, conservan borrador y recuperan respuesta sin duplicar; navegador/ENDEES revisados antes de habilitar QA.
- **Fuentes:** [api.ts](../development/frontend/src/api.ts); [AUTENTICACION-MFA-S1.md](AUTENTICACION-MFA-S1.md); [PLAN-MFA-Y-FRENTES-C1-C5.md](PLAN-MFA-Y-FRENTES-C1-C5.md)

#### F-12 · Acreditar MFA y fundamento sobre la candidata completa por HTTP/HTTPS

- **Cierre acreditado:** 0/5 subpasos; 0,00/0,00 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** HTTP y GUI MFA/gracia de 45 días revisados en laboratorio15; Browser8etapasPASS y Quality378PASS/1Dockeromitida. Proveedor sintético de DI separado, no custodia productiva final/HTTPS de la candidata. F-12.03/.04/.05 pendientes.
- **Resultado que falta cerrar:** Evidencia identifica bytes/esquema/proveedor/entorno y demuestra flujos positivos/negativos MFA completos más controles afectados; ninguna omisión pasa por éxito, sin anunciar QA/producción por pruebas del almacén.
- **Fuentes:** [CIERRE.md](../evidence/s1-20261023/distribucion14-decision/CIERRE.md); [REVISION-M3-CORRECCIONES-CODEX.md](REVISION-M3-CORRECCIONES-CODEX.md); [REVISION-D14-05-CODEX.md](REVISION-D14-05-CODEX.md); [REVISION-INSTALADOR14-06-CODEX.md](REVISION-INSTALADOR14-06-CODEX.md); [MAPA-ENTREGA.json](MAPA-ENTREGA.json); [REVISION-MFA-L1-CODEX-25-10-2026.md](REVISION-MFA-L1-CODEX-25-10-2026.md); [MENSAJE-PARA-CLAUDE-MFA-L1-HTTP-25-10-2026.md](MENSAJE-PARA-CLAUDE-MFA-L1-HTTP-25-10-2026.md); [CIERRE.md](../evidence/s1-20261025/mfa-l1-revision-codex/CIERRE.md); [REVISION-SEGURIDAD.md](../evidence/s1-20261025/mfa-l1-revision-codex/REVISION-SEGURIDAD.md); [REVISION-MFA-L1-RONDA2-CODEX-25-10-2026.md](REVISION-MFA-L1-RONDA2-CODEX-25-10-2026.md); [CIERRE.md](../evidence/s1-20261025/mfa-l1-ronda2-codex/CIERRE.md); [REVISION-SEGURIDAD.md](../evidence/s1-20261025/mfa-l1-ronda2-codex/REVISION-SEGURIDAD.md); [RESULTADO-REGRESION-ORIGINAL.json](../evidence/s1-20261025/mfa-l1-ronda2-codex/RESULTADO-REGRESION-ORIGINAL.json); [RESULTADO-RUNTIME-Y-CLI.json](../evidence/s1-20261025/mfa-l1-ronda2-codex/RESULTADO-RUNTIME-Y-CLI.json); [MFA-DASHBOARD-GRACIA-45-29-10-2026.md](MFA-DASHBOARD-GRACIA-45-29-10-2026.md); [RESULTADOS.md](../evidence/s1-20261029/mfa-dashboard-codex/RESULTADOS.md)

### I · Jerarquía, inventario y colaboración

#### I-01 · Ofrecer e integrar Deshacer de crecimiento/reducción pura de grupos

- **Cierre acreditado:** 4/7 subpasos; 1,43/2,50 puntos. Estado:parcial_acreditado.
- **Lo que hay:** I-01.01/02/03/04 completos técnicamente en laboratorio. Consulta, reintento y cancelación originales; invalidación por revisión, permiso, cuenta y cliente con vías de diálogo/edición rápida protegidas. Ensayo READ sin EDIT con Edge/PostgreSQL 17.11 PASS 21,83 s y revisión distinta de la matriz acumulada. I-01.05/06/07 pendientes: candidata coordinada, QA disponible y cierre del resultado completo.
- **Resultado que falta cerrar:** Ambas inversas puras funcionan en GUI con UUID/atributos/fechas/extremos exactos; conflictos/revocación/replay/rollback sin pérdida ni éxito falso; build/hash, prueba, revisión distinta y QA registrados.
- **Fuentes:** [C2-EVIDENCIA-GRUPOS-25-10-2026.md](C2-EVIDENCIA-GRUPOS-25-10-2026.md); [C2-INVERSA-CRECIMIENTO-25-10-2026.md](C2-INVERSA-CRECIMIENTO-25-10-2026.md); [C2-INVERSA-REDUCCION-25-10-2026.md](C2-INVERSA-REDUCCION-25-10-2026.md); [CIERRE.md](../evidence/s1-20261025/c2-inversa-reduccion-codex/CIERRE.md); [InventoryPanel.jsx](../development/frontend/src/InventoryPanel.jsx); [C2-GUI-GRUPOS-25-10-2026.md](C2-GUI-GRUPOS-25-10-2026.md); [CIERRE.md](../evidence/s1-20261025/c2-gui-grupos-codex/CIERRE.md); [REVISION.md](../evidence/s1-20261025/c2-gui-grupos-codex/REVISION.md); [C2-CONSULTA-PENDIENTE-25-10-2026.md](C2-CONSULTA-PENDIENTE-25-10-2026.md); [CIERRE.md](../evidence/s1-20261025/c2-query-codex/CIERRE.md); [REVISION.md](../evidence/s1-20261025/c2-query-codex/REVISION.md); [C2-CONTEXTO-OPERACION-25-10-2026.md](C2-CONTEXTO-OPERACION-25-10-2026.md); [CIERRE.md](../evidence/s1-20261025/c2-context-codex/CIERRE.md); [REVISION.md](../evidence/s1-20261025/c2-context-codex/REVISION.md); [C2-REVISION-PERMISOS-25-10-2026.md](C2-REVISION-PERMISOS-25-10-2026.md); [CIERRE.md](../evidence/s1-20261025/c2-eligibility-codex/CIERRE.md); [REVISION.md](../evidence/s1-20261025/c2-eligibility-codex/REVISION.md); [C2-EDICIONES-RAPIDAS-25-10-2026.md](C2-EDICIONES-RAPIDAS-25-10-2026.md); [CIERRE.md](../evidence/s1-20261025/c2-instant-codex/CIERRE.md); [REVISION.md](../evidence/s1-20261025/c2-instant-codex/REVISION.md); [C2-MATRIZ-RECUPERACION-25-10-2026.md](C2-MATRIZ-RECUPERACION-25-10-2026.md); [CIERRE.md](../evidence/s1-20261025/c2-permission-codex/CIERRE.md); [EDGE-PG.json](../evidence/s1-20261025/c2-permission-codex/EDGE-PG.json); [REVISION-I0103.md](../evidence/s1-20261025/c2-permission-codex/REVISION-I0103.md)

#### I-02 · Cerrar alcance restante de compensación colaborativa y Rehacer

- **Cierre acreditado:** 0/6 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** implementacion: Existen atributos seis campos/aliasRJ45 y API puras de grupos. No undo general/redo; mixtos/reordenamientos, roles/properties, mover/borrar/conexiones carecen de inversa general.; integracion: Atributos integrados históricamente; puras fuera de14.; prueba: Rechazos seguros y pruebas acotadas no cumplen inversas faltantes.; revision: Sin revisión de catálogo completo de compensaciones.; qa: QA36/59 atributos; no aceptación del contrato general.
- **Resultado que falta cerrar:** Tabla completa soportado/no soportado y motivo; toda inversa prometida tiene prueba de cambios ajenos y QA; un rechazo422 nunca se cuenta como undo cumplido.
- **Fuentes:** [CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md); [C2-CONCILIACION-INVENTARIO.md](C2-CONCILIACION-INVENTARIO.md); [API-COMPENSACION-POE-S1.md](API-COMPENSACION-POE-S1.md); [C2-INVERSA-REDUCCION-25-10-2026.md](C2-INVERSA-REDUCCION-25-10-2026.md)

#### I-03 · Cerrar matriz RC9 de conector, cara, rol eléctrico y presupuesto PoE

- **Cierre acreditado:** 0/6 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** implementacion: UUID/grupo/tipo, PoE OFF/null≠0, cara única, roles AC y resumen agregado ya existen. Pair no exige igualdad universal de familias de datos ni presupuesto agregado.; integracion: Integradas históricamente QA13; combinación14 final sin acreditar.; prueba: 54-C/23.10 casos concretos;63–68 resumen. Sin matriz completa de presets/conectores/caras/roles.; revision: Favorable acotada; no matriz integral.; qa: QA27/35/59; S-23 visual parcial.
- **Resultado que falta cerrar:** Matriz finita sin huecos para combinaciones prometidas, ligada a evidencia o límite explícito; identidad/cables persisten. No certificación de circuito/medio/transceptor/suministro.
- **Fuentes:** [C2-CONCILIACION-INVENTARIO.md](C2-CONCILIACION-INVENTARIO.md); [CONTRATO-INVENTARIO-S1.md](CONTRATO-INVENTARIO-S1.md); [CIERRE.md](../evidence/s1-20261017/tres-tandas-54/CIERRE.md); [CIERRE.md](../evidence/s1-20261017/seis-tandas-63-68/CIERRE.md)

#### I-04 · Cerrar variantes de jerarquía, racks, equipos y orden ya implementados

- **Cierre acreditado:** 5/7 subpasos; 1,79/2,50 puntos. Estado:parcial_acreditado.
- **Lo que hay:** I-04.01–05 completos técnicamente en laboratorio. Borrado individual de final conectado y lote Dose+equipo: cinco conjuntos de impacto exactos, cancelaciones SQL/operaciones/auditoría intactas, dos commits y cable ajeno conservado. Regresión de lote, permisos/replay/conflicto y persistencia comprobados. I-04.06/07 pendientes: candidata final integrada, revisión y aceptación.
- **Resultado que falta cerrar:** Cada operación ofrecida tiene trayectoria positiva/negativos pertinentes por versión; huecos de evidencia cerrados sin declarar funciones inexistentes; QA visible de Wascar.
- **Fuentes:** [MATRIZ-INVENTARIO-PENDIENTE.md](MATRIZ-INVENTARIO-PENDIENTE.md); [CIERRE.md](../evidence/s1-20261017/tres-tandas-52/CIERRE.md); [CIERRE.md](../evidence/s1-20261017/tres-tandas-53/CIERRE.md); [CIERRE.md](../evidence/s1-20261017/quince-tandas-55-59/CIERRE.md); [CIERRE.md](../evidence/s1-20261017/tres-tandas-61/CIERRE.md); [C2-CATALOGO-JERARQUIA-25-10-2026.md](C2-CATALOGO-JERARQUIA-25-10-2026.md); [CIERRE.md](../evidence/s1-20261025/c2-catalogue-codex/CIERRE.md); [CATALOGO.json](../evidence/s1-20261025/c2-catalogue-codex/CATALOGO.json); [REVISION-I0401.md](../evidence/s1-20261025/c2-catalogue-codex/REVISION-I0401.md); [C2-PERMISOS-BORRADO-25-10-2026.md](C2-PERMISOS-BORRADO-25-10-2026.md); [CIERRE.md](../evidence/s1-20261025/c2-delete-permission-codex/CIERRE.md); [REVISION.md](../evidence/s1-20261025/c2-delete-permission-codex/REVISION.md); [EDGE-PG.json](../evidence/s1-20261025/c2-delete-permission-codex/EDGE-PG.json); [C2-NOMBRES-DESTINOS-RACK-25-10-2026.md](C2-NOMBRES-DESTINOS-RACK-25-10-2026.md); [CIERRE.md](../evidence/s1-20261025/c2-rack-variants-codex/CIERRE.md); [EDGE-PG.json](../evidence/s1-20261025/c2-rack-variants-codex/EDGE-PG.json); [REVISION.md](../evidence/s1-20261025/c2-rack-variants-codex/REVISION.md); [C2-DUPLICADO-VARIANTES-25-10-2026.md](C2-DUPLICADO-VARIANTES-25-10-2026.md); [CIERRE.md](../evidence/s1-20261025/c2-duplicate-variants-codex/CIERRE.md); [EDGE-PG-VARIANTES.json](../evidence/s1-20261025/c2-duplicate-variants-codex/EDGE-PG-VARIANTES.json); [REGRESION-EXISTENTE.json](../evidence/s1-20261025/c2-duplicate-variants-codex/REGRESION-EXISTENTE.json); [REVISION.md](../evidence/s1-20261025/c2-duplicate-variants-codex/REVISION.md); [C2-ORDEN-TACTIL-25-10-2026.md](C2-ORDEN-TACTIL-25-10-2026.md); [CIERRE.md](../evidence/s1-20261025/c2-order-variants-codex/CIERRE.md); [REVISION.md](../evidence/s1-20261025/c2-order-variants-codex/REVISION.md); [C2-BORRADO-IMPACTO-25-10-2026.md](C2-BORRADO-IMPACTO-25-10-2026.md); [CIERRE.md](../evidence/s1-20261025/c2-delete-impact-codex/CIERRE.md); [REVISION.md](../evidence/s1-20261025/c2-delete-impact-codex/REVISION.md)

#### I-05 · Cerrar variantes de Click-Click, lotes, reconexión y cables

- **Cierre acreditado:** 0/6 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** implementacion: Todas las familias existen, incluida GUI57 de pares atómicos y cinco patch/nota/color/desconexión58.; integracion: Históricamente QA29/30; combinación14 no probada por esas ejecuciones.; prueba: PG competencia/uncommit/ámbitos; GUI incertidumbre/reserved/412 y edición. No matriz visual completa cross/roles/carreras/reconexión reservada/cancelar.; revision: Acotada y con atribución de recorridos realmente repetidos.; qa: Casos disponibles históricos no equivalen a aprobación.
- **Resultado que falta cerrar:** Todas las variantes prometidas conservan extremos/identidad/atributos, atomicidad y Click-Click; pruebas/revisión y QA visibles vinculados a versión.
- **Fuentes:** [GUI-LOTE-CONEXIONES-57.md](GUI-LOTE-CONEXIONES-57.md); [QA-CONEXIONES-EDICION-58.md](QA-CONEXIONES-EDICION-58.md); [CIERRE.md](../evidence/s1-20260928/impacto-reconexion-04/CIERRE.md); [CIERRE.md](../evidence/s1-20261017/quince-tandas-55-59/CIERRE.md)

#### I-06 · Completar verificación de Dosen y finales ya soportados en sala

- **Cierre acreditado:** 1/6 subpasos; 0,42/2,50 puntos. Estado:parcial_acreditado.
- **Lo que hay:** I-06.02 cerrado técnicamente: Edge/PG17.11 PASS32,719s,16 commits para todos los campos ofrecidos en Dose/final, roles power en puertos sin cable, gn repetido por grupo/ID, metadatos/cables exactos,7 rechazos atómicos y persistencia. Regresión edición nueva PASS27,562s. Revisión distinta3focos/13mutaciones. Borrado individual/conjunto con impacto aceptado en I-04.05, evidencia anterior identificada. No completa soporte/plantillas/AP, rutas/informes/revocación, ocupación lógica, integración o QA de I-06.
- **Resultado que falta cerrar:** Operaciones externas de Dose/final probadas como objetos de sala con topología/ámbitos exactos y QA; cualquier aplazamiento tiene decisión expresa.
- **Fuentes:** [CONTRATO-INVENTARIO-S1.md](CONTRATO-INVENTARIO-S1.md); [GUI-TRASLADO-SALA-S1.md](GUI-TRASLADO-SALA-S1.md); [CIERRE.md](../evidence/s1-20261017/tres-tandas-62/CIERRE.md); [API-CATALOGO-BASE-S1.md](API-CATALOGO-BASE-S1.md); [API-EDITOR-PLANTILLA-PRIVADA-S1.md](API-EDITOR-PLANTILLA-PRIVADA-S1.md); [METODOLOGIA-PARA-CLAUDE.md](METODOLOGIA-PARA-CLAUDE.md); [REVISION-C2-OBJETOS-SALA-CODEX-25-10-2026.md](REVISION-C2-OBJETOS-SALA-CODEX-25-10-2026.md); [CIERRE.md](../evidence/s1-20261025/c2-room-object-codex/CIERRE.md); [REVISION.md](../evidence/s1-20261025/c2-room-object-codex/REVISION.md); [MENSAJE-PARA-CODEX-C2-SALA-ENTREGA-25-10-2026.md](MENSAJE-PARA-CODEX-C2-SALA-ENTREGA-25-10-2026.md); [C2-CAMPOS-SALA-25-10-2026.md](C2-CAMPOS-SALA-25-10-2026.md); [CIERRE.md](../evidence/s1-20261025/c2-room-fields-codex/CIERRE.md); [REVISION-INDEPENDIENTE.md](../evidence/s1-20261025/c2-room-fields-codex/REVISION-INDEPENDIENTE.md); [C2-BORRADO-IMPACTO-25-10-2026.md](C2-BORRADO-IMPACTO-25-10-2026.md); [CIERRE.md](../evidence/s1-20261025/c2-delete-impact-codex/CIERRE.md); [REVISION.md](../evidence/s1-20261025/c2-delete-impact-codex/REVISION.md)

#### I-07 · Decidir modelo de terminales y pasos internos de Dose/panel

- **Cierre acreditado:** 0/4 subpasos; 0,00/0,00 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** implementacion: No modelo acordado/implementado de entrada fija+salida latiguillo simultáneas; face no crea terminal.; integracion: No integrado por falta de contrato físico explícito.; prueba: Conexiones externas no demuestran continuidad interna.; revision: Sin diseño pasante adoptado.; qa: No anunciado/disponible como ruta completa.
- **Resultado que falta cerrar:** Decisión trazable soporte/límite revisada. Si incluida, implementación/pruebas/QA propias. No deducir continuidad por una cara ni bloquear automáticamente CRUD externo.
- **Fuentes:** [CONTRATO-INVENTARIO-S1.md](CONTRATO-INVENTARIO-S1.md); [CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md); [C2-CONCILIACION-INVENTARIO.md](C2-CONCILIACION-INVENTARIO.md); [METODOLOGIA-PARA-CLAUDE.md](METODOLOGIA-PARA-CLAUDE.md)

### A · Usuarios, grupos y administración

#### A-01 · Cerrar atribución técnica C1 S-38 a S-42 en la candidata vigente

- **Cierre acreditado:** 0/5 subpasos; 0,00/1,25 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** API y panel ya existen, con pruebas históricas y regresión C1 10/10 M3 db5aa9. No está demostrado un defecto nuevo de esos mecanismos; tampoco se transfieren a app03/VM por defecto.
- **Resultado que falta cerrar:** S-38..42 tienen atribución actual y regresión pertinente posterior a cambios, conservando límites. Logs stdout/stderr ya ensayados no se declaran universalmente ausentes de secretos.
- **Fuentes:** [C1-CONCILIACION-S38-S42.md](C1-CONCILIACION-S38-S42.md); [REVISION-M3-CORRECCIONES-CODEX.md](REVISION-M3-CORRECCIONES-CODEX.md); [REVISION.md](../evidence/s1-20261023/c1-logs-d2/REVISION.md); [REVISION-D14-05-CODEX.md](REVISION-D14-05-CODEX.md)

#### A-02 · Completar aceptación visual del recorrido administrativo existente

- **Cierre acreditado:** 0/5 subpasos; 0,00/1,25 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Alta guiada, grupos de personas/clientes separados, relaciones UUID, efectivos con origen, sesiones y auditoría ya implementados/integrados históricamente. Preview administración-arbol no certifica producto ni sustituye estos recorridos.
- **Resultado que falta cerrar:** Resultados por caso/build conservados y observaciones administrativas resueltas/aceptadas expresamente por Wascar. Disponible no equivale a Pass; relación/árbol no se reinventa como AD.
- **Fuentes:** [C1-CONCILIACION-S38-S42.md](C1-CONCILIACION-S38-S42.md); [UX-ADMINISTRACION-ARBOL.md](UX-ADMINISTRACION-ARBOL.md); [INTEGRACION-ALTA-GRUPOS-WINDOWS-QA-S1.md](INTEGRACION-ALTA-GRUPOS-WINDOWS-QA-S1.md); [GUI-AUDITORIA-CONTEXTO-55.md](GUI-AUDITORIA-CONTEXTO-55.md); [QA-CASOS-WASCAR.json](QA-CASOS-WASCAR.json)

#### A-03 · Conciliar y cerrar atribución de auditoría fuera de las21 formas administrativas

- **Cierre acreditado:** 0/5 subpasos; 0,00/1,25 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** 21 formas ya capturan contexto mínimo y tienen GUI tipada. El mapa mantiene parcial cobertura/atribución de otras acciones, especialmente inventario/intercambio/operación; no hay autorización para rellenar histórico ausente.
- **Resultado que falta cerrar:** Cada acción contratada actual tiene cobertura mínima o limitación explícita sin inventar histórico; cambios y registro atómicos probados y lectura administrativa entendible.
- **Fuentes:** [API-ADMIN-AUDITORIA-CONTEXTO-21-S1.md](API-ADMIN-AUDITORIA-CONTEXTO-21-S1.md); [CIERRE.md](../evidence/s1-20261017/quince-tandas-55-59/CIERRE.md); [GUI-AUDITORIA-CONTEXTO-55.md](GUI-AUDITORIA-CONTEXTO-55.md); [MAPA-ENTREGA.json](MAPA-ENTREGA.json); [CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md)

#### A-04 · Cerrar retención operativa, correlación y recuperación de operaciones antiguas

- **Cierre acreditado:** 0/5 subpasos; 0,00/1,25 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Operaciones y auditoría durables existentes; consulta administrativa paginada y contexto ya implementados. No hay política completa de purga/caducidad; marcas canceladas no se purgan para evitar reejecución antigua.
- **Resultado que falta cerrar:** Política explícita y comprobada en frontera30d, sin resucitar operaciones canceladas ni afirmar éxito incierto; auditoría/logs consultables/correlacionables sin secretos y manual fiel.
- **Fuentes:** [CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md); [OPERACIONES-PENDIENTES.md](OPERACIONES-PENDIENTES.md); [API-ADMIN-AUDITORIA-S1.md](API-ADMIN-AUDITORIA-S1.md); [IMPLEMENTACION-REV4.md](IMPLEMENTACION-REV4.md); [001-foundation.sql](../development/server/database/001-foundation.sql)

### P · Paridad funcional y visual RC9

#### P-01 · Convertir restauración RC9 de laboratorio en importación normal

- **Cierre acreditado:** 0/7 subpasos; 0,00/1,36 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** El Full Backup original ya se cargó en C conservando seguridad/MFA. El auxiliar fijado al original no equivale a importación JSON normal desde dashboard, que sigue pendiente.
- **Resultado que falta cerrar:** Usuario capacitado importa archivo desde GUI/API con diez clientes/jerarquía/topología correctos, sin aplanamiento ni restos; evidencia/version/revisión/QA.
- **Fuentes:** [RESULTADOS.md](../evidence/s1-20261029/rc9-demo-original-codex/RESULTADOS.md); [QA-DATOS-ORIGINALES-MFA10-WASCAR.md](QA-DATOS-ORIGINALES-MFA10-WASCAR.md)

#### P-02 · Previsualizar inválidos y doble ocupación sin perder enlaces

- **Cierre acreditado:** 0/6 subpasos; 0,00/1,36 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** implementacion: Conversor lab rechaza connection_occupied; no UI staging que conserve y muestre ambos enlaces incompatibles completos.; integracion: Sin preview de colisiones de producto localizado.; prueba: Golden RC9 justifica requisito; rechazo no es preview íntegro.; revision: No revisión de staging/resolución completo.; qa: No habilitado.
- **Resultado que falta cerrar:** Se ven ambos enlaces y el original se conserva; ningún commit normal sin resolver, fallos sin restos, revisión distinta y QA.
- **Fuentes:** [CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md); [ACEPTACION.md](ACEPTACION.md); [rc9_restore.py](../tools/windows/rc9_restore.py); [RESTAURACION-QA-RC9.md](RESTAURACION-QA-RC9.md)

#### P-03 · Exportar JSON actual y original exacto como funciones distintas

- **Cierre acreditado:** 0/6 subpasos; 0,00/1,36 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** implementacion: GETproject es consultaSQL, no exportRC9. Original/mapeos archivados por herramienta lab; no rutas/UI exportJSON/original localizadas en producto. R3 histórico es distinto.; integracion: Sin flujo producto actual/original identificado.; prueba: Preservación original y reportes exactos no prueban exportJSONnormal.; revision: Sin revisión de ese flujo.; qa: No disponible como exportJSONnormal.
- **Resultado que falta cerrar:** Actual refleja commits vigentes y original conserva hash; funciones separadas respetan permisos, prueba/revisión/QA por versión.
- **Fuentes:** [CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md); [MAPA-RC9-R3.md](MAPA-RC9-R3.md); [rc9_restore.py](../tools/windows/rc9_restore.py); [Program.cs](../development/server/src/RackClick.Server/Program.cs); [InventoryPanel.jsx](../development/frontend/src/InventoryPanel.jsx)

#### P-04 · Demostrar round-trip JSON y preservar extensiones

- **Cierre acreditado:** 0/6 subpasos; 0,00/1,36 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** implementacion: properties/rc9OriginalId conservan parte de datos; metadata global no modelada sólo archivada. Sin exportactual→reimport completo.; integracion: Depende de P-01/P-03.; prueba: Comparación conversión10tablas no es round-trip sin cambios.; revision: Conversión sí; round-trip completo no.; qa: No caso producto completo aceptado.
- **Resultado que falta cerrar:** Cada formato prometido tiene ida/vuelta reproducible, diferencias permitidas documentadas y sin pérdida de campos/IDs/extensiones, con revisión.
- **Fuentes:** [ACEPTACION.md](ACEPTACION.md); [CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md); [RESTAURACION-QA-RC9.md](RESTAURACION-QA-RC9.md); [rc9_restore.py](../tools/windows/rc9_restore.py); [CIERRE.md](../evidence/s1-20261020/arranque-y-datos-rc9/CIERRE.md)

#### P-05 · Cerrar lista de herramientas RC9 restantes y sus equivalentes

- **Cierre acreditado:** 0/6 subpasos; 0,00/1,36 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** implementacion: Referencias loadJSON/importRackJSON/mergeProject/importCSV/irAppendProject y saveSnapshot/restoreSnapshot/irDownloadCurrentRescue; equivalentes completos de producto no localizados. No afirmar ausencia sólo por un nombre histórico.; integracion: BackupPG operativo es C5, no estas herramientas de inventario.; prueba: No ejecución servidor actual de esas familias acreditada.; revision: Lista de equivalencias/restantes por revisar.; qa: Sin guiones de equivalencia identificados.
- **Resultado que falta cerrar:** Desaparece rótulo genérico herramientasrestantes: lista cerrada, equivalentes/diferencias aceptadas y pruebas/revisión/QA de incluidas; S5/backup separados.
- **Fuentes:** [MAPA-RC9-R3.md](MAPA-RC9-R3.md); [CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md); [CIERRE-RESTANTE.md](CIERRE-RESTANTE.md); [Program.cs](../development/server/src/RackClick.Server/Program.cs); [InventoryPanel.jsx](../development/frontend/src/InventoryPanel.jsx)

#### P-06 · Persistir identidad documental del cliente y branding RC9

- **Cierre acreditado:** 0/6 subpasos; 0,00/1,36 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** implementacion: ReportesHTML omiten Systemhaus/logo/técnico; XLSHTML Technician vacío porque no hay campo persistido/importado. No usar actor como técnico documental.; integracion: Reportes existen; identidad documental completa no integrada.; prueba: Formatos probados, no metadata/logo nuevos.; revision: Acotada formatos existentes.; qa: S-36 identidad parcial.
- **Resultado que falta cerrar:** Campos RC9 prometidos persistidos/editables/importables/exportables y renderizados con identidad aprobada sin contenido activo; evidencia y QA.
- **Fuentes:** [CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md); [API-INFORMES-IMPRIMIBLES-S1.md](API-INFORMES-IMPRIMIBLES-S1.md); [API-XLS-HTML-RC9-S1.md](API-XLS-HTML-RC9-S1.md); [API-INFORME-RACK-SVG-S1.md](API-INFORME-RACK-SVG-S1.md); [RESTAURACION-QA-RC9.md](RESTAURACION-QA-RC9.md)

#### P-07 · Cerrar formatos existentes y resolver obligación PDF

- **Cierre acreditado:** 0/6 subpasos; 0,00/1,36 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** CSV, XLSX, SVG, HTML imprimible y XLS HTML existen y se probaron por HTTP en el laboratorio de comparación. Falta su cierre GUI/formato/aceptación; PNG y la obligación de PDF nativo se tratan explícitamente, sin confundirlos con impresión HTML.
- **Resultado que falta cerrar:** Todos formatos prometidos tienen salida/lector/impresión y permisos verificados; PDF tiene decisión y evidencia; diferencias aceptadas, no eliminadas por plan ambiguo.
- **Fuentes:** [COMPARACION-OFFLINE-RC10-SERVIDOR.md](COMPARACION-OFFLINE-RC10-SERVIDOR.md)

#### P-08 · Concluir aceptación de plantillas/favoritos/preferencias existentes

- **Cierre acreditado:** 0/6 subpasos; 0,00/1,36 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** implementacion: BASE33/7, favoritos personales, privadas+rename+editor nuevaUUID, publicar/retirar/usar compartidas, idioma/tema y paletas10tipos/28parejas existen.; integracion: Windows/QA8–13 históricos; no volver a declarar compartir/editor/paletas pendientes por notas viejas.; prueba: PG/Node/Edge por bloques; no aceptación total S-26/S-47.; revision: Distinta por bloque; combinación finalMFA requiere foco.; qa: QA46–51/55–58/66–74/79–84 históricos, no Pass automático.
- **Resultado que falta cerrar:** Cada familia S-26/S-47 probada/aceptada por actor en candidata final; sin privadas ajenas/éxitos falsos, revisión y QA, sin recrear funciones.
- **Fuentes:** [API-CATALOGO-BASE-S1.md](API-CATALOGO-BASE-S1.md); [API-FAVORITOS-PERSONALES-S1.md](API-FAVORITOS-PERSONALES-S1.md); [API-PLANTILLAS-PRIVADAS-S1.md](API-PLANTILLAS-PRIVADAS-S1.md); [API-EDITOR-PLANTILLA-PRIVADA-S1.md](API-EDITOR-PLANTILLA-PRIVADA-S1.md); [API-PLANTILLAS-COMPARTIDAS-S1.md](API-PLANTILLAS-COMPARTIDAS-S1.md); [INTEGRACION-ESQUEMA10-WINDOWS-QA-S1.md](INTEGRACION-ESQUEMA10-WINDOWS-QA-S1.md); [INTEGRACION-PALETA-CATEGORIAS-WINDOWS-QA-S1.md](INTEGRACION-PALETA-CATEGORIAS-WINDOWS-QA-S1.md)

#### P-09 · Cerrar compatibilidad y aceptación de avisos multiusuario

- **Cierre acreditado:** 0/6 subpasos; 0,00/1,36 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** implementacion: Polling5s visible, cursor/gaps, permisos actuales, borradores/Click-Click y detalle antes/después existen. Fuente actual incluye31acciones con createFromSharedTemplate; contrato428–472 describía30.; integracion: Detalle472 y extensión compartidas integrados históricamente; estructuralesC2 nuevos contexto notAvailable explícito.; prueba: 60/428–472/compartidas prueban commit/replay/rollback/aislamiento/reconexión/escala acotada; no capacidad10sesiones por ello.; revision: Distinta acotada, no combinación14MFA+C2.; qa: QA10/63–65 históricos; aceptación pendiente.
- **Resultado que falta cerrar:** Autor/acción/IDs/extremos correctos con autoridad actual; revocación detiene/limpia y borrador se conserva; límites explícitos, revisión y QA.
- **Fuentes:** [API-AVISOS-CLIENTE-S1.md](API-AVISOS-CLIENTE-S1.md); [API-AVISOS-DESCRIPTIVOS-S1.md](API-AVISOS-DESCRIPTIVOS-S1.md); [GUI-AVISOS-CLIENTE-S1.md](GUI-AVISOS-CLIENTE-S1.md); [InventoryChanges.cs](../development/server/src/RackClick.Server/InventoryChanges.cs); [InventoryChangeDetails.cs](../development/server/src/RackClick.Server/InventoryChangeDetails.cs); [CIERRE.md](../evidence/s1-20261018/sesenta-tandas-533-592/CIERRE.md)

#### P-10 · Auditar EN/DE/ES, temas y literalidad de datos

- **Cierre acreditado:** 0/6 subpasos; 0,00/1,36 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** implementacion: Tres idiomas, códigos backend localizados y preferencia idioma/tema existen. Falta auditoría integral; separador literal ? de Editar grupos sigue enInventoryPanel.; integracion: Preferencias históricasQA11/paletasQA13; nuevasGUI deben cubrirse.; prueba: Módulos EN/DE/ES/390px por bloques; no recorrido exhaustivo.; revision: UX/DOM acotadas, no lingüística integral.; qa: S-47 total pendiente.
- **Resultado que falta cerrar:** Matriz3idiomas/2temas sin texto prometido ausente/incoherente; datos intactos y capturas reales; QA deS-47 no sustituida por persistencia de idioma.
- **Fuentes:** [IMPLEMENTACION-REV4.md](IMPLEMENTACION-REV4.md); [API-PREFERENCIAS-PERSONALES-S1.md](API-PREFERENCIAS-PERSONALES-S1.md); [INTEGRACION-ESQUEMA11-WINDOWS-QA-S1.md](INTEGRACION-ESQUEMA11-WINDOWS-QA-S1.md); [InventoryPanel.jsx](../development/frontend/src/InventoryPanel.jsx); [QA-CASOS-WASCAR.json](QA-CASOS-WASCAR.json)

#### P-11 · Completar teclado, lector, contraste y paridad visual funcional

- **Cierre acreditado:** 0/6 subpasos; 0,00/1,36 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** implementacion: GUIRC9/Click-Click/SVG, ARIA/foco y status persistente848/849 existen; no auditoría integral.; integracion: 849 históricoWindows/QA11; nuevaGUI posterior debe integrarse.; prueba: Edge/AX/teclado390px/DOM acotados; voz Narrador/NVDA no acreditada. Falta flujo completo front/rear/tooltips/inspector/contraste.; revision: DOM localizadas, no certificación ni aceptaciónvisualtotal.; qa: QA78 sin lector habitual debe Bloqueado, nunca Pass automático.
- **Resultado que falta cerrar:** Matriz completa con resultados reales por versión, problemas resueltos/límites aceptados, conservando GUI/Click-Click. Voz no inferida de AX; QA de Wascar.
- **Fuentes:** [ACCESIBILIDAD-RELACIONES-GRUPOS-S1.md](ACCESIBILIDAD-RELACIONES-GRUPOS-S1.md); [INTEGRACION-AVISO-GRUPOS-WINDOWS-QA-S1.md](INTEGRACION-AVISO-GRUPOS-WINDOWS-QA-S1.md); [IMPLEMENTACION-REV4.md](IMPLEMENTACION-REV4.md); [CIERRE.md](../evidence/s1-20261018/tanda-849/CIERRE.md); [CIERRE.md](../evidence/s1-20261018/sesenta-tandas-850-909/CIERRE.md)

### W · Instalación y operación Windows

#### W-01 · Corregir parada D14-07 y validación de edición del generador

- **Cierre acreditado:** 5/5 subpasos; 2,50/2,50 puntos. Estado:cerrado_acreditado.
- **Lo que hay:** Edición07: runtimef084 integrado y presente en el payload. Guardas tempranas de edición/pins verificadas. Cierre técnico W-01 acreditado; instalación limpia/SCM/reinicio Windows permanecen pendientes en sus tareas.
- **Criterio conservado; no reabrir por este registro:** Runtime y generador de producto corregidos con negativos y revisión; ningún éxito falso de parada o paquete inseguro.
- **Fuentes:** [HALLAZGO-D14-07-PARADA-RUNTIME.md](HALLAZGO-D14-07-PARADA-RUNTIME.md); [REVISION-INSTALADOR14-06-CODEX.md](REVISION-INSTALADOR14-06-CODEX.md); [REVISION-INSTALADOR14-07-CODEX.md](REVISION-INSTALADOR14-07-CODEX.md); [REVISION-FUENTES.md](../evidence/s1-20261025/instalador14-07-codex/REVISION-FUENTES.md); [RESULTADOS.md](../evidence/s1-20261025/instalador14-07-claude/RESULTADOS.md)

#### W-02 · Instalar desde cero en Windows limpio y declarar la matriz soportada

- **Cierre acreditado:** 2/5 subpasos; 1,00/2,50 puntos. Estado:parcial_acreditado.
- **Lo que hay:** New10 en C y postboot ya están acreditados parcialmente. No repetir esa instalación para producir otro recibo; falta la matriz y escenarios restantes, incluida recuperación final y Windows11 como host cuando se ofrezca.
- **Resultado que falta cerrar:** Recorrido nuevo de instalación completo en los hosts declarados, con versiones y resultados reales; ausencia de soporte no probado indicada explícitamente.
- **Fuentes:** [RESULTADOS.md](../evidence/s1-20261029/installer10-vm-codex/RESULTADOS.md)

#### W-03 · Cuenta mínima, servicio Windows y arranque automático reales

- **Cierre acreditado:** 0/5 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Servicio estándar y arranque automático funcionaron en C. El resultado completo necesita sus negativos y comprobaciones finales de permisos/operación, sin tratarlo como servicio aún inexistente.
- **Resultado que falta cerrar:** Servicio y PostgreSQL funcionan bajo identidad mínima tras reinicio real; logs/estados y acceso privado son verificables.
- **Fuentes:** [RESULTADOS.md](../evidence/s1-20261029/installer10-vm-codex/RESULTADOS.md)

#### W-04 · HTTPS, certificados, red y acceso casa/trabajo en la edición final

- **Cierre acreditado:** 0/6 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Cambio de red fue confirmado en la instalación histórica y existen herramientas automáticas. No se traslada esa aceptación automáticamente al payload14 nuevo.
- **Resultado que falta cerrar:** Acceso LAN confiable y cambio de red con datos conservados; renovación y errores documentados, sin exponer claves privadas.
- **Fuentes:** [RACKCLICK-CASA-Y-TRABAJO.html](RACKCLICK-CASA-Y-TRABAJO.html); [CONTINUIDAD-CODEX.md](CONTINUIDAD-CODEX.md); [CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md)

#### W-05 · Repetición, cancelación, mantenimiento y diagnóstico del instalador

- **Cierre acreditado:** 0/5 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Hay preflights, archivo/retirada por identidad y reportes automáticos; experiencias históricas no equivalen a ensayo completo14 de estos recorridos.
- **Resultado que falta cerrar:** Cada fallo/cancelación tiene estado veraz y procedimiento repetible; programas/bases ajenos y cuentas manuales permanecen intactos.
- **Fuentes:** [INICIO-IMPLEMENTACION-S1.md](INICIO-IMPLEMENTACION-S1.md); [REINICIO-LIMPIO-SERVIDOR.html](REINICIO-LIMPIO-SERVIDOR.html); [REVISION-INSTALADOR14-06-CODEX.md](REVISION-INSTALADOR14-06-CODEX.md)

#### W-06 · Recorrido completo de persistencia y concurrencia del servidor instalado

- **Cierre acreditado:** 0/5 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Hay pruebas reales por bloques y New/Restore privados. Falta el recorrido integral sobre la candidata final instalada con dos sesiones y reinicio.
- **Resultado que falta cerrar:** S-55 reproducido completo y conflictos/recuperación coherentes sobre build/DB/host identificados.
- **Fuentes:** [ACEPTACION.md](ACEPTACION.md); [REVISION-INSTALADOR14-06-CODEX.md](REVISION-INSTALADOR14-06-CODEX.md)

### R · Backup, recuperación y actualización

#### R-01 · Backup programado local y retención comprobada

- **Cierre acreditado:** 0/5 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Ya hay copias nativas, programación y exportación operativa. Falta cerrar retención/fallos/restaurabilidad y facilitar su administración desde dashboard; no atribuir al botón web una existencia sólo operativa.
- **Resultado que falta cerrar:** Ejecución programada real, política de retención y fallos comprobados; sólo copias completas verificadas quedan elegibles.
- **Fuentes:** [COMPARACION-OFFLINE-RC10-SERVIDOR.md](COMPARACION-OFFLINE-RC10-SERVIDOR.md); [RESULTADOS.md](../evidence/s1-20261029/rc9-demo-original-codex/RESULTADOS.md)

#### R-02 · Destinos USB y UNC con copia local previa y tolerancia a fallos

- **Cierre acreditado:** 0/5 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** El operador básico exige disco fijo local; copiar manualmente desdeUSB/UNC no cierra el flujo operativo. D6 de aplazarUSB no está confirmada inequívocamente.
- **Resultado que falta cerrar:** Local/USB/UNC tienen prueba de copia, fallo y restauración con límites y permisos registrados.
- **Fuentes:** [ACEPTACION.md](ACEPTACION.md); [METODOLOGIA-PARA-CLAUDE.md](METODOLOGIA-PARA-CLAUDE.md); [BACKUP-RESTAURACION-WINDOWS-S1.md](BACKUP-RESTAURACION-WINDOWS-S1.md)

#### R-03 · Backup cifrado de instalación y recuperación de material privado

- **Cierre acreditado:** 0/5 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Dump de DB y ACL privadas no equivalen a backup cifrado portable de configuración, assets, certificados y claves.
- **Resultado que falta cerrar:** Copia completa cifrada y recuperable en otro host con procedimiento/material independiente; ausencia de clave no provoca fallback inseguro.
- **Fuentes:** [IMPLEMENTACION-REV4.md](IMPLEMENTACION-REV4.md); [DECISION-D2-CUSTODIA-CLAVE-TOTP.md](DECISION-D2-CUSTODIA-CLAVE-TOTP.md); [RECUPERACION-DESPLIEGUE-WINDOWS-S1.md](RECUPERACION-DESPLIEGUE-WINDOWS-S1.md)

#### R-04 · Recuperación completa en otro Windows y activación controlada

- **Cierre acreditado:** 0/5 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Restore13→14/14→14 y revocación de desafíos/sesiones están probados en laboratorios; New/Restore offline14 producen recibos reales. Falta recuperación integral del host instalado.
- **Resultado que falta cerrar:** Servicio recuperado completo y operativo en otro host con identidad nueva, integridad y revocación comprobadas; origen conservado.
- **Fuentes:** [REVISION-D14-05-CODEX.md](REVISION-D14-05-CODEX.md); [REVISION-INSTALADOR14-06-CODEX.md](REVISION-INSTALADOR14-06-CODEX.md); [RECUPERACION-DESPLIEGUE-WINDOWS-S1.md](RECUPERACION-DESPLIEGUE-WINDOWS-S1.md)

#### R-05 · Actualización y rollback compatibles con datos posteriores

- **Cierre acreditado:** 0/5 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Hay migraciónSQL y ensayos de copias/retornos privados. No es actualización en sitio probada del servicio ni retorno libre después de nuevas escrituras.
- **Resultado que falta cerrar:** Upgrade y fallos con vuelta compatible comprobados en instalación real, sin perder escrituras ni seleccionar binarios incompatibles.
- **Fuentes:** [RECUPERACION-DESPLIEGUE-WINDOWS-S1.md](RECUPERACION-DESPLIEGUE-WINDOWS-S1.md); [CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md); [REVISION-D14-05-CODEX.md](REVISION-D14-05-CODEX.md)

#### R-06 · Reset y recuperación administrativa delimitados

- **Cierre acreditado:** 0/5 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Hay herramientas de reset/archivo y recuperación administrativa. MFA/emergencia está en F-08/F-09; no es necesario rehacerlas en este bloque.
- **Resultado que falta cerrar:** Reset acotado y recuperación de acceso operativos y documentados; cancelar no modifica datos ni deja acceso omitido.
- **Fuentes:** [RECUPERAR-ADMINISTRADOR-S1.md](RECUPERAR-ADMINISTRADOR-S1.md); [ACEPTACION.md](ACEPTACION.md); [REVISION-D14-05-CODEX.md](REVISION-D14-05-CODEX.md)

### E · Paquete, manual, rendimiento y aceptación

#### E-01 · Candidata final única con fuentes y componentes compatibles

- **Cierre acreditado:** 0/5 subpasos; 0,00/1,43 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Hay candidataM3 limpia03, C2 revisado aparte y instalador06 interno. No hay una única entrega final que integre todo el alcance.
- **Resultado que falta cerrar:** Una sola candidata completa trazable y coherente, sin depender de archivos de entregas anteriores ni aceptar una mezcla no revisada.
- **Fuentes:** [REVISION-INSTALADOR14-06-CODEX.md](REVISION-INSTALADOR14-06-CODEX.md); [REVISION-D14-05-CODEX.md](REVISION-D14-05-CODEX.md); [CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md)

#### E-02 · Aprovisionamiento y construcción repetibles desde fuentes oficiales

- **Cierre acreditado:** 0/5 subpasos; 0,00/1,43 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** SDK/PG/frontend están fijados y los generadores existen. Las copiasS1/S2/S3 dependen de herramientas/artefactos y hardlinks de.local.
- **Resultado que falta cerrar:** Otra persona puede reproducir la candidata mediante el procedimiento y entradas pinadas, sin copiar.local del desarrollador.
- **Fuentes:** [REVISION-INSTALADOR14-06-CODEX.md](REVISION-INSTALADOR14-06-CODEX.md); [REVISION-D14-05-CODEX.md](REVISION-D14-05-CODEX.md); [toolchain.lock.json](../development/toolchain.lock.json)

#### E-03 · Inventario de dependencias, avisos y redistribución

- **Cierre acreditado:** 0/5 subpasos; 0,00/1,43 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** AvisoMIT completo de Otp.NET ya incorporado. La revisión general de redistribución sigue abierta; no falta añadir de nuevo ese aviso.
- **Resultado que falta cerrar:** Manifiesto y avisos completos, condiciones aplicables documentadas y cuestiones de redistribución resueltas.
- **Fuentes:** [REVISION-BUNDLE14-02-CODEX.md](REVISION-BUNDLE14-02-CODEX.md); [REVISION-INSTALADOR14-06-CODEX.md](REVISION-INSTALADOR14-06-CODEX.md); [offline-bundle14.sources.json](../development/offline-bundle14.sources.json)

#### E-04 · Manual autónomo de instalación, uso y operación

- **Cierre acreditado:** 0/6 subpasos; 0,00/1,43 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Existe manual autónomo10 con carpetas/comandos/formulario/credenciales/reinicio. Debe mantenerse y comprobarse con el paquete final y sus nuevas funciones, no volver a redactar toda la instalación desde cero.
- **Resultado que falta cerrar:** El recorrido completo funciona siguiendo sólo manual+paquete final, sin pedir archivos antiguos ni instrucciones ocultas.
- **Fuentes:** [PASOS-COMPLETOS-INSTALADOR10-WASCAR.md](PASOS-COMPLETOS-INSTALADOR10-WASCAR.md); [RESULTADOS.md](../evidence/s1-20261029/manual-autonomo10-codex/RESULTADOS.md)

#### E-05 · QA manual por módulos sobre candidata identificada

- **Cierre acreditado:** 0/5 subpasos; 0,00/1,43 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Los resultados de Wascar y la QA MFA comunicada se conservan. Dar casos pequeños por módulo/candidata; resultados antiguos de otra versión no se convierten en PASS nuevo ni se obliga a repetir lo no afectado.
- **Resultado que falta cerrar:** Casos críticos y recorridos pactados tienen resultados atribuibles; ningún resultado del usuario sobrescrito ni aprobado por el desarrollador.
- **Fuentes:** [QA-DATOS-ORIGINALES-MFA10-WASCAR.md](QA-DATOS-ORIGINALES-MFA10-WASCAR.md); [QA-CASOS-WASCAR.json](QA-CASOS-WASCAR.json)

#### E-06 · Medir carga real de diez usuarios y demo completa

- **Cierre acreditado:** 0/5 subpasos; 0,00/1,43 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** No hay resultado final de rendimiento identificado para diez usuarios y demo68racks en el host candidato. No se ha demostrado un cuello de botella concreto.
- **Resultado que falta cerrar:** Informe reproducibleS-48 demuestra datos consistentes y comportamiento aceptable con carga declarada; regresiones medidas resueltas.
- **Fuentes:** [ACEPTACION.md](ACEPTACION.md); [IMPLEMENTACION-REV4.md](IMPLEMENTACION-REV4.md); [CIERRE-RESTANTE.md](CIERRE-RESTANTE.md)

#### E-07 · Revisión final y adopción explícita de Wascar

- **Cierre acreditado:** 0/5 subpasos; 0,00/1,43 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Servidor histórico funciona según Wascar, pero la entrega final nueva no está adoptada. No corresponde anunciar100% por generar un ZIP.
- **Resultado que falta cerrar:** Conjunto final completo revisado, recorrido instalado/recuperado acreditado y confirmación de adopción de Wascar registrada.
- **Fuentes:** [ACEPTACION.md](ACEPTACION.md); [CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md); [CONTINUIDAD-CODEX.md](CONTINUIDAD-CODEX.md)

## Progreso y cierre de esta consolidación

**9,76/100 del cierre restante**, misma base RC-CIERRE-20261029-v2,53 resultados/280 subpasos/23 acreditados. **No es porcentaje global del producto.** Registrar pendientes, descargar modelos o regenerar esta hoja no suma implementación.

El cierre de esta consolidación es documental: ninguna función, plantilla o prueba de producto se acredita por este registro. Los originales y los paquetes históricos se conservan.
