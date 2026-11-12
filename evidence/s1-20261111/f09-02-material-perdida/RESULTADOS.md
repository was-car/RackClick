# F-09.02 · material nuevo y transición interna de pérdida MFA

11.11.2026. Cerrado técnicamente con dictamen independiente favorable sólo al alcance interno F-09.02. **D/E preservadas**, sin VM, servicios/cuentas Windows, instalaciones, commits o push. Los roles y cuentas app sintéticos se crearon exclusivamente en clusters PostgreSQL nuevos privados.

## Investigación y reutilización

[Plan previo](../../../docs/PLAN-F0902-MATERIAL-PERDIDA-MFA.md): contratos D2/F09, F06 y F08 revisados antes de cambiar código. Fuentes oficiales PostgreSQL17 sobre transacciones, bloqueos, schemas/permisos y RETURNING; componentes Windows/DPAPI/RCKEY y sus investigaciones anteriores reutilizados. Sin bibliotecas, extensiones o versiones nuevas.

Rotación requiere poder abrir todos los factores y no sirve como pérdida. Se implementa un protocolo propio sobre admission, lock/fence, archivos privados e identidades del almacén de mantenimiento; escritor/proveedor y sobre aprobados. No se relaja el lector ni se modifica el algoritmo criptográfico.

## Cambio acotado

Nuevos `MfaLossResetCoordinator`, `MfaLossResetDatabase`, parcial `WindowsMfaMaintenanceStore.Loss` y SQL047. Cambios mínimos en cuatro fuentes previas: lista explícita de migraciones/LatestVersion47, historia contigua conocida45–47 en mantenimiento, compatibilidad46/47 en rotación y visibilidad interna de la consulta nativa de autorización F0901. **224 de228 archivos previos de producto idénticos; cuatro nuevos; dos archivos nuevos de pruebas.** SQL001–046, Program, pruebas históricas, frontend y dependencias permanecen iguales a la referencia.

Prepare exige versiones perdidas explícitas y un censo fiable: ring, nombres de archivos, factores de todos los estados, historial y backups retenidos declarados. Elige una versión superior al máximo de ese conjunto, conserva claves legibles y rechaza descartar material aún disponible. Una dependencia de backup no declarada perdida y sin clave en el anillo detiene el proceso.

Antes de la mutación DB se crean archivo privado de originales opacos, plan/candidato y fence. Export devuelve el sobre sólo en memoria. Apply toma una copia propia acotada, comprueba hash y autenticidad contra el candidato y fija un pin privado inmutable del sobre, ligado al plan/material. El servidor no guarda ese sobre ni su contraseña.

Una transacción archiva **filas cifradas completas** en `rackclick_private`, retira sólo factores de versiones perdidas y fuerza required/pending/revisión sin cambiar cuenta, ámbito, permisos o gracia. Incluye revocaciones mínimas inseparables y witness de autoridad Windows, sin fingir un actor app. El runtime no tiene USAGE/lectura/DML sobre ese schema, incluso con los grants amplios antiguos de public. No se acredita todavía por ello F-09.03.

Publish exige binding completo de testigo, plan/material/sobre, conteos y fecha; revalida DB/archivo privado/objetos y publica clave nueva/ring. Comprueba la clave activa y abre factores restantes. Conserva blobs originales y **mantiene el fence**. Reentrada por UUID permite continuar tras interrupciones lógicas sin repetir revisiones. No emite recibo rotate ni libera el arranque. La fase final se llama `material_published_verified_fenced`, no recuperación del servicio completada.

Cada entrada productiva recaptura autoridad Windows y exige servicio vinculado parado antes de DB. Los positivos del laboratorio usan seam interno explícito y confianza de fixture; no un registro DI/config que permita habilitarlo. La CLI de F0901 **incluso si pasa la autorización sigue devolviendo transition_unavailable/exit1/cero operaciones**. El token estándar observado se rechaza antes, en autorización; no se declara un proceso elevado real.

## Pruebas del coordinador

Windows, SDK10.0.401 Release, PG17.11 nativo nuevo, roles owner/runtime separados, DPAPI y ACL reales con lector/SID de fixture. Logs/TRX/binlogs, credenciales y dumps quedan privados bajo `.local/`, sin sobres guardados.

| Ejecución | Resultado observado |
|---|---|
| Rojo inicial de componente ausente |9/9 fallan en selección de versión/capacidad; no se atribuye vulnerabilidad previa |
| Selector implementado |9/9 PASS |
| Rojo pertinente de revisión |Cuatro `No exception was thrown`: backup-only90 y alteración de SID, nueva versión y versiones perdidas. Corrida26:21PASS/5FAIL; el quinto era una expectativa de timezone del fixture |
| Corrección inicial |26/26 PASS |
| Negativo adicional de pin del sobre |1/1 FAIL antes del pin local inmutable, por `No exception was thrown`; después incluido en verde |
| Foco ampliado antes de última regresión |29/29 PASS sin omitidas |
| Mutación privada |No forzar required/pending:1FAIL, esperaba3 cuentas pendientes y encontraba0. Raíz de producto intacta |
| Build definitivo |Rebuild sin incremental,0errores/0advertencias; DLL del servidor restaurada por hash antes de ejecutar |
| Regresión definitiva |**144/144 PASS,0FAIL,0omitidas** sobre hashes finales:30propios (21 de componentes +9 de versión),76F0901,3HTTP,28SCM,4admission y3contratos de rotación |

Los30 propios incluyen todos los estados de factor, global/ordinario/cuenta inactiva, conservación de cliente/rack/equipo, clave legible restante, total de blobs ilegibles con metadata fiable y uno vacío, rollback SQL, cambios de usuario/política/códigos tras plan, reentrada tras commit o publicación interrumpidos lógicamente, sobre/candidato alterados, clave físicamente retirada en negativo, archivo/witness inaccesibles al runtime y rechazo del token nativo estándar. Un backup real se tomó cuando existía un factor90; después se retiró ese usuario del fixture. Declarar90 perdida conserva ese backup identificado y lleva a nueva versión91, sin presentarlo como recuperado. El mantenimiento/rotación anteriores se ensayan también sobre esquema47 sin convertirse en loss-reset.

Global y ordinario afectados reciben `enroll` sin sesión en autenticación de almacén. Los tres HTTP son la ausencia de emergencia remota y dos guardas históricas de API restringida, **no un servidor perdido recuperado por HTTP**. Los escenarios de corte son excepciones de checkpoint, no Kill, apagón o reinicio.

## Incidencias conservadas

Los borradores tuvieron errores de sintaxis/inferencia de tipos y dos pasadas fallidas por longitud de rutas del candidato. Se compactó su ruta y se añadió un límite antes de escribir archivos/fence, sin cambiar el escritor aprobado. Esas pasadas no acreditan los negativos de revisión: el caso de backup podía rechazar por la razón equivocada. La corrida pertinente posterior sí reproduce los cuatro por ausencia del rechazo esperado.

La comparación JSON de archivo completo esperaba timezone local y el archivo se generaba en UTC. Se fijó UTC en el fixture; no se modificaron ciphertext ni timestamps de producto por esa discrepancia. Una compilación de pruebas añadidas falló por un paréntesis extra; no se ejecutó binario viejo como verde.

Tras la mutación, una copia restauró fuente con timestamp anterior y el build incremental conservó la DLL mutada. La primera regresión dio143PASS/1FAIL, el mismo canario required/pending. **Ese intento no se presenta como verde ni defecto de la fuente restaurada.** Se reconstruyó con `--no-incremental`, se exigió el hash de la DLL anterior a mutación y sólo después se ejecutó la definitiva144/144. El código mutado nunca se copió a la raíz compartida.

## Pines, reproducción y límites

`FOCOS.json` fija todas las corridas, counters, nombres, hashes de TRX privado y DLL finales; `FUENTES.json` fija fuentes, referencias y pruebas previas conservadas; `CAMBIOS.patch` conserva el diff respecto de F0901. [Matriz](MATRIZ-CRITERIO.md) y [ficha30](../../../docs/PASO-030-MATERIAL-PERDIDA-MFA.md).

Comandos privados: `run.py red --restore --build`, `version --build`, focos de revisión y `verified --build --expected-server <hash> --filter <frontera afectada>`. El driver usa toolchain fijada, binlog único por invocación, nuevo Lab de pg_support, variables explícitas de fixture y cierre del cluster en finally. Las pruebas versionadas pueden repetirse con esas variables y dependencias oficiales ya preparadas; no hay fallback a una instalación real.

Sin anillo/censo fiables se detiene. No se prueba pérdida de carpeta completa, reconstrucción de namespace, token elevado/SYSTEM positivo, SID efectivo del servicio, custodia externa física o durabilidad universal DB/disco. Los backups afectados se conservan pero sus claves perdidas no aparecen por crear un sobre nuevo. Las rutas Win32 largas se rechazan. No instalador47, servicio recuperado, arranque loss-reset, liberación del fence o adopción de Wascar. F-09.03/.04/.05 y seis hitos completos siguen pendientes. Observación Edge F0805 intacta;175 casos QA y resultados personales conservados.


## Revisión y conciliación

[Dictamen independiente](review/DICTAMEN.md): ejecución propia y límites registrados por un revisor distinto. Sólo F-09.02 suma1/2:2111/84→2153/84=25,630952…/100 del cierre restante. Se conservan F0903–.05 y los seis hitos completos pendientes; no se declara operación instalada ni recuperación total aceptada.
