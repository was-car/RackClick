# Integración de carcasas · lote 01 · resultado

30.10.2026. **Frontal StarTech C6PANELUTP241UFT integrado y revisado en desarrollo.**
No se instala en la VM ni se habilita QA-138 en la instalación 10.

## Cambio y alcance

Nuevo selector visual por pareja/revisión exacta y cara contrastada; nuevo componente
de carcasa propia negro, orejas y cuatro bloques de seis conectores. Se reutilizan
los botones, UUID, IRPortShape, tooltips y comandos existentes. La trasera y las
revisiones desconocidas siguen genéricas; no se inventan geometrías, interfaces
activas o continuidad interna. Fuentes y decisión previas en INVESTIGACION-PREVIA.md.

Archivos de producto: hardware-shells.ts, HardwareShellFace.jsx,
MountedPhysicalRack.jsx, hardware-words.ts, server.css y el hook de build.mjs,
todos bajo development/frontend. El código adoptado, los catálogos, SQL018 y el
backend no cambian. La DLL18 usada es la anterior, congelada y verificada por SHA.
No se recompila .NET ni se modifica una versión fijada.

El nuevo scroll necesita recalcular cables: la revisión independiente reprodujo
**SHELL-01**, un desfase de 100 px. Se corrigió el hook del renderer adaptado para
escuchar scroll en captura sólo en racks con renderHardware, limpiando el listener
al desmontar. La RC9 adoptada permanece intacta. El mismo foco pasa después,
con códigos de salida rojo1/verde0 y posiciones coincidentes.

## Pruebas ejecutadas por el coordinador

Windows, Python3.12, Node24.21.0/esbuild0.25.10, Edge nativo y PostgreSQL17.11.
Laboratorios nuevos, credenciales generadas localmente, runtime SQL restringido,
sin VM, servicios instalados o bases existentes.

- 21 pruebas Node focales iniciales PASS: selección exacta, topología, revisiones,
  genéricos, inmutabilidad y montaje. Después del cambio de scroll, una regresión
  pertinente de **52 archivos / 822 pruebas Node: 822 PASS, 0 FAIL, 0 omitidas**.
  Son conteos solapados, no 843 pruebas distintas. Se conserva el aviso previo de
  Node MODULE_TYPELESS_PACKAGE_JSON; no se cambia package.json para silenciarlo.
- Build frontend privado: salida0, sin nuevas dependencias. No se modifica el dist
  de la instalación o el compartido del repositorio.
- **Edge + PostgreSQL, ejecución gui-third: PASS.** Bootstrap18 nuevo, dos paneles
  con 96 UUID propios (98 puertos en el cliente contando dos legacy), 24 controles
  frontales por objeto y cuatro bloques de seis. No imágenes remotas/iframes en la
  carcasa. Click-Click guarda dos cables independientes, frontal y trasero.
- La cara trasera es genérica y conserva sus UUID/numeración lógica; cambiar de
  cara no escribe. Enter nativo selecciona un botón libre; a390px el scroll permite
  llegar al24 con puntero real y objetivo de al menos24×24px. Se comprueba en el DOM
  que el comienzo del SVG del cable coincide con el centro del puerto antes y después
  del desplazamiento horizontal.
- Cambio de nombre/notas, incluido texto parecido a HTML, conserva todos los puertos
  y ambos cables sin crear img. Recarga y otra sesión leen el estado idéntico. Lector
  con botón deshabilitado y solicitud API403; tablas/auditoría/revisión intactas.
  Tras reiniciar el servidor de laboratorio se conserva el snapshot completo.
  No se reinició Windows ni se ensayó una instalación.
- El laboratorio y todos sus procesos de servidor quedaron detenidos. Resultados
  sanitizados: RESULTADO-PG-EDGE.json, RESULTADO-NAVEGADOR.json y NODE-RESULT.json.

Comandos de reproducción, con DLL/frontend explícitos y salida privada nueva:

```powershell
.local/node-v24.21.0-win-x64/node.exe --test development/frontend/tests/hardware-shells.test.mjs development/frontend/tests/hardware-commercial.test.mjs development/frontend/tests/hardware-mounting.test.mjs development/frontend/tests/hardware-revisions.test.mjs
# La regresión usa todos los tests/*.test.mjs de development/frontend (52 archivos).
C:/Python312/python.exe -X utf8 -B development/server/tests/test_hardware_shell_gui.py --dll <DLL18 congelada> --frontend <dist privado del lote> --output <carpeta nueva bajo .local>
```

El build se ejecutó con Node build.mjs dentro de la copia privada; no con un build
concurrente sobre obj ni contra QA. CANDIDATA.json y HASHES-FUENTES.json identifican
exactamente los bytes. DIFF-LOTE01.diff se calcula contra la copia de trabajo previa
del lote, no contra HEAD, para no atribuir cambios anteriores a esta integración.

## Intentos conservados y diagnóstico

gui-first y gui-second se detuvieron en la prueba de teclado. La primera usó
keyDown sin texto; la segunda rawKeyDown. La revisión independiente reprodujo que
esas secuencias CDP no emiten click. La tercera usa keyDown con texto CR y keyUp:
keydown/click/keyup confiables llegan al mismo botón. No se cambió producto para
hacer pasar el arnés ni se presenta esto como un defecto del usuario con teclado.
Los tres intentos quedan privados; sólo gui-third acredita el recorrido completo.

La revisión tuvo otro intento de arnés con target de extensión, separado del rojo
válido de scroll. Sus originales y límites están en review/REVISION-INDEPENDIENTE.md.

## Revisión independiente

Revisor distinto del implementador. Dictamen favorable para el foco interno:
30 comprobaciones propias de selector, negativos e inmutabilidad; DOM de fallback
trasero y revisión desconocida con todos los UUID; teclado Enter/Space; reproducción
roja/verde real del scroll; muestra visual de foto, fixture y captura de aplicación.
No ejecutó mis 822 pruebas, PostgreSQL, API o reinicio. Informe y resultados propios
en [review/REVISION-INDEPENDIENTE.md](review/REVISION-INDEPENDIENTE.md).

## Límites, QA y siguiente paso

EN/DE/ES se revisan en diccionarios/Node; el recorrido completo de aplicación se hace
en español, no en todos los idiomas. No prueba cada estado/PoE/tipo de conector,
colorimetría, equipo físico, escala CAD, exportadores, rendimiento masivo, restauración,
servicio Windows o reinicio de Windows. No hay trasera comercial contrastada.

QA138 se amplía con ubicaciones, botones, scroll, teclado y avisos; continúa planned.
Las respuestas de Wascar no se leen ni sobrescriben. Se regenera la guía con el
catálogo habitual y la disponibilidad real. Capturas de inventario sintético y dibujo
propio en VER-INTEGRACION-CARCASAS-01.html, sin fotos del fabricante incorporadas.

Siguiente: otro lote de carcasa/modelo con revisión y topología contrastadas,
manteniendo genéricos para lo desconocido. Distribución/Restore18, candidata completa
y QA de Wascar siguen pendientes. Sin cambios en MFA, instalación10, VM/QA, SQL,
credenciales existentes, limpieza, commits o push. Ledger conservado e **índice de
cierre restante9,76/100**, sin nuevo porcentaje global por contar una carcasa.
