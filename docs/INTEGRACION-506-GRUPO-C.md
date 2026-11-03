# Selección 506 · grupo C · firewalls, routers y NAS

01.11.2026. **50 perfiles nuevos y 100 caras** en desarrollo de esquema31. [Abrir los modelos](../VER-SELECCION-506-C.html) · [Probar el buscador](../VER-SELECTOR-CATALOGO-C.html) · [Cobertura vigente](COBERTURA-MODELOS-ELEGIDOS.md).

## Resultado y alcance

El grupo suma **673 extremos: 449 RJ45, 177 SFP/SFP+ y 47 entradas AC fijas**. Son 34 equipos de rack (24 de 1 U y 10 de 2 U) y 16 de sobremesa con soporte explícito. No se fuerza 1 U en los modelos altos. DS918+ necesita la bandeja de 5 U por sus cotas; no cabe en la cavidad baja de 60 mm.

La cartera total alcanza **523 comerciales**, además de 5 sintéticos. De los 506 modelos originales se cubren **168 (33,20%), 338 pendientes**. Los 355 comerciales adicionales quedan separados; superar 500 en la cartera no significa haber completado los 506 elegidos ni todas las variantes físicas.

Revisión exacta `selected506c-20261101-v1`; nueva semilla031. SQL 001–030 y definiciones anteriores se conservan. La instalación con MFA y la QA de Wascar no se actualizan con esta entrega.

## Cómo revisar

Extrae el ZIP en una carpeta nueva. Abre **VER-SELECCION-506-C.html** con Edge/Chrome, conservando **PERFILES-SELECCION-506-C** junto a él. En la parte superior izquierda busca fabricante, modelo o SKU; selecciona un resultado. En el centro revisa dimensiones, montaje, **Frontal** y **Trasera**. Despliega **Alcance y límites de las fuentes**: una referencia comunitaria o de familia no autentica una revisión física.

Pulsa una boca y un extremo de prueba compatible para ver el cable y su ancla. AC requiere una salida de prueba. Los conectores dibujados inertes no crean cables. En **Tu revisión de este modelo** marca Pass/Not Pass/No probado y escribe tu observación; a la izquierda pulsa **Exportar mis resultados JSON**. Guarda `RackClick-Revision-Visual-506C.json` separado de los lotes anteriores.

Abre **VER-SELECTOR-CATALOGO-C.html**, con **PREVIEW-SELECTOR-CATALOGO-C** al lado. Es el buscador de producción en una demostración local de 528 definiciones: escribe «sofos», Fortinet, Synology o un SKU. La lista tiene desplazamiento interno y los detalles están plegados. Flechas y Enter eligen; Escape cierra la lista. Cambiar la búsqueda invalida el producto anterior. **Revisar selección** sólo muestra el comando propuesto; no guarda inventario ni llama al servidor. Para plantillas propias se conserva el flujo independiente **Mis plantillas privadas** del inventario. [Reglas del selector](SELECTOR-CATALOGO-COMPACTO.md).

## Configuraciones y límites importantes

- En FortiGate 80F y las series 100 con medios compartidos, ISR y USG-PRO-4 se representa una configuración óptica activa explícita. Cobre alternativo está dibujado inerte; no hay dos conexiones simultáneas por combo ni cambio automático de medio.
- Las fichas primarias corrigen conteos comunitarios: FG201F tiene 18 RJ45 y FG800D tiene 26 RJ45. Los puertos bypass son físicos documentados; no se simula su puente eléctrico. En 800D se incluye una sola AC de base; el segundo módulo opcional permanece inerte.
- TS-883XU-RP incluye la SmartNIC de fábrica de 2 SFP+ 10G; TVS-EC1580MU-SAS-RP conserva sólo 4 GE y no añade 10G opcional. Los dos llevan sus dos AC fijas. C8300 conserva la configuración de doble AC respaldada por el fabricante, aunque una foto comunitaria sólo muestre una fuente.
- PSU opcionales, bahías vacías, SAS/eSATA/USB, DC externo, RPS y consola serie no se convierten en Ethernet/AC ni en equipos instalados. Los discos se dibujan como forma de carcasa; no se afirma RAID o capacidad instalada.
- UDM-Pro utiliza figuras oficiales separadas; una imagen archivada era frontal con reflejo, no trasera. ASR1002-X conserva aviso de frontal de familia/otra variante. TL-SG105E representa V5 explícita; la revisión del registro original no estaba confirmada. Se conserva la discrepancia documental de altura del FG310B y los avisos de PDFs originales del fabricante alojados en espejo de proveedor.
- Chateau5Gax queda pendiente: no se fuerza la torre con antenas en la bandeja actual ni se gira sin fundamento. Se sustituyó en esta tanda por TL-SG105E, también de la selección original. hAP acLite TC sí usa una posición horizontal respaldada.
- `gn` es ordinal lógico dentro de un grupo, no identidad física ni etiqueta de fabricante. La boca se enlaza por grupo y ordinal al UUID exacto; se conservan por separado rótulos impresos y etiquetas editables. PoE describe documentación, no telemetría ni negociación.

## Pruebas y disponibilidad

Build Release con SDK 10.0.401, cero errores/advertencias; 10 pruebas C# y 902 Node aprobadas. PostgreSQL 17.11: migración30→31 conserva 478 definiciones y 473 instancias comerciales anteriores; fresh31 crea los 50 perfiles y sus 673 extremos y guarda 132 cables (50 RJ45 / 35 SFP / 47 AC). Se comprueban replay, conflicto412, revisión422, lector403, rollback, cuenta SQL sin DDL/DML del catálogo, otra sesión y persistencia tras reiniciar el host. Edge inspecciona 100 caras y crea otro equipo desde el buscador real.

[Detalle y atribución de pruebas](../evidence/s1-20261101/integracion506c/RESULTADOS.md). La revisión independiente está separada de la implementación; no es la aceptación de Wascar.

Los visores son locales, no instaladores. No copiar DLL/SQL aislados a un servidor. Faltan 338 perfiles, las ampliaciones de conectores/montaje/módulos que correspondan, consumidores, distribución/Restore 31, paquete Windows completo y QA final. Después se ejecutará el plan de al menos 50 clientes con cobertura completa. El índice del cierre restante sigue **9,76/100**, sin nuevo porcentaje global por contar modelos.

## Modelos del grupo C

| Fabricante | Modelo seleccionado | SKU/configuración | Montaje | Extremos conectables |
|---|---|---|---|---|
| Barracuda | F80B | F80B | Sobremesa / bandeja | 5 RJ45 |
| Cisco | ASR1001 | ASR1001 | 1 U | 1 RJ45 + 4 SFP + 2 AC |
| Cisco | ASR1001-HX | ASR1001-HX | 1 U | 1 RJ45 + 16 SFP + 2 AC |
| Cisco | ASR1001-X | ASR1001-X | 1 U | 1 RJ45 + 8 SFP + 2 AC |
| Cisco | ASR1002-X | ASR1002X-5G-K9 | 2 U | 1 RJ45 + 6 SFP + 2 AC |
| Cisco | Catalyst 8300-1N1S-4T2X | C8300-1N1S-4T2X | 1 U | 5 RJ45 + 2 SFP + 2 AC |
| Cisco | ISR4321 | ISR4321/K9 | 1 U | 2 RJ45 + 1 SFP |
| Cisco | ISR4331 | ISR4331/K9 | 1 U | 2 RJ45 + 2 SFP + 1 AC |
| Cisco | ISR4351 | ISR4351/K9 | 2 U | 1 RJ45 + 3 SFP + 1 AC |
| Fortinet | FortiGate 1000D | FG-1000D | 2 U | 18 RJ45 + 18 SFP + 2 AC |
| Fortinet | FortiGate 100D | FG-100D | 1 U | 20 RJ45 + 2 SFP + 1 AC |
| Fortinet | FortiGate 100E | FG-100E | 1 U | 20 RJ45 + 2 SFP + 1 AC |
| Fortinet | FortiGate 100EF | FG-100EF | 1 U | 14 RJ45 + 8 SFP + 1 AC |
| Fortinet | FortiGate 100F | FG-100F | 1 U | 18 RJ45 + 10 SFP + 2 AC |
| Fortinet | FortiGate 101E | FG-101E | 1 U | 20 RJ45 + 2 SFP + 1 AC |
| Fortinet | FortiGate 1200D | FG-1200D | 2 U | 18 RJ45 + 20 SFP + 2 AC |
| Fortinet | FortiGate 140E-POE | FG-140E-POE | 1 U | 42 RJ45 + 2 SFP + 1 AC |
| Fortinet | FortiGate 200D | FG-200D | 1 U | 19 RJ45 + 2 SFP + 1 AC |
| Fortinet | FortiGate 201F | FG-201F | 1 U | 18 RJ45 + 12 SFP + 2 AC |
| Fortinet | FortiGate 310B | FG-310B | 1 U | 10 RJ45 + 1 AC |
| Fortinet | FortiGate 400F | FG-400F | 1 U | 18 RJ45 + 16 SFP + 2 AC |
| Fortinet | FortiGate 500D | FG-500D | 1 U | 10 RJ45 + 8 SFP + 1 AC |
| Fortinet | FortiGate 50G | FG-50G | Sobremesa / bandeja | 5 RJ45 |
| Fortinet | FortiGate 800D | FG-800D | 1 U | 26 RJ45 + 10 SFP + 1 AC |
| Fortinet | FortiGate 80D | FG-80D | Sobremesa / bandeja | 4 RJ45 |
| Fortinet | FortiGate 80F | FG-80F | Sobremesa / bandeja | 8 RJ45 + 2 SFP |
| MikroTik | RB4011iGS+RM | RB4011iGS+RM | 1 U | 10 RJ45 + 1 SFP |
| MikroTik | hAP ac lite TC | RB952Ui-5ac2nD-TC | Sobremesa / bandeja | 5 RJ45 |
| MikroTik | hAP ax S | E62iUGS-2axD5axT | Sobremesa / bandeja | 5 RJ45 + 1 SFP |
| QNAP | TS-883XU-RP | TS-883XU-RP | 2 U | 4 RJ45 + 2 SFP + 2 AC |
| QNAP | TVS-EC1580MU-SAS-RP | TVS-EC1580MU-SAS-RP | 2 U | 4 RJ45 + 2 AC |
| Sophos | XG 135 | XG 135 | Sobremesa / bandeja | 8 RJ45 + 1 SFP |
| Sophos | XGS 116 | XGS 116 | Sobremesa / bandeja | 8 RJ45 + 1 SFP |
| Sophos | XGS 126 | XGS 126 | Sobremesa / bandeja | 12 RJ45 + 2 SFP |
| Sophos | XGS 136 | XGS 136 | Sobremesa / bandeja | 12 RJ45 + 2 SFP |
| Sophos | XGS 138 | XGS 138 | Sobremesa / bandeja | 6 RJ45 + 2 SFP |
| Synology | DS918+ | DS918+ | Sobremesa / bandeja | 2 RJ45 |
| Synology | FS6400 | FS6400 | 2 U | 4 RJ45 + 2 AC |
| Synology | RS2416RP+ | RS2416RP+ | 2 U | 4 RJ45 + 2 AC |
| Synology | RS3614xs+ | RS3614xs+ | 2 U | 4 RJ45 + 2 AC |
| Synology | RS815+ | RS815+ | 1 U | 4 RJ45 + 1 AC |
| TP-Link | TL-SG105E | TL-SG105E | Sobremesa / bandeja | 5 RJ45 |
| Ubiquiti | UDM-Pro | UDM-PRO | 1 U | 9 RJ45 + 2 SFP + 1 AC |
| Ubiquiti | UNAS Pro | UNAS-Pro | 2 U | 1 RJ45 + 1 SFP + 1 AC |
| Ubiquiti | UniFi Cloud Gateway Ultra | UCG-Ultra | Sobremesa / bandeja | 5 RJ45 |
| Ubiquiti | UniFi Dream Machine Pro Max | UDM-PRO-MAX | 1 U | 9 RJ45 + 2 SFP + 1 AC |
| Ubiquiti | UniFi Dream Machine Pro Special Edition | UDM-SE | 1 U | 9 RJ45 + 2 SFP + 1 AC |
| Ubiquiti | UniFi Security Gateway Pro | USG-PRO-4 | 1 U | 2 RJ45 + 2 SFP + 1 AC |
| WatchGuard | Firebox T25 | Firebox T25 | Sobremesa / bandeja | 5 RJ45 |
| WatchGuard | Firebox T45 | Firebox T45 | Sobremesa / bandeja | 5 RJ45 |
