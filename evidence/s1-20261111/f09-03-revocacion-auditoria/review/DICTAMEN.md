# Dictamen independiente F-09.03 · paso31

11.11.2026. **Favorable al cierre técnico exclusivo de F-09.03.** Revocación efectiva de credenciales anteriores, auditoría dedicada sin secretos y recuperación del único global mediante factor nuevo contrastadas sobre los binarios finales. No quedan hallazgos bloqueantes abiertos dentro del foco repetido. No acredita CLI habilitada, arranque/servicio recuperado, F-09.04/.05 ni los seis hitos completos F09.

Revisor distinto del implementador. No se editó producto, pruebas o metadatos compartidos. Salida pública propia exclusiva: este dictamen; auxiliares privados `.local/f0903-review-*`. Sin D/E, VM, cuentas/servicios Windows, instalaciones, commits o push. Roles y cuentas app sintéticas se crearon exclusivamente en dos clústeres PG17 nuevos propios y ambos quedaron detenidos. El dictamen provisional inicial fue sustituido tras la repetición; no equivalía a aprobación.

## Contrato y decisión de auditoría

F-09.03 exige «Revocar sesiones/desafíos y registrar auditoría sin secretos, preservando recuperación de último administrador». Plan numerado031 dice «Contrastar cierre; puede existir implementación». Se reutilizan las revocaciones y SQL047 de paso30; la extensión de evidencia cierra su criterio específico.

D2 §2.2.4 exige retiro/pending/revisión, sesiones/desafíos/códigos revocados, preservación de cuentas/capacidades/ámbitos/gracia y autoridad local/alcance/marcador dentro de una transacción. §4.1 prescribe registro dedicado `windows-local` y prohíbe inventar un actor de aplicación para `audit_event`.

`rackclick_private.mfa_loss_operation` satisface esa auditoría: operaciónUUID única, modo/autoridad, instalación/DB/Systemhaus/SID, versiones, hashes, conteos y fechaUTC. Su resultado es el **commit DB de la transición loss-reset**, no servicio recuperado ni recuperación individual finalizada. `ApplyAsync` lo escribe en la transacción del archivo/retiro/pending/revocación. No necesita proyección a `audit_event` con appactor inventado.

El ciphertext anterior se conserva en el archivo privado separado; no en el testigo. SQL047 revoca PUBLIC al schema/tablas; no se amplía acceso runtime al archivo ni DML del testigo. La lectura de un futuro guard de arranque mantiene su alcance posterior.

## Bytes y comparación propia

Freeze: `.local/f0903-79ddc76e/freeze/development/server`. Pines comprobados antes y después de ambas ejecuciones propias:

| Artefacto | SHA256 |
|---|---|
| Server y copia cargada por las pruebas | `2cbce09aa94b7bd646d0ea8a34fee5c2fc00081c889c7b19bb406c46e9bed9fc` |
| Tests | `a3cb231a046e6429d99ec57856250a3da597ec99743d022fbe5b965c8355da86` |

Comparación propia contra FUENTES de F0902: **231/232 archivos de producto previos idénticos**; sólo cambia `MfaLossResetDatabase.cs`. Nueve archivos de pruebas previos y diez referencias conservados. SQL001–047, Program, CLI, dependencias y escritor/proveedor previos no cambian en ese manifiesto. Raíz y freeze coinciden para todas las fuentes de servidor comparadas y para el nuevo `MfaLossRevocationTests.cs` (SHA256 `7258026a292c5e412a152d263090ca9be7e97d780ebbe2c4e808f10046fa4845`). Las referencias fuera del servidor se compararon contra su hash previo, no contra una copia ausente del freeze. Frontend no se ejecutó ni se selló por el revisor.

Sello privado `.local/f0903-review-seal.json`, SHA256 `71784540e07e1fae202647807acfe25d5871eaad2e33718faad62ff40f1d9a1a`. Se repitió al terminar la ejecución. No se pretende sellar todo el árbol concurrente ajeno al manifiesto.

## Hallazgos y contraste final

| Gravedad inicial | Hallazgo | Contraste final |
|---|---|---|
| P2 funcional, escenario SQL inducido | La primera Apply devolvía el testigo recién escrito sin exigir binding/conteos completos antes de commit. Supresiones silenciosas de escrituras o metadata alterada podían comprometer una transición incompleta; Publish rechazaba después. | Se exigen filas de archivo/pending igual a factores planeados, finish exactamente1, RequireWitness fresco y hashes post/archivo antes de devolver/commit. Nueve casos discriminantes propios PASS, incluidos cero afectados y testigo alterado; todos comprueban rollback. |
| P2 de evidencia, sin vulnerabilidad previa demostrada | Paso30 contaba revocaciones y entregaba enroll, sin usar realmente credenciales viejas tras pérdida local. | Sesión y actor antiguos rechazados; verify/enroll/confirmación con desafío antiguo y canje de código anterior rechazados. Contraseña incorrecta no emite sesión; correcta entrega sólo enroll. Otra cuenta conserva sesión. Caso propio PASS. |
| P2 de evidencia, sin vulnerabilidad previa demostrada | F08 completaba recuperación por código; faltaba retorno del único global después de pérdida local. | Un único global conserva identidad/capacidades/gracia, no accede mientras pending, confirma TOTP nuevo versión8 y recibe sesión/CSRF nuevos; administra y conserva last_admin_required. Caso propio PASS. |

Los triggers de supresión/corrupción son inyecciones del fixture en DB nueva, no triggers encontrados en una instalación real ni una prueba de explotación por runtime. La corrección valida resultados inesperados de las escrituras ensayadas; no promete detectar cualquier manipulación arbitraria de un administrador DB comprometido.

Rojo limpio del coordinador inspeccionado:14 ejecutados,5PASS/9FAIL; los nueve muestran `No exception was thrown` en supresión de factor/sesión/desafío/código/pending/archivo/actualización de testigo, testigo sin afectados y SID alterado. El primer rojo del coordinador tenía además un fallo de fixture por factor activo sin confirmed_at al generar códigos; no se atribuye como defecto de producto. La repetición posterior aisló los nueve negativos pertinentes. No se ejecutó el rojo ni una mutación por el revisor. Sus52/52 finales se leyeron en final-sanitized.json; tampoco son pruebas propias.

## Pruebas propias ejecutadas

Windows, SDK10.0.401 fijado, PG17.11 nativo nuevo; identidades owner/runtime separadas, DPAPI/ACL reales con confianza/SID de fixture. No son SYSTEM/elevación positiva ni SID efectivo de un servicio instalado. Sin compilación, restore o suite completa propia.

```text
dotnet test tests/RackClick.Quality.Tests/RackClick.Quality.Tests.csproj
  -c Release --no-build --no-restore
  --filter FullyQualifiedName~MfaLossRevocationTests|FullyQualifiedName~CommitFailureRollsBackEveryDatabaseEffectAndKeepsCandidateAndFence
  --logger trx;LogFileName=<privado>/independent.trx
  -bl:<privado>/independent-{}.binlog
```

Driver `.local/f0903-review-run.py`, toolchain de pg_support, variables explícitas de fixture y parada en finally; sin fallback a instalación existente.

**Corrida definitiva:15 ejecutadas/15PASS/0FAIL/0omitidas, exit0.** Catorce casos nuevos y un rollback histórico. Acreditan:

- Nueve supresiones/corrupciones inducidas rechazadas antes del commit: seguridad/cuentas intactas, sin testigo ni archivo DB residual y fence conservado. Incluye actualización del testigo con cero factores.
- Testigo con conjunto exacto de diecinueve campos de metadata, conteos previstos, autoridad/SID y fecha; sin contraseñas, tokens, códigos o bytes de claves del fixture. Sin `audit_event` atribuido al afectado. Reentrada de Apply/Publish sin duplicar ni cambiar el testigo; no afectados y desafíos ya consumidos conservados.
- Sesión/actor, desafíos verify/enroll/confirmación y código antiguos sin acceso después de pérdida; cuenta ajena conserva su sesión. Contraseña errónea rechazada y contraseña correcta sólo enroll.
- Único global: identidad/autoridad/gracia conservadas; pending, desafío e inicio de enrolamiento sin API; código TOTP inválido sin sesión; TOTP nuevo válido da sesión/CSRF nuevos, permisos y administración, factor en versión8 y rechazo last_admin_required con rollback.
- Fallo SQL del INSERT o UPDATE de auditoría revierte revocaciones sin suplantar actor. Rollback histórico del paso30 también PASS.

Resultado privado `.local/f0903-review-output-b797974a/independent-sanitized.json`, SHA256 `b0460f5f3f13c9dc3230bc2193973e324e0b99d3061e34fc7f11fab53e39d318`; TRX SHA256 `93e0b79ec1485af5dab606ea8da110bd624faa5b80f8ce44e8bd181090fb9277`; binlog privado existente353967bytes. Clúster `.local/labs/f0903-review-4eb588d9b4e3419495ee93ee18c4462d` detenido y sin postmaster.pid; casos `.local/f0903-review-8` conservados.

**Incidencia propia conservada:** primera corrida15/15FAIL por `mfa_loss_path_too_long` en PrepareLoss antes de la transición: el driver eligió una raíz de fixture demasiado larga. Pila y guarda Win32 contrastadas; se acortó sólo la raíz privada, sin tocar producto ni recompilar. Esa corrida no acredita los negativos de revocación ni un defecto nuevo de producto. Resultado `.local/f0903-review-output-86b43c80/independent-sanitized.json`, SHA256 `40b6e444d60736a8292327258275c42a67eb9111e5322f7283021661c8ab16a5`; clúster propio484223d6… detenido. Los bins conservaron los mismos pins en ambos intentos.

## Archivos y símbolos consultados

- Gobierno/alcance: AGENTS, BRIEFING-MAESTRO, inicio vigente de CONTINUIDAD-CODEX, EQUIPO-Y-SKILLS; consulta pertinente de INICIO-IMPLEMENTACION-S1, CONTRATO-SERVIDOR-v0.1, MAPA-RC9-R3, ACEPTACION, PROGRESO-GLOBAL y README del servidor. D2§2.2/§4 completos, ledger F09/F0903, plan numerado031–033 y planes F0902/F0903.
- Paso30: RESULTADOS, MATRIZ-CRITERIO, FUENTES, FOCOS y review/DICTAMEN. Paso31: fuente/pruebas finales, manifiesto previo, pines y TRX/red-clean/final-sanitized privados del coordinador.
- `MfaLossResetDatabase.cs`: PlanAsync, LockAsync/RequireAsync, SnapshotAsync, ApplyAsync, ReadWitnessAsync/RequireWitness, ArchiveHashAsync. SQL047 completa y comparación de su hash previo.
- `MfaLossResetCoordinator.cs`: rutas nativas/fixture, RunExclusiveCore, ExportCore, RequirePlan/RequireWitness, AuthenticateRetained; `WindowsMfaMaintenanceStore.Loss.cs`: PrepareLoss y guarda de rutas; `MfaRotationDatabase.cs`: LockAsync y lista de tablas.
- `PostgresStore.Authentication.cs`: AuthenticateCore y prioridad pending; `MfaStore.cs`: CompleteVerify/RevokePendingChallenges; `MfaStore.Enrollment.cs`: StartEnrollment/ConfirmEnrollment/LockChallenge/WriteAudit; `MfaGraceEnforcement.cs`: gracia/exención y EnforceMfaGrace.
- `MfaAccountManagement.cs`: ChangeMfaAccount/estado/ReadOwnMfaStatus; `AdminUserState.cs`: guarda last_admin_required. `MfaLossResetTests.cs` y Fixture, `MfaLastAdministratorRecoveryTests.cs`, clase nueva `MfaLossRevocationTests.cs` completa; pg_support.py (toolchain/Lab/aislamiento/parada).
- Skills aplicadas: verification-before-completion, binlog-generation y systematic-debugging para la incidencia propia de ruta. No se usó grafo ni se afirma cobertura de indexación.

## Límites y recomendación

No se ensayaron positivos Windows elevados/SYSTEM, servicio/SID efectivo, CLI funcional, guard/startup loss-reset, retirada del fence, HTTP/HTTPS de host recuperado, reinicio/apagón, durabilidad universal DB/disco, pérdida total de carpeta sin censo fiable, custodia física del sobre o adopción de Wascar. No se integra instalador/Restore47 ni se atribuyen como propias regresiones históricas completas. La recuperación individual ensayada es backend/almacén sobre provider publicado; el fence sigue conservado y no equivale a servicio reanudado.

F-09.03 es elegible para done/+1/2 tras conciliación del coordinador. Índice recibido25,63/100 del cierre restante; sólo ese checkpoint permitiría26,13/100. No son porcentaje global nuevo del producto, crédito por pruebas o aceptación operativa. F-09.04/.05 y los seis hitos completos permanecen pendientes.
