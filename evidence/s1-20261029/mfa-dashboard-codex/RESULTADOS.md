# Resultado · MFA del dashboard y gracia45

29.10.2026. Trabajo autorizado por Wascar. Decisión actual:45 días, existentes desde rollout persistido, nuevos desde creación; administrador global Systemhaus exento por capacidades globales y con desactivación propia permitida. [Decisión](../../../docs/DECISION-MFA-GRACIA-45-DIAS-29-10-2026.md), [resumen](../../../docs/MFA-DASHBOARD-GRACIA-45-29-10-2026.md).

## Implementación y separación

- Agente backend: SQL015, MfaAccountManagement y sus14 pruebas. Consultas/acciones self/admin, sesión MFA para administrar otros, contraseña actual propia, ETag/revisión de Systemhaus, idempotencia, revocación/auditoría transaccionales y rollback.
- Agente frontend: MfaAccountPanel/MfaReminder, adaptador, textos EN/DE/ES,48 pruebas y runner de navegador. IndexedDB sólo conserva intención pública, nunca contraseña, TOTP o semilla.
- Coordinador: enforcement de vencimiento en login y sesiones antes/después de locks, activación persistida sólo tras proveedor real explícito, rutas/OpenAPI, integración ServerApp/AdminUsers/navegación,7 pruebas de vencimiento y3 HTTP más escenario Browser. SQL001–014 y dependencias no cambian. RecoveryAdministrator y el comando local verifican el esquema actual15.
- Revisor distinto: fuente congelada,12 focos propios y1 de respuesta perdida; dictamen y adenda para F-07.04 en [review/REVISION.md](review/REVISION.md). No se atribuyen al revisor ejecuciones PostgreSQL, HTTP, Browser o VM.

## Ejecuciones finales

| Ejecutor | Comprobación | Resultado |
|---|---|---|
| Coordinador | Restore locked y build Release, copia privada, SDK10.0.401 |0 errores/advertencias; binlogs privados|
| Coordinador | Quality, salvo los dos Browser opt-in |378 PASS,0 FAIL,1 Docker omitida;379 resultados|
| Coordinador | Edge/Kestrel/PostgreSQL17.11, UI real y runtime DML |1 PASS,8 etapas,0 excepciones JS; Browser separado de Quality|
| Coordinador | Node API/MFA/QR/textos/nuevo panel/onboarding |101 PASS,0 omitidas; incluye48 nuevas, no sumar dos veces|
| Coordinador | Guía QA |35 PASS;131 casos, cinco nuevos planned|
| Agente backend | Gestión MFA aislada |14 PASS con PG17.11; son parte de Quality, no otras14|
| Revisor | Focos de contrato y respuesta perdida |12+1 PASS; fuente/Node, no PG|

Los21 primeros focos,3 HTTP y83 regresiones de fixtures son subconjuntos ya incluidos en el Quality final; no se suman a378. Docker no está disponible y su omisión no cuenta como prueba de PostgreSQL. Las pruebas nativas sí usaron PostgreSQL17.11 nuevo.

Comandos: `dotnet restore --locked-mode`, `dotnet build -c Release --no-restore`, y `dotnet test -c Release --no-build --no-restore`, siempre con `-bl:<privado>/...-{}.binlog`. Filtro Quality final: `FullyQualifiedName!~MfaBrowserGuiTests&FullyQualifiedName!~BrowserDashboardShowsGrace`. Browser ejecutado aparte con `FullyQualifiedName~BrowserDashboardShowsGrace`, frontend privado construido y variables explícitas de laboratorio. Node: api.test, mfa-api.test, mfa-words.test, mfa-qr.test, mfa-account.test y test_admin_user_onboarding. Guía: `python -B tools/windows/qa_guide.py` y `python -B -m unittest tools.tests.test_qa_guide`.

El apuntador .local/mfa-dashboard-current.json identifica snapshot, logs, TRX y frontend. Conexión de laboratorio/binlogs permanecen privados. Se preservan los intentos fallidos y la salida final en rutas distintas.

## Fallos encontrados y correcciones

1. El autor backend detectó que jsonb normalizaba el recibo entre primera respuesta y replay. Se usa `INSERT ... RETURNING result_json::text` en la primera respuesta; se conserva la aserción de igualdad exacta.
2. La revisión reprodujo avisos que trataban al administrador exento como vencido y al enrolamiento obligatorio como simple gracia. Se corrigió la prioridad del aviso y su color; se conservan focos rojo/verde. El recibo histórico se separa de estado actual, evitando logout repetido tras reautenticar.
3. Primer Browser: aviso35 correcto, fallo de idioma por permitir cambios mientras se guardaba preferencia. Se añadieron disabled del selector y estado de preferencia en Mi seguridad; el runner espera confirmación antes de cambiar otra vez.
4. Segundo Browser: seis etapas correctas, reset429. El límite productivo10/minuto funcionó correctamente. El runner programa una pausa62s antes de crear/enviar el reset; no cambia reloj, límites ni reintenta mutaciones automáticamente. Tercer Browser: ocho etapas PASS.
5. Primer Quality completo:318 PASS,60 FAIL,1 Docker omitida. Cinco fixtures seguían aplicando SQL001–014; les faltaba SQL015 requerida por el código nuevo. Se añadió015 explícitamente, preservando negativos y SQL antiguos; la prueba de hueco de migración conserva el hueco14 y actualiza su recuento esperado a14 de15. Los83 focos afectados pasan y el Quality final da378 PASS/0 FAIL/1omitida.

No se presentan intentos fallidos como ejecuciones válidas. Tampoco se oculta la pausa del runner ni se atribuye el429 a fallo de MFA.

## Alcance pendiente

HTTP loopback y proveedor sintético sólo DI en Browser; no servicio real/HTTPS productivo o lectura nueva bajo SID del servicio en esta tanda. La lectura anterior que aportó Wascar se conserva en su evidencia propia. Recuperación del último administrador, códigos/sobre operativo, distribución15, instalador y QA/adopción no se cierran.

La SQL015 se probó en bases nuevas y fixtures de cuentas antiguas; la migración de una instalación Windows14 existente, backup/restore y su recuperación completa requieren el ensayo de la candidata. No se tocaron VM, servicios/cuentas Windows, firewall, certificados de confianza, instalación QA, paquetes históricos, commits o push.

Las cinco entradas QA nuevas permanecen planned;126 casos anteriores y sus resultados/observaciones de navegador no se sobrescriben. Racks primero y reorganización general de usuarios quedan en su registro propio.
