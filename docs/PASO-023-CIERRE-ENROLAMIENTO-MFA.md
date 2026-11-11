# Paso 23 · cierre del enrolamiento restringido MFA

11.11.2026 · F-07.05. Cerrado técnicamente con revisión independiente favorable. **D y E se conservan sin operaciones.**

## Qué se comprueba

Se reutilizan el login, enrolamiento, confirmación y pantalla MFA existentes. La nueva comprobación cubre la brecha entre aquellas piezas: ni el desafío, ni un factor pendiente, ni un código incorrecto permiten leer clientes o efectuar cambios.

Se crean dos cuentas ordinarias en bases nuevas: una cuyo plazo parte de su creación y otra antigua sin fecha histórica cuyo plazo parte de la activación persistida. Ambas han agotado sus45días. No se hace obligatorio MFA inmediatamente para todas las altas ni se cambia la exención de los administradores globales.

En cada caso se prueban /me, clientes, creación de cliente y preferencias en tres etapas —desafío inicial, factor pending y confirmación inválida—, tanto con la cookie de desafío como intentando usar su token como cookie Session. Las24peticiones por caso se rechazan sin sesión ni cambios en las tablas comparadas.

Al confirmar simultáneamente dos veces, sólo una respuesta obtiene sesión nueva y CSRF nuevo. Factor, consumo de desafío y sesión quedan en la misma transacción, observada desde SQL. Un reintento no genera una segunda sesión. El host utiliza el proveedor Windows/DPAPI real con activa7 y un rol PostgreSQL de ejecución no propietario, observado en las escrituras y sin DDL.

## Evidencia reutilizada y nueva

- L1ronda2 conserva consumo único, bloqueos, revocación, caducidad y rollback de auditoría.
- GUI27.10 y la revisión del punto3 acreditan el flujo visual EN/DE/ES y su evolución; la pantalla actual se contrasta por hashes con la última revisión, no sólo con el primer prototipo.
- C10 conserva enrolamiento, confirmación, siguiente login y reinicio por HTTPS; D11 aporta una verificación sintética Windows/DPAPI/TLS posterior. El smoke inicial de D11 fallido no se convierte en éxito.
- Nuevas ejecuciones:2casos completos,36casos del núcleo y70pruebas Node del frontend; cada conjunto mantiene su entorno y atribución.

[Resultados](../evidence/s1-20261111/f07-05-enrolamiento/RESULTADOS.md) · [matriz del criterio](../evidence/s1-20261111/f07-05-enrolamiento/MATRIZ-CIERRE.md) · [plan e investigación](PLAN-F0705-CIERRE-ENROLAMIENTO.md).

## Límites

Las pruebas nuevas usan TestServer HTTP en memoria: no son TCP/TLS, navegador o token del servicio. Sólo la identidad de confianza Windows es de laboratorio; el proveedor, lector, DPAPI y pipeline de aplicación son reales. La evidencia nativa previa mantiene su propio alcance, no se atribuye a esta ejecución.

No se instala candidata46 ni se opera sobre datos, cuenta personal, autenticador, políticas o credenciales de D/E. No se cierran recuperación del último administrador, custodia externa, códigos de recuperación completos, integración de candidata objetivo o aceptación productiva de Wascar por este paso.


Sólo F-07.05 acredita **1/2punto**: índice del cierre restante **21,63→22,13/100**, sin porcentaje global nuevo. [Dictamen](../evidence/s1-20261111/f07-05-enrolamiento/review/DICTAMEN.md). Siguiente paso24/F-08.01.
