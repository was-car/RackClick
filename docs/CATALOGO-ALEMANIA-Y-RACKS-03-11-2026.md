# Alemania, soportes y comodidad del rack

> **Actualización posterior de hoy:** los cambios ya están instalados en D45. [URL, comprobaciones y límites](ACTUALIZACION-D45-03-11-2026.md). El registro de desarrollo siguiente conserva el estado anterior a esa operación.

03.11.2026 · Prioridad solicitada por Wascar antes del paso9/F-03.02. La instalación D y sus datos se conservan. Este documento no acredita puntos nuevos del cierre.

## Resultado del lote

- **Seis modelos adicionales en desarrollo44**, conservando las506selecciones y868revisiones anteriores: FRITZ!Box7530AX(DE20002930),7590AXv2(DE20002998,sinS0),7690(DE20003057), DrayTekVigor167,2766 y2766ac. Total874revisiones/867modelos comerciales distintos. No son874modelos nuevos.
- USB, DSL, telefoníaRJ11/TAE y alimentaciónDC conservan sus tipos; no sonEthernet. Los radiosWiFi/DECT no crean bocas. Las tomas laterales se presentan en una vista compuesta de conectores, con ese límite declarado. FON alternativoRJ11/TAE no significa dos líneas independientes ni simulación del circuito interno.
- El buscador compacto acepta «Drytek»→DrayTek, «Fritzbox»,«Fritz!Box»,«fritz box» y«AVM», además de marcas/modelos/SKU exactos. Los alias no sustituyen identidad ni revisión.
- **Racks:** desaparecen los mínimos arbitrarios de400/1000px. Cada cara mantiene el mínimo necesario para objetivos de conexión de24px; una cara sin bocas puede ajustarse libremente. Una cara densa puede seguir requiriendo desplazamiento para que sus puertos sean utilizables.
- Equipos sobre bandeja: anchura relativa a sus medidas y al hueco útil; mínimo de panel220px limitado al espacio disponible para mantener controles legibles en móvil. «Ampliar vista»/volver a proporciones sólo cambia la presentación. Nunca cambia medidas, ocupación, IDs o cables guardados. La notificación al rendererRC9 vuelve a medir los extremos al ampliar.
- Nombres completos conservados. Nombre de soporte truncado visualmente con tooltip; revisión, claves internas, cotas y notas de cara quedan en detalles plegables. No se renombran los soportesQA ni los nombres escritos por el usuario. Advertencias de revisión desconocida permanecen visibles.

**Para ver el resultado:** [abrir revisión local](../VER-ROUTERS-ALEMANIA-01.html). Es un visorHTML con el renderer del producto y el catálogo real de desarrollo; no un instalador ni un importador de datos.

## Ejemplos concretos de Wascar

Se incorporan al foco de revisión TP-LinkTL-SG108EUN6.0(`tplink-tl-sg108e-un6-0`), ZyxelXGS1250-12(`zyxel-xgs1250-12`) y Aruba2930F-12G-PoE+-2SFP+/JL693A(`selected-nb-2ffc5d29f711ec36`). Los nombres largos «Soporte QA c01.model-…» se conservan como datos, sin usarlos como cotas físicas ni obligar a que desborden la tarjeta.

Se observó una captura de la VM D encendida, en su sesión de navegador existente: Aruba sobre soporte, barra y metadatos extensos. La captura permanece privada; no hubo instalación, login, escrituraDB, cambio de servicio ni edición de sus archivos. El conector de navegador del chat no tenía pestañas disponibles; la observación se obtuvo mediante capturaVM de sólo lectura, no mediante una sesiónGUI completa operada por Codex.

## Sondeo para próximas familias

Es una selección práctica de productos documentados por fabricantes/proveedores, **no una estadística de cuota de mercado alemana** ni un compromiso de implementar todas las variantes ahora.

| Proveedor/familia | Selección y estado | Fuente primaria |
|---|---|---|
| FRITZ!/AVM DSL |7530AX,7590AXv2,7690 incorporados al desarrollo44. Mantener revisiones/SKU distintos;7530AX presenta diferencias de dimensiones entre folletos históricos y ficha actual. |[FRITZ7530AX](https://fritz.com/products/fritz-box-7530-ax-20002930/),[FRITZ7690](https://fritz.com/products/fritz-box-7690-20003057/) |
| FRITZ cable, fibra y WAN |Siguiente sondeo:6660/6690/6670Cable,5530/5590Fiber,5690Pro,4050/4060. Falta autoría porSKU/cara y contrastar coaxial/PON, nunca presentarlos comoDSL por semejanza de carcasa. |[FamiliasFRITZ](https://fritz.com/products/) |
| DrayTekVigor |167,2766,2766ac incorporados. Siguiente:166,2865/2866,2927 y variantesLTE/WLAN por confirmar en sus fichas. No deducir bocas de un sufijo comercial. |[Vigor167](https://www.draytek.de/de/produkte/modem-router/vigor167/),[2766](https://www.draytek.de/de/produkte/modem-router/vigor2766-serie/),[catálogo2025](https://draytek.com/download_de/Produktkatalog/draytek-produktkatalog-2025.pdf) |
| TelekomSpeedport |Smart4,Smart4Plus,Smart3 yProPlus como candidatos; variantesA/B y conectores de fibra/telefonía necesitan ficha exacta. No se han integrado en este lote. |[SoporteoficialSmart](https://www.telekom.de/hilfe/geraete/router/speedport/smart-serie),[manualSmart4Plus](https://www.telekom.de/hilfe/downloads/bedienungsanleitung-speedport-smart-4-plus.pdf) |
| Vodafone |Station,EasyBox805,UltraHub7: candidatos. Identificar primero el OEM/revisión de cadaStation; no tratar todas las cajas con ese nombre como un único aparato. |[RouterVodafone](https://www.vodafone.de/hilfe/router-easyboxen.html),[Station](https://www.vodafone.de/hilfe/router/station.html) |
| o2 |HomeBox6741/6742 yHomeSpot: candidatos, incluyendo variantes históricas utilizadas en instalaciones existentes. |[Manualeso2](https://www.o2online.de/service/router/router-anleitungen/),[archivooficial](https://www.o2online.de/service/router/router-anleitungen/archiv/) |
| LANCOM empresarial |1781VA,1783VA-4G,1790VAW,1793VAW ya existen; no duplicarlos.1800VA/1803VA,1926VAG y1936VAG candidatos para ampliar por arquitectura real. |[TablaoficialLANCOM](https://www.lancom-systems.com/fileadmin/pdf/brochures-and-flyer/LANCOM-Produktvergleichstabelle.pdf) |
| Digitalisierungsbox/bintec elmeg |Familia empresarial a investigar después: versión, responsable de soporte y documentación conservada antes de escoger modelos. No se afirma cobertura ni disponibilidad vigente sin ese contraste. |Punto de investigación pendiente, sin plantilla instalada. |

La biblioteca [NetBoxDeviceTypeLibrary](https://github.com/netbox-community/devicetype-library) es referencia complementaria, no autoridad para inventar puertos ni permiso de redistribución de fotos. Se reutiliza el método de familias; las imágenes del proveedor son referencias y los vectores distribuidos son propios. Carcasas esquemáticas, no reproducciones fotográficas ni certificación mecánica.

## Funciones offline

No se da por terminada la paridad. La [comparación de302acciones del29.10](COMPARACION-OFFLINE-RC10-SERVIDOR.md) y su [plan trazado](PLAN-PARIDAD-RC10-SERVIDOR.md) se conservan. Sus47equivalentes/122adaptadas/62parciales/71ausentes describen aquel servidor10, **no una nueva medición de la candidata44**.

La observación actual de Wascar («faltan botones del offline») queda registrada sin inventar cuáles son. Antes de copiarlos, contrastar la acción concreta y su ubicación actual: un botón oculto, una adaptación a permisos y una función ausente requieren soluciones distintas. Primera cola de comodidad/paridad:

1. Acciones de conexión/edición y menús del rack: localizar frente aRC9/RC10 y no perderClick-Click, etiquetas, frontal/trasera y tooltips.
2. Informes/exportaciones: agrupar sin ocultar el acceso a lo existente; distinguirPNG/SVG/Excel/JSON.
3. ImportaciónJSON normal/merge y exportación global: cierre pendiente del plan existente; no presentarlos como equivalentes a backupPostgreSQL.
4. Historial/compensación/rehacer: conservar revisión/ámbitos; no restaurar un estado offline antiguo sobre cambios ajenos.
5. Ajustes, leyenda, zoom, orientación y atajos: comprobar los identificadoresO-/PAR- existentes antes de abrir tareas duplicadas.

No se ha reejecutado la auditoría completa de302acciones ni se han portado en este lote todos sus pendientes. No se añaden1000tareas ni pesos por botones.

## Pruebas, límites y continuidad

[Resultados del lote](../evidence/s1-20261103/alemania-racks/RESULTADOS.md), con revisión independiente del catálogo, del layout y de los tres ejemplos. Datos51extremos/sesiones/cables comprobados en PostgreSQL17.11 nuevo; reproducción visual en Edge separada de persistenciaAPI. Ninguna prueba automatizada sustituye los resultados de Wascar.

**Pendiente antes de verlo instalado en D:** candidataWindows44 completa, compatibilidad de distribución/operadores, ensayo de actualización/Restore y autorización del destino. No copiarSQL/DLL/JS sueltos sobreD. El paquete14-r2/esquema43 existente no transporta estos perfiles. No se genera un instalador parcial para aparentar esa integración.

Se pospone el paso9 por esta petición. Índice de cierre conservado: **14,76/100**, sin porcentaje global nuevo ni crédito por ampliar catálogo o mejorarCSS.
