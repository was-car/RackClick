# Paso 16 · negativos del sobre MFA

03.11.2026 · **F-05.03 completado con revisión independiente favorable.** D se conserva sin operaciones.

Las pruebas existentes cubren contraseña incorrecta; sal, nonce, etiqueta y ciphertext alterados; truncado; byte añadido o sobre concatenado; versión/algoritmos desconocidos; coste y tamaño fuera de perfil. El codec, las pruebas y las rutas de recuperación pertinentes conservan los hashes de sus revisiones.

Se relacionaron los26casos históricos del autor y los8controles independientes con los rechazos esperados. Los contadores de derivación sólo se declaran donde la prueba los comprueba. Datos extra y concatenación fallan autenticación, sin un recuentoKDF instrumentado en esos dos casos.

El coste fuera de perfil ejecutado es600001; la fuente rechaza cualquier uint distinto de600000 antes de derivar. No se afirma haber probado todos los enteros o todos los truncados posibles. No hace falta una nueva suite para cubrir las categorías exigidas.

La recuperación por componentes comprueba además que contraseña incorrecta o sobre alterado no crean el destino. Esto no sustituye recuperar una instalación real en otroWindows ni acredita el cierre completo de F-05.

[Resultado y límites](../evidence/s1-20261103/f05-03-negativos/RESULTADOS.md) · [Revisión independiente](../evidence/s1-20261103/f05-03-negativos/review/DICTAMEN-F0503.md) · [Matriz de negativos](../evidence/s1-20261103/f05-03-negativos/MATRIZ-NEGATIVOS.md).

Se acredita sólo **1/2 punto**. El índice de cierre restante pasa de **17,63 a18,13/100** (exacto1523/84), conservando pesos y numeración. F-05 completo sigue abierto; no es porcentaje global nuevo ni aceptación final.

No necesitas ejecutar nada ni proporcionar contraseñas/sobres. El siguiente paso numerado es **17/F-05.04**, recuperación del anillo en otra instancia Windows con identidades/AAD y custodia correctas.
