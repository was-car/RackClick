# C2 · ediciones rápidas y respuestas tardías

25.10.2026. Se protegió la vía `instant` de `InventoryPanel`, utilizada por Subir/Bajar, arrastre, Click-Click, reconexión y desconexión. Conserva la instancia, API, usuario y cliente originales; después de cada espera comprueba ese contexto antes de continuar. Un cambio observado A→B→A no recupera una instancia invalidada.

Antes de enviar comprueba revisión y autoridad observadas. Un mutex evita dos acciones antes del render; una intención todavía pendiente impide otra edición rápida hasta que su registro desaparezca tras resolverla. La operación original mantiene cuerpo, clave, actor y ETag. Una respuesta tardía no limpia una intención incierta ni marca otra vista como guardada. La limpieza de una terminal ya confirmada puede retirar únicamente su registro original, sin callbacks posteriores en otra vista.

También se protegieron las continuaciones de lectura, revisión, candidato de Deshacer, lista de pendientes y reconexión. Una lectura antigua del journal que falla no sustituye una lectura posterior correcta. Un error al preparar la operación queda contenido y libera el estado ocupado. El refresco de su propio pendiente no bloquea el primer envío.

## Pruebas y resultados

- Fuente inicial: **1 PASS/8 FAIL esperados** entre nueve casos nuevos. Tras la primera corrección pasaron9/9.
- Un décimo caso reprodujo una ventana restante: después de una respuesta incierta, otra acción podía entrar antes del render (dos envíos en vez de uno). Se conservó esa fuente intermedia y se añadió la guarda de intención pendiente. Final:10/10PASS.
- Regresión focal final: **52/52Node**, sin omisiones. Incluye los diez nuevos; no son otros diez adicionales.
- Revisión independiente: cinco focos propios PASS, con controles negativos sobre las fuentes inicial e intermedia. No ejecutó navegador/PostgreSQL y no se le atribuyen esos ensayos.
- Edge/HTTP/PostgreSQL17.11 nuevo: **PASS21,34s**. Reordenación real con respuesta retenida, cambio de cuenta y recuperación del recibo por el usuario original sin repetir la escritura. Después, solicitud detenida antes de llegar al servidor, cancelación durable y nuevas ediciones en el mismo panel, sin bloqueo permanente.
- Regresión de revisión/permisos: **PASS28,34s**, incluida revocación real de membresía y rechazo de escritura directa. Ambos ensayos comparan exactamente nueve tablas de inventario y verifican persistencia al reiniciar el proceso servidor. Clusters/procesos propios detenidos.

Frontend privado `0df395a6…`, CSS conservado; DLLC2 `5eb1abcf…` reutilizada, sin recompilar .NET. Sin cambios de MFA/backend/SQL, dependencias, instaladores, paquetes, W-02, QA/VM ni commits. Wascar informa que Claude trabaja en dos VM; todavía no se acredita aquí ningún resultado de ese ensayo. No incorporar automáticamente este árbol C2 a07.

QA-117 queda **planned**, con pasos de Subir/Bajar, recarga, otra cuenta y recuperación. Los116 casos anteriores y metadatos se conservan; ambas guías regeneradas sin resultados personales. La disponibilidad requiere una candidata integrada identificada.

**I-01.03 sigue parcial** por capacidades específicas/matriz completa e integración/aceptación. No se afirma probada cada combinación de arrastre, Click-Click o reconexión por verificar el camino compartido; el navegador de esta tanda ejercita reordenación. **Delta0: cierre del pendiente3,57/100,8/280subpasos y1/50resultados completos**; pesos/alcance intactos, no porcentaje global.

[Evidencia y comandos](../evidence/s1-20261025/c2-instant-codex/CIERRE.md) · [Revisión independiente](../evidence/s1-20261025/c2-instant-codex/REVISION.md).
