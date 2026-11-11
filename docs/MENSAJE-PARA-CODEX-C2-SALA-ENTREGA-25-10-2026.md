# Para Codex · entrega del foco de edición de objetos de sala (I-06) · 25.10.2026

Escrito para: Codex (revisión del bloque).

Entrego el foco de edición GUI de Dosen y dispositivos finales de sala. Detalle en `docs/C2-OBJETOS-SALA-CLAUDE-25-10-2026.md`; evidencia en `evidence/s1-20261025/c2-room-object-claude/`.

## Resultado

- Prueba de extremo a extremo: `PASS`, con PostgreSQL 17.11 nuevo y datos sintéticos.
- Guardado por GUI con cuatro comandos aceptados (dos `device.update` y dos `ports.update`).
- Solo cambian nombre, notas y el estado del puerto elegido; el resto queda igual.
- Recarga, segunda cuenta autorizada, lector sin botón de edición, rechazos 403/404/422, revisión y auditoría iguales tras los rechazos, y persistencia tras reiniciar el servidor.

## Archivos

- `development/frontend/tests/browser-room-object-edit.mjs` (nuevo).
- `development/server/tests/test_room_object_edit_gui.py` (nuevo).
- `docs/C2-OBJETOS-SALA-CLAUDE-25-10-2026.md` (nuevo).
- `evidence/s1-20261025/c2-room-object-claude/` (nuevo).

No edité archivos compartidos, ni VM, QA, instaladores, MFA o commits.

## Hashes

- DLL: `5eb1abcf…2a97585`.
- Frontend `app.js`: `04f4ef02…c81101`.
- Prueba Python: `e6a0093b…adf090c`.
- Escenario `.mjs`: `8570d085…70fdd`.

## Observaciones para tu revisión

1. Un primer intento dio 422 al cambiar el rol de energía de puertos RJ45. Es una regla correcta del producto: el rol solo aplica a puertos `power`. Fue un error mío de elección de prueba; no hay fallo de producto.
2. Hay cinco eventos de auditoría por cuatro comandos exitosos. No he desglosado el quinto; queda abierto.
3. Solo español, un puerto por objeto y estado como campo de puerto. No acredito todo I-06 con este foco.
