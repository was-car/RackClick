# Paso 29 · autorizar el operador local de emergencia MFA

11.11.2026 · F-09.01. Cerrado técnicamente con revisión independiente favorable, limitado a la autorización local. **D y E se conservan.**

## Qué aporta este paso

El nuevo modo interno `--mfa-emergency-recovery` entra antes de configurar el servidor, resolver SQL o abrir un listener. La autoridad se toma del token Windows real: SYSTEM o un miembro efectivo de Administradores con token elevado. Rechaza usuario estándar, token filtrado/no elevado, elevación desconocida y cualquier suplantación. Claims, roles de RackClick, contraseña, JSON o variables de entorno no conceden esa autoridad.

El administrador global de RackClick y el administrador de Windows son autoridades distintas. «Local» es el proceso ejecutado en el host bajo la identidad Windows; una sesión RDP administrativa autenticada puede servir para ejecutarlo. No se crea una ruta web de emergencia.

**Este paso no recupera todavía cuentas.** Incluso si pasa la autorización, el comando devuelve `mfa_emergency_transition_unavailable`, salida1, cero operaciones y ninguna sesión. La preparación del anillo, retirada de factores, revocación y auditoría se implementan en los pasos30/31; el ensayo de pérdida total y cierre corresponden a32/33. No se ofrece como instalador ni se pide ejecutarlo ahora en D.

## Qué se reutiliza

- Los patrones de token de los operadores locales existentes; las APIs del framework/Win32, sin dependencias o locks nuevos.
- El requisito D2 confirmado, la custodia y gracia45/exención global vigentes. La autorización local no sustituye el factor nuevo después de una pérdida.
- La defensa de reenrolamiento de F-08, repetida por HTTP sobre el build nuevo. `--recover-admin` sigue siendo el operador de Restore y no se convierte en la emergencia de pérdida total.

## Verificación y límites

[Plan e investigación](PLAN-F0901-AUTORIZACION-EMERGENCIA.md) · [resultados](../evidence/s1-20261111/f09-01-autorizacion-local/RESULTADOS.md) · [matriz](../evidence/s1-20261111/f09-01-autorizacion-local/MATRIZ-CRITERIO.md).

La tabla de política prueba combinaciones simuladas, incluidas SYSTEM/Administrador elevado. La ejecución nativa contrasta el token disponible no elevado, claims falsos y suplantación propia con restauración de identidad. No se ejecutó un positivo elevado/SYSTEM real ni un proceso bajo la cuenta de servicio. Esos ensayos operativos siguen pendientes; no se cambia la configuración de D/E para producirlos.

La observación de fiabilidad del recorrido automatizado Edge de F0805 sigue abierta y no se vuelve a probar o resolver por esta compuerta CLI. Los175 casos QA y sus resultados personales permanecen intactos; no hay cambio visible de GUI que habilitar.


[Dictamen independiente](../evidence/s1-20261111/f09-01-autorizacion-local/review/DICTAMEN.md):79/79 y8sondas propias PASS. Sólo F-09.01 acredita **1/2 punto**: índice del cierre restante **24,63→25,13/100**, sin porcentaje global nuevo. F-09.02–.05 y seis hitos completos pendientes. Siguiente paso30/F-09.02.
