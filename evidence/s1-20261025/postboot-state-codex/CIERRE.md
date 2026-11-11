# Postboot · corrección de la presentación del estado

25.10.2026. **Conforme en desarrollo tras revisión independiente; candidata y ensayo en VM pendientes.** [Corrección](../../../docs/CORRECCION-ESTADO-POSTBOOT-25-10-2026.md), [coordinación para Claude](../../../docs/MENSAJE-PARA-CLAUDE-POSTBOOT-ESTADO-25-10-2026.md).

Se conservan el resultado histórico del broker y sus bytes. La proyección `installationState` recoge una verificación registrada del UUID y arranque correspondientes sin afirmar salud actual ni adopción. Se preservan GUID y fechas tipadas que antes se eliminaban del informe saneado. El panel distingue ese registro al reabrirse, mantiene 95 y exige una nueva comprobación completa antes de 100.

## Ejecuciones reales del autor

Windows PowerShell 5.1 x64 en LEAO; fuentes de desarrollo y fixtures privados. Directorio `.local/postboot-state-8ddb1c7b0e864a709c096069574a04c7/`.

- **Rojo:** `Test-PostbootRecordedState.ps1` sobre las fuentes anteriores: salida 1, `Postboot report loses binding metadata: installationId`. Salidas stdout/stderr conservadas.
- Primer verde 36: política/saneador y comprobación del panel. Después se añadieron los controles de inicio de llamada y archivos.
- Segundo verde 43: incluye lectura de archivos nativos, estado separado, fallo posterior a positivo, JSON malformado, nuevo arranque y UUID cruzado.
- **Final 45:** incluye además el manejador real del botón con lanzamiento fallido simulado y el colector principal/exportación ZIP reales. El resultado original queda byte a byte intacto en las lecturas. Los secretos sintéticos no aparecen en el informe.
- Regresión pertinente única: `Test-SetupDiagnostics.ps1` **20/20**, `Test-SetupUi.ps1` **36/36**, `Test-SetupAutomaticReport.ps1` **20/20**.

Los comandos usan el PowerShell nativo de Windows con `-NoProfile -NonInteractive -ExecutionPolicy Bypass -File`, `-STA` donde corresponde, y salidas nuevas bajo el directorio privado. [Pruebas y hashes de salidas](EJECUCIONES.json).

## Revisión independiente

[REVISION.md](REVISION.md): siete controles propios sobre funciones puras y AST del manejador, con objetos/lanzador inertes. El revisor reprodujo `POSTBOOT-UI-01`: un nuevo lanzamiento fallido conservaba el 100 anterior. Se bajó a 95, salida interna de fallo y comienzo vacío antes del intento; su mismo foco pasa después. Rojo/verde y fuentes revisadas conservados por separado. Sus siete controles no son repeticiones de los 45 del autor.

## Límites

- No se ejecutó el instalador, reinicio, servicio, tarea programada, HTTPS ni SQL; tampoco operaciones VMware o sobre otra VM.
- La integración de archivos usa el lector, ACL de archivos, saneador, cuerpo completo del colector y escritor ZIP reales. Sólo cambia en la copia de prueba el espacio de nombres de gestión, la identidad administrativa esperada, la vinculación privada no disponible y la fuente CIM. No es prueba de un directorio de producción elevado.
- `result.json`, el código de salida del proceso inicial y `server-installation.json` no se modifican. Un registro postboot no sustituye a una comprobación actual de salud.
- No se volvió a ejecutar el fixture histórico de `Test-SetupLifecycle.ps1`, que todavía fija esquema 13 frente al requisito 14; no se declara verde. Este cambio no altera esa política ni actualiza ese archivo histórico.
- Fuentes de servidor C#/SQL/MFA/C2, helper W02 de Claude, paquetes históricos y laboratorio QA conservados. No builds, empaquetado, commits o publicación.

QA-120 permanece planned, con guía detallada. Los 119 casos anteriores, sus metadatos y resultados personales se conservan; ambas guías se regeneraron. [Controles](CONTROLES.json), [manifiesto](SHA256SUMS.txt).

Próximo bloque: revisar entrega corregida W02-R3 y preparar una candidata coherente con los dos arreglos del instalador. Wascar se ocupa de las operaciones sencillas de VMware/Windows. **Delta 0:** 4,79/100 del inventario restante; 11/280 subpasos, 1/50 resultados; W-02 0,50/2,50. No aceptación final ni porcentaje global nuevo.
