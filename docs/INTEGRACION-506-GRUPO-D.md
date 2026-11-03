# Selección 506 · grupo D · conectores de mayor capacidad

01.11.2026. **50 perfiles nuevos y 100 caras** en desarrollo de esquema 32. [Abrir los modelos](../VER-SELECCION-506-D.html) · [Probar el buscador](../VER-SELECTOR-CATALOGO-D.html) · [Cobertura vigente](COBERTURA-MODELOS-ELEGIDOS.md).

## Resultado y alcance

El grupo incorpora **2062 extremos: 557 RJ45, 506 SFP/SFP+, 612 SFP28, 304 QSFP+/QSFP28, 83 AC**. Son 50 equipos de rack: 41 de 1 U, 8 de 2 U y un PA-5260 de 3 U. Los conectores SFP28 y QSFP tienen tipos y dibujos propios; no se sustituyen por SFP ni RJ45.

La cartera de desarrollo alcanza **578 definiciones: 573 comerciales y 5 sintéticas**. La selección original queda en **218/506 (43,08%), 288 pendientes**. Los 355 comerciales adicionales se contabilizan por separado. La revisión de este grupo es `selected506d-20261101-v1`.

## Cómo revisar

Extrae el ZIP en una carpeta nueva. Abre **VER-SELECCION-506-D.html** con Edge o Chrome y conserva **PERFILES-SELECCION-506-D** junto a él. Arriba a la izquierda busca fabricante, modelo o SKU y selecciona un resultado. En el centro cambia entre **Frontal** y **Trasera**; despliega **Alcance y límites de las fuentes** para revisar la configuración y su certeza.

Pulsa un puerto y después el extremo de prueba del mismo tipo. Hay pruebas separadas para RJ45, SFP, SFP28, QSFP y AC; para una entrada AC utiliza la salida de prueba. Comprueba que el cable queda anclado al conector también al desplazar la vista. Las piezas inertes no son puertos conectables. Bajo las caras, en **Tu revisión de este modelo**, marca Pass, Not Pass o No probado y escribe tus observaciones. En la columna izquierda pulsa **Exportar mis resultados JSON** y guarda `RackClick-Revision-Visual-506D.json` separado de los anteriores.

Abre **VER-SELECTOR-CATALOGO-D.html**, con **PREVIEW-SELECTOR-CATALOGO-D** al lado. Es el componente del buscador de producción en una demostración local de 578 definiciones. Prueba «sofos», Fortinet, Arista o un SKU exacto. La lista tiene desplazamiento interno y los detalles están plegados. Flechas y Enter eligen; Escape cierra la lista. Cambiar la búsqueda invalida la selección anterior. **Revisar selección** sólo muestra el comando propuesto: no guarda inventario ni llama a la API. [Reglas del selector](SELECTOR-CATALOGO-COMPACTO.md).

## Configuraciones y límites

- `qsfp` representa jaulas físicas QSFP+/QSFP28 en esta selección. No se afirma QSFP-DD, breakout, transceptor instalado, negociación, capacidad eléctrica ni configuración de firmware. Una jaula conserva un único extremo aunque admita varias velocidades.
- Las fuentes AC corresponden a la configuración documentada de cada perfil. Una bahía vacía o un módulo opcional no se convierte en PSU instalada. X695 y S6730-S representan explícitamente sus bahías sin PSU activa; Nexus y Catalyst conservan los límites del módulo base. Consulta las fuentes de cada modelo antes de usarlo como inventario de una unidad real.
- La trasera del Huawei S6730-H24X4Y4C es neutral y está marcada `geometry_unverified`: no hay fotografía exacta comprobada. No se inventan conectores ni módulos de ventilación traseros. Las figuras de familia de Palo Alto se declaran como tales, sin atribuirles una revisión física exacta no demostrada. El aviso genérico del visor aún dice «usa una imagen» para la referencia no verificada de Huawei: prevalece la indicación específica de trasera neutral; ajustar ese texto queda pendiente.
- Las interfaces alternativas de gestión y los módulos opcionales permanecen inertes cuando no hay prueba de uso simultáneo. Se conservan las diferencias de SKU, dirección de aire y fuentes señaladas en la evidencia.
- El manual del PA-5260 declara 52,07 cm y 21 pulgadas de profundidad, que no son equivalentes. El perfil conserva 520,7 mm y la discrepancia; no certifica la holgura de un armario.
- La identidad de un puerto es su UUID ligado al grupo y ordinal físico. `gn` no identifica de forma inequívoca grupos distintos. Etiquetas de usuario y rótulos de fabricante se conservan separados. No se copian fotografías como superficie de conexión; las caras son vectores interactivos.

## Pruebas y disponibilidad

Build Release con SDK 10.0.401: cero errores y advertencias; 10 pruebas C# de revisión de hardware, 911 Node y 12 Python focales aprobadas. No es una ejecución completa de las pruebas del servidor/MFA.

La prueba PostgreSQL 17.11 y Edge se hizo en un laboratorio nuevo, con claves locales y cuenta de ejecución restringida. La actualización 31→32 conserva 528 definiciones y 523 instancias comerciales anteriores, su inventario, auditoría e historial. La migración 032 amplía la constraint específica a cinco tipos antes de insertar los perfiles; SQL 001–031 permanece intacto. El ensayo nuevo crea dos instancias independientes de cada modelo, prueba sus caras y extremos, conexiones compatibles y cuatro rechazos cruzados entre familias. Por API se guardan 237 cables: 49 RJ45, 32 SFP, 30 SFP28, 43 QSFP y 83 AC. Edge añade otros dos cables por Click-Click real (SFP28 y QSFP), para 239 en el escenario final; no se confunden con el contador API. También crea otro equipo desde el buscador, recarga y comprueba otra sesión y un lector. El reinicio probado es del proceso servidor; no se ha reiniciado Windows ni usado una VM. Al terminar quedan detenidos el clúster y los hosts del laboratorio. [Resultados y atribución](../evidence/s1-20261101/integracion506d/RESULTADOS.md).

Los HTML son visores locales, no instaladores. La instalación de MFA, VM y QA de Wascar se conservan. No copiar DLL o SQL aislados a un servidor. Quedan 288 perfiles, montajes/módulos especializados, consumidores, distribución/Restore 32 y el paquete Windows completo con su QA final. Después se ejecutará el plan de al menos 50 clientes de `docs/PLAN-LABORATORIO-50-CLIENTES.md`. El índice del cierre restante sigue **9,76/100**, sin nuevo porcentaje global por contar modelos o pruebas.

## Modelos del grupo D

| Fabricante | Modelo seleccionado | SKU/configuración | Montaje | Extremos conectables |
|---|---|---|---|---|
| Arista | CCS-720DF-48Y-2F | CCS-720DF-48Y-2F | 1 U | 1 RJ45 + 48 SFP/SFP+ + 4 SFP28 + 2 AC |
| Arista | CCS-720XP-24Y6-2F | CCS-720XP-24Y6-2F | 1 U | 25 RJ45 + 6 SFP28 + 2 AC |
| Arista | DCS-7020SR-24C2-F | DCS-7020SR-24C2-F | 1 U | 1 RJ45 + 24 SFP/SFP+ + 2 QSFP+/QSFP28 + 2 AC |
| Arista | DCS-7050CX3-32C-F | DCS-7050CX3-32C-F | 1 U | 1 RJ45 + 2 SFP/SFP+ + 32 QSFP+/QSFP28 + 2 AC |
| Arista | DCS-7050CX3-32S-R | DCS-7050CX3-32S-R | 1 U | 1 RJ45 + 2 SFP/SFP+ + 32 QSFP+/QSFP28 + 2 AC |
| Arista | DCS-7050SX3-48YC8-F | DCS-7050SX3-48YC8-F | 1 U | 1 RJ45 + 48 SFP28 + 8 QSFP+/QSFP28 + 2 AC |
| Arista | DCS-7060CX2-32S-F | DCS-7060CX2-32S-F | 1 U | 1 RJ45 + 2 SFP/SFP+ + 32 QSFP+/QSFP28 + 2 AC |
| Arista | DCS-7160-48YC6-F | DCS-7160-48YC6-F | 1 U | 1 RJ45 + 48 SFP28 + 6 QSFP+/QSFP28 + 2 AC |
| Arista | DCS-7280SR3-48YC8-F | DCS-7280SR3-48YC8-F | 1 U | 1 RJ45 + 48 SFP28 + 8 QSFP+/QSFP28 + 2 AC |
| Cisco | Catalyst 9300X-24Y | C9300X-24Y | 1 U | 1 RJ45 + 24 SFP28 + 1 AC |
| Cisco | Catalyst 9500-24Y4C | C9500-24Y4C | 1 U | 1 RJ45 + 24 SFP28 + 4 QSFP+/QSFP28 + 1 AC |
| Cisco | Catalyst 9500-48Y4C | C9500-48Y4C | 1 U | 1 RJ45 + 48 SFP28 + 4 QSFP+/QSFP28 + 1 AC |
| Cisco | Meraki MS225-48FP | MS225-48FP-HW | 1 U | 49 RJ45 + 4 SFP/SFP+ + 2 QSFP+/QSFP28 + 1 AC |
| Cisco | Meraki MS350-24P | MS350-24P-HW | 1 U | 25 RJ45 + 4 SFP/SFP+ + 2 QSFP+/QSFP28 + 1 AC |
| Cisco | Nexus 93108TC-FX3 | N9K-C93108TC-FX3 | 1 U | 49 RJ45 + 6 QSFP+/QSFP28 + 2 AC |
| Cisco | Nexus 93180YC-FX | N9K-C93180YC-FX | 1 U | 1 RJ45 + 48 SFP28 + 6 QSFP+/QSFP28 + 2 AC |
| Cisco | Nexus 9336C-FX2 | N9K-C9336C-FX2 | 1 U | 1 RJ45 + 36 QSFP+/QSFP28 + 2 AC |
| Dell | PowerSwitch N3248P-ON | N3248P-ON | 1 U | 49 RJ45 + 4 SFP/SFP+ + 2 QSFP+/QSFP28 + 1 AC |
| Dell | PowerSwitch S4128F-ON | S4128F-ON | 1 U | 1 RJ45 + 28 SFP/SFP+ + 2 QSFP+/QSFP28 + 2 AC |
| Extreme Networks | 4120-24MW-4Y | 4120-24MW-4Y | 1 U | 25 RJ45 + 4 SFP28 + 2 QSFP+/QSFP28 + 1 AC |
| Extreme Networks | X590-24x-1q-2c | 16790 | 1 U | 1 RJ45 + 24 SFP/SFP+ + 3 QSFP+/QSFP28 + 2 AC |
| Extreme Networks | X695-48Y-8C | X695-48Y-8C | 1 U | 1 RJ45 + 48 SFP28 + 8 QSFP+/QSFP28 |
| FS | N5860-48SC | n5860-48sc | 1 U | 1 RJ45 + 48 SFP/SFP+ + 8 QSFP+/QSFP28 + 2 AC |
| FS | N8560-48BC | n8560-48bc | 1 U | 1 RJ45 + 48 SFP28 + 8 QSFP+/QSFP28 + 2 AC |
| Fortinet | FortiGate 1000F | FG-1000F | 2 U | 10 RJ45 + 16 SFP/SFP+ + 8 SFP28 + 2 QSFP+/QSFP28 + 2 AC |
| Fortinet | FortiGate 2600F | FG-2600F | 2 U | 18 RJ45 + 2 SFP/SFP+ + 16 SFP28 + 4 QSFP+/QSFP28 + 2 AC |
| Fortinet | FortiGate 3001F | FG-3001F | 2 U | 18 RJ45 + 16 SFP28 + 6 QSFP+/QSFP28 + 2 AC |
| Huawei | Huawei S6730-S24X6Q | S6730-S24X6Q | 1 U | 1 RJ45 + 24 SFP/SFP+ + 6 QSFP+/QSFP28 |
| Huawei | S6730-H24X4Y4C | S6730-H24X4Y4C | 1 U | 1 RJ45 + 24 SFP/SFP+ + 4 SFP28 + 4 QSFP+/QSFP28 + 1 AC |
| Juniper | ACX7024-AC | ACX7024-AC | 1 U | 1 RJ45 + 24 SFP28 + 4 QSFP+/QSFP28 + 1 AC |
| Juniper | EX3400-48P | EX3400-48P | 1 U | 49 RJ45 + 4 SFP/SFP+ + 2 QSFP+/QSFP28 + 1 AC |
| Juniper | EX3400-48T | EX3400-48T | 1 U | 49 RJ45 + 4 SFP/SFP+ + 2 QSFP+/QSFP28 + 1 AC |
| Juniper | EX4100-48P | EX4100-48P | 1 U | 49 RJ45 + 4 SFP/SFP+ + 4 SFP28 + 1 AC |
| Juniper | EX4400-48F | EX4400-48F | 1 U | 1 RJ45 + 48 SFP/SFP+ + 2 QSFP+/QSFP28 + 1 AC |
| Juniper | MX204 | MX204 | 1 U | 1 RJ45 + 8 SFP/SFP+ + 4 QSFP+/QSFP28 + 2 AC |
| Juniper | QFX5100-48S-6Q | QFX5100-48S-6Q | 1 U | 1 RJ45 + 49 SFP/SFP+ + 6 QSFP+/QSFP28 + 2 AC |
| Juniper | QFX5120-48Y-AFI2 | QFX5120-48Y-AFI2 | 1 U | 1 RJ45 + 48 SFP28 + 8 QSFP+/QSFP28 + 2 AC |
| MikroTik | CCR2216-1G-12XS-2XQ | CCR2216-1G-12XS-2XQ | 1 U | 1 RJ45 + 12 SFP28 + 2 QSFP+/QSFP28 + 2 AC |
| Palo Alto Networks | PA-3260 | PA-3260 | 2 U | 15 RJ45 + 9 SFP/SFP+ + 4 QSFP+/QSFP28 + 2 AC |
| Palo Alto Networks | PA-3410 | PA-3410 | 1 U | 15 RJ45 + 11 SFP/SFP+ + 4 SFP28 + 2 AC |
| Palo Alto Networks | PA-3420 | PA-3420 | 1 U | 15 RJ45 + 11 SFP/SFP+ + 4 SFP28 + 2 AC |
| Palo Alto Networks | PA-3430 | PA-3430 | 1 U | 15 RJ45 + 11 SFP/SFP+ + 4 SFP28 + 2 QSFP+/QSFP28 + 2 AC |
| Palo Alto Networks | PA-3440 | PA-3440 | 1 U | 15 RJ45 + 11 SFP/SFP+ + 4 SFP28 + 2 QSFP+/QSFP28 + 2 AC |
| Palo Alto Networks | PA-5260 | PA-5260 | 3 U | 7 RJ45 + 18 SFP/SFP+ + 5 QSFP+/QSFP28 + 2 AC |
| Palo Alto Networks | PA-5410 | PA-5410 | 2 U | 8 RJ45 + 15 SFP/SFP+ + 4 SFP28 + 5 QSFP+/QSFP28 + 2 AC |
| Palo Alto Networks | PA-5420 | PA-5420 | 2 U | 8 RJ45 + 15 SFP/SFP+ + 4 SFP28 + 5 QSFP+/QSFP28 + 2 AC |
| Palo Alto Networks | PA-5430 | PA-5430 | 2 U | 8 RJ45 + 15 SFP/SFP+ + 4 SFP28 + 5 QSFP+/QSFP28 + 2 AC |
| Palo Alto Networks | PA-5440 | PA-5440 | 2 U | 8 RJ45 + 15 SFP/SFP+ + 4 SFP28 + 5 QSFP+/QSFP28 + 2 AC |
| Ubiquiti | Enterprise Campus Aggregation | ECS-Aggregation | 1 U | 48 SFP28 + 6 QSFP+/QSFP28 + 2 AC |
| Ubiquiti | Enterprise Fortress Gateway | EFG | 1 U | 2 RJ45 + 2 SFP/SFP+ + 2 SFP28 + 2 AC |
