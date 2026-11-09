# Paso 12 · permisos efectivos del almacén MFA

03.11.2026 · **F-04.02 completado técnicamente y revisado de forma independiente.** D se conserva sin operaciones dentro de ella.

Se reutilizaron las dos instalaciones de E y sus cuentas estándar de servicio. No se reinstaló, no se crearon usuarios ni claves y no se repitió el login MFA. La sonda comprobó la vinculación servicio/proceso/SID y ejecutó las aperturas con ambos tokens reales.

## Resultado real en E

- 30 objetivos por cuenta: padres comunes y privados, almacenes MFA propios/ajenos y management, incluidos sus 14 archivos.
- **504 comprobaciones correctas:** 16 lecturas propias/comunes permitidas, 44 lecturas ajenas o de management denegadas y 444 solicitudes de modificación denegadas. Todas las denegaciones fueron `ERROR_ACCESS_DENIED` (5); cero resultados inconcluyentes o concesiones inesperadas.
- Propietarios, herencia, protección y ausencia de redirecciones contrastados. La sonda sólo abrió identificadores: no leyó contenido de claves ni escribió o cambió permisos en los objetivos.
- Metadatos nativos de 32 nodos y ACL de los 30 objetivos sin cambios antes/después. Los dos servicios conservan estado Running/Auto y sus PID. La tarea temporal SYSTEM terminó con salida 0, fue retirada y su ausencia se confirmó por una consulta posterior.

Cuatro descriptores tienen distinta serialización entre PowerShell y el lector nativo: sólo cambia el orden de las dos concesiones Allow para SYSTEM/Administradores. Se contrastaron sus permisos equivalentes y la estabilidad antes/después con cada API; no se afirma igualdad de esos bytes entre APIs.

## Registro y siguiente paso

La revisión independiente es favorable al criterio original de F-04.02. Se acredita únicamente **5/8 = 0,625 puntos**: el índice de cierre restante pasa de **15,38 a 16,01/100** (exacto 2689/168). No es un nuevo porcentaje global del producto ni aceptación final de Wascar.

**No necesitas ejecutar ningún comando para este paso.** El siguiente es el **13/F-04.04**, revisión del resultado F-04 completo, reutilizando esta evidencia. La recuperación portable, rotación, incorporación del escritor corregido a una candidata completa y sus ensayos mantienen sus propios pasos.

[Resultados y límites](../evidence/s1-20261103/f04-02-permisos/ejecucion/RESULTADOS.md) · [Revisión independiente](../evidence/s1-20261103/f04-02-permisos/ejecucion/review/DICTAMEN-F0402.md) · [Resultado consolidado](../evidence/s1-20261103/f04-02-permisos/ejecucion/RESULTADO-CONSOLIDADO.json).
