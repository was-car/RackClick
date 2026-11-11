# C2 · matriz de recuperación y cierre técnico de I-01.03

25.10.2026. Alcance: Deshacer de crecimiento/reducción pura de grupos. Este documento concilia pruebas anteriores con un ensayo nuevo de revocación de edición. No modifica producto ni acredita la candidata de instalación, MFA o QA de Wascar.

## Resultado

I-01.03 queda técnicamente cubierto en el laboratorio identificado, con revisión independiente. I-01.05, I-01.06 e I-01.07 siguen pendientes: integrar y probar la candidata coordinada, habilitar los guiones sobre sus bytes reales y cerrar la aceptación del resultado completo.

La distinción importa: las entradas anteriores mantenían I-01.03 abierto por «capacidades específicas» e integración. El contraste del servidor permite concretarlo. Deshacer grupos exige `inventory.read` e `inventory.edit`; no exige `inventory.delete`. La integración y aceptación tienen sus propios subpasos. Se corrige esa interpretación, conservando las evidencias originales, el texto contractual, el denominador y los pesos.

## Capacidad que comprueba el servidor

| Acción | Comprobación vigente |
|---|---|
| Compensar atributos, crecimiento o reducción de grupos | Lectura y edición en el cliente actual. |
| Editar grupos, incluida reducción | Lectura y edición. Reducir grupos no equivale al comando de borrar una entidad. |
| Borrar rack/equipo/sitio/edificio/sala | Lectura y borrado; es una familia distinta. |
| Consultar una operación original | Lectura actual, sesión válida y actor original. |
| Cancelar una solicitud original | Lectura y capacidad del tipo original: borrado para tipos `.delete`, edición para los demás. Se comprueba antes de devolver incluso un resultado ya confirmado. |

Referencias de código: [InventoryStore](../development/server/src/RackClick.Server/InventoryStore.cs), [InventoryImpact](../development/server/src/RackClick.Server/InventoryImpact.cs), [InventoryCompensation](../development/server/src/RackClick.Server/InventoryCompensation.cs) y [OperationCancellation](../development/server/src/RackClick.Server/OperationCancellation.cs). Los botones no sustituyen estas comprobaciones.

## Matriz de I-01.03

| Parte del subpaso fijado | Evidencia y resultado |
|---|---|
| Consulta original ante incertidumbre | [Consulta](../evidence/s1-20261025/c2-query-codex/CIERRE.md): GET no reenvía escritura; `committed` recupera recibo, `notRecorded` conserva la intención y `cancelled` impide reintentar. |
| Reintento y cancelación originales | Consulta y [contexto](../evidence/s1-20261025/c2-context-codex/CIERRE.md): actor, cliente, cuerpo, clave y ETag originales; guardas tras esperas y limpieza sólo de la intención correspondiente. |
| Otra revisión | [Elegibilidad](../evidence/s1-20261025/c2-eligibility-codex/CIERRE.md): borrador invalidado por revisión observada; intención ya registrada no se reescribe para eludir conflicto. |
| Permiso retirado | Elegibilidad cubre pérdida de membresía. [Ensayo nuevo](../evidence/s1-20261025/c2-permission-codex/EDGE-PG.json) cubre retirar sólo edición conservando lectura: consulta permitida, cancelación y replay denegados por HTTP. |
| Cuenta o cliente cambiados | Contexto: API/actor/cliente y ciclo de vida después de esperas; cambio observado A→B→A no reactiva borrador antiguo. |
| Edición rápida y continuaciones | [Ediciones rápidas](../evidence/s1-20261025/c2-instant-codex/CIERRE.md): mismas guardas, exclusión síncrona, intención pendiente y callbacks/lecturas invalidados. |

Las cuatro referencias anteriores son pruebas históricas de sus tandas, no ejecuciones nuevas de hoy. Cada una conserva su revisión distinta. El [dictamen de esta conciliación](../evidence/s1-20261025/c2-permission-codex/REVISION-I0103.md) revisa la cobertura acumulada y el ensayo nuevo.

## Ensayo nuevo: lectura conservada sin edición

- Edge real en Windows y PostgreSQL 17.11 nuevo. Dos contextos de navegador: administrador y técnico. La concesión temporal de edición se cambia por la API administrativa real, para un cliente concreto; lectura permanece y borrado nunca se concede.
- Inversa detenida antes de llegar al servidor: se retira edición con el diálogo abierto. Reintento bloqueado, consulta `notRecorded` disponible y cancelación HTTP 403. La intención y los datos permanecen exactos. Al restituir edición, se reenvían los mismos cuerpo, actor, clave y ETag, y la inversa se confirma una vez.
- Segunda inversa confirmada con respuesta perdida: se retira edición. Replay HTTP 403; la consulta original devuelve `committed`, elimina sólo su intención y conserva los datos finales. Se retira la concesión temporal de edición.
- Resultado final PASS, 21,83 s, cero excepciones JavaScript; nueve tablas de inventario exactas respecto al inicio y persistencia tras reiniciar el proceso del servidor. Ambos procesos y el laboratorio quedan detenidos.
- Primer ensayo FAIL por una espera del observador que coincidía con un aviso anterior antes de recibir el evento de cancelación. Se conserva; se corrigió sólo la sincronización del test. No demuestra un fallo nuevo de producto.

## Crédito y límites

Sólo I-01.03 suma su peso previamente fijado: **5/14 puntos**. El cierre del trabajo restante pasa de **25/7 a 55/14 puntos: 3,57 → 3,93/100**, con **9/280 subpasos y 1/50 resultados completos**. No es un porcentaje global del producto; el 78 % antiguo está retirado.

No se recompiló ni se cambió código de producto. Se reutilizaron frontend y DLL privados identificados en [FUENTES.json](../evidence/s1-20261025/c2-permission-codex/FUENTES.json); repetir el ensayo requiere esos artefactos o construir una candidata nueva y verificarla. No acredita reproducción desde un clon limpio, instalación, servicio Windows, reinicio del sistema, MFA ni paridad completa RC9. El catálogo QA y las observaciones de Wascar se conservan sin cambios. La edición 07 no incorpora C2 automáticamente.
