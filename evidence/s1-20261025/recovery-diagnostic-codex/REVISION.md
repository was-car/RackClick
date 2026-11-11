# Diagnóstico de recuperación administrativa · revisión independiente

25.10.2026. Revisor: Codex, agente distinto del coordinador que implementó estos cambios. Propiedad de escritura limitada a este informe y focos privados nuevos. No modifiqué producto, pruebas del autor, archivos de Claude, ZIP, manifiestos, SQL ni C#. No ejecuté instalador, UI, servicios, cuentas, VM, QA, compilación ni PostgreSQL. Sí ejecuté un foco propio WinPS de funciones puras extraídas por AST, descrito abajo.

## Dictamen

**Favorable para el cambio de fuentes final y su posterior empaquetado/revisión.** El defecto de tipos encontrado durante la revisión está corregido y los mismos negativos propios pasan después. No queda un bloqueo material identificado en este alcance. No equivale a una candidata instalada ni cierra el recorrido W-02.02; ZIP 07 no incorpora estas fuentes nuevas.

El cambio conserva el fallo y el contrato de commit. Sólo convierte un rechazo conocido en un diagnóstico específico, sin reflejar mensajes privados ni transformar errores en instalación correcta. No se atribuye retrospectivamente `recovery_username_exists` al primer intento W02-B sin su salida CLI original.

## Lectura de seguridad y contratos

- **`New-RackClickRecoveredInstance.ps1:110–130`:** la promoción exige Label exacto `recover-admin`, exit nativo int 1, stderr string vacío, stdout string acotado a 16384 caracteres y JSON canónico exacto `{"status":"rejected","error":"recovery_username_exists"}`; sólo se toleran CR/LF finales. Duplicados, campos extra, otro error/estado, texto adicional, otro comando o stderr no coinciden. Esa rigidez es deliberada y compatible con el CLI probado; no se cambia por un parser que pierda claves duplicadas. El error publicado es un enum fijo. `finally` conserva parada/cierre del hijo propio.
- **`Prepare-RackClickServer.ps1:123–154`:** extrae la validación de salida a `Read-PreparationChildResult`, manteniendo límite de stdout y rechazo de stderr. Exige objeto, propiedades presentes, bool/int/string y concordancia de exit. Sólo la combinación Label installation + RequiredCode installation_prepared + exit 1 + valid false + código fijo completo se transforma en `preparation_recovery_username_exists`. Los demás errores siguen rechazados. Éxito exige exit 0, valid true y RequiredCode correcto.
- **`Show-RackClickInstaller.ps1:15–18`:** el consejo fijo requiere code/stage/childCode strings y la combinación concreta del fallo de preparación. No inserta el nombre recibido, error CLI ni detalles arbitrarios del proceso. Indica elegir un nombre nuevo y conservar usuarios de la copia. Es diagnóstico; no cambia contraseñas, ámbitos o autorización.
- Comparé las tres fuentes con los scripts de ZIP 07. Normalizando CR para evitar una diferencia puramente de fin de línea en Prepare, los cambios de lógica están acotados a estas ramas y a la extracción del lector. No se modifica `Read-RecoveryCommitResult`, migración, recuperación transaccional, revocaciones o auditoría.

## Hallazgo propio, corrección y foco nativo

Encontré que la versión intermedia comprobaba bool/int, pero no el tipo de `code`. En PowerShell, comparar un array mediante `-ceq` puede devolver una colección verdadera. Un array que contuviera el enum conocido promocionaba el diagnóstico; un array unitario de `installation_prepared` pasaba el lector de éxito; la UI podía activar el consejo con code array. Es un defecto del contrato de datos, **no una instalación falsa real demostrada**; la falta de tipo string del camino anterior de éxito ya era visible en el código histórico.

El coordinador añadió `code -is [string]` al lector y tipos string para code/stage/childCode en la rama UI. Yo no implementé ni aprobé un cambio propio: repetí el mismo foco sobre copias finales separadas.

WinPS 5.1 nativo, bloques de función completos extraídos por AST, StrictMode Latest, sin imports operativos ni procesos hijos:

| Caso | Copia anterior | Fuentes finales |
|---|---|---|
| Control de rechazo canónico escalar | Diagnóstico específico correcto | Igual |
| Negativo: array de códigos con error conocido | Promoción indebida | `preparation_child_failed` |
| Negativo: éxito con code array unitario | Retornaba como aceptado | `preparation_child_failed` |
| Negativo: code objeto | Rechazo genérico | Igual |
| Negativo UI: code array con código conocido | Consejo específico indebido | Consejo genérico |

Resultado propio: **rojo, exit 1 y 3 discrepancias de 5; verde, exit 0 y 5/5**. Las copias/JSON se conservan en `.local/recovery-diagnostic-peer-1cfb11e56b184be0a9b61cf7365ab1a4/`, con subdirectorios before/after. Antes del rojo válido hubo un fallo de serialización del observador con GenericList; preservé `probe_types-attempt01.ps1` y corregí sólo el harness a `.ToArray()`. Ese primer fallo no cuenta como prueba de producto. Las ejecuciones roja y verde válidas usan el mismo harness corregido.

## Ejecuciones del coordinador leídas, no repetidas

Leí estos resultados privados sanitizados bajo `.local/recovery-diagnostic-20261025T145807Z-302bbb69/`:

- `native-green-3.json`: **34 checks PASS**, helpers reales cargados por AST con procesos simulados; cubre canónico/duplicados/extras, tipos, exit, error vacío, otros Labels, commit no aceptado para un rechazo y UI. No es una ejecución del instalador ni una ventana UI.
- `broker-regression.json`: **20 checks PASS**, 15 procesos propios de prueba bajo la identidad actual, sin elevación/cuenta de servicio, SCM, SQL o VM. Conserva metadatos acotados y manejo del exit nativo.
- `owned-pg/result.json`: **PASS en 18,08 s**, PostgreSQL 17.11 nuevo y DLL congelada `19c94d4e…`, sin rebuild. La opción `--owned-operator` del test llama realmente a `Invoke-RecoveryOwnedChild` y `Read-RecoveryCommitResult`. Nombre existente: error exacto y 14 tablas/marcador intactos. Nombre nuevo: usuario original conservado, administrador creado, auditoría 1 y marcador consumido; laboratorio detenido e inputs intactos.

Leí también el test PG ampliado: construye el estado mediante bootstrap/marker, **no pg_restore**; los archivos con credenciales de fixture quedan bajo salida privada y no los abrí. No acredita un Restore de VM ni toda la cadena broker→preparación→GUI como instalación completa. Las 34/20 pruebas y PG son ejecuciones del coordinador, no de este revisor. Su primer intento de loader corregido y los rojos históricos no se confunden con el rojo de tipos propio descrito arriba.

## Huellas finales

| Fuente final | SHA256 |
|---|---|
| `tools/windows/New-RackClickRecoveredInstance.ps1` | `65b44ccc8640cdbcf80aa3ac230a759367b89991ad2da5c52c7766fa8c488a12` |
| `tools/windows/server-install/Prepare-RackClickServer.ps1` | `49a4b9b5ed30ab951fb39d7288630dc4a6b133d117b0beadbc154214aac81467` |
| `tools/windows/server-install/Show-RackClickInstaller.ps1` | `4426e4f9d7105b109a1ca9d2a664d6afb57150218889ad03084f7e8b5b753037` |
| `tools/tests/setup_recovery/Test-RecoveryDiagnostics.ps1` | `fc670979349443c11c6cd9c6216491b4b9481330d6365f32feb5aa9480a9b07e` |
| `development/server/tests/test_recovery_username_collision.py` | `11ca43b279e335f8641a6de83c5cdc866d0bdb3eb7093b5fa44ff736bef6e91c` |

| Evidencia privada de esta revisión | SHA256 |
|---|---|
| `probe_types.ps1` | `d99120dd3ade4083456ecad8397e08f70759527851384258ddb2e86cc998fe7e` |
| `red.json` | `ba0b2ab4f7b0e808edb170e7ebd2d96c77f05fafc689ac34670bfe1756e2230c` |
| `green.json` | `aa03882bcbcab39e58b16799de3e788e21c4b208de1efaf40ddafec04aedd6e5` |
| PG del coordinador `owned-pg/result.json` | `05d019fde43cd9adcaecddfc6fdb3597f51be41ca57b4f13d1ae8a855da1c68c` |

Copias intermedias propias: Prepare `e3effd42…`, UI `f0fb9e8c…`; no son las fuentes finales. La aplicación/DLL de prueba conserva su pin anterior y el operador nuevo tiene hash `65b44ccc…`. Hace falta una edición empaquetada coherente antes de ofrecer este diagnóstico en el servidor; no se marca disponible en QA por existir código fuente. Este dictamen no cambia el ledger ni anuncia adopción.
