# Selector compacto del catálogo

Requisito confirmado por Wascar el 01.11.2026. Responsable: C-HW-04, relacionado con C-HW-03 y REQ-HW-VISUAL-01. No crea un resultado ni peso adicional.

La lista de productos se busca por fabricante, familia, modelo o SKU. «sofos» es un alias de búsqueda de Sophos. La selección conserva el nombre, fabricante, SKU y revisión exactos; el alias no cambia identidades. No se deduce un modelo distinto por parecido ni se convierte texto libre en un perfil comercial.

En desarrollo, la ventana **Añadir hardware de referencia** tiene un campo de búsqueda y un desplegable oculto inicialmente. Escribir, hacer clic en el campo o usar la flecha despliega las coincidencias. El panel tiene desplazamiento propio y altura máxima de 240 px o 40% de la ventana. La selección y un resumen compacto permanecen visibles; dimensiones, revisión, grupos y fuente se consultan en **Detalles del modelo y conectores**, plegado inicialmente.

Flechas arriba/abajo recorren los resultados; Enter elige una opción resaltada; Escape cierra la lista sin cerrar la ventana de creación; si la lista ya está cerrada, conserva la cancelación normal del formulario. Editar la búsqueda invalida el producto anterior hasta seleccionar otro: no se guarda un modelo que ya no corresponde al texto. Los campos se bloquean con el formulario durante una operación o pérdida de autoridad. El comando sigue validando revisión, montaje, ámbito y permisos en el servidor.

## Plantillas propias

Se conserva el flujo independiente **Mis plantillas privadas** en la barra del inventario. Se cierra la ventana de hardware comercial antes de abrirlo. Allí se elige el equipo de origen, se escribe un nombre, se revisan grupos y etiquetas y se confirma el guardado por servidor. No se mezclan sus permisos, identidades ni solicitudes pendientes con el catálogo de fabricantes. Un resultado de búsqueda inexistente nunca crea una plantilla de forma implícita.

## Disponibilidad y pruebas

Esta descripción corresponde a fuentes de desarrollo. El grupo C mantiene el mismo componente y amplía sus opciones a528 definiciones. El resultado de pruebas, revisión independiente y cobertura se registra en INTEGRACION-506-GRUPO-C.md y evidence/s1-20261101/integracion506c/. La demostración B y su ZIP conservan su alcance histórico de478 definiciones. No presupone una actualización de la instalación ni de QA. El manual de instalación y el paquete completo deberán transportar el catálogo final y explicar ambos flujos.
