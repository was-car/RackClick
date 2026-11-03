# Selección506 · grupo H · Aruba6300 y Nokia7220IXR

01.11.2026. **Seis perfiles nuevos y doce caras** sobre el contrato SFP56/QSFP-DD. [Abrir los modelos](../VER-SELECCION-506-H.html) · [Probar el selector](../VER-SELECTOR-CATALOGO-H.html) · [Cobertura vigente](COBERTURA-MODELOS-ELEGIDOS.md).

## Resultado

Desarrollo37: **734definiciones/729comerciales**; selección original **374/506(73,91%),132pendientes**. Los355comerciales adicionales siguen separados. Los seisperfiles son cinco equipos1U y un NokiaH4de2U, revisión`selected506h-20261101-v1`.

Hay **257extremos**:102RJ45(incluyeOOBM/MGMT),6SFP/SFP+,12SFP56,128QSFP-DD y9entradasAC. Cada jaula mantiene un UUID/grupo/ordinal propio; no se sustituye por un tipo óptico anterior ni se crean puertos por cada lane.

## Cómo revisarlo

1. Extrae el ZIP en una carpeta nueva. Conserva **PERFILES-SELECCION-506-H** junto a **VER-SELECCION-506-H.html** y ábrelo con Edge/Chrome.
2. En la columna izquierda, bajo **Buscar marca o modelo**, escribe Aruba, Nokia o el SKU. Pulsa un resultado. En el centro aparecen las dos caras y el enlace **HTML individual de este modelo**.
3. Despliega **Alcance y límites de las fuentes de este modelo**. Revisa la población de fuentes y bahías, las reservas de identidad y la revisión física. NokiaH4debe tener64jaulasQSFP-DD; los dosH3/D5tienen32cadauno. Aruba tiene4SFP56por equipo.
4. Pulsa un puerto y después el extremo de prueba del mismo tipo. Para AC utiliza la salida de prueba. Prueba SFP56↔QSFP-DD: debe rechazar la mezcla. Al desplazar las caras, el cable debe seguir anclado al puerto. Las piezas USB/console/indicadores dibujados no se convierten en puertos de red.
5. Bajo las caras, en **Tu revisión de este modelo**, elige Pass/Not Pass/No probado y escribe observaciones. En la izquierda pulsa **Exportar mis resultados JSON** y guarda `RackClick-Revision-Visual-506H.json` separado de los lotes anteriores. **Importar en casillas vacías** conserva las observaciones existentes.
6. Abre **VER-SELECTOR-CATALOGO-H.html** con **PREVIEW-SELECTOR-CATALOGO-H** al lado. En **Perfil de referencia** escribe sofos, Aruba, Nokia o un SKU. La lista mantiene desplazamiento interno; flechas/Enter eligen, Escape cierra y cambiar la búsqueda invalida la selección anterior. **Revisar selección** muestra el comando propuesto, sin escribir inventario.

El visor es una demostración local del componente; no instala ni conecta con la API. Las pruebas del servidor descritas abajo se ejecutaron por separado en laboratorio. Tus notas y resultados anteriores permanecen intactos.

## Configuraciones y límites que deben conservarse

- **JL668A/JL664AsonnonPoE.** QuickSpecs contiene una descripciónPoE contradictoria; se sigue la tablaeléctrica oficialQSG. JL665AClass4es capacidad descriptiva: no se simulan habilitación, consumo ni presupuestoPoE. Las alturasFconservan43,9mm de QuickSpecs frente al redondeo44mm del manual.
- **JL664A:** configuración curada con unaPSUJL085A250WAC instalada y la segunda bahía vacía. No se afirma que laPSU venga incluida en la base. Las diferenciasJL669A/Bde ventiladores quedan declaradas.
- **Nokia:** configuración curada de dosPSUAC,1500WenD5,1600WenH3y2400WenH4, con cotas/conteos primarios. LosP/N3HEproceden de la biblioteca comunitaria; no están fijados por la ficha primaria de familia. **Las seiscarasNokia mantienen `geometry_unverified`** para revisión/posición fina de esas referencias; no son carcasas certificadas por número de pieza. Las fuentes, avisos y forma propia permanecen visibles.
- **H4:** el expedienteIR/YAML enumeraba32interfaces pese al nombre64. El perfil nuevo corrige a64según la fuenteNokia; el expediente histórico permanece intacto. La tablaD5de otra guía enumeraSFP+33–38, frente a dosSFP+ en ficha/foto: se conservan sólo33/34y se declara la contradicción.
- La jaula física no acredita óptica, DAC, negociación, velocidad activa, VSF, adaptación ni breakout. Los dos tipos nuevos exigen pareja del mismo tipo. AC usa el contrato genérico de roles inlet/outlet; las familiasIEC y circuitos eléctricos específicos siguen pendientes. No se inventan fuentes a partir de bahías vacías.
- Dibujos vectoriales propios a partir de referencias; sin fotografías como superficie de conexión ni imágenes empaquetadas. Las etiquetas del fabricante y los nombres del usuario se conservan separados.

## Pruebas realmente ejecutadas

SDK10.0.401/Node24.21.0: compilación0errores/0advertencias,20C#focales y955Node en76archivos, sin omitidas. Compilador:8Pythonfocales; sus6Node están incluidos en la regresión, no se suman como otra suite completa. No se ejecutó toda la suiteC#/MFA.

PostgreSQL17.11/Edge en clúster y bases nuevos, primer intento de integración correcto. La migración36→37conserva las728definiciones y723instancias comerciales anteriores, sus soportes, UUID, inventario, auditoría, operaciones e historial. Repetir migración no cambia datos. En otra base se crean dos instancias independientes de cada modelo. Se prueban24cablesAPI(6RJ45,3SFP,3SFP56,3QSFP-DD,9AC), además de2cables por Click-Click con ratónCDP real. Las redes se prueban por tipo presente en cada modelo; todas las entradasAC de la primera pareja quedan conectadas.

También pasan cuatro cruces409, replay, conflicto412, revisión desconocida422, rollback forzado de auditoría, lector403, tablas de catálogo sóloSELECT y ausencia deDDL en el runtime. El navegador inspecciona12caras/257extremos de la primera pareja, UUID/grupo/ordinal/cara, sin fotos y objetivos≥24px; crea otro equipo desde el selector734y comprueba móvil390px, recarga y otra sesión. Un reinicio del proceso servidor conserva el estado. No es reinicioWindows ni ensayo de instalador.

La revisión independiente recompone derivados y coteja fuentes/históricos, ejecuta focos propios de datos/Atlas6/12y selector734. AtribuyePG/.NET/regresión general al coordinador, sin repetirlos ni convertirlos en pruebas suyas. [Resultados, comandos y revisión](../evidence/s1-20261101/integracion506h/RESULTADOS.md).

## Disponibilidad y siguiente trabajo

QA-158planificada; la instalaciónMFA, VM y bases de Wascar no se actualizaron. No copiar DLL/SQL aislados a un servidor. Faltan132perfiles elegidos, contratos especializados y distribución/Restore37/paqueteWindows completo con QA final. Después se ejecuta el plan de al menos50clientes. **Índice del cierre restante9,76/100 sin cambio; la cobertura del catálogo no es porcentaje global.**

## Modelos

| Fabricante | Modelo seleccionado | SKU/configuración | Reserva | Extremos conectables |
|---|---|---|---|---|
| HPE | Aruba 6300F-24G-4SFP56 | JL668A | 1 U | 24 RJ45 + 4 SFP56 + 1 RJ45 + 1 AC |
| Nokia | 7220 IXR-H3 32QSFPDD 2SFP+ | 3HE16425AA | 1 U | 32 QSFP-DD + 2 SFP/SFP+ + 1 RJ45 + 2 AC |
| HPE | Aruba 6300M-24G-4SFP56 | JL664A | 1 U | 24 RJ45 + 4 SFP56 + 1 RJ45 + 1 AC |
| HPE | Aruba 6300F-48G-POE4-4SFP56 | JL665A | 1 U | 48 RJ45 + 4 SFP56 + 1 RJ45 + 1 AC |
| Nokia | 7220 IXR-D5 32*400GE | 3HE19313AA | 1 U | 32 QSFP-DD + 2 SFP/SFP+ + 1 RJ45 + 2 AC |
| Nokia | 7220 IXR-H4 64QSFPDD 2SFP+ | 3HE17750AA | 2 U | 64 QSFP-DD + 2 SFP/SFP+ + 1 RJ45 + 2 AC |
