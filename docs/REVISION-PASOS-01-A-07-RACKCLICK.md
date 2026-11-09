# Revisión de los pasos 1 al 7 de RackClick

02.11.2026 · Revisión de criterios, fuentes y evidencias. D se conserva. Esta revisión no instala, rota credenciales ni modifica el producto o la contabilidad.

**Conclusión: no se han cumplido completamente los siete pasos. Los pasos 1 y 3 están cerrados dentro de su alcance revisado; los pasos 2, 4, 5, 6 y 7 permanecen abiertos con trabajo concreto pendiente.** Una revisión favorable de una parte o una prueba de laboratorio no equivale a cerrar el requisito completo.

## Resultado por paso

| Paso | Lo pedido | Lo demostrado | Dictamen y qué falta |
|---|---|---|---|
| **1 · F-01.01** | Clasificar candidatos e indeterminados con trazabilidad y sin publicar valores. | Clasificación revisada de 92 hallazgos históricos: 80 digest, 3 identificadores y 9 narraciones. Los 90 metadatos working relacionados tienen corroboración versionada. Revisión independiente y crédito 5/8 registrados. | **Cumplido en ese conjunto histórico.** No demuestra limpieza de todo el repositorio actual, privados o historial completo. No se suman 92+90 como secretos distintos. |
| **2 · F-01.02** | Tratar una credencial real expuesta: atribuirla, coordinar revocación/rotación y verificar el resultado. | Disposición individual de los hallazgos clasificados que no son credenciales. Dos observaciones adicionales conservadas como desconocidas y posiblemente solapadas. | **Parcial.** Falta atribución y disposición verificable del antecedente de exposición: material/canal/instancia y tratamiento si corresponde. La respuesta «No lo sé» no resuelve ese antecedente ni autoriza rotar D. |
| **3 · F-01.03** | Registrar falsos positivos con criterios específicos, sin supresiones amplias ni reescribir historial. | Registro contextual de las ocurrencias revisadas, tres criterios concretos y vínculo a versión/uso/prueba. El escáner no importa el registro; sus cuatro controles conservan sus huellas. Revisión independiente y crédito 5/8 registrados. | **Cumplido en ese registro.** No es una allowlist ni permite descartar automáticamente una coincidencia nueva. Las observaciones abiertas del paso 2 no se clasificaron como falsos positivos. |
| **4 · F-01.04** | Contrastar el criterio de cierre y registrar revisión independiente. | Evaluación y revisión realizadas; ambas concluyen `closure_not_met`. Paquetes y controles contrastados dentro de sus límites. | **Revisión hecha; cierre no cumplido.** Depende de resolver el paso 2 y comprobar después el criterio completo de F-01. No corresponde acreditar un cierre sólo por haber escrito el dictamen. |
| **5 · F-02.01** | Protección SQL compatible con la cuenta e instancia reales, con lectura mínima y separación owner/migración/runtime. | Codec, lector y host opt-in en fuentes; pruebas Windows/DPAPI y PG con rol SQL restringido. El positivo usa identidad/confianza de laboratorio; la rama de confianza productiva se prueba por rechazo. | **Parcial.** Falta provisionamiento/ACL productivos y positivo bajo la cuenta efectiva del servicio, manteniendo separación de las identidades privilegiadas. |
| **6 · F-02.02** | Adaptar operadores, ficha, diagnóstico y backup sin filtrar claves ni depender de copiar un secreto del host anterior. | Adaptadores, perfil de backup protegido, entorno del hijo y ficha sin contraseñas probados. El paso 7 añade New/Restore protegido de laboratorio y corrige peticiones/temporales. | **Parcial.** Falta integración nativa completa, lector del nuevo manifiesto en Acceso privado, recibos, inventario/distribución y cuenta efectiva de backup con privilegios mínimos. |
| **7 · F-02.03** | Reanudación y Restore en destino nuevo con identidad/roles/claves nuevos, y errores ante material ausente/incorrecto. | Restore real de 20 filas en dos clústeres PG17.11 nuevos/esquema43, roles y contraseñas nuevos, dos reanudaciones del destino y negativos. Ocho casos finales pasan. | **Parcial en el entorno operativo.** Es el mismo principal Windows y se reanuda el clúster, no un servicio Windows/host HTTP protegido. Falta candidata compatible y ensayo con actores efectivos en otro destino Windows/SID. |

Los criterios literales y los estados se contrastaron entre el ledger y los siete números del plan; no se cambiaron para que la revisión pasara.

## Bloqueos concretos de integración SQL

La revisión independiente de los pasos 5–7 confirma estos límites en las fuentes actuales:

1. **Aplicación y paquete todavía no forman una entrega SQL protegida completa.** El código C# SQL del paso 5 existe en fuentes; la DLL43 histórica usada por el paso 7 sirve a sus CLI de bootstrap/recuperación y no contiene ese código nuevo. Tener esquema43 no prueba que ese host arranque con el descriptor SQL protegido.
2. **El circuito nativo sigue usando la rama legada.** `New-RackClickPrivateDeployment.ps1` y `Restore-RackClickPrivateDeployment.ps1` no transmiten `ProtectSqlCredentials`. Los inventarios de operadores siguen con 25 archivos y no transportan `RackClick.SqlSecrets.ps1`. No se debe activar el flag en una entrega incompleta.
3. **Acceso privado no admite todavía la instancia v2 completa.** `Read-RcDatabaseAccessManifest` exige manifiesto1 y los cinco nombres antiguos. Su adaptador de `runtime.json` v2 se probó sobre una instancia híbrida con manifiesto1, no con el manifiesto2 de seis archivos del paso 7. Un foco nuevo en memoria confirma el rechazo; no se abrió ninguna ventana ni credencial.
4. **Falta separación operativa de actores.** El runtime ya no descifra owner/cluster al validar metadata, pero aún hay que provisionar y comprobar sus ACL, el servicio estándar y la cuenta de backup con privilegios mínimos. DPAPI CurrentUser del provisionador no es automáticamente el del servicio; copiar el archivo o entregar owner al runtime no resuelve esa separación.

Son pendientes reales de F-02, no nuevas tareas con peso ni pruebas de que D esté averiada. La entrega11 y su funcionamiento existente se conservan.

El contrato de operadores del paso6 conserva descripciones de su estado histórico (cinco archivos, antes del opt-in del paso7). Antes de empaquetar habrá que consolidar el procedimiento operativo vigente; no leer ese documento aislado como una descripción completa de las fuentes actuales ni reescribir los sellos históricos para actualizarlo.

## Qué se comprobó ahora

- **143 entradas selladas de las siete carpetas históricas de evidencia coinciden**, sin alteraciones ni archivos ausentes en esos conjuntos. Las entradas de documentos compartidos que evolucionaron después se separan de la evidencia histórica; no se reescriben sus sellos para ocultar diferencias.
- C# SQL del paso5: 4/4 huellas actuales iguales. Paso6: 11/12 iguales; `RackClick.Instance.ps1` cambió en el paso7 y el enlace entre su snapshot previo y la versión final está contrastado. Paso7: 11/11 iguales. Las pruebas antiguas siguen siendo pruebas de esas versiones y alcances, no ejecuciones nuevas de hoy.
- Cuatro controles del escáner sin cambios. Se hicieron **14 comprobaciones nuevas en memoria** del vínculo contextual del registro: control válido, once cambios de contexto, campo ausente y campo extra. No se abrieron los registros privados ni se repitió Gitleaks.
- Los dos paquetes conservan los SHA256 fijados: Windows completo11 y cargador Demo50-02. Se compararon sus bytes; no se reanalizaron todos los binarios o ZIP anidados ni se instalaron.
- Los tres generadores pasan `--check`. Ledger, pesos, criterios, números, catálogo QA/guía y código de producto quedan vigilados sin cambios durante esta revisión. Las observaciones personales de Wascar no se leyeron ni escribieron.
- **Las referencias Git actuales tienen otra huella que la observada en el paso4.** Se registra sin atribuir causa ni afirmar reescritura o igualdad del historial actual. La clasificación aceptada sigue limitada a las versiones históricas referenciadas; no se convierte en certificación global del historial de hoy.

La revisión SQL la realizó un agente de seguridad distinto del implementador. Su informe distingue la inspección y el foco nuevo del visor de las ejecuciones históricas del coordinador. Aquí no se ejecutaron PG, servicios, GUI, autenticaciones, builds, instaladores o VM.

## Orden para terminar lo que falta

1. **Resolver el antecedente del paso2**, conservando el desconocimiento donde no haya prueba; si se identifica material efectivamente expuesto, atribuir y coordinar su tratamiento. Después repetir sólo el contraste final afectado del paso4. No volver a pedir valores por chat ni modificar D por conjetura.
2. **Cerrar la integración de los pasos5–6:** candidata con el C# SQL actual, formatos/lectores compatibles, propagación nativa New/Restore, recibos/inventario y distribución; provisionamiento de ACL y actores de servicio/backup con separación y privilegios mínimos.
3. **Completar el extremo operativo del paso7** en un destino independiente: servicio con su cuenta efectiva, backup bajo su actor, Restore con nuevas identidades/credenciales locales y reanudación. Reutilizar los ensayos de datos y negativos ya válidos; no repetirlos por inercia.
4. Revisar esa entrega completa de forma independiente antes de intentar acreditar F-02 o el paso8. No dar los pasos5–7 por cerrados únicamente por las pruebas de componentes.

## Estado y evidencias

No cambia ningún estado ni se añaden puntos. **Índice de cierre: 1849/168 = 11,01/100**, no porcentaje global nuevo. Dos de estos siete pasos están cerrados; cinco siguen abiertos. El plan conserva 53 resultados, 280 checkpoints, 25 acreditados y 268 números.

[Comprobaciones reproducibles de esta revisión](../evidence/s1-20261102/revision-pasos-01-07/COMPROBACIONES.json) · [Revisión SQL independiente](../evidence/s1-20261102/revision-pasos-01-07/REVISION-SQL-INDEPENDIENTE.md) · [Plan numerado](PLAN-PENDIENTES-NUMERADO.md).

Evidencias originales: [paso1](../evidence/s1-20261102/f01-01-clasificacion/RESULTADOS.md), [paso2](../evidence/s1-20261102/f01-02-tratamiento/RESULTADOS.md), [paso3](../evidence/s1-20261102/f01-03-registro/RESULTADOS.md), [paso4](../evidence/s1-20261102/f01-04-cierre/RESULTADOS.md), [paso5](../evidence/s1-20261102/f02-01-sql/RESULTADOS.md), [paso6](../evidence/s1-20261102/f02-02-operadores/RESULTADOS.md), [paso7](../evidence/s1-20261102/f02-03-restauracion/RESULTADOS.md).
