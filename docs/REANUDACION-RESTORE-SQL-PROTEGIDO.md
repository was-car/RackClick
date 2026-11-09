# Reanudación y Restore con credenciales SQL protegidas

02.11.2026 · desarrollo del paso 7, F-02.03. Complementa los contratos [del host](CONTRATO-CONEXION-SQL-CIFRADA-v1.md) y [de operadores](OPERADORES-SQL-CIFRADOS-v2.md). **D y los paquetes 11 se conservan. No instalar ni copiar estos scripts sobre ellos.**

## Ruta de desarrollo

`New-RackClickLabInstance.ps1` y `New-RackClickRecoveredInstance.ps1` admiten el opt-in `ProtectSqlCredentials`. Continúan exigiendo `DevelopmentLoopbackHttp`; no son una nueva candidata Windows. Sin el opt-in mantienen la rama legada. El manifiesto v2 tiene las mismas claves de cabecera y un inventario cerrado de seis archivos privados:

| Archivo | Contenido |
|---|---|
| `admin-login.json` | Acceso web inicial privado, conservado según el contrato existente. No es una clave SQL cifrada ni un export público. |
| `backup-profile.json` | Metadatos v2 del propietario, UUID, puerto/base/rol y referencia exacta al archivo cifrado. |
| `owner-password.dpapi.json` | Contraseña nueva del propietario, DPAPI CurrentUser con contexto autenticado. |
| `cluster-profile.json` | Metadatos v2 del administrador del clúster nuevo. |
| `cluster-password.dpapi.json` | Contraseña nueva del clúster, DPAPI CurrentUser con contexto distinto. |
| `runtime.json` | Descriptor v2; nunca una conexión en claro. Referencia y hash de `sql-security/<UUID>/sql-secrets/runtime.bin`. |

El runtime usa RCSQL001/DPAPI LocalMachine y conserva los requisitos de propietario/ACL del lector aprobado. El lector de instancia comprueba metadatos, rutas, inventario y hashes sin descifrar las claves privilegiadas owner/cluster. El mantenimiento y el backup las abren explícitamente mediante sus perfiles y el actor autorizado. Esta separación evita exigir al runtime la identidad DPAPI del provisionador; **no acredita todavía una cuenta de backup con privilegios mínimos ni la separación operativa final de actores**.

Los hijos bootstrap/migrate/recover-admin de la rama protegida usan una petición de proceso DPAPI CurrentUser ligada a su ruta, sin conexión SQL ni entrada sensible en claro dentro de `request.json`. El Gate exige el sobre protegido, sin fallback al formato legado; sus fallos no vuelcan excepciones internas en ese modo. Entorno/stdin se descifran sólo en memoria del actor. No se afirma borrado universal de strings o defensa contra administrador/memoria.

`initdb` necesita un archivo de contraseña. La rama protegida crea uno exclusivo privado, lo retira en `finally` también si escribir/flush falla después de crear, y nunca retira un archivo preexistente. Un corte de proceso/host antes del finally puede dejar ese temporal privado. No se promete borrado físico del disco ni recuperación automática de un intento parcial; el destino existente siempre se conserva y rechaza.

## Recuperar no significa copiar DPAPI

El origen del Restore es sólo `data.dump` + `manifest.json`, contrastados contra un SHA256 externo. En el nuevo destino se crean clúster, UUID, base, owner, runtime, contraseñas y material DPAPI nuevos. Se reutilizan la recuperación transaccional del administrador, revocación de sesiones/desafíos, auditoría y grants ya existentes. No se copian archivos de credenciales SQL del origen ni se relaja el control de MFA del Restore.

Reanudar una instancia inicializada utiliza sus perfiles locales existentes; no se regenera material ante error. Material ausente, alterado o de otro contexto produce rechazo antes de iniciar el clúster en el ensayo de mantenimiento. El host conserva además su propio preflight runtime antes de escuchar HTTP. Son controles distintos: la sonda SQL no sustituye el arranque real del servicio.

## Ensayo y límites

Se usa la aplicación43 ya fijada y verificada **sólo para sus CLI de bootstrap/recuperación**, PostgreSQL17.11 y Windows PowerShell5.1, con dos clústeres nuevos sin registrar servicios. Esa DLL histórica no incorpora los cambios C# SQL del paso5: no se afirma que pueda arrancar HTTP con el descriptor nuevo. La sonda de mantenimiento crea veinte filas sintéticas y comprueba la recuperación y reanudación del clúster con el rol runtime sin DDL. Las pruebas de claves deliberadamente alteran **sólo sus propios fixtures** y restauran los bytes al terminar. Los logs, dumps y acceso web inicial permanecen privados bajo `.local`; la evidencia exportada no contiene valores de secretos.

Pendientes para cerrar F-02: integrar el formato en setup/recibos/distribución, aplicar propiedad y ACL productivas y comprobar el servicio estándar, el backup programado con su actor y una recuperación en otro Windows/SID. El mismo usuario Windows en dos clústeres no demuestra portabilidad DPAPI ni esos actores. F-02.01/.02 conservan sus pendientes; no se trasladan para acreditarlos. F-02.03 sólo puede registrarse parcial mientras falte el extremo operativo.

[Resultados y revisión](../evidence/s1-20261102/f02-03-restauracion/RESULTADOS.md).
