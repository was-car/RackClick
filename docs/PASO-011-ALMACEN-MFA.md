# Paso 11 · almacén MFA separado y protegido desde su creación

03.11.2026 · F-04.01 cerrado técnicamente en fuentes y revisado. D se conserva, sin actualización ni operaciones en su VM.

Se reutilizaron el proveedor Windows, la inicialización elevada del instalador y los ensayos reales de C10/D11. El almacén sigue separado de `management` y PostgreSQL. No se ha creado otro proveedor ni cambiado la política de 45 días.

Se corrigieron dos huecos del escritor:

- Las carpetas y archivos nuevos reciben su DACL protegida en la propia llamada de creación. Se elimina el cambio posterior de ACL por ruta; los destinos existentes no se adoptan ni sobrescriben.
- El anillo y sus claves se preparan, escriben y validan antes de publicar el conjunto mediante un único renombrado. Si una verificación posterior falla, se conserva el almacén completo y se declara su ruta final; el reintento lo rechaza sin alterar sus bytes.

Las pruebas nuevas detectan los defectos en la referencia anterior. La regresión afectada del escritor, recuperación, lector/proveedor, anillo e inicialización pasa **195/195**, sin omitidas, en Windows con SDK 10.0.401. Se comprueban también los perfiles y el entorno del operador. La revisión independiente y sus focos propios se registran en la evidencia enlazada.

El binario instalado en D continúa tal como estaba. No tienes que ejecutar comandos, reinstalar ni cambiar su MFA. La corrección de fuentes se incluirá en la siguiente candidata completa que corresponda; no se copian DLL sueltas.

El alcance es la publicación inicial del almacén. No se atribuye al renombrado durabilidad frente a pérdida eléctrica ni una transacción disco/DB. El **paso 12, F-04.02**, conserva las comprobaciones pendientes de otros tokens, SID efectivo, padres, herencia y reparse; F-04 completo y su revisión final permanecen abiertos.

[Resultados y alcance](../evidence/s1-20261103/f04-01-almacen/RESULTADOS.md) · [Revisión independiente](../evidence/s1-20261103/f04-01-almacen/REVISION-INDEPENDIENTE.md).

Se acredita sólo **5/8 de punto**: índice **2479/168 → 323/21 = 15,38/100 del cierre restante**. Son 34 subpasos cerrados y 246 sin cierre; 53 resultados, 280 checkpoints y 268 números estables. No es un nuevo porcentaje global ni adopción del producto.
