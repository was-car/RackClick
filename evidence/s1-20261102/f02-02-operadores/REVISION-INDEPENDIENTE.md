# Revisión independiente · F-02.02

02.11.2026. Revisor `/root/f01_classification_review`, perfil de seguridad, distinto del implementador. Registro del dictamen devuelto, sin atribuirle ejecuciones del coordinador.

**Dictamen favorable parcial para desarrollo de F-02.02, sin crédito. No quedan hallazgos abiertos en la versión acotada.** New/Restore, secretos owner legados, ACL productiva, cuenta efectiva del backup y distribución continúan pendientes. Procede sólo pending → in_progress, crédito 0, índice 1849/168 = 11,01/100.

## Qué hizo realmente el revisor

- Inspección del helper SQL, Backup, Instance, ambos lanzadores, ficha/lector nativo, diagnóstico, tests, investigación, contrato y reportes públicos.
- **PS7.6.9, memoria:** reprodujo once alias retenidos antes; después comprobó cero de once. Sin archivos, DPAPI, credenciales, servicios o DB.
- **WinPS5.1.26100.9711, sustituto de descifrado:** antes, ocho campos aceptados y once normalizados rechazados. Tras corrección, acepta los dos conjuntos previstos en protegido, rechaza cada flag sensible true y rechaza once campos en legado. El intento previo de visor bajo PS7 se descartó por no tener control positivo válido; no cuenta como reproducción.
- Verificación de las doce huellas finales, los tres archivos C# previos intactos y 167 casos QA anteriores idénticos más QA-168 planificado.
- Lectura de los reportes: 27 PS, 5 interoperabilidad real, 94 acceso, 4 descriptor y regresiones 8+6+6; backup real de20filas/nuevo rol/perfil. **No ejecutó esas suites, compilaciones, backup/restore, PostgreSQL, DPAPI propio, pruebas de privilegios o ventana UI.**

## Hallazgos cerrados

**P2 alias:** .NET convierte once prefijos a ConnectionStrings. Ahora se eliminan de las claves recibidas y ambientales antes de construir el hijo. No se altera el entorno padre; protegido sigue sin fallback. [Fuente primaria fijada](https://github.com/dotnet/runtime/blob/v10.0.0/src/libraries/Microsoft.Extensions.Configuration.EnvironmentVariables/src/EnvironmentVariablesConfigurationProvider.cs).

**P2 visor:** acepta sólo ocho claves legadas o, en protegido, las once normalizadas con las tres opciones sensibles false. No se amplía legado ni se ignoran claves extra. El coordinador añadió el positivo completo con DPAPI real y los rechazos de flags; no se confunde con el test de codec.

**P3 precisión:** corregidos nombre del test que sólo probaba codec y la descripción que negaba DPAPI por mirar únicamente la ausencia de una llamada directa. La consulta local usa el adaptador acotado; las guardias de identidad/path/hash del visor siguen presentes.

## Huellas verificadas

| Archivo | SHA256 |
|---|---|
| HASHES-CODIGO.json | `a032820f3afdef81c574790e600d76fbd71aafb45d57dfad8077be8a0bc169e3` |
| RackClick.SqlSecrets.ps1 | `d30ed7b3af901b054746376b74ff978c18eefa9bc361eecd5161f4b05750562d` |
| Show-RackClickDatabaseAccess.ps1 | `74ae553cfa6164872a8235fb9a6337f70a33919ebb1a4b506874b60ca670e58a` |

El backup probado usa el mismo SID Windows de laboratorio y DPAPI CurrentUser requiere al principal correcto al provisionar/ejecutar. El almacén preparatorio no acredita propiedad SYSTEM y servicio readonly; no declarar una instalación cifrada completa por existir estos formatos. No cambiar el criterio ni mover esas condiciones a otro checkpoint para acreditarlo.

Sin ediciones, acceso a privados, credenciales, DB, VM o D por parte del revisor. Sin aceptación manual, publicación o cierre completo de F-02.
