# Paso 26 · consumo transaccional de códigos de recuperación

11.11.2026 · F-08.03. Cerrado técnicamente con revisión independiente favorable. **D y E permanecen intactas.**

## Contrato que se conserva

Un canje válido retira los diez códigos anteriores de la cuenta, revoca sus sesiones y desafíos previos, desactiva el factor anterior y exige reenrolamiento. Todo se confirma con su auditoría dentro de una transacción. No crea una sesión API y no afecta otra cuenta. Si falla la auditoría, se revierte el consumo junto con el resto del estado.

Se reutiliza el canje ya implementado en el punto 3 y los recorridos F-08.01/.02. No hay cambios de producto, interfaz, SQL del producto o dependencias. La única fuente nueva es una prueba parametrizada que fuerza dos canjes simultáneos —con el mismo código o dos códigos del conjunto— y observa sus bloqueos y escrituras en un PostgreSQL nuevo.

## Comprobaciones de esta tanda

- Dos PID deben estar realmente esperando antes de liberar el bloqueo; no se deduce concurrencia de llamar a `Task.WhenAll`.
- Sólo un canje obtiene el desafío nuevo; las seis relaciones afectadas por ese ganador comparten transacción y rol SQL de ejecución. El testigo de laboratorio sólo registra relación, operación, rol y txid.
- La otra cuenta conserva usuario, política MFA, factor, códigos, sesiones y desafíos; la política global de gracia no cambia.
- Se reutilizan y repiten los negativos existentes de replay/finalidad/CSRF, caducidad tras esperar bloqueos, límite de intentos y rollback forzado de auditoría.
- Las comparaciones de persistencia buscan valores originales y normalizados de códigos, tokens y CSRF sin imprimirlos. No equivalen a un análisis de memoria o de todos los logs.

[Resultados](../evidence/s1-20261111/f08-03-consumo/RESULTADOS.md) · [matriz](../evidence/s1-20261111/f08-03-consumo/MATRIZ-CRITERIO.md) · [plan](PLAN-F0803-CONSUMO-TRANSACCIONAL.md).

## Límites

El rol SQL es separado del propietario; los testigos y triggers son DDL exclusivo del fixture, no una migración del producto. El factor y las sesiones iniciales son sintéticos. El proveedor de prueba rechaza solicitudes de claves TOTP; esto comprueba que el canje no necesita descifrarlas, no que un host pueda arrancar sin su almacén.

El snapshot existente cubre diez tablas de identidad/MFA/Systemhaus/operación/auditoría, no todo el inventario. No se ensayan apagón, servicio/SID efectivo, TLS, instalación o aceptación de Wascar. El navegador/HTTP de F-08.02 y punto 3 se reutiliza con sus fechas; no se anuncia como otra ejecución. QA-163 y los resultados personales se conservan.

Custodia, último administrador y el cierre conjunto F-08.04/.05 e hitos operativos siguen pendientes; este criterio técnico no los acredita.


Sólo F-08.03 acredita **1/2 punto**: índice del cierre restante **23,13 → 23,63/100**, sin porcentaje global nuevo. [Dictamen](../evidence/s1-20261111/f08-03-consumo/review/DICTAMEN.md). Siguiente paso 27 / F-08.04.
