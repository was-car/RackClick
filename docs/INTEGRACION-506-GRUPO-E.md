# Selección 506 · grupo E · switches, routers y firewalls

01.11.2026. **50 perfiles nuevos y 100 caras** en esquema de desarrollo 33. [Ver los modelos](../VER-SELECCION-506-E.html) · [Probar el buscador](../VER-SELECTOR-CATALOGO-E.html) · [Cobertura vigente](COBERTURA-MODELOS-ELEGIDOS.md).

## Resultado

El grupo suma **1906 extremos**: 1389 RJ45, 211 SFP/SFP+, 154 SFP28, 90 QSFP+/QSFP28, 62 AC. El montaje se conserva por modelo: 47 equipos de 1 U, 3 equipos de 2 U. Las ranuras vacías, módulos opcionales y medios combo alternativos no se convierten en conexiones adicionales.

La cartera de desarrollo alcanza **628 definiciones: 623 comerciales y 5 sintéticas**. La selección original queda en **268/506 (52,96%), 238 pendientes**; 355 comerciales adicionales se cuentan aparte. Revisión de este grupo: `selected506e-20261101-v1`. No significa que todos estén instalados o aceptados manualmente.

## Cómo revisar los HTML

Extrae el ZIP en una carpeta nueva. Abre **VER-SELECCION-506-E.html** con Edge/Chrome, conservando **PERFILES-SELECCION-506-E** junto a él. Arriba a la izquierda busca fabricante, modelo o SKU y elige un resultado. En el centro revisa dimensiones, montaje, **Frontal** y **Trasera**. Despliega **Alcance y límites de las fuentes** para conocer la variante y la certeza de cada cara.

Pulsa una boca y después un extremo de prueba compatible del mismo tipo. Hay pruebas separadas para RJ45, SFP, SFP28 y QSFP; para una entrada AC elige **Salida AC de prueba**. Desplaza la vista y verifica el anclaje del cable. Indicadores, consola, USB, DC y módulos inertes no son puertos operativos. Bajo las caras, en **Tu revisión de este modelo**, elige Pass/Not Pass/No probado y escribe observaciones; a la izquierda pulsa **Exportar mis resultados JSON** y guarda `RackClick-Revision-Visual-506E.json` separado de tus lotes anteriores.

Abre **VER-SELECTOR-CATALOGO-E.html**, con **PREVIEW-SELECTOR-CATALOGO-E** al lado. La demostración usa el componente del buscador de producción con 628 definiciones: escribe «sofos», Aruba, Cisco o un SKU. La lista mantiene desplazamiento interno y los detalles están plegados. Flechas/Enter eligen; Escape cierra la lista. Cambiar la búsqueda invalida el producto anterior. **Revisar selección** muestra un comando propuesto; no guarda inventario ni conecta a la API. [Reglas del selector](SELECTOR-CATALOGO-COMPACTO.md).

## Configuraciones y límites

- ASR1002-HX conserva las 16 jaulas físicas que muestra la guía; los recuentos de activación o licencia4+4 no eliminan las jaulas. No se simula IOS, licencia ni EPA. Sus dos AC están en frontal; FPR4112 representa una fuente base y la segunda bahía vacía.
- Los C9200L tienen uplinks fijos; los módulos de otras familias no se añaden por similitud. Los C9300, ASR y otros equipos conservan la configuración instalada de esta revisión, no todas sus expansiones posibles.
- Los Aruba2930M representan una fuente AC instalada elegida explícitamente cuando la base se vende sin ella. En sus combos se materializa un solo medio activo; la alternativa y módulos no instalados permanecen inertes. La ficha identifica el accesorio configurado.
- El Aruba8360v2 JL704C usa la configuración48×SFP28 a1/10/25G y6×QSFP28; no se activa el modo50G que deshabilita vecinos ni se afirma SFP56 instalado. Se conservan las cotas y discrepancias de los documentos de la variante.
- S5732 se fija a cuatro25G más dos40G. No se activa simultáneamente la alternativa100G que deshabilita los cuatro SFP28. Los puertos SFP+ de stack12GE se separan por grupo y rótulo; no se hacen pasar por uplinks10G ni se simula el protocolo.
- Los Huawei configurados como chasis sin fuente conservan sus ranuras vacías y no reciben una AC ficticia; no se afirma que estén alimentados. Los accesorios y la configuración exacta se declaran por ficha.
- Los Nokia D2/D2L/D3 no se intercambian. Sus referencias de generación, dimensiones métricas y diferencias de los documentos antiguos/actuales quedan visibles en las fuentes. Un documento original alojado en un espejo se identifica como tal.
- CRS309 se representa con sus orejas de rack respaldadas por el manual. Sus entradas DC y PoE-in no se convierten en entradas AC ficticias. La representación no simula su alimentación eléctrica.
- SFP28 y QSFP conservan tipos y formas propios. No hay QSFP-DD, breakout, transceptor instalado, negociación o firmware simulado. Una jaula multi-velocidad es un único extremo. Se conectan UUID ligados a grupo y ordinal; `gn` solo no identifica un extremo.
- El aviso genérico de referencia no verificada de este visor dice «referencia», también válido para documentación sin fotografía. Los HTML anteriores permanecen intactos y esa corrección no autentica ninguna geometría desconocida.

## Pruebas y disponibilidad

PostgreSQL 17.11 y Edge en un laboratorio nuevo, con secretos locales y cuenta de ejecución restringida. La actualización32→33 conserva578 definiciones y573 instancias comerciales anteriores, inventario, auditoría, operaciones e historial. La nueva SQL033 sólo incorpora la semilla; SQL001–032 y sus constraints permanecen intactos.

Fresh33 crea dos instancias independientes de cada perfil. Se guardan **163 cables por API** y otros **2 mediante Click-Click GUI**; se prueban tipos/UUID/caras/roles, cruces incompatibles, replay, conflicto412, revisión422, lector403, rollback y catálogo SQL de sólo lectura. Edge inspecciona100caras, crea otro equipo desde el buscador y verifica recarga, otra sesión y lector. El reinicio probado es del proceso servidor, no de Windows. Clúster y hosts del laboratorio quedan detenidos al terminar. [Resultados y atribución](../evidence/s1-20261101/integracion506e/RESULTADOS.md).

Estos HTML son revisión local, no instaladores. La instalación de MFA, VM, bases existentes y QA de Wascar se conservan. Quedan 238 perfiles, los contratos especializados que correspondan, consumidores, operadores, distribución/Restore33 y el paquete Windows completo con QA final. Después se ejecutará el plan de al menos 50 clientes. Índice del cierre restante **9,76/100**, sin nuevo porcentaje global por modelos o pruebas.

## Modelos del grupo E

| Fabricante | Modelo seleccionado | SKU/configuración | Montaje | Extremos conectables |
|---|---|---|---|---|
| Arista | CCS-720DT-48S-2F | CCS-720DT-48S-2F | 1 U | 49 RJ45 + 4 SFP/SFP+ + 2 AC |
| Arista | DCS-7020TR-48-F | DCS-7020TR-48-F | 1 U | 49 RJ45 + 6 SFP/SFP+ + 2 AC |
| Arista | DCS-7020TRA-48-F | DCS-7020TRA-48-F | 1 U | 49 RJ45 + 6 SFP/SFP+ + 2 AC |
| Cisco | ASR1002 | ASR1002 | 2 U | 1 RJ45 + 4 SFP/SFP+ + 2 AC |
| Cisco | ASR1002-HX | ASR1002-HX | 2 U | 1 RJ45 + 16 SFP/SFP+ + 2 AC |
| Cisco | C9200L-24T-4G | C9200L-24T-4G | 1 U | 25 RJ45 + 4 SFP/SFP+ + 1 AC |
| Cisco | C9200L-48P-4G | C9200L-48P-4G | 1 U | 49 RJ45 + 4 SFP/SFP+ + 1 AC |
| Cisco | Catalyst 1300-24P-4X | C1300-24P-4X | 1 U | 24 RJ45 + 4 SFP/SFP+ + 1 AC |
| Cisco | Catalyst 9200L-24P-4G | C9200L-24P-4G | 1 U | 25 RJ45 + 4 SFP/SFP+ + 1 AC |
| Cisco | Catalyst 9200L-48T-4G | C9200L-48T-4G | 1 U | 49 RJ45 + 4 SFP/SFP+ + 1 AC |
| Cisco | Catalyst 9300-24P | C9300-24P | 1 U | 25 RJ45 + 1 AC |
| Cisco | Catalyst 9300-48T | C9300-48T | 1 U | 49 RJ45 + 1 AC |
| Cisco | Catalyst 9300L-48P-4X | C9300L-48P-4X | 1 U | 49 RJ45 + 4 SFP/SFP+ + 1 AC |
| Cisco | FPR3110-NGFW-K9 | FPR3110-NGFW-K9 | 1 U | 8 RJ45 + 9 SFP/SFP+ + 1 AC |
| Cisco | FPR4112-NGFW-K9 | FPR4112-NGFW-K9 | 1 U | 9 SFP/SFP+ + 1 AC |
| Cisco | Firepower 2110 | FPR2110-NGFW-K9 | 1 U | 13 RJ45 + 4 SFP/SFP+ + 1 AC |
| Cisco | Meraki MS125-48FP | MS125-48FP-HW | 1 U | 49 RJ45 + 4 SFP/SFP+ + 1 AC |
| Dell | PowerSwitch N2048 | N2048 | 1 U | 48 RJ45 + 2 SFP/SFP+ + 1 AC |
| Extreme Networks | 4120-48MW-4Y | 4120-48MW-4Y | 1 U | 49 RJ45 + 4 SFP28 + 2 QSFP+/QSFP28 + 1 AC |
| Extreme Networks | 4220-12T-4X | 4220-12T-4X | 1 U | 13 RJ45 + 4 SFP/SFP+ + 1 AC |
| Extreme Networks | 4220-48P-4X | 4220-48P-4X | 1 U | 49 RJ45 + 4 SFP/SFP+ + 1 AC |
| Extreme Networks | 4220-48T-4X | 4220-48T-4X | 1 U | 49 RJ45 + 4 SFP/SFP+ + 1 AC |
| Extreme Networks | 4220-4MW-20P-4X | 4220-4MW-20P-4X | 1 U | 25 RJ45 + 4 SFP/SFP+ + 1 AC |
| Extreme Networks | 4220-4MW-8P-4X | 4220-4MW-8P-4X | 1 U | 13 RJ45 + 4 SFP/SFP+ + 1 AC |
| Extreme Networks | 4220-8MW-40P-4X | 4220-8MW-40P-4X | 1 U | 49 RJ45 + 4 SFP/SFP+ + 1 AC |
| Extreme Networks | X440-G2-24p-10GE4 | 16533 | 1 U | 21 RJ45 + 8 SFP/SFP+ + 1 AC |
| HPE | Aruba 2930M-24G | JL319A | 1 U | 25 RJ45 + 1 AC |
| HPE | Aruba 2930M-48G | JL321A | 1 U | 49 RJ45 + 1 AC |
| HPE | Aruba 2930M-48G-PoE+ | JL322A | 1 U | 49 RJ45 + 1 AC |
| HPE | Aruba 8325-32C Front-to-Back | JL626A | 1 U | 1 RJ45 + 32 QSFP+/QSFP28 + 2 AC |
| HPE | Aruba 8360-48Y6C Front-to-Back | JL704C | 1 U | 1 RJ45 + 48 SFP28 + 6 QSFP+/QSFP28 + 2 AC |
| Huawei | S5700-52P-LI-AC | 02353174 | 1 U | 48 RJ45 + 4 SFP/SFP+ + 1 AC |
| Huawei | S5720-52X-PWR-SI-AC | 02350DLX | 1 U | 49 RJ45 + 4 SFP/SFP+ + 1 AC |
| Huawei | S5731-H24T4XC | 02352QPP | 1 U | 25 RJ45 + 4 SFP/SFP+ |
| Huawei | S5732-H48UM2CC | 02353HUB | 1 U | 49 RJ45 + 4 SFP28 + 2 QSFP+/QSFP28 |
| Huawei | S5735-L48P4XE-A-V2 | 98012120 | 1 U | 48 RJ45 + 6 SFP/SFP+ + 1 AC |
| Juniper | SRX380 | SRX380-P-SYS-JB-AC | 1 U | 17 RJ45 + 4 SFP/SFP+ + 1 AC |
| MikroTik | CRS309-1G-8S+IN | CRS309-1G-8S+ | 1 U | 1 RJ45 + 8 SFP/SFP+ |
| MikroTik | CRS317-1G-16S+RM | CRS317-1G-16S+ | 1 U | 1 RJ45 + 16 SFP/SFP+ + 2 AC |
| MikroTik | CRS328-24P-4S+RM | CRS328-24P-4S+RM | 1 U | 24 RJ45 + 4 SFP/SFP+ + 1 AC |
| Netgear | S3300-28X-PoE+ | GS728TXP | 1 U | 26 RJ45 + 2 SFP/SFP+ + 1 AC |
| Netgear | S3300-52X | GS752TX | 1 U | 50 RJ45 + 2 SFP/SFP+ + 1 AC |
| Nokia | 7220 IXR-D2 25/100GE | 3HE15622AA | 1 U | 1 RJ45 + 48 SFP28 + 8 QSFP+/QSFP28 + 2 AC |
| Nokia | 7220 IXR-D2L 25/100GE | 3HE17645AA | 1 U | 1 RJ45 + 2 SFP/SFP+ + 48 SFP28 + 8 QSFP+/QSFP28 + 2 AC |
| Nokia | 7220 IXR-D3 32*100GE | 3HE15623AA | 1 U | 1 RJ45 + 2 SFP/SFP+ + 32 QSFP+/QSFP28 + 2 AC |
| Palo Alto Networks | PA-1410 | PA-1410 | 1 U | 15 RJ45 + 11 SFP/SFP+ + 2 AC |
| Palo Alto Networks | PA-1420 | PA-1420 | 1 U | 15 RJ45 + 11 SFP/SFP+ + 2 AC |
| Palo Alto Networks | PA-3220 | PA-3220 | 2 U | 15 RJ45 + 9 SFP/SFP+ + 2 AC |
| Ubiquiti | Enterprise Campus Switch 24-Port PoE | ECS-24-PoE | 1 U | 24 RJ45 + 2 SFP28 + 2 AC |
| Ubiquiti | USW-24-POE | USW-24-POE | 1 U | 24 RJ45 + 2 SFP/SFP+ + 1 AC |
