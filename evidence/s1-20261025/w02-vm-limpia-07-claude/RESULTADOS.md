# W-02 · Preparación del recorrido New y Restore de la edición 07 — resultados

Fecha: 25.10.2026. Estado: **auxiliar y procedimiento corregidos en tres rondas de revisión de Codex; sin ensayo en VM. W-02.01 a W-02.05 siguen pendientes, 0 de 2,50 puntos.**

Qué no se ha hecho: no se ha instalado nada, no se ha lanzado el envoltorio oficial en ningún equipo, no se ha tocado la VM QA (192.168.250.78) ni la edición 07 (bytes intactos), y no se han generado recibos sintéticos de VM.

Entorno de las pruebas: equipo de desarrollo con nombre de host `LEAO`, Windows 11 Pro 10.0.26300. Windows PowerShell 5.1 para análisis y ejecución del ejecutor. Python 3.12 para leer ZIP y generar focos. Todo lo generado está en `.local/w02/focos/` (privado, fuera de git).

## Historial de rondas

1. **Primera revisión de Codex:** R1 (el envoltorio no quedaba vinculado al ZIP oficial), R2 (un informe local fabricado validaba la hoja), H1 (diagnóstico de rutas). Corregidos; ver el registro de hashes.
2. **Segunda revisión (`docs/REVISION-W02-CORRECCIONES-CODEX.md`):** R2 y el inventario de R1 quedan cerrados. Quedan **R1b** (la segunda llamada podía recibir otro `INICIAR.ps1`), el texto de reapertura tras reinicio y una batería que no fallaba con código distinto de cero.
3. **Esta ronda:** corregidos R1b, la reapertura y la batería. Ver abajo.

## Esta ronda

- **R1b · bytes bloqueados durante ambos lanzamientos.** `Lock-W02WrapperFiles` abre cada fichero validado del envoltorio solo para lectura y sin compartir escritura ni borrado. Los hashes se calculan sobre esos mismos identificadores. `Assert-W02LockedFiles` vuelve a comprobarlos antes de la primera llamada y antes de la segunda. Los identificadores se cierran en un `finally` tras la segunda llamada. Además, el manifiesto autorizado se comprueba primero.
- **Reapertura tras reinicio (§5.5).** Se abre el acceso `RackClick-VERIFICAR-05-<8 caracteres>.cmd` que la edición 07 dejó en el Escritorio durante la fase de instalación (`New-CleanVerificationEntry` en `INICIAR.ps1`, línea 138). Ejecuta `Show-RackClickInstalledServer.ps1 -VerifyInstallation` con elevación. No se vuelve a ejecutar Execute, `INICIAR.ps1` ni la limpieza. Si el acceso no existe, parar y recoger el informe. El `05` del nombre es la etiqueta histórica ya documentada.
- **Batería.** Cada ejecución crea un directorio nuevo `.local/w02/focos/run-<fecha>-<pid>`. El código de salida de Python se conserva. Un caso fallido, un lanzamiento detectado o la falta de comprobación final dan código 1. La comprobación de "no lanzado" se hace después de los casos. `W02_FOCOS_NEGATIVO=1` ejecuta una prueba deliberadamente fallida: sale con 1 y marca `LANZADO`. Verificado.
- **H1, matiz de evidencia.** Los caracteres de control se revisan en cualquier campo de texto. Los caracteres inválidos para ruta solo en `backupPath`. Un JSON roto no identifica campo (`plan_json_invalid`, `field` vacío) porque la hoja no se pudo leer. El diagnóstico no cubre toda excepción del validador oficial.
- **Orden de comprobación.** El primer intento de la batería fallaba en un caso: la alteración coordinada de `INICIAR.ps1` y `PAQUETE.json` salía `execute_wrapper_hash_mismatch` porque `INICIAR.ps1` se comparaba antes que `PAQUETE.json`. Era un rechazo correcto, pero el código no coincidía con la clasificación prevista. Se corrigió en el ejecutor: el manifiesto autorizado se comprueba primero. El intento fallido se conserva en `focos/RESULTADO-FOCOS-intento-1-FALLO.txt`.

## Registro de hashes

| Momento | SHA256 | Nota |
|---|---|---|
| Declarado en la primera tanda | `0bc555ce59fb383a0a47e824a7081ebae7f41049e06494758506e1bf75d70e57` | Medido antes de quitar la línea "Escrito para:". Ya no corresponde al fichero |
| Medido por Codex en la versión recibida (primera revisión) | `b82c097af8d7ee2e10e62940885601ccf32c7d7bba34d41371a7a5543f8617f7` | Versión anterior a la primera corrección |
| Procedimiento tras la primera corrección | `5053890dfc998916362ea278dee7070076d6183b534e2d5d51237e1453e28a84` | Versión anterior a esta ronda |
| Procedimiento tras la corrección de reapertura, batería 3 | `c7eaaa156aaef2831edc01015535524e6bd9ac81de92cd9883637f30a0305c6d` | Versión anterior a la comprobación de la primera llamada |
| **Procedimiento final (esta ronda)** | `696bd1d720924c33086d39d44404f7c3fec33b06ab01e8f7362214ed0b9d03d7` | Incluye la comprobación de la primera llamada (`-VerifyOnly`) antes del lanzamiento interactivo; registrado por la batería 4 |

Hashes finales de los ficheros de esta ronda (medidos con `sha256sum` tras la última edición; coinciden con los que registró la batería final):

| Fichero | SHA256 |
|---|---|
| `tools/windows/w02/Invoke-W02TrialPlan.ps1` (ejecutor) | `28c0b0c0309aab59b54e36aa0cbc14a0ab1667f0a3ebaeeb6da1246cb3749999` |
| `tools/tests/test_w02_trial_plan.py` | `c89fe7265ed47924558ed1c5f0422347cafd963cbf7619474e1fe0d70f6d0f33` |
| `docs/PROCEDIMIENTO-W02-NEW-RESTORE-07.md` | `696bd1d720924c33086d39d44404f7c3fec33b06ab01e8f7362214ed0b9d03d7` |
| `evidence/…/focos/generar-focos.py` | `5a94825de08d5f0e8cbc2c7df9b61357256762b085626378bf222817c4bac547` |
| `evidence/…/focos/ejecutar-focos.sh` | `bcc672d99d96561541dc4a9bd9435790714efa38e62046922beae3feca72a918` |

Los informes del ejecutor de los focos llevan el `runnerSha256` de la copia de prueba que se ejecutó (sin exclusión de LEAO, sin la compuerta de Check, o con lanzador simulado), no el del ejecutor de producción. Por eso los focos registran también el hash del ejecutor de producción.

## Pruebas: separadas por tipo

### Estáticas

`python tools/tests/test_w02_trial_plan.py`: **21 pruebas, OK.** Cubren pins de la entrega 07, pin del `payload.json`, pin del `PAQUETE.json` auténtico frente al ZIP oficial, orden de compuertas y del bloqueo dentro de `Invoke-W02Execute`, ficheros bloqueados solo para lectura, ausencia de confianza en `plan-report.json`, diagnósticos H1 antes del validador, los 15 campos frente al validador oficial, exclusiones, ASCII puro, puntos del procedimiento (reapertura del acceso del Escritorio, UUID aparte, VM B, NTFS y `export_complete`, `plan_json_invalid` sin campo) y la batería (código de salida, comprobación de lanzamientos después de los casos, directorio nuevo por ejecución).

Las estáticas no acreditan por sí solas las propiedades de seguridad; los focos nativos siguientes sí las ejercitan.

### Focos nativos en LEAO (no es VM)

Ejecutados con `bash evidence/…/focos/ejecutar-focos.sh C:/RackClick_SVR`. Resultado final: [focos/RESULTADO-FOCOS.txt](focos/RESULTADO-FOCOS.txt): **`BATERIA_OK`, código de salida 0.** 24 comprobaciones OK y ninguna FALLO, además de la línea BATERIA_OK. Resultado de la batería 4, la última: `run-20261025T123610-1015`, posterior a la última edición del procedimiento. Las baterías 1 a 3 de esta ronda (`run-…-447`, `run-…-1610`) quedan en `.local/w02/focos/`.

| Caso | Esperado | Observado |
|---|---|---|
| Estáticas | rc 0 | rc 0, 21 pruebas |
| H1 control en `backupPath` | `plan_field_control_character` | igual |
| H1 ruta inválida | `plan_field_invalid_path_character` | igual |
| H1 JSON roto | `plan_json_invalid` | igual |
| Plan válido (regresión) | `setup_plan_valid` | igual |
| R2 informe falso + modo `INVALID` / puerto 0 / hoja incompleta | rechazo oficial | `setup_mode_or_trust_invalid` / `setup_port_invalid` / `setup_plan_invalid`; `plan-report` sustituido por `fail` en los tres |
| Producción LEAO + allowlist LEAO | `execute_host_excluded` | igual |
| Producción `Check` | `os_not_server_2025` | igual (LEAO es Windows 11) |
| W envoltorio íntegro (parada antes del lanzamiento) | `prueba_stop_before_launch` | igual |
| W alteración coordinada `INICIAR.ps1` + `PAQUETE.json` | `execute_wrapper_package_mismatch` | igual (tras el ajuste de orden) |
| W extra declarado | `execute_wrapper_files_unlisted` | igual |
| W solo `PAQUETE.json` | `execute_wrapper_package_mismatch` | igual |
| W solo `INICIAR.ps1` | `execute_wrapper_hash_mismatch` | igual |
| W directorio como unión (reparse) | `execute_wrapper_reparse_not_allowed` | igual |
| **SIM control sin ataque** | `w02_official_flow_exited`, bytes autorizados en ambas llamadas | igual; `verify=ok full=ok` |
| **SIM ataque entre llamadas** | intentos bloqueados, bytes autorizados en ambas llamadas | `escritura_bloqueada renombrado_bloqueado borrado_bloqueado carpeta_bloqueada`; `verify=ok full=ok` |
| Ningún lanzamiento real | sin `execute-verify-salida.json` en los 6 directorios de envoltorio | `NO_LANZADO comprobado en 6 directorios` |
| Prueba negativa deliberada (`W02_FOCOS_NEGATIVO=1`) | código de salida 1 | código 1, `FALLO` y `LANZADO` marcados |

Qué demuestran: las compuertas de Execute se aplican en el orden previsto; la validación de la hoja no depende de informes locales; las alteraciones del envoltorio probadas se rechazan antes del lanzamiento; los ficheros validados no pueden ser escritos, renombrados ni borrados durante la primera llamada, y la segunda llamada recibe los bytes autorizados.

Lo que **no** demuestran: que el envoltorio real funcione; que un proceso real hijo (`INICIAR.ps1 -VerifyOnly`) pueda leer los ficheros bloqueados (el lanzador simulado sí lee el fichero bloqueado con `Get-FileHash`, pero no es el envoltorio); ni que una instalación con esas entradas funcione.

Nota de reproducibilidad: las baterías de esta ronda se ejecutaron desde Bash sin `PSModulePath` heredado de PowerShell 7. Codex reprodujo un fallo de `Get-FileHash` cuando el shell hereda esa variable; para repetir la batería, ejecutarla con `unset PSModulePath`.

Nota sobre el alcance: el lanzador simulado sustituye `INICIAR.ps1` por `sim/sim.ps1` solo en la copia de prueba; el ejecutor del repositorio no se ha cambiado para ello. No se ha ejecutado el `INICIAR.ps1` real en LEAO, porque `-VerifyOnly` escribe en `%LOCALAPPDATA%\RackClick`.

### VM no ejecutada

Estado del entorno, comprobado en solo lectura (`vmrun list` y los `.vmx`): VMware Workstation está instalado. Hay tres VM registradas:

- `RackClickSRV`: **encendida ahora**, con memoria activa. Podría ser la VM QA `192.168.250.78`; no se ha tocado.
- `Windows Server 2025`: apagada, sin instantáneas (`.vmsd` vacío) y con una carpeta de bloqueo de octubre. Nadie ha comprobado si está limpia; no se arranca sin decisión del usuario.
- `RackClick-Ubuntu-24.04`: no es Windows Server; no aplica.

Hasta que el usuario elija la VM de prueba, el ensayo queda pendiente. Ninguna VM se ha arrancado ni modificado.

- Lanzamiento real de `INICIAR.ps1 -VerifyOnly` y del flujo interactivo del envoltorio, con los ficheros bloqueados.
- Recorrido New y Restore en la interfaz, incluido el reinicio y la apertura de `RackClick-VERIFICAR-05-*.cmd` del Escritorio y **Verificar instalacion**.
- Exportación con el diálogo NTFS, `export_complete`, traslado a la VM B y restauración con dato sintético.
- Informe sanitizado de `Collect-RackClickInstallReport.ps1` y su SHA256.
- Controladora de dominio real (`DomainRole` 4 o 5) y rechazo de versión incompatible del host (W-02.03).
- Windows 11 como host (W-02.04).

## Hallazgos abiertos

- **H1 (validador oficial).** Sigue vigente: una ruta inválida no cubierta por el diagnóstico propio llega a `Read-SetupPlan` y lanza una excepción de .NET sin código oficial; el ejecutor la registra como `w02_plan_failed` y falla cerrado. Decisión pendiente para una edición posterior; no se modifica el validador ni la 07.
- **H2 (hoja y plan de la interfaz).** Sin comparación automática. El procedimiento exige comparar los 14 campos a mano y anotar el UUID real aparte.
- **H3 (etiquetas "05").** Tres textos en el envoltorio 07: el título del formulario, el cuadro de error y el nombre del verificador. Documentados; se parametrizarán en una edición sustantiva posterior.
- **H4 (exclusiones).** LEAO y 192.168.250.78 se excluyen; la allowlist y el requisito de Windows Server 2025 no controlador de dominio se mantienen. Son controles adicionales, no sustituyen comprobaciones del host.

## Crédito propuesto

**0,00 de 2,50 puntos** para W-02.01 a W-02.05. La corrección y los focos prueban el auxiliar, no la instalación; ningún subpaso se cumple con eso. El crédito se propondrá solo con evidencia de VM, según el criterio del plan de cierre.

No se modifica el índice de cierre ni se estima porcentaje del producto.

## Propuesta de registro para el plan de cierre

Para que Codex concilie el ledger. Este bloque no ha modificado `docs/PLAN-CIERRE-RACKCLICK.md` ni su JSON.

- W-02.01 · pendiente · procedimiento apartado 2 · crédito propuesto 0 · VM pendiente.
- W-02.02 · pendiente · procedimiento apartados 5.1 a 5.5 · crédito propuesto 0 · VM pendiente.
- W-02.03 · pendiente · procedimiento apartados 5.1 y 7; puerto ocupado probado en LEAO (`port_in_use`); rechazo de versión y DC real pendientes · crédito propuesto 0.
- W-02.04 · pendiente · fuera de este procedimiento · crédito propuesto 0.
- W-02.05 · pendiente · criterio de cierre y revisión independiente sobre la evidencia de VM · crédito propuesto 0.
- Restore en dos VM (procedimiento apartado 6) · pendiente · parte del criterio de cierre de W-02.

## Próximo paso

Revisar esta ronda. Después, ensayo en una VM Windows Server 2025 limpia no DC, con el registro del apartado 2 y las evidencias de New, reapertura del acceso de verificación, Restore en VM B e informes. Hasta entonces, W-02 sigue en 0 de 2,50.
