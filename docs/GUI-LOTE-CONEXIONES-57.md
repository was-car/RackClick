# Grupo57 · lote atómico de conexiones

Implementación: botón en InventoryPanel y componentes ConnectionBatchFields/connection-batch. Usa API existente `connections.createBatch`, un request con array `pairs` de fromPortId/toPortId/color y confirmedReservedPortIds. La GUI selecciona y valida grupoID/tipo/puertoID contra snapshot; el contrato de pares existente no transporta grupo/tipo. El servidor revalida extremos reales/cliente/estado/tipo eléctrico/ocupación y permisos, en una transacción. No se usa gn como identidad ni un bucle de POST.

## Guion manual ES
1. Abre un cliente sintético con permiso de edición. Debajo de la infraestructura/rack, baja a **Conexiones**. Pulsa **Conectar pares explícitos**.
2. En la pareja1, selecciona **Desde · Grupo / tipo** (equipo, grupo, conector y sufijo de ID); luego **Desde · Port**. Cada puerto incluye ruta, tipo, estado y sufijoID. Haz lo mismo en **Hasta**.
3. Pulsa **Añadir pareja** y selecciona los dos extremos de la pareja2. Los números pueden repetirse entre grupos: compara ruta/grupo/tipo/ID. **Retirar pareja** elimina solo esa fila del borrador.
4. Revisa la lista **Parejas seleccionadas** debajo: cada extremo incluye ruta, tipo e IDs completos del grupo y puerto, visibles con salto de línea. No debe omitir extremos ni seleccionar por número. Para puertos reservados marca **Confirmo conexiones a los puertos reservados seleccionados**. Cambiar un extremo limpia esta confirmación.
5. Pulsa **Guardar**. Solo después de commit se cierra el diálogo y aparece **Guardado por el servidor**. Deben aparecer todos los cables; rechazo no guarda ningún par.
6. Si otra cuenta cambió el cliente, se muestra conflicto, borrador conservado y guardar bloqueado. **Cargar datos actuales** exige revisar los extremos de nuevo. Si un extremo está ocupado/deshabilitado/defectuoso, no debe guardarse el lote.
7. Si se pierde respuesta, usa **Recuperar operación pendiente** y **Reintentar confirmación**; no crees otro lote. Conserva exactamente usuario/cliente/UUID/cuerpo/revisión. Cancelar pendiente no deshace un lote ya confirmado.
8. Recarga y consulta desde otro usuario autorizado: mismo número de cables, mismos extremos, sin duplicados. Ningún cable/puerto ajeno cambia.

El diálogo muestra vista previa local de pares, no promete preview de impacto del servidor para altas. Hasta128pares por request, las compatibilidades/autoridad finales son del servidor. RC9 Click-Click permanece disponible.
