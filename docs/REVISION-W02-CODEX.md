# W-02 · revisión de preparación · Codex · 25.10.2026

**Adenda vigente · 25.10.2026:** [revisión de correcciones](REVISION-W02-CORRECCIONES-CODEX.md). R2 cerrado e inventario R1 corregido; R1b entre verificación/lanzamiento, acceso postboot y agregación de fallos pendientes. Sin ensayo VM ni crédito. El dictamen siguiente se conserva como revisión histórica de la primera versión.


**Dictamen: preparación revisada; corregir el auxiliar y el procedimiento antes de usar Execute en la VM.** No se ha ensayado una instalación. W-02.01–05 permanecen pendientes, con **0 de 2,50 puntos**. La edición 07 congelada conserva sus bytes y el cierre W-01; los defectos siguientes pertenecen al auxiliar nuevo W-02.

## Hallazgos comprobados

### R1 · P2 · el directorio del envoltorio no queda vinculado al ZIP oficial

En [Invoke-W02TrialPlan.ps1](../tools/windows/w02/Invoke-W02TrialPlan.ps1), función `Invoke-W02Execute`, líneas 135–145 de la versión recibida, se validan nombres, tamaños y hashes contra el `PAQUETE.json` del propio directorio. Check verifica por separado el ZIP oficial, pero no demuestra que ese directorio contenga sus bytes.

El foco nativo acepta el original y rechaza modificar sólo INICIAR. Sin embargo, acepta modificar INICIAR y actualizar también su fila en PAQUETE; igualmente acepta un archivo extra si se declara en ese manifiesto. La modificación fue un comentario inocuo y **nunca se ejecutó**. Esto demuestra aceptación por la comprobación previa; no demuestra ejecución de código modificado en una VM.

**Corrección:** obtener el inventario confiable del ZIP oficial ya fijado y comprobar su identidad con PAQUETE y todos los miembros extraídos; alternativamente fijar también el digest del PAQUETE auténtico. Conservar controles de rutas, ancestros/reparse y extras, y la vinculación hasta el lanzamiento. Añadir negativos para alteración coordinada de archivo/manifiesto y extra declarado. No basta volver a calcular hashes contra el manifiesto mutable.

- Envoltorio oficial: `3ca223230fc5ea1ab1e2ce7e40c9b7ca222ef65e4735412cb3fdb7cfd19ddca1`.
- PAQUETE auténtico dentro de ese ZIP: `bca8e213acca4dd568140d8b769d5ad8a4ef6f1b06ee52f6a6cff820a5de4b13`.

### R2 · P2 · un informe local afirma la validación del plan

Las líneas 128–131 comprueban status, equipo y digest declarados por `plan-report.json`. El foco rechaza la ausencia del informe, pero acepta una hoja JSON sintácticamente válida e inválida para el esquema (`mode=INVALID`, puerto cero y campos insuficientes) si se fabrica un informe coincidente. Execute no vuelve a validar el plan en esa compuerta.

**Corrección:** antes del lanzamiento, leer de nuevo la hoja y validarla con el validador oficial fijado; comprobar puertos y valores desde ese plan validado. Conservar el informe como evidencia, sin tratarlo como autoridad. Un informe fabricado con el hash correcto debe seguir rechazando una hoja inválida. El foco **no demuestra** que el instalador acepte ajustes inválidos: la GUI genera y valida su propio plan, separado de la hoja (H2).

## Ajustes del procedimiento

1. **Reinicio (§5.5 y criterio de parada):** `awaiting_reboot`/exit 3 requiere reiniciar, reabrir el instalador y pulsar **Verificar instalación**. No exigir reanudación automática ni declararla fallida por no producirse.
2. **Identificador (§4):** comparar los 14 campos restantes, incluidos schemaVersion y los 13 valores configurables. La GUI genera su propio UUID; registrar ese UUID real aparte, sin exigir igualdad con el identificador de la hoja.
3. **Restore (§6.4):** VM B tiene IP/publicHost propios. Repetir también reinicio, verificación manual y evidencia de §5.5–5.7, además de §5.1–5.4.
4. **Exportación (§6.2):** indicar carpeta NTFS local elegida por el operador y comprobar `export_complete`.
5. **Sellado:** la evidencia de Claude declara `0bc555ce…` para el procedimiento; la versión recibida mide `b82c097af8d7ee2e10e62940885601ccf32c7d7bba34d41371a7a5543f8617f7`. Conservar el registro anterior y añadir corrección con el hash nuevo tras editar.

La [revisión distinta del procedimiento](../evidence/s1-20261025/w02-vm-limpia-07-codex/REVISION-PROCEDIMIENTO.md) detalla referencias, pins y límites. Su autor no repitió el foco nativo de Codex; revisó el script y su resultado.

## Decisiones sobre H1–H4

- **H1:** corregir el diagnóstico estructurado de rutas inválidas, conservando rechazo antes de mutaciones y negativos. Puede prepararse en fuente para la siguiente edición pertinente; por sí solo no impide un ensayo 07 con entradas válidas. No modificar el ZIP 07 congelado.
- **H2:** mantener explícita la comparación manual del plan de la GUI y la hoja; R2 protege el auxiliar, no implementa transferencia automática de ajustes al instalador.
- **H3:** documentar ahora las etiquetas históricas 05. Parametrizarlas al preparar otra edición sustantiva; si cambian bytes del paquete, será una edición nueva. No regenerar 07 sólo para cambiar títulos.
- **H4:** conservar exclusiones de LEAO y la allowlist. Son controles adicionales y no sustituyen comprobaciones del host real. No se ha levantado ninguna exclusión.

## Pruebas, atribución y siguiente paso

Codex repitió las **9 pruebas estáticas: 9 PASS, sin omisiones**. Pasan pese a R1/R2 y no acreditan esas propiedades. Check nativo en LEAO terminó con el rechazo esperado `os_not_server_2025`; no se invocó Execute. El foco usa dos fragmentos exactos de verificación y `Get-W02Sha` extraídos por AST de la versión recibida: no llama a Check, VerifyOnly ni INICIAR. Su exit 0 confirma la reproducción de los defectos, no una aprobación de producto.

Fuentes recibidas y resultados: [cierre reproducible](../evidence/s1-20261025/w02-vm-limpia-07-codex/CIERRE.md). No se repiten como propias las pruebas que Claude declaró. No hay instalación, VM, QA, SQL, cambios de servicios/cuentas/red ni commits.

Claude corrige auxiliar/documentos y entrega sus pruebas semánticas para revisión. Después corresponde el ensayo aislado New/Restore en Windows Server 2025 limpio, no DC, con reinicio y evidencia propia por VM. Windows 11 como host y los rechazos de compatibilidad/DC siguen sin acreditar.

**Métrica:** `RC-CIERRE-20261025-v1`, cierre del pendiente **25/7 = 3,57/100**, 8/280 subpasos y 1/50 resultados ponderados completos. Delta de esta revisión: cero. No es porcentaje global del producto ni recuperación del antiguo 78 %.
