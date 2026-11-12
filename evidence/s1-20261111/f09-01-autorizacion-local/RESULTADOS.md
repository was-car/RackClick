# F-09.01 · autorización local de emergencia, paso29

11.11.2026. Cerrado técnicamente con dictamen independiente favorable sólo a F-09.01. D/E, VM, instalaciones, cuentas y servicios instalados no se tocaron. Sin commits, push o publicación.

## Investigación antes de implementar

[Plan](../../../docs/PLAN-F0901-AUTORIZACION-EMERGENCIA.md) escrito antes de modificar producto; D2 confirmado y códigos/login ya revisados se reutilizan. Se inspeccionaron Program, RecoveryAdministrator, MfaMaintenanceCommand/MfaKeyStoreInitCommand, F0801–.05 y la especificación de pérdida total. Se conservan los operadores de Restore y mantenimiento; no se amplían sus efectos para simular una emergencia. Referencias oficiales de Microsoft y APIs/versión consultadas están en el plan. No bibliotecas, versiones, locks, SQL o algoritmo criptográfico nuevos.

## Cambio acotado

Nuevo `MfaEmergencyRecoveryCommand.cs` y rama temprana/exclusión de modos en `Program.cs`. No se modifica autenticación web, proveedor, factores, DB, GUI o archivos del instalador. La consulta nativa exige Windows sin suplantación y SYSTEM o Administradores efectivos elevados; no modifica token ni solicita privilegios. La decisión pura interna no se toma del exterior.

La etapa posterior todavía se rechaza con `mfa_emergency_transition_unavailable`, salida1 y cero operaciones/sesiones. No hay un modo de recuperación funcional que anunciar ni un éxito administrativo ficticio. Preparar material y transacción se reservan para los próximos checkpoints del mismo resultado.

## Pruebas del coordinador

| Ejecución | Resultado observado |
|---|---|
| Referencia sin rama nueva |10/10 fallan; childexit1 de dotnet test. Es el rojo por ausencia de la funcionalidad, no una vulnerabilidad demostrada en Restore |
| Build final |SDK10.0.401/Release,0errores/0advertencias, restorelocked sin cambios de dependencias |
| Compuerta final |76/76 PASS:64 filas de política simulada,2 contrastes nativos identidad/claims/impersonación y10 procesos CLI; sin omitidas |
| HTTP/PG actual |3/3 PASS: cuatro rutas anónimas401/global404 sin mutar snapshot y dos casos F0802 de API inaccesible hasta nuevo factor; PG17.11, esquema46, rol runtime separado |
| Regresión de comandos/composición |74/74 PASS, sin omitidas; operadores anteriores y composición/fallo cerrado del proveedor |
| Host normal afectado |7/7 PASS en MfaWindowsHostHttpTests, PG17.11 nuevo; no se convierten en pruebas de SID/servicio instalados |
| Mutación privada |Permitir usuario estándar:65 casos,60PASS/5FAIL, exit1. Se restaura fuente y ambas DLL por SHA256; después el foco final76/76PASS usa esos mismos bytes |

No se suman repeticiones como funciones o puntos. [FOCOS.json](FOCOS.json) conserva nombres/counters/pines; [FUENTES.json](FUENTES.json) fija el manifiesto acotado y [MUTACION.json](MUTACION.json) la sensibilidad. Rawlogs/TRX/binlogs/conexiones permanecen privados bajo `.local/`.

## Incidencias de preparación conservadas

La primera copia privada no incluía los archivos de catálogo/frontend que valida MSBuild; tras copiarlos faltaba el auxiliar de tools pinado. Dos builds fallaron cerrados por esos requisitos. Se copiaron los insumos invariantes de la referencia anterior, sin suprimir verificadores. El primer build verde falló por no pasar CancellationToken en cuatro llamadas del test HTTP nuevo; se corrigió sólo la prueba. Las tres salidas/binlogs se conservan y no se presentan como regresiones del producto.

El rojo corresponde a la revisión inicial de los diez tests de proceso. Después se fortaleció la comparación con el token padre para no aceptar indistintamente «no autorizado» y «transición no disponible»; no se atribuye al hash final una fase roja que no ejecutó esa aserción fortalecida. La mutación final sí prueba su sensibilidad: el env falso no puede convertir el token estándar real en autoridad.

## Reproducción y revisión

Comandos privados: `.local/f0901-4eef2d0f/build_and_test.py red`, `green`, `final`, `http`, `regression`, `host`; MSBuild siempre con binlog único, Release y locks existentes. Final/http/regression/host usan `--no-build --no-restore` sobre las DLL fijadas. La mutación privada fue secuencial y restauró exactamente esas DLL antes de revisión. Las bases nuevas se cierran en finally; no se reutiliza la instalación de D/E.

[Matriz](MATRIZ-CRITERIO.md) · [ficha29](../../../docs/PASO-029-AUTORIZACION-LOCAL-EMERGENCIA-MFA.md). El dictamen independiente registra sus propias ejecuciones y sondas, sin atribuirse los resultados de esta tabla.

## Límites

El token real disponible no es SYSTEM ni administrador elevado. No se ejecutó un positivo elevado/SYSTEM real ni se alteraron cuentas/privilegios para obtenerlo; la tabla simula esas decisiones. La prueba nativa de suplantación es del propio token y verifica su restauración. Las sondas HTTP no son una exploración de todas las rutas posibles. La composición Windows existente usa sus fixtures, sin afirmar SID efectivo o DPAPI de D/E.

Sin anillo nuevo, retiro de factores, auditoría de pérdida o recuperación total operativa. Todos los hitos completos F-09 y sus otros checkpoints, integración y aceptación de Wascar siguen pendientes. La observación abierta de prueba/GUI Edge del paso28 se conserva sin repetición ni declaración de arreglo. QA175 y sus resultados personales se mantienen.


## Revisión y conciliación

[Dictamen](review/DICTAMEN.md): revisor distinto79/79 y8sondas adicionales PASS en clúster propio, sin recompilar; tabla simulada/identidad nativa y límites separados. Sólo F-09.01 suma1/2:2069/84→2111/84=25,130952…/100 del cierre restante. Se preservan los otros cuatro checkpoints y los seis hitos F-09, sin declarar transición, operación instalada, positivo elevado real o aceptación.
