# Grupo58 · notas, color, patch y desconexión

Trayectoria existente integrada en InventoryPanel/OperationDialog y API connections.update/disconnect; esta tanda añade evidencia nativa y mensajes explícitos de errores comunes, sin cambiar DTO o identidades.

## Guion manual ES
1. En cliente sintético, baja a **Conexiones**. Pulsa una tarjeta de cable. Debajo, en **Cable seleccionado**, comprueba sus dos rutas y pulsa **Editar**.
2. En el diálogo, escribe **Nota del cable** multilínea con texto literal `<img>` y Unicode. Escribe **Color** con formato `#12ab34`; en **Estado de patch**, prueba separadamente **Sin documentar**, **Planificado**, **En curso**, **Terminado**, **Probado**, guardando cada vez.
3. Tras cada **Guardar**, espera cierre y **Guardado por el servidor**. Reabre: nota, color y estado exactos, mismo cable/extremos. No debe ejecutarse HTML ni aparecer una imagen creada por la nota.
4. Con el editor abierto en sesiónA, cambia el cable desde sesiónB. GuardaA: conflicto conserva los campos y bloquea el envío hasta **Cargar datos actuales**. Revisa el cable actual y guarda explícitamente el borrador deseado.
5. Recarga y abre desde otra cuenta con lectura: mismas propiedades y extremos. Cambiar color no altera estado/nota ni atributos de los puertos.
6. En **Cable seleccionado**, pulsa **Desconectar**. En la confirmación del navegador, **Cancelar**: ningún cambio. Repite y acepta: solo desaparece ese cable; los puertos y equipos permanecen.
7. Actualiza la segunda sesión: también desaparece ese cable. No confundir confirmación del navegador con éxito persistido; el mensaje de guardado llega después del commit.

Evidencia incluye rollback ante patch inválido con inventario/revisión/operación/auditoría intactos y reinicio de ASP.NET en fixture nuevo. No reinicio de Windows, ni aceptación visual completa del diseño RC9.
