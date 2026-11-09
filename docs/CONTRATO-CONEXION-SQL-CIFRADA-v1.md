# Conexión SQL cifrada · contrato v1

02.11.2026 · F-02.01. Desarrollo de fuentes; no actualización de la candidata 11 ni de D.

El objetivo es retirar la contraseña SQL de la configuración persistida y entregar al servicio únicamente su identidad de ejecución. Los archivos actuales del instalador siguen pendientes de adaptación: **este contrato no afirma que D o sus archivos SQL estén cifrados**.

## Configuración del host

La sección explícita `SqlSecret` contiene sólo metadatos:

| Campo | Contrato |
|---|---|
| `Enabled` | Ausente/false conserva el comportamiento legado. true exige la ruta cifrada; otros valores se rechazan. |
| `InstancesRoot` | Raíz absoluta de las instancias. No se crea ni se repara desde el arranque. |
| `InstallationId` | UUID canónico no vacío. |
| `Database` | Nombre de la base de esta instalación, minúsculas ASCII/dígitos/guion bajo, hasta 63 caracteres y comienzo por letra. |
| `RuntimeUser` | Rol SQL de ejecución esperado, con el mismo formato de nombre. No el owner de migración ni el administrador del clúster. |

Ruta fija: `<InstancesRoot>/<InstallationId>/sql-secrets/runtime.bin`. La configuración no elige otro archivo ni contiene contraseña. El SID lector se obtiene del proceso; se rechaza una identidad suplantada. La confianza de propietarios/escritores del host está fijada a SYSTEM y Administradores, sin configuración para ampliar esa lista. El seam interno usado por pruebas no es una opción del producto.

Con `Enabled=true`, una conexión `ConnectionStrings:RackClick` presente produce `sql_secret_plaintext_conflict`: no se usa como respaldo ni se tolera mantener ambas rutas. La selección y validación se hacen antes de construir NpgsqlDataSource y de abrir el listener. Si se habilita sin material válido, el arranque termina con código 1 y un código constante, sin ruta, secreto, pila o excepción interna de ese componente.

## Material y lectura

Formato binario: prefijo ASCII fijo `RCSQL001` seguido de un blob DPAPI LocalMachine, máximo 65.536 bytes. El texto claro tiene un máximo de 8.192 bytes UTF-8 estricto. Entropía de propósito `RackClick/SQL/runtime/v1`, instalación, SID, base y rol, separados canónicamente. Cambiar esos vínculos o el ciphertext impide abrirlo. No es una clave MFA ni un sobre portable RCKEY.

`WindowsSqlSecret.ProtectForProvisioning` devuelve sólo bytes cifrados en memoria. No escribe archivos, imprime conexiones ni ofrece un comando al usuario. El provisionador debe publicar con ACL privada desde la creación, exclusividad, integridad y recibo; su implementación pertenece al siguiente paso. No debe activar esta sección antes de completar el circuito.

El lector aprobado `WindowsMfaKeyFileReader` se reutiliza sin modificar: valida carpetas del almacén y abre/retiene el mismo archivo para comprobar propietario, DACL, identidad, tamaño y ruta final. Sólo el SID lector y los principales de confianza pueden leer; el lector no puede escribir/cambiar permisos ni ser propietario. Se conservan sus límites: no calcula acceso efectivo completo; las carpetas se validan por ruta y los ancestros superiores se anclan, sin afirmar que toda carrera desaparezca.

La conexión descifrada debe incluir contraseña explícita, host, base y usuario esperados, sin `Passfile`. Se normalizan a false `Persist Security Info`, `Include Error Detail` y `Log Parameters`. No se publica el texto. Copias de bytes y buffers nativos con texto claro se ponen a cero; el string que necesita Npgsql y sus copias internas no pueden garantizarse borrados del runtime.

DPAPI LocalMachine **no impide descifrar a quien obtiene el blob en esa máquina**: la ACL es parte esencial de la protección. No protege de administradores/SYSTEM, de memoria de un proceso autorizado o de un host comprometido. [Semántica oficial](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata), [parámetros Npgsql](https://www.npgsql.org/doc/connection-string-parameters).

## Separación y recuperación

Con protección habilitada, `--bootstrap`, `--migrate`, `--recover-admin` y `--mfa-require-all` rechazan `sql_secret_runtime_only` antes de usar credenciales o entrada interactiva. Su operador tendrá que componer una invocación de mantenimiento distinta con identidad autorizada; no puede reutilizar el blob runtime para obtener DDL. El modo `--mfa-keys-init`, que no usa SQL, conserva su contrato.

En destino nuevo se recrean owner/migración/runtime y contraseñas nuevas, se conceden permisos mínimos y se sella otro blob con el SID/instalación de destino. No copiar el DPAPI del equipo antiguo como recuperación. El dump de inventario no transporta estas credenciales. Backup/acceso HeidiSQL/diagnóstico y protección de las demás credenciales SQL deben adaptarse en F-02.02 y ensayarse en F-02.03. La custodia y los sobres MFA existentes no cambian.

## Estado y aceptación

Integración de lectura en fuentes y pruebas de laboratorio disponibles. Pendientes el provisionamiento de los operadores, la candidata completa nueva y el positivo con SID efectivo del servicio/instancia nueva. El criterio literal de F-02.01 conserva ese extremo; no se acredita por simular un lector con el grupo Usuarios. No habilitar en D ni modificar sus archivos para este lote. El resto del cierre de F-02 permanece pendiente.
