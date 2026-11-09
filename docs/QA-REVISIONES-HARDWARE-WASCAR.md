# QA — revisión de la plantilla de un equipo

30.10.2026. **Preparado; todavía no instalado en la candidata10.** Usar sólo
cuando se entregue una candidata identificada con montaje y revisión de hardware.
No hay que reinstalar ahora la VM ni repetir el MFA ya probado.

1. En **Clientes**, entra en un cliente sintético y abre un rack de pruebas con
   espacio. Si utilizas el rack lleno de QA-136, crea otro rack para este caso.
2. En la barra superior pulsa **Añadir hardware de referencia**. Elige
   **Switch, 24 RJ45 + 2 SFP**. Bajo la selección y las dimensiones debe aparecer
   **Revisión de plantilla: hw-reference-v1**. Es información de la selección,
   no un campo libre para escribir otra versión.
3. Escribe un nombre y elige el rack. Pulsa **Guardar** abajo a la derecha y
   espera **Guardado por el servidor**. La cabecera del equipo debe conservar
   su clave y revisión. Frontal:24RJ45; trasera:2SFP.
4. Cambia únicamente nombre o notas con el lápiz del equipo y guarda. Comprueba
   que revisión, número de puertos y conexiones anteriores no cambien.
5. Recarga con **F5**, vuelve al cliente/rack y comprueba la revisión y los
   datos. Si tienes otra cuenta autorizada, repite la lectura en ventana privada.
6. Si ya existe otra instancia del mismo perfil en el cliente, comprueba que
   renombrar una no cambie el nombre de la otra. No es necesario crear otra
   sólo para repetir una prueba ya realizada.
7. No alteres SQL o archivos para provocar una revisión desconocida. Ese
   negativo está automatizado en laboratorio. Si aparece espontáneamente una
   advertencia de revisión no disponible, conserva una captura: deben seguir
   presentes los equipos, puertos y montaje guardados, sin sustituirse por el
   dibujo de otra revisión. No intentes «repararla» cambiando metadatos.

Registra Pass, Not Pass, Bloqueado y observaciones en la guía habitual. El
producto sigue ofreciendo sólo las cuatro referencias genéricas v1; todavía
no hay selector de revisiones comerciales ni modelos nuevos de fabricante.
