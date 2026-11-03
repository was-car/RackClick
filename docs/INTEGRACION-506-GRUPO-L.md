# Grupo L · integración de los62 modelos restantes

02.11.2026. [Abrir los62 modelos](../VER-SELECCION-506-L.html) · [Selector compacto](../VER-SELECTOR-CATALOGO-L.html) · [Evidencia](../evidence/s1-20261102/integracion506l/RESULTADOS.md).

La selección original llega a506/506. Grupo L:62 configuraciones/124caras/1673 extremos; revisión del receptor USP separada, sin otro modelo seleccionado. Catálogo43:868 definiciones/revisiones,862 revisiones comerciales y861 modelos comerciales distintos. Los355 adicionales quedan fuera del denominador506. Integración de desarrollo comprobada; paquete instalado/QA/adopción siguen pendientes.

## Revisión local de Wascar

1. Abre VER-SELECCION-506-L.html y conserva a su lado PERFILES-SELECCION-506-L. En el buscador superior izquierdo escribe fabricante o SKU; pulsa un resultado.
2. En el centro cambia Frontal/Trasera; despliega configuración, montaje y límites. Cada boca tiene su identidad y tooltip; conectar extremos de prueba en este visor no escribe en servidor.
3. Revisa los armarios vacíos (capacidad U, cero equipos), PDU lateral, montaje compartido, pared y DIN. Los detalles secundarios se despliegan. En Moxa el detalle superior se rotula como tal; no es una trasera inventada.
4. En Tu revisión de este modelo marca Pass/Not Pass/No probado y escribe observaciones. Exporta tus resultados JSON desde la izquierda. El visor conserva las observaciones en el navegador.
5. Abre VER-SELECTOR-CATALOGO-L.html con PREVIEW-SELECTOR-CATALOGO-L al lado. Busca fabricante/modelo y elige revisión exacta. La lista tiene desplazamiento interno. Revisa sala para armario/pared/DIN y rack, posición o padre según montaje.
6. Servidor: espera la candidata completa identificada43 o superior. QA-162 sigue planificada en la instalación actual; no copies DLL/SQL sueltos. Una vez entregada, Clientes→rack/sala→Añadir hardware de referencia; elige modelo/revisión, nombre y destino. Espera Guardado por el servidor, conecta por Click-Click, pulsa F5 y contrasta otra cuenta. No hay que repetir ahora la instalación en tu VM.

## Contrato conservado

- rack/shelf ocupa U reales. Desktop requiere bandeja y hueco nominal conocido; las dimensiones desconocidas no prueban que cabe.
- rackContainer crea un rack real vacío con capacidad, no un dispositivo que ocupa todas las U. vertical0U reserva un lateral y sharedU un padre válido; no duplican ocupación U ni permiten dos hijos en el mismo slot.
- wall/pole/din/floor se asocian a sala, sin rack ni U ficticias. Los modelos L actuales usan pared y DIN; el resto son tipos del contrato, no altas ficticias.
- AC y DC se separan. DC genérico, USB-PD y UniFi SmartPower exigen sistema coincidente y roles opuestos. La forma del conector no certifica tensión, pinout o circuito eléctrico.
- Tipos físicos serie/IPC/IDC/fibra/SAS/DSL/telefonía no se convierten en RJ45 por parecerse. La continuidad declarada es documental; no produce trazado o conmutación interna.
- Bases vacías no reciben módulos inventados. Configuraciones modulares publicadas son BOM fijas. Las fuentes de cada modelo indican cotas desconocidas, variantes y geometría no comprobada.
- Observaciones menores: rótulos Core densos en Belden y algunos títulos decorativos del Atlas. Los puertos mantienen UUID/tooltips; pendientes de mejora visual, sin ocultar reservas.

## Verificación realizada

PG17.11/Windows: migración41→43 preserva805 definiciones/799 instancias; nueva base62 modelos, cuatro duplicados de armarios vacíos,17 enlaces API+17 GUI,124caras,45 rechazos de comandos, permisos, rollback, recarga, segunda cuenta y reinicio del proceso. Se conserva la revisión independiente y los intentos fallidos como evidencia. Esta matriz no afirma cablear cada extremo ni probar todos los navegadores/idiomas o reiniciar Windows.

| Fabricante | SKU | Montaje | Extremos |
|---|---|---|---|
| APC | AP7950B | vertical0U | 19 |
| APC by Schneider Electric | AR3100 | rackContainer | 0 |
| Adtran | 1287835F1 | wall | 8 |
| Adtran | 17004660F1 | rack | 7 |
| Avaya | 700476005 | rack | 24 |
| Belden | RV6PPF1U24BK | rack | 48 |
| Belden | RV6PPF2U48BK | rack | 96 |
| Cabeus | PDU-8P | rack | 9 |
| Cabeus | PL-24-Cat-5e-Dual-IDC | rack | 48 |
| Cable Matters | 180013 | rack | 0 |
| Calient | s320 | rack | 645 |
| Ciena | 170-8110-900 | rack | 30 |
| Ciena | 170-8140-900 | rack | 56 |
| Ciena | 186-1010-900 | rack | 15 |
| Ciena | NTK803DA | rack | 0 |
| Ciena | NTK803FA | rack | 0 |
| Cisco | ASR1009-X | rack | 18 |
| Cisco | ASR1013 | rack | 18 |
| DIGITUS | DN-19 16-U-SW | rackContainer | 0 |
| DITEK | DTK-RM12EXTS | rack | 24 |
| DITEK | DTK-RM24NETS | rack | 48 |
| DITEK | DTK-WM8NETS | wall | 16 |
| Datwyler | 418019 | rack | 0 |
| Datwyler | 418021 | rack | 0 |
| Datwyler | 440042 | rack | 0 |
| Dell | PowerProtect-DP4400 | rack | 13 |
| Dell | PowerScale-F710 | rack | 9 |
| Eltex | MES3510P | din | 14 |
| HPE | Q1J07A | rack | 6 |
| HPE | R7G17A | rack | 6 |
| Huawei | D3V6-192G-SAS | rack | 26 |
| LANCOM | 1781VA | desktop | 8 |
| LANCOM | 1783VA-4G | desktop | 11 |
| LANCOM | 62111 | desktop | 7 |
| LANCOM | 62115 | desktop | 11 |
| Lenovo | 7DHE | rack | 11 |
| MikroTik | S53UG+M-5HaxD2HaxD-TC&RG502Q-EA | desktop | 6 |
| Moxa | EDS-408A-SS-SC-T | din | 10 |
| Moxa | EDS-P510 | din | 13 |
| NetApp | AFF-C30A-100-C | rack | 12 |
| NetApp | AFF-C60A-100-C | rack | 12 |
| NetApp | AFFA150 | rack | 20 |
| NetApp | DE460C | rack | 10 |
| NetApp | FAS2720 | rack | 20 |
| NetApp | NS224-T-0-24-CF-C | rack | 6 |
| NetApp | StorageGRID-SG5812 | rack | 12 |
| Nokia | 3HE13571CA | rack | 22 |
| Nokia | 3HE18609CA | rack | 38 |
| Palo Alto Networks | PA-7050 | rack | 34 |
| Rittal | 5306.122 | rackContainer | 0 |
| Smartoptics | DCP-M40-PAM4-ER | rack | 50 |
| Sophos | SD-RED 60 | desktop | 9 |
| StarTech.com | RK1236BKF | rackContainer | 0 |
| Supermicro | AS-3015MR-H8TNR | rack | 20 |
| TP-Link | archer-ax1800 | desktop | 6 |
| Telco Systems | TM8104 | rack | 44 |
| Ubiquiti | U7-Outdoor | wall | 1 |
| Ubiquiti | USP-PDU-Pro | rack | 25 |
| Ubiquiti | USP-RPS | rack | 8 |
| Vertiv | SA1-01002 | sharedU | 0 |
| WTI | CPM-1600-1-C | rack | 38 |
| Zyxel | P-660HNU-T1 | desktop | 6 |
