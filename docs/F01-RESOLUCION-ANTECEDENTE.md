# F-01 · resolución investigada del antecedente de exposición

02.11.2026 · Borrador factual para revisión independiente. D, otras VM, cuentas, claves y resultados QA no se modifican. Este documento no acepta riesgo en nombre de Wascar ni acredita puntos.

## Resultado

Se agotó una investigación adicional concreta sobre las fuentes primarias conservadas del `run-1`: se separaron los canales de exposición, se localizaron las referencias de salida y se buscaron sus identificadores exactos en los eventos de herramientas del proyecto del día de la auditoría. **No se recuperó la salida implicada ni una referencia que permita identificar una credencial y su consumidor.** No corresponde declarar revocación, efimeridad o ausencia de exposición a partir de esto.

El resultado no es «faltó preguntar otra vez al operador». Se conserva su respuesta «No lo sé» y no se le pide recordar o enviar contraseñas. La limitación es la falta del registro técnico que permitiría atribuir el material.

## Qué ocurrió según las fuentes primarias

Los informes originales y los resultados de los hunters distinguen tres situaciones:

| Canal | Fuente conservada | Hecho declarado | Qué no demuestra |
|---|---|---|---|
| Búsqueda recursiva de `hunter-auth` | `REPORT.md:71`, informe ampliado:350 y `results/hunter-auth.json#/units/0/unresolved/2` | Una búsqueda sin excluir `.local` pudo leer archivos; generó una salida temporal. El autor declara no haber abierto/usado esa salida. | No identifica el material leído ni prueba que fuese sólo un nombre de archivo. Las referencias actuales al temporal no existen. |
| Búsqueda de `hunter-authz` | `REPORT.md:72` y `results/hunter-authz.json#/hardening/5` | El autor declara que se mostró contenido de archivos `.local` en su contexto y que no lo usó para sus hallazgos. | No identifica archivo, tipo de material, valor autenticador o consumidor. No es correcto convertir esta declaración en «sólo rutas». |
| Listado inicial | Informe ampliado:352 y notas de alcance | El listado contenía nombres de archivos, sin contenido. | No explica ni cancela la lectura de los otros dos canales. |

Las afirmaciones absolutas «`.local` no fue leída» que quedan en las secciones de alcance se contradicen con las notas de incidente del mismo informe. Se conserva el original; su contradicción ya no se usa como prueba exculpatoria.

## Comprobaciones nuevas y límites

1. Los SHA256 de `run-metadata.json`, `coverage-ledger.json` y `findings.json` coinciden con los recogidos en F-01.02. Los originales no cambiaron. Los directorios `artifacts`/`scratch` de los cinco agentes no conservan archivos.
2. Se procesaron localmente los informes Markdown y JSON del run para extraer referencias y narrativas con redacción previa. No se publican literales de código, contraseñas, tokens o salidas completas. Las tres referencias al temporal de `hunter-auth` —dos informes y el resultado primario— apuntan a un archivo hoy ausente; no son tres exposiciones distintas.
3. **Gitleaks 8.30.1 fijado**, sólo sobre la carpeta aportada `run-1`, con redacción100, reglas oficiales, sin permitir comentarios de exclusión y captura privada: salida0, cero hallazgos. Esto permite decir que ese detector no identificó material en los informes conservados. **No demuestra que el temporal ausente o el contexto de `hunter-authz` no contuvieran secretos**, ni cubre por sí solo todas las contraseñas posibles.
4. Con autorización acotada del coordinador se buscaron los dos identificadores exactos derivados del temporal/tarea, no términos genéricos. Alcance: archivos del proyecto RackClick, eventos de herramientas fechados25.10.2026 y sus pares de llamada/resultado. Se enumeraron43 archivos,40 con eventos del día,6.583 eventos; **cero coincidencias y cero pares recuperados**. No se examinaron mensajes libres, otros proyectos, perfiles de credenciales ni todas las conversaciones. No se deduce inexistencia del acceso.
5. Se contrastó `development/server/tests/pg_support.py:285–302`: cerrar el laboratorio detiene sus procesos propios; no revoca los roles o elimina las claves persistidas. Por ello «laboratorio detenido», «VM apagada» o «la fecha es antigua» no sirven como prueba de revocación. No se abrió un clúster ni se probó autenticación.

## Qué dato falta realmente y cómo tratarlo

La vía que permitiría completar técnicamente F-01.02 sin adivinar es obtener **una fuente local del resultado de herramienta implicado**, no una contraseña por chat:

- copia o recuperación legítima del temporal referenciado por `hunter-auth`, o su resultado de herramienta correspondiente;
- fragmento de herramienta de `hunter-authz` que mostró `.local`, con su ruta/referencia de archivo y contexto del campo;
- si aparece material autenticador, tipo y consumidor por referencia, y un recibo de retirada/revocación previo o tratamiento coordinado y verificación posterior en ese consumidor.

El análisis de ese material debe hacerse localmente con captura privada y salida saneada. Puede acabar demostrando que se mostraron datos no autenticadores; en ese caso se documentaría esa resolución sin rotación. Si identifica un secreto de laboratorio, se trata **ese consumidor identificado**, sin extenderlo automáticamente a D, al equipo anfitrión o a GitHub. Si identifica algo de D, se plantea el tratamiento concreto para coordinarlo respetando su conservación.

Con lo disponible no es posible seleccionar de forma fundada una contraseña, clave MFA, rol PostgreSQL o token para renovarlo. Renovar «todo lo que pueda existir» trasladaría una incertidumbre a cambios ajenos e innecesarios y seguiría sin demostrar que se trató el material implicado. Tampoco sería correcto marcar el punto como completo sólo porque no se encontraron secretos en los informes que quedaron.

Si el registro no puede recuperarse, el titular puede decidir expresamente el tratamiento de la incertidumbre y su alcance. **Esa decisión no está tomada aquí y no equivale a una prueba de revocación.** Cualquier conciliación del criterio de cierre tendría que ser explícita, manteniendo la historia y los pesos, antes de acreditar. No se presenta una decisión de riesgo como una corrección técnica ya realizada.

## Dictamen para el coordinador

Se ha resuelto la ambigüedad de *dónde está el hueco de evidencia*: no se trata de los92 hallazgos históricos ya clasificados, sino de dos canales de salida distintos cuyos contenidos no están retenidos en las fuentes disponibles; el listado de nombres es un tercer canal separado y no incriminatorio por sí solo.

**No hay fundamento nuevo para dar por cumplidos F-01.02/F-01.04 con el criterio actual.** El impedimento restante es externo a una corrección de código: recuperar o disponer el antecedente con evidencia suficiente. No se solicita otra respuesta «No lo sé», no se acepta el riesgo por Wascar y no se impone una operación sobre D. La integración SQL independiente puede seguir mientras se obtiene esa fuente.

[Evidencia nueva, saneada](../evidence/s1-20261102/cierre-bloqueantes-01-07/f01/RESULTADOS.md). La revisión independiente y la contabilidad corresponden al coordinador y a un revisor distinto; este borrador no los sustituye.
