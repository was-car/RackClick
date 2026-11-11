# Grupo54 · coordinador aislado, contexto de estado y PoE/cara

17.10.2026 · Windows · base `966e0cc`. Tres tandas pequeñas con archivos separados y revisión independiente. Desarrollo/ensayos acotados terminados; no candidata completa ni adopción. QA real conserva50/50/esquema4: sin actualizar, migrar ni operar por este bloque.

| Tanda / autor | Resultado | Límite |
|---|---|---|
|54-A · `copia_schema53`, Windows|Biblioteca53 ampliada4→5/6 con pins exactos; coordinador de perfil nuevo con lock, puntero atómico, readiness/app.js y recuperación4 condicionada a actividad|Sólo fixtures/clusters nuevos, caller exclusivo y URL temporal; falta adaptador/lifecycle/supervisor/puerto estable para QA real|
|54-B · `backend_audit50`, backend|Contexto transaccional de user.state.set/.cancel;006 aditiva para user/intendedTarget, conserva001–005 y DTO/rutas46/50|4/21acciones,17pendientes; sin GUI de contexto ni sesiones indirectas exhaustivas|
|54-C · `inventario_movimiento52`, QA|PoE OFF conserva watts/UUID/grupo/cable con typeRJ45PoE→RJ45 previsto; cara rear/front/auto/rear persistente y comparación exacta|Prueba código existente; no suministro eléctrico, presupuesto agregado, todos los conectores/presets, Dose/circuitos. QA27 preparado, no disponible|

[Coordinador y reproducción](../../../docs/COORDINADOR-QA-SCHEMA5-S1.md), [API/contexto de estado](../../../docs/API-ADMIN-AUDITORIA-ESTADO-CONTEXTO-S1.md), [guion QA27](../../../docs/QA-POE-CARA-WASCAR.md), [revisión distinta](revision/REVISION.md).

## Versiones y pruebas ejecutadas

Windows11 `10.0.26300`, SDK10.0.401, PostgreSQL17.11, Python3.12.3, Node24.21.0 y Edge155.0.4283.45. Sin instalaciones ni cambio de versiones fijadas. Un build C# WindowsRelease locked; frontend53 y CSS52 intactos, sin buildfrontend. Las herramientas/fuente de5 se copiaron antes de compilar6:14servidor/18frontend. Después se congeló6 en otro directorio nuevo:15/18. Ninguna copia contiene bases/cuentas de QA real.

| Ejecutor / alcance | Resultado real |
|---|---|
|Backend: `dotnet msbuild development/server/RackClick.sln -t:Restore,Build -p:Configuration=Release -p:RestoreLockedMode=true -p:RestoreSources=https://api.nuget.org/v3/index.json -m:1 -nr:false -v:minimal` con toolchain fijada|Único build correcto,0errores|
|Backend: `test_admin_audit_state_context.py --dll …/DLL54 --frontend …/copia53/frontend --baseline-dll …/copia53/server/RackClick.Server.dll --evidence …/backend/pg-final`|4/4 PASS35,667s|
|Windows: `test_qa_schema5_switch.py`, distribuciones/manifiestos4/6 explícitos, `--candidate-schema 6`; `windows/final-1`|Intento3:2correctos y1ERROR de arnés,156,484s; conservado, no PASS conjunto|
|Windows: mismo runner corregido, sólo `--case test_switch_1_selection_readiness_login_write_and_restart_1`; `windows/focal-1`|1/1 PASS44,002s global/33,375s de caso; otros2 no repetidos por autor|
|QA inventario: `test_inventory_poe_face_gui.py --dll …/copia52/server/RackClick.Server.dll --frontend …/copia53/frontend --output …/inventario/edge-pg-final`|Un grupo PASS27,641s; navegador6,641s|
|Revisor distinto: cuatro casos backend con DLL54/frontend53|4/4 PASS41,332s|
|Revisor distinto: tres casos corregidos del coordinador4→6|Única suite final conjunta corregida3/3 PASS147,260s; tres clusters nuevos, nueve bases|
|Revisor distinto: PoE/cara con pareja6/53|Un grupo PASS31,047s; navegador7,468s|
|Coordinador: nuevo gate de guía con contextos sintéticos|1/1 PASS0,001s, sin metadatosQAreal|
|Revisor distinto: `python -B -m unittest discover -s tools/tests -p test_qa_guide.py`|20/20 PASS0,259s|
|Coordinador: regeneración/check de ambas guías|4comandos0; objetos01–26 y JavaScript de notas/resultados intactos|
|Revisor distinto: fuentes/parejas/guías y capturas|54/54 comparaciones correctas;2PNG propios inspeccionados|

Los cierres de autores/revisor conservan líneas exactas, hashes, resultados y entorno. Cada arnés recibe DLL/frontend/manifest explícitos, genera secretos/fixtures nuevos y cierra sus recursos. Todos los finales correctos tienen entradas/distribuciones invariantes y procesos propios detenidos; el intento Windows con error también cerró sus tres Labs. No nuevo ensayo nativo5: compatibilidadAPI5/pins se contrasta estáticamente y las ejecuciones53 permanecen históricas.

## Correcciones y comprobaciones concretas

- **006 necesaria:**005 sólo permitía user/target o systemhaus/intendedTarget. La cancelación de estado necesita expresar user/intendedTarget sin afirmar una modificación.006 cambia exclusivamente ese CHECK mediante migración transaccional;001–005 conservan bytes/digests. Schema6 queda explícito y no altera SDK/PG/dependencias.
- Contexto se inserta junto a estado/sesiones/revisión/operation/evento antes del commit y después de replay. Desactivar revoca sesiones sólo en commit; reactivar requiere login nuevo. No-op aceptado captura r→r+1 como committed, cancelación captura r→r bajo lock con intención y objetivo inexistente permitido, sin lookup histórico inventado. Replay antiguo no rellena contexto ni repite revocación.46/50 sólo tienen puntos de regresión, no suites históricas completas nuevas.
- Pruebas backend:5→6 y repetición conservan historia/filas/contextos existentes; fallo en segundoALTER006 revierteDROP y registro de migración. Cuatro triggers(commit/cancel×ambas tablas) fuerzan503 y rollback de todas las tablas, incluidas sesiones/cuenta/revisión; reintento original tras retirar trigger confirma una sola vez.401/403/404/UUID/coherencia y GETsinDML; datos privados no se publican.
- **P3 de arnés, detectado por revisión:** caso1 enviaba /me.user(objeto) como X-RackClick-Actor; se corrigió sólo a /me.user.id. No error de producto ni cambio en biblioteca/coordinador/DLL. Intento3(2PASS/1ERROR) retenido; sólo caso1 repetido por autor. `correccion-harness.diff` y hashes distinguen ambas entradas. No atribuir al autor la suite3/3 corregida del revisor.
- Coordinador: referenciaXID única antes de servir, lockMSVCRT y comparación previa de puntero antes de os.replace; ready/app.js sin login. Fallos before_pointer/after_start restauran sólo selección4 compatible cuando inputs/historia/filas/actividad y parada son ciertos. Login/escritura o DMLcompensada(INSERT+DELETE+COMMIT) impiden rollback aunque filas iguales; incertidumbre→recovery_required, sin mover watermark ni sobrescribir ramas. Bloqueo global conservador de cluster; caller debe ser exclusivo. No certifica escritores externos/corte eléctrico ni reconcilia cambios posteriores.
- PoE/cara: cinco commitsGUI, proyectosAPI por etapa, nueve tablas exactas salvo poe/type/face del puerto objetivo; watts17.5, UUID/grupo y cable conservados. Lote con segundoUUIDdeotrogrupo revierte primerUPDATE; cara inválida422, lector/técnico sin edición403 y ámbito/crucecliente404 no dejan restos. Recarga/dos usuarios/reinicio sóloASP.NET. Watts actuales se consultan en tooltip; el campo para nuevo valor no es visor. PreparaciónSQL no se atribuye a altasGUI ni instala objetos en QAreal.
- Revisor `revision_filtros_gui44` distinto de los tres autores: cuatroPG de backend, tresPG de coordinador, unGUI PoE y20guía, con capturas/contraste de fuentes registrados en su informe. Sin builds, otras suites, QAreal o adopción. El coordinador principal verifica correspondencia/huellas/documentación, sin atribuirse esas ejecuciones.

## Disponibilidad y continuidad

Pareja de desarrollo congelada: DLL54 `919fb34cfb3cc5a030bab88130420479f774d077e7fe811ecee4900ab782c3ee`, schema6; JS53 `f7b33667f1b602849593a1b5b02fabef093374f556adc0250e54af1344bada3e`; CSS52 `50dd856718dd01b3e3356a9a08005df880c859a2652b68a670c167fa75567ec3`; servidor15/frontend18.006 SHA `7494e4e44073e198756ec4ae73b138ce6972aa885eb2d5281c915e52ecc37961`. Registrada como futura, no seleccionada en QA.

Catálogo27casos, anteriores01–26 idénticos y notas/resultados intactos. QA23/25/26/27 NO DISPONIBLES en ambos perfiles; QA24 sigue sólo restaurado50/50. Root sólo lee metadatos para generar/check guías; no credenciales/notas/exports/storage. Ningún HTTP/auth/SQL/start/stop/update/migración ni nueva observación de procesosQAreal. Último apagado observado50 histórico, sin revalidarlo aquí.

Próximo: adaptar fuente real4/lifecycle al coordinador6 y ensayar/revisar selección/recuperación con identidad/cuentas/origen conservados antes de habilitar23/25/26/27. No cambiar sólo DLL sobre otra versión de base como rollback. Faltan supervisor/puerto estable, preparación/operación real y política de sesiones restauradas; este bloque no entrega instalador ni candidata completa.

**53/100 estimado provisional; administración14/15.** Avances concretos: coordinador aislado con guardia de actividad,4/21capturas y trayectoria PoE/cara. Mantienen partes ya contabilizadas;17contextos+GUI, ficha/membresías, conexión por lotes/compensación y demás paridad, avisos, instalación/backup/manual/paquete/QA final siguen abiertos. Nada adoptado por el desarrollador.

`BASELINE.json`, `CANDIDATA6.json`, congelaciones de autores/revisor, `VERIFICACION.json`, `congelacion.json`, `cambios.diff.gz` y `SHA256SUMS` identifican contenido. Git local; nada publicado. Informes originales y fallidos se conservan como evidencia histórica.

Comprobación de whitespace del stage: excluye únicamente los dos diffs crudos `backend/backend-source.diff` y `revision/fuentes.diff`, conservando sus líneas de contexto en blanco y terminación original. Sus bytes/manifiestos no se alteran; el resto del stage pasa la comprobación.
