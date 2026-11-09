# F-01 · archivo administrativo autorizado del antecedente perdido

**Decisión de Wascar,03.11.2026:** «Archivar con el límite documentado», en respuesta a la pregunta expresa sobre cerrar los pasos2y4 conservando la incertidumbre, sin declarar falso positivo ni cambiar credenciales de D por conjetura, y reabriendo si aparece evidencia.

## Alcance exacto

Se archiva administrativamente **sólo** el antecedente de las salidas internas de la auditoría `run-1` del25.10.2026. La investigación conservada en [F01-RESOLUCION-ANTECEDENTE.md](F01-RESOLUCION-ANTECEDENTE.md) agotó sus referencias acotadas: el temporal/salida implicados no se conservan y no se pudo identificar un valor autenticador ni su consumidor. La decisión se toma con ese límite explícito.

Se distinguen los canales auth y authz del informe, sin atribuirles contenido recuperado. La observación `OBS-LOCAL-20261025` se dispone con este límite. `OBS-LAB-CHAT` permanece anotada como mención del mismo contexto **no corroborada independientemente y de posible solapamiento**, sin contarse como una segunda exposición demostrada. Su nota contextual se archiva con la incertidumbre, sin inventar una revocación ni extender la decisión a incidentes distintos que aparezcan después. Los registros originales de ambas observaciones no se editan.

- La clasificación factual permanece **indeterminada**. El archivo no demuestra ausencia de exposición, ni que se vieran sólo nombres, ni que el material fuera efímero o revocado.
- No se declara un falso positivo y no se crea una supresión del detector. Los hallazgos concretos clasificados anteriormente conservan sus resoluciones y sus límites.
- No se ha identificado una credencial concreta expuesta en este antecedente. No se presenta una rotación como realizada ni se cambian cuentas, contraseñas, factores MFA, bases, tokens o claves de D/E por conjetura.
- No se autoriza publicación de privados, reescritura de Git, una limpieza de evidencias o aceptación de exposiciones futuras. Los registros anteriores se conservan.

## Condición de reapertura

Si aparece una copia legítima de la salida, una referencia concreta a archivo/campo/consumidor o evidencia verificable de material autenticador expuesto, **se reabre F-01.02 y su revisión F-01.04** y se retira su crédito hasta resolverlo. Se analiza localmente con captura privada y recibo saneado; no se envían valores por chat. Si se identifica una credencial real, rige la coordinación y tratamiento de ese consumidor; no una rotación indiscriminada de D.

La reapertura no depende de volver a pedir a Wascar que recuerde contraseñas. Sin fuente nueva no se repite la búsqueda ya agotada.

## Conciliación explícita del plan

El criterio anterior exigía clasificación/resolución verificables de cada indeterminado. **No se declara retrospectivamente cumplido como cierre técnico.** Se prepara una enmienda limitada `RC-CIERRE-20261103-v3`, después de esta decisión y antes de acreditar:

1. Se conserva íntegra la baselinev2 anterior en el snapshot de [la evidencia nueva](../evidence/s1-20261103/f01-archivo-administrativo/), incluida su huella y la revisión previa de baseline.
2. F-01 mantiene el tratamiento de credenciales reales y sus controles. Se añade únicamente la vía administrativa de este antecedente identificado, con incertidumbre explícita y reapertura obligatoria; no una excepción general para desconocidos.
3. F-01.02 añade esa disposición limitada; F-01.04 conserva su criterio de revisión. Los pesos5/8 de ambos, los IDs,53resultados,280checkpoints,268números y denominador100 no cambian. Los demás criterios, incluida política MFA45, se conservan.
4. Sólo después de revisión independiente favorable se podrán cerrar2y4 **administrativamente**, añadiendo5/4=1,25puntos de cierre. El crédito mide resolución del inventario según la decisión; no una mejora técnica de seguridad ni prueba de revocación.

La clasificación, los controles del escáner y los informes históricos no se reescriben para conseguir una prueba verde. D y sus50clientes permanecen intactos. La adopción global del producto y los pendientes Windows/MFA/backup no se aceptan por esta decisión.
