# QA138 · primera carcasa integrada

30.10.2026. **Preparado en desarrollo; todavía no disponible en tu instalación 10.**
Este lote amplía el caso QA-138, no borra tus resultados. Espera la candidata completa
identificada; no copies archivos sueltos al servidor ni repitas la instalación/MFA.

El modelo es **StarTech.com C6PANELUTP241UFT**, revisión `startech-20261030-v1`.
Su frontal usa una carcasa propia basada en la referencia. La trasera sigue siendo
genérica porque no tenemos su geometría contrastada. Son 24 acopladores, 48 extremos
físicos; no se han añadido interfaces activas o cables internos automáticos.

| Ubicación | Qué hacer | Qué debes ver | Pass / Not Pass / observación |
|---|---|---|---|
| Menú izquierdo → Clientes | Abre un cliente sintético y un rack con 2 U libres. | Inventario del cliente y espacio disponible. | |
| Barra superior → Añadir hardware de referencia | En Perfil de referencia, elige StarTech.com · C6PANELUTP241UFT con su revisión. Escribe Panel A y pulsa Guardar abajo. Repite con Panel B. | Espera Guardado por el servidor. Dos objetos independientes, cada uno de 1 U. | |
| Encima del dibujo → Frontal | Mira ambos paneles. | Carcasa negra, orejas laterales y cuatro bloques de seis RJ45, del 1 al 24. Las ranuras decorativas no se pueden conectar. | |
| Panel A → conector 1; Panel B → conector 1 | Pulsa esos dos conectores y espera. | Aparece un cable confirmado por el servidor. Al desplazar horizontalmente el frontal, sigue unido al conector. | |
| Navegador estrecho | Reduce el ancho de la ventana. Dentro del frontal arrastra la barra horizontal hasta la derecha. Pulsa el conector 24 y cancela la selección desde el aviso superior. | Puedes llegar al conector 24 sin que los 24 se reordenen en varias filas. No se guarda ningún cambio por desplazar o cancelar. | |
| Teclado | Pulsa Tab hasta enfocar un conector libre y luego Enter. Cancela la selección. | El foco se distingue; aparece la selección del puerto correcto. | |
| Encima del dibujo → Trasera | Comprueba el aviso Cara genérica. Conecta el 1 trasero de A con el 1 trasero de B. | Otro cable y otros extremos. Los números traseros son lógicos; no se afirman como etiquetas impresas. | |
| Cabecera de A → lápiz | Cambia nombre/notas y guarda. Después pulsa F5 y vuelve al rack. | Identidad, revisión, conectores y los dos cables se conservan. | |
| Otra sesión autorizada | Entra y abre el mismo rack. Si tienes una cuenta de sólo lectura, repite con ella. | Ambas leen lo guardado; el lector no puede editar. Si no tienes esa cuenta, anota No probado. | |

Puedes ver el resultado del laboratorio sin instalar nada en
[las capturas del lote](../VER-INTEGRACION-CARCASAS-01.html).
Para creación, falta de espacio y detalle del modelo se conserva
[el guion anterior de QA138](QA-PRIMER-MODELO-COMERCIAL-WASCAR.md).

## Actualización: fotografía original

La preferencia visual de Wascar exige la imagen original en lugar del dibujo como presentación principal cuando esté disponible en una candidata identificada. El guion de fotografía y sus límites está en [INTEGRACION-FOTOS-ORIGINALES-LOTE01.md](INTEGRACION-FOTOS-ORIGINALES-LOTE01.md). En el ensayo privado, Frontal conserva forma, color, rótulos y perspectiva; los controles transparentes corresponden a los24puertos. Sin fotografía válida se identifica el respaldo. La trasera sin fuente sigue genérica. QA138 permanece planificado; no cambies la instalación10.


## Aclaración definitiva de Wascar · frontal plano interactivo

30.10.2026. El ensayo de fotografía oblicua se descarta para la presentación operativa: fue un error de interpretación. Las imágenes originales se usan como referencia para recrear forma/color/distribución en frontal plano, con bocas visibles y UUID/Click-Click. Se conserva esta evidencia histórica. Rige [el frontal interactivo corregido](FRONTAL-INTERACTIVO-REFERENCIA-ORIGINAL-LOTE01.md), probado y revisado en laboratorio; aceptación visual de Wascar y candidata completa pendientes. Capturas vigentes: [VER-FRONTAL-INTERACTIVO-01.html](../VER-FRONTAL-INTERACTIVO-01.html). QA138continúa planned.


## 30.10.2026 · Trasera específica añadida

La trasera genérica anterior queda como historia del lote. Rige [la trasera plana interactiva](TRASERA-INTERACTIVA-STARTECH-LOTE01.md), referenciada en imagen comparativa de proveedor del SKU exacto, contrastando conteo/tipo con PDFoficial. Conserva24UUID/Click-Click y ordenlógico24→1, con números/etiquetasfuera de carcasa. Fuentevisualnoautenticadafabricante; aceptaciónestética pendiente. Frontalintacto, QA138planned y capturas vigentes en [VER-TRASERA-INTERACTIVA-01.html](../VER-TRASERA-INTERACTIVA-01.html).
