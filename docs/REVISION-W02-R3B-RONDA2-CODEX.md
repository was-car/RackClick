# W02-R3b · ronda 2 · dictamen de Codex

25.10.2026. **Conforme en el alcance revisado: los dos defectos materiales de REC-02 quedan corregidos.** El siguiente cambio es fijar los pins y el procedimiento para la candidata 08; no hace falta reconstruir sus ZIP por esta revisión del auxiliar.

Fuente revisada: `tools/windows/w02/Invoke-W02TrialPlan.ps1`, SHA256 `6e7fc20e2aad67a6ebefd642497d298e2d041a0b5a92ac5678af3aa108c4e5b8`.

El revisor independiente ejecutó cuatro llamadas nativas Reconcile sobre copias y entradas ficticias nuevas:

| Caso propio | Resultado |
|---|---|
| Fase 02 completa con exit 9 y fases posteriores completas hasta exit 0 | `secuencia_incoherente`; conserva hechos 9/0 y no presenta un exit observado válido. |
| Postboot con esquema, UUID y fechas correctos, pero resultado contradictorio | `postboot_contrato_incoherente`, por la contradicción del resultado; no por campos omitidos o un esquema inválido que ocultase el defecto. |
| Recorrido normal con postboot completo y coherente | Exit observado 0, `verificacionRegistrada=true`, salud actual explícitamente no comprobada. |
| Documento sin installationId/bootUtc | `vinculo_incompleto`, sin verificación registrada. |

Entradas y salidas previas intactas; cada llamada publicó un informe nuevo. El bloqueo de bytes del envoltorio y el cuerpo de Execute permanecen idénticos a la versión anterior revisada. No se ejecutaron Execute, INICIAR, instalador, servidor, SQL, servicios, cuentas o VM. [Revisión independiente con comandos y hashes](../evidence/s1-20261025/w02-r3b-ronda2-codex/REVISION.md).

El coordinador contrastó además los productores reales del payload 08: `Test-RackClickServerAfterReboot.ps1` y `Install-RackClickServer.ps1` son byte a byte idénticos a sus fuentes actuales. Se comprobaron los campos que escriben, no se ejecutaron esos productores ni se afirma correspondencia con archivos reales de una VM. [Contraste](../evidence/s1-20261025/w02-r3b-ronda2-codex/PRODUCTORES08.json).

Las 35 estáticas, diez focales rojo/verde y regresiones son ejecuciones aportadas por Claude; no se repitieron ni se suman a las cuatro propias. Se conserva su primer rojo con carrera del harness y la corrección de esa carrera. El observador del revisor también corrigió una etiqueta de metadata propia sin repetir los cuatro casos; original y resultado corregido conservados.

Límites mantenidos: el postboot no declara equipo/run; la vinculación sigue siendo parcial. Los hashes declarados no autentican recibos. Reconcile no consulta salud actual ni relanza trabajo. Las fechas se validan con la tolerancia de cinco minutos declarada por el lector. El resultado inicial `result.json` sigue siendo histórico.

No reabrir esos dos defectos por cambiar los pins. Falta una revisión acotada del cambio 07→08, Check/Plan para el destino y el ensayo real de Restore/reinicio. Wascar realiza los pasos sencillos de Windows/VMware. **Cierre restante 4,79/100**, W-02 0,50/2,50; esta revisión de un requisito previo no completa el ensayo.
