# Punto2 · candidata de aplicación43 ·02.11.2026

**Consolidación de aplicación terminada; instalación Windows43 pendiente.**

Se reutiliza el freeze del punto1.37 fuentes backend y38 frontend deMFA/administración coinciden con la candidata10 y el árbol vivo: [contraste independiente](CONTRASTE-MFA-ADMIN.md). No se importan cambios concurrentes ni se modifican módulos del producto. Se añaden perfil43 y pruebas; se amplía sólo el generador y verificador de aplicación, manteniendo perfiles históricos.

## Evidencia ejecutada por el coordinador

-Publicación SDK10.0.401,Release,sinapphost,`--no-build --no-restore`, con binlog privado:10 archivos de aplicación/43SQL, mismoSHA de DLL y frontend del punto1. DLL `0d7fbfd28ee15c7b2911c4be0c2aca57a45b2a0067cdac3c02e8bbb419b6d411`; app `35a772565bfc078af3b4cc4ee89d3b43abfc1047bdfe864a1fedfb18c63604fe`.
-Generador: el positivo43 falla antes por perfil no admitido y pasa después. Lector nativo pasa de rechazo de43 a `artifacts_verified` para el único digest autorizado. [Rojo](GENERADOR-ROJO.txt), [antes](NATIVO-ANTES.json), [después](NATIVO-DESPUES.json).
-Regresión de distribución:33/33,0omisiones, conWindowsPowerShell5.1 y candidata real.17 pruebas nuevas43 y16 existentes15; no son33 nuevas. Faltantes/alteraciones/extras/digest desconocido/manifiesto rehecho rechazados e histórico15 conservado. [Salida](PRUEBAS-DISTRIBUCION.txt).
-Nuevo PostgreSQL17.11 con la publicación real: bootstrap43/868definiciones,7tablas de catálogoSELECT-only, creación deAruba29puertos, frontend servido exacto, administración y estado propioMFA, lector403 sin modificación, segunda sesión y reinicio del proceso. Proveedor normal desactivado explícitamente; no se activan políticas. [Recibo](PUBLICACION-PG.json).
-ComposiciónMFA/administración sobre los mismos ensamblados y frontend de la candidata:18/18,0omisiones. Incluye gestión/permisos y3HTTP+1Edge,8etapas GUI, con proveedor sintético sóloDI yHTTPloopback. [Recibo](MFA-COMPOSICION.json), [Edge](MFA-EDGE.json). No se usa SID de servicio ni se acreditaHTTPS/reinicioWindows.
-No se repiten suites995Node/35C# ni catálogo124caras del punto1 al publicar los mismos bytes. La comparación íntegra de archivos,43SQL y hash deTestAssembly mantiene la atribución; no se presentan pruebas antiguas como nuevas.

Los nuevos laboratorios y procesos se detuvieron. Logs completos,TRX,binlogs y credenciales aleatorias permanecen en.local, fuera del paquete. Se conserva el fallo de exportación documental por intentar decodificar una salidaUTF8 comoUTF16: se corrigió la lectura porBOM, sin ejecutar otra vez ni alterar el resultado nativo.

## Integridad, revisión y entrega

Manifiesto `eb274f1f82deb9936c69214fae07e4188275063cf35ec775fe41d560a1806830`;71archivos/25.484.815bytes,53servidor+18frontend. El lector sólo admite este pin para43. Los perfiles14/15 y sus manifestos no cambian. [Revisión independiente](review/REVISION.md): inventario/SHA y cuatro focos propios; no ejecutóPG niMFA.

`RackClick-Candidata43-Revision-01.zip`:82entradas/3.439.456bytes;SHA256 `af1c54b288ecbf5dd42ee6db138979254817a31665a2b36e5b642ed19f554808`. Incluye71archivos de aplicación y auxiliares de revisión, con licencias completasNpgsql/Otp.NET comprobadas contra el lock14. SinDB,dumps,cuentas,claves,runtimePostgreSQL/.NET,instalador o binlogs. La receta de archivo usa entradas fijas y fechaZIP fija; se requiere el freeze local identificado para reconstruirlo. La revisión delZIP se registra por [adenda](review/ZIP.md), conservando el primer dictamen.

## Límites y pendientes

-El ZIP es de revisión de aplicación, no un instaladorWindows aprobado ni una actualización para la VM. New/Restore/Stage/OfflineBundle/runtimes siguen cerrados en sus perfiles anteriores. El punto5 debe propagar43 y revocarDML sobre7tablas de catálogo; sin ello, la creación dehardware da503porpermisos.
-RecuperaciónMFA integral/rotación/códigos/emergencia, base50clientes, backup/importexport web,Windows/HTTPS/servicio/reinicio y QA/adopción siguen sus puntos de hoja de ruta. No se inventan nuevas funciones o resultados de cierre.
-PDB contienen rutas/símbolos de desarrollo; reproducción binaria desde otro directorio no demostrada. Licencias de las dependencias de aplicación incluidas; la revisión general de redistribución de los runtimes/instalador se mantiene abierta.
-Sin VM,QA,servicios instalados,commits,push o publicación. No se encienden/apagan máquinas ni se leen credenciales del servidor. Índice de cierre restante9,76/100 intacto; no es porcentaje global. Catálogo seleccionado506/506 en desarrollo no equivale a adopción.

[Manual del punto2](../../../docs/CANDIDATA-CONSOLIDADA43.md) · [Investigación previa](INVESTIGACION-PREVIA.md).
