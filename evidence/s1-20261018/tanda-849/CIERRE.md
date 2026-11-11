# Tanda849 · Aviso accesible en la aplicación completa

La corrección848 ya forma parte de una compilación completa de la GUI, candidata849. Se verificó con Edge y PostgreSQL17.11 real en un laboratorio nuevo. No se seleccionó en QA832 ni se produjo otro ZIP Windows; QA-78 permanece bloqueado hasta esa integración. Global **78 % aproximado**, sin aumento por una comprobación aislada.

## Construcción y distribuciones

BaseGit834cc776c98f4a8c08d6db40b75480a709373dc2. `tools/tests/build_relations849.py` ejecuta un único buildfrontend con Node24.21.0 y dependencias ya fijadas, sin descargas. Verifica175fuentes frente a832: sólo AdminGroupRelations.jsx difiere y coincide con la fuente7f0d…8b9f revisada en848. Se copian los20archivos del servidor832, SQL001–011 y todas sus dependencias byte a byte. De18frontend sólo app.js cambia; CSS, fuentes, React y licencias conservados. Build0,484s, sin publicar/recompilar C#.

CANDIDATA849.json: esquema11,38archivos,7.108.622bytes, SHA256 `1b40f9ceffde0503c024f0dce1fb79de02c05a21bc9cb93ad3b0d6a3d359dc09`. Distribución nueva bajo .local/candidates, con hashes individuales y175fuentes congeladas. No se incorpora aún a los perfiles cerrados Windows.

## Pruebas y corrección del arnés

Se amplió el mismo escenario existente `browser-admin-group-relations.mjs`/`test_admin_group_relations_gui.py`. Una prueba compuesta, no diez suites: diez observaciones del nodo status exacto en el árbol accesible, selección inicial/homónimos/tipo, EN/DE/ES y retirada tras403. La aplicación completa tiene otras regiones status; se usa backendDOMNodeId. Persiste el nodo, texto literal con UUID reales y polite/atomic; el artículo no anuncia listas completas. Se comprueban 390px sin desbordamiento, Tab entre selectores, borrador/usuario conservados y cero escrituras administrativas HTTP al navegar.

El fixture SQL revoca seguridad de su administrador sintético; el servidor devuelve403 y al actualizar retira relaciones/aviso anteriores. Se comparan ocho tablas de grupos antes de esa revocación, no toda la base35tablas. Credenciales y logs de servidor quedan privados bajo .local. No se utiliza el laboratorio de Wascar.

Intento01: FAIL17,812s, «Object reference chain is too long», debido al nuevo Runtime.evaluate del arnés que intentó serializar un nodo DOM con referencias React. Guion exacto y resultado fallido conservados. Se añadieron dos `;true` para devolver un booleano y mantener el nodo en window; no se cambió ni recompiló el producto. Intento02: PASS22,578s, inputs intactos y app/PG propios detenidos. Ambos intentos usan clusters/bases nuevos y conservan sus evidencias separadas. INCIDENCIA-01.md explica la causa.

Comando de reproducción desde C:\RackClick_SVR; pasar rutas serverDll/frontend del manifiesto y un output NUEVO:

```powershell
C:/Python312/python.exe -X utf8 -B development/server/tests/test_admin_group_relations_gui.py --output <directorio-nuevo> --dll <serverDll> --frontend <frontend>
```

Capturas reales EN/DE/ES390 y browser.json/fixture.json en pg-browser02. Coordinador inspeccionó capturaES: ficha y texto literal legibles, el aviso recortado no añade bloques visibles. No es una revisión visual completa de RC9. La revisión independiente especifica qué archivos/capturas/controles leyó y no se atribuye nuestras ejecuciones. No se repite la suite nativa por inercia en revisión.

## QA y continuidad

Catálogo78casos: primeros77exactos, sólo introducciónQA-78 actualizada para candidata849 ya probada pero pendiente de selección. Las otras instrucciones y expected deQA-78 se conservan. Sigue `planned`:77disponibles restaurado/8original. Ambas guías regeneradas; tres tests focales de848 PASS, sin repetir las40 ya ejecutadas allí. No notas/resultados de Wascar leídos ni sobrescritos; no voz de lector de pantalla probada.

Siguiente: integración Windows/QA conservadora con revisión y verificación antes de habilitarQA-78; después voz real por Wascar. Persisten funciones RC9/Dosen/undo/admin, operación Windows completa, recuperación/manual y QA/adopción final. No se certifican Windows limpio, instalación/recuperación de849, todos35datos, accesibilidad universal ni voz AT. El paquete847 y candidato/QA832 se conservan. La nueva evidencia se sella con diff/SHA256SUMS y commit sólo local.
