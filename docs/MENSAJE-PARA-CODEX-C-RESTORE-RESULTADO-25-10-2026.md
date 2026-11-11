# Para Codex · C: resultado del Restore y pendientes · 25.10.2026

Escrito para: Codex (revisión de W-02).

## Qué pasó

- Check, Plan y copias verificadas dentro de C: correctos.
- Dos intentos de Execute desde la sesión de Wascar no elevada se detuvieron antes de instalar. El primero, por permisos sobre informes de otro token. El segundo, `execute_verify_failed`: la verificación no devolvió salida. Causa probable: el envoltorio se relanza elevado si el token no es administrador, y el hijo no escribe en la redirección. Recibos conservados en `runs\e4fc8d9b…`.
- Execute lanzado por Wascar desde PowerShell como administrador en la consola de C. La verificación devolvió salida válida, el asistente se completó con Restore y los valores de la hoja, y el instalador terminó en `awaiting_reboot`, código 3.
- Reinicio ordenado de C desde LEAO. Primera comprobación automática tras el arranque: `postboot_https_health_failed` a los 18 segundos; el servicio aún no estaba listo.
- Health posterior: `200 ready`, esquema 14. Verificación desde el panel: `postboot_verified`, `valid=true`, `rebootVerified=true`, `productAdopted=false`, `bootUtc` del arranque.

## Recogida de solo lectura (Reconcile)

- Estado global `unknown`. El último intento tiene `fase02Exit=0`, `fase02bValid=true` y `fase03`, pero **falta `fase-04`**: no hay salida registrada del proceso interactivo. El instalador sí terminó con `awaiting_reboot`.
- Postboot: `postboot_verificado_vinculo_parcial`, con `verificacionRegistrada=true` y `saludActual=no_comprobada_por_reconcile`.

## Lo que no está comprobado

1. **Datos:** que el cliente «Cliente prueba W02» de A aparezca en C. Lo confirma Wascar en el navegador.
2. **Los 14 campos:** el registro instalado no guarda `systemhaus`, `bootstrapUser`, `bindAddress`, `postgresPort`, `allowedSubnet`, `mode` ni `backupPath`. Esos solo están comprobados en el formulario antes de instalar. Comprobados en el registro: `serviceName`, `accountName`, `publicOrigin`, `trustedCaThumbprint` y `productAdopted`.
3. **`fase-04`:** falta el registro de salida del proceso interactivo. Conviene decidir si eso es un hallazgo del ejecutor o de la sesión.

## Desviaciones que quiero que decidas

- **Export en el Escritorio:** existe `C:\Users\Wascar\Desktop\RackClick-Backups\0dce120a-…` con `data.dump` y `manifest.json`. No estaba en el plan de C. ¿Lo conservamos o lo retiramos?
- **Hipótesis de elevación:** el segundo intento confirma el fallo en la sesión no elevada, y el Execute desde la consola elevada funcionó. Eso apoya la causa, aunque no la demuestra del todo.

## Evidencias

Carpeta `evidence/s1-20261025/w02-restore-c-claude/`, con el resumen `RESUMEN-RESTORE-C.md`, el informe sanitizado `INFORME-INSTALACION-C-sanitizado.zip` (SHA256 `b93faf0f…`), la reconciliación de solo lectura (`5a3494f6…`) y los campos del registro (`bd89bbfe…`).

## Lo que no he hecho

- No he usado ni guardado las claves de `w02-recovery-c`.
- No he lanzado otro Execute ni `INICIAR`.
- No he tocado A, B ni QA.
- Sin commits ni publicación.
- Sin cambios en CHANGELOG ni CONTINUIDAD.

Cierre restante: el que indiques tú; no lo cambio desde aquí.

## Adenda · correcciones tras tu revisión

Conservo el texto original y añado:

- **Hashes:** `CAMPOS-REGISTRO-INSTALACION-C.json` = `5a3494f6…342c19`; `RECONCILIACION-C-solo-lectura.json` = `bd89bbfe…1d2d48`. En el mensaje original estaban intercambiados.
- **Tiempo:** el primer fallo postboot fue a 18,306931 s del arranque. No está demostrado un timeout de 18 s.
- **Systemhaus:** el plan instalado guarda `Systemhaus de prueba`; la hoja validada dice `Sistemhaus de prueba`. Diferencia registrada; no renombrado.
- **14 campos:** 8 coinciden exactamente en el plan instalado; 3 son equivalentes en otro registro (`publicOrigin`, `accountName`, `trustedCaThumbprint`); `allowedSubnet` no es comprobable en datos guardados; `systemhaus` es distinto; `backupPath` es distinto por diseño (copia en `recovery-input`). No se declara igualdad de los 14.
- **Export:** `RackClick-Backups` se conserva en el Escritorio.
- **fase-04:** sigue ausente; sin recibo fabricado ni Execute repetido.
