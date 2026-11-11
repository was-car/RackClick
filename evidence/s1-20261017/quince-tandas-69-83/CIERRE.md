# Quince tandas69–83 · cierre técnico y selección

Candidata83-FINAL02 congelada, schema7. Implementación y revisión independientes; resultado de selección real se registra al final. Avance62/100 provisional (antes60): paridad5→7 por búsqueda y consultas en pantalla antes ausentes; pesos20/25/15/15/15/10 y aportes18/19/14/7/3/1. No suma por15tandas ni contador de tests, y no es porcentaje de QA aprobada o créditos. Sin adopción.

| Tanda | Resultado técnico implementado | Evidencia principal |
|---|---|---|
|69|Cancelar/reabrir Deshacer conserva el candidato vigente; regresión completa final26.5sPASS|frontend/|
|70|Snapshot revalida sesión y lectura tras esperas y antes del commit de lectura|backend/pg02/|
|71|GET búsqueda con filtros cerrados, UUID y revisión|docs/API-CONSULTAS-INVENTARIO-S1.md|
|72|Buscar y abrir ubicación exacta por UUID|frontend/read-final02/|
|73|Unicode, límites, homónimos, paginación y aislamiento PostgreSQL|backend/pg02/|
|74|GET puertos con contexto real y filtros|backend/pg02/|
|75|Vista Puertos por grupo/tipo, sin inferir identidad de gn|frontend/read-final02/|
|76|Puertos/conexiones, revisión y contexto exacto en PG|backend/pg02/|
|77|GET cables con dos extremos, crossRack nullable|backend/pg02/|
|78|Vista Cables sin inferir circuito pasante de Dose|frontend/read-final02/|
|79|Rutas actuales y coherencia de cableado PG|backend/pg02/|
|80|Tres vistas Edge/PG, lector, segunda sesión, reload, SQL9 y restart|frontend/read-final02/|
|81|Actualizador cerrado68→83 y un laboratorio Windows nuevo|windows81/native-final02/|
|82|QA37–39 y QA36 ampliado; disponibilidad fijada a pareja exacta tras selección|docs/QA-CASOS-WASCAR.json|
|83|Revisión independiente y selección segura; resultados al final|revision/|

Pruebas nuevas Windows11, SDK10.0.401, PostgreSQL17.11, Node24.21.0, Python3.12.3; fuentes oficiales/pins existentes ver TOOLCHAIN.json. Un build backend0advertencias/errores; frontend dos builds reales, el segundo correctivo por P2-083-KEY; CSS RC9 idéntico. Los informes anteriores permanecen históricos. La primera invocación frontend usó una ruta relativa errónea del toolchain y no compiló; la segunda ejecutó el único build real.

Fallos conservados: backend/pg01 no ejecutó pruebas por restricted token87 del aislamiento; pg02 autorizado7/7. frontend/read-native01 fixturepatch vacío inválido, corregido a none sólo en arnés; read-native02PASS. compensation-native01 selector Actualizar ambiguo;02 detectó espera insuficiente del arnés.03/04 diagnosticaron aviso residual y duplicación; foco aislado propio/independiente pasó, pero no cerró regresión. El revisor encontró P2-083-KEY nuevo: dos componentes hermanos tenían la misma key. Se corrigieron únicamente los prefijos changes:/read:, sin limpieza especulativa del aviso. FINAL02 conserva DLL y SQL, cambia JS. Dos GUI finales propias PASS:26.5s compensación completa y23.594s tres vistas; guardas1panel/1canal/1consulta, SQL exacto/404/reinicio/entradas intactas/parada correctos. Pareja83 inicial e intentos conservados, no usados para selección.

Límites: consultas en pantalla inventory.read, no exportaciones ni reports.export, carga snapshot completo por cliente; sin nuevo fixture de segundoSystemhaus. Recuperar permisos tras onAuthorityLost requiere reabrir cliente/recargar. Compensación sigue limitada al último ports.update propio y sus cuatro campos; no undo/redo universal. Instalación limpia/servicio/HTTPS, recuperación en otro equipo, manual/paquete completo y QA/adopción de Wascar pendientes. No se probaron notas/resultados manuales ni se modificó backup recibido.

## Identidad final y atribución

CANDIDATA83-FINAL02.json SHA256941f15309ab553179533ab7a91d1d5c1ddcab693ace9d2c604d32749eaf1bcb3. Servidor16archivos b94a3a891a052c40483ac87ae86cc4698f00ce30b4a4b92cf91335f9457a3795; frontend18archivos JS827705fd8ecad208ea1f2a03a3a6a6d7eb0a10e3f7f8a9fb415ab9e355a4af16; CSS50dd856718dd01b3e3356a9a08005df880c859a2652b68a670c167fa75567ec3. SQL001–007, SDK/dependencias, RC9 adoptada y motorWindows intactos. No servidor compilado de nuevo por corrección GUI.

Backend propio7PG85.693s (frontend68 explícito); revisor3PG42.586s sobre pareja83 inicial, mismo DLL final. Unidades propias10/10 y revisión56/56; guía única completa revisión26/26. Contratos83 revisión7/7; Windows83 original propio67.223s/revisor62.601s. Son ejecuciones de esa pareja inicial, no nativosFINAL02 retroactivos. WindowsFINAL02 propio y GUIFINAL02 propias/independientes se registran aparte; el revisor contrasta retarget sin repetir nativoWindows cuyo motor/DLL son idénticos. Capturas nuevas de panel abierto desktop390 revisadas; revisar sólo los PNG iniciales del rack no acreditaba visual del panel.

35casos previos conservados exactamente, QA36 cambia intencionadamente y QA37–39 son nuevos. Las notas/observaciones/resultados de Wascar no se leyeron ni sobrescribieron; la guía conserva claves de navegador/exportación. QA manual anterior no se convierte en aprobación de esta versión.

## Selección y QA disponibles

Revisión independiente FINAL02: fullcomp27.812s y lectura26.297s correctas; correcciónP2cerrada, guardas de una instancia y aviso retirado. Ver revision/REVISION-FINAL02.md. Windows final propio1/1PASS63.911s con fuentes/pares intactos, filas/historia/OID/privados/puntero/3campos, perfilesocupados/PGexterno/reinicio+escrituras sólo fixture.

Operación real tras GO técnico y preflightquiet: CLI0/wrapper0,16/16TRUE33.949s (OPERACION-REAL.json). MismaDB/roles/conexiones/cuentas/URL52346,8privados y36archivosoriginales iguales; versión68 retenida, sólo tres campos config, schema7validado. APP/PGpropios apagados, ceroauth/DML técnicos, ninguna migración/reconstrucción. QAoriginal58822 no actualizado. Postobservación independiente y verificación final de guías/manifiesto en evidencias respectivas.

Wascar: ejecutar INICIAR-QA-RESTAURADO.cmd, abrir GUIA-QA-RESTAURADO.html, Ctrl+F5 en web y probar QA36(Cancelar/reabrir),QA37(Buscar),QA38(Puertos),QA39(Cables). La URL sigue http://127.0.0.1:52346. El CMD abre ACCESO-PRIVADO.txt existente; usar perfiles distintos para TécnicoA/B/Lector. Cada caso indica ubicación/botón/campo/esperado y variantes; notas previas no se sobrescriben y deben exportarse al terminar. Los resultados de QA01–05 anteriores no se consideran repetidos ahora.39casos técnicos disponibles no equivalen a39aprobados por Wascar.

15/15tandas internas cerradas; quedan alcance completo de informes/exportes, undo/redo general, Dosen/alimentación, administración visual integral, paridad, instalaciónWindows limpia/servicioHTTPS/backuprecuperación/otroPC, manual/paquete reproducible y QA/adopción final. Próximo bloque debe escoger tareas pequeñas de esos pendientes sin otro piloto ni rediseño RC9.

## Verificación final

Postobservación independiente15/15PASS; ambas copias apagadas/puertos sin escucha en ese instante, pares83/68exactos. El revisor no repitió las comparaciones privadas/originales del operador; atribución separada. Guías regeneradas y sus dos checks correctos,39/39casos restaurado y8/39original, cuatrogatesnuevos sólo83FINAL02. Una prueba focal de gates1/1PASS0.002s; no se repitieron las26unidades de guía. Primer intento de regeneración bajo sandbox fallóWinError5 leyendo punteros; mismo generador autorizado pasó, sin cambiar ACL. Notas/import/exportJS idénticosHEAD,35casos previos y13pins intactos, fuentesfinales exactas. VERIFICACION-FINAL.json detalla metadatos. SHA256SUMS vigente de este bloque cubre código/documentación/evidencias nuevas; manifiestos antiguos se conservan como historia.
