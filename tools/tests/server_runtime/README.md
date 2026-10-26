# Runtime de servidor: verificación acotada

`Test-RackClickServerRuntime.ps1` se ejecuta con Windows PowerShell 5.1 sobre un perfil nuevo cuya instalación y despliegue ya estaban preparados. Exige el SHA256 retenido fuera del perfil y el UUID de un arranque que ya terminó limpiamente. No crea bases, no modifica SCM, firewall ni almacenes de confianza y no borra archivos.

Comprueba el perfil, el rechazo de hash incorrecto, el rechazo de un UUID ajeno y la repetición idempotente de Stop del UUID terminado. Sus resultados no acreditan por sí solos Start, Backup, servicio Windows ni acceso desde otro equipo.

Ensayo de implementación ejecutado el 19.10.2026 por el agente de runtime: fixture aislada autorizada `installer-diagnostic-2b5a802fc3e4483ab123cab22206e3d2`; perfil TLS LAN `https://192.168.178.91:51077`; SDK/GUI/binarios no recompilados. Start emitió ready; Backup online creó otro destino nuevo; Stop terminó con `applicationGracefulExit=true` y `postgresCleanStop=true`, exit 0. UUID `110b0449-5b3e-4420-aaf3-f64b7e49a991`. No es una prueba ejecutada en el Windows Server de Wascar ni una aprobación independiente.

Se detectaron durante la implementación un intento de importación de helpers de .NET Framework desde PowerShell 7 y el paso de un argumento vacío a un proceso PowerShell 5.1 en el propio guion de pruebas. Se repitió con Windows PowerShell 5.1 y argumentos opcionales omitidos; cuatro comprobaciones PASS. El código publicado requiere Windows PowerShell 5.1.

El certificado automático usa CA privada y hoja RSA3072/SAN exacto de 90 días. Sólo se exporta el certificado público CA; la clave privada CA no se retiene. Renovar un perfil automático requiere emitir otra CA y distribuir su confianza explícitamente. No se instala confianza automáticamente. El PFX y su contraseña permanecen privados.

Limitaciones de este ensayo: no SCM, firewall, identidad de servicio, ACL endurecidas por broker, navegador remoto, restauración de ese backup ni peticiones HTTP activas durante el cierre. El respaldo es de base de datos; no sustituye una copia de recuperación completa de Windows/configuración/certificado.
