# Avisos de cambios del cliente · grupo60

**Ampliación428–472:** la candidata472 usa `/changes/details` y muestra resumen de nombres registrados más Antes/Después de entidades, padreUUID, ubicación/orden/grupos. Conserva este polling, borradores, Click-Click y actualización explícita. Nombres históricos distintos del autor actual/etiquetas de la vista. [Contrato, límites y pruebas](API-AVISOS-DESCRIPTIVOS-S1.md); QA63–65 preparados pero no disponibles enQA185. Texto siguiente conserva comportamiento previo compatible.

El cliente abierto consulta cambios confirmados mediante un GET autenticado cada5segundos, sin consultas solapadas. Al ocultar la pestaña se pausa; vuelve a consultar al mostrarla. Los fallos de red conservan los avisos y usan espera creciente hasta30segundos. El cursor es la revisión del cliente, no la fecha del evento. No es una conexión de eventos en tiempo real ni una historia completa.

El aviso aparece **justo debajo de la barra del inventario**, bajo **Gestionar infraestructura**, **Crear Sede**, **Crear Rack**, **Añadir equipo**, **Actualizar** y búsqueda. Su título ES es **Cambios confirmados en el servidor**. No cambia el inventario cargado, la revisión de comandos, el journal, el borrador ni la selección Click-Click. Muestra hasta50eventos de otros usuarios; una advertencia indica más cambios o historia incompleta. No inventa valores históricos ausentes.

## QA10 · recorrido básico con dos técnicos

1. Abre el acceso restaurado mediante su CMD habitual. Usa las cuentas y contraseñas del archivo privado que muestra el lanzador. Para separar sesiones, usa dos perfiles de navegador o una ventana normal y otra InPrivate. Llama **A** al técnicoA y **B** al técnicoB. No compartas una sola sesión mediante pestañas normales del mismo perfil.
2. En **A** y **B**, en la barra lateral izquierda, elige el mismo cliente de pruebas al que ambas cuentas tengan acceso. Espera a que aparezca el inventario. Si ese cliente no tiene edición para ambas cuentas, elige el cliente compartido indicado en el archivo privado; no supongas que un rol da acceso a todos los clientes.
3. En **B**, en la barra horizontal del inventario pulsa **Crear Rack**. En el diálogo escribe **Nombre** = `QA10 borrador B` y deja abierta la ventana sin pulsar **Guardar**.
4. Vuelve a **A**, en el mismo cliente pulsa **Crear Rack**. En **Nombre** escribe un nombre distinto, por ejemplo `QA10 creado A fecha-hora`; deja **Sala** en **Sin asignar** si no necesitas otra ubicación. Pulsa **Guardar**. Solo continúa cuando se cierre el diálogo y aparezca **Guardado por el servidor**.
5. Vuelve a **B** y deja esa pestaña visible. En unos5segundos debe aparecer el aviso debajo de la barra, detrás del diálogo. Su autor es el nombre **actual** deA y su operación es **Rack · Crear**. El campo **Nombre** debe seguir diciendo `QA10 borrador B`; el aviso no guarda ni reemplaza ese borrador. Al estar el modal abierto, el contenido del aviso puede quedar detrás del fondo del diálogo: no debes cerrarlo para demostrar que el campo conserva su valor.
6. Pulsa **Cancelar**, en el pie del diálogo deB. Debajo de la barra ya puedes leer el aviso. Abre **Detalle registrado del cambio**: contiene autor/ID, revisiones y fecha informativa; crear un rack no publica detalles de puertos/cables, por lo que indica **Sin detalle publicado de puertos o cables para este evento**.
7. Pulsa **Actualizar vista**, dentro del aviso. Este botón relee el proyecto únicamente por tu acción. Tras aplicar la revisión nueva, el aviso desaparece y debe aparecer el rack creado porA en **Todos los racks**. No debe existir ningún rack llamado `QA10 borrador B`.
8. RecargaB y vuelve a abrir el cliente. El rack deA permanece. Un lector autorizado puede recibir avisos y releer el inventario; no obtiene botones de edición por ello. Un usuario sin acceso a ese cliente no debe recibir sus avisos.

El botón **Actualizar vista** está deshabilitado mientras existe un borrador, una operación pendiente, una carga/escritura o una selección de equipos o Click-Click/reconexión. El texto explica: **Termina o cancela el borrador, la operación pendiente, la selección de equipos o la selección Click-Click antes de actualizar**. En el modal el fondo es inerte por diseño; usa **Cancelar** para volver al aviso, sin guardar el borrador.

## QA10 · detalle de puerto y conexión

1. Usa la preparación de **QA27** para identificar dos equipos, sus grupos, tipo de conector y puertos concretos. Los números `gn` pueden repetirse en otro grupo: compara grupo y UUID, nunca solo el número.
2. EnB abre el rack y selecciona un puerto libre con un clic. Mantén la selección Click-Click sin completar otra conexión.
3. EnA modifica otro puerto del mismo cliente. En el rack, haz clic derecho sobre el puerto; en el diálogo de **Ports/Puertos**, comprueba el grupo y la casilla del puerto, elige **Cambiar** y su valor y pulsa **Guardar**. Espera **Guardado por el servidor**. No pulses dos puertos enB mientras estás preparando este cambio.
4. Vuelve aB, deja visible la pestaña y espera el aviso **Puertos · Editar**. La selección anterior permanece y **Actualizar vista** queda deshabilitado. Abre **Detalle registrado del cambio** y compara tipo, número, ID de equipo, ID de grupo e ID de puerto registrados. Se muestran referencias antes/después; este MVP no publica todos los valores técnicos modificados.
5. Si aparecen rutas o nombres, el aviso los identifica como **etiquetas de tu vista cargada, no nombres históricos**. Pueden estar antiguos: los IDs registrados son la identidad. Las referencias de conexiones incluyen ID de cable y UUID de ambos extremos.
6. Pulsa **Quitar selección** en la franja Click-Click. Luego pulsa **Actualizar vista** y comprueba el estado actual leído del servidor. Para una conexión nueva o modificada, abre su tarjeta en **Conexiones** y verifica los extremos después de esta lectura.

## Fallos y límites visibles

- Sin red: **No se pudieron consultar cambios. Se conservan los avisos y se reintentará automáticamente**. No se declara guardado por recibir un aviso.
- Sin continuidad del historial: **El servidor no puede ofrecer una historia continua**. Pulsa **Actualizar vista** para leer el inventario actual. Si el servidor se restauró a una revisión inferior a la ya confirmada por esta página, una recarga completa o volver a abrir el cliente restablece la vista; no se rebaja silenciosamente la protección contra lecturas antiguas.
- Sin permiso o cliente: **Avisos detenidos: cliente no disponible o permiso revocado**. Se borran los detalles de los avisos y se detienen las consultas. Para volver a probar tras recuperar acceso, reabre el cliente o la página.
- Sesión terminada: **Avisos detenidos: sesión no disponible. Inicia sesión de nuevo**. Pulsar **Cerrar sesión** suspende las consultas de inmediato; si el cierre falla antes de llegar al servidor, la sesión conservada vuelve a consultar.
- Cambiar de cliente descarta su canal anterior; no traslada avisos a otro cliente. Las notificaciones no se guardan en localStorage ni se convierten en una copia paralela del inventario.

## Contrato y verificación técnica

Archivos: `ClientChangeNotice.jsx`, `client-changes.ts`; montaje mínimo en InventoryPanel y suspensión reactiva de logout en ServerApp. GET `/api/v1/customers/{id}/changes?afterRevision=R&limit=50`; ETag de revisión actual y no-store. API valida autorización actual en cada lectura. Cursor, actor, cliente, orden contiguo, shapes y referencias son validados por el adaptador; números de revisión que JavaScript no pueda representar exactamente se rechazan, no se redondean.

No sustituye auditoría administrativa, recuperación de operaciones ni autorización en escritura. La función solo queda disponible en QA cuando el catálogo detecte la pareja revisada y desplegada; escribir este manual no habilita el caso ni adopta el servidor.
