# Restauración del instalador: prueba aislada Windows

`Test-RackClickServerRestore.ps1` carga únicamente las funciones de preparación mediante el AST. No ejecuta ni relaja los guardas de identidad/rutas del punto de entrada de producción.

Ejecutar desde la raíz con PowerShell 5.1, proporcionando la carpeta de un backup PostgreSQL nativo confiable (exactamente `manifest.json` y `data.dump`):

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File .\tools\tests\server_restore\Test-RackClickServerRestore.ps1 -SourceBackupPath 'C:\ruta\backup-nativo' -NativeRestore
```

Comprueba cambio de TEMP/TMP heredado usando ProfileList del SID real, creación privada exclusiva, copia exacta con el lector original y hashes, rechazo de destino existente, pin incorrecto, origen externo directo, origen con propietario del servicio, dump alterado y archivos extra. Conserva los originales y los fixtures bajo `.local/labs/server-restore-tests-<GUID>`; no borra ni sobreescribe bases existentes.

`-NativeRestore` añade ejecución del operador original contra una instancia nueva y puertos libres: exige JSON/código de salida/recibo/estado coherentes, manifiesto original y evento de auditoría de recuperación, y parada PostgreSQL confirmada. Utiliza el ZIP fijado que ya existe bajo `.local`; no descarga dependencias, instala cuentas, registra servicios o tareas, ni altera certificados/firewall. El script conserva stdout/stderr privados dentro del fixture.

`Test-RackClickRestoredProfile.ps1` completa esa misma instancia restaurada con un perfil Production HTTPS nuevo y ejecuta `Verify`. Requiere la ruta del fixture, SHA del recibo, IP local y puerto HTTPS del recibo. Verifica la CA pública y las seis carpetas/un archivo mutables devueltos al broker. No arranca el servidor HTTPS ni agrega confianza del certificado.

El positivo de ACL con propietario Administradores/SYSTEM y un SID de servicio diferente, la entrada fija de producción en ProgramData/ProgramFiles y el ciclo SCM/reinicio se deben comprobar en el ensayo elevado del instalador. Estas pruebas con una cuenta estándar de desarrollo no los certifican. El fallo de permisos detectado inicialmente en Temp de LEAO se conserva como evidencia: el código usa AppData/Local del perfil vinculado al SID solo para compilar el helper C# fijo sin secretos, y después pasa a su TEMP privado bajo la instancia.
