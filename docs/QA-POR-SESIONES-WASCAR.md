# QA a tu ritmo · preparación del19.10.2026

El punto de entrada es **ABRIR-PLAN-QA-WASCAR.cmd**, en C:\RackClick_SVR. Regenera [EMPEZAR-QA-WASCAR.html](../EMPEZAR-QA-WASCAR.html) desde el catálogo y el snapshot real, junto con la guía restaurada. No inicia el servidor ni cambia respuestas. Para probar la aplicación en el laboratorio actual se usa **INICIAR-QA-RESTAURADO.cmd** en ese mismo equipo; LAN y servicioWindows siguen pendientes.

La aplicación de los usuarios funciona en el navegador. Estos CMD son herramientas del laboratorio de desarrollo actual, no instaladores para los clientes. El inventario de Windows11/Server2025 como posibles servidores es una preparación separada.

## Orden sugerido, sin exigir hacerlo de una vez

| Rato | Casos en orden | Objetivo |
|---|---|---|
| A | QA-01,QA-11 | Entrar y reconocer el backup restaurado, sin editar. Los recuentos históricos no obligan a deshacer cambios legítimos. |
| B | QA-91,92,93 | Revisar la novedad de grupos. Puede hacerse sólo91 al principio.92requiere destinos ficticios seleccionables;93requiere recibo nuevo y Lector. Voz y fallos de red no ensayados quedan Bloqueados por paso. |
| C | QA-02,03,04,05,06 | Volver a Administrador si se terminó93comoLector. Guardar nombres, comprobar segunda sesión y un rack ficticio. QA-04 depende de02/03; QA-06 utiliza el clienteB de03. |

Los demás casos continúan disponibles en la guía completa para otra sesión. No se exige que un único probador repita93casos como condición de entregar un resultado parcial. No se promete una fecha de adopción por la expectativa de terminar esta semana.

Cada caso de la [guía restaurada](../GUIA-QA-RESTAURADO.html) mantiene sus pasos de ubicación/botón/campo y resultado esperado. Para encontrarlo: abrir guía → Ctrl+F → escribir suID, por ejemplo QA-91 → Escape. No se inventan enlaces#ID que la guía no admite.

## Una única copia de respuestas

La landing no guarda resultados; se anotan en Tu resultado y Observaciones de la guía completa. En escritorio están a la derecha de los pasos; en pantalla estrecha, debajo. Sin probar significa no empezado; Not Pass identifica fallo; Bloqueado identifica falta de requisito o tramo no ensayado. Para pruebas parciales, anotar pasos correctos y bloqueados sin declararPass completo.

Mantener las notas en una ventana normal del navegador/perfil habitual. InPrivate u otro perfil se usan sólo para la web de una segunda sesión/cuenta: un único probador puede operar ambas. No confundir las cookies del QA original y restaurado ni guardar notas en InPrivate.

Antes de repetir/importar: pulsar arriba **Guardar copia de mis resultados** y conservar eseJSON. La guía conserva un registro por caso/perfil; cambiarlo no genera historial multiversión. Un aviso de versión/caso cambiado conserva el histórico y requiere repetir cuando se pueda. Importar mediante **Recuperar copia** sustituye sólo los casos incluidos, con confirmación; no hacerlo si las notas actuales ya están presentes.

Al finalizar cada rato: exportar otra copia, abrir Descargas con Ctrl+J y localizar Resultados-QA-Wascar-…json. Puede enviarse por el chat aunque queden pruebas sin hacer. Guardar las copias anteriores. No incluir contraseñas, tokens o capturas con credenciales.

Para detener únicamente este laboratorio: **DETENER-QA-RESTAURADO.cmd**. No modificar bases ni apagar servicios para provocar fallos. Desarrollo conserva la responsabilidad de los ensayos técnicos y de corregir los defectos.

Catálogo/guía/gates/resultados previos quedan intactos; la landing lee su disponibilidad real al regenerarse. Avance global aproximado **78 %**; las respuestas y la aceptación final de Wascar siguen pendientes. [Evidencia de esta preparación](../evidence/s1-20261019/preparar-qa-sin-prisa/CIERRE.md).
