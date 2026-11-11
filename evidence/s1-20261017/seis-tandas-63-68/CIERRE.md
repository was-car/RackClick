# Seis tandas63–68 · cierre revisado

17.10.2026. Base6db4312cc328cd5825748b37637d96809f928409; trabajo autorizado S1, seis tandas pequeñas. Implementación y revisión independiente separadas. No instalaciones, publicación, versiones/dependencias/SQL001–007 nuevas ni adopción.

## Qué quedó hecho

| Tanda | Resultado verificable |
|---|---|
|63|Contrato de primera compensación propia de último ports.update: status/label/color/face, revisión estricta, filas completas y valores inversos por puerto; sin SQL008/snapshot global/undo general.|
|64|Relaciones readonly por tipo/UUID: grupo de usuarios→miembros/concesiones; grupo de clientes→clientes/grupos usuarios con concesiones explícitas. Múltiples padres, nombres literales y borradores conservados; no herencia AD ni cálculo nuevo de permisos efectivos.|
|65|Resumen PoE por equipo/snapshot/rack: conocidos/desconocidos, null≠0, presupuesto/exceso, OFF/AC excluidos. disabled/faulty cuentan si PoE ON según RC9. Comparación decimal exacta y camposHTML decimales; ningún aviso impide guardar ni certifica suministro.|
|66|operations.compensate API: original propio/house/cliente/auditoría coherentes, sólo último commit del cliente y filas actuales JSONBexactas; inversión por fila heterogénea. Nueva revisión/audit/operación atómicos; permisos/sesión revalidados antes commit; replay/cancel/rollback/concurrencia.|
|67|Deshacer último cambio de puertos en GUI RC9, alcance por UUID/grupo explícito, metadata antes retirar journal, respuesta perdida recuperable, conflicto sin renovar elegibilidad. Acción28 de avisos integrada sin perder borradores/Click-Click.|
|68|Transición cerrada62→68 sobre motor7 existente, mismaSQL7/base/puntero/URL/cuentas, pareja previa retenida y procesos propios apagados.|

Contratos/guiones: [compensación](../../../docs/API-COMPENSACION-PUERTOS-S1.md), [GUI/QA36](../../../docs/GUI-COMPENSACION-PUERTOS-S1.md), [relaciones/QA34](../../../docs/GUI-RELACIONES-GRUPOS-S1.md), [PoE/QA35](../../../docs/GUI-PRESUPUESTO-POE-S1.md), [actualizador68](../../../docs/ACTUALIZACION-ARTEFACTOS7-68-S1.md).

## Pruebas nuevas Windows y fallos conservados

- Backend66: un build Release locked9,07s,0warnings/errores. PG01:5PASS y1FAIL415 por falta Content-Type en el rawJSON del arnés,51,815s suite; PG02 repite sólo afectado17,015s PASS con misma DLL. Agregado finalcinco focos propios y una regresión, no seisPASS en primera corrida. Incluye heterogeneidad/null/Unicode/cuatrocampos, revisión/ABA/filatamper, permisos/sesiones esperando locks reales y expiración precommit, claves/replay/cancel, falloauditrollback y concurrencia única. [Informe](backend66/CIERRE.md).
- Relaciones64: coordinador ejecutó arnés preparado por frontend,22,047s PASS; snapshot readonly,403simulado en fixture, EN/DE/ES390/Tab y borrador. La autoría de pruebas no se presenta como una ejecución del agente que las preparó.
- PoE65: primeras5unidades correctas; reproducción decimal nueva1PASS/2FAIL, focal corregido3/3 y final8/8PASS. Primer nativo15,797s FAIL por selector idioma en inventario; autor corrigió sólo guion a inicio→idioma→cliente y nativo02 PASS24,125s. Campos0.1/0.3 cancelados sin escritura, total/OFF/AC/unknown/lector/dos sesiones, SQL9exacto salvo cambios previstos y reinicio ASP.NET. Tres PNG reales inspeccionados. [Informe](poe65/CIERRE.md).
- GUI67: tres builds reales preservados(pre-stepHTML, pre-fence de aviso atrasado, final), no se llama único al build final. Primera pareja combinada CANDIDATA68 quedó histórica antes de ejecutar nativos; sólo FINAL02 se usó. Guion nativo01/02/03 falló por selector idioma, texto del botón y Actualizar ambiguo; producto intacto, evidencias conservadas. Nativo04 PASS23,782s; regresión recuperación existente PASS19,265s;51unidades autor correctas. Cuatro campos/gn duplicado, pérdida original+recarga/replay y pérdida compensación/replay,412→carga→409local sin sobrescritura, lector/404 y persistencia. [Informe](frontend67/CIERRE.md).
- Windows68 coordinador:7contratos prepin PASS1,210s, un nativo final73,554s correcto en una fuente62 nueva/versionada. Lock rechazado, PGexterno retenido hasta limpieza explícita por fixture, snapshot/historia/OID/privados/puntero exactos, tres camposconfig y escritura/reinicio sólofixture. No repite transiciones históricas ni instala servicios.
- Revisión distinta:2PG11,231s; tresGUI23,031/25,046/26,422s; Windows69,245s;59unidades220,9331ms y25guía0,356s. Artefactos/entradas intactos y fixtures apagados; no builds ni modificación de producto. [Informe independiente](revision/REVISION-FINAL02.md).

Los arneses crean bases/usuarios/secretos locales nuevos. Ninguna escritura técnica sobre datos de Wascar. Los logs históricos no son ejecuciones nuevas. Correcciones de arnés sólo repiten el foco afectado; no se maquillan fallos como PASS.

## Límites revisados del primer Deshacer

Sólo cuatro campos del último ports.update propio: cualquier commit posterior del cliente, incluso de otro objeto, bloquea por revisión. No deshace PoE/watts/propiedades/movimientos/borrados ni ofrece redo. El servidor deriva todos los valores de su auditoría, compara filas completas y autoriza lectura/escritura; no acepta before/after de UI.

D-068-01: con candidato en memoria, equipo/changedIds se comparan exactamente antes de retirar journal. Tras recarga no existe candidato durable: se valida origen/request/cliente/revisión/UUID/forma y se carga snapshot autorizado; no se promete aquella comparación exacta inexistente. Servidor sigue comprobando cada fila. D-068-02: abrir el propio diálogo consume candidato; Cancelar no escribe ni repone el botón. QA36 confirma sin Cancelar o explica preparación de otro cambio. Mejora de reapertura pendiente, no se ocultó con una promesa de guion. [Decisión1](D-068-01.json), [decisión2](D-068-02.json).

## QA real y disponibilidad

Manifiesto actual [CANDIDATA68-FINAL02.json](CANDIDATA68-FINAL02.json) SHA8ad1b29ff15126e8401278529108e437f944b6cb7730a737846c864d8e2c6aaa. Servidor16/frontal18, DLL85e80f4d…3c6e4, JSc4c044c6…e9108, CSS50dd8567…67ec3 inalterado. SQL001–007 idénticos62. La primera candidata y sus fuentes anteriores se explican en CANDIDATAS.json; no sobrescribir su evidencia.

TrasGO técnico, único operador revisado326180e04eed6c3e37d6bf1cc5457788bb1b32c5b15d7c571ce0af5531f7de07: CLI0/wrapper0,33,072s y16/16checks. [OPERACION-REAL.json](OPERACION-REAL.json): base/roles/privados/puntero/URLhttp://127.0.0.1:52346 iguales, sóloartifactDirectory/dllSha256/bundleSha256 cambiaron;62retenida, nueva68completa y apagado. Comparados36archivosQAoriginal y8privados porhash;0login/DML de aplicación/migraciones/restore. Sólo lecturas de control y procesos propios del helper.

Una observación pasiva independiente posterior15/15correcta: [post68-passive.json](revision/post68-passive.json),0SQL/HTTP/auth/start/stop y sin leer credenciales/notas/resultados/journals. No repite identidad/snapshotSQL ni se atribuye las36/8comparaciones del coordinador.

Guía restaurada36casos disponibles; original8disponibles y casos34–36pendientes allí. Los33objetos de casos anteriores, lógica de notas y copias import/export conservados; ninguna nota/resultado personal leído o sobrescrito. QA34relaciones,QA35PoE,QA36compensación con pasos exactos, ubicaciones y cuenta/ámbito nuevos. INICIAR-QA-RESTAURADO.cmd mantieneURL/cuentas privadas. Disponible no significa Pass ni adopción por Wascar.

## Progreso y siguiente trabajo

**60/100 provisional, desde58:** mismos pesos20/25/15/15/15/10, aportes18/19/14/5/3/1. Inventario18→19 por primera compensación propia nueva API+GUI; paridad4→5 por resumenPoE antes ausente. Administración14/15; contrato, documentos, número de pruebas y registro Windows no suman de nuevo. [Criterio](PROGRESO-CRITERIO.json). No mide calendario/créditos/porcentaje de QA aprobada.

Pendientes: ampliar compensación/redo y mejorar Cancelar, definir terminales/pasos internos Dose sin inventar rutas, combinaciones de conectores/alimentación, experiencia administrativa integral, plantillas/búsqueda/informes/exportes, paridad EN/DE/ES/accesibilidad, instalador Windows limpio/servicio/HTTPS, backup/recuperación en otro equipo, manual/paquete reproducible y QA/adopción final de Wascar. No candidata de servidor final. Fuentes/diff/verificación/SHA256SUMS actuales de este bloque separados de manifiestos e informes históricos; no se fabrica aquí ZIP de instalación final.
