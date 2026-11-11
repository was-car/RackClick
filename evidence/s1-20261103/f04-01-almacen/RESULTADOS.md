# Paso 11 · F-04.01 · almacén MFA inicial

03.11.2026. Desarrollo y pruebas Windows aislados. No se operaron D, E, otras VM, servicios reales, bases de datos ni credenciales del usuario. Sin commits, push, paquete nuevo o despliegue.

## Evidencia reutilizada

[Investigación previa](INVESTIGACION-PREVIA.md) y [contraste del criterio](CONTRASTE-CRITERIO.md) identifican las piezas existentes, hashes y límites. Un agente de exploración contrastó la cadena instalador → `Initialize-SetupMfaStore` → `--mfa-keys-init` → escritor, y los ensayos C10/D11/D45. No se volvieron a ejecutar ni se atribuye crédito adicional a F-04.03.

La ubicación de MFA es propia de `security/<installationId>/mfa-keys`, fuera de `management` y PostgreSQL. El proceso elevado conserva confianza fija de SYSTEM/Administradores; el servicio no crea material al arrancar. No se amplían las ACL de management.

## Cambios y prueba del defecto

La referencia del escritor era `ebbac2efc8603d5dbecf057ba645706f5ae98d5375b8597555979add95b09041`. Creaba con atributos de seguridad nulos y protegía después. Además, una excepción E/S tras renombrar podía confundirse con colisión y declarar rutas antiguas de staging.

Se suministra descriptor protegido a `CreateDirectoryW` y `CreateFileW`/`CREATE_NEW`; no se hace SetAcl posterior. Se mantienen exclusividad, confianza, identidad y preservación de objetos ajenos. Los archivos se vacían al disco sobre su identificador antes de publicar el staging completo. Tras renombrar se conserva el conjunto publicado ante fallo, con sus rutas reales; no se limpia parcialmente ni se devuelve éxito.

- Rojo instrumental: **5 fallos y 3 controles válidos** sobre la referencia con únicamente puntos de observación. Tres negativos son de DACL al nacimiento; dos, de postpublicación. Un intento anterior sin compilar no cuenta como prueba del defecto.
- Verde: **8/8**; regresión afectada definitiva: **195/195**, sin omitidas. Las ocho nuevas están incluidas en 195; no se suman otra vez.
- SDK **10.0.401**, Windows, ACL y DPAPI reales en TEMP sintético. Build sin errores ni advertencias. Binlogs, TRX y copias de compilación permanecen privados.
- [Entrega de implementación, comandos y límites](implementacion/RESULTADOS.md), [resultados sanitizados](implementacion/RESULTADOS-SANITIZADOS.json), [hashes](implementacion/HASHES.json), [diff](implementacion/DIFF-WRITER.diff).

## Comprobaciones auxiliares

La batería del operador ejecutó inicialmente 18 casos: 15 pasaron y 3 fallaron antes de comprobar el entorno porque su fixture no importaba el auxiliar SQL existente. Se añadió sólo ese import, sin relajar aserciones o cambiar los lanzadores. Resultado final: 14 perfiles ya pasados y 4 casos de wiring pasados. [Registro](PRUEBAS-OPERADOR.json), [diff](DIFF-fixture-wiring.patch).

Se corrigió también el pie del generador de la hoja maestra: tenía la constante histórica «23 acreditados». Ahora usa el mismo registro de métricas que el resto de la hoja. Un negativo que compara el pie con el ledger actual y con un checkpoint reabierto falla antes y pasa después; la batería de referencias pasa **4/4**. No cambia pesos, criterios ni resultados de producto.

## Alcance de la revisión

[Revisión independiente](REVISION-INDEPENDIENTE.md): persona/agente distinto del implementador, fuentes fijadas y comprobaciones efectivamente ejecutadas. Contrasta descriptor al nacimiento, publicación del conjunto, colisiones, fallo anterior/posterior y preservación. La evidencia anterior por sí sola no bastaba para cerrar el hueco.

No se afirma que D contenga el escritor corregido. La instalación y su material MFA se conservan. El positivo de inicialización nativa ya existente acredita la cadena del operador; la corrección se prueba ahora en el mismo escritor mediante laboratorio Windows. La incorporación a una nueva candidata completa y su ensayo siguen sus propios pasos Windows.

## Límites que permanecen

- Publicación del almacén inicial en el espacio de nombres; no durabilidad universal de la entrada de directorio, pérdida de energía ni atomicidad disco/DB.
- Los fixtures declaran al usuario del laboratorio como confiable y emplean un lector sintético. No sustituyen el ensayo de otros tokens/SID efectivo de F-04.02.
- Continúan los límites entre creación de directorio y captura de identidad, y entre validación de padre y renombrado absoluto, frente a un principal confiable comprometido.
- Rotación, sobres portables, restauración y recuperación de emergencia mantienen sus criterios separados. La política y la exención global no cambian.

La revisión independiente resultó favorable, con **16 pruebas .NET y 8 Python** propias/repetidas efectivamente ejecutadas por el revisor. Se acredita sólo F-04.01: **+5/8**, de 2479/168 a 323/21 = **15,38/100 del cierre restante**. No es porcentaje global nuevo del producto. Quedan 34 checkpoints cerrados y 246 sin cierre, conservando 53 resultados, 280 checkpoints y 268 números.

La [conciliación contable](CONCILIACION-PLAN.json) comprueba huella congelada idéntica y ausencia de cambios en otras tareas/checkpoints. F-04.02/.04 permanecen pendientes y F-04.03 no se vuelve a acreditar. No se reduce el criterio ni se acredita la tarea F-04 completa por este subpaso.
