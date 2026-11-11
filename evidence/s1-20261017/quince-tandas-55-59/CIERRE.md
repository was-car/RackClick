# Quince tandas55–59 completadas

17.10.2026 · Windows · base `adbd136`. **15/15 tandas internas implementadas, probadas y revisadas de forma acotada por otro agente.** La nueva copia del QA restaurado usa DLL59/interfaz59/esquema7 en http://127.0.0.1:52346. Se dejó apagada. Origen4, recuperación4, datos, cuentas y cuatro archivos privados conservados. No se operó QA original ni se leyeron notas/resultados del navegador. No es instalador completo ni adopción del servidor.

[Registro individual de15tandas](../../../docs/PLAN-QUINCE-TANDAS-55-59.json) · [revisión independiente](revision/REVISION.md) · [procedimiento Windows](../../../docs/ACTUALIZACION-QA-SCHEMA6-S1.md) · [guía actual](../../../GUIA-QA-RESTAURADO.html).

| Grupo | Windows · `copia_schema53` | Backend · `backend_audit50` | Interfaz · `frontend_quince` |
|---|---|---|---|
|55|Source4: identidad, artefactos, quietud e historia|Contraseña/sesión y cancelaciones,8/21|Contexto de auditoría tipado|
|56|Dump/restore a candidata y recuperación nuevas|Altas/cancelaciones de grupos,12/21|Ficha y membresías ligadas al selector|
|57|Control.lock, supervisor, puntero y URL estable|Miembros de grupos y cancelaciones,16/21|Lote único por UUID/grupo/tipo y preview|
|58|Negativos de inicio incierto, actividad y rollback|Concesiones y cancelación,18/21|Notas/color/5patch/desconexión|
|59|Selección real de nueva copia restaurada7|Nombres House/cliente,21/21|Edición/reasignación y borrado ocupado|

Cada celda enlaza su cierre a través del registro individual. Coordinador: decisiones, catálogo/guías, continuidad y congelación. `revision_filtros_gui44` revisó producto ajeno y no lo modificó para aprobarlo. Revisión y ejecución propia son conceptos separados: las quince conclusiones indican qué reprodujo el revisor y qué inspeccionó junto a la evidencia del autor.

## Resultado real y forma de probar

Ejecutar `C:\RackClick_SVR\INICIAR-QA-RESTAURADO.cmd`; usar las cuentas y contraseñas del `ACCESO-PRIVADO.txt` que abre ese CMD. En el navegador del mismo Windows, elegir Español y pulsar Ctrl+F5. La guía restaurada contiene31 casos:30 disponibles por la pareja seleccionada, QA-10 (avisos multiusuario) multiusuario continúa pendiente. Disponibilidad no significa prueba manual aprobada ni servidor encendido. Los casos pueden requerir datos ficticios preparados según sus pasos.

Se habilitan navegaciónQA-23, selección/ficha/membresíasQA-25, duplicaciónQA-26 y PoE/caraQA-27. Nuevos: QA-28contexto, QA-29lote, QA-30cables y QA-31jerarquía. QA-12/20/21/23/25 se actualizan;22 objetos anteriores permanecen idénticos. Se retiraron las parejas53anteriores del gateQA-25 porque su guion ahora exige membresías integradas56. Las claves y el código de notas/resultados se conservan; no se leen ni sobrescriben respuestas de Wascar. La propia guía señala caso/versión cambiados y conserva observaciones y exportación/importación.

CLI real59: `committed`, exit0,41,766s, `--leave-stopped`. [Resultado público](windows/59/result.json):29/29checks,0login y0DML técnicos reales. PG fuente se inició para dump/lecturas bajo lock y volvió a quedar apagado; sus filas/historia se certificaron durante la copia. La postcomprobación SQL READ ONLY posterior consultó únicamente candidata7/recuperación4, sin volver a abrir la fuente4; verificó filas exactas,001–007/digests, recuperación4 íntegra y ausencia de actividad posterior. No se afirma identidad byte por byte del directorio físico PG después de arrancarlo.

[GO previo independiente](revision/GO-TECNICO59.json), [GO del coordinador](GO-COORDINADOR59.json), [cierre real](windows/59/CIERRE.md). El revisor comprobó después sólo puntero/configmínima,16/18artefactos, puerto/marker/lock y pg_ctlstatus3: no SQL, login, HTTP ni credenciales reales propias. Sus lecturas pasivas se distinguen de los29checks del operador en `revision/POST59-PASIVO.json` y `POST59-INFORME-PUBLICO.json`.

## Versiones y pruebas reales

SDK10.0.401, PostgreSQL17.11, Python3.12.3, Node24.21.0 y Windows11; Edge155 en navegador. Sin instalar dependencias ni cambiar versiones/locks en este bloque.001–006, RC9adoptada, Click-Click, CSS52 y contratos46/50 conservados;007 es aditiva y no rellena historia ausente.

| Ejecutor | Resultado y versión realmente usados |
|---|---|
|Backend autor|Focales55:3/3,33,071s;56:2/2,19,193s;57:2/2,23,488s;59:3/3,29,016s.58 conserva intento1PASS/1FAIL de fixture18,880s y sólo atomic corregido1/1PASS6,497s, mismaDLL. Regresión final única5/5PASS54,604s sobre DLL59/schema7,21formasHTTP. Cada etapa tiene su DLL/fuentes congeladas.|
|Windows autor|55:1grupo15,223s;56:1grupo45,299s;57:1grupo80,411s sobre6.58:1grupo167,964s sobre pareja final7; fuentes58 corrigen borde de inicioPG y mantienen snapshot57 anterior.59 real descrito arriba.|
|Frontend autor|55:18,063s;56:19,875s y recuperación adicional19,125s;57final:23,500s;58:23,687s;59:25,890s.32unidades159,7823ms. DLL54/schema6 para todos;55/56/58/59 GUIbuild5/6 idénticos18/18,57final GUIbuild8. Build8 cambia sólo app.js por previewUUID; demás17archivos exactos. No atribuir estos recorridos a DLL59.|
|Revisor backend|8/8PASS98,851s sobre DLL59/schema7:5flujos con21formas, autoridad/coherencia, rollback password/sesión y migración007/legacy4. No repite todas las inyecciones de todas las familias.|
|Revisor Windows|57:1grupo90,984s;58:1grupo153,125s sobre pareja final7. Ejercitan Source4/copia; no nuevos focos55/56 separados ni recuperación4 sirviendo propios.|
|Revisor GUI|55ampliado20,485s (wire/display cliente real);56focal19,422s;57lote28,094s sobre7final.32unidades157,6938ms.58/59 revisados por fuente invariante/evidencia del autor, sin reproducción GUI propia final.|
|Guía|Coordinador:1focal nuevo de gatesPASS0,002s. Revisor:21/21PASS0,284s, contextos sintéticos sin leerQAreal; regeneración/check de ambas guías y bindings por coordinador. No repetir21por cambiar sólo dato53→56 del encabezado.|

[Cierres/backend y comandos](backend/CIERRE.md), [frontend y límites](frontend/CIERRE.md), [Windows58](windows/58/CIERRE.md). Todos los fixtures finales se cerraron y sus inputs/inmutables permanecieron intactos. Intentos fallidos se conservan por separado, sin transformarlos en suites completas correctas.

## Correcciones y límites de la evidencia

- Contexto:21formas finitas, objetos directos ordenados y sesiónUUIDpública exacta. House r→r+1 committed/r→r cancelled; cliente create null→1 y rename positivo→+1, separados del House histórico. GETautorizado GLOBAL. Replay no hace backfill; sin rawJSON ni secretos ni historia reconstruida. Negativos frontend añaden ámbito obligatorio cliente y igualdadámbito/recurso de Systemhaus. Nativo propio del revisor confirmó createHouse2→3/cliente null→1 y renameHouse3→4/cliente1→2; contexto legible desktop/390px.
- Membresías: el autor encontró/corrigió el mensaje de guardado que desaparecía trascommit; no reenviar para mostrar confirmación. Guardas conservan borrador y actor/destino original de pendiente aunque la ficha muestre otro usuario. Se prueba recuperación HTTP; no guardar contraseñas en ficha/journal.
- Lote: una solicitud `connections.createBatch`, paresUUID; GUI selecciona grupo/tipo explícitos, servidor revalida extremos reales en su cliente. No se añade grupo/tipo al DTO existente de pares ni se usa gn comoidentidad. Preview incluye IDs completos y wrap. Revisor los comprobó por DOM; su PNGmóvil no muestra el vista previa inferior y no se atribuye inspección visual de esa zona. Respuesta200perdida real y retryexacto no duplican cables.
- NegativosGUI57/58/59: primer extremo ocupado, patch inválido alvalidar y FK por ubicación ocupada. Tablas/revisión/operación/auditoría intactas; no se presentan como fallo después de insertarprimera fila. Backend sí usa triggers transaccionales para rollback durante escritura.
- Windows: revisor señaló enlaceSQL/data_directory y propiedad dePGantesdelstart; errorPOSTstart conPGreal termina parado/verificado. Lock, rollbackpre/posterior al puntero sin actividad y DMLcompensada conTODASfilasiguales+xmaxavanzado probados. Ante actividad conserva puntero7/ramas y declararecovery_required. Incertidumbredelectura/baseline usa negativos helper con mocks; no caída de proceso o fallo de disco ni garantía antepropietario que eluda locks.

## Alcance pendiente y porcentaje

**56/100 provisional**, aportes18/17/14/3/3/1 y mismos pesos20/25/15/15/15/10. Inventario+1 por la GUIausente del lote; Windows+2 por copia/recuperación/lifecycle y selecciónreal revisados. Administración sigue14/15; quince tandas no significan quince puntos de progreso ni producto final. La guía muestra el entero provisional sin segunda cifra redondeada. No mide créditos, calendario ni aceptación.

Quedan experiencia administrativa integral, otras capturas/auditoría, borrado múltiple/compensación, Dosen/presupuestos/conectores, avisos multiusuario, herramientas/informes/exportes/paridadEN/DE/ES, instalador limpio, servicio y HTTPS y backup/restore final en otroequipo, manual/paquete completo y QA/adopción de Wascar. Sin publicación ni sustitución dePostgreSQL. [Mapa actualizado](../../../docs/MAPA-ENTREGA.json).

`CANDIDATA7.json` fija16/18 archivos y SHA256c5447d77…716d332; su selecciónal congelar era falsa, el acto posterior se acredita en59. Congelación, comprobaciones y manifiesto raíz se completan después de cerrar la revisión; los manifiestos históricos55–58 y los grupos anteriores no se reescriben.

Comprobación final de integridad:69archivos públicos y17pins, cinco árboles backend de16archivos, candidata y copia seleccionada16/18 exactas; manifests frontend114/Windows62/revisión55 y subetapas válidos. No son nuevas pruebas nativas. El control de espacios exceptúa únicamente los dos diffs crudos `backend/59/diff-final.patch` y `windows/59/source.diff`: sus líneas de contexto se conservan byte por byte como evidencia. El resto, incluido producto/documentación, pasa sin exenciones; [detalle](WHITESPACE.json). [Bindings](VERIFICACION.json) y manifiesto raíz fijan el paquete de este bloque.
