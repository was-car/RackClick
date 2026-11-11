# Cierre533–592 · 60 hitos internos · 18.10.2026

**Resultado: 60/60 hitos, avance global estimado78/100 (antes77).** Biblioteca compartida por cliente implementada y probada en laboratorios nuevos. Una plantilla privada propia se publica como otra identidad inmutable; otros técnicos autorizados pueden crear equipos desde ella. Retirar la publicación impide usos nuevos y conserva originales/equipos. Permiso específico `templates.publish` por grupos y ámbitos existentes, distinto de editar inventario. No publicación externa ni acceso a privadas ajenas.

**Disponibilidad real:** candidata592 de desarrollo, esquema10. El QA restaurado y los ZIP532 permanecen en esquema9 y sin cambios. La guía contiene71casos:68disponibles en restaurado y8en original; QA69–71 nuevos quedan NO DISPONIBLES. Ningún resultado de Wascar reemplazado ni Pass manual asignado. Falta integrar y verificar esquema10 en operadores, paquete y QA antes de ofrecer este módulo a Wascar.

## Cambios y prueba asociada

| Área / archivos principales | Resultado comprobado |
|---|---|
| SQL010, SchemaMigrations, Infrastructure/Capabilities | Tres tablas compartidas nuevas, revisión por cliente y capacidad específica. SQL001–009 exactas. Migración9→10 conserva30tablas y sus filas/historia; no concede permisos automáticamente. Admin histórico concede la nueva capacidad mediante API después de migrar. Backendfoco08. |
| SharedDeviceTemplates, puente privado ForPublication, Program/OpenAPI | Copia del TEXTUTF8/hash exactos, DTO cerrados, Unicode100, límites128activas/revisión máxima, recibos/estado/fence por actor, cliente y clave. Read+publish sin edit; autoridad vigente tras espera. Sin UUID privado o blueprint en respuesta/auditoría pública. Backend01/02/03/06/07 y revisiónPG propia01/02. |
| InventorySharedTemplateDevices y extracción mínima común privada; InventoryStore/Changes/Details | Comando singular `device.createFromSharedTemplate`, read+edit sin publish. Tres tipos, UUID nuevos, grupos/GN explícitos, free/wattsNULL/sin cables ni propiedades heredadas. Retirada/creación concurrentes, recibo, rollback, reinicio/segunda sesión y avisos. Backend04/05 y Edge. |
| Adaptador/diario/diálogo shared, InventoryPanel/inventory-api | Catálogo RC9, publicación explícita desde propia, preview, retirada y uso con destino/nombre nuevos. Intención compacta sin blueprint, retry/status/fence, misma cuenta/generación/abort. Borradores y Click-Click preservados. Node y Edge multiactor. |
| admin-grants/admin-audit, AdminGroups/GroupRelations/EffectivePermissions | Décima capacidad admitida por whitelists/catálogo y etiquetas EN/DE/ES. Guardias administrativas continúan basadas en security.manage; no se exige publish a administradores históricos. Node y migración08. |
| client-changes/client-change-details/ClientChangeNotice | Nueva acción reconocida por ambos lectores y textos de avisos. P2 encontrado independientemente, corregido y reproducido en Node y EdgeFINAL02. |
| RecoveryAdministrator | RequiredSchemaVersion9→10 y comentario correspondiente. Rechaza base9 antes de Apply, sin migrarla por efecto lateral. Cambio autorizado al asignar backend, omitido en lista inicial de mutables: registrado en ALCANCE-RECOVERY-10.json, sin reescribirINICIO. No se afirma recuperación operativa completa10 ni CLIpositiva10 probada. |

Propiedad exacta, símbolos, comandos y límites: [backend](backend/RESULTADO-BACKEND.md), [frontend](frontend/RESULTADO-FRONTEND.md), [contrato](../../../docs/API-PLANTILLAS-COMPARTIDAS-S1.md), [plan60](../../../docs/PLAN-SESENTA-TANDAS-533-592.json).

## Ejecuciones nuevas y atribución

Windows11 build26300, Python3.12.3, SDK10.0.401, runtime10.0.12, PostgreSQL17.11 EDB4, Node24.21.0/esbuild0.25.10 y Edge155. Herramientas existentes verificadas; ninguna versión fijada cambiada. Git inicial limpio `cc61892f88dbd7cb0d0301c222f40a6f1a80de94`. Laboratorios/clústeres/bases/secretos nuevos; no conexiones a la aplicación QA ni a sus datos.

| Ejecutor / evidencia exacta | Ejecución y límite |
|---|---|
| Backend, backend/build01.log | Una publicación Release PASS; raw20archivos incluye web.config generado, preservado. |
| Backend, backend/postgres01/result.json | **8/8PASS**,73.122s de tests/86.078s total, candidata592 inicial. Todas las fuentes, distribuciones y baseline532 intactas; servidores/lab apagados. Sin fallos ni repeticiones en estos8focos. |
| Frontend, frontend/NODE-03.log | **124/124PASS**, regresión pertinente antes de los dos P2 independientes; no se presenta como ejecutada sobre fuenteFINAL02. |
| Frontend, frontend/NODE-04.log y NODE-05.log | **12/12PASS cada foco** de adaptador/diario/administración/generaciones. Son repeticiones pertinentes, no24casos únicos. |
| Frontend, frontend/NODE-FEED-06.log | **100/100PASS** después de corregir el feed. No sumar esta repetición como100casos únicos adicionales a124. |
| Frontend, frontend/gui02/fixture.json | **PASS29.547s**, Edge14.219s, candidata592 inicial. Publicaciones, byteexactitud, técnico/lector/publicador sin edit, tres tipos, retiro, respuesta perdida/replay/recarga/fence, permisos, idiomas390px/teclado y persistencia. |
| Frontend, frontend/gui-notice03/fixture.json | **PASS24.609s**, Edge11.0s, FINAL02. Sólo foco afectado: creación compartida ajena produce aviso v1/descriptivo real, nombres/grupos y traducción; borrador/Click-Click intactos, sin recarga automática ni escritura fantasma; refresco explícito y reinicio. |
| Revisor, revision/pg-own01/result.json | **2/2PASS**,18.796s de tests/27.094s total, candidata inicial. Propios: bytes legacy con whitespace/decimal/Unicode, permisos por unión de grupos/grupos de clientes, publisher sin edit, privacidad, retiro/replay/fence/rollback/reinicio; revocación403 y caducidad401 durante última espera privada sin definición/recibo/audit. Sin GUI ni migración repetida por revisor. |
| Revisor, revision/node-hook02.log y node-notices02.log | Focos propios correctivos **1/1 y2/2PASS**. Versiones fallidas node-hook01/node-notices01 conservadas como0/1 y0/2, sin reclasificación. |
| Coordinador, native-backup02/result.json | **1/1PASS26.765s**. Operadores nativosPS5.1 genéricos New/RestoreDatabaseBackup sobre datos10;33tablas y todas sus filas exactas, dos publicaciones/una retirada, privada/definición/recibos/sesión copiada conservados. Otra base y otro propietario, entornoPG envenenado aislado, rechazo de destino existente sin alterarlo, origen exacto, procesos propios apagados. Aplicación de la restaurada NO iniciada; sesiones copiadas NO usadas. No instalación Windows ni recuperación de aplicación/paquete10. Atribución al manifiesto inicial, servidor idéntico al final. |
| Coordinador, legacy-private01/result.json | **1/1PASS**,5.722s de prueba/13.672s total, FINAL02. Método privado histórico05 ejecutado NUEVO sobre otra base; wrapper afirma esquema10 observado sin reutilizar el writer histórico etiquetado9. Comprueba tres tipos, reset/IDs/grupos/PoE, replay tras retirar fuente, permisos y avisos. Justificado por extraer el helper común de instanciación; no suite completa. Inputs y procesos propios intactos/detenidos. |
| Coordinador, QA-TESTS-01.json | **39PASS** de metadata (35guía+2históricos532+2nuevos592). Resultado registrado desde las salidas reales de herramientas; sin repetir para fabricar un log, sinPG/GUI/manualQA. |

## Hallazgos, correcciones y fallos conservados

1. **P2, contexto de publicación:** después de guardar el journal, el hook podía enviar unPOST de clienteA aunque la generación ya hubiera cambiado. Revisor lo reprodujo con foco propio0/1; implementador añadió corte antes del envío conservando intención durable y estado de otra generación. Foco propio correctivo1/1PASS antes del primer build.
2. **P2, avisos:** faltaba la nueva acción en lectores v1/descriptivo y etiquetas. Una página con creación compartida quedaba response_invalid. Revisor reprodujo0/2; implementador corrigió tres fuentes. Foco propio2/2PASS y100regresiones afectadasPASS. Requirió segundo buildfrontend; servidor no cambió. FocoEdgeFINAL02PASS sin repetir GUI completa.
3. **Node inicial:** NODE-01 importó helper no exportado;17administrativosPASS, suite nueva no pudo importar. NODE-02 produjo9PASS/1FAIL al leer data.customerId antes de tenerdata. Correcciones del implementador y fuentes/logs conservados; Node03/04/05 posteriores correctos.
4. **GUI01:**42.593s, pasos funcionales completados y fallo al final en Escape por eventoCDP incompleto/pestaña no enfocada. Arnés original preservado; sólo se corrigió bringToFront/código27. GUI02 completaPASS en otra fixture, mismo producto inicial; no se presentaGUI01 comoPASS.
5. **Backup01:**10.781s, AttributeError del arnés al usar actor_id sin resolverlo desde `/me`; Client.login sólo establece sesión/CSRF. No llegó a ejecutar POST ni backup. Fuente ejecutada en native-backup01/HARNESS.py, resultado/log/INCIDENT conservados. Se añadió GET/me; único método acoplado repetido en otra fixture como backup02PASS. No build/cambio de producto por este error.
6. **Registro inicial de guardias:** RecoveryAdministrator estaba asignado al backend desde el encargo, pero no figuró en authorizedMutableGuards. ALCANCE-RECOVERY-10.json registra autorización, diff de dos líneas y prueba negativaCLI9. INICIO permanece intacto. Al cierre hay204guardias inmutables y5mutables autorizadas; no205.
7. Algunas escrituras normalizaron finales de línea mixtos en fuentes existentes. El diff semántico sin EOL es acotado; se conservan los bytes realmente compilados/probados, sin normalizarlos después del freeze.

Los P2 se corrigieron por el implementador; el revisor no editó producto. Las pruebas históricas no se convierten en ejecuciones nuevas. No hay P1/P2 abierto dentro del alcance al cerrar.

## Identidad de artefactos y reproducción

FINAL02: [CANDIDATA592-FINAL02.json](CANDIDATA592-FINAL02.json), SHA256 **66426b3c4fdf8c75b8c1faae4572066754934000eb2567881d93407f4ae5e9f9**.37archivos,6.939.574B:19servidor+18frontend.157fuentes de producto en SOURCE-FREEZE-APP-02.json; pruebas congeladas aparte en SOURCE-FREEZE-TESTS-02.json para que una corrección de arnés no obligue a reconstruir producto intacto.

Primera candidata: CANDIDATA592.json, SHA2568bdc15638ed5fb0446e4575d5b9fd0c6cdc215986df1b546ef9fba0b2f1daa90;37archivos/6.939.310B. Todos los19archivos del servidor son idénticos en ambas; sólo frontend/app.js cambia. DLL0bf15fbac4083ef4e35d4a75222e3467b5bdcc35326d54a9901f385b480b7f23. No C# recompilado para el arreglo de avisos. Baseline532, SQL001–009, pins/dependencias, CSS/17assets y RC9adoptada intactos.

Los comandos ejecutados están en los informes de backend/frontend y en los arneses. Para repetir usar SIEMPRE un directorio de evidencia NUEVO y los artefactos explícitos; no sobrescribir las ejecuciones conservadas:

```powershell
C:/Python312/python.exe -X utf8 -B development/server/tests/test_shared_device_templates.py --help
C:/Python312/python.exe -X utf8 -B development/server/tests/test_shared_templates_gui.py --help
C:/Python312/python.exe -X utf8 -B development/server/tests/test_shared_template_notice_gui.py --help
C:/Python312/python.exe -X utf8 -B development/server/tests/test_shared_templates_backup592.py --manifest evidence/s1-20261018/sesenta-tandas-533-592/CANDIDATA592-FINAL02.json --output evidence/repeticion-nueva-backup592
C:/Python312/python.exe -B tools/windows/qa_guide.py --profile manual --check
C:/Python312/python.exe -B tools/windows/qa_guide.py --profile rc9 --check
```

No hay ZIP592 construido ni selección de QA10. Los operadores cerrados9 y el ZIP532 mantienen su alcance real. No usar nuevaGUI592 con servidor9 ni nuevaDLL10 contra la baseQA9. La siguiente integración debe ensayar migración/recuperación/paquete y matriz de disponibilidad antes de una selección compatible; no promete rollback tras actividad.

## Progreso y siguiente paso

78/100 provisional: fundamento18/20, inventario22/25, administración14/15, paridad14/15, Windows9/15 y QA/adopción1/10. Sólo inventario aumenta1 por biblioteca publicada multiusuario antes ausente, con permiso y ámbito separados e instanciación probada. No puntos por60IDs, tests, cambioSQL o backup genérico. S-26 tiene compartición implementada en desarrollo, pero falta integración/QA y no se adopta por el desarrollador.

Próximo: integrar esquema10 de forma probada en paquete/operadores/QA; completar preferencias/herramientas/formatosDosen/undo/admin y demás paridad restante; servicioSCM/identidad mínima/arranqueWindows, PKIproductiva/DNS/renovación, Windowslimpio/otro equipo/CRT elevado, licencias, recuperación integralhost/retención/manualfinal y QA/adopción de Wascar. No estimación de fecha o créditos.

[Revisión independiente](revision/REVISION-INDEPENDIENTE.md), METADATOS-FINALES.json y SEAL-REVISION.json detallan pruebas propias y observaciones de ejecuciones ajenas. VERIFICACION-FINAL.json/diff/SHA256SUMS sellan este bloque tras estabilizar guías y continuidad. Los informes R0 y todos los cierres anteriores permanecen históricos e intactos.
