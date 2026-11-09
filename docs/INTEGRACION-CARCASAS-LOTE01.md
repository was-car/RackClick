# Integración de carcasas · lote 01

30.10.2026. Primer frontal específico: **StarTech.com C6PANELUTP241UFT**.
Se conserva la GUI RC9, su montaje y el guardado transaccional existente.
Este lote no incorpora los otros 505 modelos ni cambia la instalación de Wascar.

[Capturas reales del laboratorio](../VER-INTEGRACION-CARCASAS-01.html) ·
[Pasos QA preparados](QA-CARCASAS-LOTE01-WASCAR.md) ·
[Evidencia y revisión](../evidence/s1-20261030/hardware-shell-lot1/RESULTADOS.md).

## Contrato de representación

- La identidad funcional sigue siendo la pareja `startech-c6panelutp241uft` /
  `startech-20261030-v1`. La revisión visual propia es
  `startech-c6panelutp241uft-front-v1`; no modifica SQL018, dimensiones o contratos API.
- El frontal específico requiere esa pareja exacta, la identidad comercial guardada,
  1 U y los 48 extremos RJ45 coherentes: dos grupos separados, uno por cara, con
  24 UUID y ordinales distintos por grupo. Un nombre parecido o una revisión más
  nueva no permite tomar prestada esta carcasa.
- La disposición frontal usa los botones existentes, por UUID: cuatro bloques de
  seis, sin generar puertos o cables. Conserva selección, Click-Click, menú contextual,
  etiquetas, color y tooltip de los puertos registrados. Los elementos decorativos
  no tienen manejadores de conexión.
- Si faltan la revisión o la geometría contrastada, o la topología no coincide, se
  conserva la representación genérica con todos los conectores registrados. La
  trasera de este modelo queda explícitamente genérica con números lógicos.
- El esquema propio toma forma, color aproximado, orejas y bloques de la foto
  oficial. No es una fotografía, reproducción CAD, garantía de colorimetría o
  afirmación sobre revisiones físicas desconocidas. No incluye logos o fotos copiados.
- En pantallas estrechas, el frontal conserva su fila y se desplaza horizontalmente
  dentro de la carcasa. Los botones siguen siendo accesibles por teclado. El renderer
  recalcula los extremos de los cables cuando cambia ese desplazamiento.

Los textos de explicación están en EN/DE/ES; los nombres introducidos por usuarios,
la marca y el modelo no se traducen. Se reutilizan React/IRPortShape/CSS existentes,
sin dependencias ni llamadas remotas para dibujar.

## Proceso para los siguientes lotes

Cada cara/modelo necesita su fuente, pareja/revisión, geometría contrastada y prueba
de selección/UUID/conexiones/guardado/recarga. La biblioteca de 506 modelos sirve de
referencia, no de importación automática de especificaciones. Las caras desconocidas
quedan genéricas. Un modelo funcional nuevo requiere su propio catálogo y migración;
no se modifica una migración sellada para añadirlo.

El siguiente lote puede abordar la carcasa de la bandeja y el firewall o switch que
se seleccione, contrastando antes su revisión y topología. Los perfiles sintéticos
existentes se conservan como genéricos hasta que haya un modelo comercial identificado.

Distribución/Restore18, paquete completo, servicio/reinicio Windows y aceptación QA
siguen pendientes. El lote de frontend no habilita QA-138 en la instalación 10.
**Índice de cierre restante 9,76/100, sin crédito automático por otra carcasa.**

## Corrección visual posterior de Wascar

Wascar rechaza el aspecto del dibujo y pide forma/colores originales. El dictamen funcional anterior no implica su aceptación estética. El esquema queda como respaldo; se implementa una [integración con fotografía original para ensayo privado](INTEGRACION-FOTOS-ORIGINALES-LOTE01.md), sin editar la imagen, con puertos transparentes y manteniendo pendientes los derechos de redistribución. Las evidencias anteriores se conservan.


## Aclaración definitiva de Wascar · frontal plano interactivo

30.10.2026. El ensayo de fotografía oblicua se descarta para la presentación operativa: fue un error de interpretación. Las imágenes originales se usan como referencia para recrear forma/color/distribución en frontal plano, con bocas visibles y UUID/Click-Click. Se conserva esta evidencia histórica. Rige [el frontal interactivo corregido](FRONTAL-INTERACTIVO-REFERENCIA-ORIGINAL-LOTE01.md), probado y revisado en laboratorio; aceptación visual de Wascar y candidata completa pendientes. Capturas vigentes: [VER-FRONTAL-INTERACTIVO-01.html](../VER-FRONTAL-INTERACTIVO-01.html). QA138continúa planned.
