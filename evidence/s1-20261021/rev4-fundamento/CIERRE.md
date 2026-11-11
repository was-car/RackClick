# Revisión 4 · fundamento de seguridad y pruebas

21.10.2026, Windows/LEAO, SDK10.0.401 fijado. Base Git `e162398`, rama local `improvements/rev4-security-foundation`. Wascar pide implementar los dos documentos de Downloads; revisión4 es la referencia principal. Originales conservados y SHA registrados en [matriz](../../../docs/IMPLEMENTACION-REV4.md).

## Cambios y motivos

1. **Higiene (worker rev4_tooling21):** Gitleaks8.30.1 oficial, assets/checksums fijados; scanner/hook local que comprueba índice, working tree versionado e historial alcanzable. Captura stdout/stderr, fuerza redacción y conserva sólo metadatos privados. Rechaza privados/tipos/rutas inválidas antes de leer contenido y falla ante herramienta ausente/alterada. No hay supresiones amplias, rotación ni reescritura histórica. Workflow manual local, sin remoto ni publicación.
2. **Pruebas (worker rev4_test_foundation21):** proyecto adicional xUnit con versiones exactas/lock y Testcontainers.PostgreSql4.16.0. Primer restore4.10.0 rechazado por NU1903/SSH.NET2025.1.0; versión final resuelve2026.0.0 sin silenciar auditoría. Prueba real preparada para bootstrap Unicode100/login/sesión persistida/contraseña errónea en contenedor PG17.11 nuevo y aislado; aquí no se ejecutó por ausencia de Docker.
3. **Servidor/coordinador:** cabeceras Referrer-Policy, X-Frame-Options y Permissions-Policy; HSTS de un día para DNS/HTTPS, conservando IP/loopback, CSP/CSRF/Origin/no-CORS. Program.cs añade una llamada a `HttpSecurityHeaders`; sin rutas/DTO/esquema ni frontend modificados. Reglas C.0 en AGENTS, binlogs/dumps de memoria fuera de Git. Tres skills individuales oficiales .NET instaladas a commit fijo mediante skill-installer Git sparse (ZIP encontró MAX_PATH), disponibles próximo turno.

La matriz C.0–C.19 distingue funciones existentes de propuestas pendientes. Ya había runner SQL transaccional con hashes, rate limiting/bloqueo de login, CSRF, auditoría PostgreSQL, idiomas y SVG. No introducir DbUp/EF Core, otro CSRF, Serilog o rediseño sólo por suponer ausentes esos controles. [MFA](../../../docs/AUTENTICACION-MFA-S1.md) registra diseño y dependencias, no una función implementada; Wascar confirma que será obligatorio para todos antes de producción.

## Ejecuciones nuevas y revisión independiente

| Comprobación | Resultado real y límite |
|---|---|
| Compilación Release, nuevo proyecto y servidor | Correcta, sin avisos. SDK401; dependencias/locks de producto intactos. |
| xUnit | 10PASS,0FAIL,1SKIP. PostgreSQL omitido por Docker ausente. |
| Docker exigido, filtro PG | 0PASS,1FAIL esperado,0SKIP; salida1. Impide aprobación por omisión. |
| Servidor ASP.NET real, rutas de rechazo/seguridad | 9/9PASS, servidor temporal loopback, DB inaccesible deliberadamente. No acredita PostgreSQL. |
| Scanner/hook | Autor11/11 de regresión y foco posterior merge1/1:12 casos distintos. Revisor10/10 y focos posteriores merge1/1/triage1/1; no se atribuyen a una única suite12. Fixtures Git propios y valores sintéticos. |
| Auditoría NuGet del producto | Salida0; no se informaron paquetes vulnerables conocidos en esa consulta al feed oficial, directos/transitivos. No equivale a SAST. |
| Guías QA | Generador salida0; catálogo110, guía y plan sin cambios de hash. No casos disponibles nuevos ni resultados de Wascar modificados. |

Revisor distinto del implementador (`mfa_auth_contract21`), sin ediciones de producto: repitió9HTTP, xUnit10/1omitida, negativo Docker obligatorio y filtroCI10PASS. Reprodujo/cerró **cuatro P2**: guarda de privados históricos tardía, archivos introducidos sólo en merges omitidos, tests HTTPxUnit fuera de la solución no ejecutados por CI, jobPG sin dependencia del job principal. Los dos últimos tienen revisión estática y filtro local, no ejecución remota. No quedan bloqueadores abiertos dentro del alcance revisado; no es una auditoría integral de todo el producto.

Evidencias públicas saneadas: `coordinator-checks.json`, `http-windows.txt`, `quality-tests.json`, `product-nuget-audit.json`, `skills-provenance.json`, `secret-tooling.json`, `independent-review.json`. Los TRX, informes detallados de coincidencias y diff quedan privados bajo `.local/`. Las proyecciones públicas de informes normalizan mapas de hashes a listas ruta/SHA, conservando hash del original privado; nunca incluyen valores detectados.

## Resultado del barrido y trabajo pendiente

147 commits alcanzables,9.454 archivos tracked y11.339 entradas de metadatos comprobadas. Resultado **salida10/coincidencias**, no limpio:3.469 históricas y3.467 actuales; hay solapamiento entre ambos conjuntos, no6.936 secretos distintos. Todas activan la regla genérica.

Histórico:3.317 formas HEX64 en mapas de integridad de archivo,59UUID de solicitudes,23candidatos por contexto,69indeterminados y1contexto de fixture. Working: mismas categorías salvo67indeterminados. Son clasificaciones orientativas por forma/contexto: no prueban que una credencial sea falsa ni que el HEX sea el hash del archivo. No se suprime ningún hallazgo. Los candidatos/indeterminados requieren clasificación antes de declarar higiene completa o rotar claves que podrían afectar instalaciones existentes.

La última corrección `-m` para merges se comprobó por fixture y metadatos; el repositorio real tiene0merges y no se repitió un barrido global equivalente. El hook examina sólo cambios staged, no limpia el historial por pasar un commit.

Comprobación posterior del índice del grupo:30archivos,0coincidencias. Se reformuló una lista de palabras comunes en una entrada histórica del CHANGELOG que producía un falso positivo; no contenía una credencial y no se modificó la evidencia original ni se añadió una exclusión. Los recuentos del barrido global corresponden al estado anterior a incorporar este grupo; el hook comprueba los cambios nuevos completos. `staged-check.json` registra el resultado y modo100755 del hook. Este resultado limpio del índice no resuelve los candidatos históricos.

## Conservación y siguiente paso

Sin Docker instalado, contenedores o PostgreSQL ejecutados por este adaptador, cambio de VM/SCM/red, lectura de credenciales privadas reales, actualización de QA, nuevo instalador ni modificación de ZIP05/restauración02. Los dos archivos personales inicialmente untracked se conservan fuera del cambio.

Siguiente: clasificar coincidencias; concretar custodia y completar MFA para todos con recuperación y todos los formularios reauth; cifrado SQL/backups y ensayo portable; ejecutar PG Testcontainers/SAST/carga donde exista sandbox; integrar en candidata nueva revisada antes de QA. **Global aproximado78%, sin incremento** por añadir herramientas/tests/documentos. Adopción final sigue pendiente de Wascar.
