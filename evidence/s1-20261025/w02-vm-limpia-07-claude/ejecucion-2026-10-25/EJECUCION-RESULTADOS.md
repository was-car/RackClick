# W-02 · Ejecución real en VM del 25.10.2026 — New en W02-A y Restore en W02-B

Escrito para: revisor independiente de W-02 y responsable del ledger de cierre.

Estado: **New y Restore completados en VM; verificación posterior al reinicio registrada en ambas.** Hay desviaciones y fallos previos documentados abajo. El crédito es propuesta: lo concilia Codex.

## Entorno

- VMware Workstation en el host `LEAO` (Windows 11 Pro 10.0.26300). No se ha tocado la VM QA `192.168.250.78` ni la VM existente "Windows Server 2025".
- W02-A: `192.168.206.128`, nombre `W02-A`. W02-B: `192.168.206.129`, nombre `W02-B`. Red de solo host VMnet1.
- Ambas: Windows Server 2025 Standard Evaluation, build 26100, rol de servidor independiente (`DomainRole` 2), 4 vCPU, 6 GB de RAM, disco de 80 GB, VMware Tools en ejecución.
- Medio: `26100.32230.260111-0550.lt_release_svc_refresh_SERVER_EVAL_x64FRE_de-de.iso`. Sistema en alemán (de-DE), porque el medio es alemán.
- Artefactos de la entrega 07 copiados a cada VM y comprobados contra sus pins (4 de 4 en ambas).
- Ejecutor `Invoke-W02TrialPlan.ps1` con el SHA256 `28c0b0c0…3749999`.

## W02-A · New

| Paso | Resultado |
|---|---|
| Check | `pass` (todas las comprobaciones) |
| Plan (hoja New) | `setup_plan_valid` |
| Envoltorio descomprimido | `C:\W02\envoltorio\RackClick-Servidor-07` |
| Execute: primera llamada `-VerifyOnly` con ficheros bloqueados | `valid: true`, `clean_payload_extracted`, stderr vacío |
| Instalación | `awaiting_reboot`, código 3, `installedReady: true`, URL `https://192.168.206.128:8443` |
| Reinicio | Confirmado: último arranque posterior al reinicio |
| Verificación posterior al reinicio | `postboot_verified`, `rebootVerified: true`, `productAdopted: false` |
| Exportación | `export_complete`, manifiesto SHA256 `93a34f8c…` (primera copia) |

Nota: el `execute-report.json` de Execute no se escribió, porque el reinicio cortó la llamada del ejecutor. El estado se registra en `result.json` y en las salidas de cada paso.

Nota sobre la exportación final: la copia usada para el Restore (`e6559c36-…`, manifiesto `af6a82d2…adda`) se hizo **después** de crear el cliente de prueba "Cliente prueba W02". La primera copia (`2696090e-…`) se hizo antes y no se usa.

## W02-B · Restore

Tres intentos. Solo el tercero completó la instalación.

| Intento | Resultado | Causa conocida |
|---|---|---|
| 1 (`db0d1dc3-…`) | `setup_child_failed_preserved` en preparación de PostgreSQL (línea 45, hijo de preparación en línea 142) | **Sin causa identificada.** El registro de excepción privado no se encontró en la VM. El prerrequisito VC++ sí se instaló. |
| 2 (`af631734-…`) | `setup_account_exists` (etapa `host`, línea 82) | La cuenta `RackClickSvcB` seguía existiendo. La limpieza la marcó como **preservada** (`preservedCount: 1`, `retiredAccountCount: 0`). |
| 3 (`ee0a448d-…`) | Restore completado: `awaiting_reboot`, código 3 | Ver intervención manual abajo |

**Intervención manual (aprobada por el usuario, opción B):** antes del intento 3 se detuvieron los procesos restos del intento 2 (PID 3296 y 3400, sin ventana, responden) y se eliminó **solo** la cuenta `RackClickSvcB`. No se tocó ninguna carpeta. Registro en `vmB-restore/limpieza-manual-W02-B.txt`.

Comprobación de preparación antes del intento 3: 22 de 22 comprobaciones OK (`vmB-restore/listo-W02-B.json`).

Después del intento 3:
- Reinicio: último arranque 15:01:12 (hora local).
- Servicio `RackClick`: `Running`. Puerto 8443 escuchando.
- Verificación posterior al reinicio: `postboot_verified`, `rebootVerified: true`, `productAdopted: false`.
- Comprobación de datos: en la web de W02-B aparece **"Cliente prueba W02"**, creado en W02-A antes de la exportación.

## Desviación de la hoja

- La hoja decía `admin-prueba` como administrador de RackClick. En el intento 3 el campo de la interfaz quedó como **`wascar`** porque el operador no lo cambió (error de operador, no intencionado).
- El `admin-login.json` de la instancia restaurada tiene `username: wascar`. La instalación original (W02-A) tenía `admin-prueba`.
- No se repitió el Restore, para no volver a chocar con la cuenta de servicio preservada.
- **Decisión del responsable:** tema abierto. De momento el Restore ha funcionado correctamente aunque el usuario administrador no coincida con la hoja.
- Este caso es justamente la comparación manual de los 14 campos que el procedimiento exige y que el ejecutor no hace automáticamente (hallazgo H2).

## Hallazgos para revisión

Los mismos hallazgos, con las preguntas para Codex, están en `HALLAZGOS-PARA-CODEX.md`.


1. **Causa del fallo del intento 1 (PostgreSQL) sin identificar.** Falta el registro de excepción. Hace falta revisarlo antes de dar crédito a W-02.02.
2. **La limpieza del envoltorio preserva una cuenta de servicio de un intento fallido** y eso bloquea la reinstalación (`setup_account_exists`). Hay que decidir si es comportamiento esperado.
3. **`result.json` no se actualiza tras la verificación posterior al reinicio**: sigue en `awaiting_reboot` aunque `postboot-verification.json` diga `postboot_verified`. Pasa en ambas VM.
4. **`execute-report.json` no se escribe** cuando el reinicio llega antes de que termine la llamada del ejecutor, en ambas instalaciones.
5. **Etiquetas "05"** en el envoltorio 07 (H3): sin cambios.
6. **Python**: en ambas VM `python` es solo el alias de la Tienda; no hay Python instalado. El Check lo marca como `herramientas_previas` informativo.

## Propuesta de crédito (la concilia Codex)

- W-02.01 (VM limpia de Windows Server 2025, no DC, con registro): **1/2 propuesto**.
- W-02.02 (entrega completa sin SDK/Node/Python previos, runtime/PostgreSQL/CRT y reinicio): **1/2 propuesto, condicionado** a revisar el hallazgo 1. Sin esa revisión, 0.
- W-02.03: **0**. Solo se ha probado el puerto ocupado en el host, no en la VM; no hay prueba de versión incompatible ni de controladora de dominio.
- W-02.04: **0**. No se ha probado Windows 11 como host de servidor.
- W-02.05: **0**. Falta la revisión independiente de esta evidencia.

## Uso de credenciales de laboratorio

Las credenciales de los servidores de laboratorio se usaron para las comprobaciones directas. Son laboratorios y el responsable lo ha aceptado expresamente. No se han copiado a ningún informe.

## Ficheros de esta carpeta

- `vmA-new/`: informe sanitizado del instalador, Check y Plan revalidados, primera llamada `-VerifyOnly`, verificación posterior al reinicio, exportación y resultado del instalador.
- `vmB-restore/`: hoja Restore, Plan, verificación, comprobación de hashes de la copia, resultado del instalador, verificación posterior al reinicio, comprobación de preparación, estado tras reinicio y registro de la limpieza manual.
- `intentos-fallidos-B/`: informes sanitizados de los intentos 1 y 2, y los ficheros pequeños preservados del intento 1.

No incluye: credenciales (`credenciales-privadas.txt`, `admin-login*.json`), la copia de datos (`data.dump`) ni volcados de memoria. Quedan en `.local/`, que no se versiona.
