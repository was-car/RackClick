# Revisión de los pasos 8 al 18 de RackClick

03.11.2026 · Revisión del coordinador y dos revisores independientes. D y E se conservan sin operaciones.

**Los once pasos tienen respaldo para los criterios documentales o técnicos que se acreditaron. Esto no equivale a que todos esos módulos estén entregados y aceptados en un instalador completo.** Los pasos 9 y 10 cierran especificaciones; los demás cierran criterios técnicos, con los límites que se detallan abajo. No se encontró un bloqueante nuevo que justifique retirar sus créditos.

## Resultado uno por uno

| Paso | ID | Qué se contrastó | Dictamen y límite |
|---|---|---|---|
| 8 | F-02.04 | Protección del secreto SQL; servicio estándar, postboot de edición13 y Restore14-r2 en E; roles/material nuevos, datos SQL/API y reanudación sin regeneración; revisión del conjunto F-02 | **Cumple el cierre técnico.** No acredita un reinicio posterior al Restore14 ni New/Restore de cualquier versión futura |
| 9 | F-03.02 | Condiciones D2: recuperación restringida, límites/KDF/AAD y fases recuperables disco–DB; correspondencia con las decisiones confirmadas | **Cumple como especificación.** Se aclaró mediante adenda la ruta efectiva del almacén. Documentar las fases no implementa el coordinador |
| 10 | F-03.03 | Límites explícitos de DPAPI LocalMachine y custodia: administrador/SYSTEM o proceso de servicio comprometido no quedan aislados por este mecanismo | **Cumple documentalmente.** No promete protección contra esos actores ni sustituye permisos efectivos |
| 11 | F-04.01 | Escritor aprobado actual, descriptor seguro desde la creación, publicación inicial, fallo posterior y conservación de objetos ajenos; resultados y revisión independiente | **Cumple técnicamente en fuentes.** La incorporación del escritor corregido a una candidata completa conserva su hito pendiente |
| 12 | F-04.02 | Recibos originales de dos cuentas estándar reales en E y matriz de 504 aperturas: 16 lecturas permitidas, 44 lecturas ajenas/management y 444 derechos de modificación denegados; padres/herencia/reparse e invariancia | **Cumple el criterio de permisos efectivos.** No se deduce sólo del texto de una ACL ni se amplió management |
| 13 | F-04.04 | Conjunto F-04: creación, uso real del proveedor, descifrado/verificación ya acreditados en F-04.03 y permisos efectivos; fuentes y revisiones enlazadas | **Cumple el cierre técnico del proveedor.** Candidata completa actualizada y aceptación final siguen pendientes |
| 14 | F-05.01 | Codec RCKEY existente, perfil/cabecera/tamaños/UTF8 previos al KDF, AAD completa y contenido portable | **Cumple técnicamente.** Canonicalidad binaria y de serialización de salida; no se afirma que el parser rechace todo JSON equivalente |
| 15 | F-05.02 | Seis duraciones originales de Windows para una apertura con una derivación: 57–62 ms, mediana 59,5 ms; decisión expresa de conservar 600.000 iteraciones | **Cumple la medición y decisión exigidas.** Son casos completos xUnit/Debug, no un microbenchmark PBKDF2, una medida de D ni una garantía universal de rendimiento |
| 16 | F-05.03 | Negativos originales de contraseña, alteración, truncado, bytes extra, versiones/algoritmos y coste/tamaño; aserciones y hashes actuales | **Cumple las categorías exigidas.** No se convierten en un fuzzing exhaustivo ni se suman pruebas solapadas como funciones distintas |
| 17 | F-05.04 | Recuperación portable real LEAO→Windows Server E, dos factores y versiones 1 retirada/7 activa, AAD conservada, adaptación explícita, token estándar real y limpieza comprobada | **Cumple como portabilidad offline real.** No restauró una DB de aplicación en E ni adoptó el material en su instalación |
| 18 | F-05.05 | Dump/restore PostgreSQL17.11 de DB de aplicación45, roles restringidos, datos/factores conservados, revocación real de sesiones/desafíos y login TOTP/API/CSRF con Program y proveedor Windows reales; corrida final 8/8 | **Cumple como integración técnica de componentes en laboratorio.** HTTP usa TestServer; las comprobaciones previas de material/versiones/AAD pertenecen al fixture. No es todavía el recorrido de un operador o instalador |

Las cifras de pruebas son resultados históricos contrastados, no suites ejecutadas otra vez en esta revisión. Las ediciones13/14 del primer renglón son ediciones de entrega, no una afirmación de que la aplicación actual use esquema13/14.

## Qué falta realmente, aunque estos pasos estén cerrados

- **F-04:** integrar el escritor corregido en la candidata completa y comprobar/aceptar esa entrega. El cierre de sus checkpoints técnicos no declara esos hitos terminados.
- **F-05:** convertir los componentes probados en un recorrido operativo de exportación/recuperación. `New-RackClickRecoveredInstance.ps1` mantiene la guardia `recovery_mfa_envelope_required` cuando hay factores: el instalador no obtiene esta capacidad por haber pasado el paso18. Sus hitos de definición operativa, implementación, candidata integrada y aceptación permanecen pendientes.
- **F-06/F-09/R-04 y Windows:** coordinador, exclusión/fence/journal/marcador DB y conciliación; cortes y commit incierto; emergencia, conservación/rotación de versiones y recuperación completa, servicio/HTTPS/reinicio cuando corresponda. Son obligaciones ya registradas, no puntos nuevos creados por esta auditoría.
- **Rutas largas:** el primer intento de18 encontró un staging de 266 caracteres rechazado con Win32206. El fixture final usa una ruta menor y pasa; no se corrigió ni demostró soporte general de rutas largas en el producto. Debe delimitarse o probarse al integrar el operador.

Por tanto, puede continuarse con el paso19 sin repetir codecs, permisos ni pruebas invariantes. No sería correcto anunciar «recuperación MFA completa por instalador» o «producto listo» basándose en estos once cierres.

## Precisión documental corregida durante la revisión

El apartado1 de D2 mostraba una ruta abreviada que omitía el aislamiento `security`. Se conservó íntegra la versión anterior y se añadió una [adenda al documento](D2-CONDICIONES-TECNICAS-F03-02.md). El componente usa `<InstancesRoot>\<installationId>\mfa-keys`; el perfil nativo actual fija la raíz en `C:\ProgramData\RackClick\Instances\<installationId>\security`. La ruta efectiva incluye de nuevo el identificador bajo esa raíz. No se movieron archivos, no se regeneraron claves y no se cambiaron permisos ni decisiones de custodia.

El contraste de8 también identifica que `RackClick.Instance.ps1` evolucionó después del ensayo nativo: conserva una referencia exacta del código ensayado y el diff posterior de compatibilidad43/45. No se presenta el ensayo histórico como ejecución nueva de todos los caminos actuales.

## Cómo se comprobó

- Criterios congelados, numeración estable, estados, evidencias y revisiones contrastados contra el ledger; los tres generadores pasan `--check`.
- Once sellos históricos: **524 referencias resueltas** por bytes actuales o copias históricas exactas. Una copia antigua demuestra conservación de aquella evidencia, no que todo el código actual se ejecutara entonces.
- Dos revisiones independientes separadas del coordinador: [pasos8–13](../evidence/s1-20261103/revision-pasos08-18/audit-08-13/DICTAMEN.md) y [pasos14–18](../evidence/s1-20261103/revision-pasos08-18/audit-14-18/DICTAMEN.md). Se revisaron fuentes/aserciones y recibos originales, además de recalcular hashes y matrices.
- **Cero operaciones en D/E, builds, suites de producto, PostgreSQL o servicios en esta auditoría.** No se abrieron credenciales, claves, sobres, dumps o binlogs privados. No hubo commits ni push. Sólo documentación y comprobadores de la auditoría.

[Evidencia reproducible y límites](../evidence/s1-20261103/revision-pasos08-18/RESULTADOS.md).

## Métrica

Se conserva **19,13/100 del índice de cierre restante**: exacto1607/84, 41 checkpoints cerrados, 237 pendientes y 2 en progreso. **Esta revisión añade 0 puntos**, mantiene pesos/criterios/baselinev3 y no estima un porcentaje global nuevo del producto. La aceptación final de Wascar sigue separada.
