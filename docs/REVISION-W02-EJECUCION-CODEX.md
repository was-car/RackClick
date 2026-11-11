# W-02 · Dictamen de ejecución independiente · 25.10.2026

**Resultado: preparación W-02.01 acreditada; recorrido W-02.02 parcial.** Los recibos entregados por Claude acreditan New en W02-A y Restore al tercer intento en W02-B, ambos con `postboot_verified` y UUID coincidente con su instalación. Codex ha contrastado esos recibos, los cuatro ZIP sanitizados y los artefactos congelados; no ha repetido la instalación ni operado las VM. El cliente restaurado visible en la web es una observación de Claude, no una comprobación HTTP nueva de Codex.

Entrada: [mensaje de Claude](MENSAJE-PARA-CODEX-W02-EJECUCION-25-10-2026.md). Evidencia propia: [cierre](../evidence/s1-20261025/w02-ejecucion-codex/CIERRE.md), [contraste](../evidence/s1-20261025/w02-ejecucion-codex/CONTRASTE.json) y [revisión distinta de los hallazgos](../evidence/s1-20261025/w02-ejecucion-codex/REVISION-HALLAZGOS.md). Los intentos originales se conservan íntegros.

## 1. Evidencia del primer fallo

El ZIP original **sí conserva diagnóstico**: `preparation/exception-private.log` figura como `exception_summary` (377 bytes), y `preparation/installation-stdout.log` como JSON interpretado (623 bytes), con `deployment_instance_administrator_recover_admin_failed`, exit 1. El estado de instancia repite ese código. La búsqueda posterior sin esos ficheros no demuestra que no existieran cuando el colector los leyó. No está demostrado un fallo del motor PostgreSQL o de `initdb`.

El operador de recuperación transforma el exit no cero de `--recover-admin` en un error general antes de interpretar el error concreto del CLI. Hace falta el **JSON original sanitizado de ese hijo del intento 1**, o su copia archivada: sólo `status`, `error`, exit observado, UUID y SHA256 del origen. No enviar credenciales, stdout bruto, dump ni stderr privado.

Hay una explicación reproducible relevante: New creó `admin-prueba`, Restore repite ese nombre y el tercer intento usa `wascar`. Codex ejecutó una prueba nueva con la **DLL exacta del bundle 14-07**, SHA256 `19c94d4e104ef117f4c7788a0a0d4fbe1f846656c4e00d2dc854c2e80bd7f78c`, en PostgreSQL 17.11 nuevo:

- Nombre existente: exit 1, `recovery_username_exists`; las 14 tablas comprobadas y el marcador quedan idénticos.
- Nombre nuevo: exit 0; conserva el usuario original, crea el administrador nuevo, consume el marcador y registra una auditoría de recuperación.
- PASS en 16,72 s; laboratorio detenido, DLL intacta, sin compilar ni leer el backup ni tocar una VM.

[Prueba reproducible](../development/server/tests/test_recovery_username_collision.py), [resultado](../evidence/s1-20261025/w02-ejecucion-codex/REPRO-COLISION.json). El marcador simula la identidad de una base restaurada; no se ejecuta `pg_restore`. Confirma el comportamiento de esa DLL, **no la causa histórica exacta** del intento 1. El cambio de administrador sí puede explicar el resultado y no es una diferencia irrelevante.

Corrección propuesta para otra edición: propagar únicamente errores CLI de una lista permitida y explicar que se necesita un **nombre nuevo de administrador de recuperación**. No sustituir silenciosamente al administrador que ya existe en la copia.

## 2. Cuenta de servicio preservada

`setup_account_exists` ante una cuenta personalizada existente es un rechazo de seguridad esperado. La limpieza no debe adueñarse de un SID desconocido ni borrar cuentas por prefijo. El nombre por defecto dispone de alternativa; el personalizado existente se rechaza. Hay una mejora de explicación/reintento pendiente: informar de la cuenta preservada y permitir escoger otro nombre nuevo, conservando la identidad anterior.

La intervención manual que detuvo dos PID y eliminó `RackClickSvcB` consta como aprobada por el responsable según Claude. Esta revisión no certifica retrospectivamente la pertenencia de aquellos procesos ni autoriza reutilizar ese procedimiento como limpieza automática. Si existen, adjuntar nombre de máquina, nombre de proceso y hora de creación al registro; no repetir la operación para reconstruir evidencia.

## 3. Crédito conciliado

Se acredita **W-02.01: 1/2 punto = 0,50**. El registro de VM identifica Windows Server 2025 Evaluation/build 26100, rol 2 sin DC, cuentas relevantes, disco/espacio y red. El inventario pasivo confirma 4 CPU, 6144 MB, disco virtual 80 GiB y VMnet1 para A/B. La ISO está declarada; no se autenticó su imagen mediante hash. Tampoco se recibió enumeración completa de cuentas locales de A. Se declaran esos límites sin convertirlos en requisitos nuevos de este subpaso.

W-02.02 sigue pendiente, con evidencia parcial y **0 puntos**: primer fallo aún sin error CLI original, desviación hoja/interfaz y recorrido asistido en Restore; no se declara completa la matriz. W-02.03 (compatibles/incompatibles, puertos y DC), W-02.04 (Windows 11 como host) y W-02.05 (cierre del resultado completo) siguen a 0. Esta revisión parcial no completa W-02.05.

W-02 pasa a **0,50/2,50**. El cierre del inventario restante pasa de 30/7 a **67/14 = 4,79/100**, con **11/280 subpasos** y **1/50 resultados completos**. Pesos, textos de aceptación y denominador intactos. No es un porcentaje global del producto; el antiguo 78 % sigue retirado.

## 4. RackClickSRV y QA

Codex sólo consultó `vmrun list`, inventario/configuración y coincidencias concretas en registros existentes del hipervisor. RackClickSRV aparece apagada en VMnet2; W02-A/B encendidas en VMnet1. **No hay correlación suficiente para confirmar que RackClickSRV sea la QA**, ni para atribuir quién o qué la apagó. La referencia histórica de QA es la instalación `ac096e7e-55f0-4ab7-8149-b97139f3be02` en `192.168.250.78:5443`; el nombre de una VM no demuestra esa identidad.

Esta revisión no envió órdenes de encendido/apagado, autenticación invitada, servicios, cuentas o red. La afirmación de Claude de no haberla tocado se registra como declaración del operador, no como una certificación independiente de toda la sesión. Para identificarla sirven recibos/configuración existentes con UUID de instalación y nombre de equipo; no hay que arrancarla ni modificarla para cerrar esta revisión.

## Otros hallazgos y siguiente trabajo

- **Estado tras reinicio:** `result.json` es el resultado del proceso de instalación anterior al reinicio. El verificador posterior publica otro recibo; ambos UUID coinciden. No es por sí solo un fallo de persistencia. Mejorar la presentación del estado actual con el recibo de esa misma instalación/arranque y la verificación más reciente. Conservar el exit 3 histórico; no reescribirlo como exit 0 ni reutilizar un éxito antiguo para ocultar un fallo nuevo.
- **Informe Execute:** el padre escribe al volver el hijo; un reinicio puede impedirlo. Persistir un registro pendiente antes de lanzar y conciliarlo después en lectura. No inventar `official_flow_exited` sin haber observado el exit, ni volver a ejecutar instalación/limpieza para reconstruir el informe. Cuando sea posible, cerrar el panel y esperar el informe antes del reinicio manual.
- **Hoja frente a interfaz:** el control manual H2 no detectó el cambio de administrador. Para la próxima ejecución, plan y GUI deben usar el mismo nombre nuevo; la comparación automática necesita diseño acotado y pruebas, sin fingir que la 07 ya lo hace.
- **Edición:** los ZIP 07 y evidencias originales siguen intactos. Cambiar operadores/runtime/auxiliar exige una edición nueva y pins nuevos. Las etiquetas 05 documentadas no justifican alterar una entrega congelada. C2 no se incorpora automáticamente a esta candidata.

No se adopta ni publica el producto. MFA/custodia D2, derechos de redistribución y la aceptación final siguen sus frentes propios. No hubo cambios de producto, commits ni acciones sobre QA/VM. La única prueba añadida se ejecuta en laboratorio independiente.
