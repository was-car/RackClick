# W-02 · Revisión independiente del procedimiento 07

25.10.2026. Revisor: Codex, distinto del autor Claude. Sólo lectura de procedimiento, resultados, definición W-02 y fuentes necesarias; lectura de archivos del ZIP congelado para contrastar etiquetas/pins. **No ejecuté el validador, las nueve pruebas, el launcher, instalaciones, servicios, red, cuentas, QA ni VM.** No se modificó producto ni documentación ajena. La revisión de compuertas/vinculación del ejecutor corresponde al coordinador y no se duplica aquí.

## Dictamen y crédito

La preparación es útil y la atribución de resultados es prudente: Claude distingue los ensayos negativos sobre LEAO, las copias instrumentadas y la ausencia de VM. Es correcto mantener **W-02 en 0,00/2,50 puntos**: ninguno de sus cinco subpasos se acredita por escribir este procedimiento o pasar pruebas del ejecutor. Los cinco siguen `pending` en el JSON leído.

**El procedimiento necesita correcciones documentales antes de guiar el ensayo real.** No implican regenerar 07: hay una condición de parada equivocada tras el reinicio, una comparación imposible del UUID de hoja y GUI, y falta concretar el recorrido de VM B. No constituyen un fallo de instalación reproducido, porque no se ha ejecutado ninguna.

Estado de cierre comunicado por el coordinador: **3,57/100 del trabajo pendiente**; no es porcentaje global del producto. Esta revisión no suma crédito y no reactiva el antiguo 78 %.

## Correcciones necesarias del recorrido

### 1. Reinicio y reanudación manual del panel

`PROCEDIMIENTO-W02-NEW-RESTORE-07.md:141` y `:187` ordenan parar si el instalador no se reanuda solo. Esto contradice el comportamiento previsto:

- `Install-RackClickServer.ps1:175–179` termina una preparación correcta en `awaiting_reboot`, `setup_ready_reboot_verification_pending`, exit 3 y 95 %. No es un error por no llegar a 100 % antes del reboot.
- `Show-RackClickInstaller.ps1:203–205` lo presenta como preparado y habilita el panel.
- `Show-RackClickInstalledServer.ps1:133` indica expresamente reiniciar, **volver a abrir el panel y pulsar «Verificar instalación»**. La confirmación exige `postboot_verified`, `rebootVerified=true` y el mismo installationId (`:128`).

El procedimiento debe separar un reinicio por prerrequisito de la verificación final obligatoria del arranque automático. Después de una preparación correcta, registrar el resultado, reiniciar la VM, abrir el acceso de verificación creado por ese envoltorio y pulsar el botón; no declarar fallo únicamente porque no aparece una ventana automática. El verificador real actualmente creado puede llamarse `RackClick-VERIFICAR-05-<sufijo>.cmd` aunque proceda de 07. Conservar la correlación con esa ejecución. Si falta ese acceso o el panel devuelve un error, registrar el código y detener el ensayo.

El panel verifica también HTTPS y backup (`Show-RackClickInstalledServer.ps1:116–129`). La frase de `PROCEDIMIENTO:143` «No ampliar a HTTPS» debe permitir esas comprobaciones integradas necesarias, distinguiéndolas de cerrar toda la tarea W-04. No se deben omitir ni acreditar W-04 completa por ese resultado.

### 2. Hoja externa frente al plan de la interfaz

`PROCEDIMIENTO:107` pide comparar campo a campo los 15 valores. La GUI **genera siempre otro GUID**, no ofrece copiar `id` de la hoja (`Show-RackClickInstaller.ps1:230`). La igualdad literal de los 15 campos es imposible aun introduciendo correctamente la configuración.

Comparar los **14 campos restantes** y registrar por separado el UUID real generado y su vínculo con la hoja, intento, recibo e informes. El plan real queda en `%LOCALAPPDATA%\RackClick\Setup\<UUID-real>\plan.json` (`Show-RackClickInstaller.ps1:104–118`). No editarlo para forzar igualdad: se guarda y se entrega inmediatamente al broker (`:240–242`). La comprobación manual es evidencia de concordancia posterior, no una compuerta que este procedimiento pueda afirmar previa a toda mutación. Cualquier discrepancia configurable impide acreditar la ejecución y debe registrarse.

### 3. Restore en la VM B

`PROCEDIMIENTO:171` sólo enumera cambiar modo, carpeta y digest y repetir 5.1–5.4. Se debe indicar además:

- Registrar VM B como VM limpia propia; usar su IPv4 real y publicHost correspondiente, no copiar la IP de VM A. La plantilla DNS es ficticia: usar una resolución ya preparada o la IP real para el ensayo, sin introducir cambios de red no previstos.
- En la hoja Restore, conservar las reglas de los 15 campos, registrar el UUID real de GUI y confirmar manualmente las demás opciones. Cuenta/servicio pueden tener los mismos nombres en otra VM limpia; no se reutiliza su identidad/SID ni base de A.
- Repetir también 5.5–5.7 en B: estado de preparación, reinicio real, panel y exportación del informe. Ver el dato restaurado en navegador no sustituye comprobar el arranque tras reiniciar B.

El uso de dos VM y de un dato sintético previo al backup es adecuado. La ruta/API de exportación y los dos archivos descritos son correctos: `Export-RackClickServerBackup.ps1:13` exige `scheduled_backup_complete`; `:60–74` copia sólo `manifest.json` y `data.dump`, los verifica y crea el archivo hermano `.sha256.txt`. Añadir que aparece un selector de **carpeta local NTFS** (`:41–47`), que la salida completa es `<carpeta-elegida>\RackClick-Backups\<UUID>` (`:48–50`) y que se usa sólo tras `export_complete` (`:75`). La comparación del SHA256 tras traslado es correcta.

## H1 y H3: decisiones sin regenerar 07

**H1, ruta inválida:** `RackClick.Setup.ps1:6–7` llama a `IsPathRooted` y `GetFullPath` antes de traducir excepciones por caracteres inválidos; `Read-SetupPlan:54` lo aplica a `backupPath`. La falta de un código propio es una carencia diagnóstica. Según el informe de Claude el ejecutor la captura como `w02_plan_failed` y rechaza: no hay aquí evidencia de aceptación de una ruta inválida ni de mutación por ella. Esta revisión no vuelve a ejecutar esa prueba ni revisa su catch. **No exige reconstruir 07 para el ensayo con rutas locales válidas**; registrar el fallo si aparece. Puede mejorarse el código estable en una edición posterior, con su negativo, sin cambiar el paquete congelado.

**H3, etiqueta antigua:** confirmado directamente en `RackClick-Servidor-07/INICIAR.ps1` congelado, no sólo en la fuente viva:

- Línea 62: título del resumen `RackClick 05`.
- Línea 83: nombre del acceso `RackClick-VERIFICAR-05-…`.
- Línea 154: título del cuadro de error `RackClick 05`.

Son etiquetas editoriales; el launcher fija el payload **07** `71469d1e…` en su línea 7 y llama al instalador de su propio payload. No acreditan ejecución de la edición 05. **Conservar 07 y sus hashes**, avisar de estas etiquetas en el procedimiento y corregirlas cuando corresponda generar otra edición. No renombrar ni sustituir accesos por un verificador descargado de un paquete 05 antiguo.

## Pins, evidencia y límites

Los pines del procedimiento corresponden a la candidata 07 ya auditada: envoltorio `3ca22323…`, payload `71469d1e…`, bundle reutilizado `6d5a3896…`, `payload.json` `25a764a9…`, paquete IP `b36fd6d3…`. No se ha repetido aquí la auditoría completa de ZIP que hizo el coordinador. En esta lectura, los cuatro scripts citados del payload congelado son byte a byte iguales a las fuentes actuales usadas para las referencias de línea.

La evidencia prevista —registro de imagen/build/rol/red/discos, informes, códigos de reinicio, panel, dato restaurado y ZIP sanitizado con hash— es adecuada como base. Debe quedar un conjunto independiente por VM/intento y contener el resultado real de postboot. La ausencia previa de SDK/Node/Python debe confirmarse para acreditar W-02.02; si estaban presentes, no se debe presentar como ensayo limpio. W-02.03 requiere también la repetición con prerrequisitos compatibles e incompatibles/DC/puertos; W-02.04 no se cierra con este procedimiento y Windows 11 usado como cliente sigue necesitando sólo navegador.

**Huella documental a corregir al sellar:** `RESULTADOS.md:15` declara para el procedimiento `0bc555ce…`, pero el archivo leído tiene SHA256 `b82c097af8d7ee2e10e62940885601ccf32c7d7bba34d41371a7a5543f8617f7`. Registrar la versión realmente revisada y recalcular su huella tras las correcciones; no trasladar el digest anterior como vigente.

| Elemento leído | SHA256 |
|---|---|
| `w02-vm-limpia-07-claude/RESULTADOS.md` | `94ec1be78892302eae033fa6b6b789bff064b09730026be4129d52f79f4992b8` |
| Launcher `INICIAR.ps1` dentro del envoltorio 07 | `95feb1edd548078b4d94583cc83d1b572184aeccdc8d48eeddf01a5614930206` |
| `RackClick.Setup.ps1` del payload | `717f748f3c2f3da163acf1822fa725d2ef81768c5df9f3d1ec3f781343cc6b1f` |
| `Show-RackClickInstaller.ps1` del payload | `f9f95cc1cb3b20c29437782acfc1f218851556662dc9c7889ac0cd450591272c` |
| `Show-RackClickInstalledServer.ps1` del payload | `2da1441c83310ffd6b7202adac914f2968a047e49571b7f3fdf2c6be116736dd` |
| `Export-RackClickServerBackup.ps1` del payload | `3a12dd33009443079104f1f9dd1373688b2faaa113eea3a4f89789107a113bf2` |

No se atribuye a esta revisión una prueba Windows/DB ni el cierre de ningún subpaso W-02. El producto y los paquetes se conservaron sin cambios.

## Adenda · lectura del foco de vinculación ejecutado por el coordinador

Leí `reproduce_binding.ps1` y `.local/w02-review-20261025T102230Z-4b82fbeafe/probes/result.json`. **La ejecución es del coordinador; yo no ejecuté ni repetí el foco.** Su alcance está correctamente delimitado: fija los hashes del ejecutor y del envoltorio oficial, extrae mediante AST la función original `Get-W02Sha` y dos fragmentos exactos de `Invoke-W02Execute`; genera sólo fixtures nuevos bajo `.local`. Los fragmentos terminan antes de `Invoke-W02Check` y de la preparación de `Start-Process`. No invoca Execute completo, Check, VerifyOnly ni INICIAR. El resultado declara cero lanzamientos, servicios, cuentas, bases, QA y VM, coherentemente con el script leído.

Las observaciones reproducidas son materiales para el helper, con estos límites:

- **R1, envoltorio:** el fragmento acepta el original y rechaza modificar sólo INICIAR; acepta modificar INICIAR y actualizar su fila en PAQUETE.json, y acepta un archivo extra al declararlo también en ese manifiesto. Concuerda con `Invoke-W02Execute:137–145`: valida contra un inventario mutable del directorio extraído, sin vincular sus bytes al envoltorio oficial fijado que Check verifica por separado. La modificación de INICIAR en este foco es un comentario inocuo y **nunca se ejecuta**. No se presenta como una ejecución de código alterado en VM, sino como aceptación por la comprobación previa.
- **R2, hoja:** el fragmento rechaza si falta plan-report.json, pero acepta una hoja semánticamente inválida cuando se fabrica un informe con status pass, el nombre actual y su digest. La hoja del test es JSON sintácticamente válido, con campos insuficientes y modo/puerto inválidos; no es un error de parser JSON. Concuerda con `:128–131`, que confía en esas tres afirmaciones del informe sin volver a ejecutar el validador oficial en ese fragmento. No prueba que el instalador posterior acepte esa hoja ni que la GUI vaya a utilizarla.

El dictamen del coordinador de corregir R1/R2 **antes de usar el helper para lanzar el ensayo VM** está respaldado por esta prueba focal y por la lectura de sus líneas. La confirmación del alcance no equivale a ensayar la ruta completa ni a levantar las exclusiones del host. H1/H3 conservan el tratamiento diagnóstico/editorial anterior; estas correcciones del helper no requieren alterar ni regenerar el envoltorio 07 congelado. W-02 mantiene cero crédito.

| Elemento de la adenda | SHA256 |
|---|---|
| `reproduce_binding.ps1` del coordinador | `2105333a1231a998c38734e49f111a8a0f34b9a374f71305b43f0468d3af3fe5` |
| `probes/result.json` leído | `f6ec5ad7008c9af808800b441d3493861edad574d7d23dd538e56def46b3c722` |
| Ejecutable PS1 revisado, sin modificación | `a5f92e33cc1cd8812205554a5b2a74b46ace8d78a1dfad5ee1ece256259f3beb` |
