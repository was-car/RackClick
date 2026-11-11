# Revisión explícita de línea base · v2

29.10.2026. Wascar cambia la política anterior de MFA inmediato/configure-first-login a45 días, existentes desde activación y nuevas desde creación, con exención propia del administrador global del Systemhaus. Es un cambio autorizado del resultado prometido; no se modifica silenciosamente una línea base congelada.

Se conserva la v1 completa de JSON, informe Markdown, métrica, mapa y progreso en [baseline-v1](baseline-v1/SHA256SUMS.txt), con sus hashes. Nueva identificación: **RC-CIERRE-20261029-v2**. [Detalle verificable](REBASE.json).

No cambian los53 IDs de tareas,280 subpasos, pesos por tarea/área ni total100. Sólo se revisan título/alcance de F-07 y la primera cláusula de F-07.04 para la política confirmada; se conserva íntegra la cláusula de código erróneo/caducado/repetido, reintento/respuesta perdida y dos confirmaciones concurrentes. El resto del alcance sigue pendiente según su evidencia.

Se acredita únicamente **F-07.04,0,50 puntos**: fechas y rollout persistidos, exención por capacidades globales, enforcement en login/sesiones antes/después de locks, enrolamiento cuando se exige y negativos actuales. Pruebas nuevas con PG17.11 más regresión vigente sobreSQL15, Browser8etapas y Node; revisión independiente favorable en su [adenda](review/REVISION.md).

El índice pasa de **8,13 a8,63/100** (725/84),21/280 subpasos cerrados. No es porcentaje global del producto. No se acredita F-04, F-07.05, recuperación, instalador, QA o producción. No se añade puntuación por pruebas repetidas, artefactos o por disponer de un panel nuevo.
