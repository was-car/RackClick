# Punto6 · QA y cierre de la candidata11

02.11.2026. **Ficha y protocolo de QA preparados y revisados. El producto no se declara cerrado.** No se ejecutó ninguna VM ni instalación; no hay un resultado manual nuevo de Wascar.

## Resultado entregado

- [QA-CIERRE-CANDIDATA11.html](../../../QA-CIERRE-CANDIDATA11.html):14casos seleccionados de los167existentes, pasos de ubicación/botón/campo yresultado esperado, notas yPass/NotPass/Bloqueado. Casos de roles/recuperación señalan cuentas previas necesarias; no usar el último administrador.
- [Protocolo](../../../docs/QA-CIERRE-CANDIDATA11.md) y [definiciónJSON](../../../docs/QA-CIERRE-CANDIDATA11.json), derivados automáticamente del catálogo. No se añaden requisitos, casos o puntos.
- Herramientas nuevas: tools/qa_candidate11.py, tools/qa_candidate11.mjs, tools/tests/test_qa_candidate11.py ytools/tests/browser-qa-candidate11.mjs. No se cambia código de aplicación, instalador, SQL, versiones, dependencias ni elZIP11.
- Guardado separado porhash11, exportaciónJSON yvalidación de edición/esquema/SHA. Otrascandidatas/formatos/tiposincorrectos no se mezclan. Si cambia el guion, las notas se conservan pero suPassno cuenta hasta confirmar otro resultado expresamente.
- La hoja yelvalorador mantienen adoption=false/productionReady=false incluso con14Pass. Los resultados son autorreporte; la URL/confirmación no autentican el servidor. No se importan registros deguías anteriores ni se modifican resultados personales.

## Qué se ejecutó ahora

| Comprobación | Resultado y ámbito |
|---|---|
| ZIP físico de la entrega11 | SHA256 f090b56e13bc3d4670834746cff33a2d01831eae517dbb0343ce760241c567b0,123.473.555bytes,140entradas. Lectura/verificación, sin reconstruir ni instalar. |
| Evidencia previa | Sellos de punto3:28entradas,Demo50:53,Windows43:79, más3índiceshijos históricos fijados porbytes. Su contenido de fuentes no se ejecuta. Los resultados previos se reutilizan, no se cuentan como ensayos nuevos. |
| Pruebas Python del implementador |7PASS sobre atribución de versiones, tipos, obsolescencia, noadopción, texto no confiable y catálogo no modificado. UNIT-7.txt. |
| Navegador real del implementador |10comprobaciones PASS en Edge/nuevo perfil privado:14casos sin probar al inicio, notasHTMLcomo texto, recarga, exportJSON, rechazo deotra edición sin perder notas, importación parcial conservadora, stale/edición de notas, reconfirmación expresa yotra clave local intacta; cero errores de script. EDGE-RESULTADOS.json. |
| Revisión independiente |32focos propios PASS:20Python,8JavaScript conDOMsimulado,4guardas deauditoría. [Dictamen](review/REVISION.md). No se atribuye Edge al revisor ni mocks a ensayos HTTP/VM. |
| VMware | vmrun -T ws list mostró0VM encendidas. Sólo lectura; se consultó disponibilidad aWascar sin asumir respuesta. No se encendió, apagó o revirtió ninguna VM. |

Las10comprobaciones Edge usan datos de prueba AUTOMATED TEST ONLY en un perfil nuevo. Su captura UI-AUTOMATIZADA.png ylosJSONprivados del arnés **no son resultados manuales de Wascar**. No se ejecutaron otra vez las68pruebas/40focos/carga50 del punto5 ni se generaron recibos para la VM.

## Correcciones y fallos conservados

**QA11-R01 · P2 · corregido y revisado.** El revisor reprodujo que editar sólo las notas deunPassconhashantiguo fijaba elhashactual ylo contaba comoPassnuevo. Se separaron las acciones: editar notas conserva elhash/resultadoantiguos, el selector se presenta Sinprobar yúnicamente una elección expresa actualiza el caso. El mismo negativo falla antes y pasa después, conrojo/verde preservados en review/. Edge confirma el recorrido real. Las notas no se descartan.

**Auditoría inicial del auxiliar:** se supuso que el sello padre de punto3 incluía todos losíndiceshijos. No era así: tres estaban excluidos. La siguiente hipótesis asumía rutas locales en ellos; json-exportincluye fuentes relativas al repositorio. Ambosrechazos iniciales se registran en INCIDENCIAS-AUDIT.json; no se reescribió evidencia anterior. El auxiliar final verifica losdatos cubiertos porelpadre ylosbytes deesos tres índices mediantepins literales, sin convertir sus referencias de fuentes en nuevas ejecuciones.

**Arnés Edge, intentos01/02:** escogía elprimer destinoCDP, que resultó ser una extensión/background. La hoja no llegó a cargarse; filas0, no un error del producto. Se conservan ambosFAIL. Al seleccionar explícitamente un destino page/about:blank, el intento03 pasa. El chequeo sintáctico del módulo había pasado; no era un error del formulario.

## Conciliación de los seis puntos

| Punto | Estado comprobable | Cierre pendiente |
|---|---|---|
|1 · Catálogo |506/506seleccionados integrados en desarrollo;868revisiones con reservas explícitas. |QA/aceptación deinstalación, no afirmar aceptación de cada modelo sólo porexistir. |
|2 · Consolidación |Artefactos identificados yconservados;11 usa laaplicaciónposterior delpunto3. |Mantener identidad de versión al ensayar. |
|3 · Funciones |CódigosMFApropios yJSONcliente integrados/revisados. |Portable/emergencia/rotaciónMFA, importación/merge, backupdashboard yaceptación administrativa. No está cerrado. |
|4 · Datos50 |Datos y2553comandos de carga opcional probados en laboratorio. |TLS/MFAreal delcargador enVM/QAmanual. |
|5 · Windows |ZIP11 completo como candidata local, New/HTTPS/backup/Restore15→43 y43→43 registrados. |Elevación, cuenta efectiva,SCM,CA/firewall,backup programado/reinicioWindows11. |
|6 · QA y cierre |Ficha14casos,integridad yauxiliares probados/revisados. |VM11, resultados deWascar, recuperacióncompleta/redistribución yadopción. |

La ficha14es una selección operativa, no toda la aceptación del contrato ni un nuevo denominador. Catálogo506/506=100% de esa selección; índice acreditado delcierrependiente9,76/100intacto y global_product_percentage=null. No se acredita avance por generar documentos o sumarpruebas.

## Próximo paso concreto

Wascar prepara/inicia una VM Windows Server2025 limpia/noDC y avisa cuando Windows está en elescritorio. Conserva su estado actual con snapshot ygestiona personalmente cualquier reversión. Entonces se verifica identidad ypaquete, se ensaya11 yse recogen elresultado postboot yelinformeoficial sanitizado. No sustituir el servidor10/QA ni susdatos para realizar este ensayo.

Mientras tanto la hoja puede abrirse para leer yplanificar; sus casos permanecen Sinprobar/Bloqueado hasta realizarlos. Al terminar cada sesión se exporta suJSON yse envía junto al informe, sin credenciales, claves o códigos.

No hay commits,push,publicación,limpieza,cambios deVM/servicios/cuentas/DB/ledger, niadopción.
