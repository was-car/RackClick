# Plan pendiente de RackClick: pasos numerados

Fecha: 2026-11-11 · Versión: 2026-11-04-v1.23

**Para elegir:** «Continúa con el paso 80» o «Continúa con F-05.04». Los números se conservan al cerrar pasos. Cada resultado incluye contexto, criterio de cierre y referencias; sus subpasos son seleccionables por separado.

[Abrir visor con búsqueda](../VER-PENDIENTES-RACKCLICK.html) · [Datos completos](PLAN-PENDIENTES-NUMERADO.json) · [Hoja maestra](HOJA-DE-RUTA-MAESTRA.md)

Números conservados tras un cierre posterior: 32. Ya están acreditados y no se ofrecen como nueva implementación.

## Qué representa esta lista

Hay **268 opciones numeradas**: 225 subpasos del cierre (223 pendientes y 2 en curso), 7 cierres/mantenimiento del catálogo, 3 iniciativas posteriores y 1 proceso de repositorio. Son desgloses de trabajo, no 268 funciones ausentes ni una estimación de duración. Los 55 subpasos con crédito previo se conservan en el apéndice, fuera de los pendientes iniciales.

**Índice acreditado del cierre: 26,63/100, sin cambio. No hay un nuevo porcentaje global del producto.** Los estados formales congelados no describen por sí solos la implementación actual. Un paso puede requerir sólo conciliar pruebas existentes, integración o QA. Las 302 acciones RC10 y 13 peticiones están trazadas en los apéndices; no se suman como trabajo duplicado.

**Se conserva D:** D45 se conserva: servicio/SID/DB/HTTPS/MFA y datos existentes intactos. La lista no ejecuta ni autoriza operaciones destructivas, reinstalación o recarga de Demo50; los ensayos futuros usan su laboratorio asignado.

## Orden aconsejado

1. Conciliar los criterios históricos con las decisiones actuales y acreditar evidencia existente: E-07 y F-10. Evitar rehacer funciones ya probadas.
2. Completar recuperación operativa MFA, emergencia y backups restaurables: F-05, F-06, F-08, F-09, R-03 y R-04.
3. Cerrar importación/preview/round-trip JSON y paridad restante: P-01, P-02, P-03 y P-04.
4. Completar aceptación de permisos, inventario, administración, catálogo e idiomas usando los recorridos actuales.
5. Consolidar Windows/actualización, pruebas prolongadas, manuales, licencias, QA de Wascar y aceptación final. Elegir el laboratorio cuando el paso lo requiera; no reutilizar D automáticamente.

Los números agrupan áreas, no obligan a ejecutar secuencialmente. Las dependencias indicadas pertenecen al resultado completo; investigar primero qué parte ya está satisfecha.

## Índice

| Pasos | Área | Cantidad |
|---|---|---:|
| 1–48 | Fundamento, seguridad y MFA | 48 |
| 49–80 | Jerarquía, inventario y colaboración | 32 |
| 81–100 | Usuarios, grupos y administración | 20 |
| 101–167 | Paridad funcional y visual RC9 | 67 |
| 168–191 | Instalación y operación Windows | 24 |
| 192–221 | Backup, recuperación y actualización | 30 |
| 222–257 | Paquete, manual, rendimiento y aceptación | 36 |
| 258–264 | Catálogo: aceptación y mantenimiento | 7 |
| 265–267 | Evolución posterior a la primera entrega | 3 |
| 268–268 | Repositorio privado y mantenimiento | 1 |

## Decisiones vigentes y decisiones aún abiertas

- Confirmado: MFA tras 45 días; cuentas existentes desde activación de política, nuevas desde creación. Exención sólo del administrador global con las dos capacidades globales. Desactivar no reinicia el plazo.
- Confirmado: custodia fuera de PostgreSQL, sobre de recuperación fuera del servidor y sus backups, medios separados; recuperación y nuevo enrolamiento según la decisión aprobada. No se vuelve a pedir estas decisiones.
- Por concretar en su paso: catálogo finito de compensaciones mixtas (I-02), alcance de terminales internos (I-07), obligación/formato de PDF (P-07), matriz de hosts soportados (W-02), retención y objetivos medidos RPO/RTO/rendimiento (R-01, R-04 y E-06). Son propuestas técnicas a documentar, no motivos para detener todo el proyecto.
- USB/UNC siguen en R-02 mientras no haya una exclusión explícita. SNMP/LLDP, campo offline y federación real son posteriores; se mantienen visibles sin ampliar el primer cierre.

## F · Fundamento, seguridad y MFA

### F-01 · Clasificar hallazgos de secretos y tratar sólo credenciales reales

**Situación conocida:** F-01.01/.03 conservan su clasificación/registro técnico. F-01.02/.04 cerrados administrativamente por decisión expresa de Wascar03.11 y enmienda limitadav3: antecedente25.10 indeterminado y salida perdida, sin falso positivo, prueba de revocación ni cambios deD. Reabrir ambos y retirar5/4 si aparece evidencia concreta; no es higiene global ni aceptación de exposiciones futuras.

**Cierre esperado:** Cada candidato/indeterminado tiene clasificación y resolución verificables; credenciales reales expuestas revocadas/rotadas de forma coordinada; comprobación focal de fuentes/paquete sin exposición. Excepción limitada al antecedente run-1 del 25.10.2026 sin salida conservada: archivo administrativo expreso del titular con clasificación indeterminada y reapertura obligatoria si aparece evidencia concreta. No equivale a falso positivo, ausencia de exposición o revocación demostrada.

**Dependencias del resultado:** Sin dependencia previa declarada; contrastar antes de ejecutar..

**Fuentes:** [docs/F01-RESOLUCION-ANTECEDENTE.md](../docs/F01-RESOLUCION-ANTECEDENTE.md) · [evidence/s1-20261102/cierre-bloqueantes-01-07/f01/REVISION-RESOLUCION.md](../evidence/s1-20261102/cierre-bloqueantes-01-07/f01/REVISION-RESOLUCION.md) · [docs/DECISION-F01-ARCHIVO-ADMINISTRATIVO-03-11-2026.md](../docs/DECISION-F01-ARCHIVO-ADMINISTRATIVO-03-11-2026.md) · [evidence/s1-20261103/f01-archivo-administrativo/RESULTADOS.md](../evidence/s1-20261103/f01-archivo-administrativo/RESULTADOS.md) · [evidence/s1-20261103/f01-archivo-administrativo/review/REVISION-ARCHIVO-ADMINISTRATIVO.md](../evidence/s1-20261103/f01-archivo-administrativo/review/REVISION-ARCHIVO-ADMINISTRATIVO.md) · [evidence/s1-20261102/f01-01-clasificacion/RESULTADOS.md](../evidence/s1-20261102/f01-01-clasificacion/RESULTADOS.md) · [evidence/s1-20261102/f01-01-clasificacion/REVISION-INDEPENDIENTE.md](../evidence/s1-20261102/f01-01-clasificacion/REVISION-INDEPENDIENTE.md) · [evidence/s1-20261102/f01-02-tratamiento/RESULTADOS.md](../evidence/s1-20261102/f01-02-tratamiento/RESULTADOS.md) · [evidence/s1-20261102/f01-02-tratamiento/REVISION-INDEPENDIENTE.md](../evidence/s1-20261102/f01-02-tratamiento/REVISION-INDEPENDIENTE.md) · [evidence/s1-20261102/f01-03-registro/RESULTADOS.md](../evidence/s1-20261102/f01-03-registro/RESULTADOS.md) · [evidence/s1-20261102/f01-03-registro/REVISION-INDEPENDIENTE.md](../evidence/s1-20261102/f01-03-registro/REVISION-INDEPENDIENTE.md) · [docs/CRITERIO-FALSOS-POSITIVOS-SECRETOS.md](../docs/CRITERIO-FALSOS-POSITIVOS-SECRETOS.md) · [evidence/s1-20261102/f01-04-cierre/RESULTADOS.md](../evidence/s1-20261102/f01-04-cierre/RESULTADOS.md) · [evidence/s1-20261102/f01-04-cierre/REVISION-INDEPENDIENTE.md](../evidence/s1-20261102/f01-04-cierre/REVISION-INDEPENDIENTE.md).

#### Paso 001 · F-01.01

Clasificación terminada: 92 históricos resueltos con trazabilidad privada y revisión independiente; 90 metadatos working corroborados. No repetir como nueva implementación ni afirmar higiene global.

- Tipo de trabajo: Cerrado con revisión independiente.
- Estado formal: done; ámbito: Primera entrega; responsable: F-01.
- Texto histórico trazable: Clasificar candidatos e indeterminados privados con trazabilidad por ruta/commit y sin publicar valores.
- Número conservado tras el cierre: no repetir como nueva implementación.

#### Paso 002 · F-01.02

F-01.01/.03 conservan su clasificación/registro técnico. F-01.02/.04 cerrados administrativamente por decisión expresa de Wascar03.11 y enmienda limitadav3: antecedente25.10 indeterminado y salida perdida, sin falso positivo, prueba de revocación ni cambios deD. Reabrir ambos y retirar5/4 si aparece evidencia concreta; no es higiene global ni aceptación de exposiciones futuras.

- Tipo de trabajo: Cerrado administrativamente con incertidumbre y reapertura; no prueba de revocación.
- Estado formal: done; ámbito: Primera entrega; responsable: F-01.
- Texto histórico trazable: Si una credencial es real, coordinar revocación/rotación con la instancia afectada; corregir exposición y volver a verificar cambios/artefactos relevantes. Para el antecedente run-1 del25.10.2026 sin salida conservada, se admite sólo el archivo administrativo expreso documentado, con incertidumbre y reapertura obligatoria; no clasifica como falso positivo ni prueba revocación.
- Número conservado tras el cierre: no repetir como nueva implementación.

#### Paso 003 · F-01.03

Registro contextual de falsos positivos terminado y revisado: criterios de prueba específicos y vínculos a la versión exacta, sin supresiones ni cambios de escáner/historial. No incluye las observaciones desconocidas del paso 2.

- Tipo de trabajo: Cerrado con revisión independiente.
- Estado formal: done; ámbito: Primera entrega; responsable: F-01.
- Texto histórico trazable: Registrar falsos positivos y criterio específico sin supresiones amplias; reescritura de historial no está autorizada por defecto.
- Número conservado tras el cierre: no repetir como nueva implementación.

#### Paso 004 · F-01.04

F-01.01/.03 conservan su clasificación/registro técnico. F-01.02/.04 cerrados administrativamente por decisión expresa de Wascar03.11 y enmienda limitadav3: antecedente25.10 indeterminado y salida perdida, sin falso positivo, prueba de revocación ni cambios deD. Reabrir ambos y retirar5/4 si aparece evidencia concreta; no es higiene global ni aceptación de exposiciones futuras.

- Tipo de trabajo: Cerrado administrativamente con incertidumbre y reapertura; no prueba de revocación.
- Estado formal: done; ámbito: Primera entrega; responsable: F-01.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.
- Número conservado tras el cierre: no repetir como nueva implementación.

### F-02 · Cifrar configuración SQL y recuperar sus secretos en otra instancia

**Situación conocida:** F-02.01–.04 cerrados: postboot13, Restore14-r2 desde backup sintético LEAO hacia E con cuenta/SID/roles/material nuevos,20 clientes SQL/API,operadores/ficha/diagnóstico/backup reales y reanudación sin regeneración. Windows no se reinició tras Restore14; ese pendiente sigue en los criterios Windows, sin adopción global. D se conserva y F01 tiene disposición administrativa posterior03.11, separada del cierre técnico.

**Cierre esperado:** El secreto SQL no queda en claro en el archivo entregado/configuración recuperable; servicio estándar arranca y Restore nuevo funciona mediante procedimiento documentado, sin secretos en logs/paquetes.

**Dependencias del resultado:** Coordinación C4/C5: cuenta de servicio y procedimiento de recuperación.

**Fuentes:** [docs/IMPLEMENTACION-REV4.md](../docs/IMPLEMENTACION-REV4.md) · [docs/RECUPERACION-DESPLIEGUE-WINDOWS-S1.md](../docs/RECUPERACION-DESPLIEGUE-WINDOWS-S1.md) · [docs/REVISION-INSTALADOR14-06-CODEX.md](../docs/REVISION-INSTALADOR14-06-CODEX.md) · [evidence/s1-20261102/f02-01-sql/RESULTADOS.md](../evidence/s1-20261102/f02-01-sql/RESULTADOS.md) · [evidence/s1-20261102/f02-01-sql/REVISION-INDEPENDIENTE.md](../evidence/s1-20261102/f02-01-sql/REVISION-INDEPENDIENTE.md) · [docs/CONTRATO-CONEXION-SQL-CIFRADA-v1.md](../docs/CONTRATO-CONEXION-SQL-CIFRADA-v1.md) · [evidence/s1-20261102/f02-02-operadores/RESULTADOS.md](../evidence/s1-20261102/f02-02-operadores/RESULTADOS.md) · [evidence/s1-20261102/f02-02-operadores/REVISION-INDEPENDIENTE.md](../evidence/s1-20261102/f02-02-operadores/REVISION-INDEPENDIENTE.md) · [docs/OPERADORES-SQL-CIFRADOS-v2.md](../docs/OPERADORES-SQL-CIFRADOS-v2.md) · [evidence/s1-20261102/f02-03-restauracion/RESULTADOS.md](../evidence/s1-20261102/f02-03-restauracion/RESULTADOS.md) · [evidence/s1-20261102/f02-03-restauracion/REVISION-INDEPENDIENTE.md](../evidence/s1-20261102/f02-03-restauracion/REVISION-INDEPENDIENTE.md) · [docs/REANUDACION-RESTORE-SQL-PROTEGIDO.md](../docs/REANUDACION-RESTORE-SQL-PROTEGIDO.md) · [docs/SQL-PROTEGIDO-INSTANCIA3.md](../docs/SQL-PROTEGIDO-INSTANCIA3.md) · [docs/INSTALADOR12-SQL-PROTEGIDO.md](../docs/INSTALADOR12-SQL-PROTEGIDO.md) · [docs/CIERRE-BLOQUEANTES-PASOS-01-A-07.md](../docs/CIERRE-BLOQUEANTES-PASOS-01-A-07.md) · [evidence/s1-20261102/cierre-bloqueantes-01-07/RESULTADOS.md](../evidence/s1-20261102/cierre-bloqueantes-01-07/RESULTADOS.md) · [evidence/s1-20261102/vm12-e/RESULTADOS.md](../evidence/s1-20261102/vm12-e/RESULTADOS.md) · [evidence/s1-20261102/vm12-e/review/DICTAMEN-F02-01.md](../evidence/s1-20261102/vm12-e/review/DICTAMEN-F02-01.md) · [evidence/s1-20261103/e13-postboot-restore14/RESULTADOS.md](../evidence/s1-20261103/e13-postboot-restore14/RESULTADOS.md) · [evidence/s1-20261103/e13-postboot-restore14/review/DICTAMEN-F02-03-04.md](../evidence/s1-20261103/e13-postboot-restore14/review/DICTAMEN-F02-03-04.md) · [evidence/s1-20261102/vm12-e/service-observed13.json](../evidence/s1-20261102/vm12-e/service-observed13.json) · [evidence/s1-20261102/vm12-e/source-next-actual.json](../evidence/s1-20261102/vm12-e/source-next-actual.json) · [evidence/s1-20261103/e13-postboot-restore14/review/DICTAMEN-F02-02.md](../evidence/s1-20261103/e13-postboot-restore14/review/DICTAMEN-F02-02.md) · [evidence/s1-20261103/e13-postboot-restore14/restore14-observed.json](../evidence/s1-20261103/e13-postboot-restore14/restore14-observed.json) · [evidence/s1-20261103/e13-postboot-restore14/resume14-reconciled.json](../evidence/s1-20261103/e13-postboot-restore14/resume14-reconciled.json).

#### Paso 005 · F-02.01

F-02.01–.04 cerrados: postboot13, Restore14-r2 desde backup sintético LEAO hacia E con cuenta/SID/roles/material nuevos,20 clientes SQL/API,operadores/ficha/diagnóstico/backup reales y reanudación sin regeneración. Windows no se reinició tras Restore14; ese pendiente sigue en los criterios Windows, sin adopción global. D se conserva y F01 tiene disposición administrativa posterior03.11, separada del cierre técnico.

- Tipo de trabajo: Cerrado técnicamente con revisión independiente; no repetir ensayos invariantes.
- Estado formal: done; ámbito: Primera entrega; responsable: F-02.
- Texto histórico trazable: Diseñar e integrar protección compatible con cuenta/instancia reales y canal mínimo de lectura para el servicio; conservar separación owner/migración/runtime.
- Número conservado tras el cierre: no repetir como nueva implementación.

#### Paso 006 · F-02.02

F-02.01–.04 cerrados: postboot13, Restore14-r2 desde backup sintético LEAO hacia E con cuenta/SID/roles/material nuevos,20 clientes SQL/API,operadores/ficha/diagnóstico/backup reales y reanudación sin regeneración. Windows no se reinició tras Restore14; ese pendiente sigue en los criterios Windows, sin adopción global. D se conserva y F01 tiene disposición administrativa posterior03.11, separada del cierre técnico.

- Tipo de trabajo: Cerrado técnicamente con revisión independiente; no repetir ensayos invariantes.
- Estado formal: done; ámbito: Primera entrega; responsable: F-02.
- Texto histórico trazable: Actualizar operadores/fichas de acceso, diagnóstico y backup para no filtrar la clave ni depender de copiar un secreto ligado al host antiguo.
- Número conservado tras el cierre: no repetir como nueva implementación.

#### Paso 007 · F-02.03

F-02.01–.04 cerrados: postboot13, Restore14-r2 desde backup sintético LEAO hacia E con cuenta/SID/roles/material nuevos,20 clientes SQL/API,operadores/ficha/diagnóstico/backup reales y reanudación sin regeneración. Windows no se reinició tras Restore14; ese pendiente sigue en los criterios Windows, sin adopción global. D se conserva y F01 tiene disposición administrativa posterior03.11, separada del cierre técnico.

- Tipo de trabajo: Cerrado técnicamente con revisión independiente; no repetir ensayos invariantes.
- Estado formal: done; ámbito: Primera entrega; responsable: F-02.
- Texto histórico trazable: Ensayar reanudación y Restore en destino nuevo con identidad/roles/claves nuevos; error explícito ante clave ausente/incorrecta.
- Número conservado tras el cierre: no repetir como nueva implementación.

#### Paso 008 · F-02.04

F-02.01–.04 cerrados: postboot13, Restore14-r2 desde backup sintético LEAO hacia E con cuenta/SID/roles/material nuevos,20 clientes SQL/API,operadores/ficha/diagnóstico/backup reales y reanudación sin regeneración. Windows no se reinició tras Restore14; ese pendiente sigue en los criterios Windows, sin adopción global. D se conserva y F01 tiene disposición administrativa posterior03.11, separada del cierre técnico.

- Tipo de trabajo: Cerrado técnicamente con revisión independiente; no repetir ensayos invariantes.
- Estado formal: done; ámbito: Primera entrega; responsable: F-02.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.
- Número conservado tras el cierre: no repetir como nueva implementación.

### F-03 · Registrar decisión de custodia y ubicación definitiva D2

**Situación conocida:** Custodia/ubicación confirmadas25.10; F-03.02 concreta recuperación/KDF/publicación y F-03.03 registra límites LocalMachine frente a administrador/SYSTEM/servicio comprometido, con revisiones independientes. F-03 completa sólo la decisión documental. Política45 intacta; F-04..F-09/R-04 conservan sus pruebas/integraciones, sin nueva aceptación operativa o producción. D45 no operada.

**Cierre esperado:** Decisión de Wascar identificada y especificación D2 final sin ambigüedad sobre responsables, almacén, pérdida total, recuperación y límites; revisión técnica separada de la aceptación operativa.

**Dependencias del resultado:** Sin dependencia previa declarada; contrastar antes de ejecutar..

**Fuentes:** [docs/DECISIONES-MFA-CONFIRMADAS-25-10-2026.md](../docs/DECISIONES-MFA-CONFIRMADAS-25-10-2026.md) · [docs/D2-CONDICIONES-TECNICAS-F03-02.md](../docs/D2-CONDICIONES-TECNICAS-F03-02.md) · [evidence/s1-20261103/f03-02-condiciones/REVISION-INDEPENDIENTE.md](../evidence/s1-20261103/f03-02-condiciones/REVISION-INDEPENDIENTE.md) · [evidence/s1-20261103/f03-02-condiciones/RESULTADOS.md](../evidence/s1-20261103/f03-02-condiciones/RESULTADOS.md) · [docs/D2-LIMITES-AMENAZA-F03-03.md](../docs/D2-LIMITES-AMENAZA-F03-03.md) · [evidence/s1-20261103/f03-03-amenazas/REVISION-INDEPENDIENTE.md](../evidence/s1-20261103/f03-03-amenazas/REVISION-INDEPENDIENTE.md) · [evidence/s1-20261103/f03-03-amenazas/RESULTADOS.md](../evidence/s1-20261103/f03-03-amenazas/RESULTADOS.md).

#### Paso 009 · F-03.02

Especificación D2 conciliada y revisada: recuperación restringida, KDF/AAD y protocolo disco/DB. Operadores e integración se verifican en sus pasos F-04..F-09/R-04, sin repetir codec/proveedor ni modificar D.

- Tipo de trabajo: Cerrado documentalmente con revisión independiente.
- Estado formal: done; ámbito: Primera entrega; responsable: F-03.
- Texto histórico trazable: Desarrollo concreta las condiciones técnicas de la revisión: recuperación restringida sin clave, límites/cabecera autenticada del KDF y publicación recuperable entre disco/DB.
- Número conservado tras el cierre: no repetir como nueva implementación.

#### Paso 010 · F-03.03

Límites de amenaza DPAPI LocalMachine registrados y revisados: administrador/SYSTEM y servicio comprometido fuera del aislamiento; custodia/ACL y recuperación conservan sus criterios propios. F-03 completado sólo como decisión documental, sin operar D.

- Tipo de trabajo: Cerrado documentalmente con revisión independiente.
- Estado formal: done; ámbito: Primera entrega; responsable: F-03.
- Texto histórico trazable: Registrar límites de amenaza: DPAPI LocalMachine no aísla del administrador local ni del proceso de servicio comprometido.
- Número conservado tras el cierre: no repetir como nueva implementación.

### F-04 · Implementar proveedor TOTP Windows bajo la identidad real del servicio

**Situación conocida:** Criterios técnicos F04 conservados; writer76 e6 integrado en candidata completa16/app45 con DLLReleasec057 y frontend/SQL/dependencias/servicio preservados. Bundle2018/payload117 y cadena de pins verificados; 16 casos de creación+DB/TOTP sobre la DLL exacta y New/RestoreSQL45/43→45 reales en laboratorio. Propagación45 cerrada de SetupMfa/readiness/recibo y matrizRestore, sin retirar guardiaMFA. Integración de candidata acreditada con revisión independiente04.11; no instalación elevada, SCM/HTTPS/reinicio, formato mínimo3 o adopción de 16. target_acceptance sigue pendiente; D/E sin cambios. Se conservan las pruebas previas de SID real/504 derechos de E y núcleo del proveedor; no se atribuyen como nuevas en 16.

**Cierre esperado:** Servicio real lee/descifra y verifica factores; otra cuenta no lee, servicio no escribe ni modifica ACL, management no se amplía; negativos y revisión independiente registrados.

**Dependencias del resultado:** F-03, C4: identidad estándar del servicio disponible.

**Fuentes:** [development/server/src/RackClick.Server/Program.cs](../development/server/src/RackClick.Server/Program.cs) · [development/server/src/RackClick.Server/MfaStore.cs](../development/server/src/RackClick.Server/MfaStore.cs) · [development/server/src/RackClick.Server/MfaSecretCipher.cs](../development/server/src/RackClick.Server/MfaSecretCipher.cs) · [docs/DECISION-D2-CUSTODIA-CLAVE-TOTP.md](../docs/DECISION-D2-CUSTODIA-CLAVE-TOTP.md) · [docs/REVISION-D2-CODEX.md](../docs/REVISION-D2-CODEX.md) · [evidence/s1-20261103/f04-01-almacen/RESULTADOS.md](../evidence/s1-20261103/f04-01-almacen/RESULTADOS.md) · [evidence/s1-20261103/f04-01-almacen/REVISION-INDEPENDIENTE.md](../evidence/s1-20261103/f04-01-almacen/REVISION-INDEPENDIENTE.md) · [evidence/s1-20261103/f04-02-permisos/RESULTADOS.md](../evidence/s1-20261103/f04-02-permisos/RESULTADOS.md) · [evidence/s1-20261103/f04-02-permisos/review/DICTAMEN-PREVIO-SONDA.md](../evidence/s1-20261103/f04-02-permisos/review/DICTAMEN-PREVIO-SONDA.md) · [evidence/s1-20261103/f04-02-permisos/ejecucion/RESULTADOS.md](../evidence/s1-20261103/f04-02-permisos/ejecucion/RESULTADOS.md) · [evidence/s1-20261103/f04-02-permisos/ejecucion/review/DICTAMEN-F0402.md](../evidence/s1-20261103/f04-02-permisos/ejecucion/review/DICTAMEN-F0402.md) · [evidence/s1-20261103/f04-02-permisos/ejecucion/RESULTADO-CONSOLIDADO.json](../evidence/s1-20261103/f04-02-permisos/ejecucion/RESULTADO-CONSOLIDADO.json) · [evidence/s1-20261103/f04-04-cierre/RESULTADOS.md](../evidence/s1-20261103/f04-04-cierre/RESULTADOS.md) · [evidence/s1-20261103/f04-04-cierre/review/DICTAMEN-F0404.md](../evidence/s1-20261103/f04-04-cierre/review/DICTAMEN-F0404.md) · [evidence/s1-20261103/f04-04-cierre/MATRIZ-CIERRE.md](../evidence/s1-20261103/f04-04-cierre/MATRIZ-CIERRE.md) · [evidence/s1-20261103/f04-04-cierre/CONCILIACION-EVIDENCIA.json](../evidence/s1-20261103/f04-04-cierre/CONCILIACION-EVIDENCIA.json) · [evidence/s1-20261103/f04-04-cierre/CONTRASTE-NUCLEO.json](../evidence/s1-20261103/f04-04-cierre/CONTRASTE-NUCLEO.json) · [docs/PASO-013-CIERRE-PROVEEDOR-MFA.md](../docs/PASO-013-CIERRE-PROVEEDOR-MFA.md) · [docs/INTEGRACION-PENDIENTES-08-18-CANDIDATA16.md](../docs/INTEGRACION-PENDIENTES-08-18-CANDIDATA16.md) · [evidence/s1-20261104/f04-integracion16/RESULTADOS.md](../evidence/s1-20261104/f04-integracion16/RESULTADOS.md) · [evidence/s1-20261104/f04-integracion16/review/DICTAMEN.md](../evidence/s1-20261104/f04-integracion16/review/DICTAMEN.md) · [evidence/s1-20261104/f04-integracion16/package/ENTREGA.json](../evidence/s1-20261104/f04-integracion16/package/ENTREGA.json) · [evidence/s1-20261104/f04-integracion16/PUBLICACION-EN-PRUEBAS.json](../evidence/s1-20261104/f04-integracion16/PUBLICACION-EN-PRUEBAS.json) · [evidence/s1-20261104/f04-integracion16/HTTP-WRITER-RELEASE-R2.json](../evidence/s1-20261104/f04-integracion16/HTTP-WRITER-RELEASE-R2.json) · [evidence/s1-20261104/f04-integracion16/NEW-RESTORE45.json](../evidence/s1-20261104/f04-integracion16/NEW-RESTORE45.json) · [docs/PASO-011-ALMACEN-MFA.md](../docs/PASO-011-ALMACEN-MFA.md) · [docs/PASO-012-PERMISOS-MFA.md](../docs/PASO-012-PERMISOS-MFA.md).

#### Paso 011 · F-04.01

Cierre técnico conservado e integración del writer en candidata16/app45 completada con revisión independiente; misma DLLRelease en 16 casos y New/RestoreSQL45/43→45 de laboratorio. Falta ensayo nativo/aceptación de 16; no repetir el proveedor ni modificar D.

- Tipo de trabajo: Cerrado técnicamente e integrado en candidata16; aceptación nativa pendiente.
- Estado formal: done; ámbito: Primera entrega; responsable: F-04.
- Texto histórico trazable: Crear almacén separado de management con ACL seguras desde el primer instante y escrituras atómicas por instalador/operador.
- Número conservado tras el cierre: no repetir como nueva implementación.

#### Paso 012 · F-04.02

Completado en E con dos tokens reales: sólo lectura propia/común, ajenos/management y modificación denegados; padres/herencia/reparse e invariancia revisados. Reutilizar evidencia; conservar D. Sigue 13/F-04.04.

- Tipo de trabajo: Cerrado técnicamente con revisión independiente; 504 comprobaciones correctas.
- Estado formal: done; ámbito: Primera entrega; responsable: F-04.
- Texto histórico trazable: Dar sólo lectura al SID efectivo del servicio y mantener management cerrado; comprobar padres, herencia y reparse.
- Número conservado tras el cierre: no repetir como nueva implementación.

#### Paso 013 · F-04.04

Cierre técnico conservado e integración del writer en candidata16/app45 completada con revisión independiente; misma DLLRelease en 16 casos y New/RestoreSQL45/43→45 de laboratorio. Falta ensayo nativo/aceptación de 16; no repetir el proveedor ni modificar D.

- Tipo de trabajo: Cerrado técnicamente e integrado en candidata16; aceptación nativa pendiente.
- Estado formal: done; ámbito: Primera entrega; responsable: F-04.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.
- Número conservado tras el cierre: no repetir como nueva implementación.

### F-05 · Implementar sobre portable autenticado y restauración de claves

**Situación conocida:** 04.11: candidata16 repite creación segura y DB/TOTP sobre su DLLRelease exacta; New/RestoreSQL43→45/45→45 en laboratorio pasa sin factores. Guardiacontinúa rechazando cualquier factor sin sobre; no es implementación del operador portable. Se conserva el contexto del cierre técnico anterior: F-05.01/.02/.03 concilian codec/perfil de 600.000 iteraciones/negativos existentes; .04 comprueba portabilidad Windows y token estándar real con dos factores/AAD, sin repetirla. F-05.05 añade DBaplicación45 nueva, pg_dump/pg_restore custom transacciónúnica, igualdad de todas las filas públicas antes de RecoveryAdministrator y roles nuevos restringidos. ProveedorWindows real sobre material recuperado y Program/WebApplicationFactory: dos logins con factores conservados versiones1 retirada/7 activa, desafío sinAPI, TOTP/sesión/CSRF/API, replay/TOTPincorrecto y autoridad de backup revocada. Ocho casos pasan en WindowsPG17.11, sin omitidas, revisión independiente; sólo nuevo test/runner, sin cambios de producto. Gates de material/versiones/AAD previos son del fixture, no operador productivo. FuenteDebug F0401 cd3 cc/45 fijada; TestServer en memoria con identidad/confianzaWindowsLAB explícita y direcciones de cliente sintéticas para conservar limiter. F-05.04 sigue acreditando otroWindows/SIDreal, no se atribuye esa medición al TestServer. Origen invariable; tres clusters propios detenidos. Dos intentos fallidos de fixture preservados (ruta266/Win32206;contentroot/aserciónCrypto); no se ocultan ni son defectos del producto. F-05 checklist técnica completa, pero implementación operativa, candidata integrada y aceptación permanecen pendientes: no CLI/instalador, fence/journal/marcadorDBD2, exportaciónconcurrente, rotación/pérdida, HTTPS/servicio/reinicio/cutover/R04 o custodia/adopción nuevas. D/E sin operaciones.

**Cierre esperado:** Restore nuevo verifica factores usando clave recuperada; sin material/contraseña correctos falla explícitamente, sin emitir sesión insegura; negativos y revisión independiente.

**Dependencias del resultado:** F-03, F-04.

**Fuentes:** [docs/DECISION-D2-CUSTODIA-CLAVE-TOTP.md](../docs/DECISION-D2-CUSTODIA-CLAVE-TOTP.md) · [docs/REVISION-D2-CODEX.md](../docs/REVISION-D2-CODEX.md) · [docs/AUTENTICACION-MFA-S1.md](../docs/AUTENTICACION-MFA-S1.md) · [docs/REVISION-D14-05-CODEX.md](../docs/REVISION-D14-05-CODEX.md) · [docs/REVISION-MFA-L2D-CODEX-26-10-2026.md](../docs/REVISION-MFA-L2D-CODEX-26-10-2026.md) · [docs/REVISION-MFA-L2E-CODEX-26-10-2026.md](../docs/REVISION-MFA-L2E-CODEX-26-10-2026.md) · [evidence/s1-20261103/f05-01-sobre/RESULTADOS.md](../evidence/s1-20261103/f05-01-sobre/RESULTADOS.md) · [evidence/s1-20261103/f05-01-sobre/review/DICTAMEN-F0501.md](../evidence/s1-20261103/f05-01-sobre/review/DICTAMEN-F0501.md) · [evidence/s1-20261103/f05-01-sobre/MATRIZ-CRITERIO.md](../evidence/s1-20261103/f05-01-sobre/MATRIZ-CRITERIO.md) · [evidence/s1-20261103/f05-01-sobre/CONCILIACION-EVIDENCIA.json](../evidence/s1-20261103/f05-01-sobre/CONCILIACION-EVIDENCIA.json) · [evidence/s1-20261103/f05-02-coste/RESULTADOS.md](../evidence/s1-20261103/f05-02-coste/RESULTADOS.md) · [evidence/s1-20261103/f05-02-coste/review/DICTAMEN-F0502.md](../evidence/s1-20261103/f05-02-coste/review/DICTAMEN-F0502.md) · [evidence/s1-20261103/f05-02-coste/DECISION-PARAMETRO.md](../evidence/s1-20261103/f05-02-coste/DECISION-PARAMETRO.md) · [evidence/s1-20261103/f05-02-coste/MEDICION-CONCILIADA.json](../evidence/s1-20261103/f05-02-coste/MEDICION-CONCILIADA.json) · [evidence/s1-20261103/f05-03-negativos/RESULTADOS.md](../evidence/s1-20261103/f05-03-negativos/RESULTADOS.md) · [evidence/s1-20261103/f05-03-negativos/review/DICTAMEN-F0503.md](../evidence/s1-20261103/f05-03-negativos/review/DICTAMEN-F0503.md) · [evidence/s1-20261103/f05-03-negativos/MATRIZ-NEGATIVOS.md](../evidence/s1-20261103/f05-03-negativos/MATRIZ-NEGATIVOS.md) · [evidence/s1-20261103/f05-03-negativos/NEGATIVOS-CONCILIADOS.json](../evidence/s1-20261103/f05-03-negativos/NEGATIVOS-CONCILIADOS.json) · [docs/PASO-016-NEGATIVOS-SOBRE-MFA.md](../docs/PASO-016-NEGATIVOS-SOBRE-MFA.md) · [docs/PASO-017-RECUPERACION-PORTABLE-MFA.md](../docs/PASO-017-RECUPERACION-PORTABLE-MFA.md) · [evidence/s1-20261103/f05-04-portable/RESULTADOS.md](../evidence/s1-20261103/f05-04-portable/RESULTADOS.md) · [evidence/s1-20261103/f05-04-portable/review/DICTAMEN-F0504.md](../evidence/s1-20261103/f05-04-portable/review/DICTAMEN-F0504.md) · [evidence/s1-20261103/f05-04-portable/review/COMPROBACION-F0504.json](../evidence/s1-20261103/f05-04-portable/review/COMPROBACION-F0504.json) · [evidence/s1-20261103/f05-04-portable/ejecucion/POSTFLIGHT.json](../evidence/s1-20261103/f05-04-portable/ejecucion/POSTFLIGHT.json) · [evidence/s1-20261103/f05-04-portable/ejecucion/06-service-token.json](../evidence/s1-20261103/f05-04-portable/ejecucion/06-service-token.json) · [docs/F05-RECUPERACION-INTEGRADA-PENDIENTE.md](../docs/F05-RECUPERACION-INTEGRADA-PENDIENTE.md) · [docs/PASO-018-CIERRE-RECUPERACION-PORTABLE-MFA.md](../docs/PASO-018-CIERRE-RECUPERACION-PORTABLE-MFA.md) · [evidence/s1-20261103/f05-05-cierre/RESULTADOS.md](../evidence/s1-20261103/f05-05-cierre/RESULTADOS.md) · [evidence/s1-20261103/f05-05-cierre/MATRIZ-CIERRE.md](../evidence/s1-20261103/f05-05-cierre/MATRIZ-CIERRE.md) · [evidence/s1-20261103/f05-05-cierre/review/DICTAMEN-F0505.md](../evidence/s1-20261103/f05-05-cierre/review/DICTAMEN-F0505.md) · [evidence/s1-20261103/f05-05-cierre/review/COMPROBACION-F0505.json](../evidence/s1-20261103/f05-05-cierre/review/COMPROBACION-F0505.json) · [evidence/s1-20261103/f05-05-cierre/COORDINACION-PG-R3.json](../evidence/s1-20261103/f05-05-cierre/COORDINACION-PG-R3.json) · [evidence/s1-20261103/f05-05-cierre/implementacion/HARNESS-FREEZE6-PREVIO-PG.json](../evidence/s1-20261103/f05-05-cierre/implementacion/HARNESS-FREEZE6-PREVIO-PG.json) · [evidence/s1-20261103/f05-05-cierre/implementacion/RESUMEN-SANITIZADO-CORRIDA3.json](../evidence/s1-20261103/f05-05-cierre/implementacion/RESUMEN-SANITIZADO-CORRIDA3.json) · [docs/INTEGRACION-PENDIENTES-08-18-CANDIDATA16.md](../docs/INTEGRACION-PENDIENTES-08-18-CANDIDATA16.md) · [evidence/s1-20261104/f04-integracion16/RESULTADOS.md](../evidence/s1-20261104/f04-integracion16/RESULTADOS.md) · [evidence/s1-20261104/f04-integracion16/review/DICTAMEN.md](../evidence/s1-20261104/f04-integracion16/review/DICTAMEN.md) · [evidence/s1-20261104/f04-integracion16/package/ENTREGA.json](../evidence/s1-20261104/f04-integracion16/package/ENTREGA.json) · [evidence/s1-20261104/f04-integracion16/PUBLICACION-EN-PRUEBAS.json](../evidence/s1-20261104/f04-integracion16/PUBLICACION-EN-PRUEBAS.json) · [evidence/s1-20261104/f04-integracion16/HTTP-WRITER-RELEASE-R2.json](../evidence/s1-20261104/f04-integracion16/HTTP-WRITER-RELEASE-R2.json) · [evidence/s1-20261104/f04-integracion16/NEW-RESTORE45.json](../evidence/s1-20261104/f04-integracion16/NEW-RESTORE45.json) · [docs/PASO-014-VALIDACION-SOBRE-MFA.md](../docs/PASO-014-VALIDACION-SOBRE-MFA.md) · [docs/PASO-015-COSTE-PBKDF2-MFA.md](../docs/PASO-015-COSTE-PBKDF2-MFA.md).

#### Paso 014 · F-05.01

Validación del codec RCKEY existente conciliada y revisada: perfil fijo/tamaños/UTF8 antes de KDF y cabeceraAAD completa. Sin nuevo codec o suite; D conservada. Seguir15/F-05.02; recuperación integrada permanece pendiente.

- Tipo de trabajo: Cerrado técnicamente con revisión independiente; evidencia histórica reutilizada.
- Estado formal: done; ámbito: Primera entrega; responsable: F-05.
- Texto histórico trazable: Validar magia/versión/algoritmo, tamaños, codificación canónica y límites min/max de iteraciones antes de KDF; autenticar cabecera completa como AAD.
- Número conservado tras el cierre: no repetir como nueva implementación.

#### Paso 015 · F-05.02

Medición Windows histórica conciliada con unidad correcta y decisión explícita de conservar600000; revisión favorable. Casos completos de 57-62 ms, no KDF aislado ni medida universal/deD. Sigue16/F-05.03; no repetir benchmark sin hueco demostrado.

- Tipo de trabajo: Cerrado con revisión independiente; coste observado y perfil ratificado.
- Estado formal: done; ámbito: Primera entrega; responsable: F-05.
- Texto histórico trazable: Medir coste del parámetro propuesto600000 en Windows antes de fijarlo; no adoptarlo por silencio.
- Número conservado tras el cierre: no repetir como nueva implementación.

#### Paso 016 · F-05.03

Negativos RCKEY existentes conciliados y revisados:contraseña/alteración/truncado/extra/versiones/algoritmos/coste/tamaño. Sin nueva suite o cambios de producto; D conservada. Sigue17/F-05.04, recuperación portable real todavía pendiente.

- Tipo de trabajo: Cerrado técnicamente con revisión independiente; evidencia histórica reutilizada.
- Estado formal: done; ámbito: Primera entrega; responsable: F-05.
- Texto histórico trazable: Probar contraseña errónea, alteración, truncado, datos extra, versión/algoritmo desconocidos y coste/tamaño fuera de rango.
- Número conservado tras el cierre: no repetir como nueva implementación.

#### Paso 017 · F-05.04

Recuperación portable LEAO→WindowsServerE comprobada con dos factores/AAD y token estándar real; negativos y limpieza revisados. Sólo ensayo offline, sin adoptar DB/host. D conservada. Sigue18/F-05.05; no repetir el codec o importar material de usuario.

- Tipo de trabajo: Cerrado técnicamente con revisión independiente; portabilidad real offline.
- Estado formal: done; ámbito: Primera entrega; responsable: F-05.
- Texto histórico trazable: Recuperar anillo en otra instancia Windows preservando AAD Systemhaus/usuario/versión o mediante reenvoltura explícita; sobre y contraseña separados del dump.
- Número conservado tras el cierre: no repetir como nueva implementación.

#### Paso 018 · F-05.05

Cierre técnico F05 revisado: DBaplicación45 dump/restore y proveedorWindows/material recuperado con Program/TestServer,8/8 casos. No operador/instalador/adopción. Reutilizar evidencia; sigue19/F-06.01, D/E conservados.

- Tipo de trabajo: Cerrado técnicamente con revisión independiente; integración de componentes en laboratorio.
- Estado formal: done; ámbito: Primera entrega; responsable: F-05.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.
- Número conservado tras el cierre: no repetir como nueva implementación.

### F-06 · Cerrar rotación y recuperación coherente entre anillo y PostgreSQL

**Situación conocida:** F-06 cerrado en su criterio técnico con F-06.01–.04: fases, catálogo/retirada, caídas y recuperación trazados. Nueva prueba encadenada con tres backups reales retenidos, dos rotaciones a8/9 y Restore de cada generación en clúster nuevo; todos los TOTP/metadatos conservados y claves sólo referidas por backup protegidas. Cinco invocaciones PASS sin omisiones y revisión independiente con otras cinco; producto227 archivos idéntico a F0603, cuyas360 pruebas/15 cortes se reutilizan sin repetirlas. Sin CLI pública, integración/instalador46, SID efectivo/custodia externa real o aceptación nativa. D/E intactos.

**Cierre esperado:** Cada punto de interrupción tiene estado recuperable demostrado; todos los factores/backups retenidos siguen descifrables con versiones conservadas y faltantes se rechazan explícitamente.

**Dependencias del resultado:** F-04, F-05.

**Fuentes:** [docs/PLAN-F0604-CIERRE-ROTACION.md](../docs/PLAN-F0604-CIERRE-ROTACION.md) · [docs/PASO-022-CIERRE-ROTACION-MFA.md](../docs/PASO-022-CIERRE-ROTACION-MFA.md) · [evidence/s1-20261111/f06-04-cierre/RESULTADOS.md](../evidence/s1-20261111/f06-04-cierre/RESULTADOS.md) · [evidence/s1-20261111/f06-04-cierre/MATRIZ-CIERRE.md](../evidence/s1-20261111/f06-04-cierre/MATRIZ-CIERRE.md) · [evidence/s1-20261111/f06-04-cierre/RETENIDOS.json](../evidence/s1-20261111/f06-04-cierre/RETENIDOS.json) · [evidence/s1-20261111/f06-04-cierre/FUENTES.json](../evidence/s1-20261111/f06-04-cierre/FUENTES.json) · [evidence/s1-20261111/f06-04-cierre/PIN-NEGATIVO.json](../evidence/s1-20261111/f06-04-cierre/PIN-NEGATIVO.json) · [evidence/s1-20261111/f06-04-cierre/review/DICTAMEN.md](../evidence/s1-20261111/f06-04-cierre/review/DICTAMEN.md) · [docs/PROTOCOLO-ROTACION-MFA-v1.md](../docs/PROTOCOLO-ROTACION-MFA-v1.md) · [docs/PASO-019-FASES-ROTACION-MFA.md](../docs/PASO-019-FASES-ROTACION-MFA.md) · [evidence/s1-20261109/f06-01-fases/MATRIZ-CRITERIO.md](../evidence/s1-20261109/f06-01-fases/MATRIZ-CRITERIO.md) · [evidence/s1-20261109/f06-01-fases/RESULTADOS.md](../evidence/s1-20261109/f06-01-fases/RESULTADOS.md) · [evidence/s1-20261109/f06-01-fases/review/DICTAMEN-F0601.md](../evidence/s1-20261109/f06-01-fases/review/DICTAMEN-F0601.md) · [docs/PLAN-F0602-CATALOGO-Y-RETIRADA.md](../docs/PLAN-F0602-CATALOGO-Y-RETIRADA.md) · [docs/MANTENIMIENTO-CATALOGO-Y-RETIRADA-MFA.md](../docs/MANTENIMIENTO-CATALOGO-Y-RETIRADA-MFA.md) · [evidence/s1-20261109/f06-02-retirada/RESULTADOS.md](../evidence/s1-20261109/f06-02-retirada/RESULTADOS.md) · [evidence/s1-20261109/f06-02-retirada/REVISION.md](../evidence/s1-20261109/f06-02-retirada/REVISION.md) · [evidence/s1-20261109/f06-02-retirada/POSTGRES-REGRESION.json](../evidence/s1-20261109/f06-02-retirada/POSTGRES-REGRESION.json) · [evidence/s1-20261109/f06-02-retirada/BACKUP-NATIVO.json](../evidence/s1-20261109/f06-02-retirada/BACKUP-NATIVO.json) · [evidence/s1-20261109/f06-02-retirada/FUENTES.json](../evidence/s1-20261109/f06-02-retirada/FUENTES.json) · [docs/CONTRATO-INVENTARIO-RETENCION-MFA-v1.md](../docs/CONTRATO-INVENTARIO-RETENCION-MFA-v1.md) · [docs/PASO-020-INVENTARIO-RETENCION-MFA.md](../docs/PASO-020-INVENTARIO-RETENCION-MFA.md) · [evidence/s1-20261109/f06-02-retencion/RESULTADOS.md](../evidence/s1-20261109/f06-02-retencion/RESULTADOS.md) · [evidence/s1-20261109/f06-02-retencion/MATRIZ-CRITERIO.md](../evidence/s1-20261109/f06-02-retencion/MATRIZ-CRITERIO.md) · [evidence/s1-20261109/f06-02-retencion/review/DICTAMEN-F0602.md](../evidence/s1-20261109/f06-02-retencion/review/DICTAMEN-F0602.md) · [evidence/s1-20261109/f06-02-retencion/POSTGRES-CENSO-BACKUP.json](../evidence/s1-20261109/f06-02-retencion/POSTGRES-CENSO-BACKUP.json) · [evidence/s1-20261109/f06-02-retencion/REGRESION-COMPONENTES.json](../evidence/s1-20261109/f06-02-retencion/REGRESION-COMPONENTES.json) · [docs/PLAN-F0602-INTEGRACION-BACKUP.md](../docs/PLAN-F0602-INTEGRACION-BACKUP.md) · [docs/BACKUP-MFA-CON-INVENTARIO-DESARROLLO.md](../docs/BACKUP-MFA-CON-INVENTARIO-DESARROLLO.md) · [evidence/s1-20261109/f06-02-nativo/RESULTADOS.md](../evidence/s1-20261109/f06-02-nativo/RESULTADOS.md) · [evidence/s1-20261109/f06-02-nativo/POSTGRES-NATIVO.json](../evidence/s1-20261109/f06-02-nativo/POSTGRES-NATIVO.json) · [evidence/s1-20261109/f06-02-nativo/REGRESION.json](../evidence/s1-20261109/f06-02-nativo/REGRESION.json) · [evidence/s1-20261109/f06-02-nativo/REVISION-INDEPENDIENTE.md](../evidence/s1-20261109/f06-02-nativo/REVISION-INDEPENDIENTE.md) · [docs/PLAN-F0603-ROTACION-Y-CAIDAS.md](../docs/PLAN-F0603-ROTACION-Y-CAIDAS.md) · [docs/PASO-021-CAIDAS-ROTACION-MFA.md](../docs/PASO-021-CAIDAS-ROTACION-MFA.md) · [evidence/s1-20261110/f06-03-rotacion/RESULTADOS.md](../evidence/s1-20261110/f06-03-rotacion/RESULTADOS.md) · [evidence/s1-20261110/f06-03-rotacion/REVISION.md](../evidence/s1-20261110/f06-03-rotacion/REVISION.md) · [evidence/s1-20261110/f06-03-rotacion/FUENTES.json](../evidence/s1-20261110/f06-03-rotacion/FUENTES.json) · [evidence/s1-20261110/f06-03-rotacion/POSTGRES-REGRESION.json](../evidence/s1-20261110/f06-03-rotacion/POSTGRES-REGRESION.json) · [evidence/s1-20261110/f06-03-rotacion/MATRIZ-CAIDAS.json](../evidence/s1-20261110/f06-03-rotacion/MATRIZ-CAIDAS.json) · [evidence/s1-20261110/f06-03-rotacion/NEGATIVOS.json](../evidence/s1-20261110/f06-03-rotacion/NEGATIVOS.json).

#### Paso 019 · F-06.01

F-06.01 cerrado como especificación de fases con revisión independiente: n verificada y anillo aditivo con activa anterior antes de DB, sobre externo/persistencia exigidos, recifrado transaccional con testigo y publicación final hacia delante, fence/guard y conciliación de commit incierto. Todos los factores persistidos y versiones de backups se conservan; no se recortan estados/antirreplay/gracia. No se implementa o ejecuta un rotador, migración, retirada o caída; F-06.02/.03/.04 e hitos operativos siguen pendientes. D/E sin operaciones; reutilizar evidencia y seguir20/F-06.02.

- Tipo de trabajo: Especificación de fases cerrada con revisión independiente; rotación operativa pendiente.
- Estado formal: done; ámbito: Primera entrega; responsable: F-06.
- Texto histórico trazable: Especificar fases: persistir/verificar clave nueva antes de usarla, conservar versiones requeridas, reenvolver factores y publicar anillo coherente.
- Número conservado tras el cierre: no repetir como nueva implementación.

#### Paso 020 · F-06.02

F-06.02 cerrado técnicamente: catálogo privado con declaración de todas las raíces retenidas, inventarios/recibos pineados y comprobación exacta de objetos; unknown/legacy/parcial/missing/tampered bloquean. Retirada lógica real de versión no activa/sin factores ni backups dependientes bajo locklocal+admisiónPG+ACCESS EXCLUSIVE, censo nuevo y autenticaciónAAD. Fence/journal/publicación/reanudación e idempotencia conservan archivosDPAPI; no recifrado, SQLmutante o destruccióncriptográfica. 297 regresión pertinente+8 backup nativo+18Python, sinomisiones; revisor distinto153 focales propios y dictamen favorable sólo5/8 deestecriterio. CLI elevada/SCMpositivoservicioinstalado y token real no ensayados; siguen en QA/hitos. F-06.03 rotación/testigo/caídasreales yF-06.04 pendientes. D/E intactos; sin commits/push/instaladores/despliegues. La cobertura atestada no descubreUSB/raícesomitidas por el operador; no expira backups. Reutilizar componentes y evidencia, no repetir codecs/login/portabilidad.

- Tipo de trabajo: Cerrado técnicamente: catálogo y retirada lógica revisados; no adopción instalada/rotación.
- Estado formal: done; ámbito: Primera entrega; responsable: F-06.
- Texto histórico trazable: Retirar una versión sólo si ningún factor ni backup retenido la necesita; incluir inventario de versiones en backup/sobre.
- Número conservado tras el cierre: no repetir como nueva implementación.

#### Paso 021 · F-06.03

F-06.01/.02 conservados. F-06.03: rotación interna offline con SQL046 aditivo/testigo transaccional, publicación de clave/anillos/recibo bajo coordinador, guard de vínculo y reanudación por hechos; DPAPI anterior, TOTP/metadatos/política conservados. 360/360 regresión pertinente,15 cortes de proceso con 15 reaperturas,2 Restores custom en otros clústeres nuevos,3 negativos PG/publicación y 14 operadores; sin omisiones en resultados finales. Revisión distinta registrada con sus ejecuciones/pines y límites. Sin CLI pública rotate, instalador46, apagón/Windowsreboot, SID efectivo/servicio instalado, custodia externa real o QA/adopción. D/E intactos. No es cierre integral F-06.04/R-04 ni porcentaje global. Reutilizar este alcance, no repetir codecs/factores/retirada.

- Tipo de trabajo: Cerrado técnicamente: caídas/reinicio del coordinador y Restore de laboratorio; integración operativa pendiente.
- Estado formal: done; ámbito: Primera entrega; responsable: F-06.
- Texto histórico trazable: Inyectar caída antes/después de cada publicación y commit; reinicio/Restore deben identificar estado y recuperar sin perder factores.
- Número conservado tras el cierre: no repetir como nueva implementación.

#### Paso 022 · F-06.04

F-06 cerrado en su criterio técnico con F-06.01–.04: fases, catálogo/retirada, caídas y recuperación trazados. Nueva prueba encadenada con tres backups reales retenidos, dos rotaciones a8/9 y Restore de cada generación en clúster nuevo; todos los TOTP/metadatos conservados y claves sólo referidas por backup protegidas. Cinco invocaciones PASS sin omisiones y revisión independiente con otras cinco; producto227 archivos idéntico a F0603, cuyas360 pruebas/15 cortes se reutilizan sin repetirlas. Sin CLI pública, integración/instalador46, SID efectivo/custodia externa real o aceptación nativa. D/E intactos.

- Tipo de trabajo: Cierre técnico acreditado; implementación operativa, integración y aceptación pendientes.
- Estado formal: done; ámbito: Primera entrega; responsable: F-06.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.
- Número conservado tras el cierre: no repetir como nueva implementación.

### F-07 · Completar enrolamiento restringido cuando MFA sea exigible

**Situación conocida:** F-07.01–.05 cerrados técnicamente: enrolamiento restringido existente contrastado con evidencia GUI/nativa y fuentes actuales. Dos escenarios nuevos con cuentas ordinarias de gracia45 vencida, Windows/DPAPI real y rol SQL restringido: desafío/pending/código inválido sin /me, clientes ni mutaciones; cookie renombrada no autoriza. Dos confirmaciones producen una única sesión/CSRF nuevos, con testigo SQL de identidad/transacción y replay rechazado. 2/2 casos,36/36 de núcleo y 70/70 Node, sin omitidas; revisor distinto repite2/2. Producto227 archivos conservado, sin nuevo login o política. D/E intactos. Integración de candidata objetivo y aceptación pendientes; no nuevo ensayo TLS/servicio ni cierre de emergencia/custodia externa.

**Cierre esperado:** Usuario nuevo completa primer factor y obtiene única sesión nueva sólo al confirmar; desafío/enrolamiento incompleto no acceden a /me, clientes ni mutaciones; negativos concurrentes y revisión independiente.

**Dependencias del resultado:** F-04 para producto; proveedor sintético aislado puede permitir desarrollo/pruebas previas.

**Fuentes:** [docs/PLAN-F0705-CIERRE-ENROLAMIENTO.md](../docs/PLAN-F0705-CIERRE-ENROLAMIENTO.md) · [docs/PASO-023-CIERRE-ENROLAMIENTO-MFA.md](../docs/PASO-023-CIERRE-ENROLAMIENTO-MFA.md) · [evidence/s1-20261111/f07-05-enrolamiento/RESULTADOS.md](../evidence/s1-20261111/f07-05-enrolamiento/RESULTADOS.md) · [evidence/s1-20261111/f07-05-enrolamiento/MATRIZ-CIERRE.md](../evidence/s1-20261111/f07-05-enrolamiento/MATRIZ-CIERRE.md) · [evidence/s1-20261111/f07-05-enrolamiento/HTTP-ENROLAMIENTO.json](../evidence/s1-20261111/f07-05-enrolamiento/HTTP-ENROLAMIENTO.json) · [evidence/s1-20261111/f07-05-enrolamiento/REGRESION-NUCLEO.json](../evidence/s1-20261111/f07-05-enrolamiento/REGRESION-NUCLEO.json) · [evidence/s1-20261111/f07-05-enrolamiento/FRONTEND.json](../evidence/s1-20261111/f07-05-enrolamiento/FRONTEND.json) · [evidence/s1-20261111/f07-05-enrolamiento/FUENTES.json](../evidence/s1-20261111/f07-05-enrolamiento/FUENTES.json) · [evidence/s1-20261111/f07-05-enrolamiento/PIN-NEGATIVO.json](../evidence/s1-20261111/f07-05-enrolamiento/PIN-NEGATIVO.json) · [evidence/s1-20261111/f07-05-enrolamiento/review/DICTAMEN.md](../evidence/s1-20261111/f07-05-enrolamiento/review/DICTAMEN.md).

#### Paso 023 · F-07.05

F-07.01–.05 cerrados técnicamente: enrolamiento restringido existente contrastado con evidencia GUI/nativa y fuentes actuales. Dos escenarios nuevos con cuentas ordinarias de gracia45 vencida, Windows/DPAPI real y rol SQL restringido: desafío/pending/código inválido sin /me, clientes ni mutaciones; cookie renombrada no autoriza. Dos confirmaciones producen una única sesión/CSRF nuevos, con testigo SQL de identidad/transacción y replay rechazado. 2/2 casos,36/36 de núcleo y 70/70 Node, sin omitidas; revisor distinto repite2/2. Producto227 archivos conservado, sin nuevo login o política. D/E intactos. Integración de candidata objetivo y aceptación pendientes; no nuevo ensayo TLS/servicio ni cierre de emergencia/custodia externa.

- Tipo de trabajo: Cerrado técnicamente; integración de candidata objetivo y aceptación pendientes.
- Estado formal: done; ámbito: Primera entrega; responsable: F-07.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.
- Número conservado tras el cierre: no repetir como nueva implementación.

### F-08 · Implementar códigos de recuperación y reenrolamiento restringido

**Situación conocida:** F-08.01–.05 cerrados técnicamente y revisados en conjunto. Se conserva la generación expresa de diez códigos propios, entrega inicial única, hashes salados y canje a enrolamiento restringido: sólo TOTP nuevo permite sesión/API, también para único global; revocación/auditoría/rollback y concurrencia real contrastados. Build corregido F0804 sin recompilar, 227 archivos y cuatro tests previos conservados; foco12/12 y revisor6/6 PASS, sin omitidas. Frontend privado18 archivos: positivos Edge de dashboard8 y recuperación4 en corridas distintas; primer conjunto1PASS/1FAIL y recuperación intermitente sin causa acreditada, siete intentos preservados, sin presentar batería íntegramente verde. Sin cambios de producto, guiones compartidos, SQL, dependencias o D/E. Cuatro hitos técnicos acreditados; integración de candidata, aceptación/custodia y emergencia F-09 siguen pendientes.

**Cierre esperado:** Cada código sirve una sola vez incluso en concurrencia; recuperación no abre API antes del estado autorizado; reenrolamiento y revocación/auditoría sin secretos probados por revisor distinto.

**Dependencias del resultado:** F-07, F-10.

**Fuentes:** [docs/PLAN-F0805-CIERRE-CODIGOS.md](../docs/PLAN-F0805-CIERRE-CODIGOS.md) · [docs/PASO-028-CIERRE-CODIGOS-MFA.md](../docs/PASO-028-CIERRE-CODIGOS-MFA.md) · [evidence/s1-20261111/f08-05-cierre/RESULTADOS.md](../evidence/s1-20261111/f08-05-cierre/RESULTADOS.md) · [evidence/s1-20261111/f08-05-cierre/MATRIZ-CIERRE.md](../evidence/s1-20261111/f08-05-cierre/MATRIZ-CIERRE.md) · [evidence/s1-20261111/f08-05-cierre/FOCO.json](../evidence/s1-20261111/f08-05-cierre/FOCO.json) · [evidence/s1-20261111/f08-05-cierre/FUENTES.json](../evidence/s1-20261111/f08-05-cierre/FUENTES.json) · [evidence/s1-20261111/f08-05-cierre/FRONTEND.json](../evidence/s1-20261111/f08-05-cierre/FRONTEND.json) · [evidence/s1-20261111/f08-05-cierre/NAVEGADOR-INTENTOS.json](../evidence/s1-20261111/f08-05-cierre/NAVEGADOR-INTENTOS.json) · [evidence/s1-20261111/f08-05-cierre/OBSERVACION-NAVEGADOR.md](../evidence/s1-20261111/f08-05-cierre/OBSERVACION-NAVEGADOR.md) · [evidence/s1-20261111/f08-05-cierre/review/DICTAMEN.md](../evidence/s1-20261111/f08-05-cierre/review/DICTAMEN.md) · [docs/PLAN-F0801-GENERACION-CODIGOS.md](../docs/PLAN-F0801-GENERACION-CODIGOS.md) · [docs/PASO-024-GENERACION-CODIGOS-MFA.md](../docs/PASO-024-GENERACION-CODIGOS-MFA.md) · [evidence/s1-20261111/f08-01-generacion/RESULTADOS.md](../evidence/s1-20261111/f08-01-generacion/RESULTADOS.md) · [evidence/s1-20261111/f08-01-generacion/MATRIZ-CRITERIO.md](../evidence/s1-20261111/f08-01-generacion/MATRIZ-CRITERIO.md) · [evidence/s1-20261111/f08-01-generacion/FOCO.json](../evidence/s1-20261111/f08-01-generacion/FOCO.json) · [evidence/s1-20261111/f08-01-generacion/FRONTEND.json](../evidence/s1-20261111/f08-01-generacion/FRONTEND.json) · [evidence/s1-20261111/f08-01-generacion/FUENTES.json](../evidence/s1-20261111/f08-01-generacion/FUENTES.json) · [evidence/s1-20261111/f08-01-generacion/review/DICTAMEN.md](../evidence/s1-20261111/f08-01-generacion/review/DICTAMEN.md) · [docs/PLAN-F0802-RECUPERACION-RESTRINGIDA.md](../docs/PLAN-F0802-RECUPERACION-RESTRINGIDA.md) · [docs/PASO-025-RECUPERACION-RESTRINGIDA-MFA.md](../docs/PASO-025-RECUPERACION-RESTRINGIDA-MFA.md) · [evidence/s1-20261111/f08-02-recuperacion/RESULTADOS.md](../evidence/s1-20261111/f08-02-recuperacion/RESULTADOS.md) · [evidence/s1-20261111/f08-02-recuperacion/MATRIZ-CRITERIO.md](../evidence/s1-20261111/f08-02-recuperacion/MATRIZ-CRITERIO.md) · [evidence/s1-20261111/f08-02-recuperacion/FOCO.json](../evidence/s1-20261111/f08-02-recuperacion/FOCO.json) · [evidence/s1-20261111/f08-02-recuperacion/FRONTEND.json](../evidence/s1-20261111/f08-02-recuperacion/FRONTEND.json) · [evidence/s1-20261111/f08-02-recuperacion/FUENTES.json](../evidence/s1-20261111/f08-02-recuperacion/FUENTES.json) · [evidence/s1-20261111/f08-02-recuperacion/review/DICTAMEN.md](../evidence/s1-20261111/f08-02-recuperacion/review/DICTAMEN.md) · [docs/PLAN-F0803-CONSUMO-TRANSACCIONAL.md](../docs/PLAN-F0803-CONSUMO-TRANSACCIONAL.md) · [docs/PASO-026-CONSUMO-CODIGOS-MFA.md](../docs/PASO-026-CONSUMO-CODIGOS-MFA.md) · [evidence/s1-20261111/f08-03-consumo/RESULTADOS.md](../evidence/s1-20261111/f08-03-consumo/RESULTADOS.md) · [evidence/s1-20261111/f08-03-consumo/MATRIZ-CRITERIO.md](../evidence/s1-20261111/f08-03-consumo/MATRIZ-CRITERIO.md) · [evidence/s1-20261111/f08-03-consumo/FOCO.json](../evidence/s1-20261111/f08-03-consumo/FOCO.json) · [evidence/s1-20261111/f08-03-consumo/FUENTES.json](../evidence/s1-20261111/f08-03-consumo/FUENTES.json) · [evidence/s1-20261111/f08-03-consumo/REUTILIZACION.json](../evidence/s1-20261111/f08-03-consumo/REUTILIZACION.json) · [evidence/s1-20261111/f08-03-consumo/review/DICTAMEN.md](../evidence/s1-20261111/f08-03-consumo/review/DICTAMEN.md) · [docs/PLAN-F0804-ULTIMO-ADMINISTRADOR.md](../docs/PLAN-F0804-ULTIMO-ADMINISTRADOR.md) · [docs/PASO-027-ULTIMO-ADMINISTRADOR-MFA.md](../docs/PASO-027-ULTIMO-ADMINISTRADOR-MFA.md) · [evidence/s1-20261111/f08-04-ultimo-administrador/RESULTADOS.md](../evidence/s1-20261111/f08-04-ultimo-administrador/RESULTADOS.md) · [evidence/s1-20261111/f08-04-ultimo-administrador/MATRIZ-CRITERIO.md](../evidence/s1-20261111/f08-04-ultimo-administrador/MATRIZ-CRITERIO.md) · [evidence/s1-20261111/f08-04-ultimo-administrador/FOCO.json](../evidence/s1-20261111/f08-04-ultimo-administrador/FOCO.json) · [evidence/s1-20261111/f08-04-ultimo-administrador/FUENTES.json](../evidence/s1-20261111/f08-04-ultimo-administrador/FUENTES.json) · [evidence/s1-20261111/f08-04-ultimo-administrador/FRONTEND.json](../evidence/s1-20261111/f08-04-ultimo-administrador/FRONTEND.json) · [evidence/s1-20261111/f08-04-ultimo-administrador/SCOPE-RECONCILIACION.json](../evidence/s1-20261111/f08-04-ultimo-administrador/SCOPE-RECONCILIACION.json) · [evidence/s1-20261111/f08-04-ultimo-administrador/D2-ROJO-VERDE-INDEPENDIENTE.json](../evidence/s1-20261111/f08-04-ultimo-administrador/D2-ROJO-VERDE-INDEPENDIENTE.json) · [evidence/s1-20261111/f08-04-ultimo-administrador/CAMBIOS-PRODUCTO.patch](../evidence/s1-20261111/f08-04-ultimo-administrador/CAMBIOS-PRODUCTO.patch) · [evidence/s1-20261111/f08-04-ultimo-administrador/review/DICTAMEN.md](../evidence/s1-20261111/f08-04-ultimo-administrador/review/DICTAMEN.md).

#### Paso 024 · F-08.01

F-08.01 cerrado técnicamente: generación explícita existente de diez códigos propios con 128 bits aleatorios y hashes con sal de 128 bits, ligados a Systemhaus/usuario e independientes de la clave TOTP. Sólo la primera respuesta entrega valores; status, receipt y replay no los revelan. Una nueva prueba con dos solicitudes realmente bloqueadas simultáneamente confirma una sola entrega, diez hashes, una operación y un evento de auditoría. Pasaron 15 casos focales y 10 de Node; un revisor distinto repitió 1/1. Los 227 archivos de producto se conservaron. No se acreditan generación automática al confirmar, custodia/canje en candidata instalada, último administrador ni F-08.02 a F-08.05. D y E intactas.

- Tipo de trabajo: Cerrado técnicamente; custodia/uso instalado y F0802–05 pendientes.
- Estado formal: done; ámbito: Primera entrega; responsable: F-08.
- Texto histórico trazable: Generar y mostrar una sola vez códigos por usuario; almacenar sólo hashes con sal conforme D2, sin dependencia de clave TOTP.
- Número conservado tras el cierre: no repetir como nueva implementación.

#### Paso 025 · F-08.02

F-08.01 y F-08.02 cerrados técnicamente. Se conserva la generación revisada; contraseña y código de recuperación sólo emiten un desafío enroll nuevo, sin sesión API. Dos casos HTTP nuevos (cuenta ordinaria/global) comprueban lecturas/escrituras denegadas tras canje, start, confirmación inválida y otro login, incluso con cookie renombrada o sesión antigua. Sólo confirmar el factor nuevo emite sesión/CSRF nuevos. Gracia45 conservada. Foco final 6/6 y Node 20/20 PASS; revisor distinto repite 2/2. Producto 227 archivos conservado, sin nuevo login/política. D/E intactos. F-08.03–.05, custodia, último administrador, candidata instalada y aceptación pendientes.

- Tipo de trabajo: Cerrado técnicamente; integración/QA instalada e hitos operativos de F-08 pendientes.
- Estado formal: done; ámbito: Primera entrega; responsable: F-08.
- Texto histórico trazable: Concretar e implementar si password+código concede sólo recuperación restringida hasta reenrolar; no dejar frase ambigua que emita sesión normal antes de nuevo factor.
- Número conservado tras el cierre: no repetir como nueva implementación.

#### Paso 026 · F-08.03

F-08.01–.03 cerrados técnicamente. Se conserva el canje existente: una sola transacción consume el conjunto antiguo, revoca sesiones/desafíos y exige reenrolamiento con auditoría sin valores originales. Dos escenarios nuevos fuerzan canjes realmente solapados (mismo código o dos distintos), un ganador y seis relaciones en la transacción ganadora bajo rol runtime; otra cuenta y gracia45 intactas. Foco 9/9 PASS y repetición independiente 3/3, con rollback forzado y negativos existentes. Producto 227 archivos conservado; HTTP/Node/Edge anteriores reutilizados, no repetidos como nuevos. D/E intactos. Custodia, último administrador, F-08.04/.05, candidata instalada y aceptación pendientes.

- Tipo de trabajo: Cerrado técnicamente; integración/QA instalada e hitos operativos de F-08 pendientes.
- Estado formal: done; ámbito: Primera entrega; responsable: F-08.
- Texto histórico trazable: Consumir transaccionalmente, invalidar sesiones/desafíos/códigos anteriores según contrato y probar consumo concurrente/replay/rollback/secretos.
- Número conservado tras el cierre: no repetir como nueva implementación.

#### Paso 027 · F-08.04

F-08.01–.04 cerrados técnicamente. Único global por ambas capacidades recupera con contraseña/código, conserva identidad/autoridad y vuelve a administrar sólo tras confirmar un factor nuevo; repone códigos y conserva la guarda del último administrador de seguridad. Se corrigió un fallo preexistente D2: Desactivar ya no cancela pending (409 y CanDisable=false), sin alterar gracia45/exención de factor activo no pendiente. Base de 227: 226 archivos conservados y MfaAccountManagement corregido, una prueba nueva con 5 casos. Rojo D2 0/2 → verde 2/2; regresión de 49 seleccionados = 48 PASS / 0 FAIL / 1 navegador opcional omitido, conciliada por discovery sin ejecución nueva; 68 Node PASS. Revisor distinto: 5/5 y sondas roja/verde. D/E intactos, sin despliegue. F-08.05, custodia, emergencia F-09, candidata instalada y aceptación pendientes.

- Tipo de trabajo: Cerrado técnicamente con corrección D2 revisada; integración/QA instalada e hitos operativos pendientes.
- Estado formal: done; ámbito: Primera entrega; responsable: F-08.
- Texto histórico trazable: Garantizar vía administrativa de recuperación con códigos válidos sin bloquear último administrador.
- Número conservado tras el cierre: no repetir como nueva implementación.

#### Paso 028 · F-08.05

F-08.01–.05 cerrados técnicamente y revisados en conjunto. Se conserva la generación expresa de diez códigos propios, entrega inicial única, hashes salados y canje a enrolamiento restringido: sólo TOTP nuevo permite sesión/API, también para único global; revocación/auditoría/rollback y concurrencia real contrastados. Build corregido F0804 sin recompilar, 227 archivos y cuatro tests previos conservados; foco12/12 y revisor6/6 PASS, sin omitidas. Frontend privado18 archivos: positivos Edge de dashboard8 y recuperación4 en corridas distintas; primer conjunto1PASS/1FAIL y recuperación intermitente sin causa acreditada, siete intentos preservados, sin presentar batería íntegramente verde. Sin cambios de producto, guiones compartidos, SQL, dependencias o D/E. Cuatro hitos técnicos acreditados; integración de candidata, aceptación/custodia y emergencia F-09 siguen pendientes.

- Tipo de trabajo: Cierre técnico conjunto revisado; integración/aceptación y observación de automatización Edge pendientes.
- Estado formal: done; ámbito: Primera entrega; responsable: F-08.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.
- Número conservado tras el cierre: no repetir como nueva implementación.

### F-09 · Implementar recuperación local cuando no quedan clave, sobre ni códigos

**Situación conocida:** F-09.01–.04 técnicos: CLI local de pérdida con cinco fases, finalización/recibo/guarda y proyección48 mínima no actualizable. Ensayo real en instancia separada de E: pérdida de toda su clave v1, arranque rechazado sin listener, mantenimiento SYSTEM, servidor estándar, regreso HTTPS mediante enrolamiento restringido/TOTP2, credenciales antiguas revocadas e inventario sentinel conservado. Regresión378/378 y revisión independiente40/40 reutilizadas; revisión nativa final favorable por lectura de fuentes/recibos. 221/232 fuentes previas conservadas,11 modificadas/4 nuevas,total236; sin dependencias nuevas. D sin acceso; dos servicios previos de E Running con iguales PID, propios detenidos/puertos y tareas0. Fallos del arnés preservados, cliente HTTPAdmin separado de mantenimientoSYSTEM. F-09.05, seis hitos completos, instalador/Restore48, mantenimientoAdmin, custodia externa y QA/adopción pendientes.

**Cierre esperado:** Administrador recupera acceso mediante enrolamiento nuevo después de pérdida total simulada; no se borra inventario ni se reactivan sesiones; ninguna ruta remota permite eludir factor.

**Dependencias del resultado:** F-03, F-04, F-07.

**Fuentes:** [docs/PLAN-F0904-ENSAYO-PERDIDA-MFA.md](../docs/PLAN-F0904-ENSAYO-PERDIDA-MFA.md) · [docs/PASO-032-ENSAYO-PERDIDA-MFA.md](../docs/PASO-032-ENSAYO-PERDIDA-MFA.md) · [evidence/s1-20261111/f09-04-ensayo-perdida/RESULTADOS.md](../evidence/s1-20261111/f09-04-ensayo-perdida/RESULTADOS.md) · [evidence/s1-20261111/f09-04-ensayo-perdida/MATRIZ-CRITERIO.md](../evidence/s1-20261111/f09-04-ensayo-perdida/MATRIZ-CRITERIO.md) · [evidence/s1-20261111/f09-04-ensayo-perdida/NATIVO.json](../evidence/s1-20261111/f09-04-ensayo-perdida/NATIVO.json) · [evidence/s1-20261111/f09-04-ensayo-perdida/FUENTES.json](../evidence/s1-20261111/f09-04-ensayo-perdida/FUENTES.json) · [evidence/s1-20261111/f09-04-ensayo-perdida/FOCOS.json](../evidence/s1-20261111/f09-04-ensayo-perdida/FOCOS.json) · [evidence/s1-20261111/f09-04-ensayo-perdida/CAMBIOS.patch](../evidence/s1-20261111/f09-04-ensayo-perdida/CAMBIOS.patch) · [evidence/s1-20261111/f09-04-ensayo-perdida/INVESTIGACION-NATIVA.md](../evidence/s1-20261111/f09-04-ensayo-perdida/INVESTIGACION-NATIVA.md) · [evidence/s1-20261111/f09-04-ensayo-perdida/review/DICTAMEN.md](../evidence/s1-20261111/f09-04-ensayo-perdida/review/DICTAMEN.md) · [docs/PLAN-F0901-AUTORIZACION-EMERGENCIA.md](../docs/PLAN-F0901-AUTORIZACION-EMERGENCIA.md) · [docs/PASO-029-AUTORIZACION-LOCAL-EMERGENCIA-MFA.md](../docs/PASO-029-AUTORIZACION-LOCAL-EMERGENCIA-MFA.md) · [evidence/s1-20261111/f09-01-autorizacion-local/RESULTADOS.md](../evidence/s1-20261111/f09-01-autorizacion-local/RESULTADOS.md) · [evidence/s1-20261111/f09-01-autorizacion-local/MATRIZ-CRITERIO.md](../evidence/s1-20261111/f09-01-autorizacion-local/MATRIZ-CRITERIO.md) · [evidence/s1-20261111/f09-01-autorizacion-local/FUENTES.json](../evidence/s1-20261111/f09-01-autorizacion-local/FUENTES.json) · [evidence/s1-20261111/f09-01-autorizacion-local/FOCOS.json](../evidence/s1-20261111/f09-01-autorizacion-local/FOCOS.json) · [evidence/s1-20261111/f09-01-autorizacion-local/MUTACION.json](../evidence/s1-20261111/f09-01-autorizacion-local/MUTACION.json) · [evidence/s1-20261111/f09-01-autorizacion-local/CAMBIOS.patch](../evidence/s1-20261111/f09-01-autorizacion-local/CAMBIOS.patch) · [evidence/s1-20261111/f09-01-autorizacion-local/review/DICTAMEN.md](../evidence/s1-20261111/f09-01-autorizacion-local/review/DICTAMEN.md) · [docs/PLAN-F0902-MATERIAL-PERDIDA-MFA.md](../docs/PLAN-F0902-MATERIAL-PERDIDA-MFA.md) · [docs/PASO-030-MATERIAL-PERDIDA-MFA.md](../docs/PASO-030-MATERIAL-PERDIDA-MFA.md) · [evidence/s1-20261111/f09-02-material-perdida/RESULTADOS.md](../evidence/s1-20261111/f09-02-material-perdida/RESULTADOS.md) · [evidence/s1-20261111/f09-02-material-perdida/MATRIZ-CRITERIO.md](../evidence/s1-20261111/f09-02-material-perdida/MATRIZ-CRITERIO.md) · [evidence/s1-20261111/f09-02-material-perdida/FUENTES.json](../evidence/s1-20261111/f09-02-material-perdida/FUENTES.json) · [evidence/s1-20261111/f09-02-material-perdida/FOCOS.json](../evidence/s1-20261111/f09-02-material-perdida/FOCOS.json) · [evidence/s1-20261111/f09-02-material-perdida/MUTACION.json](../evidence/s1-20261111/f09-02-material-perdida/MUTACION.json) · [evidence/s1-20261111/f09-02-material-perdida/CAMBIOS.patch](../evidence/s1-20261111/f09-02-material-perdida/CAMBIOS.patch) · [evidence/s1-20261111/f09-02-material-perdida/review/DICTAMEN.md](../evidence/s1-20261111/f09-02-material-perdida/review/DICTAMEN.md) · [docs/PLAN-F0903-REVOCACION-AUDITORIA-MFA.md](../docs/PLAN-F0903-REVOCACION-AUDITORIA-MFA.md) · [docs/PASO-031-REVOCACION-Y-AUDITORIA-MFA.md](../docs/PASO-031-REVOCACION-Y-AUDITORIA-MFA.md) · [evidence/s1-20261111/f09-03-revocacion-auditoria/RESULTADOS.md](../evidence/s1-20261111/f09-03-revocacion-auditoria/RESULTADOS.md) · [evidence/s1-20261111/f09-03-revocacion-auditoria/MATRIZ-CRITERIO.md](../evidence/s1-20261111/f09-03-revocacion-auditoria/MATRIZ-CRITERIO.md) · [evidence/s1-20261111/f09-03-revocacion-auditoria/FUENTES.json](../evidence/s1-20261111/f09-03-revocacion-auditoria/FUENTES.json) · [evidence/s1-20261111/f09-03-revocacion-auditoria/FOCOS.json](../evidence/s1-20261111/f09-03-revocacion-auditoria/FOCOS.json) · [evidence/s1-20261111/f09-03-revocacion-auditoria/CAMBIOS.patch](../evidence/s1-20261111/f09-03-revocacion-auditoria/CAMBIOS.patch) · [evidence/s1-20261111/f09-03-revocacion-auditoria/review/DICTAMEN.md](../evidence/s1-20261111/f09-03-revocacion-auditoria/review/DICTAMEN.md).

#### Paso 029 · F-09.01

F-09.01 técnico: nueva compuerta CLI --mfa-emergency-recovery antes de host/config/SQL, autoridad de token Windows real SYSTEM o Administradores elevados; impersonación, token estándar/filtrado/no consultable y autoridad falsa por claims/env no autorizan. Incluso autorizado devuelve transition_unavailable/exit1/0 operaciones/ninguna sesión hasta F-09.02/.03. Program es el único archivo previo modificado; helper y tres tests nuevos,226 fuentes previas conservadas. Rojo10 fallos por rama ausente, final76/76, HTTP3/3 y regresión74+7 PASS sin omitidas, mutación detectada por 5 fallos; revisor79/79 y 8 sondas propias PASS. Positivos SYSTEM/elevado reales no ejecutados; política simulada separada de token nativo estándar. Sin GUI/SQL/dependencias/instaladores/VM o cambios D/E. F-09.02–.05 y los seis hitos completos pendientes. Observación Edge de F0805 sigue abierta.

- Tipo de trabajo: Compuerta local revisada; transición de pérdida total, integración y aceptación pendientes.
- Estado formal: done; ámbito: Primera entrega; responsable: F-09.
- Texto histórico trazable: Autorizar sólo operador local SYSTEM/Administradores; sin web anónima ni bypass password-only.
- Número conservado tras el cierre: no repetir como nueva implementación.

#### Paso 030 · F-09.02

F-09.01/.02 técnicos: autoridad Windows y protocolo interno Prepare/Export/Apply/Publish para pérdida explícita con censo fiable. Conserva claves legibles/blobs opacos y archivo cifrado completo privado; retira factores perdidos, fuerza required/pending, preserva cuentas/permisos/gracia45 e inventario. Sobre autenticado y pin privado inmutable; witness completamente vinculado, rollback/reentrada y publicación verificada con fence retenido. SQL047 aditiva,224 fuentes previas conservadas/4 modificadas/4 nuevas,2 tests nuevos. Regresión144/144 PASS sin omitidas y revisión independiente acotada. CLI no habilitada (transition_unavailable tras autorización)/0 operaciones; no instalador47, servicio recuperado ni positivo elevado/SID real. D/E intactos. F-09.03–.05 y seis hitos completos pendientes; observación Edge F0805 abierta.

- Tipo de trabajo: Material/transición interna revisados con fence; composición operativa, servicio real y aceptación pendientes.
- Estado formal: done; ámbito: Primera entrega; responsable: F-09.
- Texto histórico trazable: Permitir preparar anillo nuevo explícitamente, conservar material anterior recuperable, retirar factores ilegibles del uso y marcar enrolamiento pendiente sin borrar DB.
- Número conservado tras el cierre: no repetir como nueva implementación.

#### Paso 031 · F-09.03

F-09.01–.03 técnicos: loss-reset reutilizado, revocación real de credenciales anteriores y auditoría Windows dedicada sin secretos; no appactor inventado. Corregida primera aplicación: recuentos archivo/pending/finish y testigo fresh/hashes antes de commit, con rollback de resultados SQL incompletos. Rojo limpio14=5PASS/9FAIL→verde14/14; final52/52 sin omitidas. Único global conserva identidad/permisos/gracia y recupera administración sólo tras TOTP nuevo; last_admin_required vigente. Revisión independiente acotada y registrada.231/232 fuentes previas conservadas,1 adaptador DB corregido,1 test nuevo; SQL047/Program/dependencias/GUI intactos. Fence conservado, CLI aún no operativa; sin cambio D/E. F-09.04/.05 y seis hitos completos pendientes; observación Edge F0805 abierta.

- Tipo de trabajo: Revocación/auditoría y último global revisados en backend; composición y ensayo operativo de pérdida siguen pendientes.
- Estado formal: done; ámbito: Primera entrega; responsable: F-09.
- Texto histórico trazable: Revocar sesiones/desafíos y registrar auditoría sin secretos, preservando recuperación de último administrador.
- Número conservado tras el cierre: no repetir como nueva implementación.

#### Paso 032 · F-09.04

Ensayar pérdida simulada total, arranque fallido explícito, recuperación local y vuelta mediante enrolamiento restringido.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: done; ámbito: Primera entrega; responsable: F-09.
- Número conservado tras el cierre: no repetir como nueva implementación.

#### Paso 033 · F-09.05

Cerrar «Implementar recuperación local cuando no quedan clave, sobre ni códigos» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: F-09.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### F-10 · Cerrar política y administración MFA conforme a gracia45

**Situación conocida:** El panel propio/por usuario y la política45 ya se implementaron. La regla vigente es45 días, cuentas existentes desde activación y exención del administrador global Systemhaus; administradores de cliente no están exentos. El resumen y dos criterios congelados del ledger contienen redacción anterior: conciliarlos formalmente antes de acreditar F-10, sin reabrir una decisión de Wascar.

**Cierre esperado:** Panel y servidor aplican gracia45 a usuarios/técnicos/administradores de cliente, fecha de activación para existentes y exención del administrador global; protegen sesiones, reautenticación, métodos ajenos y recuperación/último administrador, con negativos y revisión independiente.

**Dependencias del resultado:** F-07, F-08, F-09, F-11.

**Fuentes:** [docs/DECISION-MFA-GRACIA-45-DIAS-29-10-2026.md](../docs/DECISION-MFA-GRACIA-45-DIAS-29-10-2026.md) · [docs/MFA-DASHBOARD-GRACIA-45-29-10-2026.md](../docs/MFA-DASHBOARD-GRACIA-45-29-10-2026.md).

#### Paso 034 · F-10.01

Conciliar API/panel MFA existentes con activacion/desactivacion/reset, revision, auditoria y ultimo administrador; corregir solo huecos comprobados.

- Tipo de trabajo: Conciliar evidencia existente.
- Estado formal: pending; ámbito: Primera entrega; responsable: F-10.
- Texto histórico trazable: Implementar API/panel de activar/desactivar y reset MFA con capacidad global vigente, revisión/idempotencia, auditoría y protección del último administrador.

#### Paso 035 · F-10.02

Contrastar revocacion, concesiones, cambios concurrentes y rollback sobre la política de 45 días existente; reutilizar los recorridos ya probados.

- Tipo de trabajo: Conciliar evidencia existente.
- Estado formal: pending; ámbito: Primera entrega; responsable: F-10.
- Texto histórico trazable: Cambios revocan sesiones/desafíos y no permiten elevar una sesión password-only tras nueva concesión; probar cambios concurrentes y rollback.

#### Paso 036 · F-10.03

Conciliar formalmente el criterio historico: cuentas nuevas cuentan 45 días desde creacion; existentes desde activacion de politica. No reiniciar el plazo al desactivar.

- Tipo de trabajo: Conciliar criterio historico.
- Estado formal: pending; ámbito: Primera entrega; responsable: F-10.
- Texto histórico trazable: Concretar transición de cuentas existentes y altas nuevas; registrar cómo se elimina excepción D7.
- Conciliación formal requerida antes de acreditar: prevalece la decisión vigente, no el criterio histórico incompatible.

#### Paso 037 · F-10.04

Conciliar y verificar politica vigente: 45 días para usuarios/tecnicos/admin de cliente; exencion solo del global Systemhaus con ambas capacidades. No imponer MFA inmediato universal.

- Tipo de trabajo: Conciliar criterio historico.
- Estado formal: pending; ámbito: Primera entrega; responsable: F-10.
- Texto histórico trazable: Antes de producción aplicar MFA a todos, incluidos lector/admin, revocar password-only y comprobar que no hay alternativa de login inseguro.
- Conciliación formal requerida antes de acreditar: prevalece la decisión vigente, no el criterio histórico incompatible.

#### Paso 038 · F-10.05

Cerrar «Cerrar política y administración MFA conforme a gracia45» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: F-10.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### F-11 · Integrar segundo paso y todos los formularios de reautenticación

**Situación conocida:** El coordinador actual ya gestiona login con desafío 202, enrolamiento, verificación TOTP y canje limitado de códigos. Panel y login MFA se probaron en navegador; D11 confirmó el proveedor Windows real y el flujo TOTP por HTTPS. Falta completar la reautenticación por familia de operación sensible y la persistencia de intenciones inciertas al navegar o recargar; no rehacer el login ni afirmar que la GUI carece de MFA.

**Cierre esperado:** Login y cada familia de reauth completan factor para mismo actor, conservan borrador y recuperan respuesta sin duplicar; navegador/ENDEES revisados antes de habilitar QA.

**Dependencias del resultado:** F-07, F-08, F-10.

**Fuentes:** [docs/MFA-DASHBOARD-GRACIA-45-29-10-2026.md](../docs/MFA-DASHBOARD-GRACIA-45-29-10-2026.md) · [docs/PUNTO3-FUNCIONES-PENDIENTES.md](../docs/PUNTO3-FUNCIONES-PENDIENTES.md) · [evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md](../evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md) · [evidence/s1-20261102/punto3/RESULTADOS.md](../evidence/s1-20261102/punto3/RESULTADOS.md) · [evidence/s1-20261102/vm11-d/RESULTADOS.md](../evidence/s1-20261102/vm11-d/RESULTADOS.md).

#### Paso 039 · F-11.01

Conciliar el coordinador de login/enrolamiento/verificacion/codigos ya integrado; cerrar la combinacion final sin entregar Session antes del factor exigible.

- Tipo de trabajo: Conciliar evidencia existente.
- Estado formal: pending; ámbito: Primera entrega; responsable: F-11.
- Texto histórico trazable: Coordinador de autenticación termina login/enrolamiento/verificación/recuperación antes de entregar Session al resto de la GUI.

#### Paso 040 · F-11.02

Integrar reauth de operaciones inciertas, usuarios/password/estado/sesiones, favoritos, plantillas, preferencias y paletas; continuar sólo mismo actor.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: F-11.

#### Paso 041 · F-11.03

Conservar borradores/journal/intención y no reenviar escritura bajo otra identidad; tratar pérdida de respuesta, caducidad/recarga y segunda sesión.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: F-11.

#### Paso 042 · F-11.04

Mantener aspecto RC9 y EN/DE/ES; catálogo con pasos exactos y estado no disponible hasta integración real, regenerar guía cuando corresponda sin alterar observaciones.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: F-11.

#### Paso 043 · F-11.05

Cerrar «Integrar segundo paso y todos los formularios de reautenticación» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: F-11.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### F-12 · Acreditar MFA y fundamento sobre la candidata completa por HTTP/HTTPS

**Situación conocida:** Candidata43 y D11 identificadas: servicio/HTTPS/DPAPI reales; TOTP del cargador corregido probado con cuenta sintetica y permiso global denegado. Completar matriz de seguridad/codigos/recuperacion/reauth; no anunciar ausencia de proveedor o deshabilitar lo ya probado por Wascar.

**Cierre esperado:** Evidencia identifica bytes/esquema/proveedor/entorno y demuestra flujos positivos/negativos MFA completos más controles afectados; ninguna omisión pasa por éxito, sin anunciar QA/producción por pruebas del almacén.

**Dependencias del resultado:** F-04 para producción; proveedor sintético permite ensayo previo, F-07, F-08, F-09, F-10, F-11, C4/C5: corregir y ensayar cadena de instalador/runtime.

**Fuentes:** [evidence/s1-20261102/vm11-d/RESULTADOS.md](../evidence/s1-20261102/vm11-d/RESULTADOS.md) · [evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md](../evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md) · [docs/REVISION-MFA-L1-RONDA2-CODEX-25-10-2026.md](../docs/REVISION-MFA-L1-RONDA2-CODEX-25-10-2026.md) · [evidence/s1-20261025/mfa-l1-ronda2-codex/CIERRE.md](../evidence/s1-20261025/mfa-l1-ronda2-codex/CIERRE.md) · [evidence/s1-20261025/mfa-l1-ronda2-codex/REVISION-SEGURIDAD.md](../evidence/s1-20261025/mfa-l1-ronda2-codex/REVISION-SEGURIDAD.md) · [evidence/s1-20261025/mfa-l1-ronda2-codex/RESULTADO-REGRESION-ORIGINAL.json](../evidence/s1-20261025/mfa-l1-ronda2-codex/RESULTADO-REGRESION-ORIGINAL.json) · [evidence/s1-20261025/mfa-l1-ronda2-codex/RESULTADO-RUNTIME-Y-CLI.json](../evidence/s1-20261025/mfa-l1-ronda2-codex/RESULTADO-RUNTIME-Y-CLI.json).

#### Paso 044 · F-12.01

Fijar la candidata final reutilizando 43/11 y la separacion ya existente entre proveedor sintetico y real. Custodia D2 confirmada: no reabrir esa decision.

- Tipo de trabajo: Conciliar evidencia existente.
- Estado formal: in_progress; ámbito: Primera entrega; responsable: F-12.
- Texto histórico trazable: Fijar conjunto aplicación/SQL/frontend/dependencias/operadores y un proveedor de laboratorio controlado explícitamente separado de custodia productiva D2; no bloquear pruebas sintéticas por decisión de custodia aún abierta.

#### Paso 045 · F-12.02

Comprobar por HTTP desafío202 sin sesión, finalidad/rutas exactas, CSRF/Origin/rate/cookies, intentos/replay/concurrencia/caducidad tras última espera y reset/política/restore.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: in_progress; ámbito: Primera entrega; responsable: F-12.

#### Paso 046 · F-12.03

Completar la matriz HTTPS/MFA final reutilizando pruebas reales de D11 y de la cuenta sintetica; no trasladar cobertura por parecido de DLL.

- Tipo de trabajo: Conciliar evidencia existente.
- Estado formal: pending; ámbito: Primera entrega; responsable: F-12.
- Texto histórico trazable: Con proveedor real final comprobar HTTPS/Secure en navegador y regresión afectada después de MFA, sin trasladar pruebas por similitud de DLL.

#### Paso 047 · F-12.04

Revisión final acotada por rutas: SQL externo parametrizado/identificadores cerrados, datos hostiles literales DOM/SVG/reportes, autorización lectura/escritura, secretos y roles runtime DML sin DDL. SAST complementa, no sustituye pruebas negativas.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: F-12.

#### Paso 048 · F-12.05

Conciliar guiones y revision de la candidata actual: MFA ya fue integrado/probado en D; no tratarlo como inexistente ni volver a deshabilitarlo para este plan.

- Tipo de trabajo: Conciliar evidencia existente.
- Estado formal: pending; ámbito: Primera entrega; responsable: F-12.
- Texto histórico trazable: Actualizar guiones/evidencias de candidata y obtener revisión independiente antes de habilitar MFA en QA.

## I · Jerarquía, inventario y colaboración

### I-01 · Ofrecer e integrar Deshacer de crecimiento/reducción pura de grupos

**Situación conocida:** I-01.01/02/03/04 completos técnicamente en laboratorio. Consulta, reintento y cancelación originales; invalidación por revisión, permiso, cuenta y cliente con vías de diálogo/edición rápida protegidas. Ensayo READ sin EDIT con Edge/PostgreSQL 17.11 PASS 21,83 s y revisión distinta de la matriz acumulada. I-01.05/06/07 pendientes: candidata coordinada, QA disponible y cierre del resultado completo.

**Cierre esperado:** Ambas inversas puras funcionan en GUI con UUID/atributos/fechas/extremos exactos; conflictos/revocación/replay/rollback sin pérdida ni éxito falso; build/hash, prueba, revisión distinta y QA registrados.

**Dependencias del resultado:** Candidata14/MFA estable coordinada.

**Fuentes:** [docs/C2-EVIDENCIA-GRUPOS-25-10-2026.md](../docs/C2-EVIDENCIA-GRUPOS-25-10-2026.md) · [docs/C2-INVERSA-CRECIMIENTO-25-10-2026.md](../docs/C2-INVERSA-CRECIMIENTO-25-10-2026.md) · [docs/C2-INVERSA-REDUCCION-25-10-2026.md](../docs/C2-INVERSA-REDUCCION-25-10-2026.md) · [evidence/s1-20261025/c2-inversa-reduccion-codex/CIERRE.md](../evidence/s1-20261025/c2-inversa-reduccion-codex/CIERRE.md) · [development/frontend/src/InventoryPanel.jsx](../development/frontend/src/InventoryPanel.jsx) · [docs/C2-GUI-GRUPOS-25-10-2026.md](../docs/C2-GUI-GRUPOS-25-10-2026.md) · [evidence/s1-20261025/c2-gui-grupos-codex/CIERRE.md](../evidence/s1-20261025/c2-gui-grupos-codex/CIERRE.md) · [evidence/s1-20261025/c2-gui-grupos-codex/REVISION.md](../evidence/s1-20261025/c2-gui-grupos-codex/REVISION.md) · [docs/C2-CONSULTA-PENDIENTE-25-10-2026.md](../docs/C2-CONSULTA-PENDIENTE-25-10-2026.md) · [evidence/s1-20261025/c2-query-codex/CIERRE.md](../evidence/s1-20261025/c2-query-codex/CIERRE.md) · [evidence/s1-20261025/c2-query-codex/REVISION.md](../evidence/s1-20261025/c2-query-codex/REVISION.md) · [docs/C2-CONTEXTO-OPERACION-25-10-2026.md](../docs/C2-CONTEXTO-OPERACION-25-10-2026.md) · [evidence/s1-20261025/c2-context-codex/CIERRE.md](../evidence/s1-20261025/c2-context-codex/CIERRE.md) · [evidence/s1-20261025/c2-context-codex/REVISION.md](../evidence/s1-20261025/c2-context-codex/REVISION.md) · [docs/C2-REVISION-PERMISOS-25-10-2026.md](../docs/C2-REVISION-PERMISOS-25-10-2026.md) · [evidence/s1-20261025/c2-eligibility-codex/CIERRE.md](../evidence/s1-20261025/c2-eligibility-codex/CIERRE.md) · [evidence/s1-20261025/c2-eligibility-codex/REVISION.md](../evidence/s1-20261025/c2-eligibility-codex/REVISION.md) · [docs/C2-EDICIONES-RAPIDAS-25-10-2026.md](../docs/C2-EDICIONES-RAPIDAS-25-10-2026.md) · [evidence/s1-20261025/c2-instant-codex/CIERRE.md](../evidence/s1-20261025/c2-instant-codex/CIERRE.md) · [evidence/s1-20261025/c2-instant-codex/REVISION.md](../evidence/s1-20261025/c2-instant-codex/REVISION.md) · [docs/C2-MATRIZ-RECUPERACION-25-10-2026.md](../docs/C2-MATRIZ-RECUPERACION-25-10-2026.md) · [evidence/s1-20261025/c2-permission-codex/CIERRE.md](../evidence/s1-20261025/c2-permission-codex/CIERRE.md) · [evidence/s1-20261025/c2-permission-codex/EDGE-PG.json](../evidence/s1-20261025/c2-permission-codex/EDGE-PG.json) · [evidence/s1-20261025/c2-permission-codex/REVISION-I0103.md](../evidence/s1-20261025/c2-permission-codex/REVISION-I0103.md).

#### Paso 049 · I-01.05

Congelar candidata coordinada con MFA/instalación y probar API+GUI sobre sus bytes; revisión distinta.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-01.

#### Paso 050 · I-01.06

Añadir guiones por botón/campo, habilitados sólo en candidata seleccionada real; conservar resultados.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-01.

#### Paso 051 · I-01.07

Cerrar «Ofrecer e integrar Deshacer de crecimiento/reducción pura de grupos» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-01.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### I-02 · Cerrar alcance restante de compensación colaborativa y Rehacer

**Situación conocida:** implementacion: Existen atributos seis campos/aliasRJ45 y API puras de grupos. No undo general/redo; mixtos/reordenamientos, roles/properties, mover/borrar/conexiones carecen de inversa general.; integracion: Atributos integrados históricamente; puras fuera de 14.; prueba: Rechazos seguros y pruebas acotadas no cumplen inversas faltantes.; revision: Sin revisión de catálogo completo de compensaciones.; qa: QA36/59 atributos; no aceptación del contrato general.

**Cierre esperado:** Tabla completa soportado/no soportado y motivo; toda inversa prometida tiene prueba de cambios ajenos y QA; un rechazo422 nunca se cuenta como undo cumplido.

**Dependencias del resultado:** I-01, Decisión expresa si se propone limitar Undo/Redo.

**Fuentes:** [docs/CONTRATO-SERVIDOR-v0.1.md](../docs/CONTRATO-SERVIDOR-v0.1.md) · [docs/C2-CONCILIACION-INVENTARIO.md](../docs/C2-CONCILIACION-INVENTARIO.md) · [docs/API-COMPENSACION-POE-S1.md](../docs/API-COMPENSACION-POE-S1.md) · [docs/C2-INVERSA-REDUCCION-25-10-2026.md](../docs/C2-INVERSA-REDUCCION-25-10-2026.md).

#### Paso 052 · I-02.01

Fijar catálogo finito y semántica de Rehacer; no copiar historial offline30 niveles ni suponer cualquier inversa de cualquier comando.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-02.
- Texto histórico trazable: Fijar catálogo finito y semántica de Rehacer; no copiar historial offline30niveles ni suponer cualquier inversa de cualquier comando.

#### Paso 053 · I-02.02

Definir evidencia/consentimiento nuevo para grupos mixtos/reordenados y extremos reservados hoy rechazados.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-02.

#### Paso 054 · I-02.03

Por cada inversa incluida: comparar after completo/estado actual, identidad, revisión, autorización y locks; no UPSERT ni desplazar cables actuales.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-02.

#### Paso 055 · I-02.04

Implementar alcance contractual pendiente. Un recorte requiere decisión expresa de Wascar.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-02.

#### Paso 056 · I-02.05

Probar cambios ajenos, reutilización UUID, evidencia corrupta, concurrencia/replay/rollback; integrar GUI/manual y revisión distinta.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-02.

#### Paso 057 · I-02.06

Cerrar «Cerrar alcance restante de compensación colaborativa y Rehacer» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-02.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### I-03 · Cerrar matriz RC9 de conector, cara, rol eléctrico y presupuesto PoE

**Situación conocida:** implementacion: UUID/grupo/tipo, PoE OFF/null≠0, cara única, roles AC y resumen agregado ya existen. Pair no exige igualdad universal de familias de datos ni presupuesto agregado.; integracion: Integradas históricamente QA13; combinación14 final sin acreditar.; prueba: 54-C/23.10 casos concretos;63–68 resumen. Sin matriz completa de presets/conectores/caras/roles.; revision: Favorable acotada; no matriz integral.; qa: QA27/35/59; S-23 visual parcial.

**Cierre esperado:** Matriz finita sin huecos para combinaciones prometidas, ligada a evidencia o límite explícito; identidad/cables persisten. No certificación de circuito/medio/transceptor/suministro.

**Dependencias del resultado:** Referencia RC9 inmutable, Candidata integrada.

**Fuentes:** [docs/C2-CONCILIACION-INVENTARIO.md](../docs/C2-CONCILIACION-INVENTARIO.md) · [docs/CONTRATO-INVENTARIO-S1.md](../docs/CONTRATO-INVENTARIO-S1.md) · [evidence/s1-20261017/tres-tandas-54/CIERRE.md](../evidence/s1-20261017/tres-tandas-54/CIERRE.md) · [evidence/s1-20261017/seis-tandas-63-68/CIERRE.md](../evidence/s1-20261017/seis-tandas-63-68/CIERRE.md).

#### Paso 058 · I-03.01

Enumerar combinaciones realmente soportadas por RC9 adoptada: tipo/grupo, auto/front/rear, inlet/outlet/unspecified y presets.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-03.
- Texto histórico trazable: Enumerar combinaciones realmente soportadas por RC9adoptada: tipo/grupo, auto/front/rear, inlet/outlet/unspecified y presets.

#### Paso 059 · I-03.02

Marcar soporte/rechazo/límite; no imponer compatibilidad física nueva por intuición.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-03.

#### Paso 060 · I-03.03

Cubrir grupos gn repetidos, conservación al editar y revalidación de enlaces al cambiar rol.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-03.

#### Paso 061 · I-03.04

Presupuesto nulo/cero/límite/excedido y watts heterogéneos/desconocidos, OFF/AC excluidos. No nueva restricción de suministro sin contrato.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-03.

#### Paso 062 · I-03.05

Recorrido frontal/trasera persistente sobre candidata final, errores atómicos y revisión distinta.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-03.

#### Paso 063 · I-03.06

Cerrar «Cerrar matriz RC9 de conector, cara, rol eléctrico y presupuesto PoE» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-03.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### I-04 · Cerrar variantes de jerarquía, racks, equipos y orden ya implementados

**Situación conocida:** I-04.01–05 completos técnicamente en laboratorio. Borrado individual de final conectado y lote Dose+equipo: cinco conjuntos de impacto exactos, cancelaciones SQL/operaciones/auditoría intactas, dos commits y cable ajeno conservado. Regresión de lote, permisos/replay/conflicto y persistencia comprobados. I-04.06/07 pendientes: candidata final integrada, revisión y aceptación.

**Cierre esperado:** Cada operación ofrecida tiene trayectoria positiva/negativos pertinentes por versión; huecos de evidencia cerrados sin declarar funciones inexistentes; QA visible de Wascar.

**Dependencias del resultado:** I-06, Candidata estable.

**Fuentes:** [docs/MATRIZ-INVENTARIO-PENDIENTE.md](../docs/MATRIZ-INVENTARIO-PENDIENTE.md) · [evidence/s1-20261017/tres-tandas-52/CIERRE.md](../evidence/s1-20261017/tres-tandas-52/CIERRE.md) · [evidence/s1-20261017/tres-tandas-53/CIERRE.md](../evidence/s1-20261017/tres-tandas-53/CIERRE.md) · [evidence/s1-20261017/quince-tandas-55-59/CIERRE.md](../evidence/s1-20261017/quince-tandas-55-59/CIERRE.md) · [evidence/s1-20261017/tres-tandas-61/CIERRE.md](../evidence/s1-20261017/tres-tandas-61/CIERRE.md) · [docs/C2-CATALOGO-JERARQUIA-25-10-2026.md](../docs/C2-CATALOGO-JERARQUIA-25-10-2026.md) · [evidence/s1-20261025/c2-catalogue-codex/CIERRE.md](../evidence/s1-20261025/c2-catalogue-codex/CIERRE.md) · [evidence/s1-20261025/c2-catalogue-codex/CATALOGO.json](../evidence/s1-20261025/c2-catalogue-codex/CATALOGO.json) · [evidence/s1-20261025/c2-catalogue-codex/REVISION-I0401.md](../evidence/s1-20261025/c2-catalogue-codex/REVISION-I0401.md) · [docs/C2-PERMISOS-BORRADO-25-10-2026.md](../docs/C2-PERMISOS-BORRADO-25-10-2026.md) · [evidence/s1-20261025/c2-delete-permission-codex/CIERRE.md](../evidence/s1-20261025/c2-delete-permission-codex/CIERRE.md) · [evidence/s1-20261025/c2-delete-permission-codex/REVISION.md](../evidence/s1-20261025/c2-delete-permission-codex/REVISION.md) · [evidence/s1-20261025/c2-delete-permission-codex/EDGE-PG.json](../evidence/s1-20261025/c2-delete-permission-codex/EDGE-PG.json) · [docs/C2-NOMBRES-DESTINOS-RACK-25-10-2026.md](../docs/C2-NOMBRES-DESTINOS-RACK-25-10-2026.md) · [evidence/s1-20261025/c2-rack-variants-codex/CIERRE.md](../evidence/s1-20261025/c2-rack-variants-codex/CIERRE.md) · [evidence/s1-20261025/c2-rack-variants-codex/EDGE-PG.json](../evidence/s1-20261025/c2-rack-variants-codex/EDGE-PG.json) · [evidence/s1-20261025/c2-rack-variants-codex/REVISION.md](../evidence/s1-20261025/c2-rack-variants-codex/REVISION.md) · [docs/C2-DUPLICADO-VARIANTES-25-10-2026.md](../docs/C2-DUPLICADO-VARIANTES-25-10-2026.md) · [evidence/s1-20261025/c2-duplicate-variants-codex/CIERRE.md](../evidence/s1-20261025/c2-duplicate-variants-codex/CIERRE.md) · [evidence/s1-20261025/c2-duplicate-variants-codex/EDGE-PG-VARIANTES.json](../evidence/s1-20261025/c2-duplicate-variants-codex/EDGE-PG-VARIANTES.json) · [evidence/s1-20261025/c2-duplicate-variants-codex/REGRESION-EXISTENTE.json](../evidence/s1-20261025/c2-duplicate-variants-codex/REGRESION-EXISTENTE.json) · [evidence/s1-20261025/c2-duplicate-variants-codex/REVISION.md](../evidence/s1-20261025/c2-duplicate-variants-codex/REVISION.md) · [docs/C2-ORDEN-TACTIL-25-10-2026.md](../docs/C2-ORDEN-TACTIL-25-10-2026.md) · [evidence/s1-20261025/c2-order-variants-codex/CIERRE.md](../evidence/s1-20261025/c2-order-variants-codex/CIERRE.md) · [evidence/s1-20261025/c2-order-variants-codex/REVISION.md](../evidence/s1-20261025/c2-order-variants-codex/REVISION.md) · [docs/C2-BORRADO-IMPACTO-25-10-2026.md](../docs/C2-BORRADO-IMPACTO-25-10-2026.md) · [evidence/s1-20261025/c2-delete-impact-codex/CIERRE.md](../evidence/s1-20261025/c2-delete-impact-codex/CIERRE.md) · [evidence/s1-20261025/c2-delete-impact-codex/REVISION.md](../evidence/s1-20261025/c2-delete-impact-codex/REVISION.md).

#### Paso 064 · I-04.06

Repetir sólo focos afectados en candidata final con segunda cuenta/reinicio; revisión y guiones faltantes.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-04.

#### Paso 065 · I-04.07

Cerrar «Cerrar variantes de jerarquía, racks, equipos y orden ya implementados» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-04.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### I-05 · Cerrar variantes de Click-Click, lotes, reconexión y cables

**Situación conocida:** implementacion: Todas las familias existen, incluida GUI57 de pares atómicos y cinco patch/nota/color/desconexión58.; integracion: Históricamente QA29/30; combinación14 no probada por esas ejecuciones.; prueba: PG competencia/uncommit/ámbitos; GUI incertidumbre/reserved/412 y edición. No matriz visual completa cross/roles/carreras/reconexión reservada/cancelar.; revision: Acotada y con atribución de recorridos realmente repetidos.; qa: Casos disponibles históricos no equivalen a aprobación.

**Cierre esperado:** Todas las variantes prometidas conservan extremos/identidad/atributos, atomicidad y Click-Click; pruebas/revisión y QA visibles vinculados a versión.

**Dependencias del resultado:** I-03, P-10, Candidata final.

**Fuentes:** [docs/GUI-LOTE-CONEXIONES-57.md](../docs/GUI-LOTE-CONEXIONES-57.md) · [docs/QA-CONEXIONES-EDICION-58.md](../docs/QA-CONEXIONES-EDICION-58.md) · [evidence/s1-20260928/impacto-reconexion-04/CIERRE.md](../evidence/s1-20260928/impacto-reconexion-04/CIERRE.md) · [evidence/s1-20261017/quince-tandas-55-59/CIERRE.md](../evidence/s1-20261017/quince-tandas-55-59/CIERRE.md).

#### Paso 066 · I-05.01

Matriz local/cross/sala y reserved positivo/negativo con origen revalidado.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-05.

#### Paso 067 · I-05.02

Reconexión cancelada y a ocupado/disabled/faulty/reserved/ajeno conserva UUID/atributos/extremo previo.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-05.

#### Paso 068 · I-05.03

Dos técnicos en GUI: un éxito y conflicto explicado sin borrador perdido; aprovechar prueba API existente.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-05.

#### Paso 069 · I-05.04

Precedencia color manual y literalidad de notas/labels en UI e informes EN/DE/ES.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-05.

#### Paso 070 · I-05.05

Corregir sólo fallos reproducidos y registrar build/pruebas/revisión/QA.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-05.

#### Paso 071 · I-05.06

Cerrar «Cerrar variantes de Click-Click, lotes, reconexión y cables» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-05.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### I-06 · Completar verificación de Dosen y finales ya soportados en sala

**Situación conocida:** I-06.02 cerrado técnicamente: Edge/PG17.11 PASS32,719 s,16 commits para todos los campos ofrecidos en Dose/final, roles power en puertos sin cable, gn repetido por grupo/ID, metadatos/cables exactos,7 rechazos atómicos y persistencia. Regresión edición nueva PASS27,562 s. Revisión distinta3 focos/13 mutaciones. Borrado individual/conjunto con impacto aceptado en I-04.05, evidencia anterior identificada. No completa soporte/plantillas/AP, rutas/informes/revocación, ocupación lógica, integración o QA de I-06.

**Cierre esperado:** Operaciones externas de Dose/final probadas como objetos de sala con topología/ámbitos exactos y QA; cualquier aplazamiento tiene decisión expresa.

**Dependencias del resultado:** I-03, I-04, I-05, P-06/P-07.

**Fuentes:** [docs/CONTRATO-INVENTARIO-S1.md](../docs/CONTRATO-INVENTARIO-S1.md) · [docs/GUI-TRASLADO-SALA-S1.md](../docs/GUI-TRASLADO-SALA-S1.md) · [evidence/s1-20261017/tres-tandas-62/CIERRE.md](../evidence/s1-20261017/tres-tandas-62/CIERRE.md) · [docs/API-CATALOGO-BASE-S1.md](../docs/API-CATALOGO-BASE-S1.md) · [docs/API-EDITOR-PLANTILLA-PRIVADA-S1.md](../docs/API-EDITOR-PLANTILLA-PRIVADA-S1.md) · [docs/METODOLOGIA-PARA-CLAUDE.md](../docs/METODOLOGIA-PARA-CLAUDE.md) · [docs/REVISION-C2-OBJETOS-SALA-CODEX-25-10-2026.md](../docs/REVISION-C2-OBJETOS-SALA-CODEX-25-10-2026.md) · [evidence/s1-20261025/c2-room-object-codex/CIERRE.md](../evidence/s1-20261025/c2-room-object-codex/CIERRE.md) · [evidence/s1-20261025/c2-room-object-codex/REVISION.md](../evidence/s1-20261025/c2-room-object-codex/REVISION.md) · [docs/MENSAJE-PARA-CODEX-C2-SALA-ENTREGA-25-10-2026.md](../docs/MENSAJE-PARA-CODEX-C2-SALA-ENTREGA-25-10-2026.md) · [docs/C2-CAMPOS-SALA-25-10-2026.md](../docs/C2-CAMPOS-SALA-25-10-2026.md) · [evidence/s1-20261025/c2-room-fields-codex/CIERRE.md](../evidence/s1-20261025/c2-room-fields-codex/CIERRE.md) · [evidence/s1-20261025/c2-room-fields-codex/REVISION-INDEPENDIENTE.md](../evidence/s1-20261025/c2-room-fields-codex/REVISION-INDEPENDIENTE.md) · [docs/C2-BORRADO-IMPACTO-25-10-2026.md](../docs/C2-BORRADO-IMPACTO-25-10-2026.md) · [evidence/s1-20261025/c2-delete-impact-codex/CIERRE.md](../evidence/s1-20261025/c2-delete-impact-codex/CIERRE.md) · [evidence/s1-20261025/c2-delete-impact-codex/REVISION.md](../evidence/s1-20261025/c2-delete-impact-codex/REVISION.md).

#### Paso 072 · I-06.01

Relacionar soporte real por operación/plantilla/AP y conservarlo.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-06.

#### Paso 073 · I-06.03

Verificar extremos/rutas en consultas, informes y avisos tras mover y revocar permisos.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-06.

#### Paso 074 · I-06.04

Documentar una ocupación por puerto lógico y separar I-07.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-06.

#### Paso 075 · I-06.05

Si se propone aplazar, decisión expresa de Wascar; no inferirla del PLAN contradictorio.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-06.

#### Paso 076 · I-06.06

Cerrar «Completar verificación de Dosen y finales ya soportados en sala» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-06.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### I-07 · Decidir modelo de terminales y pasos internos de Dose/panel

**Situación conocida:** implementacion: No modelo acordado/implementado de entrada fija+salida latiguillo simultáneas; face no crea terminal.; integracion: No integrado por falta de contrato físico explícito.; prueba: Conexiones externas no demuestran continuidad interna.; revision: Sin diseño pasante adoptado.; qa: No anunciado/disponible como ruta completa.

**Cierre esperado:** Decisión trazable soporte/límite revisada. Si incluida, implementación/pruebas/QA propias. No deducir continuidad por una cara ni bloquear automáticamente CRUD externo.

**Dependencias del resultado:** Decisión física de Wascar.

**Fuentes:** [docs/CONTRATO-INVENTARIO-S1.md](../docs/CONTRATO-INVENTARIO-S1.md) · [docs/CONTRATO-SERVIDOR-v0.1.md](../docs/CONTRATO-SERVIDOR-v0.1.md) · [docs/C2-CONCILIACION-INVENTARIO.md](../docs/C2-CONCILIACION-INVENTARIO.md) · [docs/METODOLOGIA-PARA-CLAUDE.md](../docs/METODOLOGIA-PARA-CLAUDE.md).

#### Paso 077 · I-07.01

Acordar ejemplos físicos requeridos, separando datos/PoE/AC.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-07.

#### Paso 078 · I-07.02

Definir identidades de terminal/paso, ocupación y Click-Click antes de código.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-07.

#### Paso 079 · I-07.03

Decidir si la primera entrega promete ruta pasante o límite expreso; separado de Dose/final ya requerido.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-07.

#### Paso 080 · I-07.04

Sólo si incluido: diseño/migración y pruebas dos enlaces externos+paso interno sin doble ocupación ambigua; revisión network/arquitectura.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: I-07.

## A · Usuarios, grupos y administración

### A-01 · Cerrar atribución técnica C1 S-38 a S-42 en la candidata vigente

**Situación conocida:** API y panel ya existen, con pruebas históricas y regresión C1 10/10 M3 db5 aa9. No está demostrado un defecto nuevo de esos mecanismos; tampoco se transfieren a app03/VM por defecto.

**Cierre esperado:** S-38..42 tienen atribución actual y regresión pertinente posterior a cambios, conservando límites. Logs stdout/stderr ya ensayados no se declaran universalmente ausentes de secretos.

**Dependencias del resultado:** F-10, F-11, F-12.

**Fuentes:** [docs/C1-CONCILIACION-S38-S42.md](../docs/C1-CONCILIACION-S38-S42.md) · [docs/REVISION-M3-CORRECCIONES-CODEX.md](../docs/REVISION-M3-CORRECCIONES-CODEX.md) · [evidence/s1-20261023/c1-logs-d2/REVISION.md](../evidence/s1-20261023/c1-logs-d2/REVISION.md) · [docs/REVISION-D14-05-CODEX.md](../docs/REVISION-D14-05-CODEX.md).

#### Paso 081 · A-01.01

Registrar candidata/DDL/GUI/instancia y relación de fuentes con pruebas C1 existentes.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: A-01.

#### Paso 082 · A-01.02

Después de cambios MFA ejecutar sólo focos afectados: misma sesión tras retirar última vía, unión de concesiones, último admin y suplente activo/global, password/reset/desactivación/reactivación, revocación de tokens/desafíos y replay que conserva sesión nueva.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: A-01.

#### Paso 083 · A-01.03

Mantener commit conjunto/revisión/operation/audit y negativos de fallo; comprobar logs capturados con marcadores sintéticos tras añadir factor/recuperación.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: A-01.

#### Paso 084 · A-01.04

Revisión distinta y matriz criterio→ejecución/build/resultado/límite; no forzar fallos de último admin en cuentas reales.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: A-01.

#### Paso 085 · A-01.05

Cerrar «Cerrar atribución técnica C1 S-38 a S-42 en la candidata vigente» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: A-01.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### A-02 · Completar aceptación visual del recorrido administrativo existente

**Situación conocida:** Alta guiada, grupos de personas/clientes separados, relaciones UUID, efectivos con origen, sesiones y auditoría ya implementados/integrados históricamente. Preview administración-arbol no certifica producto ni sustituye estos recorridos.

**Cierre esperado:** Resultados por caso/build conservados y observaciones administrativas resueltas/aceptadas expresamente por Wascar. Disponible no equivale a Pass; relación/árbol no se reinventa como AD.

**Dependencias del resultado:** A-01, F-11, C4: candidata/instancia QA seleccionada y guiones disponibles.

**Fuentes:** [docs/C1-CONCILIACION-S38-S42.md](../docs/C1-CONCILIACION-S38-S42.md) · [docs/UX-ADMINISTRACION-ARBOL.md](../docs/UX-ADMINISTRACION-ARBOL.md) · [docs/INTEGRACION-ALTA-GRUPOS-WINDOWS-QA-S1.md](../docs/INTEGRACION-ALTA-GRUPOS-WINDOWS-QA-S1.md) · [docs/GUI-AUDITORIA-CONTEXTO-55.md](../docs/GUI-AUDITORIA-CONTEXTO-55.md) · [docs/QA-CASOS-WASCAR.json](../docs/QA-CASOS-WASCAR.json).

#### Paso 086 · A-02.01

Wascar recorre usuario→pertenencias→efectivos y grupo→miembros/concesiones; ambas clases de grupo, homónimos y varios padres explícitos sin herencia AD.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: A-02.

#### Paso 087 · A-02.02

Comprobar retiro con sesión abierta y actualización de lectura/escritura sin logout; S-38 no exige push universal que borre todo dato ya renderizado.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: A-02.

#### Paso 088 · A-02.03

Recorrer reset/estado/sesiones/auditoría y altas/navegación; registrar lugar exacto donde haya pérdida de contexto, legibilidad o accesibilidad, versión y navegador.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: A-02.

#### Paso 089 · A-02.04

Conservar resultados previos y marcar cambios de versión; corregir sólo observaciones concretas y repetir focos. Probar teclado/voz habitual en su ámbito sin rediseñar RC9.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: A-02.

#### Paso 090 · A-02.05

Cerrar «Completar aceptación visual del recorrido administrativo existente» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: A-02.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### A-03 · Conciliar y cerrar atribución de auditoría fuera de las 21 formas administrativas

**Situación conocida:** 21 formas ya capturan contexto mínimo y tienen GUI tipada. El mapa mantiene parcial cobertura/atribución de otras acciones, especialmente inventario/intercambio/operación; no hay autorización para rellenar histórico ausente.

**Cierre esperado:** Cada acción contratada actual tiene cobertura mínima o limitación explícita sin inventar histórico; cambios y registro atómicos probados y lectura administrativa entendible.

**Dependencias del resultado:** C2/C3/C5: inventario/import-export/backup que producen esos eventos, A-01.

**Fuentes:** [docs/API-ADMIN-AUDITORIA-CONTEXTO-21-S1.md](../docs/API-ADMIN-AUDITORIA-CONTEXTO-21-S1.md) · [evidence/s1-20261017/quince-tandas-55-59/CIERRE.md](../evidence/s1-20261017/quince-tandas-55-59/CIERRE.md) · [docs/GUI-AUDITORIA-CONTEXTO-55.md](../docs/GUI-AUDITORIA-CONTEXTO-55.md) · [docs/MAPA-ENTREGA.json](../docs/MAPA-ENTREGA.json) · [docs/CONTRATO-SERVIDOR-v0.1.md](../docs/CONTRATO-SERVIDOR-v0.1.md).

#### Paso 091 · A-03.01

Enumerar acciones actuales fuera21 y contrastar actorUUID, cliente/ámbito cuando aplica, objetos directos, horaUTC, revisiones, outcome y request contra lo realmente capturado/publicado.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: A-03.

#### Paso 092 · A-03.02

Registrar diferencia concreta por acción; implementar sólo atribución mínima faltante con fallo que revierta mutation/operation/audit, sin JSON arbitrario/secretos.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: A-03.

#### Paso 093 · A-03.03

Verificar lectura honesta y aislamiento/rollback/replay de familias afectadas; contexto antiguo ausente permanece notRecorded.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: A-03.

#### Paso 094 · A-03.04

Coordinar con C2/C3/C5 para que cada familia conserve su evidencia y sólo se contabilice una vez.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: A-03.

#### Paso 095 · A-03.05

Cerrar «Conciliar y cerrar atribución de auditoría fuera de las 21 formas administrativas» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: A-03.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### A-04 · Cerrar retención operativa, correlación y recuperación de operaciones antiguas

**Situación conocida:** Operaciones y auditoría durables existentes; consulta administrativa paginada y contexto ya implementados. No hay política completa de purga/caducidad; marcas canceladas no se purgan para evitar reejecución antigua.

**Cierre esperado:** Política explícita y comprobada en frontera30 d, sin resucitar operaciones canceladas ni afirmar éxito incierto; auditoría/logs consultables/correlacionables sin secretos y manual fiel.

**Dependencias del resultado:** A-03, C5: retención y respaldo operativo.

**Fuentes:** [docs/CONTRATO-SERVIDOR-v0.1.md](../docs/CONTRATO-SERVIDOR-v0.1.md) · [docs/OPERACIONES-PENDIENTES.md](../docs/OPERACIONES-PENDIENTES.md) · [docs/API-ADMIN-AUDITORIA-S1.md](../docs/API-ADMIN-AUDITORIA-S1.md) · [docs/IMPLEMENTACION-REV4.md](../docs/IMPLEMENTACION-REV4.md) · [development/server/database/001-foundation.sql](../development/server/database/001-foundation.sql).

#### Paso 096 · A-04.01

Concretar retención30 d de resultados y tratamiento de peticiones/replays después de caducidad; proteger cancelaciones/tombstones y compensaciones que dependan de evidencia.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: A-04.
- Texto histórico trazable: Concretar retención30d de resultados y tratamiento de peticiones/replays después de caducidad; proteger cancelaciones/tombstones y compensaciones que dependan de evidencia.

#### Paso 097 · A-04.02

Definir retención/correlación de auditoría/logs y procedimiento operativo de consulta/exportación saneada; no suponer que debe añadirse Serilog o un endpoint nuevo si lo existente cubre el uso.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: A-04.

#### Paso 098 · A-04.03

Ensayar frontera temporal, petición antigua/cancelada y evidencia ausente: no reejecutar silenciosamente ni reconstruir desde el navegador.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: A-04.

#### Paso 099 · A-04.04

Documentar qué se conserva/borra y qué recuperación/compensación deja de estar disponible; vincular request/event/trace sin secretos.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: A-04.

#### Paso 100 · A-04.05

Cerrar «Cerrar retención operativa, correlación y recuperación de operaciones antiguas» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: A-04.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

## P · Paridad funcional y visual RC9

### P-01 · Convertir restauración RC9 de laboratorio en importación normal

**Situación conocida:** El Full Backup original ya se cargó en C conservando seguridad/MFA. El auxiliar fijado al original no equivale a importación JSON normal desde dashboard, que sigue pendiente.

**Cierre esperado:** Usuario capacitado importa archivo desde GUI/API con diez clientes/jerarquía/topología correctos, sin aplanamiento ni restos; evidencia/version/revisión/QA.

**Dependencias del resultado:** P-02, P-03 para original, Autenticación MFA estable.

**Fuentes:** [evidence/s1-20261029/rc9-demo-original-codex/RESULTADOS.md](../evidence/s1-20261029/rc9-demo-original-codex/RESULTADOS.md) · [docs/QA-DATOS-ORIGINALES-MFA10-WASCAR.md](../docs/QA-DATOS-ORIGINALES-MFA10-WASCAR.md).

#### Paso 101 · P-01.01

Clasificar backup multicliente frente JSON cliente/rack por formato/versión, sin aplanar ni fusionar nombres.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-01.

#### Paso 102 · P-01.02

Plan explícito destino/creación/mapeo por identidad y permisos; original exacto antes de confirmar.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-01.

#### Paso 103 · P-01.03

API staging/preview/commit con revisión/actor/CSRF/idempotencia/auditoría y capacidad de transferencia vigente.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-01.

#### Paso 104 · P-01.04

Reutilizar análisis validado; no convertir SQL generado por herramienta lab en entrada externa. Contrastar grupos/campos no soportados.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-01.

#### Paso 105 · P-01.05

GUI archivo→compatibilidad/plan→confirmación→commit→recarga y recuperación de incertidumbre.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-01.

#### Paso 106 · P-01.06

E2E10 clientes, revocación/fallo mitad y revisión distinta.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-01.
- Texto histórico trazable: E2E10clientes, revocación/fallo mitad y revisión distinta.

#### Paso 107 · P-01.07

Cerrar «Convertir restauración RC9 de laboratorio en importación normal» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-01.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### P-02 · Previsualizar inválidos y doble ocupación sin perder enlaces

**Situación conocida:** implementacion: Conversor lab rechaza connection_occupied; no UI staging que conserve y muestre ambos enlaces incompatibles completos.; integracion: Sin preview de colisiones de producto localizado.; prueba: Golden RC9 justifica requisito; rechazo no es preview íntegro.; revision: No revisión de staging/resolución completo.; qa: No habilitado.

**Cierre esperado:** Se ven ambos enlaces y el original se conserva; ningún commit normal sin resolver, fallos sin restos, revisión distinta y QA.

**Dependencias del resultado:** P-01.

**Fuentes:** [docs/CONTRATO-SERVIDOR-v0.1.md](../docs/CONTRATO-SERVIDOR-v0.1.md) · [docs/ACEPTACION.md](../docs/ACEPTACION.md) · [tools/windows/rc9_restore.py](../tools/windows/rc9_restore.py) · [docs/RESTAURACION-QA-RC9.md](../docs/RESTAURACION-QA-RC9.md).

#### Paso 108 · P-02.01

Preservar original/hash íntegros también si no se normaliza; límites de tamaño/tipo.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-02.

#### Paso 109 · P-02.02

Mostrar todos los objetos/enlaces/ocupaciones e IDs/extremos; nunca elegir cable arbitrario.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-02.

#### Paso 110 · P-02.03

Resolver explícitamente o dejar pendiente; nunca falso committed de import incompatible/parcial.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-02.

#### Paso 111 · P-02.04

Revisión/actor/permiso cambiados invalidan plan; revalidar al commit.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-02.

#### Paso 112 · P-02.05

JSON inválido, duplicados/dangling/grupos ambiguos/doble ocupación y fallo mitad/auditoría: cero efectos y original intacto.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-02.

#### Paso 113 · P-02.06

Cerrar «Previsualizar inválidos y doble ocupación sin perder enlaces» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-02.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### P-03 · Exportar JSON actual y original exacto como funciones distintas

**Situación conocida:** Exportación JSON actual por cliente con recibo, permisos vigentes, SHA256 y descarga probada en desarrollo43. La intención incierta no persiste al desmontar; importación/merge/originalRC9/backupPG quedan pendientes. No cierre íntegro de P-03.

**Cierre esperado:** Actual refleja commits vigentes y original conserva hash; funciones separadas respetan permisos, prueba/revisión/QA por versión.

**Dependencias del resultado:** P-01, P-04.

**Fuentes:** [docs/PUNTO3-FUNCIONES-PENDIENTES.md](../docs/PUNTO3-FUNCIONES-PENDIENTES.md) · [evidence/s1-20261102/punto3/RESULTADOS.md](../evidence/s1-20261102/punto3/RESULTADOS.md).

#### Paso 114 · P-03.01

Completar contrato de cliente/rack/backup reutilizando el exportador actual por cliente; conservar UUID y revision sin rehacer lo ya construido.

- Tipo de trabajo: Conciliar evidencia existente.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-03.
- Texto histórico trazable: Contrato export cliente/rack/backup acordado con revisión fuente y mapeo serverUUID↔IDexportable estable.

#### Paso 115 · P-03.02

Conciliar/acreditar la exportacion actual por cliente ya implementada desde snapshot autorizado; cerrar QA y formatos restantes sin duplicarla.

- Tipo de trabajo: Conciliar evidencia existente.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-03.
- Texto histórico trazable: Exportar estado actual desde snapshot autorizado, no archivo importado/localStorage.

#### Paso 116 · P-03.03

Descargar original byteidéntico desde procedencia persistida segura, rotulado distinto.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-03.

#### Paso 117 · P-03.04

Completar la matriz de autorizacion/recibo/auditoria y persistencia de intencion tras navegar/recargar; parte ya probada se conserva.

- Tipo de trabajo: Conciliar evidencia existente.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-03.
- Texto histórico trazable: Permiso transferencia/ámbito/actor/CSRF/revisión/recibo/auditoría y recuperación sin filtrar ajenos.

#### Paso 118 · P-03.05

Completar original byteidentico, round-trip y QA/tamanos/reinicio pendientes reutilizando las pruebas del JSON actual; no confundirlo con Full Backup.

- Tipo de trabajo: Conciliar evidencia existente.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-03.
- Texto histórico trazable: Validación/tamaño/hash/descarga segura; escritura→actual cambiado→originalSHAigual; revocación/replay/reinicio/revisión/QA.

#### Paso 119 · P-03.06

Cerrar «Exportar JSON actual y original exacto como funciones distintas» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-03.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### P-04 · Demostrar round-trip JSON y preservar extensiones

**Situación conocida:** implementacion: properties/rc9OriginalId conservan parte de datos; metadata global no modelada sólo archivada. Sin exportactual→reimport completo.; integracion: Depende de P-01/P-03.; prueba: Comparación conversión10 tablas no es round-trip sin cambios.; revision: Conversión sí; round-trip completo no.; qa: No caso producto completo aceptado.

**Cierre esperado:** Cada formato prometido tiene ida/vuelta reproducible, diferencias permitidas documentadas y sin pérdida de campos/IDs/extensiones, con revisión.

**Dependencias del resultado:** P-01, P-03, P-06.

**Fuentes:** [docs/ACEPTACION.md](../docs/ACEPTACION.md) · [docs/CONTRATO-SERVIDOR-v0.1.md](../docs/CONTRATO-SERVIDOR-v0.1.md) · [docs/RESTAURACION-QA-RC9.md](../docs/RESTAURACION-QA-RC9.md) · [tools/windows/rc9_restore.py](../tools/windows/rc9_restore.py) · [evidence/s1-20261020/arranque-y-datos-rc9/CIERRE.md](../evidence/s1-20261020/arranque-y-datos-rc9/CIERRE.md).

#### Paso 120 · P-04.01

Matriz formato/versión JSON soportado; CSV/XLS de informes no son backups.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-04.

#### Paso 121 · P-04.02

Fixtures homónimos, grupos gn repetido, legacyIDs, extensiones anidadas y metadata global.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-04.

#### Paso 122 · P-04.03

Export sin cambios→lab nuevo→import→export y comparación de conocidos/IDs/extensiones/semántica; no exigir igualdad byte si no contractual.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-04.

#### Paso 123 · P-04.04

Precisar metadatos hoy sólo archivados y conservarlos en ida/vuelta; ninguna pérdida silenciosa.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-04.

#### Paso 124 · P-04.05

Editar conocidos sin borrar desconocidos; límites/atomicidad y revisión independiente del comparador/resultados.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-04.

#### Paso 125 · P-04.06

Cerrar «Demostrar round-trip JSON y preservar extensiones» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-04.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### P-05 · Cerrar lista de herramientas RC9 restantes y sus equivalentes

**Situación conocida:** implementacion: Referencias loadJSON/importRackJSON/mergeProject/importCSV/irAppendProject y saveSnapshot/restoreSnapshot/irDownloadCurrentRescue; equivalentes completos de producto no localizados. No afirmar ausencia sólo por un nombre histórico.; integracion: BackupPG operativo es C5, no estas herramientas de inventario.; prueba: No ejecución servidor actual de esas familias acreditada.; revision: Lista de equivalencias/restantes por revisar.; qa: Sin guiones de equivalencia identificados.

**Cierre esperado:** Desaparece rótulo genérico herramientasrestantes: lista cerrada, equivalentes/diferencias aceptadas y pruebas/revisión/QA de incluidas; S5/backup separados.

**Dependencias del resultado:** P-01–P-04, I-02 si restaura estado.

**Fuentes:** [docs/MAPA-RC9-R3.md](../docs/MAPA-RC9-R3.md) · [docs/CONTRATO-SERVIDOR-v0.1.md](../docs/CONTRATO-SERVIDOR-v0.1.md) · [docs/CIERRE-RESTANTE.md](../docs/CIERRE-RESTANTE.md) · [development/server/src/RackClick.Server/Program.cs](../development/server/src/RackClick.Server/Program.cs) · [development/frontend/src/InventoryPanel.jsx](../development/frontend/src/InventoryPanel.jsx).

#### Paso 126 · P-05.01

Contrastar artefacto RC9 transformado y definir exactamente cada operación y pertenencia S1–S4.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-05.

#### Paso 127 · P-05.02

Separar import cliente/rack/append/merge/CSV de P-01; por cada una equivalente/reutilización/límite explícito.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-05.

#### Paso 128 · P-05.03

Separar snapshot/rescate por ámbito de backup/restorePG. Restaurar inventario requiere plan/revisión/permiso, nunca snapshot ciego sobre otro técnico.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-05.

#### Paso 129 · P-05.04

Implementar faltantes contractuales con identidad/atomicidad/recuperación; pruebas/guiones por operación y revisión.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-05.

#### Paso 130 · P-05.05

Decisión expresa para aplazamientos; S-50 return permanece S5.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-05.
- Texto histórico trazable: Decisión expresa para aplazamientos; S-50return permanece S5.

#### Paso 131 · P-05.06

Cerrar «Cerrar lista de herramientas RC9 restantes y sus equivalentes» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-05.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### P-06 · Persistir identidad documental del cliente y branding RC9

**Situación conocida:** implementacion: ReportesHTML omiten Systemhaus/logo/técnico; XLSHTML Technician vacío porque no hay campo persistido/importado. No usar actor como técnico documental.; integracion: Reportes existen; identidad documental completa no integrada.; prueba: Formatos probados, no metadata/logo nuevos.; revision: Acotada formatos existentes.; qa: S-36 identidad parcial.

**Cierre esperado:** Campos RC9 prometidos persistidos/editables/importables/exportables y renderizados con identidad aprobada sin contenido activo; evidencia y QA.

**Dependencias del resultado:** P-03/P-04, P-07.

**Fuentes:** [docs/CONTRATO-SERVIDOR-v0.1.md](../docs/CONTRATO-SERVIDOR-v0.1.md) · [docs/API-INFORMES-IMPRIMIBLES-S1.md](../docs/API-INFORMES-IMPRIMIBLES-S1.md) · [docs/API-XLS-HTML-RC9-S1.md](../docs/API-XLS-HTML-RC9-S1.md) · [docs/API-INFORME-RACK-SVG-S1.md](../docs/API-INFORME-RACK-SVG-S1.md) · [docs/RESTAURACION-QA-RC9.md](../docs/RESTAURACION-QA-RC9.md).

#### Paso 132 · P-06.01

Contrastar campos RC9 cliente/Systemhaus/logo/técnico/metadata y permisos.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-06.

#### Paso 133 · P-06.02

MigraciónSQL/Npgsql/API/GUI y su import/export; técnico documental independiente del actor.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-06.

#### Paso 134 · P-06.03

Validar formato/tamaño del logo y render pasivo sin HTML/URL activa.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-06.

#### Paso 135 · P-06.04

Añadir identidad real a reportesrack/cliente/etiquetas/XLS según referencia, conservando estilos/familias existentes.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-06.

#### Paso 136 · P-06.05

Hostiles/Unicode, ámbitos, persistencia, impresión/comparación visual y revisión distinta/QA.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-06.

#### Paso 137 · P-06.06

Cerrar «Persistir identidad documental del cliente y branding RC9» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-06.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### P-07 · Cerrar formatos existentes y resolver obligación PDF

**Situación conocida:** CSV, XLSX, SVG, HTML imprimible y XLS HTML existen y se probaron por HTTP en el laboratorio de comparación. Falta su cierre GUI/formato/aceptación; PNG y la obligación de PDF nativo se tratan explícitamente, sin confundirlos con impresión HTML. Imprimible, SVG y XLS HTML tienen ahora propuesta del rack al primer abrir, adopcion explicita posterior y metadatos bajo demanda, probados/revisados en laboratorio. Pendientes/errores/transporte se conservan. Falta integrar y el resto de presentacion/formatos; no repetir esos controles desde cero.

**Cierre esperado:** Todos formatos prometidos tienen salida/lector/impresión y permisos verificados; PDF tiene decisión y evidencia; diferencias aceptadas, no eliminadas por plan ambiguo.

**Dependencias del resultado:** P-06, Candidata final, DecisiónD4.

**Fuentes:** [docs/COMPARACION-OFFLINE-RC10-SERVIDOR.md](../docs/COMPARACION-OFFLINE-RC10-SERVIDOR.md) · [docs/TANDA-INFORMES-CONTEXTO-30-10-2026.md](../docs/TANDA-INFORMES-CONTEXTO-30-10-2026.md) · [docs/REVISION-INFORMES-CONTEXTO-30-10-2026.md](../docs/REVISION-INFORMES-CONTEXTO-30-10-2026.md).

#### Paso 138 · P-07.01

Lista exacta RC9/equivalentes: CSV≠XLSX≠XLSHTML, PDF/impresión, etiquetasrack sin inventar otras.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-07.

#### Paso 139 · P-07.02

Resolver D4 contradictorio sin suprimir obligación por propuesta; si nativo requerido especificar/desarrollar, si impresión equivalente registrar decisión explícita.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-07.

#### Paso 140 · P-07.03

Comparar candidata final con referencia/brandingP-06, extremos cross/sala, Unicode/hostiles y permisos en generación/replay/status/genéricas.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-07.

#### Paso 141 · P-07.04

Probar impresión/guardarPDF y etiquetas en entorno objetivo; no prometer tres hojas XLSHTML. Foco real lectorXLSX acordado si ofrecido.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-07.

#### Paso 142 · P-07.05

Registrar bytes/hash/capturas/pruebas/revisión/QA sin rehacer exportadores ya cubiertos.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-07.

#### Paso 143 · P-07.06

Cerrar «Cerrar formatos existentes y resolver obligación PDF» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-07.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### P-08 · Concluir aceptación de plantillas/favoritos/preferencias existentes

**Situación conocida:** implementacion: BASE33/7, favoritos personales, privadas+rename+editor nuevaUUID, publicar/retirar/usar compartidas, idioma/tema y paletas10 tipos/28 parejas existen.; integracion: Windows/QA8–13 históricos; no volver a declarar compartir/editor/paletas pendientes por notas viejas.; prueba: PG/Node/Edge por bloques; no aceptación total S-26/S-47.; revision: Distinta por bloque; combinación finalMFA requiere foco.; qa: QA46–51/55–58/66–74/79–84 históricos, no Pass automático.

**Cierre esperado:** Cada familia S-26/S-47 probada/aceptada por actor en candidata final; sin privadas ajenas/éxitos falsos, revisión y QA, sin recrear funciones.

**Dependencias del resultado:** Candidata final/MFA, P-10/P-11.

**Fuentes:** [docs/API-CATALOGO-BASE-S1.md](../docs/API-CATALOGO-BASE-S1.md) · [docs/API-FAVORITOS-PERSONALES-S1.md](../docs/API-FAVORITOS-PERSONALES-S1.md) · [docs/API-PLANTILLAS-PRIVADAS-S1.md](../docs/API-PLANTILLAS-PRIVADAS-S1.md) · [docs/API-EDITOR-PLANTILLA-PRIVADA-S1.md](../docs/API-EDITOR-PLANTILLA-PRIVADA-S1.md) · [docs/API-PLANTILLAS-COMPARTIDAS-S1.md](../docs/API-PLANTILLAS-COMPARTIDAS-S1.md) · [docs/INTEGRACION-ESQUEMA10-WINDOWS-QA-S1.md](../docs/INTEGRACION-ESQUEMA10-WINDOWS-QA-S1.md) · [docs/INTEGRACION-PALETA-CATEGORIAS-WINDOWS-QA-S1.md](../docs/INTEGRACION-PALETA-CATEGORIAS-WINDOWS-QA-S1.md).

#### Paso 144 · P-08.01

Conservar código y conciliar notas obsoletas; no nueva función presupuesta.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-08.

#### Paso 145 · P-08.02

Relacionar S-26 con BASE/privada/compartida/favorito y lector/editor/publicador/ajeno; identificar sólo huecos reales.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-08.

#### Paso 146 · P-08.03

Preferencias por dueño y precedencia manual→pareja→null al crear, sin recolor histórico.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-08.

#### Paso 147 · P-08.04

Foco pérdida respuesta/cambioactor/recarga/reauthMFA sobre combinación final.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-08.

#### Paso 148 · P-08.05

QA con cuentas distintas y resultados por versión; preferencias no sustituyen aceptaciónS-26.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-08.

#### Paso 149 · P-08.06

Cerrar «Concluir aceptación de plantillas/favoritos/preferencias existentes» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-08.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### P-09 · Cerrar compatibilidad y aceptación de avisos multiusuario

**Situación conocida:** implementacion: Polling5 s visible, cursor/gaps, permisos actuales, borradores/Click-Click y detalle antes/después existen. Fuente actual incluye31 acciones con createFromSharedTemplate; contrato428–472 describía30.; integracion: Detalle472 y extensión compartidas integrados históricamente; estructuralesC2 nuevos contexto notAvailable explícito.; prueba: 60/428–472/compartidas prueban commit/replay/rollback/aislamiento/reconexión/escala acotada; no capacidad10 sesiones por ello.; revision: Distinta acotada, no combinación14MFA+C2.; qa: QA10/63–65 históricos; aceptación pendiente.

**Cierre esperado:** Autor/acción/IDs/extremos correctos con autoridad actual; revocación detiene/limpia y borrador se conserva; límites explícitos, revisión y QA.

**Dependencias del resultado:** I-01, MFA final, C6 para rendimiento.

**Fuentes:** [docs/API-AVISOS-CLIENTE-S1.md](../docs/API-AVISOS-CLIENTE-S1.md) · [docs/API-AVISOS-DESCRIPTIVOS-S1.md](../docs/API-AVISOS-DESCRIPTIVOS-S1.md) · [docs/GUI-AVISOS-CLIENTE-S1.md](../docs/GUI-AVISOS-CLIENTE-S1.md) · [development/server/src/RackClick.Server/InventoryChanges.cs](../development/server/src/RackClick.Server/InventoryChanges.cs) · [development/server/src/RackClick.Server/InventoryChangeDetails.cs](../development/server/src/RackClick.Server/InventoryChangeDetails.cs) · [evidence/s1-20261018/sesenta-tandas-533-592/CIERRE.md](../evidence/s1-20261018/sesenta-tandas-533-592/CIERRE.md).

#### Paso 150 · P-09.01

Conciliar31 acciones y contexto finito por acción frente documentos30/26; no reconstruir historia.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-09.
- Texto histórico trazable: Conciliar31acciones y contexto finito por acción frente documentos30/26; no reconstruir historia.

#### Paso 151 · P-09.02

Foco final dos actores mismo cliente/rack, lector y ajeno, MFA caducada/revocación/cambio cliente/respuesta tardía.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-09.

#### Paso 152 · P-09.03

Nombres históricos vs actorCurrent/etiquetasvista rotulados, no completar con tablas actuales.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-09.

#### Paso 153 · P-09.04

Un aviso por commit, ninguno por replay/rollback; gap explícito, reconexión y borrador intacto.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-09.

#### Paso 154 · P-09.05

Coordinar escala10 sesiones conC6 sin doble tarea/métrica; QA y guion después de cambios reales.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-09.
- Texto histórico trazable: Coordinar escala10sesiones conC6 sin doble tarea/métrica; QA y guion después de cambios reales.

#### Paso 155 · P-09.06

Cerrar «Cerrar compatibilidad y aceptación de avisos multiusuario» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-09.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### P-10 · Auditar EN/DE/ES, temas y literalidad de datos

**Situación conocida:** implementacion: Tres idiomas, códigos backend localizados y preferencia idioma/tema existen. Falta auditoría integral; separador literal ? de Editar grupos sigue enInventoryPanel.; integracion: Preferencias históricasQA11/paletasQA13; nuevasGUI deben cubrirse.; prueba: Módulos EN/DE/ES/390 px por bloques; no recorrido exhaustivo.; revision: UX/DOM acotadas, no lingüística integral.; qa: S-47 total pendiente.

**Cierre esperado:** Matriz3 idiomas/2 temas sin texto prometido ausente/incoherente; datos intactos y capturas reales; QA deS-47 no sustituida por persistencia de idioma.

**Dependencias del resultado:** I-01, P-06, MFAinterfaz, P-11.

**Fuentes:** [docs/IMPLEMENTACION-REV4.md](../docs/IMPLEMENTACION-REV4.md) · [docs/API-PREFERENCIAS-PERSONALES-S1.md](../docs/API-PREFERENCIAS-PERSONALES-S1.md) · [docs/INTEGRACION-ESQUEMA11-WINDOWS-QA-S1.md](../docs/INTEGRACION-ESQUEMA11-WINDOWS-QA-S1.md) · [development/frontend/src/InventoryPanel.jsx](../development/frontend/src/InventoryPanel.jsx) · [docs/QA-CASOS-WASCAR.json](../docs/QA-CASOS-WASCAR.json).

#### Paso 156 · P-10.01

Enumerar login/MFA/reauth, inventario, plantillas/preferencias, avisos/errores/conflictos, admin/reportes.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-10.

#### Paso 157 · P-10.02

Contrastar todas claves/rótulos/ayudas/errores en 3 idiomas; cabeceras inglesas XLSHTML como adaptación declarada.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-10.
- Texto histórico trazable: Contrastar todas claves/rótulos/ayudas/errores en3idiomas; cabeceras inglesas XLSHTML como adaptación declarada.

#### Paso 158 · P-10.03

Corregir faltas reales incluido ? visible si se toma ese cambio; sin traducir nombres/etiquetas del usuario.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-10.

#### Paso 159 · P-10.04

Dark/light,390 px/desktop, texto largo/Unicode y ordenación explícita; no migrar collation por intuición.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-10.
- Texto histórico trazable: Dark/light,390px/desktop, texto largo/Unicode y ordenación explícita; no migrar collation por intuición.

#### Paso 160 · P-10.05

Reportes/conflictos/recuperaciónMFA y QA por versión con revisión distinta.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-10.

#### Paso 161 · P-10.06

Cerrar «Auditar EN/DE/ES, temas y literalidad de datos» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-10.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### P-11 · Completar teclado, lector, contraste y paridad visual funcional

**Situación conocida:** Racks/tarjetas primero, jerarquia y PoE plegables, accesos con foco y exportadores montados ya implementados y probados en laboratorio con datos originales. Revision independiente favorable; falta integrar candidata, QA y la matriz completa de accesibilidad/lector/contraste. No volver a implementar el reordenamiento.

**Cierre esperado:** Matriz completa con resultados reales por versión, problemas resueltos/límites aceptados, conservando GUI/Click-Click. Voz no inferida de AX; QA de Wascar.

**Dependencias del resultado:** I-03, P-08, P-10, MFA y GUI estructural finales.

**Fuentes:** [docs/TANDA-RACKS-PRIMERO-30-10-2026.md](../docs/TANDA-RACKS-PRIMERO-30-10-2026.md) · [docs/REVISION-RACKS-PRIMERO-30-10-2026.md](../docs/REVISION-RACKS-PRIMERO-30-10-2026.md).

#### Paso 162 · P-11.01

Matriz Tab/ShiftTab/Enter/Escape/foco para rack/puerto, alternativa Click-Click, diálogos/recovery, plantillas/avisos/admin/MFA.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-11.

#### Paso 163 · P-11.02

Lector real con status/alert/nombres/relaciones/cambios dinámicos; foco/borrador tras 412/reauth.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-11.
- Texto histórico trazable: Lector real con status/alert/nombres/relaciones/cambios dinámicos; foco/borrador tras412/reauth.

#### Paso 164 · P-11.03

Contraste dark/light, zoom/390 px; tooltips/inspector accesibles y datos actuales tras rename/move.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-11.
- Texto histórico trazable: Contraste dark/light, zoom/390px; tooltips/inspector accesibles y datos actuales tras rename/move.

#### Paso 165 · P-11.04

Capturas contra RC9 adoptada front/rear/presets/estados/PoE/reportes, literales hostiles y sin clienteanterior.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-11.
- Texto histórico trazable: Capturas contra RC9adoptada front/rear/presets/estados/PoE/reportes, literales hostiles y sin clienteanterior.

#### Paso 166 · P-11.05

Corregir reproducibles y repetir foco; revisión independiente y QA con límites voz/DOM explícitos.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-11.

#### Paso 167 · P-11.06

Cerrar «Completar teclado, lector, contraste y paridad visual funcional» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: P-11.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

## W · Instalación y operación Windows

### W-02 · Instalar desde cero en Windows limpio y declarar la matriz soportada

**Situación conocida:** New11 en D limpio Windows Server2025/noDC, CRT/runtime/PG incluidos, cuenta estandar, servicio/HTTPS y postboot verificados tras reinicio de Wascar. W-02.01/.02 ya acreditados por 10; faltan matriz de dependencias/hosts/rechazos. No reinstalar D ni duplicar credito.

**Cierre esperado:** Recorrido nuevo de instalación completo en los hosts declarados, con versiones y resultados reales; ausencia de soporte no probado indicada explícitamente.

**Dependencias del resultado:** W-01, E-01.

**Fuentes:** [evidence/s1-20261102/windows43/RESULTADOS.md](../evidence/s1-20261102/windows43/RESULTADOS.md) · [docs/INSTALADOR11-WINDOWS43.md](../docs/INSTALADOR11-WINDOWS43.md) · [evidence/s1-20261102/vm11-d/RESULTADOS.md](../evidence/s1-20261102/vm11-d/RESULTADOS.md) · [evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md](../evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md).

#### Paso 168 · W-02.03

Repetir con dependencias compatibles presentes; comprobar rechazo concreto de versión incompatible, puertos ocupados y DC antes de mutaciones.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: W-02.

#### Paso 169 · W-02.04

Conciliar S-01 con Windows11 como posible host: ensayar todo sistema que se declare soportado. Windows11 usado sólo como cliente requiere navegador, sin servidor instalado.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: W-02.

#### Paso 170 · W-02.05

Cerrar «Instalar desde cero en Windows limpio y declarar la matriz soportada» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: W-02.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### W-03 · Cuenta mínima, servicio Windows y arranque automático reales

**Situación conocida:** D11 verificada: SCM Running/Auto, SID y cuenta estandar, HTTPS43 y postboot real; custodias e identidades separadas. Faltan negativos/ACL completos y fallos de parada/hijo, no construir otro servicio.

**Cierre esperado:** Servicio y PostgreSQL funcionan bajo identidad mínima tras reinicio real; logs/estados y acceso privado son verificables.

**Dependencias del resultado:** W-02, F-04.

**Fuentes:** [evidence/s1-20261029/installer10-vm-codex/RESULTADOS.md](../evidence/s1-20261029/installer10-vm-codex/RESULTADOS.md) · [evidence/s1-20261102/vm11-d/RESULTADOS.md](../evidence/s1-20261102/vm11-d/RESULTADOS.md) · [evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md](../evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md).

#### Paso 171 · W-03.01

Conciliar cuenta estandar/SID/SCM y separacion SQL ya comprobados en D11; completar matriz ACL/negativos sin reinstalar D.

- Tipo de trabajo: Conciliar evidencia existente.
- Estado formal: pending; ámbito: Primera entrega; responsable: W-03.
- Texto histórico trazable: Instalar/verificar cuenta estándar y derecho de servicio, ACL de código/datos/claves y separación de identidades SQL runtime/migración.

#### Paso 172 · W-03.02

Arrancar y detener por SCM; comprobar señalización, tiempos, diagnósticos, cierre limpio y fallo del hijo sin estado falso Running.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: W-03.

#### Paso 173 · W-03.03

Acreditar readiness 43 y arranque automatico ya comprobados, y completar persistencia posterior del inventario/tareas en laboratorio separado. El texto readiness 14 es historico.

- Tipo de trabajo: Conciliar evidencia existente.
- Estado formal: pending; ámbito: Primera entrega; responsable: W-03.
- Texto histórico trazable: Reiniciar Windows y verificar arranque automático, readiness14, inventario persistido y tareas operativas.

#### Paso 174 · W-03.04

Completar verificacion y manual del acceso privado por instancia, reutilizando el acceso nativo existente; no introducir otra contrasena compartida.

- Tipo de trabajo: Conciliar evidencia existente.
- Estado formal: pending; ámbito: Primera entrega; responsable: W-03.
- Texto histórico trazable: Comprobar credenciales iniciales privadas y acceso administrativo recuperable, sin introducir contraseña universal.

#### Paso 175 · W-03.05

Cerrar «Cuenta mínima, servicio Windows y arranque automático reales» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: W-03.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### W-04 · HTTPS, certificados, red y acceso casa/trabajo en la edición final

**Situación conocida:** D11 tiene origen, CA y firewall limitados verificados; cargador y MFA usaron TLS normal. Faltan otro equipo cliente, cambio casa/trabajo de la candidata, renovacion/caducidad y recuperacion de certificados.

**Cierre esperado:** Acceso LAN confiable y cambio de red con datos conservados; renovación y errores documentados, sin exponer claves privadas.

**Dependencias del resultado:** W-03, E-01.

**Fuentes:** [evidence/s1-20261102/vm11-d/RESULTADOS.md](../evidence/s1-20261102/vm11-d/RESULTADOS.md) · [evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md](../evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md).

#### Paso 176 · W-04.01

Conciliar origen/SAN/puertos/subred ya verificados en D11; completar escenarios de la matriz final sin cambiar su red.

- Tipo de trabajo: Conciliar evidencia existente.
- Estado formal: pending; ámbito: Primera entrega; responsable: W-04.
- Texto histórico trazable: Fijar nombre/IP de aplicación, SAN, puerto y subred autorizada; no cambiar IP/DNS Windows por inferencia.

#### Paso 177 · W-04.02

Instalar y verificar cadena HTTPS; distribuir sólo CA pública a navegadores clientes y comprobar otra sesión desde otro equipo.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: W-04.

#### Paso 178 · W-04.03

Completar los negativos de firewall/PGlocal/CSRF/Origin/cookies reutilizando HTTPS y cookie MFA nativos ya comprobados.

- Tipo de trabajo: Conciliar evidencia existente.
- Estado formal: pending; ámbito: Primera entrega; responsable: W-04.
- Texto histórico trazable: Comprobar firewall limitado a la red elegida y PostgreSQL sólo local; CSRF/Origin/cookies bajo HTTPS real.

#### Paso 179 · W-04.04

Ensayar cambio casa/trabajo de la edición nueva, detección y recuperación de fallo, conservando datos/cuentas.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: W-04.

#### Paso 180 · W-04.05

Documentar y probar renovación/caducidad del certificado y recuperación de su clave; no considerar certificado de laboratorio una PKI productiva aceptada.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: W-04.

#### Paso 181 · W-04.06

Cerrar «HTTPS, certificados, red y acceso casa/trabajo en la edición final» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: W-04.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### W-05 · Repetición, cancelación, mantenimiento y diagnóstico del instalador

**Situación conocida:** Hay preflights, archivo/retirada por identidad y reportes automáticos; experiencias históricas no equivalen a ensayo completo14 de estos recorridos.

**Cierre esperado:** Cada fallo/cancelación tiene estado veraz y procedimiento repetible; programas/bases ajenos y cuentas manuales permanecen intactos.

**Dependencias del resultado:** W-02.

**Fuentes:** [docs/INICIO-IMPLEMENTACION-S1.md](../docs/INICIO-IMPLEMENTACION-S1.md) · [docs/REINICIO-LIMPIO-SERVIDOR.html](../docs/REINICIO-LIMPIO-SERVIDOR.html) · [docs/REVISION-INSTALADOR14-06-CODEX.md](../docs/REVISION-INSTALADOR14-06-CODEX.md).

#### Paso 182 · W-05.01

Repetir instalación contra una existente: no reinicializar base, crear admin duplicado ni tomar una carpeta ajena.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: W-05.

#### Paso 183 · W-05.02

Cancelar antes de aplicar y durante fases recuperables; comprobar estado final y posibilidad de continuar sin borrar evidencias.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: W-05.

#### Paso 184 · W-05.03

Ensayar retirada/archivo sólo de instancias/cuentas atribuidas, conservar SID y bases; tratar elementos sin atribución con informe concreto.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: W-05.

#### Paso 185 · W-05.04

Comprobar informe automático, errores y códigos de salida, y que Acceso privado abre bajo la identidad esperada sin filtrar secretos.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: W-05.

#### Paso 186 · W-05.05

Cerrar «Repetición, cancelación, mantenimiento y diagnóstico del instalador» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: W-05.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### W-06 · Recorrido completo de persistencia y concurrencia del servidor instalado

**Situación conocida:** D11 contiene Demo50 creada por 2553 comandos API y contrastada por colecciones/UUID/conexiones. Faltan recorrido instalado con roles y segunda cuenta, reinicio posterior del conjunto y concurrencia/perdida de respuesta. No recrear clientes ni repetir carga.

**Cierre esperado:** S-55 reproducido completo y conflictos/recuperación coherentes sobre build/DB/host identificados.

**Dependencias del resultado:** W-03, I-01, P-01.

**Fuentes:** [evidence/s1-20261102/vm11-d/RESULTADOS.md](../evidence/s1-20261102/vm11-d/RESULTADOS.md) · [evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md](../evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md).

#### Paso 187 · W-06.01

Reutilizar Demo50 ya creada/verificada para la prueba instalada de edicion y persistencia; no volver a generar o cargar los clientes en D.

- Tipo de trabajo: Conciliar evidencia existente.
- Estado formal: pending; ámbito: Primera entrega; responsable: W-06.
- Texto histórico trazable: Desde Systemhaus y cliente crear/editar jerarquía, rack, equipo y nota de puerto con cuenta autorizada.

#### Paso 188 · W-06.02

Guardar, cerrar navegador, reiniciar servicio y verificar desde segunda cuenta; comparar IDs y relaciones. Verificar admin/técnico/lector y ámbitos en el mismo conjunto instalado.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: W-06.

#### Paso 189 · W-06.03

Provocar conflicto simultáneo, pérdida de respuesta y reintento; confirmar una sola operación/auditoría sin éxito fantasma.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: W-06.

#### Paso 190 · W-06.04

Usar los mismos resultados para cubrir los criterios compartidos de otros bloques; no repetir esta corrida por cada documento.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: W-06.

#### Paso 191 · W-06.05

Cerrar «Recorrido completo de persistencia y concurrencia del servidor instalado» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: W-06.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

## R · Backup, recuperación y actualización

### R-01 · Backup programado local y retención comprobada

**Situación conocida:** Backup inicial, tarea programada tras postboot y backup posterior a Demo50 completados con resultado0 en D. Faltan retencion configurable, destinos/fallos y restaurabilidad; backup completo no demuestra recuperacion MFA portable.

**Cierre esperado:** Ejecución programada real, política de retención y fallos comprobados; sólo copias completas verificadas quedan elegibles.

**Dependencias del resultado:** W-03.

**Fuentes:** [docs/COMPARACION-OFFLINE-RC10-SERVIDOR.md](../docs/COMPARACION-OFFLINE-RC10-SERVIDOR.md) · [evidence/s1-20261029/rc9-demo-original-codex/RESULTADOS.md](../evidence/s1-20261029/rc9-demo-original-codex/RESULTADOS.md) · [evidence/s1-20261102/vm11-d/RESULTADOS.md](../evidence/s1-20261102/vm11-d/RESULTADOS.md) · [evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md](../evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md).

#### Paso 192 · R-01.01

Conciliar backup/tarea real despues de postboot y despues de Demo50, ambos completados; completar los negativos pendientes sin otro backup rutinario.

- Tipo de trabajo: Conciliar evidencia existente.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-01.
- Texto histórico trazable: Comprobar tarea bajo cuenta mínima después del reinicio y registrar ejecución/errores sin contraseñas.

#### Paso 193 · R-01.02

Implementar o completar retención configurable con valores documentados; nunca borrar la última copia válida por un fallo.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-01.

#### Paso 194 · R-01.03

Ensayar backups concurrentes, falta de espacio, corte de escritura y copia incompleta; verificar que no se publican como válidos.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-01.

#### Paso 195 · R-01.04

Aprovechar medidas y backup de Demo50; completar duracion/tamano/RPO/RTO requeridos sin convertir objetivos en garantias.

- Tipo de trabajo: Conciliar evidencia existente.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-01.
- Texto histórico trazable: Medir duración y tamaño con demo; documentar RPO24h/RTO2h como objetivos propuestos, no garantías ya medidas.

#### Paso 196 · R-01.05

Cerrar «Backup programado local y retención comprobada» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-01.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### R-02 · Destinos USB y UNC con copia local previa y tolerancia a fallos

**Situación conocida:** El operador básico exige disco fijo local; copiar manualmente desdeUSB/UNC no cierra el flujo operativo. D6 de aplazarUSB no está confirmada inequívocamente.

**Cierre esperado:** Local/USB/UNC tienen prueba de copia, fallo y restauración con límites y permisos registrados.

**Dependencias del resultado:** R-01.

**Fuentes:** [docs/ACEPTACION.md](../docs/ACEPTACION.md) · [docs/METODOLOGIA-PARA-CLAUDE.md](../docs/METODOLOGIA-PARA-CLAUDE.md) · [docs/BACKUP-RESTAURACION-WINDOWS-S1.md](../docs/BACKUP-RESTAURACION-WINDOWS-S1.md).

#### Paso 197 · R-02.01

Completar copia local consistente y después copia verificada a destino USB/UNC autorizado, con identidad y permisos mínimos.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-02.

#### Paso 198 · R-02.02

Ensayar NAS ausente, permisos denegados, unidad retirada, disco lleno y archivo alterado: alerta y última copia válida conservada.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-02.

#### Paso 199 · R-02.03

Restaurar desde cada destino mediante staging local privado y referencia de hash confiable.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-02.

#### Paso 200 · R-02.04

Mantener USB en el alcance final mientras no haya decisión expresa de aplazamiento; documentar D6 sin recortar silenciosamente.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-02.

#### Paso 201 · R-02.05

Cerrar «Destinos USB y UNC con copia local previa y tolerancia a fallos» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-02.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### R-03 · Backup cifrado de instalación y recuperación de material privado

**Situación conocida:** Dump de DB y ACL privadas no equivalen a backup cifrado portable de configuración, assets, certificados y claves.

**Cierre esperado:** Copia completa cifrada y recuperable en otro host con procedimiento/material independiente; ausencia de clave no provoca fallback inseguro.

**Dependencias del resultado:** F-02, F-05, W-03.

**Fuentes:** [docs/IMPLEMENTACION-REV4.md](../docs/IMPLEMENTACION-REV4.md) · [docs/DECISION-D2-CUSTODIA-CLAVE-TOTP.md](../docs/DECISION-D2-CUSTODIA-CLAVE-TOTP.md) · [docs/RECUPERACION-DESPLIEGUE-WINDOWS-S1.md](../docs/RECUPERACION-DESPLIEGUE-WINDOWS-S1.md).

#### Paso 202 · R-03.01

Definir manifiesto de recuperación de datos/roles/configuración/assets/certificados y referencias de claves; separar material de recuperación y paquete público.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-03.

#### Paso 203 · R-03.02

Cifrar y autenticar backup con clave recuperable y parámetros versionados; fallo explícito por clave errónea o integridad alterada.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-03.

#### Paso 204 · R-03.03

Integrar la protecciónSQL de F-02 y sobreTOTP de F-05; reutilizar sus resultados sin desarrollar otro cifrado para lo mismo.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-03.

#### Paso 205 · R-03.04

Ensayar acceso mínimo, diagnóstico saneado y recuperación en otro Windows/SID, sin copiar secretos ligados al host antiguo como solución.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-03.

#### Paso 206 · R-03.05

Cerrar «Backup cifrado de instalación y recuperación de material privado» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-03.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### R-04 · Recuperación completa en otro Windows y activación controlada

**Situación conocida:** Restore43-&gt;43 y 15-&gt;43 en laboratorio nuevo conserva inventario/UUID y revoca sesiones. D11 New y su backup posterior funcionan. Falta recuperacion integral en otro Windows con MFA/SID/HTTPS/reinicio y RTO; no ensayarla sobre D conservada.

**Cierre esperado:** Servicio recuperado completo y operativo en otro host con identidad nueva, integridad y revocación comprobadas; origen conservado.

**Dependencias del resultado:** R-03, W-03.

**Fuentes:** [evidence/s1-20261102/vm11-d/RESULTADOS.md](../evidence/s1-20261102/vm11-d/RESULTADOS.md) · [evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md](../evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md) · [evidence/s1-20261102/windows43/RESULTADOS.md](../evidence/s1-20261102/windows43/RESULTADOS.md).

#### Paso 207 · R-04.01

Restaurar en VM limpia con base/roles/claves/identidad nuevos, usando backup de confianza; conservar origen sin sobrescribirlo.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-04.

#### Paso 208 · R-04.02

Verificar conteos, referencias, grupos/permisos, assets, configuración y acceso; demostrar cookies/desafíos anteriores revocados y MFA recuperable.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-04.

#### Paso 209 · R-04.03

Resolver frescura del backup y cambio de servicio/URL con origen quieto; declarar qué ocurre con escrituras posteriores al snapshot.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-04.

#### Paso 210 · R-04.04

Comprobar HTTPS, login, escritura, segunda sesión, backup nuevo y reinicio real del recuperado; medir tiempo de recuperación.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-04.

#### Paso 211 · R-04.05

Cerrar «Recuperación completa en otro Windows y activación controlada» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-04.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### R-05 · Actualización y rollback compatibles con datos posteriores

**Situación conocida:** Hay migraciónSQL y ensayos de copias/retornos privados. No es actualización en sitio probada del servicio ni retorno libre después de nuevas escrituras.

**Cierre esperado:** Upgrade y fallos con vuelta compatible comprobados en instalación real, sin perder escrituras ni seleccionar binarios incompatibles.

**Dependencias del resultado:** R-04, E-01.

**Fuentes:** [docs/RECUPERACION-DESPLIEGUE-WINDOWS-S1.md](../docs/RECUPERACION-DESPLIEGUE-WINDOWS-S1.md) · [docs/CONTRATO-SERVIDOR-v0.1.md](../docs/CONTRATO-SERVIDOR-v0.1.md) · [docs/REVISION-D14-05-CODEX.md](../docs/REVISION-D14-05-CODEX.md).

#### Paso 212 · R-05.01

Definir recorrido de actualización identificado con backup previo y versiones/esquemas compatibles.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-05.

#### Paso 213 · R-05.02

Ensayar fallo antes/durante/después de migración y publicación; mantener estado inequívoco y último conjunto recuperable.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-05.

#### Paso 214 · R-05.03

Restaurar a base nueva cuando el esquema no permita binario antiguo; no sustituir sólo DLL sobre DB nueva.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-05.

#### Paso 215 · R-05.04

Probar que actividad/escrituras posteriores impiden rollback silencioso; conmutación y necesidad de recuperación quedan explícitas.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-05.

#### Paso 216 · R-05.05

Cerrar «Actualización y rollback compatibles con datos posteriores» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-05.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### R-06 · Reset y recuperación administrativa delimitados

**Situación conocida:** Limpieza local de inventario D explicitamente autorizada y revisada: preview, dryrun, commit, auditoria y seguridad preservada. No equivale a reset completo de instancia, nueva base/roles ni emergencia MFA.

**Cierre esperado:** Reset acotado y recuperación de acceso operativos y documentados; cancelar no modifica datos ni deja acceso omitido.

**Dependencias del resultado:** F-09, W-05.

**Fuentes:** [evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md](../evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md).

#### Paso 217 · R-06.01

Ensayar reinicio de laboratorio sólo sobre GUID elegido con base/roles/secretos/admin nuevos, sin tocar Windows ni otras bases.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-06.

#### Paso 218 · R-06.02

Cancelar y repetir exigen confirmar otra vez el destino; conservar datos/cuentas/SID atribuidos y un informe recuperable.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-06.

#### Paso 219 · R-06.03

Integrar el procedimiento de emergencia de F-09 con último administrador, revocación de sesiones/desafíos y auditoría.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-06.

#### Paso 220 · R-06.04

Comprobar manual y canales privados para volver a acceder sin credencial universal ni extracción de secretos a logs.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-06.

#### Paso 221 · R-06.05

Cerrar «Reset y recuperación administrativa delimitados» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: R-06.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

## E · Paquete, manual, rendimiento y aceptación

### E-01 · Candidata final única con fuentes y componentes compatibles

**Situación conocida:** Candidata11/esquema 43 identificada e instalada, mas cargador 02 separado revisado. Falta integrar los pendientes restantes y ese parche en la futura entrega final unica; no reconstruir por cambios solo documentales ni tocar D.

**Cierre esperado:** Una sola candidata completa trazable y coherente, sin depender de archivos de entregas anteriores ni aceptar una mezcla no revisada.

**Dependencias del resultado:** W-01, I-01, F-11.

**Fuentes:** [evidence/s1-20261102/vm11-d/RESULTADOS.md](../evidence/s1-20261102/vm11-d/RESULTADOS.md) · [evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md](../evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md).

#### Paso 222 · E-01.01

Preparar la futura candidata final con los pendientes resueltos y cargador 02 integrado, reutilizando procedencia y bytes revisados. No reconstruir por esta lista documental.

- Tipo de trabajo: Conciliar evidencia existente.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-01.
- Texto histórico trazable: Seleccionar fuentes revisadas de MFA/C2/GUI/operadores, con manifiesto de procedencia; conservar candidatas históricas sin mezclarlas.

#### Paso 223 · E-01.02

Preparar la futura candidata final con los pendientes resueltos y cargador 02 integrado, reutilizando procedencia y bytes revisados. No reconstruir por esta lista documental.

- Tipo de trabajo: Conciliar evidencia existente.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-01.
- Texto histórico trazable: Integrar componentes estables y construir una vez el conjunto coordinado; evitar otro build o ZIP por una corrección sólo documental.

#### Paso 224 · E-01.03

Comprobar rutas/DTO/esquema/recursoslocales, app/bundle/payload/wrapper/CMD y sus pins; sin fuentes/secretos/diagnósticos privados en entrega.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-01.

#### Paso 225 · E-01.04

Congelar versión/hashes/inventario y repetir sólo regresión pertinente tras cambios; asociar QA y manual a esos mismos bytes.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-01.

#### Paso 226 · E-01.05

Cerrar «Candidata final única con fuentes y componentes compatibles» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-01.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### E-02 · Aprovisionamiento y construcción repetibles desde fuentes oficiales

**Situación conocida:** SDK/PG/frontend están fijados y los generadores existen. Las copiasS1/S2/S3 dependen de herramientas/artefactos y hardlinks de.local.

**Cierre esperado:** Otra persona puede reproducir la candidata mediante el procedimiento y entradas pinadas, sin copiar.local del desarrollador.

**Dependencias del resultado:** E-01.

**Fuentes:** [docs/REVISION-INSTALADOR14-06-CODEX.md](../docs/REVISION-INSTALADOR14-06-CODEX.md) · [docs/REVISION-D14-05-CODEX.md](../docs/REVISION-D14-05-CODEX.md) · [development/toolchain.lock.json](../development/toolchain.lock.json).

#### Paso 227 · E-02.01

Documentar y automatizar obtención oficial y verificación de SDK fijado, PostgreSQL17, frontend, runtime yCRT; sin cambiar pins silenciosamente.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-02.

#### Paso 228 · E-02.02

Construir desde checkout/entorno nuevo con locks, sin rutas privadas preexistentes ni fuentes contaminadas por trabajo paralelo.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-02.

#### Paso 229 · E-02.03

Comprobar hashes de contenidos/manifiestos y reproducibilidad declarada; explicar PDB/rutas y diferencias no deterministas.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-02.

#### Paso 230 · E-02.04

Producir distribución, bundle e instalador con comandos públicos completos; un cliente navegador no instala SDK/Node/DB.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-02.

#### Paso 231 · E-02.05

Cerrar «Aprovisionamiento y construcción repetibles desde fuentes oficiales» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-02.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### E-03 · Inventario de dependencias, avisos y redistribución

**Situación conocida:** AvisoMIT completo de Otp.NET ya incorporado. La revisión general de redistribución sigue abierta; no falta añadir de nuevo ese aviso.

**Cierre esperado:** Manifiesto y avisos completos, condiciones aplicables documentadas y cuestiones de redistribución resueltas.

**Dependencias del resultado:** E-01.

**Fuentes:** [docs/REVISION-BUNDLE14-02-CODEX.md](../docs/REVISION-BUNDLE14-02-CODEX.md) · [docs/REVISION-INSTALADOR14-06-CODEX.md](../docs/REVISION-INSTALADOR14-06-CODEX.md) · [development/offline-bundle14.sources.json](../development/offline-bundle14.sources.json).

#### Paso 232 · E-03.01

Inventariar componentes exactos de app/runtime/PG/CRT/frontend/fuentes y origen/hash/versión/licencia de cada uno.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-03.

#### Paso 233 · E-03.02

Contrastar avisos y condiciones de redistribución con sus fuentes/licencias oficiales; distinguir tener un aviso de tener todo el permiso resuelto.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-03.

#### Paso 234 · E-03.03

Resolver ausencias/condiciones y conservar decisiones; no publicar o redistribuir como entrega final antes de cerrar los puntos reales.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-03.

#### Paso 235 · E-03.04

Verificar contenido final e informe de vulnerabilidades conocido para las versiones seleccionadas, sin cambios de versión silenciosos.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-03.

#### Paso 236 · E-03.05

Cerrar «Inventario de dependencias, avisos y redistribución» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-03.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### E-04 · Manual autónomo de instalación, uso y operación

**Situación conocida:** Manual11 con pasos00-07, acceso privado y guias D/cargador 02 disponibles y usados en ensayo. Faltan manual completo del producto, idiomas/capturas y recorridos futuros de recuperacion/importacion/operacion; no empezar otro manual desde cero.

**Cierre esperado:** El recorrido completo funciona siguiendo sólo manual+paquete final, sin pedir archivos antiguos ni instrucciones ocultas.

**Dependencias del resultado:** E-01, R-04.

**Fuentes:** [docs/INSTALADOR11-WINDOWS43.md](../docs/INSTALADOR11-WINDOWS43.md) · [docs/INSTALADOR11-WINDOWS43.html](../docs/INSTALADOR11-WINDOWS43.html) · [evidence/s1-20261102/windows43/RESULTADOS.md](../evidence/s1-20261102/windows43/RESULTADOS.md) · [evidence/s1-20261102/vm11-d/RESULTADOS.md](../evidence/s1-20261102/vm11-d/RESULTADOS.md) · [evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md](../evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md) · [docs/VM11-D-PASOS-QA.md](../docs/VM11-D-PASOS-QA.md) · [docs/INSTALADOR14-SQL-PROTEGIDO.md](../docs/INSTALADOR14-SQL-PROTEGIDO.md).

#### Paso 237 · E-04.01

Completar el manual de producto partiendo del manual11 y pasos D/cargador 02 existentes; conservar carpetas/botones y no empezar de cero.

- Tipo de trabajo: Conciliar evidencia existente.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-04.
- Texto histórico trazable: Escribir pasos00→último: requisitos/cuentas/instalación/certificados/navegador/primerloginMFA, con ubicaciones y botones exactos para Wascar.

#### Paso 238 · E-04.02

Documentar usuarios/grupos/permisos, Click-Click, guardado/conflictos, import/export, informes y límites de Dosen/Undo.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-04.

#### Paso 239 · E-04.03

Incluir credenciales mediante acceso privado local por instancia, nunca contraseñas en manual/ZIP público; explicar conexiónSQL autorizada y mínimo privilegio.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-04.

#### Paso 240 · E-04.04

Incluir red casa/trabajo, backup/retención/USB/UNC, restore, upgrade/rollback, emergenciaMFA, diagnóstico y recuperación.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-04.

#### Paso 241 · E-04.05

Seguir el manual desde un host nuevo y corregir cada paso implícito; capturas reales y vocabulario de GUI EN/DE/ES sin traducir nombres del usuario.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-04.

#### Paso 242 · E-04.06

Cerrar «Manual autónomo de instalación, uso y operación» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-04.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### E-05 · QA manual por módulos sobre candidata identificada

**Situación conocida:** D11 y Demo50 estan disponibles. HojaQA11 de 14 casos,167 casos totales, export/import y observaciones preservadas. Wascar expresa satisfaccion general, pero no sustituye resultados por caso/rol/version. Faltan cuentas diferenciadas y QA por modulos; no trasladar PASS historicos.

**Cierre esperado:** Casos críticos y recorridos pactados tienen resultados atribuibles; ningún resultado del usuario sobrescrito ni aprobado por el desarrollador.

**Dependencias del resultado:** E-01, W-06.

**Fuentes:** [docs/QA-CIERRE-CANDIDATA11.md](../docs/QA-CIERRE-CANDIDATA11.md) · [evidence/s1-20261102/qa-cierre11/RESULTADOS.md](../evidence/s1-20261102/qa-cierre11/RESULTADOS.md) · [docs/QA-CASOS-WASCAR.json](../docs/QA-CASOS-WASCAR.json) · [evidence/s1-20261102/vm11-d/RESULTADOS.md](../evidence/s1-20261102/vm11-d/RESULTADOS.md) · [evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md](../evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md).

#### Paso 243 · E-05.01

Completar QA por modulo/rol/version reutilizando catalogo 167 y hoja11 de 14 casos. Conservar resultados y repetir solo casos afectados; satisfaccion general no rellena Pass individuales.

- Tipo de trabajo: Conciliar evidencia existente.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-05.
- Texto histórico trazable: Vincular casos disponibles a build/hash, rol y ámbito reales; actualizar pasos exactos y resultado esperado, sin habilitar por código de desarrollo.

#### Paso 244 · E-05.02

Completar QA por modulo/rol/version reutilizando catalogo 167 y hoja11 de 14 casos. Conservar resultados y repetir solo casos afectados; satisfaccion general no rellena Pass individuales.

- Tipo de trabajo: Conciliar evidencia existente.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-05.
- Texto histórico trazable: Conciliar resultados antiguos por fecha/versión y pedir sólo repetición afectada; conservar Pass/NotPass/observaciones originales y su exportJSON.

#### Paso 245 · E-05.03

Preparar cuentas ficticias administrador/técnico/lector con ámbitos distintos y acceso privado, y sesiones de navegador separadas.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-05.

#### Paso 246 · E-05.04

Completar QA por modulo/rol/version reutilizando catalogo 167 y hoja11 de 14 casos. Conservar resultados y repetir solo casos afectados; satisfaccion general no rellena Pass individuales.

- Tipo de trabajo: Conciliar evidencia existente.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-05.
- Texto histórico trazable: Ofrecer guiones pequeños por módulo para una sola persona; registrar fallos/bloqueos porID y confirmar correcciones con prueba concreta.

#### Paso 247 · E-05.05

Cerrar «QA manual por módulos sobre candidata identificada» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-05.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### E-06 · Medir carga real de diez usuarios y demo completa

**Situación conocida:** Demo50 y prueba de diez actores/ambitos ya realizados en laboratorio con umbrales de humo previos. D11 carga50/2553 comandos verificada en 185.681 s y backup posterior completo; MFA/TLS del cargador probado aparte en cuenta sintetica. Faltan carga extendida instalada, memoria/CPU/consultas/picos/recuperacion y aceptacion practica, no crear de nuevo la demo.

**Cierre esperado:** Informe reproducibleS-48 demuestra datos consistentes y comportamiento aceptable con carga declarada; regresiones medidas resueltas.

**Dependencias del resultado:** E-01, W-03.

**Fuentes:** [docs/PLAN-LABORATORIO-50-CLIENTES.md](../docs/PLAN-LABORATORIO-50-CLIENTES.md) · [docs/LABORATORIO-50-CLIENTES.md](../docs/LABORATORIO-50-CLIENTES.md) · [evidence/s1-20261102/demo50/RESULTADOS.md](../evidence/s1-20261102/demo50/RESULTADOS.md) · [evidence/s1-20261102/windows43/demo/RESULTADOS.md](../evidence/s1-20261102/windows43/demo/RESULTADOS.md) · [evidence/s1-20261102/vm11-d/RESULTADOS.md](../evidence/s1-20261102/vm11-d/RESULTADOS.md) · [evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md](../evidence/s1-20261102/demo50-auth-diagnostic/RESULTADOS.md).

#### Paso 248 · E-06.01

Reutilizar Demo50 instalada y el ensayo de diez actores ya realizado; completar sesiones/roles para la carga extendida cuando se elija, en entorno separado.

- Tipo de trabajo: Conciliar evidencia existente.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-06.
- Texto histórico trazable: Preparar demo sintética prevista y diez sesiones autorizadas, combinando lectura/escritura/conflictos con ámbitos y roles.

#### Paso 249 · E-06.02

Completar carga extendida instalada, consultas/CPU/memoria/picos y recuperacion usando el ensayo local y umbrales de humo previos como antecedente; no venderlos como SLA.

- Tipo de trabajo: Conciliar evidencia existente.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-06.
- Texto histórico trazable: Medir latencias por operación, errores/conflictos, memoria/CPU y consultas durante carga y recuperación; registrar entorno/duración.

#### Paso 250 · E-06.03

Completar carga extendida instalada, consultas/CPU/memoria/picos y recuperacion usando el ensayo local y umbrales de humo previos como antecedente; no venderlos como SLA.

- Tipo de trabajo: Conciliar evidencia existente.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-06.
- Texto histórico trazable: Definir antes del ensayo los umbrales de aceptación prácticos y documentar límites; no inventar garantías de producción.

#### Paso 251 · E-06.04

Corregir sólo problemas medidos y repetir el foco; no introducir Redis/índices/caché de permisos por suposición.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-06.

#### Paso 252 · E-06.05

Cerrar «Medir carga real de diez usuarios y demo completa» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-06.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

### E-07 · Revisión final y adopción explícita de Wascar

**Situación conocida:** Servidor histórico funciona según Wascar, pero la entrega final nueva no está adoptada. No corresponde anunciar100% por generar un ZIP.

**Cierre esperado:** Conjunto final completo revisado, recorrido instalado/recuperado acreditado y confirmación de adopción de Wascar registrada.

**Dependencias del resultado:** E-03, E-04, E-05, E-06, R-04.

**Fuentes:** [docs/ACEPTACION.md](../docs/ACEPTACION.md) · [docs/CONTRATO-SERVIDOR-v0.1.md](../docs/CONTRATO-SERVIDOR-v0.1.md) · [docs/CONTINUIDAD-CODEX.md](../docs/CONTINUIDAD-CODEX.md).

#### Paso 253 · E-07.01

Conciliar los 55 criterios S1–S4 y requisitos producto de revisión 4 con evidencia, límites y casos pendientes; S-50 queda en S5.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-07.
- Texto histórico trazable: Conciliar los55 criteriosS1–S4 y requisitos producto de revisión4 con evidencia, límites y casos pendientes; S-50 queda enS5.

#### Paso 254 · E-07.02

Cerrar defectos bloqueantes y revisar seguridad/contenido/recuperación del mismo conjunto final, reutilizando pruebas válidas no afectadas.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-07.

#### Paso 255 · E-07.03

Entregar paquete/manual/evidencias/hashes y recuperación; registrar aceptación o excepciones explícitas de Wascar.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-07.

#### Paso 256 · E-07.04

Dejar lista separada de roadmap, soporte y decisiones futuras, sin convertir propuestas no aprobadas en cierre alcanzado.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-07.

#### Paso 257 · E-07.05

Cerrar «Revisión final y adopción explícita de Wascar» con evidencia, revisión independiente y aceptación manual cuando corresponda.

- Tipo de trabajo: Contrastar cierre; puede existir implementación.
- Estado formal: pending; ámbito: Primera entrega; responsable: E-07.
- Texto histórico trazable: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda.

## C · Catálogo: aceptación y mantenimiento

### C-HW-01 · Cerrar procedencia/licencias del catalogo seleccionado

**Situación conocida:** investigacion_entregada_no_plantillas_integradas. Conservar12.008 definiciones/144 racks/195 registros primarios con su procedencia y límites.

**Cierre esperado:** Fuentes, versiones y limites publicados en inventario, enlazados a E-03; sin asumir permiso sobre fotografias.

**Dependencias del resultado:** Sin dependencia previa declarada; contrastar antes de ejecutar..

**Fuentes:** [docs/ALCANCE-CATALOGO-FABRICANTES.md](../docs/ALCANCE-CATALOGO-FABRICANTES.md).

#### Paso 258 · C-HW-01

Revisar fuentes y decisiones de reutilizacion de los 506 existentes; no integrar las 12.008 definiciones investigadas por defecto.

- Tipo de trabajo: Conciliar, aceptar o mantener lo existente.
- Estado formal: not_scored; ámbito: Catálogo; responsable: E-03.
- Sin peso nuevo. Ligado al resultado responsable; no suma por separado.

### C-HW-02 · Cerrar contrato fisico y variantes pendientes de aceptacion

**Situación conocida:** selección de 506_instalada_D11_y_demo50_verificada_cierre_QA_reservas_pendiente. 506/506 seleccionados integrados en 43,868 revisiones/861 comerciales. New11/postboot y Demo50 verificados en D. Conservar modelos/contratos/selector; cerrar QA, reservas explicitadas, derechos/versionado y mantenimiento sin ampliar otra vez la seleccion.

**Cierre esperado:** Contrato y reservas contrastados, compatibilidad documentada y revision distinta; no se repite la autoria de 506.

**Dependencias del resultado:** Sin dependencia previa declarada; contrastar antes de ejecutar..

**Fuentes:** [docs/ALCANCE-CATALOGO-FABRICANTES.md](../docs/ALCANCE-CATALOGO-FABRICANTES.md).

#### Paso 259 · C-HW-02

Reutilizar contrato 43/montajes/IDs existentes; revisar reservas de BOM, poblacion, dimensiones y conectores sin inventar puertos.

- Tipo de trabajo: Conciliar, aceptar o mantener lo existente.
- Estado formal: not_scored; ámbito: Catálogo; responsable: I-03.
- Sin peso nuevo. Ligado al resultado responsable; no suma por separado.

### C-HW-03 · Aceptar la selección de 506 que ya esta integrada

**Situación conocida:** selección de 506_instalada_D11_y_demo50_verificada_cierre_QA_reservas_pendiente. 506/506 seleccionados integrados en 43,868 revisiones/861 comerciales. New11/postboot y Demo50 verificados en D. Conservar modelos/contratos/selector; cerrar QA, reservas explicitadas, derechos/versionado y mantenimiento sin ampliar otra vez la seleccion.

**Cierre esperado:** Lista seleccionada trazable y aceptada; no se exige incorporar modelos fuera de esa seleccion.

**Dependencias del resultado:** Sin dependencia previa declarada; contrastar antes de ejecutar..

**Fuentes:** [docs/ALCANCE-CATALOGO-FABRICANTES.md](../docs/ALCANCE-CATALOGO-FABRICANTES.md).

#### Paso 260 · C-HW-03

Conciliar censo 506/506, 868 revisiones y 861 modelos comerciales, excluyendo variantes auxiliares y no aplicables del conteo.

- Tipo de trabajo: Conciliar, aceptar o mantener lo existente.
- Estado formal: not_scored; ámbito: Catálogo; responsable: I-04.
- Sin peso nuevo. Ligado al resultado responsable; no suma por separado.

### C-HW-04 · Cerrar QA del selector y de las caras interactivas

**Situación conocida:** selección de 506_instalada_D11_y_demo50_verificada_cierre_QA_reservas_pendiente. 506/506 seleccionados integrados en 43,868 revisiones/861 comerciales. New11/postboot y Demo50 verificados en D. Conservar modelos/contratos/selector; cerrar QA, reservas explicitadas, derechos/versionado y mantenimiento sin ampliar otra vez la seleccion.

**Cierre esperado:** QA y reservas registradas sin lista larga, perdida de identidad ni foto pegada que anule puertos.

**Dependencias del resultado:** Sin dependencia previa declarada; contrastar antes de ejecutar..

**Fuentes:** [docs/ALCANCE-CATALOGO-FABRICANTES.md](../docs/ALCANCE-CATALOGO-FABRICANTES.md).

#### Paso 261 · C-HW-04

Probar busqueda/alias/teclado, seleccion de revision/montaje, frontal/trasera y conexiones sobre los perfiles existentes.

- Tipo de trabajo: Conciliar, aceptar o mantener lo existente.
- Estado formal: not_scored; ámbito: Catálogo; responsable: P-08.
- Sin peso nuevo. Ligado al resultado responsable; no suma por separado.

### C-HW-05 · Cerrar cobertura y reservas del catalogo por familias

**Situación conocida:** selección de 506_instalada_D11_y_demo50_verificada_cierre_QA_reservas_pendiente. 506/506 seleccionados integrados en 43,868 revisiones/861 comerciales. New11/postboot y Demo50 verificados en D. Conservar modelos/contratos/selector; cerrar QA, reservas explicitadas, derechos/versionado y mantenimiento sin ampliar otra vez la seleccion.

**Cierre esperado:** Cobertura/NA/reservas explicitas y revision independiente; no afirmar conexion manual de todas las bocas.

**Dependencias del resultado:** Sin dependencia previa declarada; contrastar antes de ejecutar..

**Fuentes:** [docs/ALCANCE-CATALOGO-FABRICANTES.md](../docs/ALCANCE-CATALOGO-FABRICANTES.md).

#### Paso 262 · C-HW-05

Reutilizar pruebas por grupo y Demo50; elegir muestras/variantes y defectos pendientes de QA sin ejecutar una nueva prueba rutinaria por cada modelo.

- Tipo de trabajo: Conciliar, aceptar o mantener lo existente.
- Estado formal: not_scored; ámbito: Catálogo; responsable: E-05.
- Sin peso nuevo. Ligado al resultado responsable; no suma por separado.

### C-HW-06 · Incluir el catalogo validado en la entrega final mantenible

**Situación conocida:** selección de 506_instalada_D11_y_demo50_verificada_cierre_QA_reservas_pendiente. 506/506 seleccionados integrados en 43,868 revisiones/861 comerciales. New11/postboot y Demo50 verificados en D. Conservar modelos/contratos/selector; cerrar QA, reservas explicitadas, derechos/versionado y mantenimiento sin ampliar otra vez la seleccion.

**Cierre esperado:** Candidata final trazable y compatible, sin actualizar D por esta tarea documental.

**Dependencias del resultado:** Sin dependencia previa declarada; contrastar antes de ejecutar..

**Fuentes:** [docs/ALCANCE-CATALOGO-FABRICANTES.md](../docs/ALCANCE-CATALOGO-FABRICANTES.md).

#### Paso 263 · C-HW-06

Conservar la instalación 43/11 ya demostrada; completar compatibilidad/versionado/update/rollback y derechos del paquete final.

- Tipo de trabajo: Conciliar, aceptar o mantener lo existente.
- Estado formal: not_scored; ámbito: Catálogo; responsable: E-01.
- Sin peso nuevo. Ligado al resultado responsable; no suma por separado.

### C-HW-07 · Dejar definido mantenimiento y ampliaciones futuras

**Situación conocida:** selección de 506_instalada_D11_y_demo50_verificada_cierre_QA_reservas_pendiente. 506/506 seleccionados integrados en 43,868 revisiones/861 comerciales. New11/postboot y Demo50 verificados en D. Conservar modelos/contratos/selector; cerrar QA, reservas explicitadas, derechos/versionado y mantenimiento sin ampliar otra vez la seleccion.

**Cierre esperado:** Metodo reutilizable, cola y criterio de soporte actualizados; los 506 no vuelven a contarse como pendientes.

**Dependencias del resultado:** Sin dependencia previa declarada; contrastar antes de ejecutar..

**Fuentes:** [docs/ALCANCE-CATALOGO-FABRICANTES.md](../docs/ALCANCE-CATALOGO-FABRICANTES.md).

#### Paso 264 · C-HW-07

Documentar como revisar nuevas familias/SKU y corregir fuentes; ampliar mas alla de 506 solo como lote nuevo acordado.

- Tipo de trabajo: Conciliar, aceptar o mantener lo existente.
- Estado formal: not_scored; ámbito: Catálogo; responsable: E-04.
- Sin peso nuevo. Ligado al resultado responsable; no suma por separado.

## FUT · Evolución posterior a la primera entrega

### FUT-01 · Diseno posterior de descubrimiento SNMP/LLDP/API

**Situación conocida:** evolucion_posterior. Evaluar SNMPv3, LLDP/CDP y API/LibreNMS/Netdisco/GLPI/Lansweeper; observaciones separadas de documentación y aprobación de cambios. Sin escanear redes ni deducir cableado pasivo.

**Cierre esperado:** Propuesta con compatibilidad/licencias/seguridad, pilotos autorizados y limites del cableado pasivo; no escanear la red por esta lista.

**Dependencias del resultado:** Sin dependencia previa declarada; contrastar antes de ejecutar..

**Fuentes:** [docs/PROTOCOLO-REUNION-EVOLUCION-FUTURA-25-10-2026.md](../docs/PROTOCOLO-REUNION-EVOLUCION-FUTURA-25-10-2026.md).

#### Paso 265 · FUT-01

Evaluar protocolos/proveedores/colectores, credenciales minimas, modelos observados y aprobacion antes de cambiar documentacion.

- Tipo de trabajo: Plan posterior; no bloquea la primera entrega.
- Estado formal: not_scored; ámbito: Posterior; responsable: FUT-01.
- Sin peso nuevo. Fuera de la primera entrega.

### FUT-02 · Paquetes de trabajo de campo offline S5

**Situación conocida:** S5_posterior. Paquetes por cliente/revisión/capacidad, sin secretos de sesión; merge de cambios, conflictos, transacción e idempotencia. No confundir con importar JSON normal.

**Cierre esperado:** Contrato y pruebas de retorno aprobados en lote posterior; no confundir con importacion JSON ordinaria.

**Dependencias del resultado:** Sin dependencia previa declarada; contrastar antes de ejecutar..

**Fuentes:** [docs/PLAN-CIERRE-RACKCLICK.json](../docs/PLAN-CIERRE-RACKCLICK.json).

#### Paso 266 · FUT-02

Definir export por cliente/revision/capacidad, trabajo offline y retorno con conflicto/merge, idempotencia y atomicidad sin secretos de sesion.

- Tipo de trabajo: Plan posterior; no bloquea la primera entrega.
- Estado formal: not_scored; ámbito: Posterior; responsable: FUT-02.
- Sin peso nuevo. Fuera de la primera entrega.

### FUT-03 · Federacion real AD/OIDC y grupos externos

**Situación conocida:** fuera_de_primera_entrega. Sólo si se incorpora esa ampliación: vinculación de identidad, grupos, revocación y fallback. La presentación tipo Entra no implica implementar un forest/GPO.

**Cierre esperado:** Decision/contrato y pruebas de identidad en alcance posterior; apariencia tipo Entra no implica forest/GPO.

**Dependencias del resultado:** Sin dependencia previa declarada; contrastar antes de ejecutar..

**Fuentes:** [docs/PLAN-CIERRE-RACKCLICK.json](../docs/PLAN-CIERRE-RACKCLICK.json).

#### Paso 267 · FUT-03

Definir proveedores, vinculacion de cuentas, grupos, revocacion y fallback cuando se incorpore esta ampliacion.

- Tipo de trabajo: Plan posterior; no bloquea la primera entrega.
- Estado formal: not_scored; ámbito: Posterior; responsable: FUT-03.
- Sin peso nuevo. Fuera de la primera entrega.

## OPS · Repositorio privado y mantenimiento

### OPS-01 · Actualizar el repositorio privado con una seleccion revisada

**Situación conocida:** actualizacion30_fuentes_demo_y_manual_verificados. Repositorio was-car/RackClick privado. Actualizacion seleccionada de fuentes congeladas de candidata10, inventario sintetico original sin seguridad, guia de fuentes oficiales y arranque de laboratorio reproducible. Sin binarios del instalador por condiciones de redistribucion abiertas; sin despliegue en QA. No puntua el cierre de producto por publicar codigo.

**Cierre esperado:** Publicacion privada verificable, sin arbol concurrente/credenciales/dumps ni binarios pendientes de redistribucion; no suma puntos por publicar.

**Dependencias del resultado:** Sin dependencia previa declarada; contrastar antes de ejecutar..

**Fuentes:** [docs/PUBLICACION-GITHUB-30-10-2026.md](../docs/PUBLICACION-GITHUB-30-10-2026.md).

#### Paso 268 · OPS-01

Preparar fuentes aceptadas, inventario sintetico sin seguridad y manuales en clon separado; revisar secretos/licencias y actualizar solo el repositorio privado autorizado.

- Tipo de trabajo: Conciliar, aceptar o mantener lo existente.
- Estado formal: not_scored; ámbito: Mantenimiento; responsable: E-01.
- Sin peso nuevo. Ligado al resultado responsable; no suma por separado.

## Apéndice A · Todas las acciones RC10, sin duplicar puntos

Clasificación de la comparación del 29.10.2026; «ausente» o «parcial» no son un diagnóstico actualizado. Antes de programar se contrasta el servidor y la evidencia actual. Cada fila conserva acción, trabajo previsto, aceptación y responsable. Puedes pedir un PAR concreto además del número principal.

| ID | Área y acción | Contraste histórico | Trabajo previsto / decisión | Aceptación | Responsable y pasos |
|---|---|---|---|---|---|
| PAR-001 / O-001 | Navegación: Abrir inicio de clientes | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | I-04: 64, 65 |
| PAR-002 / O-002 | Navegación: Abrir cliente | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | I-04: 64, 65 |
| PAR-003 / O-003 | Navegación: Abrir inventario sin asignar | adaptacion_servidor | Declarar esta diferencia de modelo y definir destino de inventario legacy en importación; no presentar Sin sala como equivalente completo a Sin cliente.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | I-04: 64, 65 |
| PAR-004 / O-004 | Navegación: Abrir rack | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | I-04: 64, 65 |
| PAR-005 / O-005 | Navegación: Volver al proyecto del cliente | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | I-04: 64, 65 |
| PAR-006 / O-006 | Navegación: Mostrar u ocultar navegación móvil | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | I-04: 64, 65 |
| PAR-007 / O-007 | Navegación: Consultar ruta jerárquica | parcial | Verificar legibilidad y completar ruta visible hasta sede/edificio/sala/rack donde la aceptación requiera esa miga.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | I-04: 64, 65 |
| PAR-008 / O-008 | Navegación: Abrir ajustes | adaptacion_servidor | Validar que todos los ajustes disponibles se encuentren y documentar entradas separadas.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | I-04: 64, 65 |
| PAR-009 / O-009 | Navegación: Cerrar ajustes | parcial | Confirmar aceptación de ajustes inline y cierre accesible de las secciones modales.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | I-04: 64, 65 |
| PAR-010 / O-010 | Ámbito: Listar clientes y sus totales | parcial | Añadir o decidir disponibilidad de totales por cliente con autorización y coste de consulta definidos.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | I-04: 64, 65 |
| PAR-011 / O-011 | Ámbito: Consultar resumen del cliente | parcial | Completar resumen del cliente o registrar diferencia de aceptación.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | I-04: 64, 65 |
| PAR-012 / O-012 | Ámbito: Conservar separación al operar cliente | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | I-04: 64, 65 |
| PAR-013 / O-013 | Systemhaus e infraestructura: Renombrar Systemhaus por diálogo | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | I-04: 64, 65 |
| PAR-014 / O-014 | Systemhaus e infraestructura: Editar Systemhaus desde ajustes | parcial | Mantener vía clara de renombrado y validar si se requiere también entrada desde ajustes.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | I-04: 64, 65 |
| PAR-015 / O-015 | Systemhaus e infraestructura: Abrir gestor de infraestructura | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | I-04: 64, 65 |
| PAR-016 / O-016 | Systemhaus e infraestructura: Editar campo Cliente de ubicación | parcial | Definir explícitamente la operación de reasignación entre clientes si forma parte de aceptación; no inferirla de renombrado ni move entre racks.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | I-04: 64, 65 |
| PAR-017 / O-017 | Systemhaus e infraestructura: Editar campo Sede de ubicación | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | I-04: 64, 65 |
| PAR-018 / O-018 | Systemhaus e infraestructura: Editar campo Edificio de ubicación | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | I-04: 64, 65 |
| PAR-019 / O-019 | Systemhaus e infraestructura: Editar campo Sala de ubicación | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | I-04: 64, 65 |
| PAR-020 / O-020 | Systemhaus e infraestructura: Añadir ubicación o cliente | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | I-04: 64, 65 |
| PAR-021 / O-021 | Systemhaus e infraestructura: Cargar ubicación para editar | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | I-04: 64, 65 |
| PAR-022 / O-022 | Systemhaus e infraestructura: Guardar cambio de ubicación | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | I-04: 64, 65 |
| PAR-023 / O-023 | Systemhaus e infraestructura: Eliminar ubicación desocupada | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | I-04: 64, 65 |
| PAR-024 / O-024 | Systemhaus e infraestructura: Asignar rack a ubicación | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | I-04: 64, 65 |
| PAR-025 / O-025 | Systemhaus e infraestructura: Quitar asignación de rack | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | I-04: 64, 65 |
| PAR-026 / O-026 | Systemhaus e infraestructura: Aplicar infraestructura | adaptacion_servidor | Conservar trazabilidad y validar cada recorrido de jerarquía; no anunciar atomicidad de varias ediciones independientes como una sola operación.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | I-04: 64, 65 |
| PAR-027 / O-027 | Systemhaus e infraestructura: Cancelar gestor de infraestructura | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | I-04: 64, 65 |
| PAR-028 / O-028 | Cliente y proyecto: Renombrar cliente o proyecto legacy | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | P-06: 132, 133, 134, 135, 136, 137 |
| PAR-029 / O-029 | Cliente y proyecto: Editar técnico documental | ausente | Diseñar/persistir metadato Técnico documental y reutilizarlo en informes, con alcance/permiso definidos.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | P-06: 132, 133, 134, 135, 136, 137 |
| PAR-030 / O-030 | Cliente y proyecto: Cargar logo de cliente | ausente | Implementar carga/validación/almacenamiento autorizado del logo y uso en reporte con política de imagen segura.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | P-06: 132, 133, 134, 135, 136, 137 |
| PAR-031 / O-031 | Cliente y proyecto: Quitar logo | ausente | Añadir eliminación de logo junto a su futuro contrato persistente.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | P-06: 132, 133, 134, 135, 136, 137 |
| PAR-032 / O-032 | Cliente y proyecto: Mostrar logo seguro en informe integrado | ausente | Integrar presentación segura del logo cuando exista captura/persistencia; probar formatos admitidos y nombres hostiles.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | P-06: 132, 133, 134, 135, 136, 137 |
| PAR-033 / O-033 | Cliente y proyecto: Crear proyecto vacío en ámbito activo | ausente | Definir si se conserva un reinicio completo del cliente, con preview, autorización y confirmación; no sustituirlo por borrados manuales. Preferir un destino/cliente nuevo o importación confirmada. No copiar un reset global que borre datos compartidos. | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | R-06: 217, 218, 219, 220, 221 |
| PAR-034 / O-034 | Cliente y proyecto: Consultar fecha de modificación | parcial | Presentar fecha de última modificación persistida si es requisito de ficha, sin confundirla con fecha de consulta.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | P-06: 132, 133, 134, 135, 136, 137 |
| PAR-035 / O-035 | Rack: Crear rack | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-036 / O-036 | Rack: Abrir propiedades del rack | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-037 / O-037 | Rack: Editar nombre del rack | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-038 / O-038 | Rack: Editar ubicación libre del rack | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-039 / O-039 | Rack: Elegir sugerencia de ubicación | ausente | Reponer sugerencias reutilizables de ubicación si la aceptación conserva ese control, diferenciándolas de la asignación relacional.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-040 / O-040 | Rack: Cambiar tamaño del rack | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-041 / O-041 | Rack: Guardar propiedades del rack | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-042 / O-042 | Rack: Cancelar propiedades del rack | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-043 / O-043 | Rack: Eliminar rack con confirmación | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-044 / O-044 | Rack: Duplicar rack con conexiones locales | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-045 / O-045 | Rack: Duplicar rack sin conexiones locales | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-046 / O-046 | Rack: Consultar capacidad y ocupación | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-047 / O-047 | Rack: Seleccionar cara frontal | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-048 / O-048 | Rack: Seleccionar cara trasera | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-049 / O-049 | Rack: Mostrar u ocultar cables físicos | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-050 / O-050 | Rack: Reducir zoom | ausente | Añadir controles de zoom accesibles con límites y exportación coherentes si se conserva el comportamiento RC10.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | P-11: 162, 163, 164, 165, 166, 167 |
| PAR-051 / O-051 | Rack: Aumentar zoom | ausente | Añadir controles de zoom accesibles con límites y exportación coherentes si se conserva el comportamiento RC10.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | P-11: 162, 163, 164, 165, 166, 167 |
| PAR-052 / O-052 | Rack: Restablecer zoom | ausente | Añadir controles de zoom accesibles con límites y exportación coherentes si se conserva el comportamiento RC10.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | P-11: 162, 163, 164, 165, 166, 167 |
| PAR-053 / O-053 | Rack: Mostrar advertencia de doble ocupación | parcial | Acreditar canal de staging/visualización para doble ocupación histórica; no declarar que el banner por sí solo demuestra conservación.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-054 / O-054 | Rack: Consultar tramo de cable fuera de cara o rack | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-055 / O-055 | Equipo: Abrir catálogo de equipos | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-056 / O-056 | Equipo: Cerrar catálogo | equivalente | Validar cierre/foco de catálogo y borrador de alta por separado.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-057 / O-057 | Equipo: Asignar nombre opcional antes de añadir plantilla | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-058 / O-058 | Catálogo y plantillas: Consultar catálogo por categorías | adaptacion_servidor | Contrastar contenido/hash y variantes AP fuera de rack; no inferir identidad sólo del número de presets.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | P-08: 144, 145, 146, 147, 148, 149 |
| PAR-059 / O-059 | Catálogo y plantillas: Crear equipo desde preset | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | P-08: 144, 145, 146, 147, 148, 149 |
| PAR-060 / O-060 | Catálogo y plantillas: Crear equipo desde favorito | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | P-08: 144, 145, 146, 147, 148, 149 |
| PAR-061 / O-061 | Catálogo y plantillas: Añadir favorito | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | P-08: 144, 145, 146, 147, 148, 149 |
| PAR-062 / O-062 | Catálogo y plantillas: Quitar favorito | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | P-08: 144, 145, 146, 147, 148, 149 |
| PAR-063 / O-063 | Catálogo y plantillas: Consultar favoritos guardados | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | P-08: 144, 145, 146, 147, 148, 149 |
| PAR-064 / O-064 | Catálogo y plantillas: Guardar equipo como plantilla | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | P-08: 144, 145, 146, 147, 148, 149 |
| PAR-065 / O-065 | Catálogo y plantillas: Crear equipo desde plantilla personal | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | P-08: 144, 145, 146, 147, 148, 149 |
| PAR-066 / O-066 | Catálogo y plantillas: Eliminar plantilla personal | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | P-08: 144, 145, 146, 147, 148, 149 |
| PAR-067 / O-067 | Catálogo y plantillas: Consultar plantillas guardadas | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | P-08: 144, 145, 146, 147, 148, 149 |
| PAR-068 / O-068 | Equipo personalizado: Desplegar creador personalizado | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-069 / O-069 | Equipo personalizado: Editar nombre personalizado | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-070 / O-070 | Equipo personalizado: Elegir altura personalizada | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-071 / O-071 | Equipo personalizado: Elegir icono personalizado | parcial | Conservar selección directa de icono en alta manual o documentar/aceptar el recorrido alternativo; no tratar edición de plantilla como el mismo control.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-072 / O-072 | Equipo personalizado: Añadir grupo inicial adicional | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-073 / O-073 | Equipo personalizado: Cambiar tipo de grupo nuevo | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-074 / O-074 | Equipo personalizado: Cambiar cantidad de grupo nuevo | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-075 / O-075 | Equipo personalizado: Configurar cara de grupo nuevo | parcial | Completar cara al definir grupo nuevo si se conserva ese flujo; alternativa requiere varias operaciones y debe aceptarse expresamente.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-076 / O-076 | Equipo personalizado: Quitar grupo nuevo | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-077 / O-077 | Equipo personalizado: Crear equipo personalizado | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-078 / O-078 | Equipo: Abrir editor de equipo | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-079 / O-079 | Equipo: Editar nombre de equipo | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-080 / O-080 | Equipo: Cambiar altura de equipo | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-081 / O-081 | Equipo: Desplegar selector de iconos | ausente | Añadir edición de icono de instancia o definir límite visible; editor de plantilla no cambia instancias existentes.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-082 / O-082 | Equipo: Elegir icono de equipo | ausente | Diseñar campo icon de instancia persistente con validación y conectar control; no confundirlo con S-220 de plantilla.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-083 / O-083 | Equipo: Editar presupuesto PoE | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-084 / O-084 | Equipo: Desplegar detalles técnicos | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-085 / O-085 | Equipo: Editar número de serie | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-086 / O-086 | Equipo: Editar dirección IP | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-087 / O-087 | Equipo: Editar modelo | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-088 / O-088 | Equipo: Editar firmware | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-089 / O-089 | Equipo: Editar notas libres | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-090 / O-090 | Equipo: Desplegar configuración de puertos | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-091 / O-091 | Equipo: Editar prefijo de puerto | parcial | Conservar edición del prefijo; corregir su uso en tooltip/inspector/cara física y probar visualmente varios grupos con gn repetido.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-092 / O-092 | Equipo: Añadir grupo a equipo existente | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-093 / O-093 | Equipo: Cambiar tipo de grupo existente | parcial | Decidir y exponer conversión de grupo con vista previa e impacto, respetando validación backend; no afirmar que el tipo es inmutable por política.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-094 / O-094 | Equipo: Aumentar cantidad de puertos | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-095 / O-095 | Equipo: Reducir cantidad de puertos | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-096 / O-096 | Equipo: Quitar grupo existente | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-097 / O-097 | Equipo: Guardar propiedades y grupos | parcial | Validar o aceptar separación de commits; si se exige una edición combinada, diseñar comando transaccional con impacto y borrador único.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-098 / O-098 | Equipo: Cancelar editor de equipo | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-099 / O-099 | Equipo: Eliminar equipo individual | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-100 / O-100 | Equipo: Subir equipo una posición | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-101 / O-101 | Equipo: Bajar equipo una posición | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-102 / O-102 | Equipo: Reordenar equipo con ratón | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-103 / O-103 | Equipo: Reordenar equipo táctil | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-104 / O-104 | Equipo: Seleccionar o deseleccionar equipo | parcial | Validar si la variante clásica de selección pertenece a aceptación; si sólo física, documentar checkbox equivalente.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-105 / O-105 | Equipo: Seleccionar todos los equipos | ausente | Añadir selección de todos con alcance visible y límite de lote 64, o declarar comportamiento parcial para racks grandes.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-106 / O-106 | Equipo: Limpiar selección de equipos | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-107 / O-107 | Equipo: Eliminar equipos seleccionados | adaptacion_servidor | Validar/añadir atajo Delete protegido frente a campos editables si se exige; conservar preview y límite real.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-108 / O-108 | Equipo: Plegar o desplegar interfaces | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-109 / O-109 | Equipo: Abrir opciones del equipo | parcial | Conectar menú contextual semántico o aceptar redistribución clara de plantilla, grupos y edición masiva; no anunciar menú completo equivalente.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-110 / O-110 | Equipo: Abrir opciones con pulsación larga | parcial | Verificar gesto táctil y alcance del menú contextual después de decidir redistribución.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-111 / O-111 | Equipo: Mover equipo a otro rack del cliente | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-112 / O-112 | Equipo: Consultar tooltip técnico | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-04: 64, 65 |
| PAR-113 / O-113 | Caras y alimentación: Abrir configuración de caras | adaptacion_servidor | Validar descubribilidad y explicar edición por grupo/IDs; mantener validación AC de enlaces existentes.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-114 / O-114 | Caras y alimentación: Asignar cara frontal al puerto | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-115 / O-115 | Caras y alimentación: Asignar cara trasera al puerto | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-116 / O-116 | Caras y alimentación: Asignar cara automática al puerto | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-117 / O-117 | Caras y alimentación: Asignar rol eléctrico entrada | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-118 / O-118 | Caras y alimentación: Asignar rol eléctrico salida | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-119 / O-119 | Caras y alimentación: Asignar rol eléctrico sin especificar | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-120 / O-120 | Caras y alimentación: Guardar caras y roles | parcial | Definir si se requiere edición conjunta atómica; mientras tanto documentar separación de operaciones y conservar borradores ante rechazo.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-121 / O-121 | Caras y alimentación: Cancelar configuración de caras | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-122 / O-122 | Caras y alimentación: Consultar conexiones de alimentación | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-123 / O-123 | Caras y alimentación: Seleccionar ruta eléctrica | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-124 / O-124 | Caras y alimentación: Desplegar inventario de puertos eléctricos | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-125 / O-125 | Puerto: Seleccionar puerto libre como origen | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-126 / O-126 | Puerto: Conectar segundo puerto local | parcial | Verificar y completar feedback visual de conexión confirmada sin señalar éxito antes del commit.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-127 / O-127 | Puerto: Cancelar origen por segundo clic | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-128 / O-128 | Puerto: Cancelar conexión local pendiente | parcial | Añadir o validar cancelación con Escape fuera de diálogos si se mantiene el atajo de referencia.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-129 / O-129 | Puerto: Inspeccionar puerto | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-130 / O-130 | Puerto: Abrir acciones desde inspector | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-131 / O-131 | Puerto: Abrir acciones por menú contextual | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-132 / O-132 | Puerto: Abrir acciones por pulsación larga | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-133 / O-133 | Puerto: Activar puerto con teclado | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-134 / O-134 | Puerto: Abrir contexto de puerto con teclado | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-135 / O-135 | Puerto: Consultar tooltip de puerto | parcial | Corregir lectura del prefijo por puerto/grupo en tooltip/inspector y contrastar numeración heterogénea en cara; no inferirlo de listas con UUID.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-136 / O-136 | Puerto: Crear o cambiar etiqueta por contexto | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-137 / O-137 | Puerto: Quitar etiqueta | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-138 / O-138 | Puerto: Editar etiqueta rápida de puerto libre | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-139 / O-139 | Puerto: Marcar puerto libre | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-140 / O-140 | Puerto: Marcar puerto reservado | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-141 / O-141 | Puerto: Marcar puerto deshabilitado | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-142 / O-142 | Puerto: Marcar puerto defectuoso | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-143 / O-143 | Puerto: Activar PoE individual | adaptacion_servidor | Conservar la adaptación por IDs; probar que el cambio de alias preserva cables/grupos y se representa correctamente.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-144 / O-144 | Puerto: Desactivar PoE individual | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-145 / O-145 | Puerto: Editar watts documentados | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-146 / O-146 | Puerto: Quitar watts documentados | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-147 / O-147 | Puerto: Asignar color individual | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-148 / O-148 | Puerto: Restablecer color individual | equivalente | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-149 / O-149 | Puerto: Cerrar menú contextual | adaptacion_servidor | Validar accesibilidad/cierre y declarar diferencia de modal frente a menú; no cambiar semántica de una operación enviada.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-150 / O-150 | Lotes de puertos: Desplegar rango de estado y PoE | adaptacion_servidor | Validar el recorrido en navegador/QA; este contraste acredita fuente, no ejecución ni adopción.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-151 / O-151 | Lotes de puertos: Cambiar inicio de rango de estado | adaptacion_servidor | Conservar mejora de identidad; validar rapidez de selección de rangos sin reintroducir gn como clave.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-152 / O-152 | Lotes de puertos: Cambiar final de rango de estado | adaptacion_servidor | Probar mismo subconjunto mediante casillas y explicar el cambio de selector; no restaurar rangos gn ambiguos.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-153 / O-153 | Lotes de puertos: Seleccionar todos en rango de estado | adaptacion_servidor | Probar mismo subconjunto mediante casillas y explicar el cambio de selector; no restaurar rangos gn ambiguos.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-154 / O-154 | Lotes de puertos: Marcar rango de puertos libres | adaptacion_servidor | Probar grupo con gn repetidos y estado del conjunto seleccionado; confirmar alcance acotado del deshacer.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-155 / O-155 | Lotes de puertos: Marcar rango de puertos reservados | adaptacion_servidor | Probar grupo con gn repetidos y estado del conjunto seleccionado; confirmar alcance acotado del deshacer.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-156 / O-156 | Lotes de puertos: Marcar rango de puertos deshabilitados | adaptacion_servidor | Probar grupo con gn repetidos y estado del conjunto seleccionado; confirmar alcance acotado del deshacer.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-157 / O-157 | Lotes de puertos: Marcar rango de puertos defectuosos | adaptacion_servidor | Probar grupo con gn repetidos y estado del conjunto seleccionado; confirmar alcance acotado del deshacer.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-158 / O-158 | Lotes de puertos: Activar PoE en rango | adaptacion_servidor | Probar ON/OFF en subgrupo con gn repetidos, y negativo en familia no RJ45.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-159 / O-159 | Lotes de puertos: Desactivar PoE en rango | adaptacion_servidor | Probar ON/OFF en subgrupo con gn repetidos, y negativo en familia no RJ45.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-160 / O-160 | Lotes de puertos: Desplegar rango de color | adaptacion_servidor | Revisar que la selección equivalente resulte clara; no usar gn como identidad inequívoca.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-161 / O-161 | Lotes de puertos: Cambiar inicio de rango de color | adaptacion_servidor | Revisar que la selección equivalente resulte clara; no usar gn como identidad inequívoca.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-162 / O-162 | Lotes de puertos: Cambiar final de rango de color | adaptacion_servidor | Revisar que la selección equivalente resulte clara; no usar gn como identidad inequívoca.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-163 / O-163 | Lotes de puertos: Seleccionar todos en rango de color | adaptacion_servidor | Revisar que la selección equivalente resulte clara; no usar gn como identidad inequívoca.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-164 / O-164 | Lotes de puertos: Asignar color a rango | adaptacion_servidor | Probar guardar/releer y compensar color en el conjunto elegido.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-165 / O-165 | Lotes de puertos: Borrar color de rango | adaptacion_servidor | Probar vuelta al color por defecto y compensación elegible.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-03: 58, 59, 60, 61, 62, 63 |
| PAR-166 / O-166 | Conexiones: Abrir detalle de cable existente | parcial | Completar/verificar presentación equivalente de detalles/fecha y recorrido de apertura desde cable.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-167 / O-167 | Conexiones: Destacar ruta al pasar tarjeta | parcial | Recuperar el destacado por hover si sigue siendo aceptación de paridad, y probar ratón/táctil.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-168 / O-168 | Conexiones: Consultar extremos documentados | equivalente | Verificar visualmente extremos locales/cross y objetos de sala con nombres duplicados.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-169 / O-169 | Conexiones: Editar nota del cable | parcial | Acordar e implementar recuperación/compensación del cambio de nota si se exige paridad de undo.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-170 / O-170 | Conexiones: Marcar patch planificado | parcial | Probar estado/recarga; completar compensación de cables si forma parte del criterio de paridad.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-171 / O-171 | Conexiones: Marcar patch en curso | parcial | Probar estado/recarga; completar compensación de cables si forma parte del criterio de paridad.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-172 / O-172 | Conexiones: Marcar patch terminado | parcial | Probar estado/recarga; completar compensación de cables si forma parte del criterio de paridad.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-173 / O-173 | Conexiones: Marcar patch probado | parcial | Probar estado/recarga; completar compensación de cables si forma parte del criterio de paridad.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-174 / O-174 | Conexiones: Marcar patch sin estado | parcial | Probar estado/recarga; completar compensación de cables si forma parte del criterio de paridad.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-175 / O-175 | Conexiones: Asignar color al cable existente | parcial | Probar color explícito y completar compensación según aceptación.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-176 / O-176 | Conexiones: Restablecer color de cable existente | parcial | Comprobar visualmente el color automático al limpiar y definir default equivalente; no afirmar igualdad de algoritmo.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-177 / O-177 | Conexiones: Desconectar cable | parcial | Probar desconexión/recarga y definir compensación segura de cable si se exige.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-178 / O-178 | Conexiones: Cerrar detalle de cable | parcial | Aclarar guardar/cancelar/cerrar y probar que un cierre nunca anuncia cambios no persistidos.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-179 / O-179 | Conexiones: Iniciar enlace entre racks | adaptacion_servidor | Probar navegación al destino sin perder origen y reflejar el flujo en QA.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-180 / O-180 | Conexiones: Completar enlace entre racks | adaptacion_servidor | Probar cruce en GUI, recarga y autorización del mismo cliente.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-181 / O-181 | Conexiones: Cancelar enlace entre racks | adaptacion_servidor | Probar cancelación por botón; recuperar Escape si permanece requisito.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-182 / O-182 | Conexiones: Iniciar reconexión de cable | adaptacion_servidor | Probar ambos extremos como ancla y documentar disparador de reconexión.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-183 / O-183 | Conexiones: Completar reconexión local o cross-rack | equivalente | Probar cambio local↔cross con color/nota/patch conservados y respuesta perdida.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-184 / O-184 | Conexiones: Cancelar reconexión | parcial | Probar cancelar con cable anterior intacto; completar o aclarar atajos adicionales.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-185 / O-185 | Conexiones: Bloquear nueva conexión ocupada o inválida | parcial | Probar negativos API/GUI y completar importación CSV por canal autorizado.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-186 / O-186 | Conexiones: Confirmar puerto reservado | equivalente | Probar reservado actual frente a lista obsoleta y cancelación sin mutación.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-187 / O-187 | Conexiones: Validar compatibilidad de alimentación | equivalente | Probar ambos sentidos y unspecified sin afirmar circuito físico.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-188 / O-188 | Conexiones en lote: Abrir conexión masiva | adaptacion_servidor | Probar acceso y visibilidad del diálogo con inventario representativo.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-189 / O-189 | Conexiones en lote: Elegir equipo origen | adaptacion_servidor | Verificar elección inequívoca de equipo/grupo con nombres repetidos.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-190 / O-190 | Conexiones en lote: Elegir tipo de puerto origen | adaptacion_servidor | Probar RJ45/RJ45 PoE dentro de familia y mezcla de grupos.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-191 / O-191 | Conexiones en lote: Elegir inicio de puertos libres origen | parcial | Añadir selección secuencial inequívoca por IDs si se necesita conservar la automatización de lote.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-192 / O-192 | Conexiones en lote: Elegir equipo destino | adaptacion_servidor | Probar que validación backend impide mismos extremos y ocupados sin alterar el lote.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-193 / O-193 | Conexiones en lote: Elegir tipo de puerto destino | adaptacion_servidor | Revisar legibilidad de grupo/tipo destino.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-194 / O-194 | Conexiones en lote: Elegir inicio de puertos libres destino | parcial | Completar generación secuencial segura si es necesaria para paridad del bulk.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-195 / O-195 | Conexiones en lote: Ajustar cantidad de conexiones | parcial | Completar conteo/generación automática y validación por IDs si se mantiene la experiencia bulk.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-196 / O-196 | Conexiones en lote: Previsualizar pares masivos | adaptacion_servidor | Probar vista previa completa de un lote y campos inválidos.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-197 / O-197 | Conexiones en lote: Guardar lote de conexiones | parcial | Probar atomicidad/recarga y completar feedback/compensación del lote si se exige.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-198 / O-198 | Conexiones en lote: Cancelar conexión masiva | adaptacion_servidor | Probar cierre antes y después del envío; distinguir cancelación de intento de cierre de diálogo.  | Recorrido GUI por IDs/grupo/tipo explícitos; conservar UUID, puertos y cables al editar. Confirmar commit, recargar y leer con otra sesión; negativos de ámbito/permiso/conflicto. Frontal/trasera y EN/DE/ES sin traducir datos propios. | I-05: 66, 67, 68, 69, 70, 71 |
| PAR-199 / O-199 | Búsqueda y filtros: Buscar en cliente completo | parcial | Ampliar consulta a serie/modelo/IP/firmware/notas/preset de equipo y probar acentos/nombres.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-200 / O-200 | Búsqueda y filtros: Abrir resultado de búsqueda | adaptacion_servidor | Verificar foco/desplazamiento y cara correcta de puerto con nombre repetido.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-201 / O-201 | Búsqueda y filtros: Buscar dentro del rack | parcial | Unificar o aclarar filtro local de cables para evitar una búsqueda que parezca incompleta.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-202 / O-202 | Búsqueda y filtros: Limpiar búsquedas al navegar cliente | parcial | Probar volver/iniciar/cambiar cliente con búsqueda, selección, reconexión y pendientes; concretar descarte.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-203 / O-203 | Búsqueda y filtros: Consultar mensaje de búsqueda vacía | equivalente | Comprobar texto de consulta y mensaje vacío en EN/DE/ES.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-204 / O-204 | Preferencias visuales: Elegir idioma EN/DE/ES | adaptacion_servidor | Probar cambio, recarga y otra sesión del actor sin traducir nombres escritos.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | P-10: 156, 157, 158, 159, 160, 161 |
| PAR-205 / O-205 | Preferencias visuales: Elegir tema oscuro | adaptacion_servidor | Probar cuenta y acceso anónimo.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | P-10: 156, 157, 158, 159, 160, 161 |
| PAR-206 / O-206 | Preferencias visuales: Elegir tema claro | adaptacion_servidor | Probar recarga y contraste de controles.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | P-10: 156, 157, 158, 159, 160, 161 |
| PAR-207 / O-207 | Preferencias visuales: Adaptar temas históricos | ausente | No migrar storage ajeno automáticamente; decidir si se necesita compatibilidad explícita. Comportamiento específico de archivo/almacenamiento offline o duplicación clásica. Mantener el objetivo útil mediante servidor/diario seguro; no crear otro inventario maestro local. | Documentar el equivalente servidor: no borrar auditoría, traducir datos del usuario ni convertir localStorage en base maestra. No crear un botón sólo por copiar el offline. | P-10: 156, 157, 158, 159, 160, 161 |
| PAR-208 / O-208 | Preferencias visuales: Configurar color por tipo de puerto | adaptacion_servidor | Probar aislamiento entre actores y restauración de preferencias.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | P-10: 156, 157, 158, 159, 160, 161 |
| PAR-209 / O-209 | Preferencias visuales: Restablecer color de un tipo | adaptacion_servidor | Probar render tras guardar/recargar.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | P-10: 156, 157, 158, 159, 160, 161 |
| PAR-210 / O-210 | Preferencias visuales: Restablecer todos los colores de tipos | adaptacion_servidor | Probar defaults en los diez tipos.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | P-10: 156, 157, 158, 159, 160, 161 |
| PAR-211 / O-211 | Preferencias visuales: Configurar color por pareja de categorías | adaptacion_servidor | Probar orden simétrico de pareja y ámbito personal.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | P-10: 156, 157, 158, 159, 160, 161 |
| PAR-212 / O-212 | Preferencias visuales: Quitar color de pareja de categorías | adaptacion_servidor | Probar selección/limpieza y recarga.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | P-10: 156, 157, 158, 159, 160, 161 |
| PAR-213 / O-213 | Preferencias visuales: Elegir color de próximas conexiones | equivalente | Probar que no recolorea cables anteriores.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | P-10: 156, 157, 158, 159, 160, 161 |
| PAR-214 / O-214 | Preferencias visuales: Restablecer color de próximas conexiones | equivalente | Probar null frente a color explícito y default personal.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | P-10: 156, 157, 158, 159, 160, 161 |
| PAR-215 / O-215 | Preferencias visuales: Activar vista clásica de respaldo | ausente | Registrar decisión de alcance: recuperar vista clásica o aceptar explícitamente su retirada. Comportamiento específico de archivo/almacenamiento offline o duplicación clásica. Mantener el objetivo útil mediante servidor/diario seguro; no crear otro inventario maestro local. | Documentar el equivalente servidor: no borrar auditoría, traducir datos del usuario ni convertir localStorage en base maestra. No crear un botón sólo por copiar el offline. | P-10: 156, 157, 158, 159, 160, 161 |
| PAR-216 / O-216 | Preferencias visuales: Volver a vista física integrada | adaptacion_servidor | Confirmar si basta vista física como referencia aprobada.  | Recorrido en navegador con ubicación visible, cambio y respuesta; recarga/otra sesión cuando persiste. EN/DE/ES, nombres literales y rechazo por servidor cuando corresponde. | P-10: 156, 157, 158, 159, 160, 161 |
| PAR-217 / O-217 | Historial y atajos: Deshacer última mutación registrada | parcial | Definir y completar matriz de compensación por tipo de operación sin revertir cambios ajenos.  | Operación y compensación con concurrencia y permisos actuales; no reescribir la historia. Atajos no deben actuar en campos ni duplicar comandos. | I-02: 52, 53, 54, 55, 56, 57 |
| PAR-218 / O-218 | Historial y atajos: Rehacer mutación deshecha | ausente | Definir recuperación/redo seguro en concurrencia o aceptación explícita del límite.  | Operación y compensación con concurrencia y permisos actuales; no reescribir la historia. Atajos no deben actuar en campos ni duplicar comandos. | I-02: 52, 53, 54, 55, 56, 57 |
| PAR-219 / O-219 | Historial y atajos: Registrar cambio en log local | adaptacion_servidor | Verificar autor/fechas/orden y permisos en eventos de operaciones reales.  | Operación y compensación con concurrencia y permisos actuales; no reescribir la historia. Atajos no deben actuar en campos ni duplicar comandos. | I-02: 52, 53, 54, 55, 56, 57 |
| PAR-220 / O-220 | Historial y atajos: Consultar log del cliente | parcial | Concretar visor histórico de cliente, filtros/paginación y límites de retención.  | Operación y compensación con concurrencia y permisos actuales; no reescribir la historia. Atajos no deben actuar en campos ni duplicar comandos. | I-02: 52, 53, 54, 55, 56, 57 |
| PAR-221 / O-221 | Historial y atajos: Vaciar log del ámbito | ausente | Mantener auditoría íntegra; decidir si se necesita limpiar sólo avisos locales sin borrar evidencia. El log local no equivale a la auditoría de seguridad del servidor. No trasladar un botón para vaciar la auditoría. | Documentar el equivalente servidor: no borrar auditoría, traducir datos del usuario ni convertir localStorage en base maestra. No crear un botón sólo por copiar el offline. | I-02: 52, 53, 54, 55, 56, 57 |
| PAR-222 / O-222 | Historial y atajos: Cerrar visor de log | parcial | Confirmar recorrido de cierre/plegado de los detalles y si se requiere visor dedicado.  | Operación y compensación con concurrencia y permisos actuales; no reescribir la historia. Atajos no deben actuar en campos ni duplicar comandos. | I-02: 52, 53, 54, 55, 56, 57 |
| PAR-223 / O-223 | Historial y atajos: Guardar mediante teclado | ausente | Completar exportación JSON con alcance y botón; decidir atajo sin interferir con navegador.  | Operación y compensación con concurrencia y permisos actuales; no reescribir la historia. Atajos no deben actuar en campos ni duplicar comandos. | P-11: 162, 163, 164, 165, 166, 167 |
| PAR-224 / O-224 | Historial y atajos: Enfocar búsqueda global mediante teclado | ausente | Recuperar atajo accesible si forma parte de paridad.  | Operación y compensación con concurrencia y permisos actuales; no reescribir la historia. Atajos no deben actuar en campos ni duplicar comandos. | P-11: 162, 163, 164, 165, 166, 167 |
| PAR-225 / O-225 | Historial y atajos: Cancelar modos mediante Escape | parcial | Probar Escape por estado y completar comportamiento sin descartar intentos enviados.  | Operación y compensación con concurrencia y permisos actuales; no reescribir la historia. Atajos no deben actuar en campos ni duplicar comandos. | I-02: 52, 53, 54, 55, 56, 57 |
| PAR-226 / O-226 | Historial y atajos: Borrar selección mediante teclado | parcial | Añadir atajo con protección de campos editables si se conserva requisito.  | Operación y compensación con concurrencia y permisos actuales; no reescribir la historia. Atajos no deben actuar en campos ni duplicar comandos. | I-02: 52, 53, 54, 55, 56, 57 |
| PAR-227 / O-227 | JSON e importación: Exportar respaldo de toda infraestructura | ausente | Definir contrato web de importación/exportación con ámbito, validación previa, revisión, permisos, idempotencia y confirmación; no usar operador externo como evidencia de dashboard.  | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-03: 114, 115, 116, 117, 118, 119 |
| PAR-228 / O-228 | JSON e importación: Exportar JSON del cliente activo | ausente | Definir contrato web de importación/exportación con ámbito, validación previa, revisión, permisos, idempotencia y confirmación; no usar operador externo como evidencia de dashboard.  | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-03: 114, 115, 116, 117, 118, 119 |
| PAR-229 / O-229 | JSON e importación: Exportar proyecto legacy | ausente | Definir contrato web de importación/exportación con ámbito, validación previa, revisión, permisos, idempotencia y confirmación; no usar operador externo como evidencia de dashboard.  | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-03: 114, 115, 116, 117, 118, 119 |
| PAR-230 / O-230 | JSON e importación: Cargar respaldo completo | ausente | Definir contrato web de importación/exportación con ámbito, validación previa, revisión, permisos, idempotencia y confirmación; no usar operador externo como evidencia de dashboard.  | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-01: 101, 102, 103, 104, 105, 106, 107 |
| PAR-231 / O-231 | JSON e importación: Sustituir inventario del cliente | ausente | Definir contrato web de importación/exportación con ámbito, validación previa, revisión, permisos, idempotencia y confirmación; no usar operador externo como evidencia de dashboard.  | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-01: 101, 102, 103, 104, 105, 106, 107 |
| PAR-232 / O-232 | JSON e importación: Cargar proyecto multicliente sobre legacy | ausente | Definir contrato web de importación/exportación con ámbito, validación previa, revisión, permisos, idempotencia y confirmación; no usar operador externo como evidencia de dashboard.  | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-01: 101, 102, 103, 104, 105, 106, 107 |
| PAR-233 / O-233 | JSON e importación: Importar rack JSON | ausente | Definir contrato web de importación/exportación con ámbito, validación previa, revisión, permisos, idempotencia y confirmación; no usar operador externo como evidencia de dashboard.  | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-01: 101, 102, 103, 104, 105, 106, 107 |
| PAR-234 / O-234 | JSON e importación: Fusionar proyectos JSON | ausente | Definir contrato web de importación/exportación con ámbito, validación previa, revisión, permisos, idempotencia y confirmación; no usar operador externo como evidencia de dashboard.  | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-04: 120, 121, 122, 123, 124, 125 |
| PAR-235 / O-235 | JSON e importación: Rechazar importación si cambia el contexto | ausente | Definir contrato web de importación/exportación con ámbito, validación previa, revisión, permisos, idempotencia y confirmación; no usar operador externo como evidencia de dashboard.  | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-02: 108, 109, 110, 111, 112, 113 |
| PAR-236 / O-236 | JSON e importación: Validar topología de proyecto importado | ausente | Definir contrato web de importación/exportación con ámbito, validación previa, revisión, permisos, idempotencia y confirmación; no usar operador externo como evidencia de dashboard.  | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-02: 108, 109, 110, 111, 112, 113 |
| PAR-237 / O-237 | JSON e importación: Validar metadatos de presentación | ausente | Definir contrato web de importación/exportación con ámbito, validación previa, revisión, permisos, idempotencia y confirmación; no usar operador externo como evidencia de dashboard.  | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-02: 108, 109, 110, 111, 112, 113 |
| PAR-238 / O-238 | JSON e importación: Remapear IDs y nombres al fusionar | ausente | Definir contrato web de importación/exportación con ámbito, validación previa, revisión, permisos, idempotencia y confirmación; no usar operador externo como evidencia de dashboard.  | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-04: 120, 121, 122, 123, 124, 125 |
| PAR-239 / O-239 | JSON e importación: Exportar rack individual | ausente | Definir contrato web de importación/exportación con ámbito, validación previa, revisión, permisos, idempotencia y confirmación; no usar operador externo como evidencia de dashboard.  | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-03: 114, 115, 116, 117, 118, 119 |
| PAR-240 / O-240 | CSV e intercambio: Importar conexiones CSV | ausente | Implementar contrato de importación CSV prevalidado y atómico, con resolución inequívoca por grupo/tipo/IDs; negativos de ambigüedad/cross.  | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-241 / O-241 | CSV e intercambio: Resolver puerto CSV por nombre/número/tipo | ausente | Implementar contrato de importación CSV prevalidado y atómico, con resolución inequívoca por grupo/tipo/IDs; negativos de ambigüedad/cross.  | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-242 / O-242 | CSV e intercambio: Rechazar CSV de enlaces cross-rack | ausente | Implementar contrato de importación CSV prevalidado y atómico, con resolución inequívoca por grupo/tipo/IDs; negativos de ambigüedad/cross.  | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-243 / O-243 | CSV e intercambio: Exportar conexiones del cliente en CSV integrado | parcial | Comparar cabeceras/celdas/idiomas con la salida RC10 y decidir compatibilidad explícita de formato.  | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-244 / O-244 | CSV e intercambio: Exportar CSV de todos los clientes | ausente | Implementar sólo con unión de ámbitos autorizados y filtro de clientes, o aceptar límite por cliente.  | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-245 / O-245 | Informes: Abrir informe moderno del cliente | parcial | Integrar diseño gráfico aprobado, branding/técnico y tablas del cliente; probar paginación/impresión EN/DE/ES.  | Comprobar formato real, Unicode/escape y contenido frente al inventario; ámbito/permiso en servidor. Descargar y abrir con la herramienta correspondiente. Distinguir HTML imprimible/PDF, XLS HTML/XLSX y QR decorativo/real. | P-07: 138, 139, 140, 141, 142, 143 |
| PAR-246 / O-246 | Informes: Abrir informe moderno del rack | parcial | Unificar salida de rack según RC10 y comprobar extremos cross y página final.  | Comprobar formato real, Unicode/escape y contenido frente al inventario; ámbito/permiso en servidor. Descargar y abrir con la herramienta correspondiente. Distinguir HTML imprimible/PDF, XLS HTML/XLSX y QR decorativo/real. | P-07: 138, 139, 140, 141, 142, 143 |
| PAR-247 / O-247 | Informes: Imprimir informe moderno o guardar PDF | adaptacion_servidor | Probar imprimir/Guardar PDF del HTML generado; completar integración de un botón compacto sin anunciar PDF nativo.  | Comprobar formato real, Unicode/escape y contenido frente al inventario; ámbito/permiso en servidor. Descargar y abrir con la herramienta correspondiente. Distinguir HTML imprimible/PDF, XLS HTML/XLSX y QR decorativo/real. | P-07: 138, 139, 140, 141, 142, 143 |
| PAR-248 / O-248 | Informes: Volver del informe moderno | parcial | Probar volver/cerrar documento sin perder rack/cliente; decidir visor integrado.  | Comprobar formato real, Unicode/escape y contenido frente al inventario; ámbito/permiso en servidor. Descargar y abrir con la herramienta correspondiente. Distinguir HTML imprimible/PDF, XLS HTML/XLSX y QR decorativo/real. | P-07: 138, 139, 140, 141, 142, 143 |
| PAR-249 / O-249 | Informes: Abrir informe clásico del cliente | ausente | Recuperar informe clásico si sigue en alcance o documentar aceptación de formato alternativo. Resolver la necesidad de informe legible, sin duplicar toda la interfaz clásica del offline. | Comprobar formato real, Unicode/escape y contenido frente al inventario; ámbito/permiso en servidor. Descargar y abrir con la herramienta correspondiente. Distinguir HTML imprimible/PDF, XLS HTML/XLSX y QR decorativo/real. | P-07: 138, 139, 140, 141, 142, 143 |
| PAR-250 / O-250 | Informes: Abrir informe clásico del rack | ausente | Completar paridad de informe y resumen, sin confundir tabla con captura del rack. Resolver la necesidad de informe legible, sin duplicar toda la interfaz clásica del offline. | Comprobar formato real, Unicode/escape y contenido frente al inventario; ámbito/permiso en servidor. Descargar y abrir con la herramienta correspondiente. Distinguir HTML imprimible/PDF, XLS HTML/XLSX y QR decorativo/real. | P-07: 138, 139, 140, 141, 142, 143 |
| PAR-251 / O-251 | Informes: Exportar CSV clásico de cliente | parcial | Definir columnas compatibles conservando protección de celdas; probar acentos y patch.  | Comprobar formato real, Unicode/escape y contenido frente al inventario; ámbito/permiso en servidor. Descargar y abrir con la herramienta correspondiente. Distinguir HTML imprimible/PDF, XLS HTML/XLSX y QR decorativo/real. | P-07: 138, 139, 140, 141, 142, 143 |
| PAR-252 / O-252 | Informes: Exportar CSV clásico de rack | adaptacion_servidor | Comparar alcance de incidentes y acordar cabeceras; no retirar protección para imitar fallo clásico.  | Comprobar formato real, Unicode/escape y contenido frente al inventario; ámbito/permiso en servidor. Descargar y abrir con la herramienta correspondiente. Distinguir HTML imprimible/PDF, XLS HTML/XLSX y QR decorativo/real. | P-07: 138, 139, 140, 141, 142, 143 |
| PAR-253 / O-253 | Informes: Imprimir informe clásico de cliente | parcial | Completar documento gráfico equivalente y verificar carga completa antes de imprimir.  | Comprobar formato real, Unicode/escape y contenido frente al inventario; ámbito/permiso en servidor. Descargar y abrir con la herramienta correspondiente. Distinguir HTML imprimible/PDF, XLS HTML/XLSX y QR decorativo/real. | P-07: 138, 139, 140, 141, 142, 143 |
| PAR-254 / O-254 | Informes: Imprimir informe clásico de rack | parcial | Completar layout y evidencia visual del PDF impreso.  | Comprobar formato real, Unicode/escape y contenido frente al inventario; ámbito/permiso en servidor. Descargar y abrir con la herramienta correspondiente. Distinguir HTML imprimible/PDF, XLS HTML/XLSX y QR decorativo/real. | P-07: 138, 139, 140, 141, 142, 143 |
| PAR-255 / O-255 | Informes: Volver de informe clásico | parcial | Verificar retorno al origen si se integra visor; no inventar limpieza de estado inexistente.  | Comprobar formato real, Unicode/escape y contenido frente al inventario; ámbito/permiso en servidor. Descargar y abrir con la herramienta correspondiente. Distinguir HTML imprimible/PDF, XLS HTML/XLSX y QR decorativo/real. | P-07: 138, 139, 140, 141, 142, 143 |
| PAR-256 / O-256 | Informes: Consultar ficha técnica dentro de reportes clásicos | parcial | Añadir los campos técnicos requeridos al informe con escape, conservando etiquetas de puertos.  | Comprobar formato real, Unicode/escape y contenido frente al inventario; ámbito/permiso en servidor. Descargar y abrir con la herramienta correspondiente. Distinguir HTML imprimible/PDF, XLS HTML/XLSX y QR decorativo/real. | P-07: 138, 139, 140, 141, 142, 143 |
| PAR-257 / O-257 | Informes: Consultar log dentro del reporte clásico | ausente | Definir historial autorizado a incluir y añadirlo al informe si permanece requisito. Resolver la necesidad de informe legible, sin duplicar toda la interfaz clásica del offline. | Comprobar formato real, Unicode/escape y contenido frente al inventario; ámbito/permiso en servidor. Descargar y abrir con la herramienta correspondiente. Distinguir HTML imprimible/PDF, XLS HTML/XLSX y QR decorativo/real. | P-07: 138, 139, 140, 141, 142, 143 |
| PAR-258 / O-258 | Informes: Consultar resumen de estados y PoE del rack | parcial | Completar resumen documental por estados/PoE con desconocidos explícitos y probar cifras.  | Comprobar formato real, Unicode/escape y contenido frente al inventario; ámbito/permiso en servidor. Descargar y abrir con la herramienta correspondiente. Distinguir HTML imprimible/PDF, XLS HTML/XLSX y QR decorativo/real. | P-07: 138, 139, 140, 141, 142, 143 |
| PAR-259 / O-259 | Informes: Consultar leyenda de cables del rack | parcial | Integrar leyenda aprobada y comprobar color, extremos y patch en documento impreso.  | Comprobar formato real, Unicode/escape y contenido frente al inventario; ámbito/permiso en servidor. Descargar y abrir con la herramienta correspondiente. Distinguir HTML imprimible/PDF, XLS HTML/XLSX y QR decorativo/real. | P-07: 138, 139, 140, 141, 142, 143 |
| PAR-260 / O-260 | Imágenes y documentos: Exportar PNG del rack | ausente | Completar captura/exportación raster y verificar dimensiones/fondo/cara/contenido real; reutilización y licencia deben investigarse antes de implementar.  | Comprobar formato real, Unicode/escape y contenido frente al inventario; ámbito/permiso en servidor. Descargar y abrir con la herramienta correspondiente. Distinguir HTML imprimible/PDF, XLS HTML/XLSX y QR decorativo/real. | P-07: 138, 139, 140, 141, 142, 143 |
| PAR-261 / O-261 | Imágenes y documentos: Exportar PNG HD del rack | ausente | Completar captura/exportación raster y verificar dimensiones/fondo/cara/contenido real; reutilización y licencia deben investigarse antes de implementar.  | Comprobar formato real, Unicode/escape y contenido frente al inventario; ámbito/permiso en servidor. Descargar y abrir con la herramienta correspondiente. Distinguir HTML imprimible/PDF, XLS HTML/XLSX y QR decorativo/real. | P-07: 138, 139, 140, 141, 142, 143 |
| PAR-262 / O-262 | Imágenes y documentos: Exportar PNG transparente del rack | ausente | Completar captura/exportación raster y verificar dimensiones/fondo/cara/contenido real; reutilización y licencia deben investigarse antes de implementar.  | Comprobar formato real, Unicode/escape y contenido frente al inventario; ámbito/permiso en servidor. Descargar y abrir con la herramienta correspondiente. Distinguir HTML imprimible/PDF, XLS HTML/XLSX y QR decorativo/real. | P-07: 138, 139, 140, 141, 142, 143 |
| PAR-263 / O-263 | Imágenes y documentos: Capturar PNG interno para reporte clásico | ausente | Completar captura/exportación raster y verificar dimensiones/fondo/cara/contenido real; reutilización y licencia deben investigarse antes de implementar.  | Comprobar formato real, Unicode/escape y contenido frente al inventario; ámbito/permiso en servidor. Descargar y abrir con la herramienta correspondiente. Distinguir HTML imprimible/PDF, XLS HTML/XLSX y QR decorativo/real. | P-07: 138, 139, 140, 141, 142, 143 |
| PAR-264 / O-264 | Imágenes y documentos: Exportar PDF clásico directo | parcial | Completar acceso directo y contenido de impresión requerido; distinguir PDF guardado por navegador.  | Comprobar formato real, Unicode/escape y contenido frente al inventario; ámbito/permiso en servidor. Descargar y abrir con la herramienta correspondiente. Distinguir HTML imprimible/PDF, XLS HTML/XLSX y QR decorativo/real. | P-07: 138, 139, 140, 141, 142, 143 |
| PAR-265 / O-265 | Imágenes y documentos: Exportar XLS HTML | parcial | Resolver metadato técnico persistido y comparar celdas con RC10 en Excel; conservar protección textual y advertencia de formato HTML.  | Comprobar formato real, Unicode/escape y contenido frente al inventario; ámbito/permiso en servidor. Descargar y abrir con la herramienta correspondiente. Distinguir HTML imprimible/PDF, XLS HTML/XLSX y QR decorativo/real. | P-07: 138, 139, 140, 141, 142, 143 |
| PAR-266 / O-266 | Etiquetas y QR: Abrir etiquetas de todos los racks del cliente | parcial | Completar campos/orden visual de etiqueta aprobada y selector de todos los racks según límites.  | Comprobar formato real, Unicode/escape y contenido frente al inventario; ámbito/permiso en servidor. Descargar y abrir con la herramienta correspondiente. Distinguir HTML imprimible/PDF, XLS HTML/XLSX y QR decorativo/real. | P-07: 138, 139, 140, 141, 142, 143 |
| PAR-267 / O-267 | Etiquetas y QR: Imprimir etiquetas por lote | adaptacion_servidor | Probar impresora/PDF, márgenes y selección completa de cliente.  | Comprobar formato real, Unicode/escape y contenido frente al inventario; ámbito/permiso en servidor. Descargar y abrir con la herramienta correspondiente. Distinguir HTML imprimible/PDF, XLS HTML/XLSX y QR decorativo/real. | P-07: 138, 139, 140, 141, 142, 143 |
| PAR-268 / O-268 | Etiquetas y QR: Volver de etiquetas por lote | parcial | Acordar navegación del documento y probar que el cliente de origen se conserva.  | Comprobar formato real, Unicode/escape y contenido frente al inventario; ámbito/permiso en servidor. Descargar y abrir con la herramienta correspondiente. Distinguir HTML imprimible/PDF, XLS HTML/XLSX y QR decorativo/real. | P-07: 138, 139, 140, 141, 142, 143 |
| PAR-269 / O-269 | Etiquetas y QR: Imprimir etiqueta individual de rack | parcial | Completar acceso de un click y metadatos de etiqueta; probar impresión.  | Comprobar formato real, Unicode/escape y contenido frente al inventario; ámbito/permiso en servidor. Descargar y abrir con la herramienta correspondiente. Distinguir HTML imprimible/PDF, XLS HTML/XLSX y QR decorativo/real. | P-07: 138, 139, 140, 141, 142, 143 |
| PAR-270 / O-270 | Etiquetas y QR: Descargar QR decorativo | ausente | Confirmar si se conserva esta salida advertida; nunca sustituirla por QR MFA o decir que es escaneable. No portar un QR decorativo como si fuera escaneable. El QR de inventario y el QR secreto TOTP son funciones diferentes. | Comprobar formato real, Unicode/escape y contenido frente al inventario; ámbito/permiso en servidor. Descargar y abrir con la herramienta correspondiente. Distinguir HTML imprimible/PDF, XLS HTML/XLSX y QR decorativo/real. | P-07: 138, 139, 140, 141, 142, 143 |
| PAR-271 / O-271 | Demo e idioma: Cargar diez clientes sintéticos | ausente | Crear un flujo de demo QA explícito, autorizado y seguro por ámbito; no presentar el auxiliar como dashboard. La instalación C ya tiene el original por auxiliar local. Falta la acción GUI/perfil QA; no precargar clientes ficticios silenciosamente en producción. | Carga opcional en laboratorio identificado; conservar cuentas, MFA, permisos y datos previos. Diez clientes completos tras recarga/otra sesión; no activar demo en producción. | E-05: 243, 244, 245, 246, 247 |
| PAR-272 / O-272 | Demo e idioma: Cargar demo en cliente activo | ausente | Definir y probar datos de demostración y reemplazo por cliente, preservando ámbitos/seguridad. La instalación C ya tiene el original por auxiliar local. Falta la acción GUI/perfil QA; no precargar clientes ficticios silenciosamente en producción. | Carga opcional en laboratorio identificado; conservar cuentas, MFA, permisos y datos previos. Diez clientes completos tras recarga/otra sesión; no activar demo en producción. | E-05: 243, 244, 245, 246, 247 |
| PAR-273 / O-273 | Demo e idioma: Traducir texto demo no editado al cambiar idioma | ausente | Diseñar identidad de datos demo y preservar texto de usuario si se incorpora generación multilingüe. Traducir sólo textos sintéticos generados para demo; conservar nombres reales escritos por usuarios. | Documentar el equivalente servidor: no borrar auditoría, traducir datos del usuario ni convertir localStorage en base maestra. No crear un botón sólo por copiar el offline. | P-10: 156, 157, 158, 159, 160, 161 |
| PAR-274 / O-274 | Demo e idioma: Generar documentación eléctrica del demo | ausente | Proveer escenario demo validado sin afirmar cálculo eléctrico; distinguir datos ya importados y generación. La instalación C ya tiene el original por auxiliar local. Falta la acción GUI/perfil QA; no precargar clientes ficticios silenciosamente en producción. | Carga opcional en laboratorio identificado; conservar cuentas, MFA, permisos y datos previos. Diez clientes completos tras recarga/otra sesión; no activar demo en producción. | E-05: 243, 244, 245, 246, 247 |
| PAR-275 / O-275 | Persistencia y recuperación: Restaurar autosave válido al arrancar | adaptacion_servidor | Probar recarga/otra sesión, carga al seleccionar cliente y aislamiento del diario local; no crear un autosave maestro paralelo a PostgreSQL.  | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-276 / O-276 | Persistencia y recuperación: Autoguardar cambios del proyecto | adaptacion_servidor | Probar commit/recarga, fallo antes de commit y respuesta perdida.  | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-277 / O-277 | Persistencia y recuperación: Rotar copias locales automáticas | ausente | Diseñar backup y recuperación desde dashboard con componente operativo separado, integridad y sobre MFA; mostrar las tareas externas como alternativa, sin darles crédito de interfaz.  | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | R-01: 192, 193, 194, 195, 196 |
| PAR-278 / O-278 | Persistencia y recuperación: Mostrar fallo de autosave | adaptacion_servidor | Probar fallos de red/journal y completar exportación de rescate de alcance adecuado.  | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-279 / O-279 | Persistencia y recuperación: Exportar respaldo desde alerta de autosave | ausente | Añadir flujo de exportación autorizado desde administración y acceso de rescate cuando sea viable. Recuperación de servidor o de borradores/diarios por actor y ámbito; no exponer copias crudas de datos ajenos. | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-280 / O-280 | Persistencia y recuperación: Detectar cambios sin exportar | adaptacion_servidor | Probar beforeunload en borrador y envío pendiente; el guardado no debe depender de haber exportado archivo.  | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-281 / O-281 | Persistencia y recuperación: Guardar snapshot nombrado completo | ausente | Definir recuperación versionada completa con permisos, confirmación, respaldo previo y revisión; no reemplazar otros usuarios en silencio. Recuperación de servidor o de borradores/diarios por actor y ámbito; no exponer copias crudas de datos ajenos. | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | R-01: 192, 193, 194, 195, 196 |
| PAR-282 / O-282 | Persistencia y recuperación: Desplegar lista de snapshots | ausente | Definir recuperación versionada completa con permisos, confirmación, respaldo previo y revisión; no reemplazar otros usuarios en silencio. Recuperación de servidor o de borradores/diarios por actor y ámbito; no exponer copias crudas de datos ajenos. | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | R-01: 192, 193, 194, 195, 196 |
| PAR-283 / O-283 | Persistencia y recuperación: Restaurar snapshot completo | ausente | Definir recuperación versionada completa con permisos, confirmación, respaldo previo y revisión; no reemplazar otros usuarios en silencio. Recuperación de servidor o de borradores/diarios por actor y ámbito; no exponer copias crudas de datos ajenos. | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | R-04: 207, 208, 209, 210, 211 |
| PAR-284 / O-284 | Persistencia y recuperación: Eliminar snapshot | ausente | Definir recuperación versionada completa con permisos, confirmación, respaldo previo y revisión; no reemplazar otros usuarios en silencio. Recuperación de servidor o de borradores/diarios por actor y ámbito; no exponer copias crudas de datos ajenos. | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | R-01: 192, 193, 194, 195, 196 |
| PAR-285 / O-285 | Persistencia y recuperación: Reparar formato de autosave al iniciar | ausente | No portar reparación de inventario local como autoridad. Definir experiencia equivalente de error/recuperación y exportación autorizada; recuperación nativa permanece canal operativo. Comportamiento específico de archivo/almacenamiento offline o duplicación clásica. Mantener el objetivo útil mediante servidor/diario seguro; no crear otro inventario maestro local. | Documentar el equivalente servidor: no borrar auditoría, traducir datos del usuario ni convertir localStorage en base maestra. No crear un botón sólo por copiar el offline. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-286 / O-286 | Persistencia y recuperación: Recuperar copia local si autosave inválido | ausente | No portar reparación de inventario local como autoridad. Definir experiencia equivalente de error/recuperación y exportación autorizada; recuperación nativa permanece canal operativo. Comportamiento específico de archivo/almacenamiento offline o duplicación clásica. Mantener el objetivo útil mediante servidor/diario seguro; no crear otro inventario maestro local. | Documentar el equivalente servidor: no borrar auditoría, traducir datos del usuario ni convertir localStorage en base maestra. No crear un botón sólo por copiar el offline. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-287 / O-287 | Persistencia y recuperación: Detectar orden ambiguo de backups | ausente | No portar reparación de inventario local como autoridad. Definir experiencia equivalente de error/recuperación y exportación autorizada; recuperación nativa permanece canal operativo. Comportamiento específico de archivo/almacenamiento offline o duplicación clásica. Mantener el objetivo útil mediante servidor/diario seguro; no crear otro inventario maestro local. | Documentar el equivalente servidor: no borrar auditoría, traducir datos del usuario ni convertir localStorage en base maestra. No crear un botón sólo por copiar el offline. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-288 / O-288 | Persistencia y recuperación: Arrancar modo seguro con todos los datos inválidos | ausente | No portar reparación de inventario local como autoridad. Definir experiencia equivalente de error/recuperación y exportación autorizada; recuperación nativa permanece canal operativo. Comportamiento específico de archivo/almacenamiento offline o duplicación clásica. Mantener el objetivo útil mediante servidor/diario seguro; no crear otro inventario maestro local. | Documentar el equivalente servidor: no borrar auditoría, traducir datos del usuario ni convertir localStorage en base maestra. No crear un botón sólo por copiar el offline. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-289 / O-289 | Persistencia y recuperación: Pausar autosave ante almacenamiento ilegible | ausente | No portar reparación de inventario local como autoridad. Definir experiencia equivalente de error/recuperación y exportación autorizada; recuperación nativa permanece canal operativo. Comportamiento específico de archivo/almacenamiento offline o duplicación clásica. Mantener el objetivo útil mediante servidor/diario seguro; no crear otro inventario maestro local. | Documentar el equivalente servidor: no borrar auditoría, traducir datos del usuario ni convertir localStorage en base maestra. No crear un botón sólo por copiar el offline. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-290 / O-290 | Persistencia y recuperación: Pausar autosave si falla cuarentena | ausente | No portar reparación de inventario local como autoridad. Definir experiencia equivalente de error/recuperación y exportación autorizada; recuperación nativa permanece canal operativo. Comportamiento específico de archivo/almacenamiento offline o duplicación clásica. Mantener el objetivo útil mediante servidor/diario seguro; no crear otro inventario maestro local. | Documentar el equivalente servidor: no borrar auditoría, traducir datos del usuario ni convertir localStorage en base maestra. No crear un botón sólo por copiar el offline. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-291 / O-291 | Persistencia y recuperación: Enumerar episodios de cuarentena | ausente | No portar reparación de inventario local como autoridad. Definir experiencia equivalente de error/recuperación y exportación autorizada; recuperación nativa permanece canal operativo. Comportamiento específico de archivo/almacenamiento offline o duplicación clásica. Mantener el objetivo útil mediante servidor/diario seguro; no crear otro inventario maestro local. | Documentar el equivalente servidor: no borrar auditoría, traducir datos del usuario ni convertir localStorage en base maestra. No crear un botón sólo por copiar el offline. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-292 / O-292 | Persistencia y recuperación: Descargar episodio completo de cuarentena | ausente | No portar reparación de inventario local como autoridad. Definir experiencia equivalente de error/recuperación y exportación autorizada; recuperación nativa permanece canal operativo. Comportamiento específico de archivo/almacenamiento offline o duplicación clásica. Mantener el objetivo útil mediante servidor/diario seguro; no crear otro inventario maestro local. | Documentar el equivalente servidor: no borrar auditoría, traducir datos del usuario ni convertir localStorage en base maestra. No crear un botón sólo por copiar el offline. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-293 / O-293 | Persistencia y recuperación: Descargar autosave crudo de episodio | ausente | No portar reparación de inventario local como autoridad. Definir experiencia equivalente de error/recuperación y exportación autorizada; recuperación nativa permanece canal operativo. Comportamiento específico de archivo/almacenamiento offline o duplicación clásica. Mantener el objetivo útil mediante servidor/diario seguro; no crear otro inventario maestro local. | Documentar el equivalente servidor: no borrar auditoría, traducir datos del usuario ni convertir localStorage en base maestra. No crear un botón sólo por copiar el offline. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-294 / O-294 | Persistencia y recuperación: Eliminar episodio de cuarentena | ausente | No portar reparación de inventario local como autoridad. Definir experiencia equivalente de error/recuperación y exportación autorizada; recuperación nativa permanece canal operativo. Comportamiento específico de archivo/almacenamiento offline o duplicación clásica. Mantener el objetivo útil mediante servidor/diario seguro; no crear otro inventario maestro local. | Documentar el equivalente servidor: no borrar auditoría, traducir datos del usuario ni convertir localStorage en base maestra. No crear un botón sólo por copiar el offline. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-295 / O-295 | Persistencia y recuperación: Exportar proyecto visible en recuperación | ausente | No portar reparación de inventario local como autoridad. Definir experiencia equivalente de error/recuperación y exportación autorizada; recuperación nativa permanece canal operativo. Recuperación de servidor o de borradores/diarios por actor y ámbito; no exponer copias crudas de datos ajenos. | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-296 / O-296 | Persistencia y recuperación: Descargar rescate crudo desde recuperación | ausente | No portar reparación de inventario local como autoridad. Definir experiencia equivalente de error/recuperación y exportación autorizada; recuperación nativa permanece canal operativo. Recuperación de servidor o de borradores/diarios por actor y ámbito; no exponer copias crudas de datos ajenos. | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-297 / O-297 | Persistencia y recuperación: Reintentar lectura de almacenamiento | ausente | No portar reparación de inventario local como autoridad. Definir experiencia equivalente de error/recuperación y exportación autorizada; recuperación nativa permanece canal operativo. Recuperación de servidor o de borradores/diarios por actor y ámbito; no exponer copias crudas de datos ajenos. | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-298 / O-298 | Fallo de aplicación: Mostrar pantalla de recuperación de render | ausente | Añadir recuperación de aplicación adaptada al servidor, sin exponer secretos/tokens ni confundir journal con copia completa. Recuperación de servidor o de borradores/diarios por actor y ámbito; no exponer copias crudas de datos ajenos. | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-299 / O-299 | Fallo de aplicación: Descargar rescate completo tras excepción | ausente | Añadir recuperación de aplicación adaptada al servidor, sin exponer secretos/tokens ni confundir journal con copia completa. Recuperación de servidor o de borradores/diarios por actor y ámbito; no exponer copias crudas de datos ajenos. | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-300 / O-300 | Fallo de aplicación: Descargar sólo autosave tras excepción | ausente | Añadir recuperación de aplicación adaptada al servidor, sin exponer secretos/tokens ni confundir journal con copia completa. Recuperación de servidor o de borradores/diarios por actor y ámbito; no exponer copias crudas de datos ajenos. | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-301 / O-301 | Fallo de aplicación: Reintentar render tras excepción | ausente | Añadir recuperación de aplicación adaptada al servidor, sin exponer secretos/tokens ni confundir journal con copia completa. Recuperación de servidor o de borradores/diarios por actor y ámbito; no exponer copias crudas de datos ajenos. | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-05: 126, 127, 128, 129, 130, 131 |
| PAR-302 / O-302 | Fallo de aplicación: Consultar detalles de excepción | ausente | Añadir recuperación de aplicación adaptada al servidor, sin exponer secretos/tokens ni confundir journal con copia completa. Recuperación de servidor o de borradores/diarios por actor y ámbito; no exponer copias crudas de datos ajenos. | Validar antes del commit; destino/ámbito explícitos; conservar identidades y cables. Negativos de formato/topología/permisos, rollback e idempotencia; relectura desde otra sesión. Separar intercambio de inventario de backup PostgreSQL y custodia MFA. | P-05: 126, 127, 128, 129, 130, 131 |

## Apéndice B · Peticiones de Wascar y dónde se cierran

| Petición | Resultado esperado y situación registrada | Responsable | Pasos |
|---|---|---|---|
| REQ-UX-01 · Racks primero, información secundaria plegable | Rack/frontal/trasera visibles al llegar; PoE y datos extensos desplegables sin ocultar errores o cambios pendientes. Estado documental: implementado_y_probado_en_laboratorio_pendiente_integracion_y_qa. | P-11 | 162, 163, 164, 165, 166, 167 |
| REQ-UX-02 · Administración de usuarios y grupos más visual | Lista/búsqueda, usuario seleccionado, pertenencias, ámbitos y métodos claros; distinguir global/cliente/técnico/lector sin otorgar derechos por nombre de rol. Estado documental: pendiente_de_mejora_y_aceptacion. | A-02 | 86, 87, 88, 89, 90 |
| REQ-UX-03 · Barra compacta de informes y exportaciones | Acciones agrupadas por rack/cliente; controles técnicos extensos bajo demanda; formato de cada descarga identificado correctamente. Estado documental: contexto_y_metadatos_de_tres_exportadores_probados_pendiente_integracion_y_resto_de_formatos. | P-07 | 138, 139, 140, 141, 142, 143 |
| REQ-UX-04 · Datos sintéticos completos y repetibles para QA | Demo50 y prueba de diez actores/ambitos ya realizados en laboratorio con umbrales de humo previos. D11 carga50/2553comandos verificada en185.681s y backup posterior completo; MFA/TLS del cargador probado aparte en cuenta sintetica. Faltan carga extendida instalada, memoria/CPU/consultas/picos/recuperacion y aceptacion practica, no crear de nuevo la demo. Estado documental: demo50_cargada_y_verificada_D11_QA_visual_pendiente. | E-05 | 243, 244, 245, 246, 247 |
| REQ-UX-05 · Exportar/importar inventario y backup desde dashboard | Separar intercambio JSON de copia PostgreSQL/secretos. Acceso administrativo, progreso, integridad, destino nuevo y recuperación MFA comprobada; no sobrescribir una base silenciosamente. Exportación actual RackClickInventory-v1 por cliente probada PG17.11/API/Edge,4MiB sin truncar, recibo/SHA256, sólo inventario. Importación/merge/originalRC9/backup PostgreSQL y Windows43 siguen pendientes; docs/PUNTO3-FUNCIONES-PENDIENTES.md. Estado documental: exportacion_JSON_actual_probada_importacion_y_backup_pendientes. | R-04 | 207, 208, 209, 210, 211 |
| REQ-UX-06 · Operación sencilla entre casa y trabajo | Nombre/origen/red/certificado coherentes y mantenimiento guiado, sin otra secuencia manual de editar varios archivos; no modificar la IP de Windows sin instrucción. Estado documental: herramientas_existentes_cierre_facilidad_pendiente. | W-04 | 176, 177, 178, 179, 180, 181 |
| REQ-UX-07 · Acceso privado del operador y datos de conexión DB | Indicar cómo obtener credenciales locales autorizadas de cada instancia y usar HeidiSQL cuando proceda; nunca incluir contraseñas en manuales públicos o ZIP documental. Estado documental: conciliar_documentacion_y_acceso_privado. | E-04 | 237, 238, 239, 240, 241, 242 |
| REQ-UX-08 · MFA propio y administrativo con política confirmada | Enrolamiento/login/GUI y politica45 existentes; F-07.01-.04 acreditados. D11 tiene proveedor real y prueba HTTPS/DPAPI de cuenta sintetica. Falta cierre integral y escenarios pendientes; no crear otro login. Codigos de recuperacion del punto3 probados en desarrollo43, no canje nativo en D. Conservar politica45 y exencion global confirmadas; recuperacion/emergencia/rotacion y aceptacion pendientes. Estado documental: implementado_parcial_cierre_y_recuperacion_pendientes. | F-10 | 34, 35, 36, 37, 38 |
| REQ-UX-09 · Avisos multiusuario comprensibles | Otro usuario ve qué cambió y dónde, sin perder su borrador ni inventar contexto histórico; ámbitos y revocación vigentes. Estado documental: implementacion_existente_matriz_final_pendiente. | P-09 | 150, 151, 152, 153, 154, 155 |
| REQ-UX-10 · QA y manual paso a paso para una sola persona | Ubicación/botón/campo, resultado esperado, rol, disponibilidad y candidata; conservar Pass/NotPass/observaciones y exportación de Wascar. Estado documental: proceso_existente_mantener_por_candidata. | E-05 | 243, 244, 245, 246, 247 |
| REQ-HW-MOUNT-01 · Montaje explícito y físico antes de ampliar marcas | Montajes y contratos probados por familias, incluidos en43 y Demo50 de D. Conservar IDs/puertos/cables. Faltan reservas explicitadas y aceptacion, no repetir bandeja/firewall desde cero. Estado documental: contrato_y_catalogo43_integrados_D11_QA_pendiente. | C-HW-02 | 259 |
| REQ-HW-VISUAL-01 · Carcasa real para modelos principales y genérica para el resto | 506/506 seleccionados integrados con868revisiones/861comerciales; tecnica interactiva aprobada conservada. Demo50 disponible en D11; faltan aceptacion visual, reservas/fuentes y mantenimiento. Los dibujados no son fotografias redistribuidas ni todos los modelos del mercado. Estado documental: seleccion506_integrada_y_cargada_D11_QA_visual_pendiente. | C-HW-04 | 261 |
| REQ-CATALOGO-BUSQUEDA-01 · Selección compacta por búsqueda, sin lista larga en el rack | Buscador compacto por marca/familia/modelo/SKU y alias sofos-&gt;Sophos ya integrado. Faltan QA de busqueda/teclado y excepciones de configuracion; no crear una lista larga ni volver a instalar perfiles. Estado documental: selector868_integrado_D11_QA_pendiente. | C-HW-04 | 261 |
| REQ-DE-CPE-01 · Routers, repetidores y familias habituales de Alemania | Seis routers FRITZ!/DrayTek y diez repetidores FRITZ!,TP-Link,devolo,Telekom instalados enD45 mediante actualización revisada y continuaciones registradas. Servicio/HTTPS/backup45 verificados;datos/MFA conservados. Falta revisiónvisual deWascar y resto de sondeo; selección506/pesos intactos. Estado documental: dieciseis_modelos_instalados_D45_QA_visual_pendiente. | C-HW-07 | 264 |
| REQ-UX-RACK-02 · Proporciones, etiquetas y desplazamiento en soportes | Mínimosporcara/objetivos24px,anchochildrelativoapadreconpisoUIacotado,ampliaciónconrelayout,captionsyrevisionesplegables,nombrescompletosconservados. Faltan aceptaciónvisualyactualizacióncompletaautorizadaenD. Laobservacióndebotonesoffline reutiliza302acciones;noduplicarplanes. Estado documental: corregido_desarrollo_revision_visual_independiente_candidata_instalada_pendiente. | P-11 | 162, 163, 164, 165, 166, 167 |

## Apéndice C · Subpasos que ya tienen crédito

Se conservan por trazabilidad; no se ofrecen como nueva implementación ni se suman otra vez.

| ID | Resultado / comprobación acreditada |
|---|---|
| F-01.01 | Clasificar hallazgos de secretos y tratar sólo credenciales reales: Clasificar candidatos e indeterminados privados con trazabilidad por ruta/commit y sin publicar valores. |
| F-01.02 | Clasificar hallazgos de secretos y tratar sólo credenciales reales: Si una credencial es real, coordinar revocación/rotación con la instancia afectada; corregir exposición y volver a verificar cambios/artefactos relevantes. Para el antecedente run-1 del25.10.2026 sin salida conservada, se admite sólo el archivo administrativo expreso documentado, con incertidumbre y reapertura obligatoria; no clasifica como falso positivo ni prueba revocación. |
| F-01.03 | Clasificar hallazgos de secretos y tratar sólo credenciales reales: Registrar falsos positivos y criterio específico sin supresiones amplias; reescritura de historial no está autorizada por defecto. |
| F-01.04 | Clasificar hallazgos de secretos y tratar sólo credenciales reales: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda. |
| F-02.01 | Cifrar configuración SQL y recuperar sus secretos en otra instancia: Diseñar e integrar protección compatible con cuenta/instancia reales y canal mínimo de lectura para el servicio; conservar separación owner/migración/runtime. |
| F-02.02 | Cifrar configuración SQL y recuperar sus secretos en otra instancia: Actualizar operadores/fichas de acceso, diagnóstico y backup para no filtrar la clave ni depender de copiar un secreto ligado al host antiguo. |
| F-02.03 | Cifrar configuración SQL y recuperar sus secretos en otra instancia: Ensayar reanudación y Restore en destino nuevo con identidad/roles/claves nuevos; error explícito ante clave ausente/incorrecta. |
| F-02.04 | Cifrar configuración SQL y recuperar sus secretos en otra instancia: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda. |
| F-03.01 | Registrar decisión de custodia y ubicación definitiva D2: Wascar confirma responsable/medio del sobre y de su contraseña por canales privados, y ubicación definitiva del almacén mfa-keys. |
| F-03.02 | Registrar decisión de custodia y ubicación definitiva D2: Desarrollo concreta las condiciones técnicas de la revisión: recuperación restringida sin clave, límites/cabecera autenticada del KDF y publicación recuperable entre disco/DB. |
| F-03.03 | Registrar decisión de custodia y ubicación definitiva D2: Registrar límites de amenaza: DPAPI LocalMachine no aísla del administrador local ni del proceso de servicio comprometido. |
| F-04.01 | Implementar proveedor TOTP Windows bajo la identidad real del servicio: Crear almacén separado de management con ACL seguras desde el primer instante y escrituras atómicas por instalador/operador. |
| F-04.02 | Implementar proveedor TOTP Windows bajo la identidad real del servicio: Dar sólo lectura al SID efectivo del servicio y mantener management cerrado; comprobar padres, herencia y reparse. |
| F-04.03 | Implementar proveedor TOTP Windows bajo la identidad real del servicio: Conectar proveedor real al producto sólo tras D2; rechazar claves/versiones ausentes sin regeneración silenciosa ni password-only. |
| F-04.04 | Implementar proveedor TOTP Windows bajo la identidad real del servicio: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda. |
| F-05.01 | Implementar sobre portable autenticado y restauración de claves: Validar magia/versión/algoritmo, tamaños, codificación canónica y límites min/max de iteraciones antes de KDF; autenticar cabecera completa como AAD. |
| F-05.02 | Implementar sobre portable autenticado y restauración de claves: Medir coste del parámetro propuesto600000 en Windows antes de fijarlo; no adoptarlo por silencio. |
| F-05.03 | Implementar sobre portable autenticado y restauración de claves: Probar contraseña errónea, alteración, truncado, datos extra, versión/algoritmo desconocidos y coste/tamaño fuera de rango. |
| F-05.04 | Implementar sobre portable autenticado y restauración de claves: Recuperar anillo en otra instancia Windows preservando AAD Systemhaus/usuario/versión o mediante reenvoltura explícita; sobre y contraseña separados del dump. |
| F-05.05 | Implementar sobre portable autenticado y restauración de claves: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda. |
| F-06.01 | Cerrar rotación y recuperación coherente entre anillo y PostgreSQL: Especificar fases: persistir/verificar clave nueva antes de usarla, conservar versiones requeridas, reenvolver factores y publicar anillo coherente. |
| F-06.02 | Cerrar rotación y recuperación coherente entre anillo y PostgreSQL: Retirar una versión sólo si ningún factor ni backup retenido la necesita; incluir inventario de versiones en backup/sobre. |
| F-06.03 | Cerrar rotación y recuperación coherente entre anillo y PostgreSQL: Inyectar caída antes/después de cada publicación y commit; reinicio/Restore deben identificar estado y recuperar sin perder factores. |
| F-06.04 | Cerrar rotación y recuperación coherente entre anillo y PostgreSQL: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda. |
| F-07.01 | Completar enrolamiento restringido cuando MFA sea exigible: Después de password válido emitir desafío enroll de finalidad fija, hash/CSRF propio, cinco minutos y consumo único; sin app_session/autoridad API. |
| F-07.02 | Completar enrolamiento restringido cuando MFA sea exigible: Presentar secreto/QR sólo al usuario durante proceso, sin URL/log/auditoría/historial; confirmar primer TOTP antes de activar factor. |
| F-07.03 | Completar enrolamiento restringido cuando MFA sea exigible: Emitir sesión/CSRF nuevos y confirmar factor/consumir desafío en una sola transacción; revalidar cuenta/política/caducidad después de locks. |
| F-07.04 | Completar enrolamiento restringido cuando MFA sea exigible: Alta nueva conserva45días desdecreación y cuenta existente desdeactivación persistida; administrador globalSystemhaus exento; el servidor exige enrolamiento al vencer o al activar/exigirMFA; probar código erróneo/caducado/repetido, reintento/respuesta perdida y dos confirmaciones concurrentes. |
| F-07.05 | Completar enrolamiento restringido cuando MFA sea exigible: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda. |
| F-08.01 | Implementar códigos de recuperación y reenrolamiento restringido: Generar y mostrar una sola vez códigos por usuario; almacenar sólo hashes con sal conforme D2, sin dependencia de clave TOTP. |
| F-08.02 | Implementar códigos de recuperación y reenrolamiento restringido: Concretar e implementar si password+código concede sólo recuperación restringida hasta reenrolar; no dejar frase ambigua que emita sesión normal antes de nuevo factor. |
| F-08.03 | Implementar códigos de recuperación y reenrolamiento restringido: Consumir transaccionalmente, invalidar sesiones/desafíos/códigos anteriores según contrato y probar consumo concurrente/replay/rollback/secretos. |
| F-08.04 | Implementar códigos de recuperación y reenrolamiento restringido: Garantizar vía administrativa de recuperación con códigos válidos sin bloquear último administrador. |
| F-08.05 | Implementar códigos de recuperación y reenrolamiento restringido: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda. |
| F-09.01 | Implementar recuperación local cuando no quedan clave, sobre ni códigos: Autorizar sólo operador local SYSTEM/Administradores; sin web anónima ni bypass password-only. |
| F-09.02 | Implementar recuperación local cuando no quedan clave, sobre ni códigos: Permitir preparar anillo nuevo explícitamente, conservar material anterior recuperable, retirar factores ilegibles del uso y marcar enrolamiento pendiente sin borrar DB. |
| F-09.03 | Implementar recuperación local cuando no quedan clave, sobre ni códigos: Revocar sesiones/desafíos y registrar auditoría sin secretos, preservando recuperación de último administrador. |
| F-09.04 | Implementar recuperación local cuando no quedan clave, sobre ni códigos: Ensayar pérdida simulada total, arranque fallido explícito, recuperación local y vuelta mediante enrolamiento restringido. |
| I-01.01 | Ofrecer e integrar Deshacer de crecimiento/reducción pura de grupos: Crear candidato desde operación confirmada propia, actor/cliente/revisión; ningún before del navegador. |
| I-01.02 | Ofrecer e integrar Deshacer de crecimiento/reducción pura de grupos: Mostrar alcance/confirmación de retirar/restaurar grupos/puertos/cables y límites de evidencia completa1..256puertos/32grupos/256IDs combinados. |
| I-01.03 | Ofrecer e integrar Deshacer de crecimiento/reducción pura de grupos: Integrar consulta/reintento/cancelación originales ante incertidumbre e invalidación tras otra revisión/permiso/cuenta/cliente. |
| I-01.04 | Ofrecer e integrar Deshacer de crecimiento/reducción pura de grupos: Decidir presentación de contexto estructural: hoy notAvailable explícito; no rotular puertos eliminados como changedIds. |
| I-04.01 | Cerrar variantes de jerarquía, racks, equipos y orden ya implementados: Cerrar lista de controles/comandos existentes y reutilizar prueba; no rehacer lotes ni CRUD por tabla51. |
| I-04.02 | Cerrar variantes de jerarquía, racks, equipos y orden ya implementados: Focos de editar/reasignar rack, reducciónU con ocupación, equipo/metadatos/presets y tooltips por UUID/homónimos. |
| I-04.03 | Cerrar variantes de jerarquía, racks, equipos y orden ya implementados: Duplicado sin/con cables y reserved confirmado válido; conservar negativos existentes. |
| I-04.04 | Cerrar variantes de jerarquía, racks, equipos y orden ya implementados: Flechas/drag/táctil según controles ofrecidos; orden documental y local/cross sin inventar posiciónU. |
| I-04.05 | Cerrar variantes de jerarquía, racks, equipos y orden ya implementados: Borrado individual/conjunto con objetos de sala y cables incidentes: commit único, impacto/cancelación exactos. |
| I-06.02 | Completar verificación de Dosen y finales ya soportados en sala: Cerrar edición/renombrado/puertos/roles/borrado con impacto de objetos de sala ofrecidos por GUI. |
| W-01.01 | Corregir parada D14-07 y validación de edición del generador: Integrar publicación atómica de stop-request en el runtime de producto, conservando identidad/ACL y el caso de dos Stop concurrentes. |
| W-01.02 | Corregir parada D14-07 y validación de edición del generador: Validar edición y nombres finales antes de escribir payload/envoltorio; rechazar traversal y combinaciones de pins incoherentes sin salidas. |
| W-01.03 | Corregir parada D14-07 y validación de edición del generador: Ejecutar focos de carrera original/corregida, negativos de edición y Start/Backup/Stop/reinicio del runtime corregido. |
| W-01.04 | Corregir parada D14-07 y validación de edición del generador: Revisar los cambios y registrar hashes; no reabrir D14-05/D14-06 ya corregidos ni modificar paquetes congelados. |
| W-01.05 | Corregir parada D14-07 y validación de edición del generador: Comprobar el criterio de cierre y registrar revisión independiente/evidencia del resultado; aceptación manual sólo donde corresponda. |
| W-02.01 | Instalar desde cero en Windows limpio y declarar la matriz soportada: Preparar otra VM limpia Windows Server2025 sin AD DS y registrar imagen/versión, cuentas, discos y red; conservar la VM QA. |
| W-02.02 | Instalar desde cero en Windows limpio y declarar la matriz soportada: Ejecutar la entrega completa sin SDK/Node/Python previos; comprobar detección/instalación de runtime, PostgreSQL17 y CRT, incluido reinicio requerido. |

## Apéndice D · Referencias y herramientas, no requisitos del producto

- **REF-01 · REA y Codebase Memory:** Mapa/búsqueda de código para el equipo; no funcionalidad de documentación de red para el usuario. Fuente: [docs/PROTOCOLO-REUNION-EVOLUCION-FUTURA-25-10-2026.md](../docs/PROTOCOLO-REUNION-EVOLUCION-FUTURA-25-10-2026.md).
- **REF-02 · Patchdocs y Pathfinder:** Ideas funcionales/de presentación y condiciones de acceso; no dependencia ni instalador integrado. Fuente: [docs/PROTOCOLO-REUNION-EVOLUCION-FUTURA-25-10-2026.md](../docs/PROTOCOLO-REUNION-EVOLUCION-FUTURA-25-10-2026.md).
- **REF-03 · LibreNMS, Netdisco, GLPI Agent, NetXMS y Lansweeper:** Evaluar API, compatibilidad y licencia antes de elegir una integración; no instalar todos los productos. Fuente: [docs/PROTOCOLO-REUNION-EVOLUCION-FUTURA-25-10-2026.md](../docs/PROTOCOLO-REUNION-EVOLUCION-FUTURA-25-10-2026.md).
- **REF-04 · NetBox, DeviceType Library, RackScope y demás biblioteca local:** Reutilizar definiciones/conceptos compatibles con fuentes/licencias; catálogo concreto enC-HW y sin sustituir el servidor RackClick. Fuente: [docs/PROTOCOLO-REUNION-EVOLUCION-FUTURA-25-10-2026.md](../docs/PROTOCOLO-REUNION-EVOLUCION-FUTURA-25-10-2026.md).
- **REF-05 · ESEngine y otros proyectos descargados:** Conservar procedencia/decisión; no convertir cada repositorio en una función que hay que implementar. Fuente: [docs/PROTOCOLO-REUNION-EVOLUCION-FUTURA-25-10-2026.md](../docs/PROTOCOLO-REUNION-EVOLUCION-FUTURA-25-10-2026.md).
- **REF-06 · Skills, plugins y herramientas de pruebas:** Usar herramientas detectadas y pertinentes; no falta instalar más por defecto ni se puntúa su número. Fuente: [docs/PROTOCOLO-REUNION-EVOLUCION-FUTURA-25-10-2026.md](../docs/PROTOCOLO-REUNION-EVOLUCION-FUTURA-25-10-2026.md).

## Actualización y límites

La lista abarca todo el alcance registrado en las fuentes actuales; no afirma que se conozcan defectos aún no descubiertos. Nuevos requisitos se incorporan con decisión y versión explicada, sin renumerar ni aumentar pesos silenciosamente. Cerrar un paso exige su evidencia y revisión; esta lista no lo cierra.

```powershell
C:/Python312/python.exe -X utf8 -B tools/build_master_roadmap.py --write
C:/Python312/python.exe -X utf8 -B tools/build_remaining_work_plan.py --write
C:/Python312/python.exe -X utf8 -B tools/build_master_roadmap.py --check
C:/Python312/python.exe -X utf8 -B tools/build_remaining_work_plan.py --check
```

Fuentes y SHA256 completos en el JSON generado. No se modifica el ledger, los pesos, el producto, las VM ni los resultados de QA.
