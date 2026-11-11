# Verificación posterior al reinicio · estado registrado y comprobación actual

25.10.2026. **Corregido en fuentes de desarrollo y revisado; todavía no incorporado a un instalador nuevo ni ensayado en la VM.**

El resultado del proceso original de instalación termina en `awaiting_reboot`, salida 3. Después del reinicio, otro proceso publica `postboot-verification.json`. El informe exportado perdía el identificador y las fechas de ese segundo documento; el panel pedía reiniciar de nuevo al reabrirse. Es un defecto de presentación y conciliación de fases, no prueba de que el servicio no arrancara.

La corrección conserva `result.json`, su salida original y el recibo de instalación. El informe añade `installationState`, con la procedencia y hashes de los documentos protegidos. La verificación registrada debe coincidir con el UUID y el arranque real; exige tipos estrictos y fechas UTC coherentes. Un documento ausente, malformado, de otro UUID, de otro arranque o un último resultado negativo no recupera un verde anterior. No afirma salud actual ni adopción del producto.

Al reabrir el panel, la barra queda en 95 y el texto distingue un reinicio ya verificado de un registro antiguo o pendiente. El 100 exige una comprobación nueva: salida nativa cero, resultado válido del mismo UUID y arranque, y fecha de comprobación posterior al inicio de esa llamada. Si no puede iniciarse el proceso, se retira el 100 anterior inmediatamente.

Archivos de producto:

- `RackClick.Setup.Lifecycle.ps1`: política pura de fechas y estado registrado.
- `RackClick.Setup.Diagnostics.ps1`: metadatos tipados y conciliación de los archivos protegidos.
- `Show-RackClickInstalledServer.ps1`: mensajes al reabrir, comprobación nueva y retirada del progreso anterior.
- `Collect-RackClickInstallReport.ps1`: conserva la proyección en el documento principal del ZIP, además de los intentos adicionales.

Pruebas Windows PowerShell 5.1:

- Rojo reproducido antes de editar: el saneador eliminaba `installationId`.
- **45 comprobaciones finales correctas**, con fechas/tipos/UUID, arranques, respuesta anterior a la nueva llamada, lectura de archivos privados y ZIP real. El resultado original conserva sus bytes. En los ensayos de archivos se sustituyen el espacio de nombres protegido, la identidad administrativa esperada, la vinculación de instancia privada no disponible y CIM; lector, ACL de los archivos, saneador, colector y exportación permanecen reales.
- Regresión pertinente: **20 diagnóstico, 36 panel y 20 informe automático**, todos correctos.
- Revisión independiente: siete controles propios; uno reprodujo el 100 residual ante fallo de inicio. Tras corregirlo, siete correctos. No sumar esos controles como ejecuciones del autor.

[Evidencia, hashes y límites](../evidence/s1-20261025/postboot-state-codex/CIERRE.md), [revisión independiente](../evidence/s1-20261025/postboot-state-codex/REVISION.md). No se ejecutaron instalación, reinicio real, servicio, HTTPS o tareas programadas en este bloque. Sin C#, SQL, MFA, builds o modificación de VM.

QA-120 añadido como **planned**, con ubicación del botón y pasos para Wascar; 119 casos anteriores y metadatos de compilaciones conservados. Guías regeneradas; sus resultados personales no se modifican. ZIP 07 sigue congelado y no contiene esta corrección. La candidata nueva y el ensayo en C siguen pendientes, junto con las correcciones del auxiliar W02-R3 de Claude.

**Delta 0:** cierre del trabajo restante 4,79/100; W-02 0,50/2,50. Esta corrección no completa por sí sola el recorrido de instalación ni la aceptación final.
