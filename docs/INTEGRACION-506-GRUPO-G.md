# Selección 506 · grupo G · servidores y equipos de red

01.11.2026. **50 perfiles nuevos y 100 caras** en esquema de desarrollo 35. [Ver los modelos](../VER-SELECCION-506-G.html) · [Probar el buscador](../VER-SELECTOR-CATALOGO-G.html) · [Cobertura vigente](COBERTURA-MODELOS-ELEGIDOS.md).

## Resultado

El grupo suma **893 extremos**: 436 RJ45, 219 SFP/SFP+, 100 SFP28, 51 QSFP+/QSFP28, 87 AC. El montaje se conserva por modelo: 3 sobremesa sobre soporte, 23 equipos de 1 U, 18 equipos de 2 U, 2 equipos de 4 U, 2 equipos de 5 U, 1 equipos de 6 U, 1 equipos de 7 U. Las ranuras vacías, módulos opcionales y medios combo alternativos no se convierten en conexiones adicionales.

La cartera de desarrollo alcanza **728 definiciones: 723 comerciales y 5 sintéticas**. La selección original queda en **368/506 (72,73%), 138 pendientes**; 355 comerciales adicionales se cuentan aparte. Revisión de este grupo: `selected506g-20261101-v1`. No significa que todos estén instalados o aceptados manualmente.

## Cómo revisar los HTML

Extrae el ZIP en una carpeta nueva. Abre **VER-SELECCION-506-G.html** con Edge/Chrome, conservando **PERFILES-SELECCION-506-G** junto a él. Arriba a la izquierda busca fabricante, modelo o SKU y elige un resultado. En el centro revisa dimensiones, montaje, **Frontal** y **Trasera**. Despliega **Alcance y límites de las fuentes** para conocer la variante y la certeza de cada cara.

Pulsa una boca y después un extremo de prueba compatible del mismo tipo. Hay pruebas separadas para RJ45, SFP, SFP28 y QSFP; para una entrada AC elige **Salida AC de prueba**. Desplaza la vista y verifica el anclaje del cable. Indicadores, consola, USB, DC y módulos inertes no son puertos operativos. Bajo las caras, en **Tu revisión de este modelo**, elige Pass/Not Pass/No probado y escribe observaciones; a la izquierda pulsa **Exportar mis resultados JSON** y guarda `RackClick-Revision-Visual-506G.json` separado de tus lotes anteriores.

Abre **VER-SELECTOR-CATALOGO-G.html**, con **PREVIEW-SELECTOR-CATALOGO-G** al lado. La demostración usa el componente del buscador de producción con 728 definiciones: escribe «sofos», Aruba, Cisco o un SKU. La lista mantiene desplazamiento interno y los detalles están plegados. Flechas/Enter eligen; Escape cierra la lista. Cambiar la búsqueda invalida el producto anterior. **Revisar selección** muestra un comando propuesto; no guarda inventario ni conecta a la API. [Reglas del selector](SELECTOR-CATALOGO-COMPACTO.md).

## Configuraciones y límites

**Siete traseras permanecen como geometría no verificada:** Ciena3926,3930,3942AC,5160,5162,8114 yKempLoadMasterX1. Son caras neutrales; las AC conocidas del5162 yLMX1 tienen posición esquemática, sin certificarla. Las cinco bases sinNICdehost (R7715,R7725,AS-2115HS,ASG-2015S yDX385) conservan únicamente la gestiónBMC y la alimentación de la configuración elegida. Las opciones de ampliación quedan descritas, sin inventar puertos.

**Correcciones verificadas:** tres rótulos de slots, las cotas Arista96 de440×88×405mm y tres nombres de grupo que superaban100caracteres. El primer ensayoPG rechazó estos últimos con422; se conserva como intento01. La segunda candidata usa nombres compactos y añade una guarda de autoría100/101, manteniendo las explicaciones completas y el límite del servidor.

- Los servidores representan una configuración documentada, con NIC/NDC/OCP y BMC separados. No se suman opciones mutuamente excluyentes ni se convierten USB, serie, SAS o bahías en interfaces Ethernet. Familia o tipo de máquina no equivale a un pedido regional autenticado.
- Los chasis modulares conservan el modelo/slot de cada tarjeta elegida y las bahías sin instalar. No son todas las configuraciones posibles ni simulan firmware, licencias o redundancia de controladores.
- Arista720XP-96ZC2 conserva2U ycuatrofuentesAC de la configuración4F; el fabricante no admite menos de3. El laboratorio usa una PDU sintética inicial de4salidas sin modificar las5definiciones sintéticas anteriores. Se conectan todas las entradas comprobadas, sin certificar carga o redundancia eléctrica.
- En JuniperACX7024X se representa el modo24SFP28+4QSFP28 sinPTP ni breakout. Los números virtuales de interfaces no crean conectores adicionales. En PA5445 tampoco se convierten los números de breakout en20jaulas físicas.
- F5r5600/r10600 usan una configuración mínima conservadora: puertoQSFP28 físico2.0 a100G documentado, gestión yfuentes; las demás jaulas quedan inertes con el mapeo de bitstream pendiente. No es una validación de todas las combinaciones posibles. Las NICdehost ausentes en las bases de servidor permanecen vacías; el puertoBMC no las sustituye.
- Los medios combo o compartidos mantienen una sola alternativa activa. No hay SFP56, QSFP-DD o serial degradados a otro tipo; las capacidades PoE y los protocolos no se activan por inferencia del nombre.
- Las reservas por cara y las fuentes familiares se muestran en el visor. Las seis traseras desconocidas del grupoF conservan su estado histórico; registrar un perfil no certifica toda su geometría mecánica. Las imágenes se usan como referencia privada para vectores interactivos, sin incrustarlas en los HTML.

## Pruebas y disponibilidad

PostgreSQL 17.11 y Edge en un laboratorio nuevo, con secretos locales y cuenta de ejecución restringida. La actualización34→35 conserva678 definiciones y673 instancias comerciales anteriores, inventario, auditoría, operaciones e historial. La nueva SQL035 sólo incorpora la semilla; SQL001–034 y sus constraints permanecen intactos.

Fresh35 crea dos instancias independientes de cada perfil. Se guardan **178 cables por API** y otros **2 mediante Click-Click GUI**; se prueban tipos/UUID/caras/roles, cruces incompatibles, replay, conflicto412, revisión422, lector403, rollback y catálogo SQL de sólo lectura. Edge inspecciona100caras, crea otro equipo desde el buscador y verifica recarga, otra sesión y lector. El reinicio probado es del proceso servidor, no de Windows. Clúster y hosts del laboratorio quedan detenidos al terminar. [Resultados y atribución](../evidence/s1-20261101/integracion506g/RESULTADOS.md).

Estos HTML son revisión local, no instaladores. La instalación de MFA, VM, bases existentes y QA de Wascar se conservan. Quedan 138 perfiles, los contratos especializados que correspondan, consumidores, operadores, distribución/Restore35 y el paquete Windows completo con QA final. Después se ejecutará el plan de al menos 50 clientes. Índice del cierre restante **9,76/100**, sin nuevo porcentaje global por modelos o pruebas.

## Modelos del grupo G

| Fabricante | Modelo seleccionado | SKU/configuración | Montaje | Extremos conectables |
|---|---|---|---|---|
| ASUS | RS300-E11-RS4 | RS300-E11-RS4 | 1 U | 3 RJ45 + 2 AC |
| Arista | CCS-720XP-96ZC2-4F | CCS-720XP-96ZC2-4F | 2 U | 97 RJ45 + 4 SFP28 + 2 QSFP+/QSFP28 + 4 AC |
| Arista | CCS-722XPM-48Y4-2F | CCS-722XPM-48Y4-2F | 1 U | 49 RJ45 + 4 SFP/SFP+ + 4 SFP28 + 2 AC |
| Barracuda | F380 | BNGF380B | 1 U | 8 RJ45 + 2 SFP/SFP+ + 1 AC |
| Barracuda | F400C-F20 | F400 Rev. C .F20 | 1 U | 8 RJ45 + 6 SFP/SFP+ + 2 AC |
| Check Point | SG16000 | CPAP-SG16000-PLUS-SNBT | 2 U | 11 RJ45 + 8 SFP/SFP+ + 2 AC |
| Check Point | SG19200 | CPAP-SG19200-PLUS-SNBT | 2 U | 3 RJ45 + 8 SFP/SFP+ + 6 SFP28 + 2 AC |
| Check Point | SG7000 | CPAP-SG7000-SNBT | 1 U | 10 RJ45 + 1 AC |
| Ciena | 3926 | 170-3926-900 | 1 U | 1 RJ45 + 8 SFP/SFP+ + 2 AC |
| Ciena | 3930 | 170-3930-900 | 1 U | 1 RJ45 + 10 SFP/SFP+ + 2 AC |
| Ciena | 3942 AC | 170-3942-900 | 1 U | 21 RJ45 + 4 SFP/SFP+ + 2 AC |
| Ciena | 5160 | 170-5160-900 | 1 U | 1 RJ45 + 24 SFP/SFP+ + 2 AC |
| Ciena | 5162 | 170-5162-900 | 1 U | 1 RJ45 + 40 SFP/SFP+ + 2 QSFP+/QSFP28 + 2 AC |
| Ciena | 8114 | 170-8114-900 | 2 U | 1 RJ45 + 48 SFP28 + 6 QSFP+/QSFP28 + 2 AC |
| Cisco | ASR1004 | ASR1004 | 4 U | 1 RJ45 + 5 SFP/SFP+ + 2 AC |
| Cisco | ASR1006 | ASR1006 | 6 U | 1 RJ45 + 5 SFP/SFP+ + 2 AC |
| Cisco | Nexus 9504 | N9K-C9504 | 7 U | 1 RJ45 + 48 SFP/SFP+ + 4 QSFP+/QSFP28 + 2 AC |
| Dell | PowerEdge R730xd | R730xd | 2 U | 5 RJ45 + 2 AC |
| Dell | PowerEdge R760xd2 | R760xd2 | 2 U | 3 RJ45 + 2 AC |
| Dell | PowerEdge R7615 | R7615 | 2 U | 3 RJ45 + 2 AC |
| Dell | PowerEdge R7715 | R7715 | 2 U | 1 RJ45 + 2 AC |
| Dell | PowerEdge R7725 | R7725 | 2 U | 1 RJ45 + 2 AC |
| F5 | BIG-IP 2000 | 2000 | 1 U | 9 RJ45 + 2 SFP/SFP+ + 1 AC |
| F5 | BIG-IP r10600 | r10600 | 1 U | 1 RJ45 + 1 QSFP+/QSFP28 + 2 AC |
| F5 | BIG-IP r2600 | r2600 | 1 U | 5 RJ45 + 4 SFP28 + 1 AC |
| F5 | BIG-IP r5600 | r5600 | 1 U | 1 RJ45 + 1 QSFP+/QSFP28 + 1 AC |
| HPE | Aruba 6300M-48SR10-POE8-4QSFP28 | S0E91A | 1 U | 49 RJ45 + 4 QSFP+/QSFP28 + 1 AC |
| HPE | ProLiant DL345 Gen11 | ProLiant DL345 Gen11 | 2 U | 5 RJ45 + 2 AC |
| HPE | ProLiant DL380e Gen8 | 669257-B21 | 2 U | 5 RJ45 + 2 AC |
| HPE | ProLiant DL380p Gen8 | 653200-B21 | 2 U | 5 RJ45 + 2 AC |
| HPE | ProLiant DX385 Gen10 Plus | ProLiant DX385 Gen10 Plus | 2 U | 1 RJ45 + 2 AC |
| HPE | ProLiant ML350 Gen10 | 877622-xx1 | 5 U | 5 RJ45 + 2 AC |
| Huawei | CloudEngine S5732-H48UM4Y2CZ-V2 | 02354VBU | 1 U | 49 RJ45 + 4 SFP28 + 2 QSFP+/QSFP28 |
| Huawei | S5735-L8P4S-A1 | 98011295 | Sobremesa · soporte requerido | 8 RJ45 + 4 SFP/SFP+ + 1 AC |
| Huawei | S5735-L8T4X-A1 | S5735-L8T4X-A1 | Sobremesa · soporte requerido | 8 RJ45 + 4 SFP/SFP+ + 1 AC |
| Juniper | ACX7024X | ACX7024X | 1 U | 1 RJ45 + 24 SFP28 + 4 QSFP+/QSFP28 + 2 AC |
| Kemp Technologies | LoadMaster X1 | LM-X1 | 1 U | 4 RJ45 + 1 AC |
| Lenovo | System x3650 M5 | 8871 | 2 U | 5 RJ45 + 2 AC |
| Lenovo | ThinkSystem SR650 V4 | 7DGx | 2 U | 5 RJ45 + 2 AC |
| Mellanox | SN2100 | SN2100 | 1 U | 1 RJ45 + 16 QSFP+/QSFP28 + 2 AC |
| Palo Alto Networks | PA-5445 | PA-5445 | 2 U | 8 RJ45 + 15 SFP/SFP+ + 4 SFP28 + 5 QSFP+/QSFP28 + 2 AC |
| Palo Alto Networks | PA-5450 | PA-5450 | 5 U | 4 RJ45 + 18 SFP/SFP+ + 4 QSFP+/QSFP28 + 2 AC |
| Ruckus | ZoneDirector 3000 | 909-0XXX-ZD00 | 1 U | 2 RJ45 + 1 AC |
| SonicWall | TZ370W | TZ370W | Sobremesa · soporte requerido | 8 RJ45 |
| Supermicro | AS-1124US-TNRP | AS-1124US-TNRP | 1 U | 3 RJ45 + 2 SFP/SFP+ + 2 AC |
| Supermicro | AS-2115HS-TNR | AS-2115HS-TNR | 2 U | 1 RJ45 + 2 AC |
| Supermicro | ASG-2015S-E1CR24L | ASG-2015S-E1CR24L | 2 U | 1 RJ45 + 2 AC |
| Supermicro | Storage SuperServer SSG-610P-ACR12N4H | SSG-610P-ACR12N4H | 1 U | 1 RJ45 + 2 SFP28 + 2 AC |
| Supermicro | SuperServer 5018D-FN8T | SYS-5018D-FN8T | 1 U | 7 RJ45 + 2 SFP/SFP+ + 1 AC |
| Supermicro | SuperStorage 6049P-E1CR36L | SSG-6049P-E1CR36L | 4 U | 3 RJ45 + 2 AC |
