# Dictamen independiente · F-06.01 · paso 19

09.11.2026 · Revisor Codex, distinto del autor del protocolo. Alcance asignado por el coordinador: revisión documental y contraste estático, sin ejecutar componentes. Único archivo escrito por el revisor: este dictamen.

**Favorable exclusivamente para F-06.01. Es suficiente acreditar +5/8 del criterio de ESPECIFICACIÓN**, tras conciliación del coordinador. El texto literal congelado en `docs/PLAN-CIERRE-RACKCLICK.json`, checkpoint F-06.01, exige «Especificar fases: persistir/verificar clave nueva antes de usarla, conservar versiones requeridas, reenvolver factores y publicar anillo coherente». Los documentos revisados satisfacen esas cuatro partes. No se acredita un rotador implementado, persistencia probada ni recuperación real ante caídas.

No cerrar F-06 completo ni sus hitos implementación, pruebas técnicas, revisión final del resultado completo, integración o aceptación. **definition_confirmed permanece pendiente**, porque F-06.02 aún debe concretar el censo/retirada. Esta revisión es sólo la revisión independiente del contrato F-06.01. No edité ledger, planes ni documentación compartida.

## Archivos y símbolos consultados

- Instrucciones/contexto: `AGENTS.md`, `docs/BRIEFING-MAESTRO.md` (salida de lectura extensa truncada; no se afirma lectura íntegra), `docs/PROGRESO-GLOBAL.md` (encabezado vigente). Estado Git comprobado antes de escribir: árbol concurrente con cambios y archivos sin seguimiento; los tres entregables del paso son nuevos/sin seguimiento. No se restituyó trabajo ajeno.
- Criterio: `docs/PLAN-CIERRE-RACKCLICK.json`, tarea F-06, sus hitos y checkpoints .01–.04.
- Entregables: `docs/PROTOCOLO-ROTACION-MFA-v1.md` §§1–8; `docs/PASO-019-FASES-ROTACION-MFA.md`; `evidence/s1-20261109/f06-01-fases/MATRIZ-CRITERIO.md`, `RESULTADOS.md`, `FUENTES-CONTRASTADAS.json`.
- Norma local: `docs/D2-CONDICIONES-TECNICAS-F03-02.md`, especialmente §4 y adenda de ruta; encabezado/adendas de `docs/DECISION-D2-CUSTODIA-CLAVE-TOTP.md`; `docs/REVISION-D2-CODEX.md`, condiciones de rotación disco/DB y límites históricos. La confirmación de custodia y las adendas prevalecen sobre frases históricas de decisión pendiente.
- Código: `MfaKeyRing.cs`: `Parse`, `RequireEntry`, `RequireState`, `EntropyFor`, `MaxVersions`, `MaxKeyVersion`; `WindowsMfaKeyProvider.cs`: constructor, `GetKey`, `GetActiveKey`, `ReadKey`, `LoadRing`, `Unprotect`; `MfaSecretCipher.cs`: `Seal`, `Open`, `Aad`, nonce/tag; `MfaStore.Enrollment.cs`: fragmentos `StartEnrollment`, `ConfirmEnrollment`, `LockChallenge`, SQL de factor y `WriteAudit`; `database/014-mfa.sql`: tablas factor, política, desafíos y códigos, leídas directamente.
- Fronteras de reutilización: `WindowsMfaKeyStoreWriter.cs`, búsquedas de API/creación/publicación y cuerpo `Publish`; `WindowsMfaKeyRecovery.cs`, cuerpo `Export` y búsqueda de `Recover`; `tools/windows/server-install/RackClick.MfaRuntime.ps1`, `Get-ServerMfaProfile`. No se atribuye revisión íntegra de cada auxiliar de bajo nivel.
- Evidencia previa: se contrastaron hashes de las doce entradas del manifiesto; lectura focal de resultados/límites L2h y dictámenes F05.05/F04-integración16. No se repitieron sus auditorías, recibos ni ensayos.

## Contraste arquitectónico

El anillo aditivo R+ conserva a activa e incorpora n como `retired`; Rf invierte sólo las activas previstas conservando las claves (§§2,4). Esto concuerda con el código: `RequireEntry` no filtra por estado, `GetKey(version)` abre la versión indicada y `GetActiveKey()` selecciona la única activa. `retired` permite lectura de n antes del commit sin elegirla para nuevos enrolamientos. No se inventa un estado `prepared`.

`StartEnrollment` usa la activa y puede reemplazar/reiniciar metadatos del factor; **no es un operador de recifrado reutilizable como tal**. El protocolo §5 conserva el mismo secreto y sólo modifica ciphertext/key_version, usando Open con AAD original y Seal con versión nueva, mismos Systemhaus/user, nonce aleatorio nuevo de 12 bytes y tag de 16. Preserva last_time_step, estado, intentos, bloqueo, fechas y política; incluye disabled/pending. Esto concuerda con las columnas SQL014 y evita reiniciar antirreplay o reactivar factores.

La separación de responsabilidades es explícita (§§3,7,8): proveedor/parser/cipher son piezas existentes; coordinador, publicador de anillo existente, migración/testigo, fence duradero y guard antes del listener siguen pendientes. El writer de creación exclusiva y las dos lecturas del exportador no se presentan como publicador existente ni instantánea estable. La ruta de §2 concuerda con constructor/profilado: raíz security y segundo nivel installationId antes de mfa-keys, según adenda D2.

El testigo dedicado se inserta en la misma transacción que recifrado/revocaciones; no se suplanta actor de aplicación para audit_event. El UUID/vínculo/material se contrastan al conciliar. §5 no equipara ausencia de respuesta a rollback: exige fin de transacción y DB primaria autoritativa, manteniendo fence ante ambigüedad. Tras commit se termina hacia delante (§6). Bloqueos consultivos no sustituyen exclusión de escritores; el contrato también exige protección frente a factores nuevos y reserva orden/timeouts de locks para implementación.

## Diez casos de la matriz: razonamiento propio

| Caso | Juicio de consistencia y referencia al protocolo |
|---|---|
| 1. Corte tras crear n, antes de R+ | Coherente: key_staged no cambia DB ni R0; fence previo impide arranque (§§3–4). No hay dependencia DB de n. |
| 2. R+ publicado, sin commit | Coherente: a sigue activa y n legible; no se borra por inferencia. Volver a R0 exige probar DB inicial, fin de transacción y cobertura (§6). |
| 3. Respuesta de commit perdida | Coherente: testigo exacto por UUID/vínculo confirma commit aunque journal diga material_ready; terminar Rf, no recifrar otra vez (§§5–6). |
| 4. Transacción viva o DB indisponible | Coherente: no concluir ausencia definitiva; conservar fence/exclusión y parar hasta hechos autoritativos (§5). |
| 5. Rf publicado, journal retrasado | Coherente: validar testigo/material/ACL/factores y avanzar; no fabricar recibos ni repetir recifrado (§6). |
| 6. Disabled/pending, antirreplay/gracia | Coherente: todas las filas se autentican/recifran; se preservan estados y metadatos. Revocar sesiones/desafíos no cambia TOTP ni gracia/exención (§5.2–5.5). |
| 7. Versión fuera de rango o entrada 65 | Coherente: §2 detiene antes del avance; parser tiene rango 1..1000000 y cupo64. SQL014 sólo exige key_version>0: precisamente por eso el censo no puede asumir que toda fila SQL sea válida para el parser. No reciclar ni liberar cupo borrando. |
| 8. Cero factores, backup exige a | Coherente: testigo/recuento cero y publicación siguen obligatorios; K/U/B y la prohibición de retirada conservan a (§§2,5.6,6). |
| 9. Inventario/material/vínculo cambian | Coherente: repetir censo tras locks y contrastar identidades/bytes; diferencias bloquean avance. UUID no se reaprovecha con parámetros distintos (§§3,5–6). |
| 10. Fallo guard/HTTPS al arrancar | Coherente: parar/reponer fence y declarar fallo, conservando commit/material. Health fallido no autoriza rollback automático (§6). |

Son diez razonamientos documentales, no diez pruebas de producto ejecutadas.

## Hallazgos por gravedad

**Contradicciones bloqueantes nuevas del criterio F-06.01: ninguna.** La guía y matriz conservan los límites del protocolo; no anuncian un operador disponible o aceptación de F-06.

- **Alta, condición operativa pendiente ya declarada:** ausencia de coordinador/testigo/publicador/fence/guard y ensayos de durabilidad/cortes. Sin esas piezas no puede ejecutarse este diseño con seguridad ni habilitar material_ready en producción. Referencias: protocolo §§3–4,7–8; D2 §4.1–4.2; límites F04/F05 previos. No bloquea acreditar una especificación que las exige expresamente; sí bloquea afirmar implementación/recuperación operativa.
- **Alta, dependencia operativa pendiente ya declarada:** censo fiable de factores/backups/operaciones/sobres y disponibilidad de todas las claves. Dependencia desconocida bloquea rotate; anillo lleno o máximo agotado no autorizan descartar versiones. Referencias: protocolo §§2,4,6,8; F-06.02. Por ello definition_confirmed del resultado completo sigue pendiente.
- **Media, concreción futura explícita:** orden SQL/timeouts, protección contra inserciones concurrentes, protocolo de puerta de arranque y persistencia verificable deben concretarse y ensayarse en implementación. El contrato fija los invariantes y reconoce que advisory lock, flush o rename aislados no los demuestran (§§3–5). No son permisos para rebajar exclusión o durabilidad.

No se encontró hueco de seguridad documental adicional que requiera corregir estos tres entregables antes de acreditar sólo .01.

## Comprobaciones ejecutadas y límites

Ejecuté lecturas Get-Content/rg, inventario de rutas, git status acotado, Test-Path y Get-FileHash SHA256/Get-Item. Las **12/12** entradas de FUENTES-CONTRASTADAS.json coinciden en hash y bytes con el árbol leído. Esta igualdad acredita identidad de fuentes/recibos, no valida por sí sola el resultado histórico.

Consulté check_index_coverage de las siete rutas de código/SQL en proyecto rackclick-desarrollo: seis sin incidencia registrada/metadata_match; SQL014 con cobertura parcial en líneas15–17. Leí SQL014 directamente completo. La primera consulta usó un nombre de proyecto no indexado y se corrigió. El índice es señal best-effort, no prueba de completitud; las conclusiones se apoyan en archivos actuales. No utilicé trazas de grafo como ejecución del producto.

**0** builds/tests de producto, PostgreSQL, servicios, VM, instalaciones, rotaciones, cifrado/descifrado, claves, credenciales o material privado. No reejecuté F04/F05. Las fuentes oficiales enlazadas por el autor se reutilizan como investigación previa; esta revisión no hizo una nueva validación web ni atribuye ejecución a Microsoft/PostgreSQL/OWASP.

D/E y las políticas confirmadas se conservan sin operaciones. No hay aceptación de Wascar, cambio funcional ni porcentaje global nuevo. Referencia de avance anterior:19,13/100 del cierre restante, distinto del porcentaje de entrega completa; esta revisión sólo recomienda el incremento literal +5/8 para conciliación del coordinador, sin recalcular ni alterar contabilidad.

## Huella de los entregables revisados

SHA256 calculado directamente el09.11.2026:

| Archivo | SHA256 |
|---|---|
| docs/PROTOCOLO-ROTACION-MFA-v1.md | 0acf68af3cbc4cb5c7a40b52304262cec20e6303cf8105668b810dfc771d4a05 |
| docs/PASO-019-FASES-ROTACION-MFA.md | 213ba9818247b7be8db61d7814415025b6b2f995cd35df3b27038a75c91967ca |
| evidence/s1-20261109/f06-01-fases/MATRIZ-CRITERIO.md | 8c5cb175c87625218522f361961e592a474cc9a41d074fc5bc56a20a95fa8cfc |

Cambiar estas fuentes exige valorar de nuevo la parte afectada; el dictamen no aprueba implementaciones futuras por anticipado.

## Adenda · conciliación del cierre documental F-06.01 · 09.11.2026

A petición del coordinador contrasté únicamente el delta de la guía y el ledger vigente frente a `.local/f0601-80d8d478a767/before/docs/PLAN-CIERRE-RACKCLICK.json`, mediante lectura y comparación JSON recursiva. No repetí la auditoría, pruebas, scans ni operaciones de producto/VM.

**Conciliación conforme al dictamen.** Sólo F-06.01 cambia de pending a done, conservando texto literal y peso5/8; se añaden sus cinco referencias y review_evidence. Las otras **52 tareas son idénticas** al backup; F-06.02/.03/.04 también son idénticos, sin crédito añadido. Los seis estados de hitos F-06 permanecen pending, incluido definition_confirmed. Dentro de F-06 sólo se actualizan además current, available y evidencias; definition_confirmed recibe razón/evidencias aclaratorias, sin cambiar estado. Ningún otro campo del ledger difiere según comparación recursiva.

Recalculé con fracciones exactas la suma de pesos de checkpoints done:1607/84 antes y3319/168 después; diferencia5/8. El redondeo es19,13→19,76/100 del cierre restante, sin nuevo porcentaje global ni aceptación operativa.

La guía cambia el encabezado a especificación completada y añade al final dictamen/peso/índice/límite operativo. Sus seis pasos y las prohibiciones de atribuir implementación/ensayo permanecen coherentes con la versión revisada. El hash actualizado sustituye únicamente la huella anterior de la guía para esta conciliación:

| Archivo | SHA256 actual |
|---|---|
| docs/PASO-019-FASES-ROTACION-MFA.md | ee6eee34f52a13faa977bc3e26fbbca78e3c16cbca87f9a5e48655e9b5ff97bd |
| docs/PROTOCOLO-ROTACION-MFA-v1.md | 0acf68af3cbc4cb5c7a40b52304262cec20e6303cf8105668b810dfc771d4a05 |
| evidence/s1-20261109/f06-01-fases/MATRIZ-CRITERIO.md | 8c5cb175c87625218522f361961e592a474cc9a41d074fc5bc56a20a95fa8cfc |

Protocolo y matriz coinciden exactamente con las huellas de la revisión inicial. No comprobé de nuevo generadores, resultados, continuidad o progreso; ese trabajo lo registra el coordinador. Única escritura de esta ampliación: esta adenda del dictamen asignado.
