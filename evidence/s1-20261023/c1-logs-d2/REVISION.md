# Revisión independiente · C1 logs y D2 · 23.10.2026

Revisor: `method_git_readonly23`, distinto del implementador de la prueba y del autor del dictamen. Secuencial: se suspendieron las ediciones del coordinador durante la revisión; el revisor escribió sólo sus artefactos privados de ejecución.

**Dictamen FAVORABLE para el grupo C1 y su documentación**, con los límites siguientes. Sin hallazgos nuevos bloqueantes en la prueba/README. **D2 sigue NO APROBADA en su forma propuesta:** acceso del servicio incompatible con ACL declarada y recuperación administrativa aún no demostrada. La revisión admite vías alternativas verificables —incluidos mecanismos de recuperación que no necesiten la clave ilegible—; no declara imposibilidad absoluta ni haber ejecutado el SID real de RackClick.

## Ejecución propia

- Fuente final `test_c1_log_secrets.py`, SHA `7591737e2fac566751cb7cb6eb553b6325a31e642092a1295df49dcba87e6114`.
- Ejecutó `--mode all` en Windows Job Object privado, timeout600, contra el baseline7b4f3e8/DLL `43e49045bd28d9fe62ca8afc05f49fb5ad2b96150bc02b2f76a3faca912a97ff`.
- **10/10PASS, exit0**, PostgreSQL17.11 medido; `labStopped`, `inputsUnchanged`, `dllUnchanged` verdaderos. Resultado saneado copiado como `reviewer-tests.json`. No se ejecutó el código concurrente M3 ni se reconstruyó el producto actual.
- Negativo del autor inspeccionado, **1FAIL/0ERROR** debido a la aserción del marcador contaminante, no a un fallo de fixture. No se repitió ese negativo ni se cuenta como positivo funcional.
- Reconstruyó `git archive` en memoria: SHA `2670b805efd2419cb35c9f621a633c1e8f13ce4dbc57cb53db04695474c1747d`, y comparó los250archivos regulares del snapshot, sin diferencias.

## Lecturas y comprobaciones

Propuesta/dictamen D2, fuente y resultado del ensayo nativo, prueba nueva y helpers congelados, README/diff, adenda C1 y evidencia. Contrastó los dos bloqueos con fuentes primarias Microsoft enlazadas en el dictamen: DPAPI LocalMachine y DACL. La reproducción nativa DPAPI del autor se revisó sin afirmar otra ejecución bajo cuenta/host diferente.

Único P3: `frozenInputFiles:261` del recibo privado contaba entradas ZIP, incluidos11directorios. Corrección acordada exclusivamente en el resumen público: `sourceArchiveEntries:261`, `regularSourceFiles:250`. Se conserva sin reescribir la procedencia privada. No afecta al código probado, DLL ni archivo ZIP.

## Hashes revisados

```text
7591737e2fac566751cb7cb6eb553b6325a31e642092a1295df49dcba87e6114  development/server/tests/test_c1_log_secrets.py
ab39a7282111b79c6588517923ac50ed7d0331c999a5209461f703d8c6cd6674  docs/REVISION-D2-CODEX.md
5caeb5a0682c293475314f7e1cd4d604030d28debcd19880f2a1dce56399f8fe  docs/C1-CONCILIACION-S38-S42.md
f4c07766017abed380ab18d24cf6dea998704452879a72c8bb8b4c419e7458c6  development/server/tests/RackClick.Quality.Tests/README.md
29877f5e636615b6cc57ee13057ea2da510f3d743b553a25ca2f22dff5396049  docs/DECISION-D2-CUSTODIA-CLAVE-TOTP.md
```

## Límites

Sin escrituras de producto/documentos por el revisor, cambios de cuentas/servicios/VM/QA/M1, publicación, escaneo de secretos ni binlogs públicos. No aprueba MFA/M3, ausencia universal de secretos, custodia portable operativa o cierre completo de C1. No suma sus diez repeticiones a los diez escenarios distintos. QA/adopción y global78% siguen pendientes/sin incremento.
