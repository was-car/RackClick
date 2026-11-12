# F-08.01 · generación propia y entrega única

11.11.2026. Cierre técnico con dictamen independiente favorable. D/E sin operaciones; sin VM, servicios, cuentas/bases instaladas, commits, push o despliegues.

## Reutilización e investigación

Generador, transacción, endpoints, panel y pruebas de punto 3 ya existen y conservan sus hashes. El registro numerado manda conciliarlos, no crear otro generador. Se reutilizan su revisión, Edge y contratos; se añade únicamente un test de dos generaciones iguales solapadas, porque el replay anterior era secuencial y la concurrencia de canje no demuestra concurrencia de entrega.

Fuentes oficiales consultadas el 11.11: [RandomNumberGenerator.GetBytes .NET 10](https://learn.microsoft.com/en-us/dotnet/api/system.security.cryptography.randomnumbergenerator.getbytes?view=net-10.0), [FixedTimeEquals .NET 10](https://learn.microsoft.com/en-us/dotnet/api/system.security.cryptography.cryptographicoperations.fixedtimeequals?view=net-10.0). Se conserva .NET/Npgsql directo y el formato revisado; no bibliotecas/dependencias/versiones nuevas.

## Qué demuestra la fuente

`NewCode` toma 16 bytes de CSPRNG y muestra 32 hexadecimales en ocho grupos; 128 bits proceden de esa construcción, no de una muestra de colisiones. Cada hash añade 16 bytes de sal independiente, dominio versionado y UUID de Systemhaus/usuario; se almacena `rck1$sal$hash`. La comparación usa igualdad constante para los hashes de longitud válida. No hay clave TOTP, semilla del autenticador o proveedor de claves en esa derivación.

La generación exige sesión MFA, contraseña actual, factor activo, revisión e identidad de operación. Su transacción sólo guarda hashes y metadatos seguros; los valores se devuelven después del commit y sólo en la primera respuesta. Los recibos y replays fuerzan codesAvailable=false/codes=null. Las rutas conservan Origin/CSRF/actor/no-store; el panel mantiene los valores sólo en memoria y su journal sólo contiene identificadores de intención.

## Ejecuciones nuevas

Windows, SDK 10.0.401/runtime 10.0.12, PostgreSQL 17.11. Copia aislada `.local/f0801-ac6e2910/freeze`, binlogs y diagnósticos privados. Restore locked y build Release: exit 0, 0 errores y 0 advertencias.

| Conjunto | Resultado y alcance |
|---|---|
| Codec existente | 9 casos puros: formato, sal/contexto, negativos y Unicode |
| Generación existente en almacén | 4 casos PG: entrega inicial/hash/recibo, autoridad/reautenticación, otro actor/intención y rollback de auditoría |
| Ruta propia existente | 1 caso HTTP/TestServer+PG: Origin, CSRF, actor, contraseña, entrega inicial y recibo/replay sin valores |
| Nuevo solapamiento de generación | 1 caso PG: dos PID realmente esperando, una sola respuesta con valores y una safe; 10 hashes / 1 operación / 1 evento de auditoría; replay/recibo invariables |
| Total C# focal | 15 PASS, 0 FAIL, 0 omitidas; no toda la suite RackClick ni 15 pruebas PostgreSQL distintas |
| Frontend existente | 10 Node PASS, 0 FAIL, 0 omitidas; contrato/journal/actor/recibos y textos EN/DE/ES; no navegador nuevo |

La espera del caso nuevo se demuestra reteniendo la fila Systemhaus y observando dos PID con locks no concedidos antes de liberarla. No se deduce solapamiento de llamar a Task.WhenAll. Los valores no se imprimen ni se incorporan a esta evidencia. El caso usa el rol DML no propietario del fixture existente y una cuenta/sesión MFA sintéticas; la generación no necesita leer una clave TOTP.

Pines finales:

- Servidor: `e2d3757943151bb5897871d07a95e07949f7a123a59ecb77ae82b93400f09b00`.
- Pruebas: `bd042f26048300263102e0b5fa15e94fa2f522765cf66cc2d40abd82bdf0dc0e`.

Comandos preservados en los logs privados: `dotnet test ... -c Release --no-build --no-restore --filter <14 focos existentes+nuevo>` y `-bl:<privado>/focus-{}.binlog`; Node 24.21.0 con `--test development/frontend/tests/mfa-recovery.test.mjs`. Los tests C# y Node son versionados; el driver privado sólo crea/cierra su clúster nuevo y fija entorno/pines. No contiene ni entrega un operador para D.

## Identidad de fuente y pruebas históricas

Las 227 fuentes/archivos de producto coinciden con F-07.05. Sólo se añade el test concurrente; no se altera generador, SQL, endpoints, UI, locks o política. La DLL tiene pin propio por reconstrucción en otra ruta: no se afirma igualdad binaria con candidata 43.

El núcleo de códigos/GUI conserva la identidad de la revisión final del punto 3. Program cambió después por mantenimiento/admisión/guardias y conexión protegida; el revisor contrastó ese delta, sin presentar el antiguo hash de Program como actual. Edge y pruebas históricas se reutilizan con sus ejecutores/entornos; las pruebas nuevas se identifican aparte.

No hubo fallo de build, de test o arreglo de producto en esta tanda. El aviso previo del revisor sobre un patrón de aserción de xUnit fue cautela histórica, no error del build actual. La prueba nueva amplía cobertura y pasó en su primera ejecución; no se inventa fase roja. Node conserva el aviso de tipo de módulo implícito del package.json existente, sin cambiar ni ocultar la configuración.

## Límites y decisiones

Se acredita sólo el literal técnico F-08.01. D2 §3a histórico menciona generación automática al confirmar enrolamiento; el flujo público revisado en punto 3 y el procedimiento vigente usan generación expresa posterior con contraseña actual/sesión MFA. No se declara satisfecha aquella automatización ni la garantía de que todos los administradores hayan guardado códigos; quedan explícitas para sus criterios/hitos.

Una sola entrega no impide copiar o descargar varias veces la respuesta que el usuario conserva visible. No se reexponen valores mediante status, receipt o replay. La puesta a cero de buffers no prueba borrado universal de strings/copies en memoria, y el fichero privado que el usuario descargue es su custodia, no un secreto almacenado en el servidor.

Independencia de la clave TOTP describe el material/hash de los códigos: no equivale a disponibilidad del host sin claves, canje operativo con pérdida de almacén o emergencia. No se ensayaron ahora uso/custodia en candidata instalada, SID de servicio, TLS, navegador, último administrador o adopción. No se prueban ni acreditan F-08.02–.05 por ejecutar generación.


## Dictamen y conciliación

[Revisión distinta](review/DICTAMEN.md): repetición propia del nuevo caso concurrente: 1/1 PASS con los mismos pines, separada de los 15 casos / 10 Node del coordinador. Sólo F-08.01 suma 1/2: 1859/84→1901/84=22,630952…/100 del cierre restante. No se acreditan los otros checkpoints/hitos de F08, una instalación o porcentaje global nuevo. Se reutiliza el guion QA-163 existente: 175 casos y resultados anteriores conservados, sin crear otro caso ni alterar disponibilidad.


Verificación documental final: el primer recorrido detectó un enlace mal escrito al plan. Se corrigió la referencia antes del escaneo y sellado; no afectaba al producto ni a las pruebas ejecutadas.
