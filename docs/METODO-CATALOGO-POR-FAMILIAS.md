# Catálogo: procedimiento de ampliación por familias

## Aplicación comprobada: grupo K, cinco familias /52 configuraciones

[Grupo K](INTEGRACION-506-GRUPO-K.md) y [evidencia](../evidence/s1-20261101/integracion506k/RESULTADOS.md). Este grupo aplica el método con52 perfiles/104caras/920extremos, una ampliación común de contrato y un build C#. No convierte un soporte sintético en otro modelo comercial ni una reserva en cobertura.

Para repetirlo en otras familias:

1. Congelar baseline y plan con IDs exactos. Separar autoría por arquitectura en archivos distintos; compartir sólo formas respaldadas por la fuente y escribir los cambios de cada SKU. Conservar las fuentes y sus revisiones anteriores.
2. Reutilizar `tools/hardware_family_v2.py` para los nueve medios admitidos y la clasificación opcional `physicalConnector`. El enum cerrado está en el contrato K; su coincidencia entre frontend, C# y SQL tiene una prueba. Un conector nuevo exige extender ese contrato con su negativo, no rebautizarlo como RJ45.
3. Para potencia, declarar por separado boca, cara y rol. El descriptor físico no añade validación de acople directo ni certifica un cordón/circuito. Mantener los roles y dejar desconocido lo no acreditado. Para IDC, declarar frontalRJ45/traseraIDC sin fabricar cable interno o trazado. Para una base vacía usar cero grupos; no poblarla para satisfacer el parser.
4. Separar la envolvente real del equipo y el hueco útil del soporte. Una bandeja comercial sin cota de hueco/carga no se convierte en padre de hijos. Un soporte propio se identifica como sintético y no certifica instalación real. Un accesorio que comparte la U o una PDUvertical0U queda reservado hasta tener montaje correcto.
5. En equipos pequeños, diseñar vistas compactas antes de probarlas en el rack: el padre tiene anchura acotada, las bocas siguen teniendo al menos24px. El grupo K usa400de ancho para NAS, preservando dimensiones físicas, relación de aspecto y los límites originales. Comprobar cuatro caras en el navegador real, no sólo el PNG de autoría.
6. Compilar todas las familias juntas desde la copia congelada, repetir sólo los focos afectados al corregir, y hacer una regresión pertinente al estabilizar. Los fallos de fixtures y expectativas antiguas se conservan y se explican; no se anuncian como fallos de producto ni como PASS inicial. La revisión la hace una persona distinta.
7. Verificar catálogo antiguo/instancias/historial sin cambios, cada modelo nuevo con otra instancia independiente, todos los UUID/caras, persistencia, permisos y rollback. Probar conexiones representativas por medio y todas las bocas de energía con roles correctos, sin afirmar una certificación eléctrica. Comprobar los formatos que consumen el tipo nuevo.
8. Antes del ZIP, ligar tanto galería como selector al digest final del catálogo, verificar bytes/sumas/CRC/enlaces y preservar observaciones anteriores. Actualizar manual, QA planificada, continuidad, changelog y la cobertura por IDs. Ningún resultado de Wascar se fabrica ni se sustituye.

La configuración/BOM y los límites se presentan en el formulario dentro de **Detalles del modelo y conectores**, cerrado al inicio. No volver a ocultar la diferencia entre chasis vacío, población elegida y dimensiones conservadoras de conjunto. Los modelos restantes se eligen de la cola vigente; no requieren empezar otra investigación completa.


01.11.2026 · Petición de Wascar. Aplica a los modelos pendientes de la selección de 506 y a los que se elijan en el futuro. Una familia comparte arquitectura física comprobada; una marca o un nombre parecido no bastan.

**Punto de partida de esta tanda:** 379/506 perfiles cubiertos, 127 pendientes; desarrollo 38 con 739 definiciones/734 comerciales. Este documento no acredita ningún modelo nuevo. [Cobertura vigente](COBERTURA-MODELOS-ELEGIDOS.md) · [Plantilla de preparación](PLANTILLA-FAMILIA-CATALOGO.json).

## Qué se reutiliza y qué se comprueba por modelo

| Compartido cuando la fuente lo permite | Comprobación obligatoria de cada SKU/configuración |
|---|---|
| Arquitectura y plantilla vectorial de carcasa | Medidas, orientación, U y montaje reales |
| Distribución paramétrica de bancos de puertos | Número, tipo, cara, rótulo y ordinal de cada boca |
| Manual de familia y referencias comunes identificadas | Diferencias de revisión, fuentes, gestión y población |
| Compilador, selector, renderer y escenario de prueba | Identidad exacta, hash, grupos, UUID y guardado |
| Un build/regresión de integración del grupo completo | Ambas caras y todos los extremos del perfil |

Se dibuja una base propia y se aplican diferencias explícitas: filas, columnas, colores, ventilación, bahías, fuentes y rótulos. No se estira una foto ni se ocultan puertos activos bajo una imagen. No se copian imágenes, código o manuales de terceros sin revisar sus condiciones; normalmente se consultan las referencias y se distribuyen los vectores propios.

## 1. Elegir la familia y cerrar el alcance

1. Leer la cobertura vigente, la hoja de ruta y la continuidad. Conservar el estado Git y los hashes del baseline antes de editar.
2. Agrupar por arquitectura: equipo activo fijo, AP PoE, panel pasivo, chasis modular, UPS/ATS/PDU, rack o bandeja. Separar las subfamilias que exijan otro conector, montaje o comportamiento.
3. Crear un plan con IDs exactos, SKU base, revisión, población de módulos/PSU y responsables. Anotar aparte los modelos reservados y la información concreta que falta. El número de candidatos es una previsión, no cobertura acreditada.
4. Dimensionar el lote por familias compatibles disponibles. No limitarlo arbitrariamente a cinco ni forzar veinte si faltan fuentes o contrato. Los casos dudosos no bloquean a las otras familias.

Los IDs originales y las fuentes históricas no se cambian para hacer coincidir un modelo. Un producto de catálogo con módulos elegidos se presenta como **configuración curada**: la base y cada cantidad de módulos permanecen explícitas. No se afirma que el fabricante los entregue incluidos.

## 2. Investigar una vez la base y registrar las diferencias

Buscar primero lo existente en RackClick. Reutilizar la investigación válida, la caché y los manuales comunes de la familia; consultar proveedor y repositorio original para resolver las diferencias de SKU. No repetir búsquedas generales para cada variante.

Para cada dato, registrar fuente, localizador, alcance y fecha. Si existe una descarga local, guardar tamaño y SHA256. Si sólo se pudo consultar la web, dejar URL/localizador y esa limitación: no inventar un hash. Una nota de consulta propia no es una captura del fabricante ni una foto trasera.

La biblioteca NetBox fijada por commit sirve como referencia complementaria. Su archivo `source-matches.json` es un índice de coincidencias; no sustituye los hechos de `selection462/part-01.json`, `part-02.json`, `part-03.json` y `official.json`. No mezclar ambos conjuntos por ID y sobrescribir accidentalmente hechos con registros vacíos.

Antes de autoría, cerrar una tabla por SKU: medidas, montaje, módulos, grupos y puertos físicos, interfaces inertes, cara de alimentación y diferencias respecto a la base. Las dudas quedan como reservas visibles, sin elevar una foto de familia a revisión mecánica certificada.

## 3. Verificar el contrato antes de dibujar

| Caso | Regla de implementación |
|---|---|
| Wi-Fi, LTE, 5G lógico | No crear una boca de cable por cada radio o estándar |
| AP alimentado por PoE | Registrar las bocas Ethernet reales; no inventar entrada AC ni simular presupuesto PoE |
| Equipo no-rack sobre bandeja | Conservar sus tres cotas y declarar orientación; comprobar que cabe realmente. No equivale a montaje en techo/pared |
| Panel vacío | No poblarlo implícitamente con jacks |
| Panel con acopladores elegidos | Especificar base + cantidad + PN de cada acoplador y su compatibilidad física |
| RJ45 hembra/hembra 1:1 | Dos extremos distintos y continuidad declarada; `mapping: "one-to-one"`, `tracingAvailable: false` en el contrato actual |
| RJ45 a IDC/110, fibra, serial o DC | Otro contrato cuando corresponda; no convertirlo en RJ45 o SFP por conveniencia |
| PDU/UPS/ATS | Entrada y salida tienen roles distintos; IEC/NEMA, sexo del conector, cordón cautivo y conmutación no se deducen de `power` |
| Chasis modular | Sólo aparecen los módulos de la configuración elegida. Las bahías vacías no añaden interfaces |

La continuidad pasiva no crea un cable externo ni un trazado de rutas automáticamente. Cada extremo conserva UUID, grupo, ordinal y cara. Se comprueba por IDs; `gn` no es una identidad global.

Si el autor de perfiles necesita un contrato ya existente que su helper no admite, se añade una extensión de autoría separada y acotada. Se conservan los helpers y catálogos publicados. Una copia estructural usada para validar nunca sustituye los datos originales que se compilan, almacenan y muestran.

## 4. Producir datos y dibujos por familia

Mantener una fuente de autoría por familia, una base de geometría y diferencias explícitas por modelo. Cada modelo sigue teniendo una revisión inmutable, evidencia, límites y posiciones reales de puertos. Antes de integrar:

- Identidad y SKU originales, sin colisiones con el catálogo existente.
- Grupos con tipos, roles, caras, nombres y prefijos válidos; cotas y U comprobadas.
- Un objetivo interactivo por extremo real, sin duplicar puertos por velocidad o lane.
- Contraste legible y objetivos de al menos 24 px; la densidad se resuelve con escala/desplazamiento.
- Frontal y trasera contrastados. La ausencia de referencia se muestra como reserva, con superficie neutral y sin detalles inventados.
- Componentes opcionales/inertes sin UUID de red. Fotografías como referencia privada, no como superficie operativa.
- Antes de adopción, el formulario de selección debe permitir reconocer la población elegida y el origen de las cotas. Que el BOM esté en la evidencia no demuestra que se comunique bien en la interfaz; registrar esa reserva si sólo aparece en manual/galería.

La plantilla de preparación enlazada arriba es una ficha; **no es un perfil instalable ni una orden de ejecución**. Los inputs efectivos de cada tanda quedan fijados en su plan y lock.

Si la configuración lleva módulos que sobresalen, distinguir las cotas del chasis vacío, las de los módulos y la envolvente del conjunto. Sin plano del ensamblaje, una envolvente conservadora debe declarar su cálculo y sus exclusiones; no se presenta como medida certificada ni incluye automáticamente clavijas, cables o radios de curvatura. No usar las medidas del embalaje como medidas del equipo.

## 5. Integrar y probar el grupo una sola vez

1. Congelar autorías, plan, lock y entradas transitivas. Compilar sólo una copia aislada de las fuentes asignadas; no adoptar todo el árbol de trabajo concurrente.
2. Ejecutar negativos específicos del contrato nuevo y del generador. Si falla algo, conservar intento, causa, corrección y repetición; no presentar el binario previo como resultado del build fallido.
3. Hacer un build final, la regresión pertinente y binlogs privados únicos. No repetir la suite completa por cada modelo ni sumar dos veces focos incluidos en otra suite.
4. En PostgreSQL nuevo, migrar desde el baseline y comprobar conservación de definiciones e instancias anteriores, historial, auditoría y operaciones. Repetir migración debe conservar el estado.
5. En otra base nueva, crear todas las configuraciones de la tanda. Comprobar grupos/UUID/caras y propiedades especiales de cada familia. Probar creación, ocupación, conexiones compatibles e incompatibles, replay, conflictos, rollback y permisos de runtime.
6. En navegador, inspeccionar todos los modelos y ambas caras, probar Click-Click representativo de cada comportamiento nuevo, guardado confirmado, F5, otra sesión autorizada y un lector. El reinicio del proceso verifica persistencia; no se anuncia como reinicio Windows.
7. Una persona distinta revisa los cambios y ejecuta focos independientes acotados. Debe separar lo que ejecutó de lo que leyó en la evidencia del implementador.

## 6. Entregar y dejar preparados los siguientes modelos

Actualizar continuidad, changelog, cobertura y registro maestro; regenerar la guía QA con disponibilidad real. Conservar resultados y notas de Wascar, fuentes históricas, bases, VM y paquetes anteriores. Mantener un resultado responsable por requisito, sin asignar puntos nuevos por botones, variantes o pruebas.

El ZIP de revisión contiene visor, HTML por modelo, manual, licencias y evidencias sanitizadas; verificar enlaces, nombres, CRC y SHA256 de todos sus miembros antes de entregar. Los binlogs, secretos y fotografías originales no entran. Este ZIP no equivale al instalador Windows completo.

Para una familia aplazada, dejar: miembros exactos, motivo de reserva, contrato que falta, dato/fuente por conseguir, siguiente prueba que permitiría desbloquearla y prioridad. La próxima sesión retoma ese punto; no repite desde cero una investigación ya válida.

La cobertura del catálogo y el índice de cierre restante son métricas distintas. Ni investigar una familia ni crear un plan aumenta el porcentaje global o acredita QA.
