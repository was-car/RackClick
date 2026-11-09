# Operadores SQL protegidos · formatos v2

02.11.2026 · desarrollo F-02.02. Complementa [el contrato del host](CONTRATO-CONEXION-SQL-CIFRADA-v1.md). **No es una actualización de D ni de la candidata 11. No copiar scripts sueltos a una instalación.**

## Componentes disponibles en fuentes

`RackClick.SqlSecrets.ps1` define funciones sin operar el equipo al importarlo. No añade comandos HTTP, dependencias, usuarios o servicios. Usa `System.Security` de Windows PowerShell 5.1.

| Componente | Función y límite |
|---|---|
| `New-SqlProtectedRuntimeStore` | Prepara un árbol nuevo `<instancia>/sql-security/<UUID>/sql-secrets/runtime.bin`, con ACL privada y ciphertext RCSQL001. Devuelve un descriptor; no reescribe manifiestos ni activa el host. La fase elevada debe asignar después propiedad SYSTEM y lectura sin escritura al SID del servicio. |
| `Get-SqlRuntimeDefinition` | Valida el descriptor v2 contra la raíz/UUID/base/rol esperados y fija la ruta. No acepta otra raíz o un formato desconocido como conexión legada. |
| `Read-RackClickInstance` | Lee el descriptor runtime v2, contrasta hash y retiene el archivo cifrado. Devuelve metadatos SQL, sin conexión descifrada. Conserva el formato runtime legado por una rama explícita. El resto del contrato de cinco secretos de instancia sigue siendo legado. |
| Lanzadores de laboratorio y servicio | Seleccionan el entorno mediante `Set-SqlRuntimeEnvironment`. En protegido pasan sólo metadatos `SqlSecret__*`, eliminando `ConnectionStrings` y sus alias. En legado desactivan explícitamente SqlSecret y usan la conexión anterior. |
| `New-SqlProtectedBackupProfile` | Crea una carpeta exclusiva nueva con `backup-profile.json` v2 y `password.dpapi.json`. No adopta un destino existente. La contraseña usa DPAPI CurrentUser, vinculada además a propósito/UUID/SID/host/puerto/base/usuario. |
| `Read-BackupProfile` | Acepta v1 legado o v2 protegido. El v2 exige descifrado correcto; no intenta interpretar el ciphertext como una contraseña en claro. |
| Ficha y diagnóstico | Exportan metadatos de conexión y códigos finitos. La ficha omite contraseñas web/SQL; su consulta local autorizada sigue disponible en la ventana privada. |

## Identidad, entorno y recuperación

El perfil de backup se debe **crear y usar bajo la cuenta que ejecutará el backup**. No crearlo bajo Administrator y suponer que la cuenta estándar podrá abrirlo. En otra máquina/cuenta se generan credenciales y perfil nuevos; no copiar `password.dpapi.json` del origen como recuperación.

DPAPI CurrentUser no es un formato portable ni reemplaza la custodia MFA. El host .NET consume el runtime RCSQL001 con LocalMachine y ACL de servicio; PowerShell produce/consume el mismo formato sin añadir una CLI .NET. La interoperabilidad se prueba en ambos sentidos y en el validador completo del visor. Las copias de bytes propias se limpian; los strings de PowerShell/.NET no tienen borrado garantizado.

El aislamiento del proceso hijo elimina los dos nombres normales de ConnectionStrings/SqlSecret y los once prefijos que .NET 10 convierte a ConnectionStrings: MYSQL, SQLAZURE, SQL, CUSTOM, POSTGRESQL, APIHUB, DOCDB, EVENTHUB, NOTIFICATIONHUB, REDISCACHE y SERVICEBUS, todos seguidos de `CONNSTR_`. Se limpian tanto las claves recibidas como las ambientales, sin cambiar el entorno del padre. [Fuente .NET fijada](https://github.com/dotnet/runtime/blob/v10.0.0/src/libraries/Microsoft.Extensions.Configuration.EnvironmentVariables/src/EnvironmentVariablesConfigurationProvider.cs).

El operador de backup usa el pgpass temporal privado ya existente y lo retira al finalizar. Exporta sólo `data.dump` y `manifest.json`; no incorpora perfil, contraseña, ciphertext o claves DPAPI. Restaurar SQL con el operador actual crea una base nueva y no autoriza arrancar la aplicación por sí solo: faltan los grants/runtime y la recuperación de aplicación que correspondan. [Formato pgpass oficial](https://www.postgresql.org/docs/17/libpq-pgpass.html).

## Acceso local y ficha

La ventana elevada «Acceso privado» valida servicio, recibos, hashes, rutas y archivos antes de presentar datos. El runtime v2 se lee mediante el lector nativo acotado; sólo se añade la ruta exacta de ciphertext con UUID. El visor acepta las ocho claves legadas o las once del codec .NET protegido, con `Persist Security Info`, `Include Error Detail` y `Log Parameters` estrictamente false. Los flags no amplían el formato legado.

**«Guardar ficha sin contrasenas»** crea un archivo nuevo con URL, usuario web, host, puerto, base, usuario SQL y aviso de que SQL directo tiene escritura y no aplica ámbitos web. Ninguna de las dos contraseñas entra en ese archivo. La ventana conserva máscara por defecto y revelado local explícito. No adjuntar capturas de contraseñas al QA. La ficha es información operativa, no un backup ni un export de credenciales.

El diagnóstico acepta sólo el vocabulario finito revisado; un valor desconocido no se refleja como mensaje/código arbitrario. No copia conexión, perfil privado o ciphertext al informe.

## Tramos que siguen pendientes

1. Conectar estos formatos a New/Restore y a sus recibos/hashes, sin dejar las credenciales SQL restantes en claro. El lector Instance aún exige los cinco archivos originales y la referencia `owner-password.txt`; un perfil v2 aislado no equivale a una instancia protegida completa.
2. Aplicar y comprobar la propiedad/ACL productiva del runtime, y crear el perfil de backup bajo su cuenta efectiva. El almacén preparatorio actual no acredita por sí mismo esos permisos.
3. Actualizar el inventario/lector de distribución para transportar el módulo nuevo, construir una candidata completa y comprobar compatibilidad. El paquete 11 conserva sus bytes y sus operadores anteriores.
4. Ensayar servicio, backup programado y recuperación en otra instancia/host con actores nuevos. Los ensayos locales de este lote usan el mismo principal Windows y PostgreSQL 17.11 nuevo, no el SID efectivo del servicio.

F-02.02 permanece **en progreso, sin crédito**. F-02.01 conserva su extremo de cuenta/instancia real pendiente; F-02.03 y cierre final también. QA-168 está planificado para una candidata futura, no habilitado en D.
