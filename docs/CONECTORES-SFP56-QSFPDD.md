# SFP56 y QSFP-DD · soporte para continuar el catálogo

01.11.2026. Se amplía el contrato a siete familias físicas en desarrollo36. **No añade modelos comerciales:** selección368/506(72,73%),138pendientes;728definiciones/723comerciales. El catálogo sellado35 y los perfiles anteriores permanecen intactos.

## Qué cambia

- `sfp56` y `qsfpdd` conservan tipo, UUID, grupo, ordinal y cara. Sus nombres son SFP56 y QSFP-DD; los símbolos propios muestran56/DD. Una jaula sigue siendo un extremo.
- Validación servidor/SQL036, colores personales, filtros, edición/plantillas, avisos y formatos de salida reconocen ambos tipos. Diez colores anteriores conservados; se añaden dos identificadores. El archivo RC9 adoptado permanece intacto: el build adapta su componente extraído mediante anclas verificadas.
- Para un puerto de estas dos familias se exige un par del mismo tipo incluso en un equipo manual sin perfil. Los perfiles existentes conservan su comprobación estricta y los demás equipos manuales su comportamiento histórico. Potencia mantiene sus roles y validaciones previos.
- No se deducen transceptores, LC/MPO, velocidad, negociación, adaptación, compatibilidad cruzada o breakout. La compatibilidad mecánica documentada por fabricantes requiere información adicional para convertirse en un enlace configurado. El importador RC9 histórico sigue rechazando estos tipos: no se promete un roundtrip nuevo.

## Ver la demostración local

1. Extrae el ZIP en una carpeta nueva y conserva la carpeta `VISTA-CONECTORES-7` junto al acceso HTML.
2. Abre **VER-CONECTORES-7.html** con Edge/Chrome. En el centro hay dos bloques, **Extremos A** y **Extremos B**.
3. Pulsa **SFP56** en A y luego **SFP56** en B. Bajo los bloques aparece la confirmación local. Repite con **QSFP-DD**.
4. Pulsa SFP56 en A y QSFP-DD en B: debe indicar tipos distintos y rechazar. **Reiniciar demostración** borra sólo las conexiones de esta página. AC se muestra como símbolo, pero la demostración no simula su conexión sin roles.

El visor reutiliza el componente operativo, pero **no llama a la API ni guarda inventario**. No es un modelo de marca, un instalador ni una prueba de persistencia del servidor. Los símbolos no son cotas mecánicas certificadas. No sustituye tus resultados ni observaciones anteriores.

## Pruebas y límites reales

SDK10.0.401/Node24.21.0, sin versiones o dependencias nuevas: build0errores/0advertencias,20C#focales y949Node, todos aprobados y sin omitidas. Helperv3:8Python. No se ejecutó toda la suite C#/MFA.

PostgreSQL17.11 y Edge nativos en un laboratorio nuevo: actualización35→36 conserva las728definiciones completas, el inventario previo con cinco tipos/cables, auditoría, operaciones y paleta personal con su recibo. Repetir la migración no cambia datos. En una segunda base nueva, dos equipos genéricos de cuatro puertos por cada una de las siete familias prueban siete cables API y dos por Click-Click real. Se ejecutan24solicitudes cruzadas (22pares dirigidos únicos), rechazo422de ámbito por IDs, tipo desconocido, replay, conflicto412, rollback forzado de auditoría, lector403 y runtime sinDDL. Filtros/CSV devuelven ocho puertos por familia nueva y SVG conserva UUID y rótulos56/DD. Recarga, otra sesión y reinicio del proceso servidor conservan datos.

El primer ensayo falló antes del login porque el fixture no había concedido permisos al runtime de la base de actualización. El segundo completó migración/API y se detuvo al inspeccionar el SVG con un guion que esperaba un botón HTML. Ambos se conservan como FAIL; se corrigieron sólo los drivers y el tercero usa otro clúster/base. El clic final se ejecuta con eventos de ratón CDP sobre el rectángulo real del puerto. No se cambió producto ni se recompiló por esas correcciones. La candidata y la ejecución auxiliar tienen manifiestos separados. [Evidencia y revisión](../evidence/s1-20261101/conectores7/RESULTADOS.md).

VM, servicio/DB instalados, MFA y QA de Wascar permanecen intactos. No copiar DLL/SQL aislados al servidor. QA157 es planificada, no habilitada. Faltan perfiles H y los otros modelos elegidos, contratos de potencia/pasivos/montaje/almacenamiento, consumidores pendientes, distribución/Restore36 y paquete Windows completo con QA. Después: laboratorio de al menos50clientes. **Índice del cierre restante9,76/100 sin cambio; cobertura del catálogo no es porcentaje global.**
