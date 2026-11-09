# Paso 5 · F-02.01 · conexión SQL cifrada

02.11.2026. Coordinador: Codex. Encargo: conservar D, reutilizar evidencia y continuar F-02.01. **Implementación en fuentes y pruebas de laboratorio terminadas; resultado parcial, no acreditado.** Falta el extremo literal de compatibilidad positiva con la cuenta/instancia real del servicio y el provisionamiento de la ruta cifrada. La candidata 11 y D no cambian.

## Reutilización y cambio concreto

Se contrastaron primero el ledger/registro maestro, C.6, recuperación Windows y fuentes actuales. La conexión runtime sigue en texto plano en el circuito instalado: la protección MFA/TLS no la cifra. [Investigación y decisión previa](INVESTIGACION-PREVIA.md), con fuentes Microsoft/Npgsql y alternativas descartadas. No se añadió dependencia, versión, migración o biblioteca de cifrado.

- `WindowsSqlSecret.cs`, nuevo: codec DPAPI LocalMachine en memoria, con formato acotado y vínculo de propósito/instalación/SID/base/usuario. Rechaza identidades SQL distintas, contraseña ausente y passfile; normaliza opciones de Npgsql para no devolver información sensible.
- `SqlSecretConnection.cs`, nuevo: selección explícita del modo y lectura del archivo fijo; deriva el SID del host y fija confianza productiva SYSTEM/Administradores. Reutiliza sin editar el lector aprobado de MFA para ACL, identidad, ruta y lectura retenida. No escribe/repara/regenera.
- `Program.cs`: dos cambios acotados, guardia para mantenimiento y selección de la conexión antes de Npgsql/listener. Con `SqlSecret:Enabled=true`, la conexión en claro se rechaza y no es fallback. Bootstrap/migración/recuperación/política local mantienen identidad independiente; inicialización MFA sin SQL conserva su ruta. [Diff exacto](DIFF-Program.diff), contra copia previa del árbol compartido.
- `SqlSecretConnectionTests.cs`, nuevo: pruebas Windows/DPAPI/ACL, procesos de arranque y conexión a PostgreSQL con rol runtime. No se cambiaron pruebas previas, interfaces MFA, lector/proveedor MFA, csproj o locks.

[Contrato](../../../docs/CONTRATO-CONEXION-SQL-CIFRADA-v1.md) · [Ficha para Wascar](../../../docs/PASO-005-CONEXION-SQL-CIFRADA.md). Hashes finales en [HASHES-CODIGO.json](HASHES-CODIGO.json).

## Pruebas ejecutadas por el coordinador

Windows del anfitrión, SDK fijado **10.0.401**, configuración Debug, PostgreSQL **17.11** nuevo mediante `pg_support.Lab`, con base/owner/runtime/contraseñas sintéticos nuevos en cada ejecución. No VM ni servicio instalado. Contraseñas, salidas completas, TRX y binlogs quedan exclusivamente en `.local/f02-01-sql` y `.local/labs`; el directorio privado de este lote queda restringido al operador y SYSTEM. No se versionan.

Compilación de `tests/RackClick.Quality.Tests/RackClick.Quality.Tests.csproj --no-restore`, con binlog privado de nombre único en cada invocación. Resultado final: **0 errores y 0 advertencias**. Sin restore, publish o empaquetado. [Resumen](BUILD.json).

```
C:/Python312/python.exe -X utf8 -B evidence/s1-20261102/f02-01-sql/ejecutar-focos.py focal-final "FullyQualifiedName~SqlSecretConnectionTests"
C:/Python312/python.exe -X utf8 -B evidence/s1-20261102/f02-01-sql/ejecutar-focos.py regresion-final "FullyQualifiedName~SqlSecretConnectionTests|FullyQualifiedName~MfaWindowsHost|FullyQualifiedName~MfaKeyStoreInitCommandTests|FullyQualifiedName~MfaHttpTests|FullyQualifiedName~MfaPolicyRequireAllCommandTests"
```

- **39/39 nuevas PASS**, sin omitidas: round-trip real DPAPI; otro UUID/SID/base/usuario y blob alterado rechazados; formato/tamaño/cabecera; contraseña Unicode y parámetros inválidos; modo explícito sin downgrade; conexión en claro conflictiva; lectura sin mutación del archivo/DACL; ACL de lectura a terceros o escritura al lector rechazadas; ausencia/corrupción/bloqueo/ruta inválida sin regeneración; propietario de laboratorio rechazado por confianza productiva; cuatro CLI de mantenimiento y procesos de arranque con rechazo sanitizado. [Resultado focal](PRUEBAS-focal-final.json).
- **SQL real**: conexión descifrada con rol de ejecución distinto de owner/administrador, consulta de atributos sin superusuario/CREATEDB/CREATEROLE/BYPASSRLS, SELECT permitido y CREATE TABLE rechazado con SQLSTATE 42501. Esto prueba permisos del rol de laboratorio, no el token Windows de un servicio instalado.
- **132/132 PASS** en una regresión afectada final, sin fallos ni omitidas: incluye las 39 nuevas y 93 existentes de host/enrolamiento/MFA/CLI. No sumar las dos ejecuciones como 171 pruebas diferentes. [Resultado](PRUEBAS-regresion-final.json). No se repitió el resto de inventario/catálogo, suites criptográficas invariantes, instalación o carga Demo50.

Los procesos negativos devuelven exit 1 y sólo el código esperado, sin salida de listener/DB o pila del componente. No son ensayos positivos de toda la configuración cifrada con identidad productiva.

## Incidencias y corrección antes de estabilizar

El primer build falló en la prueba nueva: `FileSecurity.Sddl` es una adaptación de PowerShell, no propiedad de esa API .NET. Se corrigió a `GetSecurityDescriptorSddlForm`; no se modificó producto por ese error. Tras ello, 38/38 pruebas iniciales pasaron.

Se añadió el borde de una contraseña con sustituto UTF-16 sin pareja. La referencia inicial del codec dejaba escapar `EncoderFallbackException`; el negativo falló antes de corregir. El revisor lo identificó también por lectura. Ahora se devuelve `sql_secret_connection_invalid`, sin excepción interna; pasa dentro de las 39 finales. [Rojo saneado](NEGATIVO-UNICODE.json), [diff](DIFF-Unicode.diff) y fuente previa conservados. La salida original está privada. No se hizo otra mutación ni se presenta como ensayo de memoria borrada.

## Límites y continuación

- **La lectura positiva usa un SID de grupo Usuarios y confianza de laboratorio**, mediante seam interno, no el SID efectivo de RackClick. La rama productiva tiene confianza fija y sólo se ejercita su rechazo al propietario de laboratorio. El positivo bajo servicio estándar/instancia nueva sigue pendiente en el propio F-02.01; no se transfiere su criterio silenciosamente a otro paso.
- Sólo lectura integrada en el host y sellado en memoria. Los operadores actuales todavía escriben/leen sus archivos SQL legados; `runtime.json`, lanzadores, fichas, backup y otras credenciales SQL requieren adaptación en F-02.02. No habilitar la opción en D ni afirmar que sus secretos o los del ZIP11 estén ya cifrados.
- DPAPI está ligado a la máquina y la ACL es esencial. No es defensa frente a administradores/SYSTEM, captura de memoria o un host comprometido. No se ha probado portabilidad ni se ofrece copiar el blob a otra VM: el destino debe crear credenciales y material local nuevos.
- El string usado por Npgsql no puede ponerse a cero de forma garantizada; se borran las copias byte/nativas propias. No hay ensayo forense de memoria. Se conservan los límites del lector aprobado sobre carpetas/ancestros/acceso efectivo.
- No publicación de archivos cifrados por un nuevo escritor, ampliación del instalador, arranque de servicio real, Restore de otro host, reinicio Windows o aceptación manual. Esos circuitos siguen pendientes; no son fallos nuevos de D.

**Contabilidad propuesta y revisada:** sólo F-02.01 pending → in_progress, crédito 0. Índice exacto **1849/168**, **11,01/100**, sin incremento; F-02.02/.03/.04 siguen pending. F-01 y todos los demás resultados/criterios/pesos y números se conservan. No es porcentaje global nuevo ni cierre completo del cifrado SQL.

## Preservación y registro

Sin acceso a D/otras VM, cuentas, SCM, bases existentes, contraseñas reales, MFA instalado o transcripciones. Sin cambios en aplicación frontend, esquema, catálogo, paquetes, QA/resultados de Wascar, commits o publicación. [Preservación](PRESERVACION.json). Los clústeres de laboratorio propios quedaron detenidos por su contexto; no se borran sus evidencias privadas.

Revisión separada en [REVISION-INDEPENDIENTE.md](REVISION-INDEPENDIENTE.md). Ledger/contexto/ficha/CHANGELOG/continuidad se actualizan con el resultado parcial. Los tres generadores de planificación se regeneran secuencialmente y verifican con `--check`; contabilidad e identidades estables quedan en ESTADO.json y VERIFICACION-CIERRE.json. Sello final SHA256SUMS.txt después de terminar todos los archivos; no se reescriben sellos históricos.
