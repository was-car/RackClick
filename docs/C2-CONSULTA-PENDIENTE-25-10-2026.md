# C2 · Consultar una operación pendiente de inventario

25.10.2026 · Codex. **Implementado y revisado en laboratorio; no desplegado en QA ni incorporado a la candidata 07.** Continúa I-01.03 sin darlo por completo. Claude mantiene W-02; no se editaron sus fuentes, instaladores, MFA ni paquetes.

## Resultado

El cuadro de recuperación de inventario añade **Consultar operación pendiente**, sin reenviar la escritura. Consulta el endpoint GET existente para el cliente y requestId originales, con la sesión autenticada. No crea otra clave ni modifica cuerpo/revisión/actor de la operación guardada.

- **committed:** valida el recibo original y recupera su resultado. Para Deshacer estructural comprueba también variante, fuente y conjuntos de IDs. Una revisión actual exterior más alta no invalida un recibo histórico legítimo.
- **notRecorded:** muestra que todavía no existe resultado registrado. Conserva el journal y la incertidumbre; permite reintentar o cancelar esa misma intención. No significa que se haya cancelado ni guardado.
- **cancelled:** valida el recibo de cancelación, incluido su operationId exterior. Retira sólo esa entrada del journal y muestra la cancelación confirmada, con reintento deshabilitado.
- Errores de red, autorización, recibos inválidos o cambio de actor no se convierten en éxito. La consulta comprueba actor/aborto antes y después del GET; el diálogo vuelve a comprobar su contexto vivo después de las esperas locales antes de aplicar callbacks.

Se conserva el diálogo RC9 y los textos EN/DE/ES se renderizan como texto React. La autorización y el cerrojo de cancelación siguen en el servidor existente. No hay SQL, migración, endpoint nuevo, dependencia o cambio de versión.

## Propiedad y corrección revisada

Producto: `development/frontend/src/inventory-api.ts`, `OperationDialog.jsx` y nuevo `inventory-operation-status-words.ts`. Pruebas nuevas: `inventory-operation-status.test.mjs`, `browser-inventory-operation-status.mjs` y runner `development/server/tests/test_inventory_operation_status_gui.py`. Fuentes anteriores y diagnósticos privados se conservan bajo el puntero `.local/c2-query-current.txt`.

El revisor distinto reprodujo **P2** en la primera implementación: después del GET, un cambio de actor mientras esperaba IndexedDB podía hacer llegar el callback al contexto anterior. Se añadió una referencia viva de API/actor/cliente y guardas en las fronteras asíncronas de la consulta. El negativo falla con la versión original preservada y pasa con la final. No se demostró escritura cruzada ni corrupción SQL. [Revisión y prueba propia](../evidence/s1-20261025/c2-query-codex/REVISION.md).

## Pruebas reales

| Comprobación | Resultado |
|---|---|
| Node 24.21.0 | 25/25 PASS: 9 nuevas y 16 regresiones, sin omisiones. |
| Revisor distinto | 8/8 focos propios PASS; original de P2 conserva 1 FAIL esperado. Función extraída/callbacks controlados, no navegador propio. |
| Edge 156 / PostgreSQL 17.11, bytes finales | PASS 25,77 s: respuesta comprometida perdida→GET; solicitud no enviada→notRecorded→reintento exacto; cancelación desde otra sesión del mismo actor→GET cancelled; POST tardío 409. |
| Ámbitos | Otro actor no obtiene el recibo del primero; lector sin acceso al otro cliente obtiene 404 real. |
| Persistencia | Nueve tablas de inventario exactamente restauradas, incluidas fechas y extremos; misma lectura después de reiniciar el proceso del servidor. |
| Regresión de grupos sobre bytes finales | PASS 21,78 s: crecimiento/reducción, respuesta perdida, reload/replay, lectura en otra sesión y persistencia. |

El primer ensayo GUI falló en el observador de la prueba: envolver window.fetch después de que la API capturase su fetcher no contaba el GET real. Se corrigió sólo la observación a CDP Network; el resultado fallido y una ejecución intermedia anterior al P2 se conservan separados. La primera copia privada para build omitió un archivo de referencia adoptada; se completó esa copia, sin cambiar el build ni la referencia original. No se presentan esos intentos como PASS.

Frontend final privado **`72d970f02d8e32a4642fa8fe1c3f0803a2fab044bcdc71d377f95c5bedf78767`**; CSS **`50dd856718dd01b3e3356a9a08005df880c859a2652b68a670c167fa75567ec3`** conservado. DLL C2 reutilizada **`5eb1abcf9d2f91d293bae8f1b01e94f0352ca254c0387aaa45de1c35b2a97585`**; no compilación .NET ni nueva distribución. [Comandos, resultados y capturas](../evidence/s1-20261025/c2-query-codex/CIERRE.md).

## QA, métrica y próximo paso

QA-114 documenta ubicaciones, botones y resultados de cada estado. Sigue **planned**, no disponible en la QA actual. Los 113 casos anteriores son iguales; sólo cambia la revisión del catálogo y se añade el caso. Ambas guías se regeneraron sin escribir resultados/observaciones de Wascar ni cambiar el snapshot QA.

I-01.03 sigue pendiente: falta completar invalidaciones con candidato vivo por revisión, permiso, cuenta y cliente, incluidas las fronteras asíncronas de las vías heredadas de submit/cancel. Tampoco se acredita integración en la candidata coordinada, MFA, Windows/VM, reinicio del sistema o aceptación manual. La prueba de reinicio es del proceso de servidor.

**Cierre del pendiente: 25/7 = 3,57/100 puntos, 8/280 subpasos y 1/50 resultados completos.** Esta tanda añade una función y cierra su P2, pero no un subpaso completo del inventario fijo: delta de crédito cero. No es porcentaje global del producto. El siguiente bloque C2 debe completar esas invalidaciones antes de acreditar I-01.03; después integrar una candidata nueva coordinada, conservando la 07 y sus evidencias.
