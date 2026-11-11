# Grupo55 · contexto de auditoría en RC9

Implementación: `AdminAuditContext.jsx`, `admin-audit-context.ts`, integración en `AdminAudit.jsx`. GET de solo lectura `/api/v1/admin/audit/{eventId}/context`, validación estricta del envoltorio/ETag, identidad/fecha/actor/recurso, campos finitos y formas ordenadas. Compatible con DLL54 (sin los dos campos cliente) y DTO7 (campos cliente nullable explícitos). Nombres de actor actuales; UUID histórico independiente. No reconstruye nombres/JSON privado, revisiones faltantes ni objetos indirectos. La revisión House actual del envoltorio no se presenta como histórica. `notRecorded` no significa ausencia de cambios.

## Guion manual ES (solo cuando la guía indique disponible)
1. Inicia sesión como administrador. En la barra lateral izquierda, debajo del árbol de clientes, abre **Usuarios**. En **Crear cuenta**, escribe un nombre sintético y contraseña local nueva; pulsa **Crear usuario**. Espera **Alta confirmada por el servidor**.
2. Arriba en Usuarios pulsa **Volver a clientes**; en la barra lateral izquierda, debajo de **Usuarios**, abre **Auditoría**. En la tarjeta de operación `user.create` correspondiente, pulsa **Ver detalle**.
3. Debajo de los campos administrativos aparece **Contexto registrado del evento**. Compara **ID histórico del autor**, **Ámbito registrado**, **Resultado registrado**, **Revisiones históricas de Systemhaus** y **Objetos directos registrados**. Deben proceder del evento confirmado; el objeto es el ID del usuario creado. El nombre del autor de la tarjeta es actual.
4. Pulsa **Volver a leer contexto**: lee de nuevo, sin escritura ni notificación de guardado. Si falla, se retiran los valores anteriores y aparece un error con reintento.
5. Cierra el detalle mientras carga: ninguna respuesta atrasada debe volver a mostrarlo. Abre desde otra sesión administradora y compara UUID/revisiones.
6. Un evento antiguo puede indicar **El contexto no se registró o no se puede publicar de forma coherente**. No rellenar esos huecos. Eventos de cancelación indican intención bloqueada; no un undo.
7. Para alta/rename de cliente con DTO7, se muestran por separado las revisiones House y cliente. Alta de cliente: **Sin cliente anterior (creación)** → 1, nunca revisión0 inventada.

Límite: no feed de avisos, nombres históricos de recursos ni diff completo; permiso global `security.manage` siempre comprobado por servidor. Habilitación QA depende de pareja exacta, revisión y actualización compatible del laboratorio.
