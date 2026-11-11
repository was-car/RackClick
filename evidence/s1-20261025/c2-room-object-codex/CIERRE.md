# Foco de edición Dosen/finales · revisión de Codex

25.10.2026. Entrega original de Claude preservada en su carpeta. Root coordinador reforzó exclusivamente los dos tests entregados y ejecutó el ensayo nuevo; agente QA `room_edit_review` hizo sensibilidades propias y revisión independiente. No se modificó el producto.

- `test_room_object_edit_gui.original.py` y `browser-room-object-edit.original.mjs`: fuentes exactas de la entrega original, SHAe6a0093b…090c y8570d085…70fdd. No afirmar que esos hashes corresponden a los tests actuales.
- `REVISION.md`: carencia inicial P2 de comparación de properties y su adenda; seis mutaciones indebidas pasaban antes, ahora fallan; dos controles válidos pasan. Sólo las ejecuciones propias del revisor se atribuyen a él.
- `EDGE-PG-INDEPENDIENTE.json`, `EDGE-BROWSER-INDEPENDIENTE.json`: ejecución nueva en Windows/Edge/PostgreSQL17.11 PASS27,656s. Misma DLL5eb1… y frontend04f4…; artefactos/entradas sin cambio y todos los procesos propios detenidos.
- Auditoría medida por acción:2device.update+2ports.update de inventario y1user.preference.set. Esta última es selección de idioma; sólo hay cuatro filas de operación de inventario y revisión+4. No es una quinta edición ni un fallo del producto.
- Comparación de nueve tablas con metadatos adicionales no vacíos, UUID/cables/atributos íntegros. Rechazos403/404/422 conservan estado exacto de inventario, cliente, operaciones y auditoría; recarga/otra cuenta y reinicio persistidos.
- `FUENTES-REVISADAS.json`: hashes actuales de los dos tests. Salida privada/artefactos explícitos en `ENTORNO.json`; claves generadas localmente, nunca publicadas.

Reproducción desde la raíz, con artefactos explícitos y una salida nueva bajo `.local/`:

```powershell
C:/Python312/python.exe -X utf8 -B development/server/tests/test_room_object_edit_gui.py --dll <DLL5eb1> --frontend <dist04f4> --output <directorio-nuevo>
```

Requiere la toolchain local del proyecto y Edge. No usar bases, sesiones o instaladores de QA/VM. Los artefactos de entrada exactos viven en `.local/`; un clon sin ellos no acredita esta ejecución. Sólo se prueba español, dos objetos y un estado de puerto por objeto; no rol de energía, todos los campos, idiomas o borrado/impacto.

Foco aceptado, I-06.02 en curso, sin cerrar todo I-06 ni cambiar pesos. Cierre pendiente5,86/100 sin incremento, global sin recalcular. Claude sigue MFA-L1 y Codex borrado/impacto. No código de producto, build, paquetes, VM, QA o commits.

Verificaciones: hashes de fuentes actuales coinciden con la ejecución nueva; métrica sin cambios de alcance/pesos; Gitleaks8.30.1 cero hallazgos en el conjunto seleccionado (no todo el historial); Codebase Memory refrescado con937archivos curados. No cambia catálogo/guíasQA porque no hay cambio visible de producto ni disponibilidad nueva.
