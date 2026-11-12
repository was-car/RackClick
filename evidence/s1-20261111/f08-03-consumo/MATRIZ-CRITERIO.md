# F-08.03 · consumo, revocación, concurrencia y rollback

Literal: consumir transaccionalmente, invalidar sesiones/desafíos/códigos anteriores según contrato y probar consumo concurrente/replay/rollback/secretos. El paso 26 ordena reutilizar las pruebas existentes; el canje no se reimplementa.

| Criterio | Implementación existente | Evidencia focal |
|---|---|---|
| Un único commit del canje | `RedeemRecoveryCode` usa BeginTransaction y pasa db/tx a sus comandos, incluido audit | Dos casos nuevos: testigo de seis relaciones bajo txid del audit ganador, rol runtime observado |
| Un ganador con solicitudes solapadas | `LockChallenge` bloquea cuenta/factor/desafío/política; revalidación después de espera | Dos PID esperando sobre la cuenta antes de liberar; mismo código o dos distintos del conjunto antiguo, exactamente un resultado enroll |
| Revocación delimitada | UPDATE de diez códigos, factor/política, DELETE de sesiones por usuario y consumo de desafíos por Systemhaus/usuario | Dos sesiones/ tres desafíos antiguos revocados, diez códigos consumidos, un nuevo desafío; otra cuenta conserva seis colecciones propias y la gracia global no cambia |
| Replay, finalidad y CSRF | Rechazo de consumed/finalidad equivocada y comprobación CSRF | `ReplayWrongPurposeAndWrongCsrfCannotConsumeAValidEnrollmentOrCode`; evidencia F-08.02 reutilizada |
| Caducidad y límites de fallo | Reloj SQL después de todos los bloqueos, incluido FOR UPDATE de códigos; intentos acotados | Caducidad/política cambiada, espera de código demostrada y límite compartido de fallos existentes |
| Rollback real | Auditoría en la misma transacción | Trigger de prueba falla al insertar audit; `RecoveryAuditFailureRollsBackEverythingIncludingTheUsedCode` compara diez tablas, incluido el código presentado |
| Sin valores originales persistidos | Digest de token/CSRF, códigos salados ligados a cuenta, audit sólo contadores | Snapshot sin códigos originales/normalizados ni tokens/CSRF de los desafíos conocidos; NoKeys impide solicitar claves TOTP |

La prueba histórica `OnlyOneConcurrentUseCanSucceedEvenFromDifferentVerifyChallenges` se conserva, pero su `Task.WhenAll` no se presenta como prueba suficiente del solapamiento. La nueva usa observación de bloqueos real y un testigo SQL sin valores secretos. El resultado no prueba recuperación de un apagón, memoria/logs completos, candidata instalada, custodia o último administrador.
