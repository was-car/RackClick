# Grupo K · 52 configuraciones de cinco familias

01.11.2026. [Abrir los 52 modelos](../VER-SELECCION-506-K.html) · [Selector compacto](../VER-SELECTOR-CATALOGO-K.html) · [Método reutilizable](METODO-CATALOGO-POR-FAMILIAS.md) · [Familias pendientes](FAMILIAS-CATALOGO-PENDIENTES.md).

**52 perfiles, 104 caras y 920 extremos**: 28 UPS/ATS/PDU, seis paneles Panduit con IDC, diez accesorios vacíos, dos NAS TerraMaster y seis consolas serie. Desarrollo **41: 805 definiciones /799 comerciales**; selección original **444/506 (87,75 %), 62 pendientes**. Los 355 comerciales adicionales se cuentan aparte.

## Revisar paso a paso

1. Extrae el ZIP en una carpeta nueva. Conserva juntos **VER-SELECCION-506-K.html** y **PERFILES-SELECCION-506-K**. Abre el HTML en Edge o Chrome.
2. En el panel izquierdo escribe fabricante o SKU y pulsa un resultado. En el centro revisa frontal y trasera; despliega **Alcance y límites de las fuentes de este modelo**. El enlace **HTML individual de este modelo** abre sólo ese equipo.
3. Revisa cantidades, posiciones y rótulos. Serie no es Ethernet: Digi usa diez contactos; Lantronix no gana un puerto adicional por compartir consola con puerto1. USB, AUI, sensores, baterías/DC y ranuras vacías permanecen inertes si no se modelan expresamente.
4. Pulsa una boca y un extremo de prueba del mismo tipo. Para potencia usa roles opuestos: hay **Entrada AC de prueba** y **Salida AC de prueba**. El visor no guarda en servidor ni certifica un cable o circuito. IDC y RJ45 son extremos distintos; la correspondencia del panel es documental, sin cable interno ni trazado automático.
5. Bajo las caras, en **Tu revisión de este modelo**, marca Pass/Not Pass/No probado y escribe observaciones. En la izquierda pulsa **Exportar mis resultados JSON** y guarda `RackClick-Revision-Visual-506K.json`. Importar en casillas vacías conserva tus notas anteriores.
6. Abre **VER-SELECTOR-CATALOGO-K.html** con **PREVIEW-SELECTOR-CATALOGO-K** al lado. Busca APC, Panduit, TerraMaster, Opengear, CommScope o SKU. La lista tiene desplazamiento interno. Despliega **Detalles del modelo y conectores**: configuración/BOM, cotas y límites quedan visibles antes de confirmar. El comando de **Revisar selección** es una demostración, no una escritura al servidor.
7. **Sólo con candidata completa identificada41 o superior**: Clientes → rack sintético → **Añadir hardware de referencia**. Elige revisión `selected506k-20261101-v1`, nombre/rack y, para NAS, un soporte compatible libre. Espera **Guardado por el servidor**. Conecta por Click-Click, recarga F5 y abre otra sesión autorizada. Un lector no debe editar. No copies DLL o SQL aislados a la instalación nativa.

## Límites de configuración

- **Potencia:** 50 entradas y247 salidas en el conjunto, incluidos los nueve AC de las consolas. IEC/NEMA/IEC60309 describen la forma documentada; no inventan pinout, extremo del cordón, voltaje, corriente, protección, conmutación, redundancia ni circuito. Un cable genérico puede tener extremos distintos; C19→C14 no se rechaza por comparar dibujos. Los roles inlet/outlet sí se validan. No hay inferencia eléctrica de los enlaces.
- **IDC:** 216 bocas RJ45 frontales y216 terminaciones IDC traseras. Misma ordinal declarada, UUID y grupos separados, sin trazado. No se reinterpretan como acopladores hembra/hembra ni se aceptan cables externos RJ45↔IDC.
- **Accesorios:** diez bases mecánicas vacías, cero puertos. Las bandejas StarTech/EFB no se anuncian como soportes de hijos: faltan datos del hueco útil. Las cajas de fibra y bases CommScope no reciben módulos o bocas ficticios.
- **NAS:** F2-424 conserva su altura222 mm vertical; usa un soporte **sintético7U** con hueco440×280×500. F6-424 Max cabe nominalmente en soporte5U. El soporte no es un producto comercial ni certifica carga, retención o ventilación. Cuatro RJ45 entre ambos NAS; sin AC ficticia para la entrada DC externa. Cuatro vistas compactas, sin recorte horizontal de la carcasa en la bandeja.
- **Referencias:** las geometrías exactas no comprobadas y variantes de familia quedan señaladas por SKU. Se dibujan vectores propios. No se distribuyen fotografías o PDF de terceros, ni se presenta cada dibujo como una medición certificada.
- **Observación menor P3:** en la trasera de Panduit DP24688TGY el texto repetido de IDC queda denso. Los ordinales, tooltips y UUID son correctos; se conserva la observación de legibilidad para una mejora visual posterior.

## Modelos

| Fabricante | SKU / configuración | Reserva | Extremos |
|---|---|---|---|
| APC | AP4421A | 1 U | 1 power + 1 power + 12 power + 1 rj45 |
| APC | AP4422A | 1 U | 1 power + 1 power + 1 power + 1 rj45 |
| APC | AP4423A | 1 U | 1 power + 1 power + 1 power + 8 power + 1 rj45 |
| APC | AP4424A | 2 U | 1 power + 1 power + 2 power + 16 power + 1 rj45 |
| APC | AP4430A | 1 U | 1 power + 1 power + 1 power + 8 power + 1 rj45 |
| APC | AP4431A | 2 U | 1 power + 1 power + 1 power + 1 rj45 |
| APC | AP4432A | 2 U | 1 power + 1 power + 2 power + 16 power + 1 rj45 |
| APC | AP4433 | 1 U | 1 power + 1 power + 12 power + 1 rj45 |
| APC | AP4433A | 1 U | 1 power + 1 power + 12 power + 1 rj45 |
| APC | AP4434A | 1 U | 1 power + 1 power + 1 power + 8 power + 1 rj45 |
| APC | AP6031A | 1 U | 1 power + 4 power |
| APC | SMT2200RM2U | 2 U | 1 power + 6 power + 2 power |
| APC | SMT3000RMI2UC | 2 U | 1 power + 8 power + 1 power + 1 rj45 |
| APC | SMX3000RMLV2U | 2 U | 1 power + 3 power + 3 power + 1 power |
| APC | SRT5KRMXLT | 3 U | 1 power + 2 power + 2 power + 1 rj45 |
| APC by Schneider Electric | SMT1500RMI2U | 2 U | 1 power + 4 power |
| Commscope | 760193771 | 1 U | 0 (accesorio vacío) |
| Commscope | 760207274 | 1 U | 0 (accesorio vacío) |
| Commscope | 760207308 | 2 U | 0 (accesorio vacío) |
| Commscope | 760231464 | 4 U | 0 (accesorio vacío) |
| Commscope | 760237046 | 1 U | 0 (accesorio vacío) |
| Digi | 70001743 | 1 U | 16 console + 1 rj45 + 1 power |
| EFB Elektronik | 691651ATS.8 | 1 U | 0 (accesorio vacío) |
| Eaton | 5PX1500IRT2UG2 | 2 U | 1 power + 8 power |
| Eaton | 5PX1500iRT | 2 U | 1 power + 8 power |
| Eaton | 9PX3000iRT2U | 2 U | 1 power + 8 power + 2 power |
| Eaton | 9PX3000iRT3U | 3 U | 1 power + 8 power + 2 power |
| Eaton | PDUMH15AT | 1 U | 1 power + 1 power + 8 power |
| Eaton | PDUMH20HVAT | 1 U | 2 power + 8 power + 2 power |
| Eaton | SMART1500LCD | 2 U | 1 power + 8 power |
| Eaton | SMART1500RMXL2UA | 2 U | 1 power + 8 power |
| Eaton | SMART2200CRMXL | 4 U | 1 power + 4 power + 4 power |
| FS | FHD-1UFMT-N | 1 U | 0 (accesorio vacío) |
| Lantronix | ETS16PR | 1 U | 16 console + 1 rj45 + 1 power |
| Lantronix | ETS32PR | 2 U | 32 console + 1 rj45 + 1 power |
| Opengear | CM7132-2-DAC | 1 U | 32 console + 1 console + 2 rj45 + 2 power |
| Opengear | CM8116 | 1 U | 16 console + 1 console + 2 rj45 + 2 power |
| Opengear | CM8148 | 1 U | 48 console + 1 console + 2 rj45 + 2 power |
| Panduit | DP245E88TGY | 1 U | 24 rj45 + 24 idc |
| Panduit | DP24688TGY | 1 U | 24 rj45 + 24 idc |
| Panduit | DP246X88TGY | 1 U | 24 rj45 + 24 idc |
| Panduit | DP485E88TGY | 2 U | 48 rj45 + 48 idc |
| Panduit | DP48688TGY | 2 U | 48 rj45 + 48 idc |
| Panduit | DP486X88TGY | 2 U | 48 rj45 + 48 idc |
| Panduit | FRME1U | 1 U | 0 (accesorio vacío) |
| Panduit | FRME2U | 2 U | 0 (accesorio vacío) |
| Raritan | PX3-5190R | 1 U | 1 power + 8 power + 2 rj45 |
| SNR | SNR-UPS-ONRT-1000-S24 | 2 U | 1 power + 8 power |
| StarTech.com | CABSHELF1U | 1 U | 0 (accesorio vacío) |
| Terramaster | F2-424 | 0 U | 2 rj45 |
| Terramaster | F6-424 Max | 0 U | 2 rj45 |
| WTI | VMR-16HD20-2 | 2 U | 2 power + 16 power + 1 rj45 |

## Reservas de esta tanda

APC AP7950B: PDU vertical0U, pendiente su montaje. Vertiv SA1-01002: comparte la U/raíles del switch, requiere relación de montaje. Cabeus PDU-8P y PL-24-Cat-5e-Dual-IDC: faltan cotas/envolvente trasera suficientes. Se conservan los datos originales; no se fuerza una U ficticia para cumplir la cuota.

## Pruebas e integración

Build aislado con SDK10.0.401, PostgreSQL17.11, Node24.21.0 y esbuild0.25.10 fijados. **984 pruebas Node en 81 archivos**, focos C# de hardware/medios físicos y verificación del compilador; resultados exactos en [la evidencia](../evidence/s1-20261101/integracion506k/RESULTADOS.md).

Migración **39→41** con752 definiciones/747 instancias comerciales previas: filas antiguas, UUID, auditoría, operaciones e historial conservados; repetir no cambia datos. Su ensayo pasó en el primer laboratorio y se reutiliza explícitamente con los mismos hashes de DLL, baseline y modelos. En otra base nueva,52 pares independientes,920 extremos por conjunto, **334 cables API +4 Click-Click GUI**, permisos restringidos, rechazo de metadatos reservados, conflicto, replay y rollback. Sidecar de conectores sólo SELECT para runtime e inmutable también para el propietario; cuatro reportes reales CSV/XLSX conservan clasificación y pasan el mismo validador de descarga del cliente, ejecutado con Node. Edge inspecciona104 caras y sus UUID, recarga, otra sesión y reinicio del proceso. No es ensayo de instalación ni reinicio Windows.

**QA-161 planificada**; la instalación nativa MFA, sus bases y las VM no se han modificado. Falta integrar en el paquete completo Windows/Restore, completar los62 modelos restantes y la aceptación de Wascar; después, laboratorio de50 clientes. **Índice del cierre restante9,76/100 sin incremento automático; no es porcentaje global del producto.**
