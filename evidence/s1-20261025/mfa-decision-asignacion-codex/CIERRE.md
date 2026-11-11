# MFA · decisiones y asignación · 25.10.2026

Wascar confirmó explícitamente la custodia propuesta y la recuperación propuesta en sus dos respuestas. Se registran en docs/DECISIONES-MFA-CONFIRMADAS-25-10-2026.md; claves y contraseñas no se solicitaron ni se publicaron. Custodia externa en medios separados a cargo de Wascar; almacén local por instancia y recuperación restringida sin password-only.

Lectura del coordinador: D2v2/revisión, contrato MFA, Program, Authenticate, MfaStore, migración y perfil/bundle locales. Comprobación nueva del bundle: application/server/database/014-mfa.sql presente (ruta exacta en CONTRASTE.json); esquema14 activo en la lista de migraciones. El recibo de C es evidencia anterior, no una nueva consulta a la VM.

Revisión independiente acotada de rackclick_security (mfa_lab_scope_review): conforme con asignar enrolamiento restringido y pruebas de laboratorio; store actual sólo verifica, Authenticate no inicia enrolamiento, no hay rutas de enrolamiento. Confirmó invariantes y propiedad propuesta. Sólo lectura: no ejecutó build, PostgreSQL, HTTP, VM o inspección de secretos; no acredita de nuevo los tests históricos.

Se asigna MFA-L1 a Claude y se mantiene C2 en Codex. Proveedor sintético sólo dentro del host/fixture de pruebas, endpoints/middleware reales; modo normal sin activación por defecto. Proveedor real, recuperación completa, UI y candidata siguen pendientes. No se implementó código MFA en esta tanda.

Sin pruebas nuevas de producto, servicios, VM, QA, builds, paquetes o commits. Se conservan D2v2 previa y sus hashes como historia; adendas posteriores registran la confirmación sin inventar implementación. Cierre ponderado del pendiente sin cambio: 5,86/100; porcentaje global sin recalcular.
