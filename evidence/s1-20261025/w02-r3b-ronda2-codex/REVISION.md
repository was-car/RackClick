# Revisión independiente W02-R3b · ronda 2

25.10.2026. **Favorable para los dos contratos de REC-02 revisados: los contraejemplos materiales de la ronda anterior quedan cerrados en este alcance.** No habilita por sí sola Execute con 08: falta la conciliación del formato/candidata que realiza el coordinador. No es prueba de instalación, salud actual, QA ni adopción.

Fuentes leídas: mensaje de entrega de ronda 2, resumen/evidencia de Claude, auxiliar actual y casos focales pertinentes. Pins:

- `tools/windows/w02/Invoke-W02TrialPlan.ps1`: `6e7fc20e2aad67a6ebefd642497d298e2d041a0b5a92ac5678af3aa108c4e5b8`.
- `tools/tests/test_w02_trial_plan.py`: `51cee32e2c10665843a3c3034a9591fd078dbd831bb116f9cf36c644de0f8176`.
- Harness `evidence/s1-20261025/w02-r3b-claude/focos-r3b/ejecutar_focos_r3b.py`: `84f71e50d3adedd1ba3fdc443685f3260d54c14c102331ac43689574851b9881`.

## Ejecución independiente

Ejecuté cuatro llamadas nativas **únicamente a Reconcile**, con copia byte a byte del helper y archivos ficticios nuevos. Recibos y fases usan los nombres de campos/tipos/fechas del productor fuente actual: UTC explícita con siete decimales, orden temporal válido, fase 02, validación 02b y ambas fases interactivas completas. El postboot normal contiene los diez campos emitidos tras éxito por el verificador fuente. **No he ejecutado ese productor ni contrastado estos fixtures contra el ZIP 08**; esa comparación corresponde al coordinador.

| Caso propio | Resultado esperado y observado |
|---|---|
| A: fase 02 exit 9 y continuación completa hasta 04 exit 0 | `secuencia_incoherente`, exit del resumen null; hechos conservan 9/0. El motivo identifica exactamente `fase02_distinta_de_cero_con_continuacion`. |
| B: postboot completo, schema 1, identidad/boot/checked UTC válidos, success=true y código esperado pero valid=false/exit 9/rebootVerified=false | `postboot_contrato_incoherente`, `verificacionRegistrada=false`. Motivo único `resultado_verificado_incoherente`. |
| C: control completo positivo | `exit_observado` 0 y `postboot_verificado_vinculo_parcial`, registro true y salud actual no comprobada. |
| D: postboot por lo demás completo sin installationId ni bootUtc | `vinculo_incompleto`, registro false y salud actual no comprobada. |

Así, A/B **no pasan por campos ausentes, schema inválido o fecha ficticia de 2100**: prueban las contradicciones específicas. En cada llamada comparé SHA256 de todas las entradas antes/después; permanecieron idénticas y sólo apareció un nuevo informe. No se restauró/modificó el result preboot.

Comando: `C:/Python312/python.exe -I -B .local/w02-r3b-r2-peer-77c9be578b6d48d9ac59bb2cbb0f97f5/probe_round2.py`. WinPS 5.1 como hijo, con módulos WinPS explícitos. **Exit 0, cuatro de cuatro.** Se leyó CIM local sólo para el boot de contexto; ninguna acción en VM.

Artefactos privados bajo ese directorio:

- Observador ejecutado, conservado como `probe_round2.initial.py`: `aea7ef32173cd0c50b3a76c93c124f6ff6d22ae96cd414039096c0e3157291f1`.
- Resultado original `result.json`: `18b2151fa090ef4ea37fa3bac7bf79ab6c1502621cd628d6abd76817881d9082`.
- `result-corrected.json`: `3a40bc790d42522a65f3f09367fa5169e0310c220b38e1ab2644eb839f70c4c2`.

El original tenía un booleano mal nombrado que podía interpretarse como contraste de payload 08 ya realizado por el coordinador. Conservé original/observador y emití corrección **sólo de metadatos**, sin repetir pruebas ni cambiar sus cuatro resultados: ese contraste no lo ejecutó el revisor y seguía asignado al coordinador. Observador con etiqueta aclarada: `8fd65e105945a27f5ff4e70eafcb226f2e5d565496bce371ec716e5219c26323`.

## Lectura focal y límites

- `ConvertTo-W02Utc:261–268` exige string UTC T/Z y valida calendario con cultura invariante. `Get-W02PhaseVerdict:290–330` comprueba etiquetas, tipos pertinentes, fechas y orden recibo→02→02b→03→04. Rechaza continuación tras exit nativo no cero antes de seleccionar el estado observado. Conserva hechos individuales sin promover su combinación contradictoria.
- `Get-W02PostbootProblems:333–354` exige el contrato de resultado coherente y fechas válidas antes de clasificar identidad/arranque (`454–463`). La tolerancia temporal del código es **ahora +5 minutos**, no rechazo absoluto de toda fecha mayor que ahora. No convierte ausencia de identidad/boot en otra instalación.
- La salida separa `verificacionRegistrada` de `saludActual='no_comprobada_por_reconcile'`. La nota explicita que hashes/auxiliar declarados no autentican recibos. El archivo postboot no declara equipo o run, por lo que el vínculo continúa parcial; el positivo no demuestra salud actual ni procedencia completa.
- Comparé por texto las secciones Lock/Assert/Publish/boot y todo Invoke-W02Execute/entrada frente a mi copia c8cf2f7c de la ronda anterior: **idénticas**. No amplié ni repetí la revisión cerrada de R1b/historia. Los cambios de esta ronda no relajan esas compuertas.
- Las 35 estáticas, diez focales y regresiones comunicadas pertenecen a Claude; las leí como evidencia aportada, no las ejecuté ni las sumo a mis cuatro llamadas. El rojo R7 inicial se atribuye al harness, como declaró el autor, no a un fallo nuevo demostrado del producto.

No encuentro un bloqueo material nuevo dentro del alcance solicitado. Permanecen separados la referencia de edición 07 del helper, la candidata 08 y su conciliación posterior, además de la ejecución manual en Windows por Wascar. No inferir cierre de esos trabajos a partir de esta revisión de Reconcile.

Única escritura pública: este informe. No modifiqué helper, pruebas o procedimiento de Claude, producto, paquetes, ledger, commits ni evidencias históricas. Cero Execute, INICIAR/VerifyOnly, instalador, SQL, autenticación, privilegios, servicios, cuentas, red, secretos o acciones Windows/VMware.

## Adenda · contraste de productores comunicado por el coordinador

Después de mis focos, el coordinador comunicó la comparación estática del payload 08 con las fuentes: `Test-RackClickServerAfterReboot.ps1` coincide en ambos con `fb2630c245b63131c892045b600b970b289d03341a3dcc393420dac5198bd95a`; `Install-RackClickServer.ps1`, con `181ab16c1e930a2ed9e5fff11b626fb2de847622aa1d92e1d0b7e693c139f653`. Confirma la forma del postboot y el preboot awaiting_reboot/95/exit 3/managementPath. **Es su contraste por lectura, no una ejecución de productores ni una comparación realizada por mí.** No repetí esa operación ni leí otras instancias. La futura fijación de referencias 08 y procedimiento continúa separada; no requiere reconstruir estos ZIP por esta adenda.
