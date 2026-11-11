# Paso 14 · F-05.01 · validación del sobre RCKEY

03.11.2026. **Cerrado con revisión independiente favorable.** Se reutilizó evidencia existente antes de decidir que no hacía falta implementar otro codec. No se cambió código de aplicación, dependencias o formato; cero compilaciones, pruebas criptográficas nuevas, sobres nuevos u operacionesVM/DB/cuentas/servicios. D y E conservadas sin operaciones.

## Contraste y decisión

[Investigación](INVESTIGACION-Y-DECISION.md) y [matriz](MATRIZ-CRITERIO.md) relacionan el criterio original con las validaciones actuales: tamaño antes de KDF; magia/versión/algoritmos/longitudes exactos; enteros big-endian; perfil v1 mínimo=máximo600000; contraseña en UTF-8 estricto; metadata0..42 como AAD y etiqueta GCM separada. No se cambia el coste por consultar documentación ni se afirma una medición universal.

La canonicalidad queda delimitada: cabecera binaria fija y salida canónica de L2e. Su lector acepta variantes JSON válidas del parser, sin exigir igualdad byte a byte con la salida. El contenido cifrado se analiza después de autenticar; no se promete validarlo antes de KDF. NFC/NFD siguen siendo contraseñas distintas, sin normalización silenciosa.

## Evidencia existente comprobada

- Codec `8a7b06ee0441086c40aba3cc8735c21fc562eee08383a58e6ed169b01b7d7fe1` y pruebas `5d15b220d6d12cfe9ab8e340fe39a8e902b47f609af434989f84db96060e4a1f` idénticos a L2d. Payload, sus pruebas y parser conservan las otras tres identidades verificadas.
- L2d26.10:26pruebas repetidas y8controles independientes PASS, sin fallos/omisiones, SDK10.0.401. Incluyen referencia con offsets literales en ambos sentidos y rechazo de tag calculado sin AAD. Mismo motor .NET, no otro backend o vector público.
- L2e26.10:28pruebas repetidas y8controles independientes PASS. Su alcance de serialización/análisis y límites se conserva; no acredita recuperación real.
- `CONCILIAR-EVIDENCIA.py`, Python3.12, salida0:25referencias y cinco fuentes actuales. Sellos históricos7/7 y7/7 correctos; resultados/códigos de salida contrastados. `SALIDA-VERIFICACION.json` conserva la segunda comprobación de referencias. No se reabren binlogs, TRX privados, claves o credenciales.

Esos resultados son históricos y **no se presentan como ejecuciones nuevas** de este lote. La observación57–62ms del autor se conserva con su fecha/equipo; no se usa aquí para acreditar F-05.02. Se preservaron configuraciones/documentos iniciales y el sello del paso13 se contrastó antes de modificar planes, sin reescribirlo.

## Revisión independiente y cierre

[Dictamen F-05.01](review/DICTAMEN-F0501.md), revisor distinto del autor y coordinador: favorable, sin bloqueo material ni nuevas suites necesarias. Su [verificador](review/Verify-F0501-References.py) terminó en0; [comprobación](review/COMPROBACION-F0501.json) registra referencias, constantes y límites. No modificó producto/ledger ni operó VM/DB/material privado.

Sólo **F-05.01** recibe **1/2 punto**:1397/84→1439/84 =**17,13/100 del cierre restante**.37checkpoints cerrados/243sin cierre (241pending,2in_progress), con53resultados/280checkpoints/268números, pesos y criterio congelado intactos. **F-05 completo permanece abierto.** No es porcentaje global nuevo del producto ni adopción de Wascar.

Se actualizan ledger, contexto maestro, plan numerado, progreso y changelog. La afirmación antigua «no implementado» se sustituye por el estado real de los componentes, sin acreditar sus operaciones finales. Tres generadores en write/check, verificación del cambio exclusivo, escaneo de selección y sello final quedan registrados. No hay cambio visible o de disponibilidad QA; casos/resultados de Wascar intactos. Sin commits ni push.

Siguiente **15/F-05.02**, contrastar primero la medición Windows existente. F-05.03/.04/.05, recuperación portable real, AAD de factores en otroWindows, rotación/códigos/emergencia, candidata completa y aceptación final conservan sus propios criterios. Los límites de lectura/materialización del operador, memoria y durabilidad no se resuelven mediante este codec en memoria.
