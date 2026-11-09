# QA138 — primer modelo comercial

30.10.2026. **Preparado, aún no disponible en la instalación 10.** Espera una
candidata completa identificada de esquema 18. No reinstales ni repitas MFA ahora.
Las capturas del laboratorio se ven en VER-PRIMER-MODELO-COMERCIAL.html.

Anota Pass/NotPass/observaciones en la guía habitual, conservando respuestas
anteriores. No hay que modificar SQL, descargar el PDF o abrir PowerShell.

| Paso y ubicación | Acción | Resultado esperado | Tu resultado |
|---|---|---|---|
| 1 · Menú izquierdo, Clientes | Abre un cliente sintético y crea/abre un rack nuevo de 2 U. | Rack vacío y espacio para dos paneles. | |
| 2 · Barra superior del inventario | Pulsa **Añadir hardware de referencia**. En **Perfil de referencia** elige **StarTech.com · C6PANELUTP241UFT** y su revisión. | El formulario distingue datos contrastados; muestra483×44,3×138mm,1U,24 RJ45frontales y 24 traseros. | |
| 3 · Formulario central | Escribe «Panel StarTech A» en Nombre, elige el rack y pulsa **Guardar** abajo a la derecha. | Espera Guardado por el servidor; aparece el modelo con su revisión exacta. | |
| 4 · Mismo botón superior | Crea «Panel StarTech B» en el mismo rack. | Dos objetos distintos;2/2U reservadas. Cambiar uno no modifica el otro. | |
| 5 · Encima del dibujo | Pulsa **Frontal**. En A pulsa el conector 1 y después el conector 1 deB. | Un cable confirmado por servidor, con los extremos seleccionados. | |
| 6 · Encima del dibujo | Pulsa **Trasera**. Comprueba24 conectores y conecta el 1 de A con el 1 de B. | Otro cable; el ordinal 1 trasero no es el puerto frontal 1. Los números traseros se explican como lógicos. | |
| 7 · Cabecera del primer panel | Pulsa su lápiz, cambia nombre y notas y guarda. | Identidad del modelo, revisión, dimensiones y conectores no cambian; ambos cables se conservan. | |
| 8 · Navegador | Pulsa F5 y vuelve al cliente/rack. Si tienes otra cuenta autorizada, abre una ventana privada y entra. | Ambas sesiones leen lo guardado; marca/modelo no se traducen al cambiar de idioma. | |
| 9 · Mismo rack lleno | Intenta añadir otro panel y luego cancela. | Rechazo por falta de espacio, sin tercer equipo ni éxito fantasma. | |
| 10 · Cuenta de sólo lectura | Si se entregó esa cuenta, abre el cliente/rack. | Puede leer; no puede crear o editar. Si no se entregó, anota No probado. | |

Son 24  acopladores con48 extremos físicos por panel; no48 interfacesEthernetactivas.
La correspondencia interna está declarada y el trazado automático sigue pendiente.
El dibujo es un esquema propio. El enlace **Ficha del fabricante** es opcional y
se abre fuera de la aplicación; no hace falta para completar la prueba.
