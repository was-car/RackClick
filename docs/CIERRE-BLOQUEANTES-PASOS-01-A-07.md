# Bloqueantes de los pasos 1–7 · resolución técnica

**Actualización03.11 con decisión del propietario:** los pasos1–7 están cerrados, y también el checkpoint8 de revisión de F-02. **2/4 se cierran administrativamente con incertidumbre y reapertura**, según [decisión expresa y enmiendav3](DECISION-F01-ARCHIVO-ADMINISTRATIVO-03-11-2026.md); no se declaran falso positivo ni revocación.5/6/7 tienen cierre técnico: E13 postboot y Restore14-r2 con otro SID/material,20clientes,operadores/backup/reanudación. No hay postboot14 ni adopción general. [Ensayo](../evidence/s1-20261103/e13-postboot-restore14/RESULTADOS.md). D se conserva; no instalar12 ni14original.

02.11.2026. Continuación de la revisión solicitada por Wascar. Se conserva D con su instalación11, MFA, catálogo y Demo50. No se instala encima ni se sustituyen sus archivos. No hay commits ni publicación.

## Qué se ha resuelto

- **Entrega SQL integrada:** nueva publicación del servidor con el código SQL protegido, frontend vigente del punto3, perfil43 cerrado y bundle de26 operadores. Incluye `RackClick.SqlSecrets.ps1`; el lector nativo, Stage y los inventarios aceptan esa combinación explícita. Los paquetes anteriores conservan sus bytes.
- **Credenciales mínimas:** New y Restore nativos seleccionan el manifiesto3 para esta candidata. No conservan las contraseñas de cluster/owner. Runtime usa su material protegido; backup dispone de otro rol SQL con CONNECT/USAGE/SELECT y sin escritura ni DDL. Los privilegios elevados se usan únicamente durante la preparación nueva.
- **Acceso privado compatible:** lectura explícita de los manifiestos1/2/3 y sus inventarios exactos. La ficha exportada no contiene contraseñas. No se ha ampliado la confianza del lector productivo para que pase el laboratorio.
- **Peticiones transitorias:** las peticiones protegidas de preparación se consumen antes de arrancar el hijo. New/Restore mínimos no declaran éxito si queda una petición cifrada pendiente. Se conserva la limpieza exclusiva de los temporales libpq.
- **Reanudación y recuperación:** PG17.11 real,20 clientes sintéticos, roles/material nuevos, dos reanudaciones y nuevo backup. El SQL de backup no puede borrar y el runtime no puede crear tablas. Ciphertext de otro contexto y material ausente se rechazan.
- **Instalador12 y manual:** paquete nuevo con las dependencias existentes, New/Restore, visor y manual autónomo00–07. No es una actualización ya aplicada ni una instalación Windows aceptada.

La separación es de privilegios SQL. No se afirma protección frente al compromiso completo del administrador Windows o del actor que administra los archivos PostgreSQL.

## Estado de cada uno de los siete pasos

| Paso | Resultado de esta tanda | Qué queda para cumplir su cierre |
|---|---|---|
| 1 · F-01.01 | Clasificación anterior reutilizada, sin repetirla ni ampliar su alcance. | Ya cerrado en el conjunto histórico revisado. |
| 2 · F-01.02 | Investigación agotada; Wascar autoriza archivar con incertidumbre explícita. Enmienda limitadav3 revisada antes de acreditar. | **Cerrado administrativamente.** Indeterminado, sin falso positivo/revocación demostrada; reapertura obligatoria y retirada de crédito si aparece evidencia concreta. |
| 3 · F-01.03 | Registro contextual anterior conservado; no se añaden supresiones del escáner. | Ya cerrado en su registro revisado. |
| 4 · F-01.04 | Revisión independiente de la decisión/enmiendav3 y alcance; controles anteriores conservados. | **Cerrado como revisión de disposición administrativa.** No es una prueba técnica de ausencia de exposición ni aceptación del producto. |
| 5 · F-02.01 | Servicio13 Running/Auto bajo SID real no administrador,HTTPS43,SQL protegido y separación de roles; contratos/implementación iguales a14-r2. | **Cumplido y revisado.** Sólo se acredita su5/8; reboot y Restore conservan sus propios pasos. |
| 6 · F-02.02 | Getter instalado14-r2, ficha real sin contraseñas, diagnóstico y backup bajo actor real; origen sólo dump/manifiesto. | **Cumplido y revisado.** No habilita por arrastre QA manual de D. |
| 7 · F-02.03 | Restore LEAO→E con cuenta/SID/roles/material nuevos,20clientes,HTTPS y backup; reanudación del servicio sin regenerar material. | **Cumplido y revisado.** Error del comparador y conciliación conservados. Postboot14 sigue en W-03.03/R-04.04; no es otro gate añadido a este criterio literal. |

## Entrega y pruebas

La entrega revisada se identifica en [RESULTADOS.md](../evidence/s1-20261102/cierre-bloqueantes-01-07/RESULTADOS.md), con sus hashes completos, fallos intermedios y alcance de las pruebas. No usar los artefactos intermedios r1 como entrega final. El manual [INSTALADOR12-SQL-PROTEGIDO.md](INSTALADOR12-SQL-PROTEGIDO.md) explica carpetas, PowerShell, verificación, instalación, reinicio y recuperación.

El protocolo de mantenimiento es [SQL-PROTEGIDO-INSTANCIA3.md](SQL-PROTEGIDO-INSTANCIA3.md): las actualizaciones con DDL se preparan mediante Restore a instancia nueva. No hay una contraseña owner oculta que el servicio deba poder descifrar, ni se añade mantenimiento DDL en sitio de forma implícita.

## Siguiente operación concreta

El reinicio confirmado de E y el Restore14-r2 ya están verificados en sus alcances. New13 sigue en5443 y el recuperado con20clientes en5444. No repetir New/Restore ni operar D. Para el postboot del recuperado, pendiente en sus criterios Windows, Wascar reinicia E desde Windows y se usa el verificador original14. F01 sólo se reabre si aparece evidencia concreta; no repetir investigación agotada o rotar por conjetura. Siguiente resultado numerado abierto:9/F-03.02, según priorización posterior.

**Contabilidad vigente03.11:** 2479/168 = **14,76/100** del índice de cierre. Sobre el corte técnico13,51 se añaden5/4 por disposición/revisión administrativa F01, sin duplicar créditos. No es porcentaje global nuevo ni mejora técnica de seguridad medida. No hay tareas o pesos nuevos; la excepción F01 y su nueva huella están versionadas explícitamente. El checkpoint8 sólo registra la revisión final de F-02 ya realizada.
