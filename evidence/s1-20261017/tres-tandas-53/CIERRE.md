# Grupo53 · selección de usuario, copia recuperable y duplicación

17.10.2026 · Windows · base `a4b3f45`. Tres tareas pequeñas con propietarios separados y revisión por otra persona. Desarrollo acotado terminado; no candidata completa ni adopción. QA real conserva50/50/esquema4; no actualizado ni migrado por este bloque.

| Tanda / propietario | Resultado | Límite |
|---|---|---|
|53-A · `preview_admin51`, frontend|Usuario seleccionado por ID dirige Estado/Contraseña/Sesiones/Permisos efectivos; destino visible y bloqueo por borrador/contraseña/pending/sesión, con journals originales recuperables|No ficha completa ni membresías centralizadas; QA25 preparado, no disponible|
|53-B · `copia_schema53`, Windows|Biblioteca nueva de preparación4→5 y recuperación4: dump y dos bases NUEVAS, identidad/secretos PG nuevos, filas/cuentas/sesiones/historia exactas y runtime005 comprobado|Sólo fixtures recién creados; no adaptador/coordinador/switch real ni instalación/recuperación operativas|
|53-C · `inventario_movimiento52`, QA|Duplicación GUI remapea rack/equipos/grupos/puertos/cable interno, conserva fuente/externos/atributos; gn repetido, rechazos atómicos, permisos y persistencia|Código de inventario existente; SQL prepara fixture, no altas por GUI ni objetos en QA real. QA26 preparado, no disponible|

[Selección y guion](../../../docs/GUI-ADMIN-SELECCION-S1.md), [copia/recuperación y reproducción](../../../docs/RECUPERACION-SCHEMA5-LAB-S1.md), [duplicación y preparación manual](../../../docs/QA-DUPLICACION-RACK-WASCAR.md), [revisión distinta](revision/REVISION.md).

## Versiones y ejecuciones reales

Windows11 `10.0.26300`, SDK10.0.401, PostgreSQL17.11, Python3.12.3, Node24.21.0 y Edge155.0.4283.45. No instalaciones ni versiones cambiadas. No nuevo build C#/SQL. Se copió la distribución52 completa a carpeta nueva `.local/candidates`, sin base/cuentas, contrastando14servidor/18frontend. Se conserva la copia50 inmutable13/18.

| Ejecutor | Comando / alcance | Resultado |
|---|---|---|
|Frontend|Dos builds `npm --prefix development/frontend run build` con toolchain fijada|Correctos; segundo justificado por texto EN/DE/ES de ayuda|
|Frontend|`test_admin_user_selection_gui.py --dll …/copia52/server/RackClick.Server.dll --frontend development/frontend/dist --output …/frontend/edge-pg-final`|Un escenario PASS17,875s; producto final, arnés anterior a una línea posterior de scroll para captura|
|Windows|`test_qa_schema5_copy.py` con distribuciones y manifiestos completos50/52 explícitos; sólo caso1|1/1 focal33,188s,3bases nuevas|
|Windows|Mismo runner final, tres casos; comando exacto `windows/RUNS.json`|3/3 PASS75,075s,7bases nuevas en su cluster propio|
|QA inventario|`test_inventory_duplicate_gui.py --dll …/copia52/server/RackClick.Server.dll --frontend …/copia52/frontend --output …/inventario/edge-pg-final`|Un grupo PASS33,235s; navegador6,109s|
|Revisor distinto|Tres casos de copia/recuperación con distribuciones inmutables50/52|3/3 PASS70,676s|
|Revisor distinto|Selección GUI, arnés final y pareja DLL52/frontend53|Un escenario PASS18,219s|
|Revisor distinto|Duplicación GUI con la misma pareja final52/53|Un grupo PASS33,141s; navegador6,625s|
|Coordinador|Dos negativos de gates de guía con contextos sintéticos|2/2 PASS0,002s; observado antes de ajustes de listas/EOL, sin repetir para generar log|
|Revisor distinto|`python -B -m unittest discover -s tools/tests -p test_qa_guide.py`|19/19 PASS0,199s|
|Coordinador / revisor|Regeneración/check de guías / comparación de fuentes, versiones, catálogo, capturas|4comandos0 /48comparaciones correctas y3PNG propios inspeccionados|

Los runners crean y cierran clusters/bases/perfiles propios; no usan QA real ni `DEFAULT_DLL` mutable. Todos los finales citados registran entradas intactas y procesos de fixture cerrados. El focal Windows y caso1 de final se distinguen; no se suman como cobertura distinta. No suites históricas completas nuevas.

Selección ejercita lectura403, tres journals sintéticos con targets distintos, consultas/cancelaciones originales, bloqueos/desbloqueos explícitos, nombres/IDs/ENDEES, propio/inactivo, retiro de resultados anteriores, un único state.set al usuario B y lectura tras recarga. Las tres cancelaciones y ese POST de estado son intencionales; no afirmar cero escrituras del escenario. La prueba no certifica lista vacía/eliminación de cuentas, red o respuestas tardías artificiales.

Copia valida todas las tablas/filas previas e historia001–004,005 exacta y vacía sin backfill, identidades/secretos nuevos, fuente/recuperación/dump/artefactos intactos, cookies/login/proyecto/sesiones en5 y recuperación4, DDL runtime denegado y alta/contexto con runtime005. Los negativos rechazan entradas/historia/archive/output incompatibles sin sobrescribir destino; INSERT005 realmente revocado impide `prepared` y conserva copias/journal. Exclusividad la aporta el dueño del fixture: snapshots no certifican guardia operativa de actividad ni recuperación tras escrituras posteriores. Se restauran dos bases en el mismo cluster sintético; no se prueba otro equipo/cluster.

Duplicación compara9tablas y proyecto por UUID/atributos, nuevas identidades y sólo cable interno remapeado. Fuente/cable externo no cambian. Cuatro409 de reserved sin/incorrecta confirmación y disabled/faulty,403/404 y rack ajeno bajo otro cliente no dejan restos de inventario/revisión/operation/audit. Recarga/dos usuarios y reinicio sólo ASP.NET persisten. No varianteGUI sin cables ni confirmación positiva reserved conectado, Dosen, arrastre/táctil o reinicioWindows/PostgreSQL.

## Correcciones y evidencia preservada

- Intento frontend inicial FAIL30,421s: SQL del fixture insertaba nombres con mayúsculas, mientras login normaliza a minúsculas. Corregidos sólo los nombres sintéticos del arnés; no política de producto/D-007. Intento fallido y salida conservados.
- P3 de ayuda: texto52 decía selecciones independientes en todos los paneles. Corregido EN/DE/ES antes del segundo build y focal final; grupos/alta siguen independientes.
- Después del PASS propio sólo cambió una línea de desplazamiento del arnés para encuadrar el selector móvil. No producto/build. La revisión ejecutó ese arnés final; su captura móvil útil/legible no se atribuye al autor.
- Windows e inventario no requirieron correcciones de producto en esta tanda. Informes/manifiestos históricos no se reescriben ni se presentan como vigentes de fuentes53.
- `revision_filtros_gui44` es distinto de los tres autores:3PG+2GUI+19guía+48comprobaciones/3PNG. No builds, suites anteriores ni lectura/operación de QA real. El coordinador revisó contratos/diffs y correspondencia de resultados, sin atribuirse esas ejecuciones.

## Disponibilidad y siguiente grupo

Pareja de desarrollo: DLL52 `2ebfc2c875a519e91a9338dab1762202f4dfa001834a4c80dcfc3c13dafd5f91`, JS53 `f7b33667f1b602849593a1b5b02fabef093374f556adc0250e54af1344bada3e`, CSS52 `50dd856718dd01b3e3356a9a08005df880c859a2652b68a670c167fa75567ec3`, schema5, árboles14/18. Sólo registrada como futura, no seleccionada en QA.

Guías26casos regeneradas/check desde metadatos locales. QA23/25/26 NO DISPONIBLES en ambos perfiles; QA24 conserva disponibilidad sólo restaurado50/50. Se adaptan únicamente pasos15–18/23 para selector común cuando aparezca, conservando alternativa50; otros objetos anteriores idénticos. Código de notas/resultados intacto: no se abrieron ni reemplazaron observaciones/exportaciones/credenciales privadas. El cambio de huella de esos cinco guiones conserva resultados previos y avisa del cambio de instrucciones.

Sin HTTP/auth/SQL/start/stop/update/migración de QA real; no nueva comprobación de sus procesos. El último apagado observado50 sigue histórico. Antes de ofrecer navegación/selección53 debe integrarse el coordinador4→5, su exclusión/guardia de actividad y recuperación compatible en fixtures, revisar/ensayar switch con pareja exacta y sólo después seleccionar copia nueva en restaurado. No sustituir DLL50 sobre schema5 como rollback. Origen/cuentas/observaciones se conservan.

**53/100 estimado provisional; administración14/15.** Hitos: cuatro paneles con selección común segura, preparación/recovery aisladas y duplicación íntegra. No se aumenta por pruebas del mismo alcance parcial. Próxima terna: coordinador4→5 en fixtures, siguiente familia de contexto administrativo y PoE OFF/cara persistente. Ficha/membresías,19contextos+GUI, avisos, paridad restante, servicio/HTTPS/instalación, backup/manual/paquete/QA final continúan pendientes.

`BASELINE.json`, congelaciones de autores/revisor, `VERIFICACION.json`, `congelacion.json`, `cambios.diff.gz` y `SHA256SUMS` identifican fuentes/resultados. Git local; nada publicado.
