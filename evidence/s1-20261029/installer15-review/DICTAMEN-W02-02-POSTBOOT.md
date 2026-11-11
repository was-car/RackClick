# Dictamen independiente — postboot10 y W-02.02

29.10.2026. Conciliación de recibos y pruebas de contrato en lectura; este revisor no operó la VM ni reinició Windows. No se modificó el ledger.

**Propongo acreditar W-02.02:1/2de punto (0,50).** El criterio literal pide ejecutar la entrega sin SDK/Node/Python previos, comprobar runtime/PostgreSQL/CRT y el reinicio requerido. La ruta New de la candidata10 cumple ese alcance con el operador oficial. No se acredita W-02 completo ni los subpasos03–05.

## Qué está contrastado

- El preflight identifica Windows Server2025 Standard Evaluation, noDC, sin servicios/cuenta/directorios RackClick ni puertos reservados ocupados. El coordinador ejecutó el envoltorio en VerifyOnly y el operador oficial desde el payload verificado, usando el constructor privado de planes extraído exactamente de la GUI. **No fue un ensayo de clics en el asistente ni se ejecutó la limpieza de namespace**: la VM carecía de instalaciones previas. Esas diferencias no sustituyen una futura prueba UX; no cambian la instalación de dependencias del operador oficial que cubre este subpaso.
- No se ejecutaron compiladores, SDK, Node ni Python dentro del invitado. Runtime10.0.12 y PostgreSQL17.11 proceden del bundle verificado. La inspección final no encuentra dotnet global ni Node. `pythonAvailable:true` en la inspección inicial es un descubrimiento de comando: `python-command-kind.json` demuestra que es el alias WindowsApps, **no un intérprete Python probado**. No se afirma una búsqueda forense de todo el disco.
- El requisito Visual C++ anterior era incompatible; el recibo oficial registra instalación nativa con exit0, ambas DLL14.51.36247.0 y postcheck válido. **No se observó exit3010 del redistribuible**. El reinicio requerido por el recorrido del instalador sí se realizó y se verificó; no se presenta como una ejecución de la rama CRT3010.
- La instalación inicial guarda `awaiting_reboot`, exit observado3, como resultado histórico. El recibo instalado, el postboot final y el vínculo del ensayo coinciden en UUID y esquema15. El arranque nuevo es posterior a la fecha de instalación y al arranque inicial.
- `postboot-final.json` registra `postboot_verified`, exit0 y comprobación posterior al arranque nuevo. La observación independiente del coordinador registra servicio Running/Auto, healthready15 y validación TLS normal. El contrato oficial postboot comprueba también cuenta y tarea de backup. `INSTALLATION-RECEIPT.json` contiene `scheduledBackupVerified:true`.
- El primer postboot falló con `postboot_https_health_failed` a **21,767332s** del nuevo arranque. Se conserva sin atribuir una causa no demostrada. El éxito posterior se obtuvo mediante una comprobación oficial manual después de estar disponible: **no se afirma que la primera comprobación automática pasara**, ni que el fallo fuera un timeout de22s.
- La prueba MFA posterior usa exactamente ese nuevo arranque: contraseña202 → verify200 → estadoMFA200 → logout204. Conserva validación TLS, usa el proveedor Windows real y confirma persistencia del factor/clave a través del reinicio. Sigue siendo prueba HTTP con el adaptador de cookies documentado, no un ensayo visual del navegador.

## Comprobaciones de este revisor

`W02-02-POSTBOOT-CONCILIADO.json` registra hashes de9recibos, vínculos/orden de fechas y los límites del ensayo. Ejecuté además `Probe-Postboot10.ps1` con Windows PowerShell5.1: el helper oficial clasifica el recibo final como `recorded`, el fallo inicial como `unconfirmed` y mantiene `currentHealthVerified:false`. Es una conciliación de evidencia, no un nuevo sondeo de salud. Salida: `POSTBOOT-CONTRATOS.json`.

Una primera invocación propia bajo PowerShell7 falló por su conversión automática de fechas JSON a objetos DateTime; el contrato espera cadenas como las de Windows PowerShell5.1. Se repitió con5.1, sin cambiar producto ni recibos. No se cuenta el primer intento como fallo de la instalación.

Los campos históricos `rebootVerified:false` del recibo inicial y `success:false`/awaiting_reboot no se reescriben: el postboot separado acredita el resultado posterior. No son, por sí mismos, contradicción con la verificación nueva.

## Adenda de cambio de IP10

Ya existe el companion10 con SHA256 `69d8b30b64f32ccba077f7bbc916c90fde15dbce4d88e7476c4b8cf1d1e85d99`. Verifiqué todas sus sumas, ausencia de entradas extra y `payload.json` ligado a10 (`14e3092a863663bbf1f71f9e23918e7b419a057d7505bca7d42bc6b1a40b42ad`). El motor coincide con la fuente y fija ese digest. Esto supera la limitación de ausencia del paquete10 registrada en la adenda anterior; los ZIP09 siguen intactos. **No se ejecutó un cambio real de IP en este dictamen.**

## Límites de cierre

W-02.03 (matriz de dependencias presentes/rechazos), W-02.04 (otros hosts declarados) y W-02.05 (cierre integral) conservan su estado. Tampoco se acredita Restore con factores MFA, recuperación operativa, clicsGUI, cambioIP, backup/restore integral ni adopción productiva. La aceptación de Wascar sigue siendo suya. El coordinador puede sumar este0,50 al ledger; no se calcula un porcentaje global del producto ni se suma otra vez el subpasoW-02.01 ya acreditado.
