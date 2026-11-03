# Selección 506 · grupo I · cinco perfiles de red

01.11.2026. [Abrir los cinco modelos](../VER-SELECCION-506-I.html) · [Probar el selector](../VER-SELECTOR-CATALOGO-I.html) · [Cobertura vigente](COBERTURA-MODELOS-ELEGIDOS.md).

## Resultado y alcance

Desarrollo 38: **739 definiciones, 734 comerciales**. La selección original tiene **379/506 cubiertos (74,90 %), con 127 pendientes**. Los 355 comerciales adicionales se cuentan aparte. Esta tanda añade cinco perfiles y diez caras, revisión `selected506i-20261101-v1`, con **211 extremos conectables**. No modifica la instalación nativa MFA ni sus datos.

| Fabricante | Modelo | SKU/configuración | Ocupación | Extremos conectables |
|---|---|---|---|---|
| Fortinet | FortiGate 3701F | FG-3701F | 2 U | 2 rj45 + 2 sfp56 + 4 sfp28 + 18 sfp56 + 4 qsfpdd + 2 power |
| Ciena | 5171 Router | 170-5171-920 | 2 U | 32 sfp28 + 8 sfp56 + 1 rj45 + 2 power |
| Juniper | ACX7332 | ACX7332 | 3 U | 32 sfp28 + 8 qsfp + 1 rj45 + 2 power |
| Huawei | NE8000 F1A-8H20Q | 02353AES | 1 U | 28 sfp + 20 sfp28 + 8 qsfp + 1 rj45 + 2 power |
| Palo Alto Networks | PA-5580 | PA-5580 | 3 U | 12 qsfp + 8 qsfpdd + 8 sfp28 + 4 sfp + 2 power |

Los tipos indican la familia de conector físico, no ópticas instaladas, negociación ni velocidad activa. Cada extremo conserva UUID, grupo, ordinal, cara y rol. Una bahía vacía no añade un puerto.

## Cómo revisarlo paso a paso

1. Extrae el ZIP en una carpeta nueva. Deja **PERFILES-SELECCION-506-I** junto a **VER-SELECCION-506-I.html**. Abre ese HTML con Edge o Chrome.
2. Arriba a la izquierda, en **Buscar marca o modelo**, escribe Palo Alto, Fortinet, Huawei, Ciena, Juniper o el SKU. Pulsa un resultado. En el centro aparecen frontal y trasera; **HTML individual de este modelo** abre su archivo separado.
3. Despliega **Alcance y límites de las fuentes de este modelo**. Contrasta la configuración instalada, las bahías vacías y las reservas de forma/revisión. La trasera de Ciena es neutral; no se presenta como foto o geometría certificada.
4. Pulsa un puerto y luego un extremo de prueba del mismo tipo. Para AC elige la salida de prueba. Prueba SFP56 con QSFP-DD: debe rechazarse la mezcla. Desplaza la cara y comprueba que el cable sigue anclado. Los controles, consola y conectores inertes no adquieren UUID de red.
5. Debajo de las caras, en **Tu revisión de este modelo**, marca Pass, Not Pass o No probado y añade observaciones. A la izquierda pulsa **Exportar mis resultados JSON**. Guarda `RackClick-Revision-Visual-506I.json` separado de tus resultados anteriores. **Importar en casillas vacías** conserva las notas ya existentes.
6. Abre **VER-SELECTOR-CATALOGO-I.html**, con **PREVIEW-SELECTOR-CATALOGO-I** al lado. En **Perfil de referencia** busca sofos, Fortinet, Juniper o un SKU. La lista tiene desplazamiento interno; flechas y Enter eligen, Escape cierra y cambiar el texto invalida la selección anterior. **Revisar selección** muestra un comando de ejemplo: no escribe inventario.

Los visores son locales y no requieren cuenta ni conectan a la API. Las pruebas reales del servidor se hicieron por separado en un laboratorio nuevo. No se deben copiar DLL o SQL sueltos a la instalación de Wascar.

## Configuraciones y reservas

- **PA-5580:** 3 U; doce QSFP28, ocho QSFP-DD, ocho SFP28 y cuatro SFP auxiliares. HSCI A/B queda inerte. Configuración explícita de dos fuentes AC de 2700 W con alimentación high-line; las otras dos bahías quedan vacías. No se afirma que esta configuración sea la de redundancia completa de cuatro fuentes. La figura frontal es compartida de familia; el orden/rol fino de los cuatro SFP auxiliares conserva su reserva.
- **FortiGate 3701F:** 2 U; dieciocho SFP56 de datos, dos SFP56 HA, cuatro SFP28 ULL, cuatro QSFP-DD, dos RJ45 MGMT y dos entradas AC. ULL con velocidad predeterminada de 10 G no convierte la jaula SFP28 en otro tipo.
- **Huawei NE8000 F1A-8H20Q, 02353AES:** 1 U; los veintiocho SFP+ y veinte SFP28 son grupos físicos distintos, además de ocho QSFP28. MGMT trasero y dos AC de configuración explícita. Interfaces reservadas, timing y consola quedan inertes; no se inventa un SKU de conjunto PSU.
- **Ciena 5171 Gen2, 170-5171-920:** los conteos 32 SFP28 y 8 SFP56 proceden de la ficha Gen2 exacta. La foto de familia anterior sólo orienta la forma. Módulos opcionales vacíos; no se añaden cuatro QSFP-DD. Dos entradas AC frontales de la configuración elegida. Sin referencia trasera certificada: trasera neutral y reserva visible, sin conectores o ventiladores inventados. Las notas documentales no se presentan como fotos.
- **Juniper ACX7332:** configuración fija de 32 SFP28 y 8 QSFP28, un RE0 con MGMT y dos AC frontales; RE1 y tres bahías de tarjeta de línea vacías. El máximo de una foto con módulos opcionales no se toma como puertos instalados.
- **Nokia SR-1se reservado:** la fuente comunitaria y la foto no bastan para confirmar su población de alimentación. No se integra en esta tanda ni se cuenta como cubierto. Su expediente e imágenes se conservan.

No se simulan lanes, breakout, adaptación, ópticas, circuitos eléctricos particulares ni presupuesto PoE. Se reutilizan los siete tipos existentes y el contrato genérico AC inlet/outlet. Los dibujos son vectores propios basados en referencias; no hay fotografías usadas como superficie de conexión ni imágenes originales redistribuidas.

## Pruebas realizadas y límites

SDK 10.0.401, PostgreSQL 17.11 y Node 24.21.0 fijados. Build sin errores ni advertencias, **20 pruebas C# focales y 961 Node** en 77 archivos. La regresión Node incluye los focos del compilador; no se suman dos veces. No es la suite C#/MFA completa.

Migración real **37→38**: conserva 734 definiciones y 729 instancias comerciales previas, UUID, soportes, auditoría, operaciones e historial. Una segunda migración no cambia datos. En otra base nueva se crean dos instancias por modelo. Se comprueban **28 cables por API** (4 rj45, 5 sfp28, 2 sfp56, 2 qsfpdd, 10 power, 3 qsfp, 2 sfp) y otros **dos por Click-Click real** con ratón CDP, todas las entradas AC de la primera instancia y cuatro cruces incompatibles. También replay, conflicto 412, revisión desconocida 422, rollback de auditoría, lector 403, catálogo sólo SELECT y runtime sin DDL.

Edge inspecciona diez caras y 211 extremos de las primeras instancias, sus UUID/caras y objetivos de al menos 24 px, sin fotos. Se crea otro equipo desde el selector 739; recarga, otra sesión y reinicio del proceso conservan el estado. Se comprueban móvil de 390 px y permisos. Esto no es reinicio de Windows, ensayo de instalador ni actualización de QA.

La revisión independiente distingue sus propias pruebas de datos, reconstrucción de derivados y visores de las pruebas PostgreSQL/.NET del coordinador. [Evidencia, comandos y dictamen](../evidence/s1-20261101/integracion506i/RESULTADOS.md).

## Disponibilidad y próximo trabajo

**QA-159 planificada**: estos cambios aún no están en la instalación nativa de Wascar. Faltan 127 modelos, contratos especializados y la distribución/Restore/paquete Windows completos con QA final. El laboratorio de al menos 50 clientes viene después de completar los 506 elegidos. **Índice del cierre restante: 9,76/100 sin cambio; no es porcentaje global del producto.**
