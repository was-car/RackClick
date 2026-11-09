# Primer modelo comercial: StarTech.com C6PANELUTP241UFT

30.10.2026. Implementado y revisado en desarrollo. **No instalado en la VM de
Wascar ni disponible todavía en su candidata10.**

[Capturas del ensayo](../VER-PRIMER-MODELO-COMERCIAL.html) ·
[Revisión independiente](REVISION-PRIMER-MODELO-COMERCIAL-30-10-2026.md) ·
[Guion QA preparado](QA-PRIMER-MODELO-COMERCIAL-WASCAR.md).

## Datos contrastados

Se usa este SKU concreto, no el panel vacío C6PANELUTP241U ni un panel de
terminación110. La [ficha oficial](https://media.startech.com/cms/pdfs/c6panelutp241uft_datasheet.pdf)
describe un panel pasante1U con 24 acopladoresRJ45UTP preinstalados. Se representan
24 conectores frontales y 24 traseros: **48 extremos físicos, no48 interfaces Ethernet
activas independientes**. La correspondencia de cada acoplador se declara sin
crear cables automáticos ni afirmar que el trazado interno esté implementado.

La ficha fijada publica dimensiones métricas nominales de483×44,3×138mm, tomando
el eje largo del montaje como ancho. Se conserva44,3sin truncar. Valores de
otras fichas/cachés no se mezclan para inventar más precisión. Revisión física
y fecha de lanzamiento desconocidas; la revisión `startech-20261030-v1` es del
catálogo de RackClick. La numeración trasera es lógica, no una afirmación de
etiquetas impresas. El orden invertido ilustra una vista exterior esquemática.

El dibujo es propio, técnico y sin escala CAD garantizada. No contiene fotografías
o logotipos copiados. El PDF y la imagen consultada permanecen privados como
referencia; en el producto sólo se incluye la URL, los hechos y la procedencia.
No se deducen conectores de alimentación, módulos, IDC o PoE no documentados.

## Incorporación controlada

La autoría comercial, los hechos y el lock18 son archivos separados de las cuatro
referencias sintéticas congeladas. El nuevo compilador fija una sola pareja
clave/revisión y verifica los hashes, fuente, dimensiones y componentes antes de
escribir. No importa catálogos de Internet ni admite una opción force.

```powershell
C:/Python312/python.exe -X utf8 -B tools/build_hardware_catalog.py --check
C:/Python312/python.exe -X utf8 -B tools/build_hardware_catalog18.py --check
```

`--write` regenera únicamente sus derivados predeterminados: registroC#, JSONde
interfaz, migración018, manifiesto y guardMSBuild. No toca bases o instalaciones.
**Una018ya aplicada/publicada no se edita para añadir otro modelo**: el siguiente
conjunto necesitará otra revisión y migración. Los digests son coherencia, no
firmas o autorizaciones para saltarse la revisión independiente.

SQL018 amplía altura/fondo a numeric e inserta/sella el modelo con los triggers17
activos. C# usa decimal. La cuenta de ejecución mantiene sóloSELECTdelcatálogo.
La creación reutiliza la transacción de inventario, permisos, conflicto de
revisión, idempotencia y auditoría. Guarda también la identidad comercial en la
instancia, protegida contra edición genérica; cada instancia recibe UUIDs propios.

La interfaz conserva el diálogo y Click-Click. Cada opción se identifica por
clave/revisión exactas; no hay elección latest. Los nombres de marca/modelo/SKU y
los escritos por el usuario no se traducen. La fuente oficial se ofrece como enlace
opcional; crear/leer el modelo no necesita Internet. Las cuatro referencias v1 y
el alias antiguo que omite la revisión se conservan. Para el modelo comercial,
omitir o cambiar la revisión se rechaza en el servidor.

## Resultado del ensayo

| Foco | Resultado real |
|---|---|
| Autoría | 43PASS y1omitida por privilegio de symlink; junction de Windows sí probado. |
| Compilación | SDK10.0.401, restore locked/buildRelease sin errores ni advertencias; binlogs privados. |
| Registro/interfaz | 4pruebas C# y817NodePASS; buildfrontend/37adaptadoresPASS. |
| Integridad de build | Cambiar hechos primarios rechaza MSBuild/Node; el dist anterior queda igual. |
| PostgreSQL 17.11/Edge | Actualización17→18 real y bootstrap1→18; dos instancias nuevas,96conectores, identidad/dimensiones, dos cables por ambas caras, edición/recarga/otra cuenta/lector,390 px y reinicio. |
| Regresión v1 | 20comprobacionescompuestas/14negativosHTTPPASS;4U,81conectores del conjunto,3cables, rollback y concurrencia de montaje. |
| Revisión distinta | 8focospropiosPASS, con PostgreSQL nuevo y negativos de identidad/revisión/permisos. |

El primer Node falló porque una aserción seguía exigiendo un único catálogo.
Ahora exige dos y conserva expresamente las cuatro referencias v1. No se quitó
ninguna negativa de revisión o permiso. Fuentes, comandos y límites completos:
`evidence/s1-20261030/hardware-commercial/RESULTADOS.md`.

## Pendiente

Es el primer perfil comercial, no un catálogo completo por fabricante ni una
reproducción fotográfica. Más modelos y variantes, módulos/combos, geometrías
específicas y trazado pasante requieren sus controles y pruebas. El comentarioXML
histórico del registro aún dice synthetic; no describe este conjunto ampliado y
queda como detalle documental menor registrado por el revisor.

Distribución/operadores/Restore18, servicioHTTPS, backup/reinicio nativo y QA de
Wascar siguen pendientes. No copiar sólo esta DLL a la instalación actual.
Instalación10 y su MFA intactos; sin commits, push ni publicación de paquetes.
**Índice de cierre restante:9,76/100**, sin incremento automático ni porcentaje
global nuevo. No se acredita todo C-HW-03/C-HW-06 por un modelo.


## 30.10.2026 · Trasera específica añadida

La trasera genérica anterior queda como historia del lote. Rige [la trasera plana interactiva](TRASERA-INTERACTIVA-STARTECH-LOTE01.md), referenciada en imagen comparativa de proveedor del SKU exacto, contrastando conteo/tipo con PDFoficial. Conserva24UUID/Click-Click y ordenlógico24→1, con números/etiquetasfuera de carcasa. Fuentevisualnoautenticadafabricante; aceptaciónestética pendiente. Frontalintacto, QA138planned y capturas vigentes en [VER-TRASERA-INTERACTIVA-01.html](../VER-TRASERA-INTERACTIVA-01.html).
