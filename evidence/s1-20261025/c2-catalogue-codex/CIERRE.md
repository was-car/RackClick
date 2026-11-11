# C2 · catálogo I-04.01

## Resultado y alcance

[Catálogo](../../../docs/C2-CATALOGO-JERARQUIA-25-10-2026.md) de **19 familias y 23 comandos únicos** de jerarquía, racks, equipos y orden. Cada familia identifica control o ausencia de control separado, comando, permiso del servidor, prueba reutilizable y límites. [Versión estructurada](CATALOGO.json).

Se concilia lo existente para evitar rehacer CRUD/lotes. El cierre de I-04.01 es documental; no implica ejecutar ni aprobar todas sus variantes. Los cierres 52, 53, 55–59, 61 y 62 conservan sus entornos/versiones/resultados originales. Leer sus informes y fuentes de pruebas no constituye una repetición actual.

## Comprobaciones realizadas en Windows / LEAO

- Git inspeccionado antes de editar; se preservó el árbol de trabajo ajeno.
- Lectura del despacho actual, controles frontend, permisos y evidencias. Una consulta de exploración acotada devolvió la lista; no editó archivos ni ejecutó suites.
- Comparación documental con Python 3.12: las 19 filas contienen 23 tipos distintos y coinciden con los literales de jerarquía/racks/equipos del despachador, excluyendo `device.editPortGroups`, que pertenece a I-01/I-03. No se crean nuevos comandos. [Resultado de lectura](LECTURA.json).
- Comprobación de enlaces y hashes de las fuentes/catalogo/guías anteriores. El primer control de enlaces usó separadores Windows frente a POSIX; se corrigió la normalización del propio control con `as_posix()`. El diagnóstico se conserva privado; no fue un fallo de producto.
- [Revisión distinta](REVISION-I0401.md) del catálogo y su alcance. Sus comprobaciones se distinguen de las del coordinador; no se declara una revisión funcional de todas las variantes.
- Generador de progreso `tools/progress_report.py --write` y `--check`, comprobación de diferencias, escaneo de secretos y verificación SHA256 registrados al cierre.

**Pruebas funcionales nuevas: cero. Builds: cero.** El cambio sólo documenta funciones existentes; no necesita repetir las suites históricas. No se ejecutaron PostgreSQL, Edge, instaladores, servicios o pruebas de las VM.

## Diferencia encontrada y trabajo pendiente

**I04-GUI-01:** lectura de código detecta que la interfaz añade `inventory.edit` a flujos que el servidor autoriza con `inventory.read` + `inventory.delete`: botones individuales anidados en `canEdit`, apertura por `open` y permiso enviado al diálogo. Se registra sin afirmar reproducción DOM ni corrección. Debe corregirse y probarse con cuentas separadas, revocación, recuperación e intento HTTP directo antes del cierre de I-04.05/06.

I-04.02–07 siguen pendientes, incluidas variantes de U/metadatos/presets, duplicado sin cables/reserved positivo, drag/táctil, borrado, candidata final/segunda cuenta/reinicio y revisión/QA aplicables. No se retira ningún requisito ni se trata una función no ensayada como inexistente.

## Crédito y conservación

Tras el dictamen independiente, sólo I-04.01 recibe su peso fijado **5/14**: cierre del trabajo restante **55/14 → 30/7 puntos**, redondeado **3,93 → 4,29/100**, **10/280 subpasos y 1/50 resultados completos**. [Registro](CREDITO-I0401.json). No es un porcentaje global del producto. Texto, pesos y demás subpasos intactos; I-04 permanece parcial.

Producto, catálogo de 117 casos, guías QA y observaciones de Wascar conservados. Sin commits, push, SQL, compilación, paquetes, instalación, servicios, cuentas, red, QA o VM. W-02 sigue a cargo de Claude; no se incorpora crédito de ensayos aún no recibidos/revisados.

[Fuentes y hashes](FUENTES.json), [controles](CONTROLES.json), [escaneo](ESCANEO.json), [manifiesto final](SHA256SUMS.txt). Siguiente: corregir I04-GUI-01 como foco de borrado; después cerrar variantes pendientes reutilizando las pruebas válidas y ensayar sólo lo afectado en la candidata coordinada.
