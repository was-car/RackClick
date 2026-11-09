# MFA · decisiones confirmadas por Wascar · 25.10.2026

**Adenda03.11.2026:** La custodia aquí confirmada se conserva. La exigencia inmediata para todos que figura en el cuerpo histórico fue sustituida por [gracia45/exención global](DECISION-MFA-GRACIA-45-DIAS-29-10-2026.md). Las condiciones técnicas están concretadas y revisadas en [F-03.02](D2-CONDICIONES-TECNICAS-F03-02.md); eso no acredita recuperación portable/emergencia/rotación implementadas. MFA nativo ya se ensayó por separado; no alterar D por los estados históricos que siguen.

**Custodia y recuperación confirmadas expresamente.** Estas decisiones sustituyen las menciones anteriores que las dejaban pendientes. La implementación completa y su revisión siguen pendientes; MFA aún no está disponible para usuarios.

## Custodia y ubicación

- Almacén por instancia: `C:\ProgramData\RackClick\Instances\<installationId>\mfa-keys\`, separado de PostgreSQL y de `management`.
- Claves cifradas en reposo. Se conserva el diseño D2 v2 de DPAPI LocalMachine, anillo por versiones, lectura para el SID real del servicio y gestión por operador autorizado. No relajar los controles de `management`.
- Sobre de recuperación cifrado, fuera del servidor y de sus backups. Wascar custodia el sobre y su contraseña en medios separados. La ubicación concreta del medio externo y sus contraseñas se establecen localmente, no se publican en este documento.
- DPAPI LocalMachine no protege frente al administrador local ni frente a un proceso de servicio comprometido. La portabilidad depende del sobre y su contraseña; copiar un blob ligado a otro host no basta.

## Recuperación

- Restablecimiento web sólo por administrador con capacidad `security.manage` y MFA completado. Comprobarlo en el servidor, con auditoría y revocación de sesiones/desafíos.
- Si el único administrador pierde el factor: códigos de recuperación o procedimiento local de emergencia. Debe poder recuperarse sin depender del mismo factor perdido.
- La recuperación conduce a enrolamiento restringido. Siempre debe confirmar un factor nuevo antes de obtener acceso completo; contraseña válida o estado pendiente no equivalen a sesión API.
- No se autoriza un bypass web anónimo ni se cambian los permisos de la cuenta de ejecución de PostgreSQL.

## Requisitos ya decididos que se mantienen

MFA será obligatorio para **todos los usuarios antes de producción**. Las excepciones históricas de laboratorio no revocan esa política. Se mantienen RC9, EN/DE/ES, Npgsql directo, migraciones aditivas y revisión por alguien distinto del implementador.

La revisión D2 v2 conserva sus condiciones técnicas: cabecera del sobre autenticada, trabajo KDF acotado, publicación/rotación recuperables entre disco y DB, y prueba bajo el SID efectivo del servicio. Son trabajo de diseño/implementación del equipo; no otra solicitud de permiso para comenzar S1.

## Estado comprobado y siguiente lote

El repositorio ya incluye `014-mfa.sql` en `SchemaMigrations.Files`, con `LatestVersion=14`. Codex leyó además el SQL014 dentro del bundle 14-08 local: SHA256 `4a2e93311093d2372f33ff00c8318f63d7d773552540c83371754aa83ba1eba8`. La prueba C registró esquema14. **No se necesita encender C ni repetir su instalación para resolver esta cuestión.** Esto no significa que MFA esté habilitado: Program mantiene proveedor ausente y faltan enrolamiento/interfaz.

Claude toma [MFA-L1](MENSAJE-PARA-CLAUDE-MFA-L1-25-10-2026.md): backend de enrolamiento y pruebas HTTP reales en laboratorio. Codex conserva inventario C2 y hará la revisión independiente del lote MFA. El proveedor real de custodia, recuperación portable, interfaz y candidata completa siguen su secuencia después de ese primer bloque.
