# Restore · diagnóstico del administrador existente · 25.10.2026

**Corregido en desarrollo y probado con el operador real; todavía sin paquete nuevo ni instalación en VM.** Si el administrador de recuperación ya existe en la copia, la causa deja de perderse entre operadores y el panel explica que hay que elegir un nombre nuevo. No cambia el rechazo ni se reutiliza/modifica el usuario existente.

La reproducción anterior con la DLL exacta 07 mostró `recovery_username_exists`, pero `Invoke-RecoveryOwnedChild` lo convertía en `recover_admin_failed`; la preparación volvía a convertirlo en `preparation_child_failed`. El panel etiquetaba toda la preparación como PostgreSQL y no mostraba la causa de recuperación.

Cambios propios:

- [New-RackClickRecoveredInstance.ps1](../tools/windows/New-RackClickRecoveredInstance.ps1): promueve únicamente la salida canónica de ese rechazo emitida por `recover-admin`, exit 1 y stderr vacío. Tamaño limitado; se rechazan propiedades extra/duplicadas, mayúsculas distintas, texto añadido, códigos desconocidos y otras etiquetas. El resto conserva su diagnóstico genérico. El lector de commit y la limpieza del proceso propio siguen vigentes.
- [Prepare-RackClickServer.ps1](../tools/windows/server-install/Prepare-RackClickServer.ps1): lector separado conserva límites, JSON y tipos/exit coherentes. Sólo el código completo conocido con `valid=false` llega como `preparation_recovery_username_exists`. Código no string se rechaza, incluido un array de un solo elemento.
- [Show-RackClickInstaller.ps1](../tools/windows/server-install/Show-RackClickInstaller.ps1): texto fijo sólo para la combinación exacta de código superior, etapa y código del hijo, todos strings. Indica «Usa un nombre nuevo para el administrador de RackClick» y que se conservan los usuarios. No refleja salida privada del hijo.

El cambio no añade propiedades al DTO ni amplía los límites de códigos. `Restore-RackClickPrivateDeployment`, `OfflineBundle`, broker, servidor C#, SQL y MFA permanecen como estaban. Los prefijos existentes caben en los límites actuales. Los ZIP 07 siguen congelados; aún contienen los operadores anteriores. Hace falta una candidata nueva para ensayar esta corrección.

Pruebas nuevas de Windows:

- Fase roja sobre el operador original: fallo esperado `known_rejection_preserved`.
- [34 comprobaciones nativas](../tools/tests/setup_recovery/Test-RecoveryDiagnostics.ps1), con funciones reales cargadas por AST y frontera de procesos simulada: error conocido, negativos, limpieza, preparación, contrato de éxito y texto del panel.
- Regresión existente del broker: **20/20**, con 15 procesos propios bajo la identidad actual; sin cuentas/servicios/VM.
- [Prueba PostgreSQL ampliada](../development/server/tests/test_recovery_username_collision.py), opción `--owned-operator`: **PASS 18,08 s** con PostgreSQL 17.11 nuevo, DLL congelada 07 `19c94d4e…`, `Invoke-RecoveryOwnedChild` y `Read-RecoveryCommitResult` reales. El negativo conserva exactamente las 14 tablas enumeradas y el marcador; el positivo conserva el usuario original, crea el nuevo, consume el marcador y registra una auditoría. Laboratorio detenido e inputs intactos. No ejecuta `pg_restore`, preparación completa, servicio ni instalador.

La revisión independiente detectó arrays que PowerShell podía tratar como coincidencias en los códigos: rojo propio 3 fallos/5 comprobaciones; tras exigir strings, verde 5/5. Primer intento verde del autor falló por un error del cargador AST de pruebas que perdía parámetros inline; se corrigió el test y se conservaron las salidas. Ambos hechos quedan separados de la prueba de producto.

[Evidencia y revisión](../evidence/s1-20261025/recovery-diagnostic-codex/CIERRE.md). **QA-119 queda planned**, con pasos y ubicación de controles; guías regeneradas y 118 casos anteriores intactos. No ejecutarlo con ZIP 07 ni sobre A/B/QA. Resultados personales de Wascar conservados.

No se establece la causa exacta histórica del intento 1 por esta prueba; su JSON específico sigue no disponible. La corrección permite obtener un diagnóstico concreto en un ensayo futuro. W02-R3 de Claude continúa separado. Proyección del estado postboot y candidata nueva siguen pendientes. Sin builds, commits, publicación, cambio de dependencias, QA o VM.

**Delta 0:** 4,79/100 del inventario restante, 11/280 subpasos y 1/50 resultados completos; W-02 sigue 0,50/2,50. Esta corrección no completa el recorrido de instalación W-02.02 ni concede aceptación final.
