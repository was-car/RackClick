# Revisión independiente — fuente única de hardware

30.10.2026. Revisor `catalog_review`, distinto del implementador. Dictamen
**favorable para este tramo acotado de desarrollo**, con los dos diagnósticos
menores corregidos. No acredita catálogo SQL general, modelos comerciales,
instalador, QA o aceptación de Wascar.

## Alcance y contraste

Leídos `tools/build_hardware_catalog.py`, sus pruebas, los tres archivos de
`development/hardware/`, los derivados C#/JSON/targets, el registro de hardware,
el `.csproj`, la compuerta Node, su llamada en `build.mjs` y el nuevo import de
`hardware-mounting.ts`. La versión anterior del registro se consultó en la
copia `before/` identificada por `.local/hardware-catalog-current.txt`.

Se contrastaron las cuatro definiciones con las constantes anteriores: claves,
revisión v1, U, dimensiones, colores y grupos/etiquetas/prefijos coinciden.
El registro conserva copia inmutable y búsqueda exacta. Los datos de entrada
se convierten en literales, no en instrucciones de un catálogo descargado.
La comprobación de escape de texto es sobre la salida del generador; el revisor
no compiló ese texto sintético en C#.

El target de publicación es cerrado16: el compilador verifica el lock completo
y la proyección contra la referencia congelada antes de escribir derivados.
El manifiesto y las compuertas de build comprueban coherencia de los archivos;
sus hashes **no son firmas ni autorizan por sí mismos otro modelo**. Modificar
deliberadamente código, lock y referencia pertenece al control de fuentes y
requiere otra revisión. No es un cargador de catálogos de terceros en ejecución.

`hardware-reference.json` conserva SHA256
`837cac53424dcf8324fd7dcad2cdc1907c79d21084755c7964b3d33accc4c2b6`;
SQL016 conserva
`c2402ce8741bbb3ab24ecd11e2203263704297dd08330b0111e5e5a3cb89b6e0`.

## Hallazgos y repetición propia

Dos fallos menores de diagnóstico, sin publicación parcial observada:

1. Un entero físico `10**400` lanzaba `OverflowError` al convertirse a float en
   `math.isfinite`. Ahora el rango se comprueba primero y se obtiene
   `catalog_dimensions_invalid`.
2. Un entero JSON de5000dígitos lanzaba el `ValueError` del límite de Python.
   Ahora se traduce a `catalog_json_invalid`; `CatalogError` conserva su código,
   incluidos los duplicados.

Los focos propios pasan de **5 PASS/2 FAIL a7 PASS/0 FAIL**. Se conservan el
comprobador y ambas salidas en
`evidence/s1-20261030/hardware-catalog/review/`. Los otros cinco casos cubren:
clave JSON duplicada mediante escape Unicode; texto con control/sustituto sin
pareja; escape de comillas/barra/emoji; nuevo modelo rechazado conservando los
cuatro derivados existentes; manifiesto con un fichero extra rechazado por
Node real. Las pruebas usan árboles temporales independientes, sin producto
modificado por el revisor.

La primera salida se midió antes de la corrección, sobre el código que el
revisor acababa de leer. No se conservó una copia de ese compilador ni su hash
anterior; no se afirma una referencia histórica reproducible por hash. El foco
final queda identificado con los hashes de la entrega revisada.

## Ejecuciones y límites

Comando propio:

```powershell
C:/Python312/python.exe -X utf8 -B evidence/s1-20261030/hardware-catalog/review/probe_catalog_review.py
```

Python3.12 y Node24.21.0 del equipo Windows. Sin DB, servicios, cuentas, VM,
lectura de secretos ni compilaciones sobre los `obj` del coordinador. El revisor
no ejecutó su regresión PostgreSQL/Edge, el build .NET ni la compuerta MSBuild:
esas ejecuciones pertenecen al coordinador y deben quedar en su evidencia.

La publicación de varios derivados no es una transacción; si se interrumpe,
`--check` y las compuertas deben impedir construir con una combinación obsoleta.
No se acredita durabilidad frente a corte del sistema ni resistencia frente a
un administrador que reescriba el repositorio. El límite de precisión del
contrato actual sigue siendo altura/profundidad enteras. SQL016 y su montaje
siguen cerrados a las cuatro referencias: normalizar tablas/capacidades e
incorporar fabricantes exige el siguiente contrato y migración.

No se incrementa crédito o porcentaje por esta revisión.

## Adenda — referencias de la hoja maestra

Se revisa también la corrección acotada de `tools/build_master_roadmap.py` y
`tools/tests/test_master_roadmap_refs.py`. El requisito de montaje ya apuntaba a
`C-HW-02` y otras ampliaciones declaradas, pero el generador admitía sólo IDs del
ledger para `owner`/`related`; por ello no podía regenerar esa configuración.
Ahora construye un conjunto separado `reference_ids` para esos vínculos. No
modifica el conjunto original `ids` que exige responsables RC10 del ledger ni
la suma de créditos. Los IDs duplicados siguen rechazados tras reunir registros.

Dictamen favorable para esta corrección documental. Foco propio de5
comprobaciones PASS (`review/probe_roadmap_review.py` y
`review/FOCOS-ROADMAP.json`): métrica, resultados base y mapa RC10 idénticos al
usar un responsable de catálogo o de ledger; ampliación duplicada rechazada;
bytes del ledger conservados. El foco calcula en memoria y no regenera archivos.
Las tres pruebas de desconocidos/igualdad del implementador se leyeron, sin
atribuir al revisor esa ejecución. No acredita puntos ni añade resultados
ponderados. No se repitieron catálogo, PostgreSQL, navegador o compilaciones.
