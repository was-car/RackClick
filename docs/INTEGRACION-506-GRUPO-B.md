# Integración de la selección 506 · grupo B

01.11.2026. Cincuenta perfiles nuevos, dos caras propias por modelo, y selector compacto en desarrollo. No es un instalador ni una actualización automática de la instalación de Wascar.

[Abrir los 50 modelos](../VER-SELECCION-506-B.html) · [Probar el selector](../VER-SELECTOR-CATALOGO.html) · [Cobertura vigente](COBERTURA-MODELOS-ELEGIDOS.md)

## Qué incluye

- Revisión exacta `selected506b-20261101-v1`, SQL 030 nuevo y catálogo C#/frontend consistente: 50 modelos, 100 caras y 1.248 extremos; 1.056 RJ45, 150 SFP/SFP+ y 42 entradas AC fijas.
- 27 equipos de rack y 23 de sobremesa con montaje explícito sobre una bandeja compatible. La reserva U de la bandeja no se duplica en el hijo.
- Total de desarrollo: 478 definiciones, 473 comerciales. Cobertura de la selección original: **118/506 (23,32%), 388 pendientes**. Los otros perfiles comerciales son modelos adicionales: no se suman como si completaran la lista elegida.
- Formas, colores, bancos y conectores dibujados como esquema plano propio a partir de referencias; no se pegan fotos operativas ni se sustituyen UUID por números de puerto ambiguos.

## Cómo revisar sin instalar

Extrae el ZIP de revisión en una carpeta nueva. Abre **VER-SELECCION-506-B.html** y conserva **PERFILES-SELECCION-506-B** junto a él. Busca en la columna izquierda, elige modelo, comprueba frontal/trasera y despliega **Alcance y límites de las fuentes**. Puedes pulsar bocas y extremos sintéticos compatibles para revisar anclas; esos cables locales no son conexiones guardadas en un servidor. Marca Pass/Not Pass/No probado y exporta `RackClick-Revision-Visual-506B.json`, separado de tus resultados anteriores.

Abre **VER-SELECTOR-CATALOGO.html**, con **PREVIEW-SELECTOR-CATALOGO-B** al lado. Se usa el mismo componente de desarrollo. Escribe «sofos», Fortinet, Aruba, un modelo o SKU: aparece una lista filtrada con desplazamiento interno, no una página con cientos de filas. Flechas y Enter eligen, Escape cierra la lista. El siguiente Escape conserva la cancelación normal del formulario en el servidor. Los detalles técnicos están plegados inicialmente. Cambiar la búsqueda invalida el modelo anterior; no se elige una coincidencia aproximada ni se crea un perfil desde texto libre.

El botón **Revisar selección / Review selection** de esta demostración sólo muestra el comando propuesto; no conecta a una API ni guarda inventario. El idioma se cambia arriba. [Contrato y plantillas propias](SELECTOR-CATALOGO-COMPACTO.md).

## Límites físicos y de fuente

C1300-12XS y Aruba J9777A/J9774A representan una configuración fija con SFP activo. Sus alternativas cobre compartidas están dibujadas inertes: no son puertos adicionales simultáneos. El cambio de medio se mantiene pendiente de contrato/UX específico.

Las cuatro jaulas EX4000 son físicas y reconfigurables; la herramienta no configura Virtual Chassis. Los cinco Arista llevan cuatro SFP+ 10G y dos entradas AC fijas, sin inferir SFP28 o fuentes opcionales. DGS-3130-54PS usa explícitamente la revisión B de 430 mm; la foto comunitaria no autentica esa revisión. MS120-24P conserva SFP de 1G aunque el YAML comunitario dijera otra velocidad. Las imágenes comunitarias que muestran variantes o rótulos contradictorios no prevalecen sobre el manual del SKU. En particular, la frontal comunitaria asignada al C1300-12XS muestra cobre de otra variante o familia; el dibujo de 12 SFP se fundamenta en la tabla oficial y esa imagen no se trata como coincidencia exacta.

DC externo, USB, consola serie, RPS, módulos opcionales y aberturas pasivas no se convierten en Ethernet, AC, fuentes instaladas o ventiladores activos ficticios. PoE describe capacidades y estados de documentación, no negociación ni telemetría. Se conservan avisos de familia/revisión no confirmada. El OS6400-24 sigue pendiente por sus medios compartidos y stacking; se reemplazó en este grupo por el Extreme4220-24T ya presente en la selección original.

## Pruebas y revisión

El resultado definitivo se registra en [evidencia del grupo](../evidence/s1-20261101/integracion506b/RESULTADOS.md). Entorno: Windows, SDK10.0.401, PostgreSQL17.11 y Node24.21.0 fijados. Las pruebas de laboratorio y la revisión independiente se atribuyen por separado; no representan la aceptación de Wascar.

## Qué falta

Completar los 388 modelos restantes; ampliar contratos de conectores/montaje/módulos cuando lo exijan sus datos; integrar consumidores, operadores, distribución, backup/Restore y paquete Windows completo; aceptación final. Después de completar todos los perfiles, crear el laboratorio integral de al menos 50 clientes con cobertura de modelos y conexiones. No copiar DLL ni SQL sueltos al servidor ni sustituir su base o cuenta MFA.

El índice del cierre restante continúa en **9,76/100**, sin incremento automático ni nuevo porcentaje global por perfiles, pruebas o documentos.

## Modelos de este grupo

| Fabricante | Modelo de la selección | SKU/configuración | Montaje | Extremos conectables |
|---|---|---|---|---|
| Arista | CCS-720DP-24S-2F | CCS-720DP-24S-2F | 1 U | 25 RJ45 + 4 SFP + 2 AC |
| Arista | CCS-720DP-24ZS-2F | CCS-720DP-24ZS-2F | 1 U | 25 RJ45 + 4 SFP + 2 AC |
| Arista | CCS-720DP-48S-2F | CCS-720DP-48S-2F | 1 U | 49 RJ45 + 4 SFP + 2 AC |
| Arista | CCS-720DP-48ZS-2F | CCS-720DP-48ZS-2F | 1 U | 49 RJ45 + 4 SFP + 2 AC |
| Arista | CCS-720DT-24S-2F | CCS-720DT-24S-2F | 1 U | 25 RJ45 + 4 SFP + 2 AC |
| Cisco | Catalyst 1300-12XS | C1300-12XS | Sobremesa / bandeja | 1 RJ45 + 12 SFP + 1 AC |
| Cisco | Catalyst 1300-12XT-2X | C1300-12XT-2X | Sobremesa / bandeja | 13 RJ45 + 2 SFP + 1 AC |
| Cisco | Catalyst 1300-16P-4X | C1300-16P-4X | Sobremesa / bandeja | 16 RJ45 + 4 SFP + 1 AC |
| Cisco | Catalyst 1300-48P-4X | C1300-48P-4X | 1 U | 48 RJ45 + 4 SFP + 1 AC |
| Cisco | Catalyst C9200CX-12P-2X2G | C9200CX-12P-2X2G | Sobremesa / bandeja | 14 RJ45 + 2 SFP + 1 AC |
| Cisco | Meraki MS120-24P | MS120-24P-HW | 1 U | 25 RJ45 + 4 SFP + 1 AC |
| D-Link | DGS-1100-08 | DGS-1100-08 | Sobremesa / bandeja | 8 RJ45 |
| D-Link | DGS-1100-08PLV2 | DGS-1100-08PLV2 | Sobremesa / bandeja | 8 RJ45 |
| D-Link | DGS-1100-08V2 | DGS-1100-08V2 | Sobremesa / bandeja | 8 RJ45 |
| D-Link | DGS-3130-54PS | DGS-3130-54PS | 1 U | 51 RJ45 + 4 SFP + 1 AC |
| Extreme Networks | 4220-12P-4X | 4220-12P-4X | 1 U | 13 RJ45 + 4 SFP + 1 AC |
| Extreme Networks | 4220-24P-4X | 4220-24P-4X | 1 U | 25 RJ45 + 4 SFP + 1 AC |
| Extreme Networks | 4220-24T-4X | 4220-24T-4X | 1 U | 25 RJ45 + 4 SFP + 1 AC |
| Extreme Networks | 5320-48P-8XE | 5320-48P-8XE | 1 U | 48 RJ45 + 8 SFP + 1 AC |
| Grandstream | GWN7803P | GWN7803P | 1 U | 24 RJ45 + 4 SFP + 1 AC |
| HPE | Aruba 2530-8G | J9777A | Sobremesa / bandeja | 8 RJ45 + 2 SFP |
| HPE | Aruba 2530-8G-PoE+ | J9774A | Sobremesa / bandeja | 8 RJ45 + 2 SFP |
| HPE | Aruba 2930F-12G-PoE+-2SFP+ | JL693A | Sobremesa / bandeja | 14 RJ45 + 2 SFP + 1 AC |
| HPE | Aruba 2930F-48G-PoE+-4SFP | JL557A | 1 U | 48 RJ45 + 4 SFP + 1 AC |
| HPE | Aruba 2930F-8G-PoE+-2SFP+ | JL258A | Sobremesa / bandeja | 8 RJ45 + 2 SFP |
| HPE | Aruba 6200F-24G-4SFP+ | JL724A | 1 U | 25 RJ45 + 4 SFP + 1 AC |
| HPE | Aruba 6200F-48G-4SFP+ | JL726A | 1 U | 49 RJ45 + 4 SFP + 1 AC |
| Juniper | EX2300-48P | EX2300-48P | 1 U | 49 RJ45 + 4 SFP + 1 AC |
| Juniper | EX2300-C-12P | EX2300-C-12P | Sobremesa / bandeja | 13 RJ45 + 2 SFP + 1 AC |
| Juniper | EX4000-12MP | EX4000-12MP | Sobremesa / bandeja | 13 RJ45 + 4 SFP + 1 AC |
| Juniper | EX4000-12P | EX4000-12P | Sobremesa / bandeja | 13 RJ45 + 4 SFP + 1 AC |
| Juniper | EX4000-12T | EX4000-12T | Sobremesa / bandeja | 13 RJ45 + 4 SFP + 1 AC |
| Juniper | EX4000-24MP | EX4000-24MP | 1 U | 25 RJ45 + 4 SFP + 1 AC |
| Juniper | EX4000-24P | EX4000-24P | 1 U | 25 RJ45 + 4 SFP + 1 AC |
| Juniper | EX4000-24T | EX4000-24T | 1 U | 25 RJ45 + 4 SFP + 1 AC |
| Juniper | EX4000-48MP | EX4000-48MP | 1 U | 49 RJ45 + 4 SFP + 1 AC |
| MikroTik | CRS112-8P-4S-IN | CRS112-8P-4S-IN | Sobremesa / bandeja | 8 RJ45 + 4 SFP |
| MikroTik | CRS326-24G-2S+RM | CRS326-24G-2S+RM | 1 U | 24 RJ45 + 2 SFP |
| MikroTik | CRS418-8P-8G-2S+RM | CRS418-8P-8G-2S+RM | 1 U | 17 RJ45 + 2 SFP + 2 AC |
| Netgear | GS105 | GS105 | Sobremesa / bandeja | 5 RJ45 |
| Netgear | GS108PEv3 | GS108PEv3 | Sobremesa / bandeja | 8 RJ45 |
| Netgear | GS108PP | GS108PP | Sobremesa / bandeja | 8 RJ45 |
| Netgear | GS308EP | GS308EP | Sobremesa / bandeja | 8 RJ45 |
| Netgear | ProSafe GS510TPP | GS510TPP | 1 U | 8 RJ45 + 2 SFP + 1 AC |
| Ruijie | RG-NBS3100-24GT4SFP-P | RG-NBS3100-24GT4SFP-P | 1 U | 24 RJ45 + 4 SFP + 1 AC |
| SNR | S5210G-24TX | s5210g-24tx | 1 U | 24 RJ45 + 4 SFP + 1 AC |
| TP-Link | SG3218XP-M2 V1 | 0132600339 | 1 U | 16 RJ45 + 2 SFP + 1 AC |
| TP-Link | TL-SG105 | TL-SG105 | Sobremesa / bandeja | 5 RJ45 |
| Zyxel | ES1100-8P | ES1100-8P | Sobremesa / bandeja | 8 RJ45 + 1 AC |
| Zyxel | GS-108B-v3 | GS-108B-v3 | Sobremesa / bandeja | 8 RJ45 |
