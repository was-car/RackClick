# Aplicación de las propuestas de revisión 4

21.10.2026. Rama local `improvements/rev4-security-foundation`, base `e162398`.
Wascar solicita implementar las propuestas recibidas. La revisión 4 prevalece sobre el borrador anterior; sus indicaciones de auditoría inicial se consideran contexto del documento, no una revocación de la autorización de desarrollo vigente.

Originales conservados en Downloads, sin copiarlos al producto:

| Documento | SHA256 |
|---|---|
| 02-RackClick.md | c3d4e582e2187efee5c43a7f20b39c9dadea4d22c9d996d4c9abb7c4dcff977f |
| Revisión 4 | 2d684509301740c55ef00e05105cbdc3dbed5c7f0ef02c84d12312d4db910b9e |

## Primer grupo implementado

- Reglas C.0 incorporadas a AGENTS.md; diagnósticos binlog/memoria excluidos de Git. Se conserva Npgsql directo, SQL versionado y la GUI RC9.
- Gitleaks oficial fijado, comprobación de archivos versionados/historial y hook de pre-commit. Las coincidencias históricas se conservan para clasificación; pasar el hook de cambios nuevos no certifica un historial limpio.
- Proyecto adicional `RackClick.Quality.Tests`: xUnit y Testcontainers.PostgreSql. No sustituye el ejecutable histórico de dominio ni las pruebas nativas Windows/PostgreSQL/Edge existentes. Docker no está instalado en LEAO: una prueba omitida no cuenta como PostgreSQL ejecutado.
- Cabeceras HTTP adicionales en respuestas exitosas y rechazadas: Referrer-Policy, X-Frame-Options, Permissions-Policy. HSTS de un día sólo para origen configurado DNS/HTTPS y petición HTTPS; sin preload, subdominios ni HSTS en IP/loopback HTTP. Se conservan CSP, no-store, CSRF y ausencia de CORS. Es código de desarrollo; la VM y los ZIP congelados no han sido actualizados.
- Tres skills oficiales de .NET instaladas en este perfil de Codex desde el commit fijado `c848e7fffab05c594f9b954c6f3beb373d108447`: `dotnet-webapi`, `analyzing-dotnet-performance`, `binlog-generation`. Estarán disponibles en el próximo turno. La descarga ZIP del instalador encontró MAX_PATH en Windows; se completó mediante su modo Git sparse, sin cambiar Windows ni sobrescribir skills existentes.
- Workflow local manual de seguridad preparado; no hay publicación ni ejecución en GitHub.

Resultados, revisión independiente y límites: [evidencia del grupo](../evidence/s1-20261021/rev4-fundamento/CIERRE.md). El avance global sigue aproximadamente en **78%**. Esta matriz no anuncia las veinte propuestas como terminadas.

## Contraste de C.0–C.19 con el producto

| Punto | Decisión y estado real |
|---|---|
| C.0 Reglas | Incorporadas. Revisar SQL/render por rutas y pruebas negativas; añadir una regla no acredita una auditoría exhaustiva del código. Runtime DML separado de owner/migración en `New-RackClickLabInstance.ps1` y SQL de fundamento. |
| C.1 Skills .NET | Tres skills oficiales instaladas y fijadas. No añadir EF Core. No declarar instalados plugins Anthropic en Codex. |
| C.2 MCP PostgreSQL | Pendiente en laboratorio dedicado, con rol de sólo lectura y modo restricted. No conectar MCP a los roles runtime de QA: tienen escritura y acceso fuera de los ámbitos de la API. `pg_stat_statements`/hypopg requieren comprobar soporte y necesidad en PostgreSQL Windows antes de instalar extensiones. |
| C.3 Rendimiento/caché | Pendiente medir diez sesiones y planes de consultas en laboratorio. No añadir Redis ni cachear autorizaciones/respuestas privadas. No se afirma un cuello de botella sin medición. |
| C.4 Strix | Diferido hasta sandbox aislado con backup probado. No ejecutado contra LEAO, VM, dominio ni red de Wascar. Docker ausente. |
| C.5 MFA | Implementación parcial, **no disponible para usuarios**. Enrolamiento backend/rutas entregados para revisión; cuatro hallazgos y HTTP positivo/concurrencia pendientes. [Dictamen y paquete de pruebas autorizado](REVISION-MFA-L1-CODEX-25-10-2026.md). Custodia/recuperación confirmadas; proveedor real/UI pendientes. Obligatorio para **todos antes de producción**. |
| C.6 Secretos | Gitleaks/hook implementados. Historial requiere clasificación y tratamiento de candidatos reales; no reescritura ni rotación ciega. Connection string actual en archivo privado con ACL sigue siendo texto plano: cifrado/recuperación ligado a cuenta/instancia pendiente. DPAPI de otros secretos del instalador no acredita cifrado SQL. |
| C.7 Hooks | Hook Git explícito y focal. No automatizar build completo tras cada edición ni instalar comandos exclusivos de Claude; evitar gasto y cambios simultáneos. |
| C.8 Agentes externos | No instalados: ya existen perfiles RackClick especializados. Se conserva separación implementador/revisor y gasto moderado. |
| C.9 Codex | AGENTS y skills individuales compatibles; no se copian configuraciones privadas de MCP ni se instalan marketplaces indiscriminadamente. |
| C.10 Frontend | RC9/React y pruebas Node/Edge CDP ya existen (`browser-inventory.mjs`, `api.test.mjs`, etc.). Mantener Click-Click. Playwright puede complementar recorridos, no es requisito para reemplazar los E2E actuales ni rediseñar. No se ejecutaron esos E2E en este grupo sin cambios GUI. |
| C.11 Backend | Nuevo proyecto xUnit/Testcontainers, paquetes fijados y lock propio. Docker requerido para PG contenedorizado; CI debe fallar si falta, no aprobar por omisión. Pruebas históricas PostgreSQL nativas conservadas y diferenciadas de nuevas ejecuciones. |
| C.12 CI | Borrador manual local: build, pruebas, auditoría NuGet y escáner. Publicación sigue sin autorización. CodeQL/Dependabot pendientes del repositorio remoto, licencia y decisión de publicación. |
| C.13 Hardening | Cabeceras añadidas y comprobadas. Rate limiter nativo ya limita login a 10/min/IP; bloqueo por cuenta ya existe. Auditoría NuGet ejecutada. SAST aún pendiente: no confundir escáner de secretos con análisis de SQLi/XSS. |
| C.14 Auditoría | Ya existe auditoría transaccional en PostgreSQL y logging estructurado mediante ILogger. Serilog no sustituye el registro de negocio ni es obligatorio para que exista auditoría. Retención/correlación/exportación operativa quedan por cerrar. |
| C.15 Backup | pg_dump/pg_restore y ensayos Windows a bases nuevas ya existen; funcionamiento Restore comunicado por Wascar. Cifrado portable y custodia/recuperación de claves siguen pendientes. No adoptar pgBackRest suponiendo soporte Windows nativo; tampoco contar un backup nuevo como restauración probada. |
| C.16 Migraciones | El supuesto de ausencia de runner es incorrecto: `SchemaMigrations.Apply` ya aplica SQL001–013 ordenado, registra hashes y rechaza alteraciones/huecos/versiones desconocidas; `PostgresStore.Migrate` usa transacción/bloqueo asesor. Conservarlo; no introducir DbUp duplicando esa autoridad. |
| C.17 CSRF/CORS | Ya existe Origin exacto, cookie Strict/HttpOnly/Secure y token CSRF derivado/vinculado a sesión, validado por servidor. No hay CORS habilitado. No cambiar a otro mecanismo de Antiforgery sin contrato/migración y pruebas de compatibilidad; MFA debe preservar y ampliar esta protección. |
| C.18 Idiomas | EN/DE/ES ya existen en GUI/adaptador y preferencias por cuenta; backend devuelve códigos estables localizados por frontend. No traducir nombres del usuario. Auditoría de cobertura/ordenación sí pendiente; cambiar collation sin ensayo sería una migración funcional. |
| C.19 Accesibilidad | Rack usa SVG (`inventory-rack-svg.ts`), no sólo canvas. Hay controles con ARIA; falta auditoría integral teclado/lector/contraste. Mantener diseño y Click-Click. |

## Orden siguiente y límites de entrega

1. Clasificar hallazgos del historial sin difundir valores; rotar únicamente credenciales identificadas y coordinando instalaciones que las usen.
2. Aplicar política MFA confirmada para todos y concretar custodia/recuperación; implementar desafío, enrolamiento, recuperación y todos los recorridos de login/reauth, con pruebas PostgreSQL y revisión independiente antes de habilitar GUI.
3. Cifrado de secretos/backup compatible con recuperación en otra máquina; comprobar exportación/restauración, no sólo lectura en el mismo Windows.
4. Ejecutar Testcontainers en host Docker Linux disponible; SAST y carga en laboratorio aislado. Medir antes de índices/caché.
5. Integrar cambios revisados en candidata completa nueva, actualizar guiones QA reales y realizar comprobaciones Windows/VM/reinicio/recuperación. No modificar ZIP05 ni datos/restauración ya utilizados por Wascar.

## Fuentes oficiales contrastadas

Instalación repetible en un perfil Codex que aún no contenga esas skills (con Git en PATH):

```powershell
C:/Python312/python.exe -B C:/Users/w.p/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py --repo dotnet/skills --ref c848e7fffab05c594f9b954c6f3beb373d108447 --method git --path plugins/dotnet-aspnetcore/skills/dotnet-webapi plugins/dotnet-diag/skills/analyzing-dotnet-performance plugins/dotnet-msbuild/skills/binlog-generation
```

El instalador rechaza destinos existentes; no borrarlos para forzar una actualización. Los binlogs que proponga una skill se guardan sólo bajo `.local/`, porque pueden contener valores de entorno.

- Skills .NET: https://github.com/dotnet/skills/tree/c848e7fffab05c594f9b954c6f3beb373d108447
- Skills Codex: https://learn.chatgpt.com/docs/build-skills
- HTTPS/HSTS: https://learn.microsoft.com/aspnet/core/security/enforcing-ssl?view=aspnetcore-10.0
- MFA ASP.NET Core: https://learn.microsoft.com/aspnet/core/security/authentication/mfa?view=aspnetcore-10.0

Las propuestas son objetivos y posibles herramientas; las decisiones finales se apoyan en el código y la evidencia real. Nunca anunciar MFA, SAST, carga, cifrado portable o QA final por haber preparado documentos o workflows.
