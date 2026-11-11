# Decisión de ingeniería · conservar 600.000 en RCKEYv1

03.11.2026 · F-05.02. Se evalúa el parámetro propuesto a partir de su medición Windows existente. **Se conserva expresamente PBKDF2-HMAC-SHA256 con600000iteraciones, salida32bytes, en el perfil RCKEYv1.** No se cambia el codec ni se anuncia como ajuste óptimo para cualquier hardware.

## Medida reutilizada

El log final de L2d registra seis casos que llaman una vez a `Open` y comprueban una derivación: alteración de ciphertext60ms, sal57ms, nonce58ms, tag59ms, truncado62ms y contraseña incorrecta62ms. Rango57..62ms; mediana59,5ms, calculada sobre los enteros publicados por el runner.

El entorno observado es Windows, runner64bits y .NET10.0.12, proyecto de pruebas Debug. El SDK10.0.401 consta en los registros de entrega/revisión. No constan CPU, plan de energía, carga concurrente o compilación exacta de Windows en esas filas. No se inventan esos datos ni se etiqueta la medición como Release o medida de D.

Cada duración incluye la operación, GCM, manejo del fallo, limpieza y aserciones. No es un cronometraje aislado de PBKDF2 ni una distribución estadística de llamadas idénticas. El primer caso de cabecera aparece con73ms (254ms en el otro log), porque prepara el sobre válido mediante el `Lazy` del fixture; la comprobación del rechazo conserva contador0. Ese tiempo no se convierte en una derivación de parámetros inválidos ni se elimina del log original. La extracción compara sólo los seis casos de una operación descritos arriba; no calcula percentiles/SLA.

El otro log muestra esos seis casos en61/57/57/58/57/57ms. Refuerza la escala local observada; no se fusionan ambos como doce repeticiones controladas. Los casos de ida/vuelta y dos sellados se conservan como contexto, sin dividir sus duraciones para fingir una medida directa de cada KDF.

## Razón de conservar el perfil

1. El coste observado es compatible con un trabajo administrativo local de sellado/apertura de un sobre de recuperación. No se ha demostrado una latencia que justifique reducir el parámetro. No corresponde a cada login TOTP ni acredita una carga de usuarios simultáneos.
2. Los archivos no pueden elegir un coste ilimitado: el perfil validado exige exactamente600000 antes de derivar. Las entradas fuera de ese perfil se rechazan. Se conserva la misma identidad de formato y no se cambian las reglas de sobres existentes.
3. La cifra no se adopta por silencio: D2 la propuso, el autor entregó la medición antes de la revisión L2d que aceptó expresamente el perfil, F-03.02 lo concretó y esta decisión explica su ratificación. La constante del prototipo ya existía para poder medirlo; eso no se confunde con una aprobación final previa a la medición. No se reconstruye una cronología de precisión que no consta en los recibos.
4. El procedimiento final debe ser local/autorizado, con trabajo administrativo acotado y sin reintentos automáticos o trabajos KDF solapados. Es un requisito de integración pendiente de comprobar; esta medición **no acredita que exista ya un limitador operativo de concurrencia**.

Una nueva plataforma, una regresión material de duración o una propuesta de algoritmo/perfil distinta exige evaluación del caso y revisión explícita, conservando compatibilidad/versionado. Esta decisión no reduce el parámetro para obtener un tiempo objetivo arbitrario ni demuestra resistencia universal a contraseñas débiles, hardware atacante o filtración conjunta del sobre y contraseña.

## Alcance del cierre

El criterio original exige medir600000enWindows antes de fijarlo y evitar adopción tácita; no fija un SLA ni un benchmark estadístico en cada VM. Se acreditará sólo F-05.02 tras revisión independiente de esta medida/decisión. Rendimiento de la candidata final, operador de recuperación, otroWindows, negativos finales y cierre de F-05 conservan sus criterios propios. D/E y sus datos/MFA se conservan sin operaciones.
