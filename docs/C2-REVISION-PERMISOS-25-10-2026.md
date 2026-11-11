# C2 · borradores ante revisión y permisos observados

25.10.2026. Una revisión nueva conocida o una pérdida de escritura/acceso ya observada bloquean la preparación y el primer envío del diálogo abierto. Los campos y el envío se deshabilitan con explicación; cargar datos actuales sigue siendo una acción explícita. No se sustituye automáticamente el snapshot ni se renueva un Deshacer antiguo.

`InventoryPanel` conserva la revisión máxima recibida por los avisos y la transmite, junto con la autoridad observada, a `OperationDialog`. El diálogo comprueba elegibilidad antes y después de preview, después de guardar el journal y antes del primer envío. Si la intención ya quedó registrada, conserva cuerpo, actor, clave y ETag originales. Consulta y cancelación siguen resolviendo esa intención bajo autorización del servidor; una revisión posterior no las convierte en otra escritura. La pérdida de escritura bloquea el reintento, pero no borra la intención.

## Comprobación real

- Control negativo nuevo contra la fuente anterior: 12 PASS / 5 FAIL esperados. Con la corrección, 17/17 casos del diálogo pasan; regresión focal completa **42/42 Node**, sin omisiones.
- Revisión independiente: **5/5 negativos propios PASS** y tres controles fallan contra la fuente anterior. Su primer fallo fue una regex del observador, corregida y documentada; no se atribuye al producto.
- Edge / PostgreSQL17.11 nuevo: **PASS,31,27s**. Otro administrador confirma un cambio, el aviso invalida el diálogo abierto y ni un submit controlado prepara/envía la operación. Después revoca realmente la membresía del usuario original: el canal recibe denegación y el diálogo bloquea escritura. Una petición HTTP directa también es rechazada por el servidor, sin depender de los botones. Se restablece la membresía únicamente en ese laboratorio.
- Regresión de cambio de cuenta y respuestas tardías: **PASS,20,45s**, sobre el frontend final. En ambos escenarios se comparan exactamente nueve tablas de inventario y se comprueba persistencia tras reiniciar el proceso servidor. Clusters y procesos propios detenidos.

Frontend privado `98086c07…`, CSS conservado; DLLC2 `5eb1abcf…` reutilizada. No hay compilación .NET, cambios de MFA/backend/SQL, dependencias, W-02, paquetes, instalación, QA/VM ni commits. Los datos son sintéticos; no se publican contraseñas ni tokens. Los eventos programáticos del ensayo no sustituyen QA manual.

QA-116 queda **planned**, con pasos por botón para dos perfiles. Los115 casos anteriores y demás metadatos se conservan; ambas guías regeneradas sin escribir resultados personales. Pendiente integración antes de habilitarlo en QA.

## Límite y seguimiento

El guardado sigue siendo autorizado por el servidor. La señal local de escritura cubre `inventory.edit` y la pérdida de acceso del canal; no toda capacidad específica, por ejemplo `inventory.delete`, ni revocaciones todavía no observadas. Quedan la vía heredada `instant`, la matriz completa y la candidata coordinada/aceptación. No se acredita autenticación/MFA ni instalación.

**I-01.03 parcial, delta0: cierre del pendiente3,57/100;8/280subpasos y1/50resultados.** Pesos/alcance intactos; no es porcentaje global del producto.

[Evidencia y comandos](../evidence/s1-20261025/c2-eligibility-codex/CIERRE.md) · [Revisión independiente](../evidence/s1-20261025/c2-eligibility-codex/REVISION.md).
