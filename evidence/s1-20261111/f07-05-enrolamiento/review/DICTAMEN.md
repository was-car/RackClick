# Dictamen independiente · F-07.05 · enrolamiento restringido

11.11.2026. Revisor `rackclick_security`, distinto del autor de la nueva prueba y del runner. Producto en sólo lectura. Escrituras propias limitadas a este dictamen y a la salida privada de su laboratorio nuevo. Sin operaciones sobre D/E, VM, servicios, cuentas o bases instaladas, credenciales del usuario, commits o publicación.

**Dictamen favorable al cierre técnico de F-07.05 con su peso existente de 1/2 punto.** El criterio literal queda cubierto por la evidencia anterior contrastada y las comprobaciones actuales. No se identificó un hallazgo P1/P2 pendiente dentro del alcance revisado. El revisor ejecutó por su cuenta los dos escenarios nuevos, ambos PASS y sin omisiones; no se atribuye la regresión ni Node del coordinador.

## Criterio y alcance

Se contrastó literalmente F-07 de `docs/PLAN-CIERRE-RACKCLICK.json`: usuario nuevo completa primer factor, recibe una única sesión nueva sólo al confirmar; desafío/enrolamiento incompleto sin acceso a /me, clientes o mutaciones; negativos concurrentes y revisión distinta.

Rige gracia45/exención global confirmada el 29.10. El caso de cuenta nueva usa una fecha de creación sintética cuyo plazo ya venció; el caso existente conserva NULL histórico y obtiene el plazo desde activación persistida. Ninguno introduce MFA inmediato para todas las altas. Las capacidades globales y la activación voluntaria conservan sus controles anteriores, además de la regresión actual de gracia.

La brecha inicial era de cobertura conjunta: el negativo HTTP histórico probaba /me y logout, sin toda la matriz de clientes/mutaciones y estados. No se demostró un defecto de producto. Los fallos de owner.pgpass, columna owner_id y copia de esbuild fueron de preparación/fixture y se conservan como tales; no son una fase roja de un arreglo de producto.

## Ejecución propia

Se inspeccionaron antes de ejecutar `MfaEnrollmentClosureTests.RestrictedEnrollmentWorker`, el runner y el helper `pg_support.Lab`. Se repitió únicamente:

```powershell
C:/Python312/python.exe -B tools/tests/run_mfa_enrollment_closure.py --source-root C:/RackClick_SVR/.local/f0705-33db9a25/freeze --expected-server-sha256 1a6cb30d7a74efa7760c6ea88c46adfac4674c84071b9f88ea023ac2117aef06 --expected-tests-sha256 801d965a11d73165764aa579fd75c6c7ea163cc0cd53ccb9bcd1d9c061e3c8ec --mode closure
```

Salida 0; PostgreSQL17.11 nuevo, dos bases46 propias; **new-account-due: 1 PASS; existing-account-due: 1 PASS; 0 fallos/omisiones**. Se leyeron también los resultados individuales de ambos TRX: uno Passed en cada archivo, no sólo sus agregados. El clúster propio `f0705-enrollment-41c1e8f1157948689e73254d73a2ea07` quedó detenido. No hubo restore/build propios ni repetición de los36casos o70Node.

La prueba comprueba en cada escenario:

- Contraseña incorrecta401, sin cookie, desafío o sesión; contraseña válida202/enroll, sin sesión API.
- Tres estados: desafío inicial, factor pending y TOTP rechazado. Cuatro rutas en cada estado: GET /me, GET /customers, POST /customers y POST /me/preferences; tanto con cookie MFA como con su token renombrado Session. Las24peticiones por escenario dan401, sin cookie de sesión y con el snapshot SQL invariable. No se cuentan como24funciones nuevas.
- Dos confirmaciones concurrentes: exactamente una200 y una401, un factor activo y una única sesión verificada. Token/CSRF nuevos respecto del desafío, hashes persistidos y atributos de cookies; /me y /customers200 sólo con la sesión obtenida. Replay401 sin segunda sesión.
- Proveedor Windows/DPAPI real: material1retirado/7activo y factor cifrado con7. Sólo se sustituye `IMfaHostIdentity` por identidad/confianza de laboratorio; no se registra un proveedor de claves sintético.
- El rol runtime se crea NOSUPERUSER/NOCREATEDB/NOCREATEROLE, separado del propietario; CREATE TABLE rechaza42501. El testigo SECURITY INVOKER registra `current_user` y `txid_current()` directamente durante las escrituras HTTP. Factor, consumo de desafío e inserción de sesión comparten la transacción que inserta esa única sesión; todos los actores observados son runtime. No se deduce ese hecho sólo de una cadena de conexión.

Identidades finales, verificadas antes y después de la ejecución:

| Archivo | SHA256 |
|---|---|
| RackClick.Server.dll | `1a6cb30d7a74efa7760c6ea88c46adfac4674c84071b9f88ea023ac2117aef06` |
| RackClick.Quality.Tests.dll | `801d965a11d73165764aa579fd75c6c7ea163cc0cd53ccb9bcd1d9c061e3c8ec` |
| MfaEnrollmentClosureTests.cs | `1b8feb2ef6ffd776b7392acd8efefacae90e2789f9efa7566a0cd66b89388b8a` |
| run_mfa_enrollment_closure.py | `9514e4a80bc65c961d7401fdaacc858541284edd774382e15c574b093d003973` |

Recibos propios privados, sin abrir contextos/pgpass/claves: `.local/f0705-review/closure-run.txt` SHA256 `81a1b64186b5a20bed77337dd0359c84991e8cdfb00c33653508818bfb576923`; `result-sanitized.json` del clúster propio SHA256 `1fa6486398bb14bbfd87ebcc4030af388609b7a521a6e72256ba505aec8d0231`. TRX new SHA256 `937d4ae5f4692207af50365a40bc722b2fda76aca3cf162d4a0ea197f60735e0`; TRX existing SHA256 `fd7a944df4d72e14d1c4632d6629f6c86dd8761b9055a2dcde89666d19b67af4`. Los binlogs, conexiones y material de laboratorio permanecen privados.

## Reutilización e identidad de fuentes

Se recalcularon las227entradas de producto de `evidence/s1-20261111/f06-04-cierre/FUENTES.json`: coinciden tanto con el árbol actual como con la copia congelada F0705; cero diferencias. La fuente final de la nueva prueba también coincide entre ambas. No se atribuye identidad binaria con C10 a una reconstrucción actual.

- **L1ronda2, 25.10:** revisión/recibos sustentan finalidad fija, TTL/hash/CSRF, locks, consumo único, confirmación/auditoría transaccionales y rollback. Los negativos actuales de caducidad tras espera, revocación concurrente, finalidades y dos confirmaciones se conservan en las36pruebas de regresión del coordinador.
- **GUI27.10 y dashboard29.10:** se conservan su alcance y fechas. La política actual `MfaGraceEnforcement` y `PostgresStore.Authentication` mantienen los hashes revisados; QR y CSS de login mantienen su identidad. La pantalla actual contiene recuperación y por eso no se presenta como idéntica a toda la GUI inicial.
- **Punto3, 02.11:** se leyeron `review/REVISION.md`, su adenda final y `MFA-EDGE.json`. Se recalcularon los hashes contra `COMPARACION-FUENTES-FINAL.json`: API, MfaChallengeForm, mfa-words, panel y módulos de recuperación actuales coinciden. La revisión final y Edge ya incluían enrolamiento y acceso sólo después de confirmar; no es necesario repetir navegador por esta ampliación de cobertura backend. Las70Node actuales complementan ese contraste, sin convertirse en navegador nuevo.
- **C10:** evidencia compuesta de enrolamiento/confirmación, siguiente login y verificación posterior al reinicio, HTTPS/proveedor real. El intentoB conserva su fallo posterior y sólo acredita su tramo completado; C y postboot mantienen sus positivos propios.
- **D11:** el smoke inicial fallido por MFA personal activado no se presenta como PASS. El recibo sintético posterior `demo50-auth-diagnostic/NATIVE-MFA-CARGADOR-02.json` prueba Windows/DPAPI/TLS normal con login202→verify200→me200→rechazo de ámbito global→logout204. Sus dos copias no son dos ejecuciones distintas.

Se leyeron los recibos saneados de este lote: `HTTP-ENROLAMIENTO.json` (coordinador2PASS), `REGRESION-NUCLEO.json` (36PASS), `FRONTEND.json` (70PASS/0skip) y `PIN-NEGATIVO.json` (pin incorrecto rechazado antes de crear laboratorio/ejecutar worker). No se presentan como ejecuciones propias ni se suman las dos repeticiones del mismo caso como casos funcionales distintos.

## Hitos y crédito

Es conciliable `implementation_complete=done` **para el resultado F-07 de enrolamiento restringido**: API/GUI públicas existentes, fuentes identificadas y flujo completado con persistencia real. No falta un operador de producto dentro de ese resultado; esta conclusión no cierra los operadores de recuperación/rotación de otros resultados.

`definition_confirmed` conserva su done previo. `technical_tests_same_scope` e `independent_review_same_scope` pueden quedar done con esta evidencia compuesta. `integrated_current_candidate` y `target_acceptance` permanecen pending para la candidata objetivo y aceptación instalada. El coordinador puede acreditar sólo F-07.05,1/2, conservando pesos, criterio, denominador y créditos anteriores. Este revisor no modifica ledger, QA ni porcentajes.

## Límites y archivos/símbolos consultados

Las pruebas nuevas son HTTP en memoria con cookies enviadas manualmente: no TCP/TLS, política efectiva de navegador, SCM ni token/SID efectivo de un servicio. DPAPI es real bajo confianza de laboratorio. Los fixtures históricos de regresión tienen su propio esquema/rol: no se extiende a todos ellos la cobertura conjunta46/runtime/DPAPI de los dos escenarios nuevos. No se prueban aquí cortes físicos de red/energía, memoria física, custodia externa, recuperación de último administrador, códigos completos ni integración/instalación46 o adopción. D/E y datos/factor personales permanecen fuera de la ejecución.

Consultados AGENTS, BRIEFING-MAESTRO, EQUIPO-Y-SKILLS, perfil security, lectura inicial/contrato/aceptación, ledgerF07, decisión45, plan/ficha23, RESULTADOS/MATRIZ/FUENTES y evidencias citadas. En producto: `Program` (composición, excepciones exactas del middleware y login/start/confirm/recover/me), `AuthenticateCore`/`AuthenticateForLogin`, `Session`/`RequireCurrentSession`, `StartEnrollment`/`ConfirmEnrollment`/`LockChallenge`/`ChallengeOpen`/`WriteAudit`, `MfaGraceDueSql`/`EnforceMfaGrace`/`EnsureMfaGracePolicy`, SQL015, composición Windows y `MfaTotp`. En pruebas: Enrollment/HTTP/Grace y la nueva `RestrictedEnrollmentWorker`; en GUI: `MfaChallengeForm`, API y módulos/textos/QR citados por sus manifiestos.

Hallazgos finales: **ningún P1/P2 de producto abierto dentro del alcance**. La brecha de evidencia queda cubierta; las limitaciones anteriores siguen explícitas. No se revisó todo el repositorio, historial, dependencias transitivas o rutas de aplicación ajenas a F-07, ni se afirma un escaneo general de secretos.
