# F-06.02 · inventario y guarda de retención

09.11.2026 · Componentes implementados/probados/revisados; **F-06.02 en progreso,0crédito**. Wascar pide paso20, conservar D y reutilizar evidencia antes de implementar.

## Reutilización y diseño

Se parte del protocolo19 revisado y las piezas anillo/RCKEY/RCKPAY. El sobre ya conserva una versión por clave dentro de su contenido autenticado. El manifiesto SQL histórico es de ocho campos cerrados y dos archivos; añadirle campos/archivos rompería el lector. Se crea un inventario lateral enlazado, sin modificar esos formatos ni dependencias. Investigación y fuentes: INVESTIGACION-PREVIA.json y docs/CONTRATO-INVENTARIO-RETENCION-MFA-v1.md, escrito antes de implementar.

Fuentes nuevas: MfaKeyRetention.cs y MfaFactorKeyInventoryReader.cs; sus dos clases de prueba y runnerPG. No se modifican fuentes previas, Program, proveedor, writer, SQL, locks o csproj. Los modelos/códigos son internos, sin endpoint o comando nuevo. Inventarios y decisiones son metadatos, no autorización de borrado.

## Ejecuciones reales

- Implementador separado:51casos de inventario/guarda/JSON/sobre real sintético PASS, sin omitidas. Stub rojo de orden/copias, mutación de requiredVersions detectada por dos negativos y tres rojos Unicode antes de su corrección. Detalle e intentos: IMPLEMENTACION-INVENTARIO.md. El primer positivo falló por fixtureC#CS8752; otro intento usó incrementalmente una DLL mutada por conservar mtime. Ambos quedan declarados y fueron sustituidos por ejecución final recompilada con fuente restaurada.
- Coordinador: primer build del lector falló por xUnit1051, porque faltaban tokens de cancelación en llamadas de sus fixtures; no era fase roja de comportamiento. Corregidos sólo esos fixtures. Rojo válido contra stub vacío en copia aislada:10casos realesPG,2PASS/8FAIL por recuentos y rechazos ausentes.
- Lector final:10/10PASS con PostgreSQL17.11, tres DB nuevas de esquema45 y roles nuevos sólo SELECT. Casos: todos los estados, censo vacío, permisos/invariancia, aislamiento, transacción de otra conexión, cancelación, versión SQL fuera del perfil e inventario separado contra backup real. No se lee ciphertext en el lector; la fixture utiliza bytes opacos sintéticos y el testigo SQL de invariancia se calcula en la DB.
- Dump custom real del laboratorio sin escritores: inventario lateral fuera de la carpeta backup, ligado a su manifiesto/dump y a un sobre autenticado sintético en memoria. Read-BackupManifest nativo pasa antes/después, rechaza con backup_files_invalid un tercer archivo propio de prueba y vuelve a pasar al retirarlo. Filas de factores iguales en testigos frescos antes/después. Rojo y verde usaron clústeres distintos, ambos detenidos; no se reusó D/E o una base instalada.

La regresión de piezas reutilizadas pasó una vez sobre los binarios finales del coordinador: **115/115**, incluyendo51nuevos y64de anillo/payload/sobre, sin omitidas. Contadores exactos en REGRESION-COMPONENTES.json. BuildRelease/SDK10.0.401, binlogs privados únicos. No se atribuyen al implementador los ensayos PG/nativos del coordinador, ni a esta tanda los ensayos previos F04/F05.

Revisor independiente de seguridad: ejecutó sus51casos por DLL directa y contrastó código/fuentes/binarios; no se le atribuyen los10PG o115de regresión del coordinador. [Dictamen](review/DICTAMEN-F0602.md): componentes sin defectos nuevos observados, pero alcance insuficiente para cerrar el criterio operativo completo. Faltan caller nativo, catálogo confiable y publicación/consumo/retirada coordinados. La evidencia de factores con bytes opacos y dump quieto no demuestra descifrado, snapshot concurrente, custodia externa o retirada real.

## Frontera operativa y crédito pendiente

No se ejecutó una retirada real. CandidateUnreferenced no autoriza borrar archivos, no bloquea escritores y no demuestra autenticidad/vigencia del censo o dump. Un catálogo completo se exige expresamente, pero su registro confiable y su coordinación con DB/anillo están pendientes. La conexión se vincula a la instalación por el futuro coordinador; el GUID suministrado no prueba ese vínculo. Inventario lateral y sobre se prueban como componentes; no están publicados por el operador nativo o instalador.

F-06.03 mantiene coordinador/testigo/fence/guard/publicador y caídas, F-06.04 el cierre integrado. Se acepta la recomendación estricta: sólo F-06.02 pasa de pending a **in_progress**, sin reescribir su texto/peso y sin cerrar hitos de F06. **0puntos nuevos**,3319/168=19,76/100 del cierre restante;42done/235pending/3in_progress,53resultados/280checkpoints/268números. D/E, sus datos y MFA intactos; sin commits, push, publicación, servicios o cuentas Windows. No hay porcentaje global nuevo.

El runnerPG es un arnés externo ejecutado desde el workspace y fijado por SHA; no se presenta como contenido de las DLL ni como archivo ejecutado desde freeze. Las cuatro fuentes/pruebas C# sí coinciden exactamente con freeze. Ambos laboratorios propios se conservaron detenidos, con credenciales/logs/dumps privados fuera de la evidencia pública.
