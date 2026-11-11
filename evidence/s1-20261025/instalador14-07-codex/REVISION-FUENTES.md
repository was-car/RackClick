# Revisión independiente de fuentes · instalador 07 · W-01

25.10.2026. Revisor: Codex, distinto de Claude, implementador de esta tanda. Alcance: runtime D14-07 y tres empaquetadores. Sin cambios de producto, QA, VM, servicios, red, cuentas ni commits. No se repitieron la suite de 95 ni un ciclo PostgreSQL. Las únicas ejecuciones propias fueron focos de archivos/AST y de empaquetado en un directorio privado nuevo.

## Dictamen

**Favorable al cierre técnico de W-01**, combinando esta revisión/focos propios con el ciclo de runtime corregido ejecutado por Claude y la comprobación de artefactos/focos realizada por el coordinador. No se ha identificado un bloqueo material nuevo en el alcance asignado.

- D14-07 está integrado en el runtime de producto; el escritor y el lector coinciden con la propuesta atómica revisada. Se conserva el rechazo de identidad ajena, la ACL privada y la publicación sin sobrescribir un ganador concurrente.
- La entrada `edition` ya no permite nombres con traversal; los tres generadores comprueban edición/hash antes de crear salidas. Se eliminó el default 05 implícito y la combinación con el bundle histórico incompatible se rechaza.
- La edición 07 es un artefacto nuevo; los paquetes 06 congelados no se han modificado para esta revisión. Generar/verificar paquetes y ejecutar runtime foreground **no acredita instalación limpia Windows, SCM, host C# de servicio ni reinicio de Windows**: continúan en W-02/W-03.

La referencia de seguimiento es `docs/PLAN-CIERRE-RACKCLICK.md`, base RC-CIERRE-20261025-v1. El indicador anterior de 78 % está retirado. Este archivo no modifica el plan ni calcula un nuevo porcentaje global; el coordinador registra una sola vez los subpasos W-01 respaldados por la evidencia conjunta.

## D14-07: lectura y comparación con la propuesta

`tools/windows/server-install/Invoke-RackClickServerRuntime.ps1` pasa de `29c55fd1…` a `f08466f2…`. El bloque de Stop escribe a un temporal UUID dentro del mismo `runRoot`, cierra mediante `Write-BackupNewText`, comprueba ACL y publica con `File.Move`, que no sobrescribe. Si otro Stop publicó primero, revalida ACL y exige schema 1, runId e instanceId esperados. `finally` elimina sólo el temporal propio. Las condiciones posteriores de confirmación de parada siguen exigiendo estado/código adecuados, ausencia de postmaster, liberación del lock y puertos cerrados antes de devolver `server_stopped`.

**Comparación propia por parser WinPS:** extraje los bloques AST de las condiciones `[IO.File]::Exists($request)` y `[IO.File]::Exists($stopPath)` del runtime actual copiado y de la propuesta privada revisada `0752db6a…`. Ambos textos coinciden quitando únicamente CR. Además coincide la secuencia completa de tokens del runtime, excluyendo comentarios, saltos de línea y continuación de línea. El hash binario distinto no representa una implementación nueva no revisada de estos bloques.

### Foco propio: dos escritores solapados

`check_concurrent_publish.ps1` usa los bloques AST exactos, importa los helpers reales y no los sustituye. Un breakpoint WinPS deja al escritor A inmediatamente después del `CreateNew` real de su temporal. Un segundo proceso WinPS ejecuta el mismo bloque y publica B mientras A permanece detenido; después A continúa. Sólo se manipulan los archivos privados del fixture, sin ejecutar el runtime completo.

| Escenario observado | Resultado |
|---|---|
| B tiene la misma identidad que A | B publica primero; A acepta el ganador tras fallar el Move sin overwrite |
| B tiene runId/instanceId ajenos | A rechaza `server_stop_request_invalid`; conserva los bytes del ganador |
| Ambos escenarios | El nombre final no existe mientras A abre su temporal; ACL final válida; bytes de B intactos; cero temporales al terminar |

Esto acredita la rama de publicación concurrente y su validación de identidad, **no dos operaciones completas de Stop contra PostgreSQL**. El primer y segundo intento del observador no acreditaron la programación pretendida: la invocación recursiva de B dentro de la acción del debugger no completó el ganador. Se conservaron los directorios y el diagnóstico. El tercer intento usa B en un proceso WinPS aparte y termina exit 0 con ambos escenarios. No se atribuyen los intentos fallidos a un defecto del producto.

## Edición y hashes antes de escrituras

- `package_server_installer.py:38`: `checked_edition` exige una cadena ASCII de dos dígitos mediante `fullmatch`, un SHA256 hexadecimal minúsculo de 64 caracteres y un pin presente exactamente una vez como literal entre comillas en `RackClick.Setup.ps1`. `build` lo llama en su primera instrucción, antes de comprobar entradas o crear salidas.
- `package_clean_server_installer.py:10`: los parámetros de edición y digest son obligatorios; repite esa validación antes de delegar la construcción interior. El prefijo del envoltorio sólo incorpora los dos dígitos validados y nombres internos literales.
- `package_cambio_ip.py:29`: comprueba edición y formato de digest antes de abrir entrada/salida; después exige el digest real de `payload.json` y el pin correspondiente del motor antes de crear el ZIP. Sus miembros proceden del payload fijado y de nombres internos literales.
- Las tres CLI exigen los nuevos argumentos. Los destinos continúan confinados y protegidos por creación exclusiva. No se han convertido dos salidas en una transacción: un fallo posterior del envoltorio puede dejar el payload nuevo, como declara Claude.

La comprobación del pin es de coherencia con la fuente, no un registro cerrado que asocie cada número de edición a un contenido. No acredita regenerar 05 ni acepta como equivalentes sus fuentes antiguas. Al retirar los defaults desaparece la generación histórica implícita e incoherente identificada en la revisión 06.

### Foco propio distinto de las pruebas del autor

Ejecuté `check_guards.py` sobre copias byte a byte de los tres módulos y de sus dos fuentes de pins, en su estructura relativa normal, sin mocks ni cambios de funciones. **17 rechazos esperados**, exit 0:

- Ediciones con NUL, CR, dígitos arábigos e indicador bidi/traversal, en los tres builders.
- Hash de formato válido pero valor ajeno a la fuente, en payload y envoltorio.
- Hash de payload pasado como bytes en el builder de IP.
- ZIP mínimo real: digest de payload incorrecto y, con digest correcto, motor incoherente; rechazos `payload_hash_mismatch` y `engine_pin_mismatch`.

Cada operación dejó la carpeta de salidas exactamente igual, incluido el hash de un archivo testigo existente. Se verificaron de nuevo los hashes de las fuentes al finalizar. Los casos con ZIP mínimo alcanzan la comprobación de contenido y motor; no se limitan a entradas ausentes. No se construyó ni extrajo un instalador real en este foco.

## Atribución de las demás pruebas

Leí `evidence/s1-20261025/instalador14-07-claude/RESULTADOS.md` y `d14-07/LIFECYCLE-RESULT.json`. **La ejecución de 83,02 s es de Claude**, no mía: runtime foreground, perfil real enlazado con recibo sintético explícito, aplicación e9/DLL19c, login/CSRF/escritura/backup, dos paradas normales y persistencia tras reinicio foreground. Declara `applicationHttpDrain=false`, sin SCM ni reboot Windows. No se amplía ese alcance a MFA por HTTP ni al proveedor de custodia.

El coordinador comunica su auditoría de la cadena ZIP y hashes, conservación de 06, 14 pruebas afectadas sin omisiones y repetición nativa del escritor original/corregido. Son sus ejecuciones; no las he duplicado. Mi dictamen no transforma las 95 pruebas comunicadas por Claude en 95 pruebas propias.

## Relación con W-01

| Subpaso | Evidencia que respalda su acreditación |
|---|---|
| W-01.01 | Integración del runtime actual, igualdad con la propuesta y foco propio de publicación solapada/ACL/identidad |
| W-01.02 | Validación temprana en tres builders, negativos propios y del autor, y nombres del artefacto final revisados por el coordinador |
| W-01.03 | Focos de carrera original/corregida del coordinador, negativos propios y lifecycle foreground de Claude con límites explícitos |
| W-01.04 | Esta revisión independiente y hashes de fuentes/artefactos; D14-05/D14-06 no reabiertos ni modificados |
| W-01.05 | Conclusión conjunta del coordinador sobre las evidencias anteriores: no persiste la publicación parcial demostrada ni la edición insegura de 06; no equivale a aceptación de Windows instalado |

## Identidades y evidencia privada propia

| Fuente de producto revisada | SHA256 |
|---|---|
| `Invoke-RackClickServerRuntime.ps1` | `f08466f2a7633074131ad0a261bdb98f83f5a292e5a8a366c04e76cd6cfca2ed` |
| `package_server_installer.py` | `d998d898e2460816687b4dca4c3aa2778d00fbcc8d3b36a660c1252d3e6232ce` |
| `package_clean_server_installer.py` | `49ce188165ecca2da636e834e4d0534ab94860b22d93ea70c3a6d194ba478732` |
| `package_cambio_ip.py` | `e7d4b8273cc091d930635af888da994f5c4803941816f9a3b84b53a24ef62c95` |

Raíz privada: `.local/installer07-review-peer-ff944d6fd3fc4dde94792e9d2b187028/`.

| Registro propio | SHA256 |
|---|---|
| `check_guards.py` | `6e44bbec73062903f75841b9989e09e2e9d309634449dad8b8c394f26fbfd557` |
| `guards-result.json` | `97551e3a424068b9ca2c5e54931cd51320f56a788ceab27388902747e44ad6e8` |
| `check_concurrent_publish.ps1` | `7e8d3b4893f07dffc3a1b131eb7e54f771144cf40ff8343d264b18ee6f498795` |
| `concurrent-result.json` | `0d6c0caeca0db8fc489302dc47b6842409e18079e204348306de5038675baa1d` |

`attempts.json` conserva el alcance de los dos intentos no acreditados y del tercero válido. El resultado lifecycle de Claude leído tiene SHA256 `8b33332467257c1f10f3903e7dcb1c7686f5d2157914a764701beb66a01d58e9`.
