# C2 · duplicado sin cables y reserva confirmada

25.10.2026 · I-04.03. Se completa la comprobación de variantes existentes, sobre la DLL C2 y el frontend privado ya identificados. No se necesitó cambiar la lógica del producto ni reconstruir artefactos.

## Qué se verificó

- **Sin cables:** aunque el rack fuente tenga un extremo reservado conectado y otro reservado suelto, elegir No no exige confirmarlos. Se copian rack/equipos/grupos/puertos con UUID nuevos y atributos exactos, sin añadir conexiones.
- **Con cables y reserva válida:** Sí presenta la casilla obligatoria. Intentar guardar sin marcarla no envía POST ni cambia proyecto, revisión o auditoría. Al marcarla, el comando confirma exclusivamente el UUID original del puerto reservado que participa en el cable interno; no incluye el reservado suelto, el externo ni UUID de la copia.
- Sólo se duplica el cable interno, con extremos nuevos y atributos conservados. El cable externo permanece en el original; la copia del puerto que estaba unido al exterior queda sin cable.
- Grupos distintos con `gn=1` no se confunden: la correspondencia se hace por UUID de equipo/grupo/puerto. Las dos copias y el original tienen conjuntos de UUID disjuntos.
- Recarga, segunda sesión autorizada y lectura tras reiniciar el proceso servidor conservan el proyecto y los datos exactos. Dos copias producen exactamente dos operaciones, dos commits de auditoría y dos incrementos de revisión.

La prueba inicial usa SQL para preparar datos ficticios; las dos duplicaciones se realizan por GUI. No se afirma un alta GUI de toda la preparación ni un nuevo circuito físico.

## Resultado

1. Prueba existente repetida, **PASS 33,469 s**, Edge/PostgreSQL 17.11: copia con cables y cuatro rechazos 409 (reserva sin confirmar, confirmación ajena, disabled y faulty), dos denegaciones 403/404 y aislamiento entre clientes 404. Cada rechazo deja iguales inventario, cliente/revisión, operaciones y auditoría.
2. Variantes nuevas, **PASS 23,219 s**, mismo frontend/DLL: sin cables y reserva confirmada válida. Comparación completa de nueve tablas, extremos y atributos, con recarga/otra sesión/reinicio; laboratorios y servidores propios detenidos.
3. Revisión distinta: **3/3 pruebas propias de sensibilidad del comparador SQL**. Rechaza atributos alterados, UUID reutilizados y extremos cambiados; el esperado deriva del estado inicial y los mapas, sin copiar atributos arbitrarios del resultado.

Se reutilizan `app.js` `c357d447…0990e`, DLL `5eb1abcf…7585` y CSS sin cambios. Los ensayos usan Windows y PostgreSQL real, no SQLite/Docker. No se incorporan al instalador 08 ni al QA actual.

[Evidencias, comandos y revisión](../evidence/s1-20261025/c2-duplicate-variants-codex/CIERRE.md). Se acredita sólo I-04.03 con su peso fijo 5/14; I-04.04–07 siguen pendientes. QA-122 queda planned, complementando QA-26 sin alterar sus resultados anteriores.
