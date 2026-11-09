# SQL protegido · instancia3 · candidata12

02.11.2026. Extiende los formatos1/2 conservando sus lectores. No modifica D ni los ZIP11. La candidata12 sólo puede acreditarse como instalación después del ensayo Windows de su paquete exacto.

## Datos y actores

La cabecera del manifiesto3 conserva las19claves anteriores y añade `backupRole`, exactamente `rc_backup_` seguido del UUID de la instancia sin guiones. El privado contiene exactamente `admin-login.json`, `backup-profile.json`, `backup-password.dpapi.json` y `runtime.json`. El descriptor runtime conserva versión2 y su archivo RCSQL001 bajo `sql-security/<UUID>/sql-secrets/runtime.bin`.

- **Provisionamiento:** crea roles cluster/owner/runtime/backup y contraseñas nuevas. Cluster y owner se usan sólo para inicializar, migrar/recuperar en la base nueva y conceder permisos. Sus contraseñas no se conservan en perfiles de la instancia3.
- **Ejecución web:** usa únicamente runtime SQL, sin propiedad de la base ni DDL. El lector Windows deriva el SID efectivo y requiere propiedad SYSTEM/Administradores, con lectura sin escritura para el SID del servicio. El setup elevado aplica esa seguridad después de la preparación; el laboratorio con propietario del operador no sustituye ese positivo.
- **Backup:** usa otro rol SQL, sin superusuario/CREATEDB/CREATEROLE/replicación/bypassRLS, con CONNECT, USAGE y SELECT de tablas/secuencias. No tiene DML ni DDL. Su contraseña CurrentUser se crea bajo la cuenta Windows que ejecuta el backup; la tarea programada usa esa misma cuenta. Esto separa los privilegios SQL; no promete defensa frente a compromiso del actor Windows que también administra los archivos PG.
- **Acceso privado:** el operador elevado consulta runtime por el lector administrativo ya existente. Los manifiestos1/2/3 tienen ramas e inventarios cerrados. La ficha exportada no incluye contraseñas. No se entregan las credenciales SQL owner/cluster al operador desde un archivo oculto.

## Temporales y peticiones

El intermediario recibe las peticiones de bootstrap/migrate/recover-admin cifradas CurrentUser y ligadas a su ruta. En modo mínimo el Gate las abre con DeleteOnClose y cierra el identificador antes de descifrar/arrancar el hijo. New/Restore no declaran preparación correcta si conservan una petición protegida sin consumir. El archivo de initdb y el pgpass de Restore son exclusivos y temporales, con retirada propia en finally; no se adoptan archivos ajenos.

No se afirma borrado físico universal ni limpieza de strings administrados. Un corte antes de consumir una petición puede dejar ciphertext en un intento incompleto; no se promueve ese intento como instalación preparada. Los temporales de libpq se retiran también después de un rechazo.

## Mantenimiento y recuperación

**Las actualizaciones con DDL siguen el procedimiento de Restore a instancia nueva.** Se crea un backup nativo con la cuenta de lectura, se verifica contra su manifiesto/pin, y se recupera con una aplicación compatible en un clúster/base nuevos. El provisionador nuevo dispone de owner/cluster sólo durante esa preparación; no necesita descifrar ni reutilizar los del origen. Revoca las sesiones/desafíos según el contrato de recuperación y concede permisos al runtime/backup nuevos. Las transiciones de esquema admitidas siguen siendo una lista explícita del operador, no cualquier SQL/versionado del llamador.

No usar `--migrate` contra una instancia3 en marcha ni esperar que haya una contraseña owner para HeidiSQL. No se incorpora mantenimiento DDL en sitio como función implícita de esta entrega. La recuperación de claves/factores MFA conserva su guardia existente y su procedimiento separado: un backup con factores no se convierte automáticamente en restaurable por haber protegido SQL.

En la misma instalación, reiniciar servicio o ejecutar el backup reutiliza runtime/backup locales; no regenera nada ante error. En otro Windows/SID se genera todo de nuevo. Un perfil cifrado copiado de otro contexto se rechaza; sólo se transportan `data.dump` y `manifest.json`, nunca los perfiles DPAPI como recuperación.

## Estado y ensayo

El ensayo PG17.11 nuevo de instancia3 comprueba New, backup con rol mínimo, Restore de20clientes sintéticos, dos reanudaciones y backup posterior. Los roles SQL de escritura/DDL se rechazan donde corresponde. El visor tiene122controles y12focos de orquestación con fronteras simuladas, sin abrir datos reales. Estas pruebas no reemplazan el servicio estándar, el backup programado, HTTPS o el reinicio en VM.

La nueva distribución usa el perfil cerrado `schema43-sql-protected-01`, frontend vigente del punto3 y código C# SQL actual. El bundle nuevo transporta26operadores, incluido `RackClick.SqlSecrets.ps1`; los paquetes históricos conservan25 y sus bytes. Las fuentes actuales no deben empaquetarse como un bundle histórico sin ese módulo.

[Registro del trabajo y pruebas](../evidence/s1-20261102/cierre-bloqueantes-01-07/) · [Revisión anterior de1–7](REVISION-PASOS-01-A-07-RACKCLICK.md), superada sólo en los tramos técnicos que se acrediten después.
