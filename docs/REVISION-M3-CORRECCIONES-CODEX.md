# M3 · revisión de correcciones · Codex · 23.10.2026

**Dictamen: NO desplegable todavía.** El build nuevo supera C1 y los casos de reset/política/CSRF comprobados. Quedan dos bloqueos concretos: caducidad tras esperar la política y paquete que sigue transportando la aplicación13. No se corrige la instalación cambiando únicamente el pin exterior.

Implementación: Claude. Revisión independiente: Codex, con revisión separada de los operadores. Entrada: `BUILD-M3-CORRECCIONES-23-10-2026.md`, conservada en la evidencia. No se modificó código de Claude, proyectos/locks, SQL, operadores, QA, VM, cuentas o servicios del servidor. Sin commits/push. El informe anterior sigue siendo evidencia histórica; éste identifica otra versión.

## Build revisado y pruebas nuevas

- DLL real candidata **`db5aa9fdff06e72e1acffecb05bb7f9100e05baeee8fe9b0df60ba03d046b68a`**, copiada desde `.local/m3-publish`. Coincide con la declaración de Claude. El probe referencia esa DLL directamente; no recompila el producto para sus pruebas de almacén/reset.
- Copia congelada de259 archivos del árbol de trabajo, base Git `7b4f3e8a9eb9b7278f0347b3cdd473348966e821`. Manifiesto de fuentes SHA `ec9bed9e304bb797efa5ccaeb6e63920c66c91a5c438724e9579a3fd1cc90ac5`; archivo privado SHA `e70cc0ffe166f7d982eb8f6f7543b558ed8fd56dc83328afe5fc3da6c9f912e0`. Los cambios no son un commit.
- Windows11 build26300, PostgreSQL17.11 nativo y SDK10.0.401 fijado para compilar los dos auxiliares de prueba. Clústeres nuevos, sólo loopback, owner/runtime separados y secretos locales privados. Sin utilizar M1 ni un QA existente.
- **C1:10/10 conformes sobre la DLL candidata**, con bootstrap/migraciones reales hasta14 y **sin hook de014 manual**. Permisos/membresías, último administrador, sesiones/reset/replay/concurrencia/rollback/auditoría y logs del alcance anterior. No equivale a aceptación de todos los módulos ni del instalador.
- **25 comprobaciones adicionales conformes**:11 de bootstrap/arranque/migración/login de la DLL real y14 HTTP sobre una variante con proveedor sintético descrita abajo. **10 comprobaciones directas MFA:9 conformes y1 fallo de caducidad**. Las reproducciones no se suman como funciones nuevas.

## Dictamen por corrección original

| Hallazgo | Resultado independiente | Estado |
|---|---|---|
| M3-01 · migración/readiness | Bootstrap real aplica14 con14 registros de historial; readiness14 y login normal funcionan. Ante base13 real el candidato responde readiness503 y no migra desde el runtime. `--migrate` con owner lleva13→14 y, tras refrescar grants del runtime por el fixture, readiness/login funcionan. | Corregido en servidor/runner en ese alcance. **Publicación e instalación siguen bloqueadas**, según P-01. No se acredita que el instalador gestione correctamente los grants. |
| M3-02 · reset y desafío | Llamada real a `ResetOrCancelUserPassword` con sesión administrativa válida y auditoría confirmada: el desafío anterior se rechaza. También se ejecutó el endpoint administrativo real por HTTP en la composición de prueba y se rechazó su desafío pendiente. | Corregido para reset confirmado en esos escenarios. No se repitieron aquí las carreras/reset revertido de Claude; tampoco se sustituyen por una transacción réplica. |
| M3-03 · política | Cambio de revisión invalida el desafío; `enrollment_pending` devuelve `mfa_enrollment_required`. Las consultas revisan exigencia/revisión bajo locks. | Corregido en los escenarios probados. La espera de esa consulta mantiene el problema temporal siguiente. Panel M4/enrolamiento aún fuera de esta revisión. |
| M3-04 · caducidad | La espera por cuenta ya rechaza el desafío vencido, pero una espera posterior por política permite emitir sesión vencida. | **Abierto**, reproducido sobre la DLL candidata exacta. |
| M3-05 · CSRF propio | HTTP: ausente403, incorrecto403, ambos sin gasto de intentos/consumo/sesión; correcto200 con identidad, sesión y CSRF nuevos; replay401. | Corregido para el código HTTP ensayado con proveedor sintético. No equivale a proveedor/custodia de producción habilitados. |

## M3-04 · P2 · todavía hay un bloqueo después de comprobar la vigencia

En `MfaStore.cs` se leen `expires_at>clock_timestamp()` y `databaseNow` al bloquear el desafío. **Después** se ejecuta `SELECT ... FROM app_mfa_user ... FOR SHARE`, que también puede esperar. No se vuelve a tomar el reloj ni a comprobar vigencia tras esa espera.

Reproducción nueva (`expiry_after_policy_wait`): crear usuario/factor y desafío mediante contraseña válida; acortar su vigencia a2s; mantener la fila de política con `FOR UPDATE` en otra conexión sin cambiar sus valores; iniciar verificación; observar en `pg_stat_activity` su espera por la política; liberar el bloqueo después de que PostgreSQL confirme la caducidad. Resultado: **`session_issued`**, cuando se esperaba `mfa_challenge_invalid`. `lockWitness:true` y `expiredAtRelease:true`. La espera equivalente por cuenta produce el rechazo correcto.

Corrección solicitada: adquirir todos los locks, incluido el de política, y hacer una comprobación fresca de cuenta/factor/política/desafío con reloj PostgreSQL **después de la última espera**. No conservar `databaseNow` anterior para el TOTP. Añadir negativos de espera por política y por desafío; una expresión evaluada dentro de una consulta que aún puede esperar no prueba por sí sola una decisión posterior al lock. La semántica del reloj está documentada por [PostgreSQL17](https://www.postgresql.org/docs/17/functions-datetime.html#FUNCTIONS-DATETIME-CURRENT).

Es un fallo de la lógica MFA latente con proveedor de prueba; no se afirma explotación por HTTP en el producto actual, cuyo proveedor continúa siendo `null`.

## P-01 · P1 · payload exterior nuevo, aplicación interior antigua

Los hashes declarados del ZIP exterior, payload y CMD coinciden. Se verificaron también los112 archivos declarados por `payload.json`. Esa integridad **no acredita que contenga el build M3**:

| Elemento transportado | Medición nueva |
|---|---|
| Payload exterior | `ffb4426cd69a4351f1ccff1a438eaf0ed7b6d7e0656bc857b461d03b08f69bb0` |
| `RackClick.zip` interior | `a0df90ed3a2864492d8d9bdc2cc2e552113a6b9c81a3e603c1c2920486c26869` |
| Manifiesto de aplicación interior | `55bdd496ec654494fd8e3400140e3e84241488986e24481939bad67cde7a91c6`, **esquema13** |
| DLL interior | `15586afdd75f0c244dd5b8123aab33a6264c43ad7f62831f8e7442404dfa0f0d`, distinta de `db5aa9…` |
| SQL014 interior | **Ausente**; sólo001–013 |

`Test-ServerDistribution` ejecutado en WinPS5.1 verifica correctamente40 archivos de esa aplicación13. Una distribución diagnóstica de la publicación M3 real, con25 archivos servidor y esquema14, se rechaza con exit2 `manifest_distribution_unsupported`. Ese manifiesto diagnóstico no es un nuevo perfil de entrega aprobado.

La revisión separada de los cuatro scripts está en `REVISION-OPERADORES.md` de la evidencia: hashes actuales/congelados coinciden y AST sin errores, pero **no aprobados como entrega14**. Los acoplamientos no se limitan a esos cuatro archivos:

- `package_server_installer.py`, `RackClick.Setup.ps1` y `Prepare-RackClickServer.ps1` siguen fijando el bundle13 `a0df90ed…`.
- `package_offline_bundle.py`, `RackClick.OfflineBundle.ps1`, `Test-ServerDistribution.ps1` y `RackClick.Stage.ps1` mantienen perfiles/esquemas/listas/conteos hasta13. No basta cambiar `-eq13` a14: también hay que conservar SQL013 para14, incluir014, Otp.NET y el inventario completo que se publique.
- `Invoke-RackClickServerRuntime.ps1` y `Start-RackClickLabInstance.ps1` aún rechazan `ExpectedSchema14`.
- Restore valida el historial del backup frente al esquema del stage antes de ejecutar `--recover-admin`; un backup13 no se convierte en14 por cambiar `RequiredSchemaVersion` en la CLI.

Corrección solicitada: producir una distribución de aplicación14 coherente y revisada, con dependencias/avisos, manifiesto y perfil; construir desde ella el bundle interior; alinear staging, runtime, New/Restore/recuperación y verificadores; después regenerar wrapper, pin y CMD con identidad nueva. **No sobrescribir los ZIP anteriores ni retirar los controles de integridad para aceptar mezclas.** Probar instalación/actualización/Restore sobre esa nueva candidata.

## Alcance exacto del ensayo HTTP

La DLL candidata fija `mfaKeys=null`, así que un flujo HTTP MFA correcto no es alcanzable con su composición actual. Se creó **sólo bajo `.local`** otra copia de las fuentes: se sustituyó esa única asignación por un proveedor que lee una clave sintética generada para el laboratorio y se añadió esa clase de prueba. Los cuerpos de endpoints, middleware y almacén permanecen iguales byte a byte. No hay nueva opción ni clave de prueba en el producto.

DLL de esta variante: `795a702cd746c6cb66c2ae76737d150bd663b7443caea404bb5c07f13dc5bdf4`. Hashes/diferencia en `http-test-composition.json`. Las14 comprobaciones incluyen desafío202 sin sesión, cookie HttpOnly/Strict/ruta mínima, desafío rechazado como sesión, CSRF ausente/incorrecto/correcto y no consumo, sesión/CSRF nuevos, identidad, replay y reset administrativo HTTP real. Loopback Development: no certifica TLS ni observación de Secure en navegador. No anunciarla como la DLL transportada ni como MFA de producción.

## Pendientes y siguiente entrega

1. Corregir/revalidar M3-04 en la fuente de Claude.
2. Resolver P-01 y entregar hashes del **conjunto** aplicación–bundle–wrapper–CMD. Entonces probar `Test-ServerDistribution` positivo14, negativos e instalación/actualización/Restore.
3. Preservar fixtures Python históricos que fijan artefactos13; adaptar sólo pruebas activas al nuevo contrato. El ensayo nuevo ya demuestra arranque13 rechazado, bootstrap14 y migración13→14 real, sin reescribir resultados históricos.
4. Recuperación CLI completa14, instalación Windows limpia, enrolamiento/proveedor real/M4/M5/M6 y QA/adopción siguen pendientes. No se ejecutó `--recover-admin` ni instalación elevada desde esta revisión.

Evidencia/comandos/resultados: `evidence/s1-20261023/m3-correcciones-codex/CIERRE.md`. Laboratorios detenidos, fuentes y DLL inmutables. No se tocó QA ni se hicieron commits. **Avance global aproximado78%, sin incremento por el recuento de pruebas.**
