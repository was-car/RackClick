# Paso 15 · F-05.02 · coste Windows y decisión del perfil

03.11.2026. **Cerrado con revisión independiente favorable.** Se reutilizó primero la medición existente. No hubo benchmark, compilación o prueba criptográfica nueva; tampoco operaciónVM/DB/cuentas/servicios/clave. D/E se conservan sin operaciones. Código, dependencias y perfil del producto intactos.

## Qué se contrastó

El criterio exige medir600000enWindows antes de fijarlo y evitar adopción tácita. [Investigación](INVESTIGACION-Y-DECISION.md), [matriz](MATRIZ-CRITERIO.md) y [decisión explícita](DECISION-PARAMETRO.md) documentan su cumplimiento sin añadir otro requisito o repetir una suite.

`CONCILIAR-MEDICION.py`, Python3.12, salida0, extrae por nombres las seis filas del log final de L2d:60/57/58/59/62/62ms, rango57..62 y mediana59,5. Cada caso llama un Open y comprueba una derivación. La corrida anterior61/57/57/58/57/57 se conserva por separado. [Resultado completo](MEDICION-CONCILIADA.json), [segunda verificación](SALIDA-VERIFICACION.json).

La unidad son **duraciones de casos xUnit**, con PBKDF2, GCM, manejo del fallo, limpieza y aserciones; no PBKDF2 aislado. Windows de laboratorio, Debug, runner64bits/.NET10.0.12; SDK10.0.401 consta en los registros. No constan CPU, buildWindows, carga o energía. No se atribuyen estos tiempos a D, Release o cualquier hardware. El primer caso con Lazy73/254ms y la duración de la suite no se ocultan ni convierten en coste de una derivación de parámetros inválidos; se conserva el log íntegro.

Codec/tests mantienen los hashes L2d `8a7b06ee…`/`5d15b220…`; los valores completos constan en el JSON. Se contrastaron11referencias públicas sin abrir binlogs/TRX privados, credenciales o materialMFA. La evidencia antecede a la aceptación de L2d/F-03.02; el prototipo ya debía contener el parámetro para medirlo y no se finge una aprobación previa a las medidas.

## Decisión y precisión documental

Se **conserva expresamente PBKDF2-HMAC-SHA256/600000/32bytes de RCKEYv1**. La escala observada es compatible con el uso administrativo previsto, el perfil está acotado antes deKDF y se preservan los sobres existentes. No se sostiene coste óptimo, latencia universal, resistencia a cualquier contraseña débil o una capacidad de concurrencia medida. Operador local/autorizado y trabajo sin reintentos/solapamiento son requisitos de integración pendientes, no un limitador operativo acreditado.

Fe de erratas fechada en `docs/D2-CONDICIONES-TECNICAS-F03-02.md` aclara la frase histórica «por derivación». [Snapshot y hashes](D2-ACLARACION-UNIDAD.json), [diff](DIFF-D2-UNIDAD.diff): cuerpo original íntegro, sin cambios de algoritmo, perfil, AAD, política45, custodia o criterio. Los documentos/revisiones históricos conservan su texto; esta precisión explica su unidad y no sustituye sus registros por una nueva ejecución. La versión de D2 anterior a la adenda se conserva para contrastar las referencias históricas que la fijaban por hash.

## Revisión y contabilidad

[Dictamen independiente favorable](review/DICTAMEN-F0502.md). Su [verificador](review/Verify-Cost-Evidence.py) terminó en0; [comprobación](review/COMPROBACION-F0502.json) registra extracción propia, once referencias, fuentes y adenda. El revisor no ejecutó benchmarks/VM/producto ni modificó el ledger.

Sólo **F-05.02 +1/2**:1439/84→1481/84 =**17,63/100 del cierre restante**.38checkpoints cerrados/242sin cierre (240pending,2in_progress),53resultados/280checkpoints/268números, criterios, pesos y huella congelada intactos. F-05.03/.04/.05 y todoF05 siguen abiertos. No es porcentaje global nuevo ni adopción.

Planes, contexto maestro, progreso y changelog actualizados; tres generadores write/check y conciliación del único cambio. Escaneo de selección y sello final conservados. Documentos previos/sellos archivados, sin reescribir evidencia antigua. Sin UI/disponibilidadQA modificada, casos/resultados de Wascar intactos; sin commits/push. Siguiente **16/F-05.03**, conciliar los negativos existentes antes de implementar. La recuperación en otroWindows y la aceptación final conservan sus pasos.
