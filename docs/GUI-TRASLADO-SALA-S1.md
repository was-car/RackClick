# Traslado entre salas · GUI RC9 · grupo62 / QA33

17.10.2026. Cambio acotado S1, posterior a R0. Reutiliza OperationDialog, journal durable, revisión/idempotencia y proyección de extremos existentes. No modifica RC9 adoptada, CSS global, API, esquema ni traslado de equipos entre racks.

## Comportamiento

En cliente → Gestionar infraestructura → Objetos en salas → tarjeta de toma de pared/dispositivo final → Mover, se muestra nombre literal y Sala actual con ruta Sede / Edificio / Sala y UUID. Sala de destino empieza vacía y exige elegir otra sala del snapshot autorizado de ese cliente. Cada opción muestra ruta y UUID: las salas homónimas no se fusionan. EN: Current room / Destination room; DE: Aktueller Raum / Zielraum; ES: Sala actual / Sala de destino.

Sin otra sala, se informa que no puede guardarse un traslado; el selector está deshabilitado. Incluso enviar directamente el formulario se rechaza localmente sin crear petición ni confirmar un guardado. Tras412, el destino del borrador se conserva y Cargar datos actuales actualiza sala actual/opciones desde el snapshot nuevo. El build vuelve a comprobar objeto, clase y destino distinto vigente antes de preparar el comando; si otro usuario ya trasladó el objeto al destino elegido, no se envía un traslado a su sala actual.

Se envía exclusivamente device.move con id y roomId, sin rack, U ni conversión de clase. El servidor existente calcula sort_order=max(destino)+1: es orden documental, no una U física. Cambian sala y ese orden; se conservan puertos/grupos/atributos/cables/extremos por UUID. Las etiquetas de extremos se derivan de ubicación actual tras refresco; no se reconstruye historia. Dos puertos explícitos de una Dose pueden tener cables externos distintos; esto no declara un circuito interno entre ellos.

## Guion manual QA33: preparar datos nuevos

Disponibilidad: el coordinador la determina por artefactos reales y catálogo QA. Este documento no habilita casos. No usar ni trasladar objetos del backup de Wascar para preparar la prueba.

1. Entrar con administrador o técnico autorizado; abrir un cliente NUEVO de prueba desde Clientes. En Gestionar infraestructura crear Sede A y Sede B; en cada sección usar Crear Edificio y luego Crear Sala. Poner el mismo nombre Sala QA33 en ambas salas. Confirmar ruta diferente y UUID distinto en Mover.
2. En una sección de sala usar Crear Toma de pared y Crear Dispositivo final. Escribir nombres literales nuevos (por ejemplo Toma QA33 Ω y Final QA33 東京); crear los puertos explícitos documentados. Ambos deben figurar en Objetos en salas, sin rack ni U. Crear otro objeto de prueba en sala destino para comprobar que permanece intacto.
3. Si se prueban cables, usar equipo NUEVO de rack con puerto libre → puerto1 explícito de la toma; puerto2 distinto de la toma → puerto explícito del final. Usar Click-Click y anotar UUID de cables/puertos y atributos. No conectar dos cables al mismo puerto ni deducir continuidad interna por compartir Dose.
4. En tarjeta Toma QA33 Ω pulsar Mover. Revisar Sala actual (ruta completa y UUID). Ver Sala de destino vacía. Pulsar Guardar sin elegir: la validación exige destino y no aparece confirmación de guardado. La sala actual no debe aparecer como destino.
5. Seleccionar la otra Sala QA33 por su ruta/UUID y pulsar Guardar UNA vez. Esperar Guardado por el servidor y cierre del diálogo. Revisar ruta de tarjeta y tooltip del puerto, cables/etiquetas/estados/PoE/watts/cara/notas originales. Repetir con Final QA33 東京. No debe crearse un rack ni consumirse U; el orden documental puede pasar al final del destino.
6. Recargar página, entrar de nuevo al cliente y comprobar ambas ubicaciones y UUID/cables. Abrir segunda cuenta autorizada en otro perfil de navegador y comprobar la misma ubicación. Lector debe consultar sin botones de escritura; cuenta sin ámbito no debe ver el cliente ni conseguir su snapshot por URL.
7. Conflicto: con Mover abierto y destino elegido, otra cuenta autorizada modifica el nombre del cliente de prueba y guarda. Primer usuario pulsa Guardar: esperar aviso de conflicto, destino conservado y guardado bloqueado. Pulsar Cargar datos actuales: revisar Sala actual vigente y mismo destino elegido antes de reintentar. Si otro usuario ya movió el objeto al destino, cancelar y revisar; no se confirma otro traslado a la misma sala.
8. Cliente NUEVO con una sola sala y una toma NUEVA: tarjeta → Mover debe mostrar aviso Sin otra sala y selector deshabilitado; ningún guardado confirmado. Cancelar. Revisar textos en EN/DE/ES y ventana estrecha390px; los nombres propios permanecen literales.

## Evidencia y límites

Build frontal único y candidato congelado18archivos en evidence/s1-20261017/tres-tandas-62/frontend/frontend-candidate.json; salida build.log. Arnés nuevo test_room_device_move_gui.py exige --dll/--frontend/--output explícitos, compara hashes antes/después, crea laboratorio PostgreSQL nuevo y lo apaga. Escenario Edge nuevo browser-room-device-move.mjs reutiliza soporte CDP local sin dependencias nuevas. No se prueban instalación limpia, reboot de Windows, GUI de alta completa, restauración productiva, topología pasante ni adopción. QA33 requiere catálogo/guías del coordinador y revisión independiente antes de declararse disponible.
## Ejecuciones propias sobre pareja final62

Candidata técnica .local/candidates/tres62-final-7265674801944438a070589428ff6b3c: DLL SHA25678fcf05cd2c0be9bb8dac6a28788c591538be6e662af38f88cb840388e225c27; frontend app.js468fa553d18f62c3ac1830a6d857baa612519f482ab83c42aa456ab0a107c726. Un único build frontend;18archivos congelados. CANDIDATA62 del coordinador identifica la pareja.

- Nuevo test_room_device_move_gui.py --dll .local/candidates/tres62-final-7265674801944438a070589428ff6b3c/server/RackClick.Server.dll --frontend .local/candidates/tres62-final-7265674801944438a070589428ff6b3c/frontend --output evidence/s1-20261017/tres-tandas-62/frontend/native-v2: PASS24,969s en Windows11/Edge/PostgreSQL17.11. Nueve tablas comparadas exactamente: sólo room_id y sort_order de Dose/final (destino previo3 intacto; nuevos órdenes4/5). Dos commits de traslado, dos rechazos412 documentados; el segundo refresco muestra sala actual nueva e impide enviar un no-op al destino ya actual. Lector403, ajeno404, destino ajeno/inexistente404 y UUID/ubicación/U incompatibles422. Recarga dos actores y reinicio de ASP.NET exactos. No es reboot Windows.
- Regresión test_inventory_movement_gui.py con la misma pareja y --output evidence/s1-20261017/tres-tandas-62/frontend/rack-regression-v1: PASS21,625s. Traslado entre racks, orden, proyección local/cross, conflicto, permisos y persistencia/reinicio conservados.
- Capturas room-move-390-en/de/es.png inspeccionadas visualmente: nombre literal/ruta/UUID/textos/botones legibles y sin recorte horizontal. Escenario sin destinos y selección/limpieza Click-Click también correctos.
- Intento native-v1 FAIL9,469s por errata del arnés al añadir un puerto libre (tupla de4valores en bucle de3). Falló antes de INSERT/Edge; evidencia conservada, laboratorio apagado. Se corrigió exclusivamente el test y se repitió el foco en v2; sin otro build ni cambio de producto.

Los arneses finales registran inputsUnchanged=true, labStopped=true y serversStopped=true. La revisión independiente y QA de Wascar corresponden al cierre conjunto del coordinador. Estimación vigente recibida58/100; este informe no la incrementa ni mide aceptación/créditos.
