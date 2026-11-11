# Paso 13 · F-04.04 · cierre técnico del proveedor Windows

03.11.2026. **Cerrado técnicamente con revisión independiente favorable.** El criterio original de F-04 queda cubierto. Este lote no modifica producto, no compila ni ejecuta nuevas pruebas de aplicación, no opera VM/servicios/cuentas/DB y no abre claves ni credenciales. D y E permanecen sin operaciones.

## Qué se hizo y por qué

Se reutilizó primero la evidencia de los tres subpasos cerrados. La [investigación y decisión](INVESTIGACION-Y-DECISION.md) descarta crear otro proveedor o repetir las suites por existir un nuevo paso documental. La [matriz](MATRIZ-CIERRE.md) relaciona cada obligación literal con su prueba y sus límites. Conserva el estado de propuesta con que fue revisada; el [dictamen final](review/DICTAMEN-F0404.md) resuelve su última fila y autoriza el cierre técnico, no una adopción de la entrega.

- **F-04.01:** writer actual con descriptor protegido desde creación y publicación completa/preservación posterior, regresión195 y revisión independiente. El escritor corregido no se presenta como instalado en D.
- **F-04.02:** dos tokens reales de servicios de E,504 aperturas correctas; sólo lecturas propias/comunes, sin acceso ajeno/management o derechos de modificación. Padres/herencia/reparse e invariancia contrastados; tarea temporal retirada. No se vuelve a ejecutar la sonda.
- **F-04.03:** proveedor Windows real con lectura/descifrado y verificación de factores en C10/D11, incluido nuevo login y evidencia posterior al reinicio.39 resultados históricos del host cubren fallos cerrados sin regeneración/sesión alternativa. El intentoB parcial se conserva como parcial.

El resultado no suma esos contadores como pruebas nuevas ni atribuye al revisor ejecuciones que hizo otro operador. Se preserva la observación favorable de Wascar sobre su MFA administrativo, sin rellenar sus demás resultados QA.

## Correspondencia de fuentes

`CONCILIAR-EVIDENCIA.py` ejecutado con Python3.12, salida0:99 referencias por hash y los sellos anteriores de30/54entradas correctos **antes de actualizar los planes**. Se guardaron las tres configuraciones iniciales y las copias de los documentos que cambian en esta tanda. `SALIDA-VERIFICACION.json` conserva la segunda verificación de referencias inmutables, también correcta.

Composición Windows, proveedor, lector, anillo y dos archivos de pruebas conservan identidad respecto a F-04.03. `CONTRASTE-NUCLEO.json` añade cuatro fuentes del núcleo de autenticación/enrolamiento/cifrado idénticas a la copia usada por C10. El writer coincide con la revisión del paso11.

Program completo sí cambió: SQL protegido, recorrido de recuperación por código y mapping de exportaciónJSON. El [diff](DIFF-PROGRAM-DESDE-C10.diff) lo explicita; el segmento de composición/resolución MFA es idéntico y el archivo actual coincide con el manifiesto45. **No se afirma identidad de toda la DLL actual con la de C10** ni se acredita por esta comparación la recuperación/exportación completa.

Los sellos anteriores no se reescriben. Algunos enumeran planes vivos: después de su regeneración, una diferencia en esos documentos es esperada y se contrasta con las copias iniciales y la conciliación del nuevo lote. Eso no transforma una evidencia antigua en una prueba recién ejecutada. Las fuentes y recibos inmutables conservan sus hashes.

## Revisión independiente

Agente `rackclick_security`, distinto de los implementadores, emitió [dictamen favorable](review/DICTAMEN-F0404.md). Su [verificador](review/Verify-F0404-References.py) terminó en0 y su [comprobación](review/COMPROBACION-F0404.json) registra las99referencias, cuatro núcleos y correspondencia de componentes. Cero nuevas pruebas de producto, operacionesVM, acceso a DB/binlogs/credenciales privados o cambios del ledger por el revisor.

La revisión acepta la evidencia compuesta del criterio técnico. Definición, implementación en fuentes, pruebas del alcance y revisión quedan cumplidas; **integración en una candidata completa y aceptación final permanecen pendientes**. No se exige tocar D para cerrar este criterio ni se declara terminado todo el proyecto.

## Contabilidad y continuidad

Sólo **F-04.04** recibe **5/8 =0,625 puntos**:2689/168→1397/84 =**16,63/100 del cierre restante**.36checkpoints cerrados y244sin cierre (242pending,2in_progress);53resultados/280checkpoints/268números, criterios, pesos y huella congelada intactos. F-04 completa sus cuatro checkpoints técnicos. No es un nuevo porcentaje global del producto ni aceptación de producción.

Ledger, contexto maestro, plan numerado, progreso y changelog se concilian; los tres generadores documentales se regeneran y comprueban. `VERIFICACION-CIERRE.json` registra el cambio exclusivo; el escaneo de selección y el sello final se conservan junto a esta evidencia. No hay cambio visible de aplicación o disponibilidad QA que requiera alterar casos/resultados de Wascar. Sin commits ni push.

Siguiente: **14/F-05.01**, contrastar el sobre RCKEY existente antes de implementar. Permanecen en sus pasos propios la recuperación portable, rotación/coherencia disco-DB, códigos/emergencia, candidata Windows completa, New/Restore/backups con MFA y aceptación final. Gracia45/exención y custodia confirmada intactas. Los límites de D2 frente a SYSTEM/administrador/proceso comprometido y la durabilidad ante cortes siguen explícitos.
