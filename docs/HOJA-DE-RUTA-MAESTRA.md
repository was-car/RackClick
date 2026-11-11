# Hoja de ruta maestra de RackClick

2026-11-11 · Entrada única para continuar el proyecto. Integra el cierre existente, las peticiones de Wascar, la comparación RC10 y el catálogo de fabricantes. No declara implementado lo que sólo está investigado.

**Abrir este documento al planificar.** [Registro completo JSON](REGISTRO-REQUISITOS-MAESTRO.json) · [Trazabilidad de las 302 acciones](TRAZABILIDAD-RC10-MAESTRA.csv) · [Pasos numerados para elegir](PLAN-PENDIENTES-NUMERADO.md) · [Conciliación de documentos](CONCILIACION-PLANES-30-10-2026.md).

## Estado que se conserva

D fue actualizada en sitio a aplicación45 el03.11.2026, conservando servicio/SID/DB/cuentas/MFA/certificados/URL. HTTPS ready45 y backup real posteriorPASS, Auto/Running. Inventario actual preservado:50clientes,180racks,1561equipos/objetos,20650puertos,2202conexiones;43tablas comparadas idénticas. Catálogo884revisiones/877comerciales, selección506 intacta. Datos previos manuales no se sustituyen por cifras históricas Demo50. Windows no reiniciado para postboot45; QA/login personal posterior y cierre restante pendientes. No volver a migrar o cargar Demo50.

El cierre cuantificado mantiene 53 resultados (50 con peso y 3 controles), 280 subpasos y 55 acreditados. Son comprobaciones de cierre, no funciones nuevas que haya que escribir. Las 302 acciones RC10 son detalle trazado; el catálogo nuevo es una ampliación diferenciada.

## Qué falta, por bloques

| Bloque | Trabajo que falta cerrar |
|---|---|
| F · Seguridad/MFA | Clasificación de hallazgos reales; configuración SQL y secretos recuperables; custodia/ACL finales; sobre portable, rotación, custodia/cierre de códigos y emergencia del último administrador; reautenticación y matriz final. Conservar panel/login/gracia de 45 días ya construidos. |
| I · Inventario y colaboración | Variantes de conectores/caras/PoE, reconexión y lotes por IDs/grupo/tipo; compensación/rehacer seguro, concurrencia GUI, Dosen/finales y decisión separada sobre terminales internos. |
| A · Administración | Recorrido más visual de usuarios/grupos/ámbitos, aceptación de C1 vigente, auditoría fuera de las21 formas y retención/correlación. La autorización sigue en servidor. |
| P · Paridad RC9/RC10 | Import/export JSON normal y merge/round-trip; branding/técnico/logo; PNG y cierre de formatos; herramientas/atajos; racks primero, detalles plegables, avisos, EN/DE/ES y accesibilidad. |
| W · Windows y red | Matriz soportada y negativos de cuenta/servicio; red/certificados casa-trabajo sencillos; repetición/cancelación/diagnóstico y recorrido instalado completo. New11/postboot deD ya probado se conserva. |
| R · Backup y recuperación | Retención, destinos local/USB/UNC, cifrado y secretos/MFA, restore completo en otro Windows, actualización/rollback y reset delimitado. Integrar operación en dashboard. |
| E · Entrega | Candidata única, build repetible, licencias/SBOM/avisos, manual final y QA por módulos, carga de 10 usuarios con demo completa y adopción. |
| C-HW · Fabricantes | Selección506/506 integrada en43 y cargada enD. Cerrar QA/reservas de configuración/geometría, procedencia/licencias, publicación y mantenimiento; no repetir la autoría de esos modelos. |
| FUT · Después | Descubrimiento SNMP/LLDP/API, paquetes de campo S5 y federación AD/OIDC real; mantienen su alcance posterior. |

Rendimiento requiere medición en la candidata con datos/usuarios representativos. La lista no demuestra un fallo de PostgreSQL ni exige cambiar de base. Las mejoras se decidirán sobre resultados reproducidos.

## Peticiones de Wascar registradas

- **REQ-UX-01 · Racks primero, información secundaria plegable** → P-11 (relacionados:I-04). Rack/frontal/trasera visibles al llegar; PoE y datos extensos desplegables sin ocultar errores o cambios pendientes. Estado:implementado_y_probado_en_laboratorio_pendiente_integracion_y_qa.
- **REQ-UX-02 · Administración de usuarios y grupos más visual** → A-02 (relacionados:P-11, F-10). Lista/búsqueda, usuario seleccionado, pertenencias, ámbitos y métodos claros; distinguir global/cliente/técnico/lector sin otorgar derechos por nombre de rol. Estado:pendiente_de_mejora_y_aceptacion.
- **REQ-UX-03 · Barra compacta de informes y exportaciones** → P-07 (relacionados:P-11). Acciones agrupadas por rack/cliente; controles técnicos extensos bajo demanda; formato de cada descarga identificado correctamente. Estado:contexto_y_metadatos_de_tres_exportadores_probados_pendiente_integracion_y_resto_de_formatos.
- **REQ-UX-04 · Datos sintéticos completos y repetibles para QA** → E-05 (relacionados:P-01, E-06, C-HW-05, I-03, I-05, I-06, R-04). Demo50 y prueba de diez actores/ambitos ya realizados en laboratorio con umbrales de humo previos. D11 carga50/2553comandos verificada en185.681s y backup posterior completo; MFA/TLS del cargador probado aparte en cuenta sintetica. Faltan carga extendida instalada, memoria/CPU/consultas/picos/recuperacion y aceptacion practica, no crear de nuevo la demo. Estado:demo50_cargada_y_verificada_D11_QA_visual_pendiente.
- **REQ-UX-05 · Exportar/importar inventario y backup desde dashboard** → R-04 (relacionados:R-01, R-03, P-01, P-03, F-05). Separar intercambio JSON de copia PostgreSQL/secretos. Acceso administrativo, progreso, integridad, destino nuevo y recuperación MFA comprobada; no sobrescribir una base silenciosamente. Exportación actual RackClickInventory-v1 por cliente probada PG17.11/API/Edge,4MiB sin truncar, recibo/SHA256, sólo inventario. Importación/merge/originalRC9/backup PostgreSQL y Windows43 siguen pendientes; docs/PUNTO3-FUNCIONES-PENDIENTES.md. Estado:exportacion_JSON_actual_probada_importacion_y_backup_pendientes.
- **REQ-UX-06 · Operación sencilla entre casa y trabajo** → W-04 (relacionados:W-05, E-04). Nombre/origen/red/certificado coherentes y mantenimiento guiado, sin otra secuencia manual de editar varios archivos; no modificar la IP de Windows sin instrucción. Estado:herramientas_existentes_cierre_facilidad_pendiente.
- **REQ-UX-07 · Acceso privado del operador y datos de conexión DB** → E-04 (relacionados:F-02, W-03). Indicar cómo obtener credenciales locales autorizadas de cada instancia y usar HeidiSQL cuando proceda; nunca incluir contraseñas en manuales públicos o ZIP documental. Estado:conciliar_documentacion_y_acceso_privado.
- **REQ-UX-08 · MFA propio y administrativo con política confirmada** → F-10 (relacionados:F-07, F-08, F-09, F-11). Enrolamiento/login/GUI y politica45 existentes; F-07.01-.04 acreditados. D11 tiene proveedor real y prueba HTTPS/DPAPI de cuenta sintetica. Falta cierre integral y escenarios pendientes; no crear otro login. Codigos de recuperacion del punto3 probados en desarrollo43, no canje nativo en D. Conservar politica45 y exencion global confirmadas; recuperacion/emergencia/rotacion y aceptacion pendientes. Estado:implementado_parcial_cierre_y_recuperacion_pendientes.
- **REQ-UX-09 · Avisos multiusuario comprensibles** → P-09 (relacionados:I-05, A-03). Otro usuario ve qué cambió y dónde, sin perder su borrador ni inventar contexto histórico; ámbitos y revocación vigentes. Estado:implementacion_existente_matriz_final_pendiente.
- **REQ-UX-10 · QA y manual paso a paso para una sola persona** → E-05 (relacionados:E-04, E-07). Ubicación/botón/campo, resultado esperado, rol, disponibilidad y candidata; conservar Pass/NotPass/observaciones y exportación de Wascar. Estado:proceso_existente_mantener_por_candidata.
- **REQ-HW-MOUNT-01 · Montaje explícito y físico antes de ampliar marcas** → C-HW-02 (relacionados:C-HW-04, C-HW-05, C-HW-06). Montajes y contratos probados por familias, incluidos en43 y Demo50 de D. Conservar IDs/puertos/cables. Faltan reservas explicitadas y aceptacion, no repetir bandeja/firewall desde cero. Estado:contrato_y_catalogo43_integrados_D11_QA_pendiente.
- **REQ-HW-VISUAL-01 · Carcasa real para modelos principales y genérica para el resto** → C-HW-04 (relacionados:C-HW-01, C-HW-03, C-HW-05, C-HW-06). 506/506 seleccionados integrados con868revisiones/861comerciales; tecnica interactiva aprobada conservada. Demo50 disponible en D11; faltan aceptacion visual, reservas/fuentes y mantenimiento. Los dibujados no son fotografias redistribuidas ni todos los modelos del mercado. Estado:seleccion506_integrada_y_cargada_D11_QA_visual_pendiente.
- **REQ-CATALOGO-BUSQUEDA-01 · Selección compacta por búsqueda, sin lista larga en el rack** → C-HW-04 (relacionados:C-HW-03, C-HW-05, REQ-HW-VISUAL-01). Buscador compacto por marca/familia/modelo/SKU y alias sofos-&gt;Sophos ya integrado. Faltan QA de busqueda/teclado y excepciones de configuracion; no crear una lista larga ni volver a instalar perfiles. Estado:selector868_integrado_D11_QA_pendiente.
- **REQ-DE-CPE-01 · Routers, repetidores y familias habituales de Alemania** → C-HW-07 (relacionados:C-HW-01, C-HW-03, C-HW-04, C-HW-05). Seis routers FRITZ!/DrayTek y diez repetidores FRITZ!,TP-Link,devolo,Telekom instalados enD45 mediante actualización revisada y continuaciones registradas. Servicio/HTTPS/backup45 verificados;datos/MFA conservados. Falta revisiónvisual deWascar y resto de sondeo; selección506/pesos intactos. Estado:dieciseis_modelos_instalados_D45_QA_visual_pendiente.
- **REQ-UX-RACK-02 · Proporciones, etiquetas y desplazamiento en soportes** → P-11 (relacionados:C-HW-04, REQ-HW-VISUAL-01, REQ-UX-01, REQ-CATALOGO-BUSQUEDA-01). Mínimosporcara/objetivos24px,anchochildrelativoapadreconpisoUIacotado,ampliaciónconrelayout,captionsyrevisionesplegables,nombrescompletosconservados. Faltan aceptaciónvisualyactualizacióncompletaautorizadaenD. Laobservacióndebotonesoffline reutiliza302 acciones;noduplicarplanes. Estado:corregido_desarrollo_revision_visual_independiente_candidata_instalada_pendiente.

## Catálogo de fabricantes: ampliación trazada

[Alcance completo](ALCANCE-CATALOGO-FABRICANTES.md) · [Visor de consulta](../CATALOGO-HARDWARE.html). 12.008definiciones comunitarias y144 racks no son12.152plantillas aprobadas. 195 registros primarios pueden solaparse;19 tienen campos físicos parciales. Fechas/revisiones desconocidas se conservan. No se instala PacketTracer ni se copian fotos por estar publicadas.

- **C-HW-01 · Inventario de fabricantes, modelos y fuentes** — investigacion_entregada_no_plantillas_integradas. Conservar12.008definiciones/144 racks/195 registros primarios con su procedencia y límites.
- **C-HW-02 · Contrato y normalización de catálogo de fabricantes** — seleccion506_instalada_D11_y_demo50_verificada_cierre_QA_reservas_pendiente. 506/506 seleccionados integrados en43,868revisiones/861comerciales. New11/postboot y Demo50 verificados en D. Conservar modelos/contratos/selector; cerrar QA, reservas explicitadas, derechos/versionado y mantenimiento sin ampliar otra vez la seleccion.
- **C-HW-03 · Selección y validación del primer catálogo curado** — seleccion506_instalada_D11_y_demo50_verificada_cierre_QA_reservas_pendiente. 506/506 seleccionados integrados en43,868revisiones/861comerciales. New11/postboot y Demo50 verificados en D. Conservar modelos/contratos/selector; cerrar QA, reservas explicitadas, derechos/versionado y mantenimiento sin ampliar otra vez la seleccion.
- **C-HW-04 · Selector por marca/familia/modelo y vistas físicas** — seleccion506_instalada_D11_y_demo50_verificada_cierre_QA_reservas_pendiente. 506/506 seleccionados integrados en43,868revisiones/861comerciales. New11/postboot y Demo50 verificados en D. Conservar modelos/contratos/selector; cerrar QA, reservas explicitadas, derechos/versionado y mantenimiento sin ampliar otra vez la seleccion.
- **C-HW-05 · Prueba por modelo y revisión independiente** — seleccion506_instalada_D11_y_demo50_verificada_cierre_QA_reservas_pendiente. 506/506 seleccionados integrados en43,868revisiones/861comerciales. New11/postboot y Demo50 verificados en D. Conservar modelos/contratos/selector; cerrar QA, reservas explicitadas, derechos/versionado y mantenimiento sin ampliar otra vez la seleccion.
- **C-HW-06 · Publicación y actualización del catálogo** — seleccion506_instalada_D11_y_demo50_verificada_cierre_QA_reservas_pendiente. 506/506 seleccionados integrados en43,868revisiones/861comerciales. New11/postboot y Demo50 verificados en D. Conservar modelos/contratos/selector; cerrar QA, reservas explicitadas, derechos/versionado y mantenimiento sin ampliar otra vez la seleccion.
- **C-HW-07 · Ampliación y mantenimiento de cobertura** — seleccion506_instalada_D11_y_demo50_verificada_cierre_QA_reservas_pendiente. 506/506 seleccionados integrados en43,868revisiones/861comerciales. New11/postboot y Demo50 verificados en D. Conservar modelos/contratos/selector; cerrar QA, reservas explicitadas, derechos/versionado y mantenimiento sin ampliar otra vez la seleccion.

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

- **SIG-DE-CPE-01 · Revisión visual de Alemania, repetidores y soportes antes del paso 9** (C-HW-07, P-11, REQ-DE-CPE-01, REQ-UX-RACK-02). Wascar revisa D45 con Ctrl+F5; usar perfiles del catálogo/sala y comprobar soportes sin repetir instalación ni Demo50. Registrar observaciones. Los pasos9/10 están cerrados documentalmente; paso11 cerrado en fuentes. Postboot45/instalación limpia/Restore45 mantienen su criterio propio.
- **SIG-CIERRE-01 · Elegir un paso del inventario numerado de pendientes** (E-07, F-10, E-05). Continuar paso33/F-09.05: revisar conjuntamente F-09.01–.04, límites y entrega operativa. Reutilizar378/378,40/40 y ensayo nativo completo en E sin repetir la pérdida ni tocar D. Conciliar mantenimiento Admin, segunda pérdida/retirada posterior, candidata/operadores/manual48 y aceptación; no acreditar seis hitos por inercia.
- **SIG-RECUPERACION-02 · Cerrar recuperacion MFA portable y local de forma integrada** (F-05, F-06, F-08, F-09, R-03, R-04). F04 writer ya integrado en candidata16 completa y revisado, aceptación nativa pendiente. Completar coordinador D2/vínculo backup-material/CLI/RestoreMFA con fence-journal-marcador y cortes, reutilizando componentes/DBTOTP comprobados. No quitar guardia recovery_mfa_envelope_required o tocar D.
- **SIG-JSON-03 · Importacion JSON normal con previsualizacion y original** (P-01, P-02, P-03, P-04, REQ-UX-05). Completar importacion/merge/round-trip sin confundir cargador fijo de demo con importador general.

Estas tres salidas pueden prepararse con archivos/responsables separados; sus dependencias se revisan antes de implementar. Este bloque sólo consolida documentos; no inicia esas tres tandas, instalaciones o ensayos VM.

Después:intercambio JSON/backup desde dashboard, administración visual, paridad restante y primera selección de modelos; finalmente integración Windows/restore/carga/QA/adopción. Seguridad y recuperación necesarias para producción siguen siendo condiciones de entrega.

## Lista completa de resultados base

A continuación están los53 resultados existentes con su avance acreditado, contexto y cierre. Los280 subpasos literales y evidencias están en el JSON maestro; los criterios que necesitan conciliación se señalan. «Sin crédito» no significa que no exista código.

### F · Fundamento, seguridad y MFA

#### F-01 · Clasificar hallazgos de secretos y tratar sólo credenciales reales

- **Cierre acreditado:** 4/4 subpasos; 2,50/2,50 puntos. Estado:cerrado_acreditado.
- **Lo que hay:** F-01.01/.03 conservan su clasificación/registro técnico. F-01.02/.04 cerrados administrativamente por decisión expresa de Wascar03.11 y enmienda limitadav3: antecedente25.10 indeterminado y salida perdida, sin falso positivo, prueba de revocación ni cambios deD. Reabrir ambos y retirar5/4 si aparece evidencia concreta; no es higiene global ni aceptación de exposiciones futuras.
- **Criterio conservado; no reabrir por este registro:** Cada candidato/indeterminado tiene clasificación y resolución verificables; credenciales reales expuestas revocadas/rotadas de forma coordinada; comprobación focal de fuentes/paquete sin exposición. Excepción limitada al antecedente run-1 del25.10.2026 sin salida conservada: archivo administrativo expreso del titular con clasificación indeterminada y reapertura obligatoria si aparece evidencia concreta. No equivale a falso positivo, ausencia de exposición o revocación demostrada.
- **Fuentes:** [F01-RESOLUCION-ANTECEDENTE.md](F01-RESOLUCION-ANTECEDENTE.md); [REVISION-RESOLUCION.md](../evidence/s1-20261102/cierre-bloqueantes-01-07/f01/REVISION-RESOLUCION.md); [DECISION-F01-ARCHIVO-ADMINISTRATIVO-03-11-2026.md](DECISION-F01-ARCHIVO-ADMINISTRATIVO-03-11-2026.md); [RESULTADOS.md](../evidence/s1-20261103/f01-archivo-administrativo/RESULTADOS.md); [REVISION-ARCHIVO-ADMINISTRATIVO.md](../evidence/s1-20261103/f01-archivo-administrativo/review/REVISION-ARCHIVO-ADMINISTRATIVO.md)

#### F-02 · Cifrar configuración SQL y recuperar sus secretos en otra instancia

- **Cierre acreditado:** 4/4 subpasos; 2,50/2,50 puntos. Estado:cerrado_acreditado.
- **Lo que hay:** F-02.01–.04 cerrados: postboot13, Restore14-r2 desde backup sintético LEAO hacia E con cuenta/SID/roles/material nuevos,20clientes SQL/API,operadores/ficha/diagnóstico/backup reales y reanudación sin regeneración. Windows no se reinició tras Restore14; ese pendiente sigue en los criterios Windows, sin adopción global. D se conserva y F01 tiene disposición administrativa posterior03.11, separada del cierre técnico.
- **Criterio conservado; no reabrir por este registro:** El secreto SQL no queda en claro en el archivo entregado/configuración recuperable; servicio estándar arranca y Restore nuevo funciona mediante procedimiento documentado, sin secretos en logs/paquetes.
- **Fuentes:** [IMPLEMENTACION-REV4.md](IMPLEMENTACION-REV4.md); [RECUPERACION-DESPLIEGUE-WINDOWS-S1.md](RECUPERACION-DESPLIEGUE-WINDOWS-S1.md); [REVISION-INSTALADOR14-06-CODEX.md](REVISION-INSTALADOR14-06-CODEX.md); [RESULTADOS.md](../evidence/s1-20261102/f02-01-sql/RESULTADOS.md); [REVISION-INDEPENDIENTE.md](../evidence/s1-20261102/f02-01-sql/REVISION-INDEPENDIENTE.md); [CONTRATO-CONEXION-SQL-CIFRADA-v1.md](CONTRATO-CONEXION-SQL-CIFRADA-v1.md); [RESULTADOS.md](../evidence/s1-20261102/f02-02-operadores/RESULTADOS.md); [REVISION-INDEPENDIENTE.md](../evidence/s1-20261102/f02-02-operadores/REVISION-INDEPENDIENTE.md); [OPERADORES-SQL-CIFRADOS-v2.md](OPERADORES-SQL-CIFRADOS-v2.md); [RESULTADOS.md](../evidence/s1-20261102/f02-03-restauracion/RESULTADOS.md); [REVISION-INDEPENDIENTE.md](../evidence/s1-20261102/f02-03-restauracion/REVISION-INDEPENDIENTE.md); [REANUDACION-RESTORE-SQL-PROTEGIDO.md](REANUDACION-RESTORE-SQL-PROTEGIDO.md); [SQL-PROTEGIDO-INSTANCIA3.md](SQL-PROTEGIDO-INSTANCIA3.md); [INSTALADOR12-SQL-PROTEGIDO.md](INSTALADOR12-SQL-PROTEGIDO.md); [CIERRE-BLOQUEANTES-PASOS-01-A-07.md](CIERRE-BLOQUEANTES-PASOS-01-A-07.md); [RESULTADOS.md](../evidence/s1-20261102/cierre-bloqueantes-01-07/RESULTADOS.md); [RESULTADOS.md](../evidence/s1-20261102/vm12-e/RESULTADOS.md); [DICTAMEN-F02-01.md](../evidence/s1-20261102/vm12-e/review/DICTAMEN-F02-01.md); [RESULTADOS.md](../evidence/s1-20261103/e13-postboot-restore14/RESULTADOS.md); [DICTAMEN-F02-03-04.md](../evidence/s1-20261103/e13-postboot-restore14/review/DICTAMEN-F02-03-04.md)

#### F-03 · Registrar decisión de custodia y ubicación definitiva D2

- **Cierre acreditado:** 3/3 subpasos; 0,00/0,00 puntos. Estado:cerrado_acreditado.
- **Lo que hay:** Custodia/ubicación confirmadas25.10; F-03.02 concreta recuperación/KDF/publicación y F-03.03 registra límites LocalMachine frente a administrador/SYSTEM/servicio comprometido, con revisiones independientes. F-03 completa sólo la decisión documental. Política45 intacta; F-04..F-09/R-04 conservan sus pruebas/integraciones, sin nueva aceptación operativa o producción. D45 no operada.
- **Criterio conservado; no reabrir por este registro:** Decisión de Wascar identificada y especificación D2 final sin ambigüedad sobre responsables, almacén, pérdida total, recuperación y límites; revisión técnica separada de la aceptación operativa.
- **Fuentes:** [DECISIONES-MFA-CONFIRMADAS-25-10-2026.md](DECISIONES-MFA-CONFIRMADAS-25-10-2026.md); [D2-CONDICIONES-TECNICAS-F03-02.md](D2-CONDICIONES-TECNICAS-F03-02.md); [REVISION-INDEPENDIENTE.md](../evidence/s1-20261103/f03-02-condiciones/REVISION-INDEPENDIENTE.md); [RESULTADOS.md](../evidence/s1-20261103/f03-02-condiciones/RESULTADOS.md); [D2-LIMITES-AMENAZA-F03-03.md](D2-LIMITES-AMENAZA-F03-03.md); [REVISION-INDEPENDIENTE.md](../evidence/s1-20261103/f03-03-amenazas/REVISION-INDEPENDIENTE.md); [RESULTADOS.md](../evidence/s1-20261103/f03-03-amenazas/RESULTADOS.md)

#### F-04 · Implementar proveedor TOTP Windows bajo la identidad real del servicio

- **Cierre acreditado:** 4/4 subpasos; 2,50/2,50 puntos. Estado:cerrado_acreditado.
- **Lo que hay:** Criterios técnicos F04 conservados; writer76e6 integrado en candidata completa16/app45 con DLLReleasec057 y frontend/SQL/dependencias/servicio preservados. Bundle2018/payload117 y cadena de pins verificados; 16casos de creación+DB/TOTP sobre la DLL exacta y New/RestoreSQL45/43→45 reales en laboratorio. Propagación45 cerrada de SetupMfa/readiness/recibo y matrizRestore, sin retirar guardiaMFA. Integración de candidata acreditada con revisión independiente04.11; no instalación elevada, SCM/HTTPS/reinicio, formato mínimo3 o adopción de16. target_acceptance sigue pendiente; D/E sin cambios. Se conservan las pruebas previas de SID real/504derechos de E y núcleo del proveedor; no se atribuyen como nuevas en16.
- **Criterio conservado; no reabrir por este registro:** Servicio real lee/descifra y verifica factores; otra cuenta no lee, servicio no escribe ni modifica ACL, management no se amplía; negativos y revisión independiente registrados.
- **Fuentes:** [Program.cs](../development/server/src/RackClick.Server/Program.cs); [MfaStore.cs](../development/server/src/RackClick.Server/MfaStore.cs); [MfaSecretCipher.cs](../development/server/src/RackClick.Server/MfaSecretCipher.cs); [DECISION-D2-CUSTODIA-CLAVE-TOTP.md](DECISION-D2-CUSTODIA-CLAVE-TOTP.md); [REVISION-D2-CODEX.md](REVISION-D2-CODEX.md); [RESULTADOS.md](../evidence/s1-20261103/f04-01-almacen/RESULTADOS.md); [REVISION-INDEPENDIENTE.md](../evidence/s1-20261103/f04-01-almacen/REVISION-INDEPENDIENTE.md); [RESULTADOS.md](../evidence/s1-20261103/f04-02-permisos/RESULTADOS.md); [DICTAMEN-PREVIO-SONDA.md](../evidence/s1-20261103/f04-02-permisos/review/DICTAMEN-PREVIO-SONDA.md); [RESULTADOS.md](../evidence/s1-20261103/f04-02-permisos/ejecucion/RESULTADOS.md); [DICTAMEN-F0402.md](../evidence/s1-20261103/f04-02-permisos/ejecucion/review/DICTAMEN-F0402.md); [RESULTADO-CONSOLIDADO.json](../evidence/s1-20261103/f04-02-permisos/ejecucion/RESULTADO-CONSOLIDADO.json); [RESULTADOS.md](../evidence/s1-20261103/f04-04-cierre/RESULTADOS.md); [DICTAMEN-F0404.md](../evidence/s1-20261103/f04-04-cierre/review/DICTAMEN-F0404.md); [MATRIZ-CIERRE.md](../evidence/s1-20261103/f04-04-cierre/MATRIZ-CIERRE.md); [CONCILIACION-EVIDENCIA.json](../evidence/s1-20261103/f04-04-cierre/CONCILIACION-EVIDENCIA.json); [CONTRASTE-NUCLEO.json](../evidence/s1-20261103/f04-04-cierre/CONTRASTE-NUCLEO.json); [PASO-013-CIERRE-PROVEEDOR-MFA.md](PASO-013-CIERRE-PROVEEDOR-MFA.md); [INTEGRACION-PENDIENTES-08-18-CANDIDATA16.md](INTEGRACION-PENDIENTES-08-18-CANDIDATA16.md); [RESULTADOS.md](../evidence/s1-20261104/f04-integracion16/RESULTADOS.md); [DICTAMEN.md](../evidence/s1-20261104/f04-integracion16/review/DICTAMEN.md); [ENTREGA.json](../evidence/s1-20261104/f04-integracion16/package/ENTREGA.json); [PUBLICACION-EN-PRUEBAS.json](../evidence/s1-20261104/f04-integracion16/PUBLICACION-EN-PRUEBAS.json); [HTTP-WRITER-RELEASE-R2.json](../evidence/s1-20261104/f04-integracion16/HTTP-WRITER-RELEASE-R2.json); [NEW-RESTORE45.json](../evidence/s1-20261104/f04-integracion16/NEW-RESTORE45.json)

#### F-05 · Implementar sobre portable autenticado y restauración de claves

- **Cierre acreditado:** 5/5 subpasos; 2,50/2,50 puntos. Estado:cerrado_acreditado.
- **Lo que hay:** 04.11: candidata16 repite creación segura y DB/TOTP sobre su DLLRelease exacta; New/RestoreSQL43→45/45→45 en laboratorio pasa sin factores. Guardiacontinúa rechazando cualquier factor sin sobre; no es implementación del operador portable. Se conserva el contexto del cierre técnico anterior: F-05.01/.02/.03 concilian codec/perfil600000/negativos existentes; .04 comprueba portabilidad Windows y token estándar real con dos factores/AAD, sin repetirla. F-05.05 añade DBaplicación45 nueva, pg_dump/pg_restore custom transacciónúnica, igualdad de todas las filas públicas antes de RecoveryAdministrator y roles nuevos restringidos. ProveedorWindows real sobre material recuperado y Program/WebApplicationFactory: dos logins con factores conservados versiones1retirada/7activa, desafío sinAPI, TOTP/sesión/CSRF/API, replay/TOTPincorrecto y autoridad de backup revocada. Ocho casos pasan en WindowsPG17.11, sin omitidas, revisión independiente; sólo nuevo test/runner, sin cambios de producto. Gates de material/versiones/AAD previos son del fixture, no operador productivo. FuenteDebug F0401cd3cc/45 fijada; TestServer en memoria con identidad/confianzaWindowsLAB explícita y direcciones de cliente sintéticas para conservar limiter. F-05.04 sigue acreditando otro Windows/SIDreal, no se atribuye esa medición al TestServer. Origen invariable; tres clusters propios detenidos. Dos intentos fallidos de fixture preservados (ruta266/Win32206;contentroot/aserciónCrypto); no se ocultan ni son defectos del producto. F-05 checklist técnica completa, pero implementación operativa, candidata integrada y aceptación permanecen pendientes: no CLI/instalador, fence/journal/marcadorDBD2, exportaciónconcurrente, rotación/pérdida, HTTPS/servicio/reinicio/cutover/R04 o custodia/adopción nuevas. D/E sin operaciones.
- **Criterio conservado; no reabrir por este registro:** Restore nuevo verifica factores usando clave recuperada; sin material/contraseña correctos falla explícitamente, sin emitir sesión insegura; negativos y revisión independiente.
- **Fuentes:** [DECISION-D2-CUSTODIA-CLAVE-TOTP.md](DECISION-D2-CUSTODIA-CLAVE-TOTP.md); [REVISION-D2-CODEX.md](REVISION-D2-CODEX.md); [AUTENTICACION-MFA-S1.md](AUTENTICACION-MFA-S1.md); [REVISION-D14-05-CODEX.md](REVISION-D14-05-CODEX.md); [REVISION-MFA-L2D-CODEX-26-10-2026.md](REVISION-MFA-L2D-CODEX-26-10-2026.md); [REVISION-MFA-L2E-CODEX-26-10-2026.md](REVISION-MFA-L2E-CODEX-26-10-2026.md); [RESULTADOS.md](../evidence/s1-20261103/f05-01-sobre/RESULTADOS.md); [DICTAMEN-F0501.md](../evidence/s1-20261103/f05-01-sobre/review/DICTAMEN-F0501.md); [MATRIZ-CRITERIO.md](../evidence/s1-20261103/f05-01-sobre/MATRIZ-CRITERIO.md); [CONCILIACION-EVIDENCIA.json](../evidence/s1-20261103/f05-01-sobre/CONCILIACION-EVIDENCIA.json); [RESULTADOS.md](../evidence/s1-20261103/f05-02-coste/RESULTADOS.md); [DICTAMEN-F0502.md](../evidence/s1-20261103/f05-02-coste/review/DICTAMEN-F0502.md); [DECISION-PARAMETRO.md](../evidence/s1-20261103/f05-02-coste/DECISION-PARAMETRO.md); [MEDICION-CONCILIADA.json](../evidence/s1-20261103/f05-02-coste/MEDICION-CONCILIADA.json); [RESULTADOS.md](../evidence/s1-20261103/f05-03-negativos/RESULTADOS.md); [DICTAMEN-F0503.md](../evidence/s1-20261103/f05-03-negativos/review/DICTAMEN-F0503.md); [MATRIZ-NEGATIVOS.md](../evidence/s1-20261103/f05-03-negativos/MATRIZ-NEGATIVOS.md); [NEGATIVOS-CONCILIADOS.json](../evidence/s1-20261103/f05-03-negativos/NEGATIVOS-CONCILIADOS.json); [PASO-016-NEGATIVOS-SOBRE-MFA.md](PASO-016-NEGATIVOS-SOBRE-MFA.md); [PASO-017-RECUPERACION-PORTABLE-MFA.md](PASO-017-RECUPERACION-PORTABLE-MFA.md); [RESULTADOS.md](../evidence/s1-20261103/f05-04-portable/RESULTADOS.md); [DICTAMEN-F0504.md](../evidence/s1-20261103/f05-04-portable/review/DICTAMEN-F0504.md); [COMPROBACION-F0504.json](../evidence/s1-20261103/f05-04-portable/review/COMPROBACION-F0504.json); [POSTFLIGHT.json](../evidence/s1-20261103/f05-04-portable/ejecucion/POSTFLIGHT.json); [06-service-token.json](../evidence/s1-20261103/f05-04-portable/ejecucion/06-service-token.json); [F05-RECUPERACION-INTEGRADA-PENDIENTE.md](F05-RECUPERACION-INTEGRADA-PENDIENTE.md); [PASO-018-CIERRE-RECUPERACION-PORTABLE-MFA.md](PASO-018-CIERRE-RECUPERACION-PORTABLE-MFA.md); [RESULTADOS.md](../evidence/s1-20261103/f05-05-cierre/RESULTADOS.md); [MATRIZ-CIERRE.md](../evidence/s1-20261103/f05-05-cierre/MATRIZ-CIERRE.md); [DICTAMEN-F0505.md](../evidence/s1-20261103/f05-05-cierre/review/DICTAMEN-F0505.md); [COMPROBACION-F0505.json](../evidence/s1-20261103/f05-05-cierre/review/COMPROBACION-F0505.json); [COORDINACION-PG-R3.json](../evidence/s1-20261103/f05-05-cierre/COORDINACION-PG-R3.json); [HARNESS-FREEZE6-PREVIO-PG.json](../evidence/s1-20261103/f05-05-cierre/implementacion/HARNESS-FREEZE6-PREVIO-PG.json); [RESUMEN-SANITIZADO-CORRIDA3.json](../evidence/s1-20261103/f05-05-cierre/implementacion/RESUMEN-SANITIZADO-CORRIDA3.json); [INTEGRACION-PENDIENTES-08-18-CANDIDATA16.md](INTEGRACION-PENDIENTES-08-18-CANDIDATA16.md); [RESULTADOS.md](../evidence/s1-20261104/f04-integracion16/RESULTADOS.md); [DICTAMEN.md](../evidence/s1-20261104/f04-integracion16/review/DICTAMEN.md); [ENTREGA.json](../evidence/s1-20261104/f04-integracion16/package/ENTREGA.json); [PUBLICACION-EN-PRUEBAS.json](../evidence/s1-20261104/f04-integracion16/PUBLICACION-EN-PRUEBAS.json); [HTTP-WRITER-RELEASE-R2.json](../evidence/s1-20261104/f04-integracion16/HTTP-WRITER-RELEASE-R2.json); [NEW-RESTORE45.json](../evidence/s1-20261104/f04-integracion16/NEW-RESTORE45.json)

#### F-06 · Cerrar rotación y recuperación coherente entre anillo y PostgreSQL

- **Cierre acreditado:** 4/4 subpasos; 2,50/2,50 puntos. Estado:cerrado_acreditado.
- **Lo que hay:** F-06 cerrado en su criterio técnico con F-06.01–.04: fases, catálogo/retirada, caídas y recuperación trazados. Nueva prueba encadenada con tres backups reales retenidos, dos rotaciones a8/9 y Restore de cada generación en clúster nuevo; todos los TOTP/metadatos conservados y claves sólo referidas por backup protegidas. Cinco invocaciones PASS sin omisiones y revisión independiente con otras cinco; producto227archivos idéntico a F0603, cuyas360pruebas/15cortes se reutilizan sin repetirlas. Sin CLI pública, integración/instalador46, SID efectivo/custodia externa real o aceptación nativa. D/E intactos.
- **Criterio conservado; no reabrir por este registro:** Cada punto de interrupción tiene estado recuperable demostrado; todos los factores/backups retenidos siguen descifrables con versiones conservadas y faltantes se rechazan explícitamente.
- **Fuentes:** [PLAN-F0604-CIERRE-ROTACION.md](PLAN-F0604-CIERRE-ROTACION.md); [PASO-022-CIERRE-ROTACION-MFA.md](PASO-022-CIERRE-ROTACION-MFA.md); [RESULTADOS.md](../evidence/s1-20261111/f06-04-cierre/RESULTADOS.md); [MATRIZ-CIERRE.md](../evidence/s1-20261111/f06-04-cierre/MATRIZ-CIERRE.md); [RETENIDOS.json](../evidence/s1-20261111/f06-04-cierre/RETENIDOS.json); [FUENTES.json](../evidence/s1-20261111/f06-04-cierre/FUENTES.json); [PIN-NEGATIVO.json](../evidence/s1-20261111/f06-04-cierre/PIN-NEGATIVO.json); [DICTAMEN.md](../evidence/s1-20261111/f06-04-cierre/review/DICTAMEN.md)

#### F-07 · Completar enrolamiento restringido cuando MFA sea exigible

- **Cierre acreditado:** 5/5 subpasos; 2,50/2,50 puntos. Estado:cerrado_acreditado.
- **Lo que hay:** F-07.01–.05 cerrados técnicamente: enrolamiento restringido existente contrastado con evidencia GUI/nativa y fuentes actuales. Dos escenarios nuevos con cuentas ordinarias de gracia de 45 días vencida, Windows/DPAPI real y rol SQL restringido: desafío/pending/código inválido sin /me, clientes ni mutaciones; cookie renombrada no autoriza. Dos confirmaciones producen una única sesión/CSRF nuevos, con testigo SQL de identidad/transacción y replay rechazado. 2/2 casos,36/36 de núcleo y70/70 Node, sin omitidas; revisor distinto repite2/2. Producto227archivos conservado, sin nuevo login o política. D/E intactos. Integración de candidata objetivo y aceptación pendientes; no nuevo ensayo TLS/servicio ni cierre de emergencia/custodia externa.
- **Criterio conservado; no reabrir por este registro:** Usuario nuevo completa primer factor y obtiene única sesión nueva sólo al confirmar; desafío/enrolamiento incompleto no acceden a /me, clientes ni mutaciones; negativos concurrentes y revisión independiente.
- **Fuentes:** [PLAN-F0705-CIERRE-ENROLAMIENTO.md](PLAN-F0705-CIERRE-ENROLAMIENTO.md); [PASO-023-CIERRE-ENROLAMIENTO-MFA.md](PASO-023-CIERRE-ENROLAMIENTO-MFA.md); [RESULTADOS.md](../evidence/s1-20261111/f07-05-enrolamiento/RESULTADOS.md); [MATRIZ-CIERRE.md](../evidence/s1-20261111/f07-05-enrolamiento/MATRIZ-CIERRE.md); [HTTP-ENROLAMIENTO.json](../evidence/s1-20261111/f07-05-enrolamiento/HTTP-ENROLAMIENTO.json); [REGRESION-NUCLEO.json](../evidence/s1-20261111/f07-05-enrolamiento/REGRESION-NUCLEO.json); [FRONTEND.json](../evidence/s1-20261111/f07-05-enrolamiento/FRONTEND.json); [FUENTES.json](../evidence/s1-20261111/f07-05-enrolamiento/FUENTES.json); [PIN-NEGATIVO.json](../evidence/s1-20261111/f07-05-enrolamiento/PIN-NEGATIVO.json); [DICTAMEN.md](../evidence/s1-20261111/f07-05-enrolamiento/review/DICTAMEN.md)

#### F-08 · Implementar códigos de recuperación y reenrolamiento restringido

- **Cierre acreditado:** 5/5 subpasos; 2,50/2,50 puntos. Estado:cerrado_acreditado.
- **Lo que hay:** F-08.01–.05 cerrados técnicamente y revisados en conjunto. Se conserva la generación expresa de diez códigos propios, entrega inicial única, hashes salados y canje a enrolamiento restringido: sólo TOTP nuevo permite sesión/API, también para único global; revocación/auditoría/rollback y concurrencia real contrastados. Build corregido F0804 sin recompilar, 227 archivos y cuatro tests previos conservados; foco12/12 y revisor6/6 PASS, sin omitidas. Frontend privado18 archivos: positivos Edge de dashboard8 y recuperación4 en corridas distintas; primer conjunto1PASS/1FAIL y recuperación intermitente sin causa acreditada, siete intentos preservados, sin presentar batería íntegramente verde. Sin cambios de producto, guiones compartidos, SQL, dependencias o D/E. Cuatro hitos técnicos acreditados; integración de candidata, aceptación/custodia y emergencia F-09 siguen pendientes.
- **Criterio conservado; no reabrir por este registro:** Cada código sirve una sola vez incluso en concurrencia; recuperación no abre API antes del estado autorizado; reenrolamiento y revocación/auditoría sin secretos probados por revisor distinto.
- **Fuentes:** [PLAN-F0805-CIERRE-CODIGOS.md](PLAN-F0805-CIERRE-CODIGOS.md); [PASO-028-CIERRE-CODIGOS-MFA.md](PASO-028-CIERRE-CODIGOS-MFA.md); [RESULTADOS.md](../evidence/s1-20261111/f08-05-cierre/RESULTADOS.md); [MATRIZ-CIERRE.md](../evidence/s1-20261111/f08-05-cierre/MATRIZ-CIERRE.md); [FOCO.json](../evidence/s1-20261111/f08-05-cierre/FOCO.json); [FUENTES.json](../evidence/s1-20261111/f08-05-cierre/FUENTES.json); [FRONTEND.json](../evidence/s1-20261111/f08-05-cierre/FRONTEND.json); [NAVEGADOR-INTENTOS.json](../evidence/s1-20261111/f08-05-cierre/NAVEGADOR-INTENTOS.json); [OBSERVACION-NAVEGADOR.md](../evidence/s1-20261111/f08-05-cierre/OBSERVACION-NAVEGADOR.md); [DICTAMEN.md](../evidence/s1-20261111/f08-05-cierre/review/DICTAMEN.md)

#### F-09 · Implementar recuperación local cuando no quedan clave, sobre ni códigos

- **Cierre acreditado:** 4/5 subpasos; 2,00/2,50 puntos. Estado:parcial_acreditado.
- **Lo que hay:** F-09.01–.04 técnicos: CLI local de pérdida con cinco fases, finalización/recibo/guarda y proyección48 mínima no actualizable. Ensayo real en instancia separada de E: pérdida de toda su clave v1, arranque rechazado sin listener, mantenimiento SYSTEM, servidor estándar, regreso HTTPS mediante enrolamiento restringido/TOTP2, credenciales antiguas revocadas e inventario sentinel conservado. Regresión378/378 y revisión independiente40/40 reutilizadas; revisión nativa final favorable por lectura de fuentes/recibos. 221/232fuentes previas conservadas,11modificadas/4nuevas,total236; sin dependencias nuevas. D sin acceso; dos servicios previos de E Running con iguales PID, propios detenidos/puertos y tareas0. Fallos del arnés preservados, cliente HTTPAdmin separado de mantenimientoSYSTEM. F-09.05, seis hitos completos, instalador/Restore48, mantenimientoAdmin, custodia externa y QA/adopción pendientes.
- **Resultado que falta cerrar:** Administrador recupera acceso mediante enrolamiento nuevo después de pérdida total simulada; no se borra inventario ni se reactivan sesiones; ninguna ruta remota permite eludir factor.
- **Fuentes:** [PLAN-F0904-ENSAYO-PERDIDA-MFA.md](PLAN-F0904-ENSAYO-PERDIDA-MFA.md); [PASO-032-ENSAYO-PERDIDA-MFA.md](PASO-032-ENSAYO-PERDIDA-MFA.md); [RESULTADOS.md](../evidence/s1-20261111/f09-04-ensayo-perdida/RESULTADOS.md); [MATRIZ-CRITERIO.md](../evidence/s1-20261111/f09-04-ensayo-perdida/MATRIZ-CRITERIO.md); [NATIVO.json](../evidence/s1-20261111/f09-04-ensayo-perdida/NATIVO.json); [FUENTES.json](../evidence/s1-20261111/f09-04-ensayo-perdida/FUENTES.json); [FOCOS.json](../evidence/s1-20261111/f09-04-ensayo-perdida/FOCOS.json); [CAMBIOS.patch](../evidence/s1-20261111/f09-04-ensayo-perdida/CAMBIOS.patch); [INVESTIGACION-NATIVA.md](../evidence/s1-20261111/f09-04-ensayo-perdida/INVESTIGACION-NATIVA.md); [DICTAMEN.md](../evidence/s1-20261111/f09-04-ensayo-perdida/review/DICTAMEN.md)

#### F-10 · Cerrar política y administración MFA conforme a gracia de 45 días

- **Cierre acreditado:** 0/5 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** El panel propio/por usuario y la política de 45 días ya se implementaron. La regla vigente es45 días, cuentas existentes desde activación y exención del administrador global Systemhaus; administradores de cliente no están exentos. El resumen y dos criterios congelados del ledger contienen redacción anterior: conciliarlos formalmente antes de acreditar F-10, sin reabrir una decisión de Wascar.
- **Resultado que falta cerrar:** Panel y servidor aplican gracia de 45 días a usuarios/técnicos/administradores de cliente, fecha de activación para existentes y exención del administrador global; protegen sesiones, reautenticación, métodos ajenos y recuperación/último administrador, con negativos y revisión independiente.
- **Fuentes:** [DECISION-MFA-GRACIA-45-DIAS-29-10-2026.md](DECISION-MFA-GRACIA-45-DIAS-29-10-2026.md); [MFA-DASHBOARD-GRACIA-45-29-10-2026.md](MFA-DASHBOARD-GRACIA-45-29-10-2026.md)
- **Conciliar redacción antes de acreditar:** F-10.03, F-10.04; aplicar la decisión45 días/exención global vigente.

#### F-11 · Integrar segundo paso y todos los formularios de reautenticación

- **Cierre acreditado:** 0/5 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** El coordinador actual ya gestiona login con desafío 202, enrolamiento, verificación TOTP y canje limitado de códigos. Panel y login MFA se probaron en navegador; D11 confirmó el proveedor Windows real y el flujo TOTP por HTTPS. Falta completar la reautenticación por familia de operación sensible y la persistencia de intenciones inciertas al navegar o recargar; no rehacer el login ni afirmar que la GUI carece de MFA.
- **Resultado que falta cerrar:** Login y cada familia de reauth completan factor para mismo actor, conservan borrador y recuperan respuesta sin duplicar; navegador/ENDEES revisados antes de habilitar QA.
- **Fuentes:** [MFA-DASHBOARD-GRACIA-45-29-10-2026.md](MFA-DASHBOARD-GRACIA-45-29-10-2026.md); [PUNTO3-FUNCIONES-PENDIENTES.md](PUNTO3-FUNCIONES-PENDIENTES.md); [RESULTADOS.md](../evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md)

#### F-12 · Acreditar MFA y fundamento sobre la candidata completa por HTTP/HTTPS

- **Cierre acreditado:** 0/5 subpasos; 0,00/0,00 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Candidata43 y D11 identificadas: servicio/HTTPS/DPAPI reales; TOTP del cargador corregido probado con cuenta sintetica y permiso global denegado. Completar matriz de seguridad/codigos/recuperacion/reauth; no anunciar ausencia de proveedor o deshabilitar lo ya probado por Wascar.
- **Resultado que falta cerrar:** Evidencia identifica bytes/esquema/proveedor/entorno y demuestra flujos positivos/negativos MFA completos más controles afectados; ninguna omisión pasa por éxito, sin anunciar QA/producción por pruebas del almacén.
- **Fuentes:** [RESULTADOS.md](../evidence/s1-20261102/vm11-d/RESULTADOS.md); [RESULTADOS.md](../evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md)

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
- **Lo que hay:** Exportación JSON actual por cliente con recibo, permisos vigentes, SHA256 y descarga probada en desarrollo43. La intención incierta no persiste al desmontar; importación/merge/originalRC9/backupPG quedan pendientes. No cierre íntegro de P-03.
- **Resultado que falta cerrar:** Actual refleja commits vigentes y original conserva hash; funciones separadas respetan permisos, prueba/revisión/QA por versión.
- **Fuentes:** [PUNTO3-FUNCIONES-PENDIENTES.md](PUNTO3-FUNCIONES-PENDIENTES.md); [RESULTADOS.md](../evidence/s1-20261102/punto3/RESULTADOS.md)

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
- **Lo que hay:** CSV, XLSX, SVG, HTML imprimible y XLS HTML existen y se probaron por HTTP en el laboratorio de comparación. Falta su cierre GUI/formato/aceptación; PNG y la obligación de PDF nativo se tratan explícitamente, sin confundirlos con impresión HTML. Imprimible, SVG y XLS HTML tienen ahora propuesta del rack al primer abrir, adopcion explicita posterior y metadatos bajo demanda, probados/revisados en laboratorio. Pendientes/errores/transporte se conservan. Falta integrar y el resto de presentacion/formatos; no repetir esos controles desde cero.
- **Resultado que falta cerrar:** Todos formatos prometidos tienen salida/lector/impresión y permisos verificados; PDF tiene decisión y evidencia; diferencias aceptadas, no eliminadas por plan ambiguo.
- **Fuentes:** [COMPARACION-OFFLINE-RC10-SERVIDOR.md](COMPARACION-OFFLINE-RC10-SERVIDOR.md); [TANDA-INFORMES-CONTEXTO-30-10-2026.md](TANDA-INFORMES-CONTEXTO-30-10-2026.md); [REVISION-INFORMES-CONTEXTO-30-10-2026.md](REVISION-INFORMES-CONTEXTO-30-10-2026.md)

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
- **Lo que hay:** Racks/tarjetas primero, jerarquia y PoE plegables, accesos con foco y exportadores montados ya implementados y probados en laboratorio con datos originales. Revision independiente favorable; falta integrar candidata, QA y la matriz completa de accesibilidad/lector/contraste. No volver a implementar el reordenamiento.
- **Resultado que falta cerrar:** Matriz completa con resultados reales por versión, problemas resueltos/límites aceptados, conservando GUI/Click-Click. Voz no inferida de AX; QA de Wascar.
- **Fuentes:** [TANDA-RACKS-PRIMERO-30-10-2026.md](TANDA-RACKS-PRIMERO-30-10-2026.md); [REVISION-RACKS-PRIMERO-30-10-2026.md](REVISION-RACKS-PRIMERO-30-10-2026.md)

### W · Instalación y operación Windows

#### W-01 · Corregir parada D14-07 y validación de edición del generador

- **Cierre acreditado:** 5/5 subpasos; 2,50/2,50 puntos. Estado:cerrado_acreditado.
- **Lo que hay:** Edición07: runtimef084 integrado y presente en el payload. Guardas tempranas de edición/pins verificadas. Cierre técnico W-01 acreditado; instalación limpia/SCM/reinicio Windows permanecen pendientes en sus tareas.
- **Criterio conservado; no reabrir por este registro:** Runtime y generador de producto corregidos con negativos y revisión; ningún éxito falso de parada o paquete inseguro.
- **Fuentes:** [HALLAZGO-D14-07-PARADA-RUNTIME.md](HALLAZGO-D14-07-PARADA-RUNTIME.md); [REVISION-INSTALADOR14-06-CODEX.md](REVISION-INSTALADOR14-06-CODEX.md); [REVISION-INSTALADOR14-07-CODEX.md](REVISION-INSTALADOR14-07-CODEX.md); [REVISION-FUENTES.md](../evidence/s1-20261025/instalador14-07-codex/REVISION-FUENTES.md); [RESULTADOS.md](../evidence/s1-20261025/instalador14-07-claude/RESULTADOS.md)

#### W-02 · Instalar desde cero en Windows limpio y declarar la matriz soportada

- **Cierre acreditado:** 2/5 subpasos; 1,00/2,50 puntos. Estado:parcial_acreditado.
- **Lo que hay:** New11 en D limpio Windows Server2025/noDC, CRT/runtime/PG incluidos, cuenta estandar, servicio/HTTPS y postboot verificados tras reinicio de Wascar. W-02.01/.02 ya acreditados por10; faltan matriz de dependencias/hosts/rechazos. No reinstalar D ni duplicar credito.
- **Resultado que falta cerrar:** Recorrido nuevo de instalación completo en los hosts declarados, con versiones y resultados reales; ausencia de soporte no probado indicada explícitamente.
- **Fuentes:** [RESULTADOS.md](../evidence/s1-20261102/windows43/RESULTADOS.md); [INSTALADOR11-WINDOWS43.md](INSTALADOR11-WINDOWS43.md); [RESULTADOS.md](../evidence/s1-20261102/vm11-d/RESULTADOS.md); [RESULTADOS.md](../evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md)

#### W-03 · Cuenta mínima, servicio Windows y arranque automático reales

- **Cierre acreditado:** 0/5 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** D11 verificada: SCM Running/Auto, SID y cuenta estandar, HTTPS43 y postboot real; custodias e identidades separadas. Faltan negativos/ACL completos y fallos de parada/hijo, no construir otro servicio.
- **Resultado que falta cerrar:** Servicio y PostgreSQL funcionan bajo identidad mínima tras reinicio real; logs/estados y acceso privado son verificables.
- **Fuentes:** [RESULTADOS.md](../evidence/s1-20261029/installer10-vm-codex/RESULTADOS.md); [RESULTADOS.md](../evidence/s1-20261102/vm11-d/RESULTADOS.md); [RESULTADOS.md](../evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md)

#### W-04 · HTTPS, certificados, red y acceso casa/trabajo en la edición final

- **Cierre acreditado:** 0/6 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** D11 tiene origen, CA y firewall limitados verificados; cargador y MFA usaron TLS normal. Faltan otro equipo cliente, cambio casa/trabajo de la candidata, renovacion/caducidad y recuperacion de certificados.
- **Resultado que falta cerrar:** Acceso LAN confiable y cambio de red con datos conservados; renovación y errores documentados, sin exponer claves privadas.
- **Fuentes:** [RESULTADOS.md](../evidence/s1-20261102/vm11-d/RESULTADOS.md); [RESULTADOS.md](../evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md)

#### W-05 · Repetición, cancelación, mantenimiento y diagnóstico del instalador

- **Cierre acreditado:** 0/5 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Hay preflights, archivo/retirada por identidad y reportes automáticos; experiencias históricas no equivalen a ensayo completo14 de estos recorridos.
- **Resultado que falta cerrar:** Cada fallo/cancelación tiene estado veraz y procedimiento repetible; programas/bases ajenos y cuentas manuales permanecen intactos.
- **Fuentes:** [INICIO-IMPLEMENTACION-S1.md](INICIO-IMPLEMENTACION-S1.md); [REINICIO-LIMPIO-SERVIDOR.html](REINICIO-LIMPIO-SERVIDOR.html); [REVISION-INSTALADOR14-06-CODEX.md](REVISION-INSTALADOR14-06-CODEX.md)

#### W-06 · Recorrido completo de persistencia y concurrencia del servidor instalado

- **Cierre acreditado:** 0/5 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** D11 contiene Demo50 creada por2553comandos API y contrastada por colecciones/UUID/conexiones. Faltan recorrido instalado con roles y segunda cuenta, reinicio posterior del conjunto y concurrencia/perdida de respuesta. No recrear clientes ni repetir carga.
- **Resultado que falta cerrar:** S-55 reproducido completo y conflictos/recuperación coherentes sobre build/DB/host identificados.
- **Fuentes:** [RESULTADOS.md](../evidence/s1-20261102/vm11-d/RESULTADOS.md); [RESULTADOS.md](../evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md)

### R · Backup, recuperación y actualización

#### R-01 · Backup programado local y retención comprobada

- **Cierre acreditado:** 0/5 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Backup inicial, tarea programada tras postboot y backup posterior a Demo50 completados con resultado0 en D. Faltan retencion configurable, destinos/fallos y restaurabilidad; backup completo no demuestra recuperacion MFA portable.
- **Resultado que falta cerrar:** Ejecución programada real, política de retención y fallos comprobados; sólo copias completas verificadas quedan elegibles.
- **Fuentes:** [COMPARACION-OFFLINE-RC10-SERVIDOR.md](COMPARACION-OFFLINE-RC10-SERVIDOR.md); [RESULTADOS.md](../evidence/s1-20261029/rc9-demo-original-codex/RESULTADOS.md); [RESULTADOS.md](../evidence/s1-20261102/vm11-d/RESULTADOS.md); [RESULTADOS.md](../evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md)

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
- **Lo que hay:** Restore43-&gt;43 y15-&gt;43 en laboratorio nuevo conserva inventario/UUID y revoca sesiones. D11 New y su backup posterior funcionan. Falta recuperacion integral en otro Windows con MFA/SID/HTTPS/reinicio y RTO; no ensayarla sobre D conservada.
- **Resultado que falta cerrar:** Servicio recuperado completo y operativo en otro host con identidad nueva, integridad y revocación comprobadas; origen conservado.
- **Fuentes:** [RESULTADOS.md](../evidence/s1-20261102/vm11-d/RESULTADOS.md); [RESULTADOS.md](../evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md); [RESULTADOS.md](../evidence/s1-20261102/windows43/RESULTADOS.md)

#### R-05 · Actualización y rollback compatibles con datos posteriores

- **Cierre acreditado:** 0/5 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Hay migraciónSQL y ensayos de copias/retornos privados. No es actualización en sitio probada del servicio ni retorno libre después de nuevas escrituras.
- **Resultado que falta cerrar:** Upgrade y fallos con vuelta compatible comprobados en instalación real, sin perder escrituras ni seleccionar binarios incompatibles.
- **Fuentes:** [RECUPERACION-DESPLIEGUE-WINDOWS-S1.md](RECUPERACION-DESPLIEGUE-WINDOWS-S1.md); [CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md); [REVISION-D14-05-CODEX.md](REVISION-D14-05-CODEX.md)

#### R-06 · Reset y recuperación administrativa delimitados

- **Cierre acreditado:** 0/5 subpasos; 0,00/2,50 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Limpieza local de inventario D explicitamente autorizada y revisada: preview, dryrun, commit, auditoria y seguridad preservada. No equivale a reset completo de instancia, nueva base/roles ni emergencia MFA.
- **Resultado que falta cerrar:** Reset acotado y recuperación de acceso operativos y documentados; cancelar no modifica datos ni deja acceso omitido.
- **Fuentes:** [RESULTADOS.md](../evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md)

### E · Paquete, manual, rendimiento y aceptación

#### E-01 · Candidata final única con fuentes y componentes compatibles

- **Cierre acreditado:** 0/5 subpasos; 0,00/1,43 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Candidata11/esquema43 identificada e instalada, mas cargador02 separado revisado. Falta integrar los pendientes restantes y ese parche en la futura entrega final unica; no reconstruir por cambios solo documentales ni tocar D.
- **Resultado que falta cerrar:** Una sola candidata completa trazable y coherente, sin depender de archivos de entregas anteriores ni aceptar una mezcla no revisada.
- **Fuentes:** [RESULTADOS.md](../evidence/s1-20261102/vm11-d/RESULTADOS.md); [RESULTADOS.md](../evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md)

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
- **Lo que hay:** Manual11 con pasos00-07, acceso privado y guias D/cargador02 disponibles y usados en ensayo. Faltan manual completo del producto, idiomas/capturas y recorridos futuros de recuperacion/importacion/operacion; no empezar otro manual desde cero.
- **Resultado que falta cerrar:** El recorrido completo funciona siguiendo sólo manual+paquete final, sin pedir archivos antiguos ni instrucciones ocultas.
- **Fuentes:** [INSTALADOR11-WINDOWS43.md](INSTALADOR11-WINDOWS43.md); [INSTALADOR11-WINDOWS43.html](INSTALADOR11-WINDOWS43.html); [RESULTADOS.md](../evidence/s1-20261102/windows43/RESULTADOS.md); [RESULTADOS.md](../evidence/s1-20261102/vm11-d/RESULTADOS.md); [RESULTADOS.md](../evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md); [VM11-D-PASOS-QA.md](VM11-D-PASOS-QA.md); [INSTALADOR14-SQL-PROTEGIDO.md](INSTALADOR14-SQL-PROTEGIDO.md)

#### E-05 · QA manual por módulos sobre candidata identificada

- **Cierre acreditado:** 0/5 subpasos; 0,00/1,43 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** D11 y Demo50 estan disponibles. HojaQA11 de14casos,167casos totales, export/import y observaciones preservadas. Wascar expresa satisfaccion general, pero no sustituye resultados por caso/rol/version. Faltan cuentas diferenciadas y QA por modulos; no trasladar PASS historicos.
- **Resultado que falta cerrar:** Casos críticos y recorridos pactados tienen resultados atribuibles; ningún resultado del usuario sobrescrito ni aprobado por el desarrollador.
- **Fuentes:** [QA-CIERRE-CANDIDATA11.md](QA-CIERRE-CANDIDATA11.md); [RESULTADOS.md](../evidence/s1-20261102/qa-cierre11/RESULTADOS.md); [QA-CASOS-WASCAR.json](QA-CASOS-WASCAR.json); [RESULTADOS.md](../evidence/s1-20261102/vm11-d/RESULTADOS.md); [RESULTADOS.md](../evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md)

#### E-06 · Medir carga real de diez usuarios y demo completa

- **Cierre acreditado:** 0/5 subpasos; 0,00/1,43 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Demo50 y prueba de diez actores/ambitos ya realizados en laboratorio con umbrales de humo previos. D11 carga50/2553comandos verificada en185.681s y backup posterior completo; MFA/TLS del cargador probado aparte en cuenta sintetica. Faltan carga extendida instalada, memoria/CPU/consultas/picos/recuperacion y aceptacion practica, no crear de nuevo la demo.
- **Resultado que falta cerrar:** Informe reproducibleS-48 demuestra datos consistentes y comportamiento aceptable con carga declarada; regresiones medidas resueltas.
- **Fuentes:** [PLAN-LABORATORIO-50-CLIENTES.md](PLAN-LABORATORIO-50-CLIENTES.md); [LABORATORIO-50-CLIENTES.md](LABORATORIO-50-CLIENTES.md); [RESULTADOS.md](../evidence/s1-20261102/demo50/RESULTADOS.md); [RESULTADOS.md](../evidence/s1-20261102/windows43/demo/RESULTADOS.md); [RESULTADOS.md](../evidence/s1-20261102/vm11-d/RESULTADOS.md); [RESULTADOS.md](../evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md)

#### E-07 · Revisión final y adopción explícita de Wascar

- **Cierre acreditado:** 0/5 subpasos; 0,00/1,43 puntos. Estado:pendiente_de_cierre_acreditado.
- **Lo que hay:** Servidor histórico funciona según Wascar, pero la entrega final nueva no está adoptada. No corresponde anunciar100% por generar un ZIP.
- **Resultado que falta cerrar:** Conjunto final completo revisado, recorrido instalado/recuperado acreditado y confirmación de adopción de Wascar registrada.
- **Fuentes:** [ACEPTACION.md](ACEPTACION.md); [CONTRATO-SERVIDOR-v0.1.md](CONTRATO-SERVIDOR-v0.1.md); [CONTINUIDAD-CODEX.md](CONTINUIDAD-CODEX.md)

## Progreso y cierre de esta consolidación

**26,63/100 del cierre restante**, misma base RC-CIERRE-20261103-v3, 53 resultados / 280 subpasos / 55 acreditados. **No es porcentaje global del producto.** Registrar pendientes, descargar modelos o regenerar esta hoja no suma implementación.

El cierre de esta consolidación es documental: ninguna función, plantilla o prueba de producto se acredita por este registro. Los originales y los paquetes históricos se conservan.
