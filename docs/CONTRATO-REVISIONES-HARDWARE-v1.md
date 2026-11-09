# Identidad y revisión de hardware — primer tramo

30.10.2026. Extensión del contrato de montaje; el esquema de base permanece en16.
No se modifica el JSON `hw-reference-v1`, una migración aplicada o la instalación10.

## Regla

Una definición se identifica por **clave y revisión**, con comparación exacta.
Dos revisiones de una clave pueden coexistir en el registro sin sustituirse.
Duplicar una pareja clave/revisión es un error de configuración, no una edición.
No existe búsqueda implícita de «latest» ni respaldo hacia otra revisión.

El registro copia sus entradas y protege también las listas/objetos anidados.
Esto evita modificaciones accidentales desde su API de código; no constituye
una frontera de seguridad frente a un administrador que cambie el programa.

## Crear una instancia

Las solicitudes nuevas fijan la revisión que mostraba el formulario:

```json
{"type":"device.createHardware","payload":{
  "profileKey":"desktop-firewall-6", "profileVersion":"hw-reference-v1",
  "rackId":"<uuid>", "name":"Firewall QA",
  "mountParentId":"<uuid de bandeja>", "mountSlotKey":"main"
}}
```

Por compatibilidad, una solicitud anterior que **omite** `profileVersion` sigue
ligada a `hw-reference-v1`, permanentemente. Una revisión desconocida, vacía o
explícitamente nula se rechaza sin cambios parciales. No se interpreta como una
petición de la revisión nueva. El cuerpo y la revisión de una operación pendiente
se conservan para replay; cambiar de catálogo no reescribe esa solicitud.

Se materializan grupos/puertos con UUID propios y las dimensiones de la revisión
elegida. La versión ya se guarda en `properties.hardwareProfileVersion`; la API
no permite cambiarla mediante edición de notas/colores. No hace falta otra
migración para este primer tramo de vínculo.

## Leer y representar

- La proyección conserva la revisión y las dimensiones registradas. No toma las
  dimensiones de una definición «actual» diferente.
- Si está instalada la pareja exacta, se usa su representación.
- Si la revisión no está disponible o no se registró, se muestra una advertencia
  y una representación genérica. Se conservan nombre, puertos reales y relación
  padre/hijo. No se sustituye el perfil por el de otra revisión ni desaparecen
  los dispositivos montados por no conocer su dibujo.
- No se inventan dimensiones de alojamiento para una revisión desconocida.
  Las dimensiones guardadas válidas pueden seguir mostrándose como datos.
- Una bandeja de revisión desconocida no se ofrece para montar equipos nuevos:
  no se presuponen las dimensiones del alojamiento v1. El servidor también lo
  rechaza, independientemente del control visual.

## Límites y ampliación

Sólo están publicadas las cuatro referencias sintéticas v1. Las revisiones
adicionales usadas en pruebas son fixtures, no modelos disponibles para crear.
SQL016 sigue limitando ese primer ensayo a cuatro claves/reservas. Antes de
añadir fabricantes hacen falta el catálogo normalizado de definiciones,
validación de modelos/variantes, importación controlada, licencias y publicación
del catálogo. Este registro no los acredita como implementados.

Tampoco se habilita QA de esquema16 ni se actualizan los operadores/instalador.
La nueva guía manual se habilitará sólo con una candidata identificada.
