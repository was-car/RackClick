# C2 · orden de equipos y cancelación táctil

25.10.2026 · I-04.04. Cambio de desarrollo probado en laboratorio Windows, separado del instalador 08 y de la VM C apagada por Wascar.

## Fallo y corrección

Al cancelar un arrastre táctil, `touchDrag.current` conservaba origen y destino. Un toque posterior en una zona normal del rack disparaba `touchEnd` y podía guardar aquella reordenación cancelada. Se reprodujo en Edge con eventos táctiles nativos emulados mediante CDP: revisión 1→2 y equipos A/B intercambiados sin una nueva intención de moverlos.

`InventoryPanel.jsx` descarta ahora esa referencia al recibir `touchcancel` en captura sobre el contenedor del rack. Es la única diferencia de producto. No cambia RC9 adoptada, estilos, textos, comandos, permisos, Click-Click, API ni backend. Un gesto válido sigue guardando su orden por UUID y con confirmación del servidor.

## Pruebas ejecutadas

| Ejecución nueva | Resultado |
|---|---|
| Frontend anterior, cancelación seguida de toque normal | FAIL 18,641 s; reproduce la escritura inesperada; entradas inmutables y laboratorio detenido |
| Primera ejecución corregida | Cancelación/flechas/drag/touch superados; FAIL 20,000 s por una expectativa incorrecta del test al mover entre racks |
| Prueba final corregida | PASS 26,875 s, Edge/PostgreSQL 17.11, cinco commits y nueve tablas exactas |
| Regresión existente de movimiento | PASS 22,813 s, mismo frontend/DLL, incluida competencia 412, permisos y persistencia |

La expectativa intermedia pretendía compactar el valor numérico del orden del equipo que permanece en el origen. El contrato existente conserva ese valor y añade el equipo al final del destino. Se corrigió exclusivamente el esperado del observador, manteniendo la comparación completa. El fallo y las fuentes iniciales se conservaron; no se cambió el backend para satisfacer el test.

La prueba final verifica:

- Cancelar el gesto y tocar después fuera del asa no envía comandos ni cambia datos/revisión. Flecha de límite deshabilitada, drag desde puerto bloqueado, soltar sobre sí mismo y cancelar Mover tampoco escriben.
- Flecha, drag HTML5 y táctil reordenan A/B. Mover B al segundo rack lo incorpora después de C; Subir lo deja antes de C. Exactamente cuatro `device.reorder`, un `device.move`, cinco operaciones y cinco auditorías.
- UUID, metadatos, tamaños, grupos, puertos y atributos/extremos del cable conservados. Sólo cambian rack/orden/revisión previstos. El cable pasa de local a entre racks con sus mismos extremos y atributos.
- Recarga, otra sesión autorizada y reinicio del proceso servidor devuelven el mismo proyecto. Dos usuarios sin edición para ese cliente reciben 403; lecturas fuera de ámbito 404; ningún rechazo deja cambios de inventario, revisión, operación o auditoría.

El drag HTML5 usa eventos DOM con DataTransfer sobre los controles reales; el táctil usa eventos `isTrusted` de Edge/CDP. No acredita un ratón o pantalla táctil físicos ni una matriz de dispositivos. El orden es documental: no se añade una posición U física persistida.

## Artefactos, revisión y continuidad

Un build frontend privado, derivado de la copia C2 anterior con ese único cambio: `app.js` SHA256 `04f4ef02c15ed46f57756e43d3949222d9f8d9f11961765acafe57eec3c81101`. CSS `50dd8567…7ec3` y DLL `5eb1abcf…7585` idénticos. No se compiló .NET ni se cambió el payload 08, MFA, QA seleccionado o VM.

Revisión distinta: comparación exacta del cambio, ejecución Node sobre los portadores JSX reales (cancelar descarta la referencia; repetir cancel es seguro; gesto válido sigue funcionando) y tres focos propios de sensibilidad del comparador SQL. [Evidencias, comandos y dictamen](../evidence/s1-20261025/c2-order-variants-codex/CIERRE.md).

QA-123 queda **planned**; sus pasos no habilitan esta variante en la candidata actual ni reabren el ensayo C. Los 122 casos anteriores y sus resultados personales se conservan. I-04.05–07 y la integración/aceptación siguen pendientes.
