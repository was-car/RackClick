# Selección 506 · grupo F · servidores y equipos de red

01.11.2026. **50 perfiles nuevos y 100 caras** en esquema de desarrollo 34. [Ver los modelos](../VER-SELECCION-506-F.html) · [Probar el buscador](../VER-SELECTOR-CATALOGO-F.html) · [Cobertura vigente](COBERTURA-MODELOS-ELEGIDOS.md).

## Resultado

El grupo suma **819 extremos**: 541 RJ45, 102 SFP/SFP+, 48 SFP28, 52 QSFP+/QSFP28, 76 AC. El montaje se conserva por modelo: 5 sobremesa sobre soporte, 35 equipos de 1 U, 10 equipos de 2 U. Las ranuras vacías, módulos opcionales y medios combo alternativos no se convierten en conexiones adicionales.

La cartera de desarrollo alcanza **678 definiciones: 673 comerciales y 5 sintéticas**. La selección original queda en **318/506 (62,85%), 188 pendientes**; 355 comerciales adicionales se cuentan aparte. Revisión de este grupo: `selected506f-20261101-v1`. No significa que todos estén instalados o aceptados manualmente.

## Cómo revisar los HTML

Extrae el ZIP en una carpeta nueva. Abre **VER-SELECCION-506-F.html** con Edge/Chrome, conservando **PERFILES-SELECCION-506-F** junto a él. Arriba a la izquierda busca fabricante, modelo o SKU y elige un resultado. En el centro revisa dimensiones, montaje, **Frontal** y **Trasera**. Despliega **Alcance y límites de las fuentes** para conocer la variante y la certeza de cada cara.

Pulsa una boca y después un extremo de prueba compatible del mismo tipo. Hay pruebas separadas para RJ45, SFP, SFP28 y QSFP; para una entrada AC elige **Salida AC de prueba**. Desplaza la vista y verifica el anclaje del cable. Indicadores, consola, USB, DC y módulos inertes no son puertos operativos. Bajo las caras, en **Tu revisión de este modelo**, elige Pass/Not Pass/No probado y escribe observaciones; a la izquierda pulsa **Exportar mis resultados JSON** y guarda `RackClick-Revision-Visual-506F.json` separado de tus lotes anteriores.

Abre **VER-SELECTOR-CATALOGO-F.html**, con **PREVIEW-SELECTOR-CATALOGO-F** al lado. La demostración usa el componente del buscador de producción con 678 definiciones: escribe «sofos», Aruba, Cisco o un SKU. La lista mantiene desplazamiento interno y los detalles están plegados. Flechas/Enter eligen; Escape cierra la lista. Cambiar la búsqueda invalida el producto anterior. **Revisar selección** muestra un comando propuesto; no guarda inventario ni conecta a la API. [Reglas del selector](SELECTOR-CATALOGO-COMPACTO.md).

## Configuraciones y límites

**Seis traseras siguen pendientes de detalle geométrico:** MES2308P, MES2324P, ZXR10-5950-28PD-L, ZXR10-5950-28TD-L, GS1100-16 y DEC2770. Se muestran como caras neutrales `geometry_unverified`; sus entradas respaldadas no certifican la posición exacta. Contarlas como perfiles registrados y probados no las convierte en carcasas completas.

- Los servidores representan una configuración explícita. Se distinguen iDRAC, iLO, XClarity/IPMI y las NIC del host. No se suman alternativas NDC/OCP/FlexibleLOM; módulos, discos, VGA, serie, USB y SAS no reciben puertos Ethernet ficticios. La ficha identifica accesorios y opciones instaladas o vacías.
- Los identificadores de familia o tipos de máquina no son números de pedido certificados. La referencia errónea de DL360 Gen11 en el expediente previo queda documentada como historia y no se hereda en el nuevo perfil.
- S9600-32X conserva32QSFP28 activos; los cuatroSFP28 que comparten el puerto0 permanecen inertes en este modo. No son36enlaces simultáneos. Las fuentes AC/DC alternativas se fijan a una configuración declarada.
- SMCGS8P-Smart conserva la revisión de su ficha original: el SFP combo alternativo no suma otro enlace. D-Link DES1005P conserva su revisión explícita, sin mezclar disposición, cotas o PoE de revisiones vecinas.
- PA415/445 y los sobremesa usan el soporte existente que corresponde a sus cotas, sin orejas o montaje de rack inventados. DC y PoE-in no se convierten en AC. El MES3510P industrial permanece pendiente de un contrato DIN y no pertenece al grupoF.
- SFP28 y QSFP conservan tipos y glifos propios; no hay QSFP-DD, breakout, negociación, firmware o certificación de óptica/eléctrica. Cada extremo conserva UUID, grupo, ordinal, tipo y cara. Las certezas de referencia y límites de geometría se muestran por ficha; una fuente de familia no certifica todas las revisiones físicas.
- Las capacidades PoE son descriptivas y no activan por nombre los roles de todos los puertos. Los datos conservan powerRole unspecified: el combo de SMC y los puertos no capaces de PA415/445 no se convierten en PSE. Este lote no acredita negociación ni alimentación real.

## Pruebas y disponibilidad

PostgreSQL 17.11 y Edge en un laboratorio nuevo, con secretos locales y cuenta de ejecución restringida. La actualización33→34 conserva628 definiciones y623 instancias comerciales anteriores, inventario, auditoría, operaciones e historial. La nueva SQL034 sólo incorpora la semilla; SQL001–033 y sus constraints permanecen intactos.

Fresh34 crea dos instancias independientes de cada perfil. Se guardan **151 cables por API** y otros **2 mediante Click-Click GUI**; se prueban tipos/UUID/caras/roles, cruces incompatibles, replay, conflicto412, revisión422, lector403, rollback y catálogo SQL de sólo lectura. Edge inspecciona100caras, crea otro equipo desde el buscador y verifica recarga, otra sesión y lector. El reinicio probado es del proceso servidor, no de Windows. Clúster y hosts del laboratorio quedan detenidos al terminar. [Resultados y atribución](../evidence/s1-20261101/integracion506f/RESULTADOS.md).

Estos HTML son revisión local, no instaladores. La instalación de MFA, VM, bases existentes y QA de Wascar se conservan. Quedan 188 perfiles, los contratos especializados que correspondan, consumidores, operadores, distribución/Restore34 y el paquete Windows completo con QA final. Después se ejecutará el plan de al menos 50 clientes. Índice del cierre restante **9,76/100**, sin nuevo porcentaje global por modelos o pruebas.

## Modelos del grupo F

| Fabricante | Modelo seleccionado | SKU/configuración | Montaje | Extremos conectables |
|---|---|---|---|---|
| Alcatel-Lucent | OS6400-24 | OS6400-24 | 1 U | 20 RJ45 + 4 SFP/SFP+ + 1 AC |
| Alcatel-Lucent | OS6860-24 | 903713-90 | 1 U | 24 RJ45 + 4 SFP/SFP+ + 2 QSFP+/QSFP28 |
| Alcatel-Lucent | OS6860-48 | 903715-90 | 1 U | 48 RJ45 + 4 SFP/SFP+ + 2 QSFP+/QSFP28 |
| Avaya | ERS 3526T-PWR+ | ERS 3526T-PWR+ | 1 U | 24 RJ45 + 4 SFP/SFP+ + 1 AC |
| D-Link | DES-1005P | DES-1005P | Sobremesa · soporte requerido | 5 RJ45 |
| D-Link | DGS-1520-52 | DGS-1520-52 | 1 U | 51 RJ45 + 2 SFP/SFP+ + 1 AC |
| D-Link | DXS-3400-24TC | DXS-3400-24TC | 1 U | 21 RJ45 + 4 SFP/SFP+ + 1 AC |
| Dell | PowerEdge R350 | R350 | 1 U | 3 RJ45 + 2 AC |
| Dell | PowerEdge R540 | R540 | 2 U | 3 RJ45 + 2 AC |
| Dell | PowerEdge R620 | R620 | 1 U | 5 RJ45 + 2 AC |
| Dell | PowerEdge R630 | R630 | 1 U | 5 RJ45 + 2 AC |
| Dell | PowerEdge R640 | R640 | 1 U | 5 RJ45 + 2 AC |
| Dell | PowerEdge R6515 | R6515 | 1 U | 3 RJ45 + 2 AC |
| Dell | PowerEdge R720 | R720 | 2 U | 5 RJ45 + 2 AC |
| Dell | PowerEdge R7515 | R7515 | 2 U | 3 RJ45 + 2 AC |
| Dell | PowerEdge R7525 | R7525 | 2 U | 3 RJ45 + 2 AC |
| Edgecore | AS4625-54T-O-AC-F | F0PEC4654xxxx | 1 U | 49 RJ45 + 6 SFP/SFP+ + 2 AC |
| Edgecore | AS7326-56X-O-AC-F | FP4ZZ7656xxxx | 1 U | 1 RJ45 + 2 SFP/SFP+ + 48 SFP28 + 8 QSFP+/QSFP28 + 2 AC |
| Eltex | MES2308P | MES2308P | 1 U | 10 RJ45 + 2 SFP/SFP+ + 1 AC |
| Eltex | MES2324P | MES2324P | 1 U | 24 RJ45 + 4 SFP/SFP+ + 1 AC |
| F5 | BIG-IP i2600 | i2600 | 1 U | 1 RJ45 + 6 SFP/SFP+ + 1 AC |
| F5 | BIG-IP i5600 | i5600 | 1 U | 1 RJ45 + 8 SFP/SFP+ + 4 QSFP+/QSFP28 + 1 AC |
| Grandstream | GWN7831 | GWN7831 | 1 U | 28 SFP/SFP+ + 1 AC |
| HPE | ProLiant DL20 Gen11 | ProLiant DL20 Gen11 | 1 U | 4 RJ45 + 2 AC |
| HPE | ProLiant DL360 Gen10 | P19766-B21 | 1 U | 5 RJ45 + 2 AC |
| HPE | ProLiant DL360 Gen10 Plus | ProLiant DL360 Gen10 Plus | 1 U | 5 RJ45 + 2 AC |
| HPE | ProLiant DL360 Gen11 | ProLiant DL360 Gen11 | 1 U | 5 RJ45 + 2 AC |
| HPE | ProLiant DL360 Gen9 | 755258-B21 | 1 U | 5 RJ45 + 2 AC |
| HPE | ProLiant DL380 Gen10 | P19717-B21 | 2 U | 5 RJ45 + 2 AC |
| HPE | ProLiant DL380 Gen11 | P52534-B21 | 2 U | 5 RJ45 + 2 AC |
| HPE | ProLiant DL385 Gen10 Plus v2 | ProLiant DL385 Gen10 Plus v2 | 2 U | 5 RJ45 + 2 AC |
| Huawei | AR6140-S | 02353BMU | 1 U | 5 RJ45 + 4 SFP/SFP+ + 2 AC |
| Lenovo | ThinkSystem SR250 V2 | 7D7Q | 1 U | 3 RJ45 + 2 AC |
| Lenovo | ThinkSystem SR630 V2 | 7Z7x | 1 U | 3 RJ45 + 2 AC |
| Lenovo | ThinkSystem SR630 V3 | 7D7x | 1 U | 3 RJ45 + 2 AC |
| Lenovo | ThinkSystem SR645 | 7D2X | 1 U | 3 RJ45 + 2 AC |
| Lenovo | ThinkSystem SR650 | 7X0x | 2 U | 3 RJ45 + 2 AC |
| Netgate | 8300 Security Gateway | 8300 Security Gateway | 1 U | 4 RJ45 + 8 SFP/SFP+ + 1 AC |
| Nvidia | SN2201 | SN2201 | 1 U | 49 RJ45 + 4 QSFP+/QSFP28 + 2 AC |
| OPNsense | DEC2770 | DEC2770 | 1 U | 7 RJ45 + 2 SFP/SFP+ + 1 AC |
| Palo Alto Networks | PA-415 | PA-415 | Sobremesa · soporte requerido | 10 RJ45 |
| Palo Alto Networks | PA-445 | PA-445 | Sobremesa · soporte requerido | 10 RJ45 |
| SMC Networks | SMCGS8P-SMART | SMCGS8P-SMART | Sobremesa · soporte requerido | 8 RJ45 + 1 AC |
| Supermicro | SuperServer 1027R-WRF | SYS-1027R-WRF | 1 U | 3 RJ45 + 2 AC |
| Supermicro | SuperServer 5019D-FN8TP | SYS-5019D-FN8TP | 1 U | 7 RJ45 + 2 SFP/SFP+ + 1 AC |
| Supermicro | SuperServer 6029P-TR | SYS-6029P-TR | 2 U | 3 RJ45 + 2 AC |
| UfiSpace | S9600-32X | S9600-32X | 2 U | 1 RJ45 + 32 QSFP+/QSFP28 + 2 AC |
| ZTE | ZXR10-5950-28PD-L | ZXR10 5950-28PD-L / zxr10-5950-28pd-l | 1 U | 25 RJ45 + 4 SFP/SFP+ + 2 AC |
| ZTE | ZXR10-5950-28TD-L | ZXR10 5950-28TD-L / zxr10-5950-28td-l | 1 U | 25 RJ45 + 4 SFP/SFP+ + 2 AC |
| Zyxel | GS1100-16 | GS1100-16 | Sobremesa · soporte requerido | 16 RJ45 + 1 AC |
