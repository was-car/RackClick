# Repetidores WLAN del mercado alemán

> **Actualización posterior de hoy:** los cambios ya están instalados en D45. [URL, comprobaciones y límites](ACTUALIZACION-D45-03-11-2026.md). El registro de desarrollo siguiente conserva el estado anterior a esa operación.

03.11.2026 · Ampliación solicitada por Wascar. Desarrollo de catálogo en esquema 45; D y E se conservan. No se instala ni publica nada en este lote.

## Qué se incorpora

Diez perfiles de cuatro fabricantes, elegidos a partir de sus fichas y manuales oficiales. Es una selección de equipos documentados para Alemania/EU, no una medición de cuota de mercado ni una lista completa de repetidores disponibles.

| Fabricante | Modelo o variante | Ubicación | Ethernet | Alimentación en el aparato |
|---|---|---|---:|---|
| FRITZ! | FRITZ!Repeater 600, DE | Enchufe/pared | 0 | Clavija EU integrada de dos pines |
| FRITZ! | FRITZ!Repeater 1200 AX, DE | Enchufe/pared | 1 × Gigabit | Clavija EU integrada de dos pines |
| FRITZ! | FRITZ!Repeater 2400, DE | Enchufe/pared | 1 × Gigabit | Clavija EU integrada de dos pines |
| FRITZ! | FRITZ!Repeater 3000 AX, DE | Sobremesa | 2 × Gigabit | Entrada DC; fuente externa |
| FRITZ! | FRITZ!Repeater 6000, DE | Sobremesa | 1 × 2,5 GbE + 1 × Gigabit | Entrada DC; fuente externa |
| TP-Link | RE605X EU | Enchufe/pared | 1 × Gigabit | Clavija EU integrada de dos pines |
| TP-Link | RE700X EU | Enchufe/pared | 1 × Gigabit | Clavija EU integrada de dos pines |
| devolo | WiFi 6 Repeater 3000 EU | Enchufe/pared | 1 × Gigabit | Clavija EU integrada de dos pines |
| devolo | WiFi 6 Repeater 5400 EU | Sobremesa | 2 × Gigabit | Entrada DC; fuente externa |
| Telekom | Speed Home WLAN, modelo 2021 | Sobremesa | 2 × Gigabit | Entrada DC; fuente externa |

Son **13 extremos Ethernet y 10 de alimentación**. El FRITZ!Repeater 600 no tiene LAN. Las bandas WiFi y radios Mesh no se convierten en puertos de cable, no generan conexiones automáticas y no simulan cobertura. Estos modelos devolo no se presentan como Powerline.

Los diez se crean como dispositivos finales **de sala**, sin U, rack, bandeja, padre o ranura implícitos. Los seis equipos de enchufe usan ubicación `wall`; los cuatro de sobremesa usan `tabletop`. La entrada DC no representa una entrada AC del aparato. `eu-2pin-plug` describe una clavija de dos pines, sin afirmar una certificación eléctrica o un estándar mecánico concreto para todos los SKU.

## Cómo verlos y buscarlos

Abrir [VER-REPETIDORES-ALEMANIA-01.html](../VER-REPETIDORES-ALEMANIA-01.html), junto a su carpeta de archivos, o extraer el ZIP de revisión completo y abrir ese mismo HTML. Utiliza el buscador compacto por marca, familia, modelo o SKU. También acepta «repetidor», «repetidores», «repeter», «Repeater», «Verstärker», «WLAN-Verstärker», «répéteur» y las formas FRITZ!Repeater/FRITZ Repeater/AVM.

Elegir un perfil no crea datos. Frontal/Trasera, los conectores y Ampliar vista usan los componentes del producto con datos locales. Pulsar un puerto identifica su grupo y ordinal; este visor no guarda cables en PostgreSQL. Los controles están en ES/DE/EN y los nombres comerciales se conservan literalmente.

La vista de sala mantiene objetivos de conexión de al menos 24 px. Se ajusta al espacio y permite ampliar la representación sin cambiar cotas ni montaje. El detalle trasero agrupa tomas para operarlas: **no afirma que una toma físicamente inferior o lateral esté en la trasera**. Las reservas de cada perfil siguen accesibles en detalles.

## Fuentes y límites físicos

- FRITZ!: [1200 AX](https://fritz.com/products/fritz-repeater-1200-ax-20002974/), [3000 AX](https://fritz.com/products/fritz-repeater-3000-ax-20002988/) y [catálogo oficial](https://business.fritz.com/downloads/de/FRITZ_auf_einen_Blick.pdf). Las referencias exactas de cada modelo y sus observaciones están en [fritz-reference.md](../development/hardware/german-repeaters/fritz-reference.md).
- TP-Link: [RE605X](https://www.tp-link.com/de/home-networking/range-extender/re605x/#specifications) y [RE700X](https://www.tp-link.com/de/home-networking/range-extender/re700x/#specifications). La ficha EU general no acredita por sí sola una revisión V1/V2/V3. Sus ejes W × D × H se normalizan expresamente; las medidas no certifican el espacio de antenas desplegadas.
- devolo: [3000](https://www.devolo.de/de/produkte/wifi-6-repeater-3000) y [5400](https://www.devolo.de/de/produkte/wifi-6-repeater-5400). Se conservan sus tres medidas como desconocidas en el contrato: las referencias consultadas mezclan ejes, cuerpo y otras especificaciones. No se deduce el encaje de una fotografía ni se convierte una tabla AC contradictoria en un conector del 5400.
- Telekom: [ficha oficial Speed Home WLAN 2021](https://www.telekom.com/resource/blob/627822/c83408f468252af4369eea285310d15a/dl-produktsteckbrief-speed-home-data.pdf). No se mezcla con el manual de la segunda generación.

Las carcasas son vectores propios que toman forma y color como referencia, con reservas visibles; no son fotografías redistribuidas, planos de fabricación ni certificación de encaje. LED y botones decorativos son inertes. Las fichas/manuales descargados para investigar quedan privados y no entran en el ZIP de revisión.

## Integración y comprobaciones

- Esquema nuevo 45, generado desde autoría, lock y manifiesto propios. Las migraciones 1–44 y las 874 revisiones anteriores se conservan. El catálogo de desarrollo suma **884 revisiones / 877 modelos comerciales distintos**; la selección original de 506 no cambia.
- PostgreSQL 17.11 independiente: migración 44→45 idempotente, creación de dos ejemplares de cada modelo en sala, 23 extremos por conjunto y 19 conexiones representativas (9 Ethernet y 10 de energía, con fuente sintética sólo para comprobar roles). Identidades, metadatos y conexiones se conservan en otra sesión y después de reiniciar ASP.NET. Rechazos 403/404/422/409 sin mutación y catálogo sin DDL/DML para el rol de ejecución.
- Build .NET con SDK 10.0.401: cero errores y advertencias. Frontend compilado con las dependencias existentes. Regresión de hardware: 179/179; foco del generador: 18/18. No se suman pruebas solapadas como cobertura independiente.
- Edge: 10 modelos × 2 caras × 3 anchos, 69 representaciones de extremos, nueve búsquedas y tres idiomas. La revisión independiente contrasta el contrato, los archivos históricos, las geometrías y la ausencia de desplazamiento innecesario. Corrigió el cuerpo circular de Telekom; también se recolocaron tres rótulos del 6000.

[Evidencia, hashes, incidencias y dictamen](../evidence/s1-20261103/repetidores-alemania/RESULTADOS.md).

## Qué falta

QA-171 sigue **planificado** para Wascar. Falta transportar el desarrollo 44/45 en una candidata Windows completa y compatible y ensayarla antes de actualizar D. Ni el HTML ni este ZIP son instaladores. No se copian DLL/SQL/JS sueltos a la instalación conservada.

Las siguientes familias de operadores alemanes y las acciones offline pendientes continúan en [el sondeo y la cola existente](CATALOGO-ALEMANIA-Y-RACKS-03-11-2026.md). No se ha reejecutado la comparación completa de 302 acciones. El paso 9 sigue sin ejecutarse. Índice de cierre: **14,76/100**, sin crédito nuevo por ampliar catálogo ni porcentaje global recalculado.
