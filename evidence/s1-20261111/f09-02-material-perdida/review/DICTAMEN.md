# Dictamen independiente F-09.02 · paso 30

11.11.2026. **Favorable al cierre técnico exclusivo de F-09.02.** El recorrido interno `Prepare → Export → Apply → Publish` prepara y publica material nuevo, conserva el material anterior y los factores cifrados, retira del uso los ilegibles y fuerza pending. El fence se conserva. No quedan hallazgos bloqueantes abiertos en el alcance inspeccionado y repetido. No acredita operación nativa disponible, recuperación del servicio, F-09.03/.04/.05 ni los hitos completos F-09.

Revisor distinto del implementador. No se editó producto ni pruebas compartidas. Única salida pública propia: este dictamen; auxiliares, TRX/binlog y credenciales sintéticas privados bajo `.local/`. Sin D/E, VM, servicios/cuentas Windows, instalaciones, commits o push. El coordinador autorizó un clúster propio con roles PostgreSQL y cuentas app sintéticas para la repetición; quedó detenido.

## Bytes y comparación

Freeze: `.local/f0902-5221c47e/freeze/development/server`. Pines verificados antes y después del ensayo:

| Artefacto | SHA256 |
|---|---|
| Server y copia cargada por las pruebas | `69ed57d2ae0d84d633f0fd962c6d140fa4ac53da3eaabff4d3f0ac3f94ff3de8` |
| Tests | `dce2518cd81834bd7dde99143bcf28ed9dea436e752091fcefe2aa757f9ef953` |

Comparación propia del manifiesto previo de228 archivos:224 idénticos, cuatro modificados, ninguno ausente. Cambian `MfaMaintenanceCoordinator.cs`, `MfaRotationCoordinator.cs`, `SchemaMigrations.cs` y `MfaEmergencyRecoveryCommand.cs`. En este último se comprobó por reconstrucción/hash que sólo cambia `private → internal` de `AuthorizationFailure`. Diez fuentes/pruebas asignadas coinciden entre raíz y freeze. SQL014/046, writer, Program y dependencias del manifiesto previo permanecen idénticos. Sello privado: `.local/f0902-review-source-seal.json`.

## Hallazgos corregidos

| Gravedad inicial | Hallazgo | Contraste final |
|---|---|---|
| P1 | Backup con versión requerida ausente del anillo y no declarada perdida podía quedar sin cobertura. | Plan exige cobertura de dependencias no perdidas. Backup-only90 rechaza antes del fence; declarar90 perdida conserva/identifica el backup y selecciona91. Ambos casos pasaron en repetición propia. |
| P2 | Testigo parcialmente revalidado: autoridad/alcance podían diferir del plan manteniendo su hash. | Binding completo de instalación/DB/Systemhaus/SID, modo/autoridad, versiones, conteos, fecha y hashes. Alteraciones SID/nueva versión/versiones perdidas rechazan Publish; casos propios PASS. |
| P2 | Publish aceptaba un hash de sobre alterado en el testigo sin referencia independiente. | Pin privado inmutable `loss-envelope-pin` ligado a plan/material/sobre antes de DB; reentrada/Publish lo exigen. Alterar sólo `envelope_sha256` rechaza; caso propio PASS. |
| Observación de robustez | Hash y autenticación sobre byte[] mutable del llamador. | Apply usa una copia propia acotada≤1MiB para ambos y la pone a cero; codec histórico intacto. |

Los rojos y la mutación del coordinador se inspeccionaron como evidencia registrada; **no se ejecutaron por el revisor**. No se atribuyen como propias sus144 pruebas. Sus incidencias de rutas/timezone/build incremental permanecen declaradas en RESULTADOS y no se presentan como verdes. La repetición propia usó los pines definitivos.

## Pruebas propias

Windows, SDK10.0.401 fijado, PG17.11 nuevo, owner/runtime separados, DPAPI y ACL reales bajo identidad/trust de fixture. El lector/SID de fixture no equivale al SID efectivo de un servicio instalado. Sin contextos F06.

```text
dotnet test tests/RackClick.Quality.Tests/RackClick.Quality.Tests.csproj
  -c Release --no-build --no-restore
  --filter FullyQualifiedName~MfaLossReset
  --logger trx;LogFileName=<privado>/independent.trx
  -bl:<privado>/independent-{}.binlog
```

**30 ejecutadas /30 PASS /0 FAIL /0 omitidas; exit0**: nueve de selección/capacidad y21 de componentes. Sin compilación propia. Driver `.local/f0902-review-run.py`; resultados `.local/f0902-review-output/independent-sanitized.json`, SHA256 `2d90add42ae6d50db6751083f3030681056df9d44e8c6d3992d5247350b4a39d`. TRX SHA256 `410f3eaaf24e0dbfd5faf0e5ec98501ae656167427b10667b081a7cb0a08a2f1`. Binlog privado existente de353827bytes. Clúster `.local/labs/f0902-review-78a1c8ca59ce4fd88ac4aa4864e12a40` detenido y sin postmaster.pid; casos nuevos `.local/f0902-review-c` conservados.

La repetición acredita:

- Active/pending/disabled, global y cuenta inactiva: archivo de filas cifradas completas, retiro sólo de las perdidas, required/pending/revisión y revocación de los afectados. Cuentas/grupos/gracia, factor legible y centinelas de cliente/rack/equipo conservados. La cuenta inactiva sigue inactiva.
- Autenticación de almacén de global/ordinario afectados entrega sólo desafío enroll, sin sesión. No fue HTTP de un host recuperado ni confirmación del factor nuevo.
- Total de blobs ilegibles con anillo fiable, uno vacío: nueva versión8 publicada, originales y fence preservados. Clave físicamente ausente ensayada en el negativo de sustitución del candidato: no se reconstruye ni cambia DB. No se afirma un positivo completo con carpeta desaparecida.
- Rollback SQL inducido sin seguridad parcial/testigo/archivo DB residual; candidato/fence conservados. Cambios posteriores al plan de usuario/política/código rechazan antes del commit.
- Interrupciones lógicas tras commit o publicar clave mediante excepciones de checkpoint; reentrada hacia delante por UUID sin repetir revisión. No fueron Kill, apagón ni reinicio.
- Sobre/candidato/testigo alterados rechazan. Backup real retenido declarado perdido conserva bytes y versión identificada; sobre nuevo no recupera claves viejas. Compatibilidad de mantenimiento/rotación sobre47 conservada.
- Grants amplios de public no abren rackclick_private: SELECT del archivo y DELETE del testigo con runtime fallan42501. Las cuatro entradas nativas rechazan el token estándar observado antes de SCM/SQL.

Sonda CLI adicional propia sobre el ServerDLL fijado, con configuración de host deliberadamente inválida: `--mfa-emergency-recovery` devuelve exit1, `mfa_emergency_not_authorized`, stage authorization, cero operaciones, ninguna sesión y stderr vacío. `.local/f0902-review-cli.json`, SHA256 `18d175f4c37c441b2543782b0fd2cd67538d3586e9f0c19884c954d9ff386fe6`. La transición autorizada sigue bloqueada por código inspeccionado; **no se ejecutó con token elevado/SYSTEM**.

## Archivos y símbolos consultados

- Gobierno: AGENTS, BRIEFING-MAESTRO, CONTINUIDAD-CODEX, EQUIPO-Y-SKILLS, README del servidor; consulta pertinente de CONTRATO-SERVIDOR-v0.1, MAPA-RC9-R3, ACEPTACION, INICIO-IMPLEMENTACION-S1 y PROGRESO-GLOBAL. D2 §1/§2.2/§4, ledger F09, plan numerado29–33 y planes F0901/F0902; resultados/focos/mutación/matriz/pines de la tanda.
- `MfaLossResetCoordinator.cs`: entradas nativas, Native, RunCore/RunExclusiveCore, RequirePlan/RequireWitness, RequireLostAndRetained, AuthenticateRetained y VerifyEnvelope; seams de fixture separados de las rutas productivas.
- `MfaLossResetDatabase.cs`: NextVersion, LockAsync/RequireAsync, PlanAsync, SnapshotAsync, ReadWitnessAsync/RequireWitness, ApplyAsync y ArchiveHashAsync. SQL047 completo: testigo metadata separado del archivo cifrado; archivo sin FK al usuario/factor vivo.
- `WindowsMfaMaintenanceStore.Loss.cs`: censo, PrepareLoss, ReadLossJournal, VerifyLossOriginal, Inspect/RequireLossMaterial, Pin/RequireLossEnvelope y PublishLoss. Parciales previos: constructor/lock/catálogo/anillo y preparación/publicación/guardas de rotación.
- `MfaRotationCoordinator.cs`/Database: Prepare/Resume/Exclusive, binding, locks, snapshot, rewrap y testigo; `MfaMaintenanceCoordinator.cs`: OwnerConnection/ValidateDatabase; `MfaMaintenanceAdmission.cs` y `MfaRotationStartupGuard.cs`; `WindowsMfaMaintenanceService.cs`: RequireStopped/ValidateObservedState.
- `WindowsMfaKeyStoreWriter.cs`: CreateStoreFromMaterial/CreateInitialStore, StageMaterial y ProtectVersionMaterial; `MfaEmergencyRecoveryCommand.cs`: AuthorizationFailure/DenialForToken; SchemaMigrations y SQL014/015/046. MfaKeyRetention/inventarios, MfaBackupCatalog.Parse/Open y codecs de sobre/payload.
- PostgresStore.Authentication (prioridad pending), MfaStore.Enrollment/Recovery, consultas pertinentes de MfaGraceEnforcement/MfaAccountManagement; grants RackClick.Instance.ps1 y pg_support.py. MfaLossResetVersionTests/MfaLossResetTests y lectura pertinente de pruebas anteriores de rotación/autorización.

Grafo rackclick-desarrollo, generación2026-11-11T12:28:46Z: cobertura consultada en páginas de cinco rutas. SQL014/046 con parse parcial; las seis rutas nuevas faltan en esa generación. Se leyeron fuentes directas y fijaron bytes. No se reindexó ni se tomó la señal best-effort como prueba de completitud.

## Límites y recomendación

No se ensayaron positivos elevados/SYSTEM, servicio/SID efectivo, guard/arranque loss-reset, liberación del fence, HTTPS/login del host perdido, reenrolamiento completo posterior a pérdida, reinicio/apagón, custodia física del sobre ni durabilidad universal disco/DB. No se integra instalador/backup-role/Restore47. Sin metadata fiable no se implementa aquí alternativa de namespace nuevo. El archivo preserva ciphertext; no demuestra descifrado sin claves anteriores ni sustituye backup/sobre externo. Los límites D2 frente a administrador/SYSTEM/servicio comprometido se mantienen.

El compuesto técnico de F-09.02 queda satisfecho y es elegible para done/+1/2 tras conciliación del coordinador. F-09.03/.04/.05 y los seis hitos completos mantienen su alcance pendiente. No se añaden puntos por pruebas ni porcentaje global nuevo, ni se adopta candidata u operación de emergencia para Wascar.

