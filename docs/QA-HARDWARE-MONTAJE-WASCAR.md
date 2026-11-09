# QA — bandeja, firewall, switch y patch panel

**Actualización30.10.2026:** el siguiente paquete debe incluir esquema17 y su catálogoSQL. Los pasos visibles se conservan; QA136/137 siguen pendientes de una candidata completa identificada. No reinstalar la VM ahora.


30.10.2026. **Preparado, todavía no disponible en tu instalación 10.** Se ha
probado en un laboratorio independiente de Windows/PostgreSQL/Edge. Espera una
candidata identificada que incluya esquema 16; no reinstales tu VM ni cambies sus
datos para intentar activar este caso. No hay que repetir tu QA de MFA.

Cuando se entregue esa candidata, utiliza un cliente sintético de pruebas y un
rack nuevo de 4 U. Conserva las observaciones en la guía habitual: Pass, Not Pass,
Bloqueado y notas. No modifiques los resultados anteriores.

| Paso | Ubicación y acción | Resultado esperado | Resultado / observación |
|---|---|---|---|
| 1 | En Clientes abre el cliente sintético. En la barra superior pulsa **Crear Rack**, escribe un nombre de prueba y altura **4 U**, y guarda. Abre su tarjeta. | Rack vacío; confirmación del servidor. | |
| 2 | En la barra superior, junto a Añadir equipo, pulsa **Añadir hardware de referencia**. En Perfil elige **Bandeja, reserva de 2 U**. Escribe «Bandeja QA», elige el rack nuevo y pulsa **Guardar** abajo a la derecha. | Aparece la bandeja y su alojamiento main; 2/4 U reservadas. | |
| 3 | Pulsa el mismo botón. Elige **Firewall de sobremesa, 6 + 1 RJ45**, nombre «Firewall QA», el rack y **Bandeja QA** en Bandeja de montaje. Guarda. | El firewall aparece dentro de la bandeja. Dice 0 U adicionales y conserva dimensiones físicas propias. La reserva sigue en 2/4 U. | |
| 4 | Añade **Switch, 24 RJ45 + 2 SFP** y **Patch panel pasante, 24 + 24 RJ45**, cada uno con su nombre y en ese rack. | Quedan 4/4 U reservadas, libre 0 U. Son referencias genéricas; no productos comerciales verificados. | |
| 5 | Intenta añadir otro switch al mismo rack. | Mensaje de falta de espacio; el diálogo permanece abierto. No aparece otro equipo ni se afirma éxito. Pulsa Cancelar. | |
| 6 | Sobre el dibujo pulsa **Frontal**. Haz clic en LAN1 del firewall y después en el puerto 1 del switch. Espera **Guardado por el servidor**. Después conecta el puerto 2 del switch con F1 del panel. | Dos cables y extremos correctos en el inspector de la derecha. | |
| 7 | Encima del dibujo pulsa **Trasera**. Debes ver MGMT1 del firewall, 2 SFP del switch y 24 RJ45 del panel. Haz Click-Click entre R1 del panel y MGMT1 del firewall. | Tercer cable guardado. F1 y R1 son distintos aunque ambos tengan número 1. La correspondencia interna del panel no se presenta como cable automático. | |
| 8 | En la cabecera del firewall pulsa el lápiz. Cambia nombre y notas, guarda. Pulsa F5 y vuelve a abrir cliente/rack. Abre también otra sesión autorizada en una ventana privada. | Las dos sesiones leen los mismos nombres, montaje y cables. No se ofrece cambiar U o presupuesto PoE en ese editor. | |
| 9 | Intenta eliminar sólo la bandeja con su botón ×. | El servidor pide retirar primero el equipo montado. Se conservan bandeja, firewall y cables. No confirmes la eliminación del rack completo como parte de este paso. | |
| 10 | Con una cuenta de sólo lectura abre el cliente. | Puede leer; no puede crear ni editar. No basta con ocultar botones: el servidor también rechaza escrituras. Anota No probado si no se entregó esa cuenta. | |
| 11 | En un rack de prueba con un equipo anterior RC9 añade una bandeja. Comprueba frontal/trasera, colapsar con −/+, subir/bajar el equipo anterior e inspector. | Se conserva su dibujo y sus controles RC9. El nuevo montaje no sustituye el resto del rack. | |
| 12 | En **Información e informes**, genera el inventario imprimible del rack. Prueba SVG y XLS/HTML RC9 sólo si deseas comprobar el límite informado. | Impresión identifica el soporte y «0 U adicionales». SVG/XLS explican que todavía no representan montaje; no descargan un archivo parcial. | |

No cortes la red ni detengas PostgreSQL para esta QA manual. Si aparece una
operación pendiente, utiliza Consultar/Reintentar de esa operación; no crees otra.
Adjunta los resultados exportados de la guía y una captura si algo no coincide.
