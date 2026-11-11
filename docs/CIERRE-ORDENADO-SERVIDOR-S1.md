# Cierre ordenado local del servidor Windows

Grupo248–257, desarrollo interno S1. El servidor conserva sus rutas HTTP, GUI, permisos, esquema9 y dependencias. Esta extensión optativa permite que el lanzador local solicite el cierre normal del host y que Kestrel termine peticiones ya iniciadas. No es un instalador, servicio Windows ni aceptación final.

## Contrato privado por ejecución

`RackClick:ShutdownPipe` y `RackClick:ShutdownToken` deben estar ambos ausentes o ambos presentes. Ausentes mantienen el comportamiento anterior. El canal requiere Windows, nombre `rc-shutdown-` seguido de UUID de32 caracteres hexadecimales minúsculos distinto de cero y token criptográfico de64 caracteres hexadecimales minúsculos. Una configuración incompleta o inválida impide iniciar el servidor mediante un mensaje fijo sin valores privados. Bootstrap y migración no registran este canal.

El lanzador genera nombre/token nuevos para cada ejecución y los entrega exclusivamente al entorno privado del hijo mediante `RackClick__ShutdownPipe` y `RackClick__ShutdownToken`. No se imprimen, guardan en el manifiesto público ni envían por HTTP.

El servidor mantiene un único `NamedPipeServerStream` con `CurrentUserOnly`, `Asynchronous` y `FirstPipeInstance`. Los clientes tienen que pertenecer a la misma cuenta y nivel de elevación Windows; el nombre se conserva también entre solicitudes rechazadas. La protección corresponde a [PipeOptions de Microsoft](https://learn.microsoft.com/en-us/dotnet/api/system.io.pipes.pipeoptions?view=net-10.0).

## Protocolo y resultado real

La solicitud es JSONL ASCII, máximo256 bytes incluyendo LF, sin CR, con exactamente los campos `schemaVersion:1`, `action:"stop"` y `token`. Se rechazan duplicados, campos desconocidos, tipos distintos y nonce incorrecto. La comparación del token usa `CryptographicOperations.FixedTimeEquals`; no se registran solicitudes ni secretos.

Cada cliente tiene un plazo total de3 segundos para lectura y respuesta. EOF, JSON inválido, exceso de tamaño, desconexión o inactividad no detienen el host ni inutilizan el canal para el siguiente cliente. El cliente recibe una línea fija con `schemaVersion:1` y `accepted:false` cuando el transporte permite responder. Un cliente desconectado o vencido puede recibir solamente EOF.

La petición válida recibe `{"schemaVersion":1,"accepted":true}` y LF. El cliente tiene que leer ese ACK completo y cerrar su extremo del pipe **antes** de esperar la salida del proceso. El servidor escribe y llama `FlushAsync`, conserva la conexión y espera EOF dentro del mismo plazo de3 segundos; sólo entonces llama `IHostApplicationLifetime.StopApplication()`. Bytes adicionales, ausencia de cierre o timeout no ordenan parar el host. Esta espera evita desconectar y descartar un ACK pendiente: [`DisconnectNamedPipe` descarta bytes no leídos](https://learn.microsoft.com/en-us/windows/win32/api/namedpipeapi/nf-namedpipeapi-disconnectnamedpipe), mientras [`PipeStream.FlushAsync` no confirma consumo](https://raw.githubusercontent.com/dotnet/runtime/v10.0.0/src/libraries/System.IO.Pipes/src/System/IO/Pipes/PipeStream.cs). No se usa `WaitForPipeDrain` sin límite. EOF por sí solo tampoco demuestra consumo; el cliente oficial verifica ACK y cierre, y después la salida.

Ese ACK sólo confirma que la solicitud está autenticada; no confirma que el cliente haya completado el protocolo ni que el proceso haya terminado. La finalización se comprueba por separado. `HostOptions.ShutdownTimeout` se fija en15 segundos para el host configurado; [Microsoft documenta el alcance del plazo](https://learn.microsoft.com/en-us/dotnet/api/microsoft.extensions.hosting.hostoptions.shutdowntimeout?view=net-10.0).

El lanzador debe esperar el proceso y comprobar exitCode0. Incluso una salida0 puede ocurrir después de agotar los15 segundos y abortar peticiones largas: ACK y exitCode0 sólo acreditan cierre normal solicitado, no drenaje universal. Por ello el reporte mantiene `applicationHttpDrain:false` y diferencia `applicationGracefulExit:true` cuando la orden autenticada termina con salida0 sin cierre forzado. La prueba de petición en curso200 demuestra exclusivamente ese recorrido acotado. Si el proceso no termina dentro del plazo del lanzador, el JobObject sigue siendo una recuperación forzada. La pertenencia al JobObject y la parada de PostgreSQL siguen siendo responsabilidad del lanzador. Un error de infraestructura del canal hace fallar el host conforme a la política predeterminada de `BackgroundService`, en lugar de mantener una aplicación viva sin canal de control.

## Pruebas y límites

`development/server/tests/test_native_shutdown.py` crea un fixture nuevo y privado Windows sin PostgreSQL. Una sola compilación de fixture sin paquetes enlaza una copia byte por byte del mismo `NativeShutdown.cs`. No añade rutas de prueba al producto. Los cinco grupos comprueban configuración cerrada, rechazo recuperable/EOF, límites y timeout, cliente autenticado que no cierra o envía bytes adicionales sin parar el host, lector de ACK retrasado500ms seguido de salida normal con petición HTTP en curso200, y exclusividad del canal.

```powershell
C:/Python312/python.exe -B development/server/tests/test_native_shutdown.py --evidence .local/evidencia-cierre-nueva
```

Cada directorio de evidencia debe ser nuevo. Las salidas crudas de procesos y tokens quedan sólo en `.local` privado. El reporte público contiene hashes, entorno, resultados y límites. Estos tests no prueban PostgreSQL, HTTPS, SCM ni instalación limpia; la integración de la aplicación compilada corresponde al recorrido separado del coordinador. La revisión independiente se registra aparte de las pruebas del implementador. El catálogo y los resultados QA de Wascar no se modifican por este cambio operativo sin interfaz nueva.

Resultado propio17.10.2026: **5/5 correctos,27,547s, Windows11**, una compilación del fixture3,890s, cero paquetes y cero builds de aplicación por este implementador. La fuente copiada al fixture coincide byte por byte con `NativeShutdown.cs` SHA256 `b7f8608da21fb318a5df685c86cf14aa35edc1d3d228ed3e6746d034b5d4b2db`. Fuentes intactas y procesos de fixtures detenidos al terminar. [Resultado y límites](../evidence/s1-20261017/treinta-tandas-248-277/backend/own/native01/result.json), [cierre del bloque](../evidence/s1-20261017/treinta-tandas-248-277/backend/CIERRE.md). No se ha ejecutado aquí una prueba con otra cuenta/elevación Windows ni la expiración real de15 segundos de una petición larga; no se deduce drenaje universal de la salida0.
