# W-02 · revisión de correcciones · 25.10.2026

**Dictamen: R2 cerrado; R1 corrige la autoridad del inventario, pero queda R1b en el paso al lanzamiento. No usar Execute para el ensayo hasta corregir ese paso y la reapertura tras reinicio.** No hay instalación, VM ni crédito nuevo: W-02.01–05 continúan pendientes, **0/2,50 puntos**. La edición 07 y el cierre W-01 se conservan.

Revisión de helper `48543689…`, pruebas `2e8ccf7f…`, procedimiento `5053890d…`; [hashes completos recibidos](../evidence/s1-20261025/w02-correcciones-codex/RECEPCION.json). Los cuatro ZIP 07 conservan sus hashes fijados. No se modificó código de Claude.

## Resultado de las correcciones

- **R1, inventario:** el original pasa; archivo/manifiesto alterados conjuntamente, extra declarado y junction se rechazan. El inventario se obtiene del ZIP oficial y su PAQUETE auténtico; el manifiesto local ya no autoriza archivos. Esta parte está comprobada.
- **R2:** Execute ejecuta el validador oficial sobre la hoja real. Los tres informes falsos no autorizan modo inválido, puerto cero ni hoja incompleta, y su `plan-report.json` queda en fail. Cerrado para el defecto revisado.
- **H1 auxiliar:** se comprueban los tres códigos nuevos. Precisar la evidencia: controles se revisan en cualquier campo string; caracteres inválidos de ruta sólo en `backupPath`. JSON roto puede tener `field` vacío porque no se pudo identificar un campo. El diagnóstico no cubre toda posible excepción del validador oficial.
- **Procedimiento:** UUID aparte/otros 14 campos, red propia de VM B, repetición de §5.5–5.7 y exportación NTFS con `export_complete` corregidos. La causa y los tres hashes documentales se conservaron correctamente.

## R1b · P2 · conservar los bytes hasta ambas llamadas

`Invoke-W02Execute` comprueba el directorio con `Assert-W02WrapperTree`, llama a INICIAR con VerifyOnly y después vuelve a ejecutar el mismo archivo. No conserva su identidad mediante bloqueo/copia protegida ni lo vincula de nuevo al pasar a esa segunda llamada.

El foco mantiene la función Execute original y controla Plan, Check y Start-Process. La primera llamada recibe el INICIAR auténtico; el simulador añade un comentario inocuo y devuelve un VerifyOnly válido. La segunda llamada llega con **hash diferente**, y Execute termina `w02_official_flow_exited`. **No se ejecutó ese archivo ni hubo hijos del envoltorio**: demuestra la desvinculación de la comprobación y la segunda llamada, no una explotación real en VM.

**Corrección acotada al helper:** mantener acceso de lectura sin compartir escritura/borrado sobre los archivos realmente validados, comprobar sus hashes mientras estén protegidos y conservar esa vinculación durante ambas llamadas; o lanzar una copia privada protegida validada contra los mismos pins. Incluir rutas/ancestros, reemplazo y reparse. Comprobarlo sólo otra vez y volver a dejar una ventana no resuelve la propiedad. Negativo necesario: intento de cambio después de VerifyOnly se rechaza o queda bloqueado, y ambos lanzamientos conservan los bytes autorizados. No requiere regenerar 07.

## Reapertura y batería de pruebas

**Procedimiento §5.5:** «reabrir el instalador» sigue siendo ambiguo. INICIAR del envoltorio pasa por inventario/limpieza; no es el acceso de comprobación posterior. Indicar abrir el acceso del Escritorio **RackClick-VERIFICAR-05-*.cmd creado por ESTA edición 07**, seleccionar la instalación existente y pulsar **Verificar instalacion**. No volver a Execute, INICIAR o limpieza tras reiniciar. Si el acceso no existe, detener y recopilar el informe, sin improvisar otra instalación. El 05 del nombre es la etiqueta histórica ya documentada. También se precisa la formulación anterior de Codex, que no distinguía esos accesos.

**Batería Bash:** registra observaciones útiles, pero no garantiza fallo del proceso ante FALLO: el último cat puede salir cero, la tubería de estáticas pierde el código Python y NO_LANZADO se imprime siempre. Corregir la agregación de resultados y verificar con un caso intencionadamente fallido que devuelve código no cero. Usar un directorio nuevo por ejecución y evitar la retirada mediante rmdir construido en otra shell. No se ejecutó esa batería sobre los directorios existentes de Claude; la repetición propia usa salidas nuevas y no borra fixtures.

## Decisiones y evidencia

**H1 del validador oficial:** queda registrado para una edición posterior pertinente; no modificar RackClick.Setup.ps1 ni reconstruir 07 sólo para ampliar el diagnóstico. Los casos no cubiertos siguen fallando cerrado; no impiden por sí solos un ensayo con entradas válidas. **H2:** comparación manual de los 14 campos y UUID real aparte. **H3:** etiquetas históricas documentadas; ninguna regeneración cosmética.

Codex repitió **16/16 estáticas** y verificó **12 observaciones nativas esperadas**, además del testigo R1b. El revisor distinto leyó procedimiento/launcher y límites del foco; no ejecutó esas pruebas. [Cierre y reproducción](../evidence/s1-20261025/w02-correcciones-codex/CIERRE.md), [revisión distinta](../evidence/s1-20261025/w02-correcciones-codex/REVISION-PROCEDIMIENTO.md), [tanda para Claude](MENSAJE-PARA-CLAUDE-W02-CORRECCIONES-25-10-2026.md).

Sin QA/VM, servicios, cuentas, SQL, paquetes, commits ni publicación. Cierre del pendiente **25/7 = 3,57/100**, 8/280 subpasos y 1/50 resultados completos; delta cero y sin porcentaje global del producto.
