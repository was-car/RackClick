# Lote de50 modelos · revisión visual y catálogo24

30.10.2026. Petición de Wascar: ampliar por marcas/familias y entregar50HTML para verificar. Son **50 modelos nuevos**, aparte de los seis comerciales anteriores. [Abrir índice](../VER-50-MODELOS.html).

## Cómo revisarlos

1. Abre VER-50-MODELOS.html con doble clic en Edge o Chrome. No requiere PowerShell, cuenta, contraseña ni instalación. Conserva la carpeta CARCASAS-50-01 junto al archivo. Si lo llevas a otro equipo, extrae antes todo el ZIP.
2. A la izquierda busca la marca o modelo y pulsa su nombre. En el centro verás Frontal y Trasera, a ancho completo; en ventana estrecha desplaza horizontalmente donde haya muchos puertos.
3. Comprueba carcasa/color, cubierta/bandejas, ventiladores, ubicación/orden/cantidad de bocas. Pulsa una boca y después un puerto de prueba del mismo tipo. La salida AC de prueba sólo acepta una entrada, no otra salida. Son cables de demostración local: el visor no escribe inventario en el servidor.
4. Debajo elige Pass, Not Pass o No probado y escribe observaciones. Usa el índice para llevar juntas las50. Se guardan en el almacenamiento local de esa página/navegador; un HTML individual puede tener su propio almacenamiento según el navegador.
5. Pulsa Exportar mis resultados JSON en la columna izquierda y envía ese archivo cuando termines. Importar en casillas vacías recupera resultados compatibles sin sobrescribir notas existentes. No afecta a tu QA anterior.

## Certeza de las referencias

**33 model_reference,13 family_reference y4 unverified_reference.** Son categorías de procedencia visual, no porcentajes de calidad ni aceptación. Todas tienen definición de puertos/dimensiones contrastada, pero no todas las vistas tienen el mismo nivel de evidencia. Las fotos/PDF son referencias privadas y no se incluyen en el visor.

- model_reference: referencias del modelo; dibujo propio aproximado, sin afirmar reproducción milimétrica o revisión física.
- family_reference: alguna vista/variante se apoya en chasis o documentación familiar. El aviso queda visible; en QNAP también distingue chasis de RAM instalada.
- unverified_reference: una referencia de cara aún no confirma el SKU exacto. Son Cisco C1300-48T-4G, CBS250-48T-4G, CBS350-24T-4G y CBS350-48T-4G. No se presentan como carcasas exactas aprobadas. El caso4X→4G se usa sólo como referencia de geometría y conserva los datos4G del fabricante.

En Algunas fuentes de red hubo redirecciones a otro modelo: no se usaron como prueba del modelo pedido. La selección final sustituyó esos casos por equipos documentados. La recepción por espejo de una guía está identificada como tal, sin atribuir una descarga directa al fabricante que no ocurrió.

## Implementación y pruebas

Un catálogo24 con revisión exacta batch50-20261030-v1, motor de bancos físicos por clave de grupo+ordinal y dibujo propio común. SQL001–023,11definiciones previas y seis carcasas anteriores conservados. Total61perfiles de desarrollo:56comerciales y5sintéticos; ninguna actualización de la instalación10/MFA.

SDK10.0.401 sin cambios: build final0errores/advertencias,5HardwareRevisionTestsPASS; Node24.21.0/esbuild0.25.10,858/858pruebas en59archivos. Los binlogs quedan privados. No se presenta como regresión completa.NET/MFA.

PG17.11 nuevo: bootstrap24 y23→24 preservan los seis modelos anteriores,11definiciones, inventario/montajes/UUID/operaciones/auditoría e historial1–23; repetir migración no cambia nada. Los50nuevos se crearon por API:639puertos propios (565RJ45/52SFP/22AC). Con companions/PDU/legacy son1991extremos. Se guardaron90cables:50RJ45,18SFP y22AC→outlet. Grupos, caras, roles, ordinales y puertos no usados permanecen correctos.

Replay de dos representantes no duplica; fallo de auditoría forzado revierte la creación, montaje y puertos. Revisión desconocida, NAS en bandeja baja, lector403 y runtime sinDDL/DML del catálogo fallan sin mutación. Otra sesión y reinicio del host ASP.NET leen el mismo snapshot. No fue reinicio de Windows; laboratorios detenidos.

Edge nativo en esa misma base leyó50modelos/100caras, UUID de inventario exactos, blancos>=24px, recarga/segunda sesión/lector y ausencia de fotos en superficie operativa. El Atlas se prueba aparte:50clics de demostración,100caras, teclado/SFP/AC, anclas, etiquetas escapadas y resultados JSON. Los IDs de demostración del visor son claves sintéticas; no se confunden con UUID del servidor.

Revisión independiente distinta en evidence/s1-20261030/hardware-batch50/review/. La recepción se limita al motor/catálogo/visor y focos ejecutados; Wascar sigue revisando estética y candidata. Los dos P3 del motor se reprodujeron y corrigieron antes del freeze (diagnóstico de tipos y geometría compartida mutable). El primer build rechazó una fuente cuyo rótulo de procedencia cambió; no se relajó la guarda. Dos intentos del arnés PG/GUI fallaron por expectativa de prefijo recortado y navegación mediante tarjetas ya ocultas; se conservaron y corrigieron los arneses, sin cambiar el producto. El recorrido final completo pasa.

## Límites y disponibilidad

USB/DC/consola/HDMI/expansión/ventiladores/discos/indicadores son dibujos cuando no tienen contrato operativo. Una consola RJ45 no se convierte en Ethernet. No se inventan módulos, ópticas, PoE, RAID, adaptadores o telemetría. Medidas nominales/soportes no certifican altura con pies, holguras, carga ni ventilación. Las fichas exactas, diferencias y límites se conservan en los tres JSON de autoría y evidencia de cada marca.

Los50HTML están disponibles ahora para revisión visual local. La versión del servidor sigue de desarrollo: distribución/Restore24/candidata completa, aceptación estética y QA final pendientes. QA144planned conserva143casos anteriores. No se tocaron VM, QA instalada, bases existentes, MFA, instaladores, commits/push o limpieza. **Índice de cierre restante9,76/100 intacto, sin porcentaje global nuevo por sumar modelos o pruebas.**

## Lista de50 HTML individuales

| Marca | Modelo / SKU | RJ45 / SFP / AC | Referencia visual | HTML |
|---|---|---|---|---|
| Cisco | C1300-24T-4G | 24 / 4 / 1 | family_reference | [Abrir](../CARCASAS-50-01/modelos/cisco-c1300-24t-4g.html) |
| Cisco | C1300-48T-4G | 48 / 4 / 1 | unverified_reference | [Abrir](../CARCASAS-50-01/modelos/cisco-c1300-48t-4g.html) |
| Cisco | CBS250-16T-2G | 16 / 2 / 1 | family_reference | [Abrir](../CARCASAS-50-01/modelos/cisco-cbs250-16t-2g.html) |
| Cisco | CBS250-24T-4G | 24 / 4 / 1 | family_reference | [Abrir](../CARCASAS-50-01/modelos/cisco-cbs250-24t-4g.html) |
| Cisco | CBS250-48T-4G | 48 / 4 / 1 | unverified_reference | [Abrir](../CARCASAS-50-01/modelos/cisco-cbs250-48t-4g.html) |
| Cisco | CBS350-16T-2G | 16 / 2 / 1 | family_reference | [Abrir](../CARCASAS-50-01/modelos/cisco-cbs350-16t-2g.html) |
| Cisco | CBS350-24T-4G | 24 / 4 / 1 | unverified_reference | [Abrir](../CARCASAS-50-01/modelos/cisco-cbs350-24t-4g.html) |
| Cisco | CBS350-48T-4G | 48 / 4 / 1 | unverified_reference | [Abrir](../CARCASAS-50-01/modelos/cisco-cbs350-48t-4g.html) |
| Fortinet | FortiGate 40F / FG-40F | 5 / 0 / 0 | model_reference | [Abrir](../CARCASAS-50-01/modelos/fortinet-fg40f.html) |
| Fortinet | FortiGate 71F / FG-71F | 10 / 0 / 0 | model_reference | [Abrir](../CARCASAS-50-01/modelos/fortinet-fg71f.html) |
| HPE Aruba Networking | JL680A | 8 / 2 / 0 | model_reference | [Abrir](../CARCASAS-50-01/modelos/aruba-jl680a.html) |
| HPE Aruba Networking | JL685A | 48 / 4 / 1 | model_reference | [Abrir](../CARCASAS-50-01/modelos/aruba-jl685a.html) |
| HPE Aruba Networking | JL805A | 12 / 4 / 1 | family_reference | [Abrir](../CARCASAS-50-01/modelos/aruba-jl805a.html) |
| HPE Aruba Networking | JL806A | 26 / 2 / 1 | family_reference | [Abrir](../CARCASAS-50-01/modelos/aruba-jl806a.html) |
| HPE Aruba Networking | JL808A | 50 / 2 / 1 | family_reference | [Abrir](../CARCASAS-50-01/modelos/aruba-jl808a.html) |
| HPE Aruba Networking | JL810A | 8 / 0 / 0 | model_reference | [Abrir](../CARCASAS-50-01/modelos/aruba-jl810a.html) |
| HPE Aruba Networking | JL812A | 24 / 2 / 1 | family_reference | [Abrir](../CARCASAS-50-01/modelos/aruba-jl812a.html) |
| HPE Aruba Networking | JL814A | 48 / 4 / 1 | family_reference | [Abrir](../CARCASAS-50-01/modelos/aruba-jl814a.html) |
| QNAP | TS-233 | 1 / 0 / 0 | model_reference | [Abrir](../CARCASAS-50-01/modelos/qnap-ts-233.html) |
| QNAP | TS-262 / TS-262-4G | 1 / 0 / 0 | family_reference | [Abrir](../CARCASAS-50-01/modelos/qnap-ts-262-4g.html) |
| QNAP | TS-264 / TS-264-8G | 2 / 0 / 0 | family_reference | [Abrir](../CARCASAS-50-01/modelos/qnap-ts-264-8g.html) |
| QNAP | TS-451D2 / TS-451D2-4G | 2 / 0 / 0 | model_reference | [Abrir](../CARCASAS-50-01/modelos/qnap-ts-451d2-4g.html) |
| QNAP | TS-453D / TS-453D-8G | 2 / 0 / 0 | family_reference | [Abrir](../CARCASAS-50-01/modelos/qnap-ts-453d-8g.html) |
| QNAP | TS-462 / TS-462-4G | 1 / 0 / 0 | family_reference | [Abrir](../CARCASAS-50-01/modelos/qnap-ts-462-4g.html) |
| QNAP | TS-473A / TS-473A-8G | 2 / 0 / 1 | model_reference | [Abrir](../CARCASAS-50-01/modelos/qnap-ts-473a-8g.html) |
| QNAP | TS-673A / TS-673A-8G | 2 / 0 / 1 | model_reference | [Abrir](../CARCASAS-50-01/modelos/qnap-ts-673a-8g.html) |
| QNAP | TS-873A / TS-873A-8G | 2 / 0 / 1 | model_reference | [Abrir](../CARCASAS-50-01/modelos/qnap-ts-873a-8g.html) |
| QNAP | TS-932PX / TS-932PX-4G | 2 / 2 / 0 | model_reference | [Abrir](../CARCASAS-50-01/modelos/qnap-ts-932px-4g.html) |
| Sophos | XGS 107 | 8 / 1 / 0 | model_reference | [Abrir](../CARCASAS-50-01/modelos/sophos-xgs107-gen1.html) |
| Sophos | XGS 87 | 4 / 1 / 0 | model_reference | [Abrir](../CARCASAS-50-01/modelos/sophos-xgs87-gen1.html) |
| Synology | DS1520+ | 4 / 0 / 0 | model_reference | [Abrir](../CARCASAS-50-01/modelos/synology-ds1520plus.html) |
| Synology | DS1522+ | 4 / 0 / 0 | model_reference | [Abrir](../CARCASAS-50-01/modelos/synology-ds1522plus.html) |
| Synology | DS1525+ | 2 / 0 / 0 | model_reference | [Abrir](../CARCASAS-50-01/modelos/synology-ds1525plus.html) |
| Synology | DS1621+ | 4 / 0 / 1 | model_reference | [Abrir](../CARCASAS-50-01/modelos/synology-ds1621plus.html) |
| Synology | DS1821+ | 4 / 0 / 1 | model_reference | [Abrir](../CARCASAS-50-01/modelos/synology-ds1821plus.html) |
| Synology | DS1823xs+ | 4 / 0 / 1 | model_reference | [Abrir](../CARCASAS-50-01/modelos/synology-ds1823xsplus.html) |
| Synology | DS218+ | 1 / 0 / 0 | model_reference | [Abrir](../CARCASAS-50-01/modelos/synology-ds218plus.html) |
| Synology | DS220+ | 2 / 0 / 0 | model_reference | [Abrir](../CARCASAS-50-01/modelos/synology-ds220plus.html) |
| Synology | DS223 | 1 / 0 / 0 | model_reference | [Abrir](../CARCASAS-50-01/modelos/synology-ds223.html) |
| Synology | DS223j | 1 / 0 / 0 | model_reference | [Abrir](../CARCASAS-50-01/modelos/synology-ds223j.html) |
| Synology | DS224+ | 2 / 0 / 0 | model_reference | [Abrir](../CARCASAS-50-01/modelos/synology-ds224plus.html) |
| Synology | DS225+ | 2 / 0 / 0 | model_reference | [Abrir](../CARCASAS-50-01/modelos/synology-ds225plus.html) |
| Synology | DS720+ | 2 / 0 / 0 | model_reference | [Abrir](../CARCASAS-50-01/modelos/synology-ds720plus.html) |
| Synology | DS723+ | 2 / 0 / 0 | model_reference | [Abrir](../CARCASAS-50-01/modelos/synology-ds723plus.html) |
| Synology | DS725+ | 2 / 0 / 0 | model_reference | [Abrir](../CARCASAS-50-01/modelos/synology-ds725plus.html) |
| Synology | DS920+ | 2 / 0 / 0 | model_reference | [Abrir](../CARCASAS-50-01/modelos/synology-ds920plus.html) |
| Synology | DS923+ | 2 / 0 / 0 | model_reference | [Abrir](../CARCASAS-50-01/modelos/synology-ds923plus.html) |
| Synology | DS925+ | 2 / 0 / 0 | model_reference | [Abrir](../CARCASAS-50-01/modelos/synology-ds925plus.html) |
| Synology | RS819 | 2 / 0 / 1 | model_reference | [Abrir](../CARCASAS-50-01/modelos/synology-rs819.html) |
| Synology | RS822+ | 4 / 0 / 1 | model_reference | [Abrir](../CARCASAS-50-01/modelos/synology-rs822plus.html) |
