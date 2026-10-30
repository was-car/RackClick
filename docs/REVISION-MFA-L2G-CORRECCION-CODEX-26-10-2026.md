# Revisión de corrección MFA-L2G-01

**Dictamen: MFA-L2G-01 corregido; L2g aceptado en el alcance de laboratorio.** La identidad publicada queda ligada a la retención de lectura y el sustituto idéntico ya no produce éxito. No se exige conservar el identificador de renombrado con DELETE.

## Ejecución nueva de Codex

**125 archivos congelados y16 hashes contrastados**. Restore locked/build Release SDK **10.0.401**, **0 errores/0 advertencias**.

| Grupo | Resultado |
|---|---|
| Focos del autor: recuperación19 + archivos34 | **53 PASS** |
| Cuatro negativos/controles originales de Codex, sin modificar | **4 PASS** |
| Dos controles adicionales de retención | **2 PASS** |

**59 PASS, sin fallos u omisiones;23,907s** para restore/build y los grupos. El negativo original había fallado en la referencia anterior; ahora pasa sin cambiar su expectativa. Los nuevos controles comprueban File.Replace durante retención (con control positivo sin bloqueo) y que intentar sustituir la carpeta padre no dé éxito con un archivo ajeno. No se repitieron las mutaciones anteriores o la regresión completa.

[Resultados](../evidence/s1-20261026/mfa-l2g-correccion-codex/RESULTADOS-EJECUTADOS.json), [fuentes](../evidence/s1-20261026/mfa-l2g-correccion-codex/FUENTES-ENTREGADAS.json), [controles originales](../evidence/s1-20261026/mfa-l2g-correccion-codex/MfaL2gIndependentReviewTests.cs), [controles nuevos](../evidence/s1-20261026/mfa-l2g-correccion-codex/MfaL2gCorrectionHoldReviewTests.cs), [cierre](../evidence/s1-20261026/mfa-l2g-correccion-codex/CIERRE.md).

## Decisión y límites

Se acepta cerrar el handle de renombrado y abrir uno de lectura: compara la identidad esperada antes de llamar al lector, mantiene GENERIC_READ/FileShare.Read durante sus comprobaciones y repite la identidad sobre el mismo handle. No es una comparación seguida de lectura libre. Las aperturas de lectura son compatibles. El archivo distinto se rechaza y la limpieza por identidad conserva el ajeno.

La ventana rename→retención sigue existiendo: un sustituto en ella se rechaza, pero un original movido a una ruta desconocida no se busca. El residuo con la ruta registrada no identifica la ubicación actual del original; **no significa limpieza completa**. No se exige buscar/borrar por prefijo o recorrer el volumen. Mantener esta precisión en el futuro operador.

Fuente de apoyo del subrevisor distinto confirmó la corrección/diff y compatibilidad read/read, sin pruebas propias. Su comunicación quedó registrada; la notificación final terminó por capacidad del modelo y no se le atribuye otra revisión o ejecución. El dictamen y las pruebas anteriores son de Codex, independiente del implementador.

Cinco binlogs/logs/TRX privados; fuentes compartidas/congeladas y ocho documentos protegidos intactos. Durabilidad del directorio, custodia externa, exclusión de backups y SID efectivo siguen pendientes. Sin producto editado por Codex, dependencias, PostgreSQL/HTTP, cuentas/servicios, instaladores, VM/QA, commits/push o GitHub.

[Siguiente lote L2h](MENSAJE-PARA-CLAUDE-MFA-L2G-CORREGIDO-26-10-2026.md): selección de versión activa en el backend antes de componer el proveedor real con el host. No habilitar MFA en QA. **Índice del cierre pendiente7,63/100**, sin crédito nuevo de custodia productiva ni porcentaje global recalculado.
