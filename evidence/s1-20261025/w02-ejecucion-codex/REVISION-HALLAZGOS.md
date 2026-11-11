# W-02 · Revisión estática de los hallazgos de ejecución

25.10.2026. Revisor independiente: Codex. Leí el mensaje de entrega, EJECUCION-RESULTADOS y HALLAZGOS-PARA-CODEX; contrasté fuentes con scripts del payload 07 congelado y consulté **sólo metadatos/campos permitidos del INFORME.json sanitizado** del primer fallo. No abrí credenciales, dumps ni logs privados originales. No ejecuté instalador, auxiliar, SQL, servicios, cuentas, red, VM o pruebas del producto; sólo lecturas y comparación de bytes de scripts. La identidad global de la evidencia, hashes/entorno y crédito del ledger los concilia el coordinador, no esta revisión.

## 1. Primer fallo: recuperación administrativa, no fallo initdb demostrado

**P2 de diagnóstico/propagación; causa concreta aún pendiente.** La narración «fallo PostgreSQL sin logs» necesita corregirse: el ZIP sanitizado `intentos-fallidos-B/informe-fallo-W02-B.zip` contiene:

- `preparation/exception-private.log`: `status=exception_summary`, 377 bytes, frames de `Prepare-RackClickServer.ps1` líneas 142 y 230.
- `preparation/installation-stdout.log`: `status=parsed`, 623 bytes, `valid=false`, exit 1, código `deployment_instance_administrator_recover_admin_failed`.
- `instance/installation-state.json`: el mismo código de fallo.

Por tanto, **hay diagnóstico preservado al menos en el colector**. No he comprobado la existencia física actual de esos logs en la VM ni se deduce su ausencia original de la búsqueda posterior. Tampoco se demuestra que fallara initdb o el motor PostgreSQL.

La cadena del código congelado es coherente: `Prepare-RackClickServer.ps1:229–230` invoca el instalador privado; `:141–142` convierte la respuesta fallida en `preparation_child_failed`. `New-RackClickRecoveredInstance.ps1:240–245` está en fase `administrator`, ejecuta `--recover-admin`; su helper `:110–116` convierte cualquier exit no cero en `recover_admin_failed` **antes de interpretar el error JSON del CLI**. De ahí el diagnóstico general recibido.

**Hipótesis concreta, aún no acreditada por intento:** `RecoveryAdministrator.cs:154–157` rechaza `recovery_username_exists` si el nombre de recuperación ya existe en el backup. La narración dice que New creó `admin-prueba`, la hoja Restore repite ese nombre y el tercer intento usa uno distinto. Eso podría explicar tanto el primer rechazo como el éxito posterior; el cambio de usuario no debe tratarse automáticamente como irrelevante. La fuente actual tiene hash `814ebd94…`, ya revisada para la aplicación 03; en esta tarea no se ejecutó ni inspeccionó IL de la DLL congelada.

**Corrección/prueba propuesta:** conservar en los wrappers el `status/error` permitido del CLI cuando falla, sin exportar stdout bruto ni secretos; mostrar una indicación concreta para elegir un **nuevo administrador de recuperación**, sin sustituir o reutilizar automáticamente el usuario existente. Recuperar únicamente ese JSON sanitizado o ejecutar en laboratorio nuevo, con DLL/pins congelados, el negativo de nombre ya existente frente al positivo de nombre nuevo. Comprobar que el negativo no produce commit/auditoría de recuperación ni cambia usuarios/sesiones; el positivo conserva los usuarios anteriores y crea el nuevo administrador con sus revocaciones/auditoría. No se propone relajar la comprobación ni afirmar causa cerrada por haber pasado un reintento.

El catch de `Prepare-RackClickServer.ps1:250` omite silenciosamente errores al escribir su excepción: merece un estado sanitizado explícito de publicación fallida como prueba adicional. No demuestra que eso ocurriera aquí, dado el resumen existente en el colector.

## 2. Cuenta Windows preservada: seguridad prevista y fricción de reintento

**Rechazo esperado de seguridad; P3 de explicación/experiencia de reintento, no defecto por no borrar cuentas.** `RackClick.Setup.Namespace.ps1:51–76` inventaría y preserva las cuentas/SID y bloquea referencias vivas. No promete eliminarlas al archivar carpetas. `Install-RackClickServer.ps1:81–83` sólo genera un nombre alternativo automáticamente para el nombre por defecto `RackClickSvc`; un nombre personalizado existente se rechaza con `setup_account_exists`.

Así, volver a elegir `RackClickSvcB` después de preservarla produce el comportamiento programado. No debe corregirse eliminando cuentas por prefijo o reapropiándose de su SID. La eliminación manual registrada es una intervención del ensayo; esta revisión no la ejecutó ni valida retrospectivamente todas sus precondiciones.

**Corrección/prueba propuesta:** explicar la colisión y ofrecer un nombre nuevo dentro de la regla admitida, conservando cuenta/SID y archivos anteriores. Antes de mutar, comprobar el nombre que realmente vaya a usarse. Negativo con una cuenta ajena/manual existente: rechazo sin cambiar contraseña, grupos, derechos o SID; positivo con nombre libre: nueva identidad y datos separados, cuenta antigua intacta. Probar también el caso por defecto con sufijo UUID. El problema operativo del reintento se trata sin desactivar esta protección.

## 3. result.json frente a postboot-verification.json

**No es por sí solo un defecto de persistencia ni contradicción del servicio; P3 de semántica/presentación si se promete un estado único actual.** `Install-RackClickServer.ps1:175–189` escribe el resultado histórico del proceso que prepara la instalación, en `awaiting_reboot`, exit 3 y `rebootVerified=false`. El verificador posterior es otro proceso: `Test-RackClickServerAfterReboot.ps1:43–49` publica `postboot-verification.json`, y no modifica el resultado del intento anterior. El panel sí exige resultado postboot válido, UUID coincidente y `rebootVerified=true` (`Show-RackClickInstalledServer.ps1:128`).

**Corrección/prueba propuesta:** documentar ambos archivos como eventos de fases distintas o añadir una proyección de estado actual ligada a recibo/UUID/bootUtc; conservar el resultado original como historia. No cambiar retroactivamente un exit 3 en un exit 0. Probar preparación → postboot correcto → verificación posterior fallida: la presentación no debe mostrar éxito usando sólo un archivo histórico o un UUID distinto. El postboot correcto observado no acredita por sí solo adopción del producto.

## 4. execute-report.json ausente al reiniciar

**P3 de robustez/evidencia del auxiliar W-02, separado del producto.** `Invoke-W02TrialPlan.ps1:268–279` espera a que termine la interfaz oficial; el informe se escribe después de retornar (`:288–290`). Un reinicio que termine el padre mientras espera impide llegar a esa escritura; tampoco se garantiza un catch/finally al terminar Windows. La ausencia no prueba fallo de PostgreSQL ni éxito de instalación.

**Corrección/prueba propuesta:** en el procedimiento, cerrar el flujo de instalación ya finalizado y esperar el informe antes del reinicio manual cuando sea posible. Para interrupciones inevitables, persistir antes del lanzamiento un registro `started/pending` con identidad del ensayo, hashes y hora; completar el resultado si vuelve el hijo. Una consulta posterior **sólo de evidencia** puede correlacionarlo con recibo y postboot, sin repetir Execute/INICIAR ni una limpieza. No inventar `official_flow_exited` si nunca se observó la salida.

Foco inocuo propuesto: hijo de prueba que termina normalmente y otro cuya espera se interrumpe al terminar sólo el padre de laboratorio; debe quedar el diario pendiente, nunca éxito ficticio. La instalación real y el reinicio siguen requiriendo su evidencia propia; el hueco del auxiliar puede documentarse sin borrar esos resultados nativos.

## Identidad de las referencias y límites

Comparé estos scripts actuales con sus bytes dentro del payload 07 (y el operador de recuperación de su bundle interno); todos resultaron iguales. No se presupone identidad sólo por el nombre del archivo:

| Script congelado contrastado | SHA256 |
|---|---|
| `Prepare-RackClickServer.ps1` | `0ed88989661d37b307a121ed09f912b4eff125ef6e1bc91e2239e460e782161f` |
| `Install-RackClickServer.ps1` | `181ab16c1e930a2ed9e5fff11b626fb2de847622aa1d92e1d0b7e693c139f653` |
| `RackClick.Setup.Namespace.ps1` | `c516f8521631d67ebac89aac95fcc643cad235533a1cec2bb08c2ee3dcceb7e3` |
| `Test-RackClickServerAfterReboot.ps1` | `fb2630c245b63131c892045b600b970b289d03341a3dcc393420dac5198bd95a` |
| `Show-RackClickInstalledServer.ps1` | `2da1441c83310ffd6b7202adac914f2968a047e49571b7f3fdf2c6be116736dd` |
| `New-RackClickRecoveredInstance.ps1` | `4e10b2791ca6721c1b0dec2cb54b12d420d89d647c78eb3adf8e94ff8cfde5cd` |

El auxiliar externo leído es `28c0b0c0309aab59b54e36aa0cbc14a0ab1667f0a3ebaeeb6da1246cb3749999`. No reaudité la cadena completa de artefactos, la identidad de las VM, huella de ISO, inventario inicial ni la pertenencia de RackClickSRV a QA. No se otorga crédito del ledger en este informe ni se declara resuelto el primer fallo sin su error concreto/prueba focal. Se conserva toda la evidencia de intentos fallidos y de intervención manual.

## Adenda · resultado focal y criterio W-02.01

Leí el test `test_recovery_username_collision.py` antes de su ejecución y ahora `REPRO-COLISION.json`: **la ejecución es del coordinador, no mía**, con la DLL congelada `19c94d4e…`, PostgreSQL 17.11 y laboratorio nuevo, sin rebuild, backup ni VM. Termina PASS en 16,72 s: el mismo nombre devuelve exactamente `recovery_username_exists`, deja las 14 tablas listadas y el marcador sin cambios; el nombre nuevo conserva el usuario original, crea otro administrador, registra una auditoría y consume el marcador. Laboratorio detenido e input intacto. Acredita ese comportamiento real de la DLL, no un pg_restore ni la causa exacta del intento 1: todavía falta su stdout/error CLI específico para convertir la hipótesis en causalidad confirmada.

Leí también `REGISTRO-VM.json`, `CONTRASTE.json` y el inventario de `ENTRADAS.json` del coordinador, sin repetir su auditoría de 35 archivos/cuatro ZIP ni sus lecturas pasivas del hipervisor. **Conforme con acreditar sólo W-02.01: 1/2 punto.** El registro identifica las dos VM de ensayo, imagen declarada/edición/build/rol 2, cuentas de operador y servicio, discos/espacio y red; el coordinador contrasta 4 CPU, 6144 MB, 80 GiB y VMnet1 mediante configuración pasiva y correlaciona por UUID las evidencias postboot. Es suficiente para el subpaso de preparación/registro de VM, sin presentarlo como auditoría exhaustiva: no se aportó la enumeración completa de cuentas de A ni huella criptográfica del medio ISO; la imagen queda declarada, no autenticada por esta revisión. RackClickSRV aparece apagada en VMnet2, pero su vínculo con la instalación QA y la causa del apagado siguen sin demostrar; esta lectura no afirma haberlo confirmado ni haber actuado sobre ella. No se exige certificar toda QA para este subpaso. W-02.02 a W-02.05 continúan pendientes sin crédito; no se adopta el producto ni se modifica el ledger desde este informe.
