# Grupo52 · navegación, contexto de auditoría y movimiento

17.10.2026 · Windows · base `6e50a19`. Continuación autorizada en tres tareas pequeñas con propietarios separados. Código y pruebas de desarrollo terminados/revisados en este alcance; no candidata completa ni adopción. La pareja real de QA conserva50/50 y esquema4: no se ha actualizado ni migrado.

| Tanda / autor | Resultado concreto | Límite |
|---|---|---|
| 52-A · `preview_admin51`, frontend | Árbol real EN/DE/ES con12 destinos y foco a formularios/listas existentes; grupos se ocultan sin desmontarse, conservando borradores | Primera etapa; falta selección centralizada de usuario y vista completa propuesta51. QA23 preparado, no disponible en QA actual. |
| 52-B · `backend_audit50`, backend | Migración005 aditiva, captura transaccional de `user.create` y `.cancel`, nuevo GET de contexto tipado con autorización global |2/21 acciones con contexto nuevo; otras19 y GUI de contexto pendientes. Schema5 sólo en labs nuevos. |
| 52-C · `inventario_movimiento52`, QA | Recorrido GUI de movimiento/orden, cable local→cross,412, identidades/atributos exactos, dos usuarios y reinicio ASP.NET | Comprueba código existente; no prueba altas por GUI, drag/táctil, Dosen ni paridad completa. QA24 habilitado sólo en restaurado50/50. |

[Contrato de navegación](../../../docs/GUI-ADMIN-NAVEGACION-S1.md), [API de contexto](../../../docs/API-ADMIN-AUDITORIA-CONTEXTO-S1.md), [guion QA24](../../../docs/QA-MOVIMIENTO-ORDEN-WASCAR.md). Los formularios/adaptadores previos, Click-Click, RC9 adoptada, dependencias/versiones fijadas y SQL001–004 se conservan.005 agrega dos tablas; no backfill ni inferencias de revisiones desde operation. Revisión de cancelación es la observada bajo lock, sin incremento. Contexto, cuenta, revisión, operación y evento se confirman/revierten juntos; replay no añade contexto.

## Ejecuciones nuevas y versiones

Windows11 `10.0.26300`, SDK10.0.401, PostgreSQL17.11, Python3.12, Node24.21.0 y Edge155.0.4283.45. Cada arnés crea bases/clusters/perfiles nuevos con secretos privados locales y cierra sus procesos. Para trabajar en paralelo se copió la distribución50 completa a una carpeta `.local/candidates` nueva, sin datos/cuentas de QA; hashes13servidor/18frontend antes/después. Frontend/inventario usaron esa copia mientras backend compilaba schema5.

| Ejecutor | Comando / alcance | Resultado |
|---|---|---|
| Backend | `dotnet msbuild development/server/RackClick.sln -t:Restore,Build -p:Configuration=Release -p:RestoreLockedMode=true -p:RestoreSources=https://api.nuget.org/v3/index.json -m:1 -nr:false -v:minimal`, toolchain local | Build Windows correcto,0avisos/errores |
| Backend | `test_admin_audit_context.py --case test_context_create_cancel_replay_conflict_persistence --evidence …/backend/pg-create-focal` |1/1 focal,6,572s; anterior al argumento explícito de baseline |
| Backend | Mismo runner final sin filtro, `--baseline-dll …/copia50/server/RackClick.Server.dll --evidence …/backend/pg-final` |5/5 finales,49,553s |
| Frontend | Tres builds `npm --prefix development/frontend run build` con toolchain fijada | Correctos; los dos posteriores justificados por correcciones móviles |
| Frontend | `test_admin_navigation_gui.py --dll …/copia50/server/RackClick.Server.dll --frontend development/frontend/dist --output …/frontend/edge-pg-estabilizado` | Escenario completo17,625s; CSS anterior al margen móvil final |
| Frontend | Mismo runner con `--mobile-only --output …/frontend/edge-pg-movil-confirmado` | Focal final12,469s;12títulos y navegación debajo de cabecera fija, sin escritura |
| QA de inventario | `test_inventory_movement_gui.py --dll …/copia50/server/RackClick.Server.dll --frontend …/copia50/frontend --output …/inventario/edge-pg-final` | Un grupo19,297s; navegador6,969s |
| Revisor distinto | Runner contexto con sólo migración/recuperación y rollback, `--case` repetido |2/2 finales21,285s; no los otros3casos ni regresiones puntuales46/50 |
| Revisor distinto | Runner navegación completo con DLL52 y frontend52 finales | Un grupo18,094s; única ejecución completa sobre esa pareja final |
| Revisor distinto | Runner movimiento con la misma pareja52/52 | Un grupo20,938s; navegador7,266s |
| Coordinador | Dos pruebas nuevas de gates en `tools/tests/test_qa_guide.py` |2/2 focales0,020s |
| Revisor distinto | `python -B -m unittest discover -s tools/tests -p test_qa_guide.py` |17/17 finales0,227s |
| Coordinador / revisor | Regeneración/check de ambas guías / comparación de fuente, catálogo, guías y artefactos |4salidas0 /44comparaciones correctas |

La migración prueba4→5, repetición,1→5, fallo DDL sin parcial y recuperación de una copia4 a base NUEVA con DLL50. No es recuperación operativa de QA real. Las otras pruebas backend incluyen HTTP real de alta/cancelación, stale/replay, triggers sobre ambas tablas para rollback total, UUID/House/autoridad/caducidad durante espera PostgreSQL y redacción;46/50 sólo tienen regresiones puntuales dentro de un caso, no suites completas nuevas.

Navegación compara tablas públicas y HTTP sin escrituras al recorrer paneles; la creación explícita por UI hace un solo POST y persiste tras recarga/segunda sesión. El focal móvil sólo lee. Movimiento siembra por SQL2racks/3equipos/3grupos/6puertos/1cable, escribe movimiento/orden por GUI y compara las9tablas de inventario salvo ubicación/orden previstos. Conserva UUID/extremos/atributos;403lector/técnico fuera de edición y404lectura ajena no cambian inventario. Reinicio únicamente del servidor ASP.NET de fixture.

## Correcciones y revisión independiente

- Frontend: contención de formularios/selectores bajo `.rc-admin-panels` corrige overflow390 sin ocultar body ni recortar contenido. Margen móvil64px evita que cabecera fija48px cubra títulos. Fuente final probada por focal y por escenario completo del revisor.
- Fallos auxiliares frontend conservados: ruta inexistente del arnés, serialización de nodo CDP, espera inicial y espera de datos de listas. Los directorios con nombre `final` que fallaron no se presentan como PASS. El cierre propio detalla cada intento y versión.
- Inventario: primer intento falló sólo al comparar el orden de arrays del proyecto esperado frente al transporte. La comparación final normaliza por UUID conservando sortOrder y todos los atributos; el orden visible se comprueba además en DOM. No se modificó producto de inventario.
- Baseline50: argumento explícito permite otra ruta, conservando validación estricta de los13archivos. Metadata Git de la DLL50 y rutas deterministas hacen que compilar el mismo código no pruebe identidad binaria. Reconstrucción byteidéntica50 no ejecutada en52; limitación documentada, sin relajar hashes.
- Revisión por `revision_filtros_gui44`, distinto de los tres autores: [dictamen](revision/REVISION.md). Ejecutó exactamente2PG+2GUI+17guía,44comparaciones y revisó4capturas propias; no build, otros3PG, suites antiguas ni operaciones de QA real. El coordinador también inspeccionó las fuentes/diffs y coherencia del alcance, sin atribuirse esas ejecuciones.

## Disponibilidad, continuidad y siguiente grupo

Pareja de desarrollo revisada: DLL `2ebfc2c875a519e91a9338dab1762202f4dfa001834a4c80dcfc3c13dafd5f91`; JS `5d721e0abc3d283152c7919bd995884f4b1645fb41b0ef10269bdeac3462e40e`; CSS `50dd856718dd01b3e3356a9a08005df880c859a2652b68a670c167fa75567ec3`. Servidor14/frontend18 archivos. Está registrada como pareja futura; no seleccionada en QA.

QA23 de navegación permanece NO DISPONIBLE en ambas guías. QA24 de movimiento está DISPONIBLE sólo en restaurado50/50 por código ya probado; también reconoce la pareja52 cuando se seleccione en el futuro. Casos01–22, huellas/disponibilidad y código de notas/resultados se conservan. Las guías se regeneraron desde metadatos locales; no se abrieron notas/exportaciones/credenciales. Sin HTTP/auth/SQL/start/stop en QA real; no nueva comprobación de sus procesos: su último estado observado en50 era apagado. Primer arranque/QA manual de50 aún no se convierte en prueba nueva por estos labs.

Una futura selección schema5 necesita copia/recuperación nueva, permisos runtime y procedimiento compatible. No volver a DLL50 sobre schema5 sustituyendo sólo archivos. Se conserva la instancia real y su recuperación anterior. `BASELINE.json`, congelaciones por autor, `VERIFICACION.json`, `cambios.diff.gz` y `SHA256SUMS` identifican el contenido; informes originales se mantienen como históricos.

**53/100 estimado provisional; administración14/15.** Hitos concretos:12enlaces reales,2/21capturas mínimas y movimiento/orden comprobados. Quedan selección centralizada/ficha administrativa,19capturas y GUI de contexto, duplicación/PoE-cara y resto de matriz/paridad, avisos multiusuario, instalación Windows/backup/manual/paquete/QA final. Próxima terna propuesta: selección administrativa acotada, siguiente familia de captura y recorrido de duplicación; preparar recuperación/selección schema5 antes de anunciar disponible la navegación. No aumento automático por contar tandas o pruebas.

Comprobación de whitespace del stage: se excluyen únicamente `backend/backend-source.diff` y `revision/producto.diff`, que conservan cuatro líneas de contexto en blanco del diff original. No se alteraron sus bytes ni los manifiestos del autor/revisor; el resto del stage pasa la comprobación.
