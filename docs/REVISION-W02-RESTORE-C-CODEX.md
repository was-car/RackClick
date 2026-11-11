# Restore C · revisión de Codex · 25.10.2026

**Adenda vigente · 25.10.2026:** Wascar confirma funcionamiento y pide cerrar. El ensayo operativo Restore C queda **cerrado con observaciones**. Retirado el encargo adicional sobre el colector; no repetir pruebas visuales/Execute/Restore para este cierre. Fase04, texto Systemhaus y límites históricos se conservan sin bloquear el ensayo. [Decisión y mensaje vigente](MENSAJE-PARA-CLAUDE-C-CERRADO-25-10-2026.md). El cuerpo siguiente es histórico.

**Resultado:** Restore operativo comprobado. Codex confirmó desde Windows invitado el servicio en ejecución, HTTPS con validación normal de certificados, esquema 14, login de `w02-recovery-c`, presencia exacta de «Cliente prueba W02» en la API y logout correcto. **La comprobación visual en el navegador y el cierre completo de W-02 siguen pendientes.**

## Qué se ejecutó realmente

- Claude ejecutó la instalación 08 y el reinicio. Codex no repitió Execute, INICIAR, Restore ni reinicio.
- Codex utilizó VMware Tools con la identidad Windows autorizada, leyendo la clave local privada sin imprimirla. Dos sondas PowerShell escribieron sus resultados en `C:\W02\informes`; se copiaron al host. No se cambiaron ACL, cuentas, servicios, firewall, configuración ni datos de clientes. El login creó una sesión de prueba y el logout la revocó; esto sí implica escrituras de autenticación.
- Medición principal: `2026-10-25T20:18:07.8226016Z`, equipo `WIN-O8PBF3UU7T7`, instalación `54ce3eec-940e-4b22-a004-ed118f052c19`, URL `https://192.168.206.131:8443`.
- Servicio `Running`; `/health/ready` devolvió `ready`, esquema 14. Sin desactivar la validación TLS.
- Login HTTP 200; la respuesta autenticada de `/api/v1/customers` contiene exactamente una coincidencia literal con «Cliente prueba W02»; logout HTTP 204. No se midió el total de clientes: `customerCount=null` es una limitación de la proyección PowerShell, no una ausencia de datos.
- `postboot_verified`, `valid=true`, `success=true`, `exitCode=0`, `rebootVerified=true`, `productAdopted=false`. UUID y `bootUtc=2026-10-25T20:07:16.5000000Z` coinciden con la máquina observada. Se midió después el SHA256 del recibo: `fd72871c3bcc28a8edc23966d88c2e8472063412df19749fd238c496079419b2`.

No se controló un navegador de C. La API confirma datos persistidos y accesibles con la cuenta recuperada, pero no sustituye la aceptación visual de Wascar.

## Hoja, preparación y red

La hoja conservada mide `939cd061d68c820be5d7a9b8db0f3aefb78fcdd6a598234ee57097ba5a0aedfb`. Preparación y recibo coinciden en usuario, servicio, cuenta, dirección, puertos, modo Restore y hash de entrada. La regla de firewall está habilitada, entrada Allow, IP local `192.168.206.131`, puerto 8443 y red remota `192.168.206.0/255.255.255.0`, equivalente a `/24`. HTTPS validado aporta además comprobación efectiva de confianza.

Dos diferencias deben quedar explícitas:

1. El UUID de la hoja `be68c7be-…` y el UUID generado por la interfaz `54ce3eec-…` son distintos, como permite el procedimiento. El `id=false` de la sonda es una comparación literal, no un fallo de instalación.
2. La hoja dice **«Sistemhaus de prueba»** y `preparation-plan.json` dice **«Systemhaus de prueba»**. Por tanto, no se puede afirmar igualdad literal de los otros 14 campos. En Restore ese parámetro no renombra el Systemhaus recuperado; no se ha modificado la base para hacer coincidir el texto.

`backupPath` se transforma a `codeRoot\recovery-input`. Allí se midieron el manifiesto original `af6a82d20417368ccc003a58bb28af437778edf89eeb95d538240a5e6fd0adda` y el dump original `dac0be497c3259e720344f09ef6e7df5e1a8b573a15c3c35b9c1bd1dfdd6e43b`, 134576 bytes. Coinciden con A07. No se inspeccionó el contenido del dump.

## Exportación adicional y dependencias

Se conserva **sin borrar ni trasladar** `C:\Users\Wascar\Desktop\RackClick-Backups\0dce120a-9ca9-4e3a-bbfe-2375b12f2a3b`. Es una exportación privada posterior al Restore; no sustituye a la entrada A07 ni se publica su dump. Se midieron sólo metadatos y hashes:

- Creación declarada: `2026-10-25T20:04:52.4238974Z`.
- Manifiesto: `824eef509428c32e811d80b01ea1dcdf934a47f461370b4b9031554e2a98836b`.
- Dump: 135177 bytes, `5721a2c410814c4bc0bfcd65197583eed02cf9f582996136bb279a9f719e820a`; coincide con los campos del manifiesto.
- `postgresVersion=17.11`. El código de backup exige `SHOW server_version_num=170011` antes de completar. Esto es evidencia indirecta del motor durante ese backup, no una consulta SQL nueva ejecutada por Codex ni prueba de su procedencia administrativa completa.

Ambas DLL de CRT medidas en System32 son `14.51.36247.0`. La lectura de ejecutables bajo el árbol privado del servicio produjo `UnauthorizedAccessException`; se conservó el primer informe parcial. No se cambiaron permisos para continuar. Falta incorporar de forma segura las mediciones reales de frameworks y PostgreSQL del recibo Stage/preflight, además del inventario suficiente de dependencias previo a instalación. El perfil fijado no equivale a una medición del runtime activo.

## Evidencia histórica y límites

- Reconcile conserva `unknown`: falta `fase-04`, por tanto no hay exit observado del proceso interactivo. La comprobación positiva de servicio/datos no reconstruye esa salida. No fabricar recibos ni repetir Restore sólo para obtenerla.
- El ZIP sanitizado de Claude es preboot. El postboot fue contrastado después directamente, no atribuido a ese ZIP.
- El primer fallo está registrado **18,306931 segundos después del arranque**. Eso no demuestra que la petición durara 18 segundos ni identifica su causa. Se conserva el fallo junto al éxito posterior.
- Los hashes de los dos JSON están intercambiados en el resumen y mensaje de Claude. Valores medidos: `CAMPOS-REGISTRO-INSTALACION-C.json` = `5a3494f6415dd6f81a5a7a9c21d0b2efac0595edc2ca6754df34372e0c342c19`; `RECONCILIACION-C-solo-lectura.json` = `bd89bbfe606a8791a09cfca3a08f9a806db60df3805e5988884b7b376e1d2d48`. No se reescribieron sus originales.

La revisión independiente ejecutó 12 aserciones sobre los cuatro archivos públicos. Sus límites iniciales se complementan con las sondas del coordinador, sin convertirlas en un ensayo completo del instalador.

## Cierre y siguiente trabajo

W-02.02 queda **en curso**, sin crédito adicional: Restore y datos sí, matriz completa de dependencias/instalación y salida del auxiliar aún no. W-02 conserva **0,50/2,50**; cierre del pendiente **5,50/100**, 13/280 subpasos, 1/50 resultados. No es porcentaje global del producto. No cambia el alcance ni los pesos.

Siguiente: conciliar las correcciones documentales; obtener una proyección permitida de los recibos de dependencias; registrar la diferencia de Systemhaus y la ausencia de fase04. El próximo ensayo planificado debe permitir cerrar el proceso del asistente antes de reiniciar, conservando su salida real. No hay orden de reinstalar C ni de crear otra VM.

[Evidencia y sondas](../evidence/s1-20261025/w02-restore-c-codex/CIERRE.md). Sin commits, build, paquetes nuevos ni cambios en A, B o QA.
