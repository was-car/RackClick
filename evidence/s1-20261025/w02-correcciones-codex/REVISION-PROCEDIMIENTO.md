# W-02 · Revisión de correcciones del procedimiento y diagnóstico H1

25.10.2026. Revisor: Codex, distinto del implementador Claude. **Sólo lectura** de procedimiento, resultados y fuentes necesarias. No ejecuté el auxiliar, validador, pruebas, launcher, servicios, SQL, QA ni VM. No modifiqué históricos, producto ni archivos de Claude. La reproducción/revisión de R1/R2 y cadena ZIP corresponde al coordinador; no se duplica ni se atribuye aquí.

## Dictamen

Las correcciones principales del procedimiento están incorporadas. **Queda una precisión operativa necesaria antes de entregarlo al operador: identificar el acceso correcto para verificar después de reiniciar**, evitando volver al flujo de instalación/limpieza. Se resuelve en documentación sin regenerar 07. No se ha encontrado otro bloqueo nuevo de producto dentro de este alcance.

W-02 conserva **0,00/2,50 puntos**: ni las correcciones ni la revisión sustituyen New/Restore/reinicio en VM. No se modifica el ledger ni se calcula porcentaje global.

## Correcciones comprobadas

- **UUID, `PROCEDIMIENTO:107–109`:** registra por separado el UUID generado por la GUI y compara los otros 14 campos. Concuerda con `Show-RackClickInstaller.ps1:230`; la comparación se declara manual/posterior, sin prometer una compuerta automática. H2 permanece abierto con ese límite. Para realizarla, la ruta conocida del plan es `%LOCALAPPDATA%\RackClick\Setup\<UUID-real>\plan.json` (`Show-RackClickInstaller:104–118`); no debe editarse para igualarlo a la hoja.
- **Reanudación, `:151–158`:** elimina la condición errónea de fallo por no reanudarse automáticamente y reconoce `awaiting_reboot`/exit 3. Es un estado normal de preparación que requiere la verificación final del arranque; no debe interpretarse únicamente como un reinicio excepcional por CRT/runtime/PostgreSQL.
- **VM B, `:168` y `:190–194`:** usa IP/publicHost/subred propios y repite 5.5–5.7, además de 5.1–5.4. Incluye el dato sintético restaurado como comprobación separada.
- **Exportación, `:178–188`:** describe selector local NTFS, carpeta `RackClick-Backups\<guid>`, manifiesto/dump, archivo hermano `.sha256.txt`, `backup-export-*.json` y `export_complete`. Coincide con el exportador congelado revisado en la tanda anterior. Los pines 07 y el hash documental recibido ya están identificados; no se ha vuelto a auditar el ZIP completo en esta revisión.

## Precisión operativa pendiente: abrir el panel, no el instalador de cero

`PROCEDIMIENTO:155` dice «Reabrir el instalador manualmente». Puede inducir a ejecutar otra vez `INICIAR.ps1` o `Execute`, aunque ambos son recorridos de instalación. El launcher congelado pasa por `Get-SetupNamespacePlan` y el resumen/reset antes de abrir la GUI de instalación (`Start-RackClickCleanInstall.ps1:128–139`). Una instalación con servicio en esas rutas produce `namespace_registered_service_preserved` (`RackClick.Setup.Namespace.ps1:54–59`); no es el acceso de verificación postboot.

Sustituir la instrucción por algo explícito: **tras reiniciar, abrir el acceso `RackClick-VERIFICAR-05-<sufijo>.cmd` creado en el Escritorio por esta ejecución de 07, que abre el panel del servidor instalado; usar «Verificar instalacion» si no se ejecuta ya al abrir. No volver a Execute/INICIAR ni confirmar otra limpieza.** Registrar el resultado para el UUID real. Si falta ese acceso o no se puede validar su instalación, parar y conservar el informe.

La etiqueta 05 es H3, ya documentada; no significa que se deba recuperar un verificador de un ZIP histórico 05. La comprobación integrada del panel incluye HTTPS y backup: `PROCEDIMIENTO:160` puede aclarar que se conserva esa comprobación necesaria sin acreditar por ello toda W-04, MFA o red.

## H1: qué cubre realmente el diagnóstico

`Invoke-W02TrialPlan.ps1:84–94` añade comprobación antes del validador oficial (`:149`), sin sustituirlo:

| Entrada | Código y campo por lectura |
|---|---|
| JSON sintácticamente roto | `plan_json_invalid`; no se puede atribuir un campo concreto y `field` puede quedar vacío |
| Control ASCII 0x00–0x1f en una propiedad de texto | `plan_field_control_character`; `field` es el nombre de esa propiedad |
| Caracteres de `GetInvalidPathChars()` en `backupPath` no vacío | `plan_field_invalid_path_character`; `field=backupPath` |

Dos matices de documentación: `RESULTADOS.md` afirma inválidos de ruta «en cualquier campo de texto», pero el código los aplica **sólo a backupPath**; los controles sí se comprueban en todos los strings de primer nivel. `PROCEDIMIENTO` §5.3 no debe prometer un nombre de campo para cualquier JSON roto. Son precisiones de atribución, no aceptación de rutas inválidas demostrada ni motivo para regenerar 07.

El validador oficial sigue intacto; las demás rutas inválidas pueden terminar en rechazo genérico como reconoce el informe. Los 18 focos y 16 pruebas estáticas comunicados son **de Claude**, no ejecuciones propias ni evidencia de VM. H3 mantiene sus tres etiquetas editoriales para una edición posterior; H2 no se presenta como comparación automática.

## Huellas recibidas y límites

| Archivo revisado | SHA256 |
|---|---|
| `tools/windows/w02/Invoke-W02TrialPlan.ps1` | `485436893495e718dd682e6b871b0171c660666d7a6e030f2ee49a7d9b220e00` |
| `docs/PROCEDIMIENTO-W02-NEW-RESTORE-07.md` | `5053890dfc998916362ea278dee7070076d6183b534e2d5d51237e1453e28a84` |
| `evidence/s1-20261025/w02-vm-limpia-07-claude/RESULTADOS.md` | `97000809d7cda890ba9ba3a6363b7c6be3a674c2fa406b25165301b716b2c169` |

La huella vigente del procedimiento coincide ahora con la declarada por Claude; los dos digests anteriores se conservan como historia. Cualquier corrección documental posterior debe sellarse con su nuevo digest. Esta revisión no acredita lanzamiento completo, instalación limpia, cuenta/SCM, reinicio real, exportación ni Restore en VM.

## Adenda · lectura del foco del coordinador y límite de la batería

Leí `reproduce_corrections.ps1` y `.local/w02-corrections-review-20261025T105928Z-0acccacd/probes02/result.json`; **no ejecuté ni repetí esta prueba**. El coordinador fija el helper recibido por SHA256, importa sus declaraciones/funciones mediante AST sin ejecutar su entrada principal y crea destinos nuevos bajo `.local`, comprobando ancestros sin reparse. Intercepta la limpieza del Plan para conservar los fixtures. El resultado contiene 12 observaciones esperadas de validación oficial/R2, H1, exclusión y comparación del envoltorio; todas coinciden. Son ejecuciones del coordinador, distintas de las 18 comunicadas por Claude.

**R1b queda respaldado en este alcance:** el foco conserva la función `Invoke-W02Execute` original y controla exclusivamente Plan, Check y Start-Process. El sustituto de Start-Process no inicia hijos: en su primera llamada registra que INICIAR coincide con el hash original, simula una respuesta VerifyOnly válida y añade un comentario inocuo al archivo. La segunda llamada recibe el archivo con hash distinto y la función termina `w02_official_flow_exited`. El resultado registra dos llamadas simuladas, `firstEntryMatchesPin=true`, `secondEntryMatchesPin=false`, cero hijos reales y cero operaciones de servicio/cuenta/DB.

Esto demuestra la desvinculación entre la comprobación y la segunda llamada en ese recorrido controlado; **no** demuestra ejecución real de código alterado, explotación en VM, superación de las compuertas de host ni instalación. Exit 0 del foco significa que se reprodujeron las observaciones esperadas, incluida la debilidad restante; no es aprobación del auxiliar para lanzar la instalación. Es razonable mantener R1b abierto antes de ese uso real.

También leí `focos/ejecutar-focos.sh` de Claude. Hay un límite real de su señal automática:

- `caso`, líneas 18–26, escribe OK/FALLO pero no acumula fallos ni devuelve error por discrepancia; la última operación es el printf del registro.
- El resultado estático pasa por `tail -1` sin comprobar el exit del proceso Python (líneas 35–36). La creación de junction fallida sólo añade texto (línea 32).
- La línea 68 escribe **NO_LANZADO incondicionalmente**, incluso si el bucle anterior añadió una línea LANZADO.
- El último `cat` (línea 76) puede acabar exit 0 aunque el archivo contenga FALLO o LANZADO. `set -u` no convierte esos registros en aserciones.

Por tanto, ni exit 0 de esa batería ni la frase NO_LANZADO acreditan automáticamente «18/18 sin lanzamientos». Deben inspeccionarse los resultados individuales o corregir la agregación/aseveración del runner. Esto es una limitación de evidencia de prueba; no invalida por sí sola cada observación registrada ni demuestra un fallo del instalador. W-02 continúa en cero crédito.

| Elemento leído para la adenda | SHA256 |
|---|---|
| `reproduce_corrections.ps1` del coordinador | `30ce24cd307d87b8f83c9322c5f4e4e104b9e7712857075a55d1fddc8f0d3d1b` |
| `probes02/result.json` | `696b8bbef35b0655cbf055952dba5c364aa1648ed95eb9477c6a52f80a69121f` |
| `focos/ejecutar-focos.sh` de Claude | `ded323d3e91fbc4356b621c308d092defe43daaa5cb797407e0d7deaa7e34d60` |
