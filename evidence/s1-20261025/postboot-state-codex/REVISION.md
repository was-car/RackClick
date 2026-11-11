# Revisión independiente de la proyección postboot

25.10.2026. **Conforme en el alcance revisado, con el fallo de progreso encontrado y corregido por el coordinador.** Una verificación guardada se presenta como antecedente del arranque, sin declarar salud actual ni adopción. El panel sólo alcanza 100 con el resultado de su nueva llamada y salida nativa cero. No se acredita instalación, reinicio real ni estado operativo de una VM.

## Fuentes finales revisadas

| Fuente | SHA256 |
|---|---|
| `tools/windows/server-install/RackClick.Setup.Lifecycle.ps1` | `2e6fc6b5b1230ce58f6a1de2e58207f4ba5988ab7cd102eb494bec002c71880f` |
| `tools/windows/server-install/RackClick.Setup.Diagnostics.ps1` | `5455103b6643e1c6eb5a0dd183e744ccf63dc6664971cc83a410702c6b304ac4` |
| `tools/windows/server-install/Show-RackClickInstalledServer.ps1` | `20f348e5f4ee6035fd6be37d0d94eb2385124bb4fb9112f28b513eb334c7eeda` |
| `tools/windows/server-install/Collect-RackClickInstallReport.ps1` | `96e571d48d78b96df1f1ff0a55b3c040fb6b1d2cb8c95e6fb3642b6bffec1914` |

Son cambios del coordinador, no de este revisor. No modifiqué producto ni pruebas del autor. La cuarta fuente se añadió expresamente al alcance para comprobar que la proyección llegue al informe exportado.

## Contratos y lecturas

- `Test-SetupUtcTimestamp` exige string UTC con T/Z y formato delimitado, y valida calendario con cultura invariante. `Get-SetupRecordedInstallationState` valida tipo de objeto, schema numérico, GUID canónico, fechas de contexto y orden temporal. La confirmación exige booleanos reales, exit numérico cero, código exacto, UUID de la misma instalación, arranque nuevo respecto al de instalación, checked no anterior al boot/instalación ni posterior a la observación y boot igual al actual (`Lifecycle:3–35`). Un registro de otro arranque queda stale; uno ausente, pending. La salida conserva `currentHealthVerified=false` y `productAdopted=false` incluso en recorded.
- El saneador conserva UUID/fechas sólo después de validarlos (`Diagnostics:14–24`). La nueva proyección usa dos archivos de management derivados del GUID del intento, no rutas tomadas de un JSON, con las verificaciones de ruta/ACL y el lector existente acotado a 1 MiB (`Diagnostics:83–103,198–214`). Rechazos de lectura o ACL no se convierten en positivo. El arranque se mide de nuevo por CIM en el código del colector; no se usa el boot guardado como si fuera el actual. **No ejecuté ese acceso al sistema operativo**.
- Al reabrir, el panel fija 95 y distingue registro guardado de verificación actual (`Show:101–110`). Para alcanzar 100 exige el mismo validador, exit nativo int cero y checkedUtc no anterior a `verificationStartedUtc`, que se fija antes de iniciar su hijo nuevo (`Show:74–80,131–152`). Los stdout tienen nombre nuevo por GUID. No se promueve un JSON anterior del mismo arranque a nueva comprobación.
- `New-SetupSanitizedReport` incluye un default no verde y copia `latest.installationState` (`Collect:52–53`). `Export-SetupSanitizedReport` serializa el Record completo a INFORME.json, Depth 14 y ZIP CreateNew (`Collect:57–70`), sin filtrar de nuevo esa propiedad. Es un contraste de flujo por lectura; no exporté un ZIP ni probé integración de archivos/ACL.
- El `result.json` preboot y su exit 3 no se reescriben por esta proyección. El registro posterior, el estado actual solicitado por el usuario y la adopción del producto permanecen diferenciados. No se añaden operaciones SQL, autenticación o cambios de servicio a estas funciones de presentación.

## Hallazgo propio y corrección

**POSTBOOT-UI-01 · P2 de presentación · corregido.** En la fuente inicial del panel `cc4cb2a63894637a4a0616ea3891632477f1312497e29ed0d2bd776b268e9272`, una verificación previa podía dejar la barra en 100. Al pedir otra, si fallaba Start-Process, el catch indicaba error y exit 1 pero no bajaba la barra: seguía en 100. Lo reproduje con el cuerpo AST exacto del manejador Add_Click, objetos de panel ficticios y los límites ReadReceipt/Start-Process sustituidos por stubs inertes. No se abrió GUI ni se lanzó un hijo real.

El coordinador añadió al inicio del manejador reset a 95, exit 1 y borrado del inicio anterior. Repetí el mismo observador sobre copia nueva de la fuente final: el fallo de inicio deja **95 y exit 1**. La copia roja y su resultado permanecen intactos. No atribuyo este foco simulado a una comprobación visual o de procesos reales.

## Ejecución propia y artefactos

Directorio nuevo privado: `.local/postboot-state-peer-aeb1bea15f7b4f1dbd8f1fc7f836e32c/`.

Se ejecutó `probe_postboot.ps1` en **Windows PowerShell 5.1**, primero contra las copias rojas y después contra `green-source`, con OutputPath distinto. Se extrajeron por AST las funciones de política, saneador y criterio de finalización, sin ejecutar los top-level de los scripts de producto. El manejador sólo recibió stubs inertes. PSModulePath del hijo se fijó a los módulos de WinPS, sin cambiar el host.

| Artefacto propio | SHA256 / resultado |
|---|---|
| `probe_postboot.ps1` | `f802b98af04245b02affb5733ce3f5cde5f8d9c38fb061c2fc78c6e4ec682667` |
| `red.json` | `647b62850b3d3c242a7763abed7e7d65384bdb8c8bd6aa73409200f77fb89878` · exit 1, un fallo de siete |
| `green.json` | `1f4fe1a4bba1f1158e789c1e0d48d53c47ccb26bb12585cbfd175aa57a63f058` · exit 0, siete de siete |

Los otros seis controles propios pasan en ambas fuentes: positivo guardado sin salud/adopción bajo es-ES, offset en lugar de Z rechazado, fecha imposible rechazada, exit nativo string rechazado, checked del mismo boot anterior al nuevo inicio rechazado y booleano array rechazado. Las aserciones usan funciones reales; no hay servicios, cuentas, SQL ni VM. El cambio de cultura fue local al proceso de prueba y se restauró.

No repetí la suite del autor. Su nuevo test `Test-PostbootRecordedState.ps1` se leyó, pero sus ejecuciones e integración de archivos/ZIP pertenecen al coordinador y se registrarán como tales cuando publique el resultado. Mi verde no acredita los lectores protegidos sobre una instalación existente, SCM, HTTPS, tareas programadas ni un reinicio real.

La única escritura pública de esta revisión es este archivo. Fuera de él sólo creé mis fixtures privados. No modifiqué auxiliar W02 de Claude, C#/MFA/C2, paquetes, QA, VM, servicios, cuentas, red, ledger ni instalación. El producto empaquetado anterior no incorpora automáticamente estas fuentes; necesita candidata coherente y revisión de su recorrido correspondiente.

## Adenda · resultados finales del coordinador leídos

Después del dictamen anterior leí los cuatro resultados exactos bajo `.local/postboot-state-8ddb1c7b0e864a709c096069574a04c7/`. **Son ejecuciones del coordinador, no repeticiones de este revisor.** El test del autor final es `tools/tests/setup_lifecycle/Test-PostbootRecordedState.ps1`, SHA256 `e972d17446d1c793c9a79f5177ac87e81aba2129a47ef8deb52dd94d0ddad803`.

| Resultado leído | Resultado declarado / SHA256 |
|---|---|
| `green-final.json` | 45/45 · `89c9b2ac3f50a4559f4744913f0aeb6d70a747f84d26ce667daaf0b058cb16f6` |
| `regression-diagnostics.json` | 20/20 · `3f204554f310dfa30569e923b7e5a309ab16156175e72b902f2e22cd0353f065` |
| `regression-ui.json` | 36/36 · `a0bfeed60c494bee05f920ef691ffa9a67b930eb0adca4264d054a7e91c23964` |
| `regression-automatic-report.json` | 20/20 · `940ffc3648ff33a2bca72199dc2c71d510cddeac8f8ff057a33ffa66f6ef8b0a` |

El 45/45 cubre funciones reales de política/saneado, criterio de llamada nueva, manejador de inicio fallido y fixtures nativos de lectura de archivos, colector superior y ZIP. Declara conservación del result original exit 3, retención de estado separado y ausencia de secreto ficticio en el informe exportado; también el rechazo del último registro negativo/malformado, boot distinto y UUID ajeno. **La integración sustituye el namespace fijo, la frontera de SID esperado, el binding privado de instancia no disponible y el origen CIM de arranque.** No es prueba sobre management/SCM/ACL administrativos reales de una instalación existente ni sobre un reboot real.

Las tres regresiones se registran separadamente: diagnósticos con fixtures privados/lecturas y controles de saneado; construcción STA y políticas de UI sin instalación; exportación automática y procesos propios en fixtures. Sus límites excluyen instalación elevada, SCM, SQL y VM; la exportación usa Desktop aislado cuando corresponde. No he leído credenciales ni logs brutos para contrastarlas.

Estos resultados amplían la evidencia de composición de archivos e informe final, manteniendo el límite de mi ejecución propia en los siete controles AST/política descritos. No aparece un bloqueo material nuevo; los cuatro archivos finales necesitan propagación a una candidata nueva antes de considerarlos disponibles en el servidor. No se añade crédito de QA/adopción ni se habilita Execute del auxiliar W02 pendiente.
