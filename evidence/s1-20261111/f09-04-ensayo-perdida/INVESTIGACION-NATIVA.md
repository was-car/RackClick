# F-09.04 · decisiones del ensayo Windows

11.11.2026. Continuación del plan aprobado de pérdida total de **material de claves**, con anillo/censo fiables. D permanece fuera del ámbito. E conserva sus instalaciones anteriores y recibe una instancia sintética separada: cuenta estándar nueva, PostgreSQL propio, puertos exclusivos y binarios48 fijados. No es un instalador48 ni adopción productiva.

Se reutilizan el lector/escritor DPAPI, las identidades y los controles SCM aprobados, el shim Windows y el coordinador de procesos con Job Object del proyecto. No se añaden dependencias, versiones ni bibliotecas. La recuperación local se ensaya como SYSTEM; el servicio de aplicación se ejecuta con su propia cuenta estándar. Esto no acredita por analogía el mantenimiento positivo desde una sesión Administrador.

## Incidente de preparación y decisión

El primer inicializador utilizaba `pg_ctl start` con stdout/stderr redirigidos. El proceso de arranque terminó, pero el PostgreSQL descendiente conservó los pipes; esperar su EOF bloqueó al inicializador. El padre alcanzó su límite de espera. Posteriormente se observaron dos fallos de creación de proceso `0xC0000142`. No se deduce de ese código que no se ejecutara SQL ni que el catálogo estuviera vacío.

La inspección de control del clúster rechazó un estado distinto de cierre limpio **antes** de ejecutar consultas single-user. No se ejecutaron reparación, `pg_resetwal`, cambios de autenticación ni borrado. Se conservó íntegro el directorio del intento propio, en el mismo padre y con destino exclusivo, verificando sus hashes de control y versión. Su catálogo queda **desconocido**, su estado **no limpio**, y no se afirma recuperabilidad. Los rechazos y recibos originales permanecen privados.

La reanudación usa un `postgres.exe` en primer plano dentro del Job Object propio: comprueba pertenencia, espera readiness, ejecuta las operaciones cortas y solicita parada limpia antes de esperar salida y EOF. Cada operación corta tiene un plazo que incluye proceso y drenaje, y registra la salida del proceso antes del EOF. Una parada inconclusa se conserva sin matar procesos ni reintentar automáticamente.

El diagnóstico bajo la cuenta estándar se lanza con un archivo y argumentos cortos: [CreateProcessWithLogonW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-createprocesswithlogonw) limita la línea de comando a1024caracteres. No se ponen contraseñas en argumentos. Los comandos/resultados privados se conservan en `.local`; las credenciales del inicializador quedan fuera del acceso del servicio antes de registrar SCM.

La ejecución directa de [postgres17](https://www.postgresql.org/docs/17/app-postgres.html) permite mantener el proceso supervisado durante la preparación. Esto resuelve el problema de pipes del arnés; no modifica el producto ni atribuye el incidente a MFA. La preparación del laboratorio y la transición de recuperación se evalúan por separado. No se afirma atomicidad ante pérdida de alimentación de un renombrado ni durabilidad universal de directorios.

## Correcciones adicionales del arnés, sin reconstruir el producto

La segunda preparación creó el clúster y dos roles, pero se detuvo al obtener `.stdout`: PowerShell emitía dos objetos internos `VoidTaskResult` al llamar a los awaiters de las copias de streams. Se reprodujo en Windows PowerShell5.1: tres objetos antes y un único Hashtable después de descartar expresamente esos dos resultados. El proceso SQL había devuelto0; la parada de PostgreSQL también devolvió0 y dejó el clúster limpio. Se conservaron las credenciales cifradas del checkpoint para continuar sobre esos objetos, sin recrear roles o clúster.

La siguiente preparación se detuvo al leer `postmaster.pid` durante el arranque, antes de consultar SQL. Se conservó el tipo externo `MethodInvocationException`, pero no su excepción interna: ese registro **no identifica por sí solo** un error de compartición concreto. La parada y la comprobación posterior de control fueron correctas. La espera corregida abre ese archivo temporal con compartición de lectura/escritura/borrado y sólo tolera, dentro de su plazo normal, errores de archivo ausente o compartición/bloqueo2/32/33. Los demás errores se propagan; identidad, puerto, pertenencia al Job y estado `ready` siguen siendo obligatorios. Cada reanudación exige hashes actuales del control y del recibo de parada, y comprueba el catálogo antes de modificar SQL.

## Límites de aceptación

El validador Scheduler rechazó tres variantes con HRESULT `0x80041319`, sin registrar ni ejecutar tareas. La misma definición pasó la validación al fijar explícitamente el contexto de la acción al identificador de su principal. Se consultaron [RegisterTaskDefinition](https://learn.microsoft.com/en-us/windows/win32/taskschd/taskfolder-registertaskdefinition) y el [esquema de tareas](https://learn.microsoft.com/windows/win32/taskschd/task-scheduler-schema); flags1 valida, flags2 crea. Launcher49 conserva el48 original y se fija por un hash externo, con el resto de controles y limpieza conservados.

Los primeros clientes HTTP fallaron con Timeout. La prueba de cabeceras sin leer cuerpo no se elevó a éxito completo. Se instrumentó la llamada real, se verificó la base propia por SQL de sólo lectura (siete relaciones vacías) y se midió Ready con lectura del cuerpo antes de repetir Baseline. El cliente final usa TLS1.2 y conserva pin/nombre; sólo admite hasta tres GET de salud ante Timeout. Ningún POST, seed ni transición de mantenimiento se reintenta. La causa universal de la primera conexión no quedó demostrada: no se afirma una corrección del servidor por este ajuste del arnés.

Se separan identidades: cliente HTTP Administrador Windows, mantenimiento SYSTEM y servidor bajo cuenta estándar. Los clientes SYSTEM fallidos se conservan como tales. Baseline final, pérdida, rechazo explícito, cinco fases de recuperación y vuelta por TOTP2 pasaron; el laboratorio propio se detuvo al terminar, sin tocar las instalaciones anteriores.

Siguen separados: prueba de componentes; ensayo nativo con servicio/TLS/TOTP; instalación/Restore48; custodia física externa; pérdida de todos los metadatos; una segunda pérdida después de otra completada; retirada de versiones tras pérdida sin rotación posterior; F-09.05 y QA final de Wascar. Un resultado `data_verified` del CLI no acredita por sí mismo servicio recuperado o acceso administrativo.
