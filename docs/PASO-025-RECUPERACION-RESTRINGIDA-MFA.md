# Paso 25 · recuperación MFA sin acceso API hasta reenrolar

11.11.2026 · F-08.02. Cerrado técnicamente con revisión independiente favorable. **D y E permanecen intactas.**

## Contrato conservado

1. La contraseña válida abre un desafío de verificación; un código de recuperación sin ese desafío no basta.
2. Canjear el código devuelve **202 y un desafío nuevo de enrolamiento**, con CSRF propio. No emite una sesión API normal y retira las sesiones antiguas.
3. Antes de configurar el factor, mientras está pendiente y después de una confirmación inválida, la API sigue denegando lecturas y escrituras. Renombrar la cookie de desafío como cookie de sesión tampoco autentica.
4. Volver a iniciar sesión con contraseña durante la recuperación sigue conduciendo a enrolamiento. La exención global de la política de 45 días no evita un reenrolamiento explícitamente pendiente.
5. Sólo confirmar el nuevo factor emite una sesión y CSRF nuevos y permite entrar. La política de gracia conserva su valor y fecha.

Se conserva la implementación del punto 3; no hay otro login ni cambios de producto, esquema, dependencias o interfaz. La única fuente nueva es una prueba HTTP con dos escenarios, cuenta ordinaria y administrador global, en PostgreSQL nuevo y con rol SQL restringido.

## Evidencia y uso

[Resultados y límites](../evidence/s1-20261111/f08-02-recuperacion/RESULTADOS.md) · [matriz](../evidence/s1-20261111/f08-02-recuperacion/MATRIZ-CRITERIO.md) · [plan](PLAN-F0802-RECUPERACION-RESTRINGIDA.md).

La GUI existente ofrece **Perdí mi autenticador** en el desafío de verificación, seguido de **Recuperar y configurar un autenticador nuevo**. El procedimiento está en [punto 3](PUNTO3-FUNCIONES-PENDIENTES.md), asociado a QA-163. Esto no habilita otro caso ni exige repetir la instalación en D. No se han usado cuentas o factores personales de Wascar.

## Lo que no se cierra

El nuevo foco usa TestServer y claves sintéticas de laboratorio por DI; no es un nuevo ensayo de navegador, TLS, DPAPI, SID efectivo o candidata instalada. El Edge histórico se reutiliza con su fecha y límites. El aislamiento SQL sí se comprueba con una cuenta no propietaria y rechazo real de DDL.

La revocación observada permite comprobar que el estado restringido no hereda una sesión antigua. Concurrencia de canje, replay, rollback, custodia y último administrador mantienen sus pasos F-08.03 a F-08.05 y sus hitos operativos propios. Los códigos no sustituyen la recuperación local de un host que no puede arrancar por pérdida del almacén TOTP.


Sólo F-08.02 acredita **1/2 punto**: índice del cierre restante **22,63 → 23,13/100**, sin porcentaje global nuevo. [Dictamen](../evidence/s1-20261111/f08-02-recuperacion/review/DICTAMEN.md). Siguiente paso 26 / F-08.03.
