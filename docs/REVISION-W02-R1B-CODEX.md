# W-02 · revisión de la ronda R1b

25.10.2026. Implementación de Claude; revisión y repeticiones nuevas de Codex en Windows/LEAO. [Evidencia](../evidence/s1-20261025/w02-r1b-codex/CIERRE.md), [segunda lectura del procedimiento](../evidence/s1-20261025/w02-r1b-codex/REVISION-PROCEDIMIENTO.md).

**Dictamen: las tres correcciones pedidas quedan conformes dentro del alcance comprobado.** No hay otro ajuste del auxiliar requerido por esta revisión antes del ensayo controlado. Esto autoriza continuar la preparación del ensayo ya solicitado; no acredita instalación ni adopción y no convierte la edición 07 en una entrega aprobada para la VM QA.

1. **R1b cerrado para las carreras probadas.** Los archivos autorizados se abren con FileAccess.Read/FileShare.Read y permanecen retenidos durante ambas llamadas. Se comprueban hashes sobre esos mismos streams; el manifiesto se valida primero. La simulación repetida mantiene los bytes autorizados en ambas llamadas y rechaza escritura, renombrado, borrado y movimiento de carpeta. Un foco propio, con las tres funciones exactas extraídas por AST, confirma lectura paralela, escritura rechazada con IOException/código nativo 32, escritura permitida tras Dispose y liberación también al fallar la validación. No ejecuta el entrypoint.
2. **Reapertura corregida.** §5.5 identifica el acceso `RackClick-VERIFICAR-05-<8 caracteres>.cmd` creado por ESTA ejecución de la edición 07. Se abre la instalación existente y se comprueba con **Verificar instalacion**. No se repiten Execute, INICIAR ni limpieza; si falta el acceso, se para y se recoge informe. `05` es la etiqueta histórica documentada.
3. **Batería corregida.** Cada corrida usa una salida nueva y agrega los fallos. Repetición final **24 comprobaciones OK / BATERIA_OK / exit 0**. Negativo deliberado: código esperado incorrecto más marcador sintético de lanzamiento, **exit 1 / BATERIA_FALLIDA**. El marcador no es un proceso lanzado. Las **21 estáticas** también pasan, tanto directamente como dentro de la batería; son repeticiones del mismo conjunto, no 42 pruebas distintas.

La primera corrida propia de Bash falló con exit1 por el entorno heredado de módulos de PowerShell 7: el hijo Windows PowerShell 5.1 no encontraba Get-FileHash. Se conservó esa salida. Se repitió retirando únicamente `PSModulePath` del entorno de ese proceso para que Windows PowerShell inicializara su ruta estándar; sin cambiar configuración del equipo, fuentes o política. Esta condición se registra para repetir desde Bash, no como defecto demostrado del instalador. La batería falló correctamente en vez de declarar éxito.

La prueba de Claude que primero devolvía hash_mismatch en vez de package_mismatch fue un rechazo correcto con clasificación distinta; se conserva como evidencia suya, no como ejecución de Codex. Los seis hashes recibidos coinciden. Los cuatro ZIP oficiales 07 permanecen intactos.

## Límite de aceptación y siguiente paso

El lanzador de la batería es un proceso PowerShell simulado que lee el archivo; **no se ejecutó INICIAR real ni su VerifyOnly**, que crea un área privada. Tampoco instalación, servicios, New/Restore, exportación, informe, reapertura real del Escritorio o reinicio Windows. Se mantiene el ensayo de compatibilidad del envoltorio con los archivos retenidos como primera comprobación real en la VM; si falla, parar y recoger salida, sin quitar el bloqueo para avanzar.

H1 oficial queda para una edición posterior pertinente; H2 se comprueba manualmente; H3 está documentado y no exige regenerar 07 sólo por etiquetas. No se modificaron helper, pruebas, procedimiento, producto ni paquetes. No hay cambios en QA/VM, SQL, servicios/cuentas/red ni commits.

**W-02.01–05 siguen pendientes, 0/2,50 puntos.** Cierre del pendiente **3,57/100**, 8/280 subpasos y 1/50 resultados completos, delta0 y alcance/pesos intactos. No porcentaje global del producto. El siguiente avance de W-02 necesita evidencia del técnico en Windows Server 2025 limpio no DC, con New, acceso tras reinicio y Restore en VM B, siguiendo el procedimiento existente.
