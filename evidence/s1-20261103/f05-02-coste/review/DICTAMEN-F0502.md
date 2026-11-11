# F-05.02 · dictamen independiente de coste y decisión

03.11.2026. Revisor `rackclick_security`, distinto del autor del codec y del coordinador que concilia la medida. **Favorable a cerrar sólo F-05.02, con su peso original de 1/2.** El criterio exige medir el parámetro propuesto en Windows y decidir explícitamente; no exige un benchmark aislado de PBKDF2, otra VM o un SLA de producción. No se identifica un hueco que justifique repetir el trabajo.

## Qué se midió realmente

Se inspeccionaron el codec y pruebas invariables, los logs públicos L2d, su revisión independiente previa y la matriz/decisión actuales. El [verificador independiente](Verify-Cost-Evidence.py), salida 0, contrasta 11 referencias por hash y extrae directamente las filas; [resultado](COMPROBACION-F0502.json).

El log final contiene seis casos con una llamada `Open` y aserción de **una derivación**: ciphertext60, sal57, nonce58, etiqueta59, truncado62 y contraseña incorrecta62 milisegundos. Rango **57–62 ms**, mediana **59,5 ms** sobre los enteros publicados. El otro log contiene 61/57/57/58/57/57 ms y se conserva separado.

Son **duraciones de casos completos de xUnit**, con apertura, PBKDF2, GCM, tratamiento del fallo, limpieza y aserciones. **No son tiempos exclusivos de la función PBKDF2** ni seis repeticiones idénticas para obtener percentiles. El entorno documentado es Windows de laboratorio, proyecto Debug, runner64bits/.NET10.0.12 y SDK10.0.401. No se inventan CPU, carga, plan de energía o build de Windows ausentes del registro; no se extrapola a D o a cualquier hardware.

El primer caso de cabecera 73ms, y 254ms en la otra corrida, incluye la preparación del sobre válido mediante Lazy del fixture. El rechazo de esa llamada `Open` comprueba cero derivaciones; no se usa el tiempo de todo el caso para afirmar que el rechazo derivó o que costó cero milisegundos. Las duraciones de dos sellados/ida y vuelta son contexto, no medidas puras obtenidas dividiendo entre dos.

## Criterio y decisión explícita

La fuente actual del codec conserva `8a7b06ee0441086c40aba3cc8735c21fc562eee08383a58e6ed169b01b7d7fe1`; sus pruebas, `5d15b220d6d12cfe9ab8e340fe39a8e902b47f609af434989f84db96060e4a1f`. El parámetro medido es el mismo600000, no una cifra nominal sin ejecución previa.

La [decisión de ingeniería](../DECISION-PARAMETRO.md) conserva expresamente600000 tras leer esa evidencia. La medida precede a la aceptación documentada L2d y a las condiciones F-03.02; se distingue la constante del prototipo usada para medir de una aprobación final anterior a la medida. No se reconstruye una cronología de mayor precisión que la conservada.

La razón es suficiente y acotada: escala local observada compatible con el trabajo administrativo previsto, perfil ya validado/limitado antes de KDF y conservación del formato. No se sostiene que600000sea óptimo universal, que todas las contraseñas sean seguras o que el servidor soporte una concurrencia determinada. El procedimiento local/autorizado, sin reintentos automáticos o trabajos solapados, permanece como requisito de integración; **no se acredita un limitador operativo existente**.

La fe de erratas de D2 precisa la frase histórica «por derivación». Se verificaron el snapshot y hashes antes/después, encabezado conservado y cuerpo original íntegro: cambia la explicación de unidad, no el perfil, AAD, custodia, política45 o criterio. La corrección no sustituye los logs ni se presenta como otro benchmark.

## Límites y recomendación

Esta revisión sólo ejecutó extracción/comprobación documental. Cero compilaciones, pruebas criptográficas nuevas, benchmarks, sobres, VM/D/E, servicios, DB o lecturas de credenciales/claves/binlogs/TRX privados. No se modificó producto o ledger. La evidencia histórica conserva su autoría y contexto.

Coste en la candidata final, recuperación portable, otro Windows, negativos F-05.03, operación real F-05.04 y cierre F-05.05 siguen sus criterios. No se reduce el parámetro para lograr un tiempo arbitrario ni se concede aceptación productiva.

Recomendación exclusiva: **F-05.02 +1/2**, `1439/84 → 1481/84`, **17,63/100 del cierre restante** cuando lo registre el coordinador. No se cierra todo F-05, no se añaden puntos por muestras y no se declara un porcentaje global nuevo.
