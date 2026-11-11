# C2 · operaciones pendientes y cambio de contexto

25.10.2026. Desarrollo y laboratorio Windows en LEAO. Sin despliegue, instalación, cambios en QA/VM ni commits.

El diálogo de inventario conserva su usuario, cliente y API originales. Enviar, reintentar, cancelar y actualizar vuelven a comprobar ese contexto después de cada espera relevante. Si cambia la cuenta o el cliente, o se desmonta el diálogo, una respuesta antigua no confirma ni cierra una operación de la vista siguiente. Un recorrido observado A→B→A tampoco reactiva el borrador anterior. `InventoryPanel` se monta con una clave de usuario y cliente.

Una intención incierta conserva el registro local original. El usuario original puede volver y consultar el resultado del servidor sin repetir la escritura. Si ya se recibió un resultado definitivo, la limpieza puede eliminar únicamente su registro original; no autoriza callbacks en otro contexto. Un callback iniciado antes del cambio no se cancela universalmente con esta guarda.

## Cambios y comprobación

- Producto: `OperationDialog.jsx` y la clave de `InventoryPanel` en `ServerApp.jsx`. Sin cambios de autenticación, MFA, API del servidor, SQL, estilos ni dependencias.
- Pruebas nuevas: 11 casos con promesas controladas y una prueba de Edge/HTTP real. El auxiliar Python admite dos escenarios mediante una lista cerrada y conserva el anterior como predeterminado.
- Control negativo contra la fuente anterior: 4 PASS / 7 FAIL esperados. La primera repetición contra la corrección tuvo dos fallos del harness: asignaba una referencia DOM a un controlador de aborto. Se corrigió el observador, no el producto para satisfacerlo; repetición final 11/11.
- Regresión focal final: **36/36 Node**, sin omisiones. Incluye los 11 nuevos y 25 casos pertinentes anteriores.
- Revisión independiente: encontró un rechazo que escapaba de la limpieza tras un error definitivo. Corregido; **9/9 casos propios** y 11/11 del autor repetidos por el revisor. Estos 11 son una repetición, no pruebas adicionales distintas.
- Edge 156 / PostgreSQL 17.11 nuevo: **PASS, 20,81 s**. Se retuvieron respuestas reales de envío y cancelación después de su confirmación en el servidor; se cambió la cuenta y se liberaron. Sin callbacks tardíos para el siguiente usuario, registro original conservado y consulta posterior correcta por su propietario. Nueve tablas de inventario quedaron exactamente como al principio y se verificó persistencia tras reiniciar el proceso servidor.
- Regresión de consulta anterior sobre el mismo frontend final: **PASS, 24,52 s**, mismas comprobaciones SQL/reinicio. El primer intento del escenario nuevo falló por exigir botones habilitados cuando había una intención pendiente: espera corregida y fallo conservado. No se cuenta como PASS.

Los cambios de cuenta y la pulsación de Actualizar del escenario automático son eventos controlados por el ensayo. No equivalen a QA manual ni a un corte de red imprevisible. Ambos laboratorios y los procesos servidor terminaron detenidos. No se recompiló .NET: se reutilizó la DLL C2 `5eb1abcf…`. El frontend final es `12b6ded4…`; CSS intacto.

## QA y cierre pendiente

QA-115 queda **planificado**, con ubicaciones y pasos por cuenta/cliente. Los 114 casos previos y sus metadatos se conservan; se regeneraron ambas guías sin modificar resultados personales. Este cambio todavía no está disponible en la candidata QA.

I-01.03 sigue parcial: falta cerrar la matriz completa de revisión/permisos y las vías heredadas, además de integración coordinada y aceptación. No se acredita reautenticación/MFA ni instalación. **Delta de crédito: 0; cierre del pendiente 3,57/100, 8/280 subpasos y 1/50 resultados completos.** Es el índice del trabajo restante fechado, no porcentaje global del producto. Pesos y alcance intactos.

[Evidencia y comandos](../evidence/s1-20261025/c2-context-codex/CIERRE.md) · [Revisión independiente](../evidence/s1-20261025/c2-context-codex/REVISION.md).
