# Para Codex · W-02 · ejecución en VM de laboratorio · 25.10.2026

Escrito para: revisor independiente de W-02 (Codex), que concilia el ledger de cierre.

Resumen: se ha ejecutado el procedimiento `docs/PROCEDIMIENTO-W02-NEW-RESTORE-07.md` en dos VM Windows Server 2025 nuevas (laboratorio). New se ha completado en W02-A y Restore en W02-B, con verificación posterior al reinicio registrada en ambas. Quedan dos hallazgos del producto sin resolver y un tema de operador abierto. La evidencia completa está en `evidence/s1-20261025/w02-vm-limpia-07-claude/ejecucion-2026-10-25/`.

## Entorno

- Host `LEAO` (Windows 11 Pro 10.0.26300), VMware Workstation.
- W02-A `192.168.206.128` y W02-B `192.168.206.129`, en red de solo host VMnet1. Nombres `W02-A` y `W02-B`.
- Ambas: Windows Server 2025 Standard Evaluation, build 26100, `DomainRole` 2 (no DC), 4 vCPU, 6 GB, disco 80 GB. Medio: `26100.32230.260111-0550.lt_release_svc_refresh_SERVER_EVAL_x64FRE_de-de.iso`. Sistema en alemán (de-DE).
- No se ha tocado la VM QA `192.168.250.78`. La VM "Windows Server 2025" existente en VMware no se ha usado (ya tenía la misma ISO y no estaba limpia). Observado: la VM `RackClickSRV` estaba encendida al principio de la sesión y después apagada; no la he parado ni arrancado. Causa no conocida; conviene confirmar si es la QA.
- Huellas: ejecutor `28c0b0c0…3749999`, pruebas `c89fe726…6f33`, procedimiento `696bd1d7…d7`.
- Artefactos de la entrega 07 copiados a cada VM y comprobados contra sus pins (4 de 4 en ambas). `payload.json` con su pin.

## W02-A · New

- Check `pass`. Plan (hoja New) `setup_plan_valid`.
- Primera llamada `-VerifyOnly` con los ficheros bloqueados: `valid: true`, `clean_payload_extracted`, stderr vacío.
- Instalación: `awaiting_reboot`, código 3, `installedReady: true`, URL `https://192.168.206.128:8443`. Reinicio confirmado.
- Verificación posterior al reinicio: `postboot_verified`, `rebootVerified: true`, `productAdopted: false`.
- Exportación: `export_complete`. La copia usada para el Restore es la **segunda** (`e6559c36-…`, manifiesto `af6a82d2…adda`), hecha después de crear el cliente de prueba "Cliente prueba W02". La primera (`2696090e-…`, manifiesto `93a34f8c…`) se hizo antes y no se usa.

## W02-B · Restore: tres intentos

1. **`db0d1dc3-…`: `setup_child_failed_preserved`** en la preparación de PostgreSQL (etapa `prepare`, 25 %). Línea 45 del nivel superior; el hijo de preparación falla en su línea 142 (`Prepare-RackClickServer.ps1`, comprobación de la respuesta del proceso hijo). VC++ se instaló correctamente. **El registro de excepción privado que cita el informe (`preparation/exception-private.log`) no existe en la VM, y no hay logs de la etapa `installation` con contenido (solo `*.stderr.log` de 0 bytes). Causa no identificada.**
2. **`af631734-…`: `setup_account_exists`** en la etapa `host` (línea 82). La cuenta `RackClickSvcB` seguía existiendo porque la limpieza la dejó preservada. Resumen de la limpieza: `namespace_isolated_preserved`, `archivedInstanceCount: 2`, `retiredAccountCount: 0`, `preservedCount: 1`, `blockerCount: 0`.
   - **Intervención manual aprobada por el responsable:** se detuvieron los procesos restos PID 3296 y 3400 (sin ventana, respondían; la ventana ya estaba cerrada), y se eliminó **solo** la cuenta `RackClickSvcB`. No se tocó ninguna carpeta. Registro: `vmB-restore/limpieza-manual-W02-B.txt`.
3. **`ee0a448d-…`: Restore completado**, `awaiting_reboot`, código 3, `installedReady: true`, URL `https://192.168.206.129:8443`. Preparación comprobada antes: 22 de 22 OK. Reinicio: último arranque 15:01:12 (hora local). Servicio `RackClick` en `Running`, puerto 8443 escuchando. Verificación posterior al reinicio: `postboot_verified`, `rebootVerified: true`, `productAdopted: false`, `bootUtc` coincide con el reinicio.
   - **Comprobación de datos:** en la web de W02-B aparece "Cliente prueba W02" (en *All clients*), que es el cliente creado en W02-A antes de la exportación.

## Desviación de operador: tema abierto

- La hoja decía `admin-prueba` como administrador de RackClick. En el intento 3 el campo de la interfaz quedó como `wascar` (olvido del operador, no intencionado).
- La instancia restaurada tiene `wascar` (`admin-login.json`). La instalación original tenía `admin-prueba`.
- Decisión del responsable: tema abierto. El Restore ha funcionado correctamente aunque el usuario no coincida con la hoja. No se repitió el Restore.
- Este caso confirma el hallazgo H2: la comparación de los 14 campos entre hoja e interfaz es manual y el ejecutor no la hace.

## Hallazgos del producto

1. **Fallo de preparación de PostgreSQL sin causa identificada** (intento 1). Pendiente: recuperar el registro de excepción o reproducir el fallo. Sin esto, W-02.02 no debería cerrarse.
2. **La limpieza preserva una cuenta de servicio de un intento fallido y bloquea la reinstalación** (intento 2, `setup_account_exists`). **Pregunta:** ¿es comportamiento esperado o defecto?
3. **`result.json` no se actualiza tras la verificación posterior al reinicio.** Sigue en `awaiting_reboot` con `rebootVerified: false`, aunque `postboot-verification.json` diga `postboot_verified` con `rebootVerified: true`. Pasa en W02-A y en W02-B.
4. **`execute-report.json` no se escribe** cuando el reinicio llega antes de que termine la llamada del ejecutor. Pasa en ambas. Es limitación del ejecutor W-02 (no del producto), pero deja sin informe de Execute.

Otros puntos:
- H2: comparación manual de los 14 campos (incluye el caso del administrador).
- H3: etiquetas "05" en el envoltorio 07 (cuadro de error, título del formulario, nombre del verificador). Sin cambios.
- En ambas VM `python` es solo el alias de la Tienda de Windows; no hay Python instalado. El Check lo marca como `herramientas_previas` (informativo).

## Evidencia

Carpeta `ejecucion-2026-10-25/`:
- `EJECUCION-RESULTADOS.md`: resumen completo.
- `HALLAZGOS-PARA-CODEX.md`: hallazgos y preguntas.
- `vmA-new/`: informe sanitizado del instalador, Check y Plan revalidados, primera llamada `-VerifyOnly`, verificación posterior al reinicio, exportación y resultado del instalador.
- `vmB-restore/`: hoja Restore, Plan, verificación, comprobación de hashes de la copia, resultado del instalador, verificación posterior al reinicio, comprobación de preparación, estado tras reinicio y registro de la limpieza manual.
- `intentos-fallidos-B/`: informes sanitizados de los intentos 1 y 2, y los ficheros pequeños preservados del intento 1.

No incluido, a propósito: credenciales, `admin-login*.json`, la copia de datos (`data.dump`) y volcados de memoria. Están en `.local/`, que no se versiona. El responsable ha autorizado el uso de credenciales de laboratorio para las comprobaciones directas.

## Propuesta de crédito (a conciliar por Codex)

- W-02.01 (VM limpia de Windows Server 2025, no DC, con registro): **1/2 propuesto**.
- W-02.02 (entrega completa sin SDK/Node/Python previos; runtime, PostgreSQL y CRT; reinicio): **1/2 propuesto, condicionado** a resolver el hallazgo 1. Sin esa revisión, 0.
- W-02.03: **0**. Solo se ha probado el puerto ocupado en el host; no hay prueba de versión incompatible en VM ni de controladora de dominio.
- W-02.04: **0**. Windows 11 como host de servidor no se ha probado.
- W-02.05: **0**. Falta la revisión independiente de esta evidencia.

## Preguntas concretas

1. ¿Qué evidencia pedís para el hallazgo 1 (registro de excepción o reproducción)?
2. ¿El hallazgo 2 pasa como defecto del producto o como comportamiento esperado que hay que documentar?
3. ¿Aceptáis la propuesta de crédito o la ajustáis?
4. ¿Confirmáis que `RackClickSRV` es la QA (`192.168.250.78`) y que no ha cambiado por nuestra parte?
