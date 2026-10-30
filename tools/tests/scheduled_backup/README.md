# Backup automático: pruebas del wrapper

Ejecutar `Test-RackClickScheduledBackup.ps1` con **Windows PowerShell 5.1**. Crea un directorio de prueba nuevo privado bajo `.local`, conserva su resultado JSON y no inicia PostgreSQL. Son nueve comprobaciones: Unicode en rutas, contrato JSON del hijo, rechazo de JSON roto, salida nativa fallida pese a JSON de éxito, hash inválido, stderr inesperado, exclusión por lock real, reutilización del lock y reemplazo atómico real del recibo en PS5.1.

El guion extrae las funciones reales del wrapper mediante su AST, sin ejecutar su entrada principal. Las comprobaciones de locks y archivos usan el sistema Windows real; las respuestas de procesos son fixtures deliberados. No representan pruebas PostgreSQL ni del Programador de tareas.

Ensayo adicional del implementador, 19.10.2026: fixture aislada autorizada `installer-diagnostic-2b5a802fc3e4483ab123cab22206e3d2`, Windows PowerShell 5.1, runtime TLS LAN existente en puerto 51077 y PostgreSQL 51076. Arranque real, wrapper real, recibo `latest-backup.json` coherente, backup manifiesto/dump verificados con el lector original y parada limpia de aplicación/PostgreSQL. Exit 0. Un hash de perfil incorrecto devolvió JSON de fallo y exit 2, sin tocar el último recibo positivo. No se cambiaron servicios, tareas, firewall, confianza TLS ni la QA de Wascar.

Backup real conservado: `runtime/backups/daily-20261019T200522050Z-ba98694a3a1c4f3b90b66718899a8299`. SHA256 del manifiesto: `eb7f20197e8ee5ae91808eb76ecf009425d34218e4f5a64bfebb9414c282a222`. No se ha restaurado esa copia en este bloque.

Interfaz operativa: `Invoke-RackClickScheduledBackup.ps1 -ManifestPath <perfil absoluto> -ExpectedManifestSha256 <hash retenido>`. Debe ejecutarse bajo la identidad Windows fijada en el perfil. No registra tareas ni eleva privilegios. La configuración horaria/credencial del Programador corresponde al broker. No aplica retención ni borra copias.

`latest-backup.json` indica el último intento que consiguió el lock; una ejecución concurrente falla sin sobrescribirlo. Un error posterior a conseguir el lock publica un recibo negativo, conservando los archivos de copias anteriores. Salida 0 exige creación, verificación y publicación coherente; una copia local no protege contra pérdida del disco y no equivale a una recuperación completa del servidor.

Incidencia del guion de pruebas: el primer archivo UTF8 sin BOM no se interpretó correctamente en PS5.1 por sus literales Unicode; se fijó UTF8 con BOM y se repitió con nueve PASS. No se alteraron versiones de herramientas ni código de producto.
