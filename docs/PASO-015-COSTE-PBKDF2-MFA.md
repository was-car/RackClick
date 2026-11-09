# Paso 15 · coste de PBKDF2 del sobre MFA

03.11.2026 · **F-05.02 completado con revisión independiente favorable.** D se conserva sin operaciones.

Los logs Windows del26.10 contienen seis pruebas de apertura del sobre, cada una con una derivación a600000iteraciones. Publican duraciones de **57–62ms**, con mediana59,5ms. Es el tiempo de cada caso completo, incluidos GCM, limpieza y aserciones; no un cronometraje exclusivo de PBKDF2 ni una medición de D.

Se conserva expresamente el perfil **PBKDF2-HMAC-SHA256/600000/32bytes**: el coste local observado es compatible con el uso administrativo previsto y no se ha demostrado un motivo para reducirlo. No se presenta como parámetro óptimo para todaCPU ni como latencia garantizada. Corresponde al sobre de recuperación, no a cada verificación TOTP del login.

El codec y sus pruebas conservan los hashes revisados. No hace falta compilar o medir de nuevo para este criterio. El procedimiento administrativo acotado y sin solapamientos es una condición de integración pendiente de comprobar, no un limitador ya acreditado.

[Resultado y límites](../evidence/s1-20261103/f05-02-coste/RESULTADOS.md) · [Revisión independiente](../evidence/s1-20261103/f05-02-coste/review/DICTAMEN-F0502.md) · [Decisión del parámetro](../evidence/s1-20261103/f05-02-coste/DECISION-PARAMETRO.md).

Se acredita sólo **1/2 punto**. El índice de cierre restante sube de **17,13 a17,63/100** (exacto1481/84), conservando pesos y numeración. F-05 completo sigue abierto; no es porcentaje global nuevo ni aceptación final.

No necesitas ejecutar nada o facilitar claves/sobres. El siguiente paso es **16/F-05.03**, conciliar los negativos existentes de contraseña, alteración, truncado, datos extra y perfiles fuera de rango. La recuperación real en otroWindows sigue en su paso propio.
