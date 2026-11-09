# Tanda · racks primero

30.10.2026. Desarrollo y pruebas terminados en laboratorio; revisión independiente favorable. No está instalado en la VM de Wascar ni publicado todavía como nueva candidata. La candidata 10 y sus datos/MFA se conservan.

## Cambio realizado

- Al abrir un cliente, las tarjetas de racks preceden a la jerarquía extensa, PoE e informes. Al abrir un rack, su vista RC9 precede a los controles secundarios.
- **Información e informes** en la barra superior lleva a la zona secundaria; **Volver a los racks** devuelve posición y foco al inventario principal.
- La jerarquía se puede plegar. **Gestionar infraestructura** la abre y sitúa al usuario en ella; un resultado de búsqueda de sitio, edificio o sala abre el panel antes de enfocar el destino.
- PoE empieza plegado, con sus avisos agregados de exceso/datos incompletos visibles. Se conservan cálculos, nombres, UUID y detalle por equipo.
- Los exportadores mantienen sus propios controles y permanecen montados. No hay otro desplegable exterior que oculte una operación incierta; selección y formulario se conservan al navegar.

Se reutilizaron componentes RC9 y HTML nativo, tras [investigación previa](../evidence/s1-20261030/racks-first/INVESTIGACION-PREVIA.md). No se añadieron dependencias ni se cambió servidor, SQL, permisos, MFA o el archivo offline adoptado.

## Pruebas y revisión

Compilación frontend privada y 37 pruebas del adaptador correctas; ejecución completa de unidades: **801 Pass, 0 Fail**. Edge real con PostgreSQL 17.11 y los 10 clientes/5408 puertos originales reproduce la vista anterior y comprueba la nueva a 1440 y 390 px, EN/DE/ES, teclado, foco, selección Click-Click, borrador SVG, error y reintento con la misma solicitud, búsqueda, recarga y otra sesión. Las 10 tablas de inventario quedan idénticas.

Una regresión PoE separada comprueba los dos avisos de exceso con el panel cerrado, estados/cálculos, edición confirmada, permisos de lector/404 fuera de ámbito y persistencia tras reiniciar sólo el servidor de ese laboratorio. Ambos laboratorios quedan detenidos.

Se conservó un primer intento fallido del despacho de teclado CDP. Con la página activa y la secuencia completa de Enter/Space, el mismo producto pasa; no se alteró su código para superar esa prueba. Los registros crudos quedan privados.

[Revisión independiente](REVISION-RACKS-PRIMERO-30-10-2026.md): siete invocaciones críticas y CSS anterior conservados; capturas y resultado final contrastados. El revisor no implementó el cambio ni repitió el laboratorio. No hay P1/P2 confirmados. La barra móvil aún ocupa bastante altura: mejora posterior registrada.

## Qué queda

Preparar la integración en una candidata identificada, compactar más los formularios de informes/controles técnicos y realizar QA de Wascar. No se acredita el bloque completo P-11, lector de pantalla o contraste integral por este foco. No se repiten ahora instalación, importación o MFA de la VM para obtener otra evidencia.

Los casos **QA-133/134** están preparados y marcados no disponibles hasta integrar; [pasos para Wascar](QA-RACKS-PRIMERO-WASCAR.md). Se conservaron los 132 casos previos y los resultados personales no se modifican. La guía HTML se regeneró y verificó.

**Índice de cierre restante: 9,76/100, sin cambio de base o pesos.** REQ-UX-01 pasa a implementado/probado en laboratorio, pendiente de integración/QA; REQ-UX-03 queda parcialmente atendido. Eso muestra el avance concreto sin declarar completada toda la matriz de accesibilidad/paridad.
