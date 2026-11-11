# C2 · campos y roles de Dosen y dispositivos finales

25.10.2026 · cierre técnico de I-06.02. Se completan las comprobaciones de los editores existentes; no se modifica el producto ni se reconstruyen sus artefactos.

## Cobertura nueva

En un laboratorio PostgreSQL17.11 nuevo, con cuentas e inventario sintéticos, Edge ejercita los controles reales de una Dose y un dispositivo final:

- Nombre, presupuesto PoE y las cinco notas: serie, modelo, IP, firmware y texto. El editor de sala no ofrece unidades de rack. Se preservan propiedades adicionales y anidadas, UUID, sala y demás metadatos.
- Estado, PoE, vatios, color, etiqueta y cara del puerto RJ45 seleccionado. Se prueban activar/desactivar PoE y vaciar vatios/color/etiqueta, sin confundir null con texto vacío.
- Roles `outlet` e `inlet` en puertos `power` sin cable. No se declara verificación de un circuito físico. RJ45 y power repiten gn=1: los comandos identifican dispositivo, grupo, tipo y UUID del puerto; el vecino permanece intacto.
- Cada una de las dieciséis escrituras recibe200, incrementa la revisión y se confirma por lectura del servidor antes de comprobar el estado de guardado. Dos operaciones son `device.update` y catorce `ports.update`.
- Recarga y segunda cuenta autorizada leen el proyecto completo y los controles con los valores guardados. Unicode y nombres/notas con apariencia de HTML permanecen como texto, sin elementos inyectados.

La comparación independiente de nueve tablas SQL permite únicamente los campos esperados. Identidades, jerarquía, grupos, puertos no elegidos, cables y extremos no cambian. Un rol eléctrico sobre RJ45, PoE sobre power, un lote con puertos de grupos distintos y vatios fuera de límite producen422; un puerto de otro cliente404. Lector403 y usuario ajeno404 tampoco escriben. Cada rechazo conserva inventario, cliente/revisión, operaciones y auditoría completos. Dos cuentas leen el mismo estado después de reiniciar el proceso servidor.

## Resultado y revisión

- Foco nuevo Windows/Edge/PostgreSQL17.11: **PASS32,719s**,16 operaciones y auditorías de inventario2+14. Fuentes/artefactos sin cambios durante el ensayo; laboratorio y procesos propios detenidos.
- Regresión de edición de objetos de sala ejecutada de nuevo con los mismos artefactos: **PASS27,562s**, cuatro operaciones, cuatro auditorías de inventario más una preferencia de idioma,403/404/422 sin cambios y persistencia tras reiniciar el proceso.
- Revisor distinto del implementador: tres focos puros del comparador y contraste de los recibos. Control válido aceptado; trece mutaciones indebidas de identidad, pertenencia, metadatos, valores vacíos, vecinos y cables rechazadas. No repitió Edge/PostgreSQL ni operó VM.

El borrado con impacto se apoya en el foco anterior de [borrado individual y conjunto](C2-BORRADO-IMPACTO-25-10-2026.md): dispositivo final conectado individual y lote Dose/equipo, previews/cancelaciones exactos, permisos y cables conservados. Es evidencia anterior identificada, no una ejecución nueva atribuida a esta tanda. La [revisión anterior de edición](REVISION-C2-OBJETOS-SALA-CODEX-25-10-2026.md) permanece intacta.

## Límites y siguiente paso

I-06.02 queda completado técnicamente tras revisión, con peso fijo5/12. **I-06 completo sigue pendiente**: mapa de operaciones/plantillas/AP, rutas/informes/avisos y revocación, ocupación lógica frente a I-07, integración y aceptación. No se aplaza alcance por esta prueba.

Sólo español y un puerto RJ45/power seleccionado por objeto; no exhaustividad de todos los valores/idiomas, hardware, circuito eléctrico, Windows reboot, instalación o QA. La DLL5eb1 y el frontend04f4 usados son artefactos privados C2; no están integrados automáticamente en el instalador08 ni disponibles en un clon limpio. No se habilitan casos QA al añadir estas pruebas.

MFA-L1 continúa en la zona de Claude según informa Wascar; este bloque no modifica sus archivos, dependencias ni claves. C sigue cerrado y apagado según Wascar. Sin commits/push, paquetes nuevos, VM o QA. [Evidencias, comandos y revisión](../evidence/s1-20261025/c2-room-fields-codex/CIERRE.md).
