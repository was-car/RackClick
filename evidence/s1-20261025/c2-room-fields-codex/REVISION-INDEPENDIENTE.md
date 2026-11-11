# I-06.02 · revisión independiente de campos de objetos de sala

25.10.2026 · Revisor distinto del implementador y del ejecutor del laboratorio. **Dictamen: conforme para el cierre técnico de I-06.02**, combinando este foco con edición básica y borrado/impacto ya aceptados. No acredita I-06 completo, integración de la candidata ni QA de Wascar.

## Archivos y símbolos contrastados

- `development/server/tests/test_room_fields_gui.py`: `fixture`, `expected_sql`, `main`, negativos y estado tras reiniciar. SHA256 `1c3c0ce55149dce3e0316aec53245831dfab5a9b925c10ad6f05565fafb84764`.
- `development/frontend/tests/browser-room-fields.mjs`: `commit`, `editPort`, `displayed`, registro de comandos y comprobaciones finales. SHA256 `f8bf56841f06dee4cb4bedd0cbb0f894c6e5094acc904703c074d28b5c955562`.
- Dependencias de comparación: `canonical` de `test_rack_variants_gui.py` y `normalize` de `browser-quince-support.mjs`. Sólo ordenan las colecciones; no excluyen propiedades o atributos.
- Informes finales del ensayo nuevo y su única regresión; `initial-project.json`, `expected-project.json` y `room-fields-details.json` del nuevo foco.
- Alcance previo de `docs/REVISION-C2-OBJETOS-SALA-CODEX-25-10-2026.md` y `docs/C2-BORRADO-IMPACTO-25-10-2026.md`. Sus ejecuciones anteriores se mantienen históricas.

## Cobertura y hallazgos

**Sin hallazgo bloqueante de gravedad P1/P2 en los archivos revisados.** La preparación distingue Dose y dispositivo final, familia RJ45 y grupo power con `gn=1` repetido. Cada comando se contrasta por UUID de dispositivo/grupo/puerto y familia; el número visible no decide la identidad.

Los dos editores modifican nombre, presupuesto PoE y las cinco notas. Catorce comandos de puertos cubren estado, PoE, watts, color, etiqueta, cara y rol power en ambos objetos. Hay valores vacíos/null, PoE en ambas direcciones y texto Unicode con apariencia de HTML. Los controles se reabren tras lectura por otra cuenta y recarga, sin emitir escrituras adicionales. No se ofrece `sizeU` para estos objetos.

El esperado SQL parte del estado original y sólo altera los campos previstos; conserva propiedades anidadas, sala, UUID, grupos, puertos no seleccionados, cables y extremos. El comparador no obtiene el esperado de la respuesta que valida. Los roles outlet/inlet se prueban en puertos power sin conexión; la prueba no afirma comprobar un circuito eléctrico ni su seguridad física.

Los siete rechazos exigen igualdad completa de inventario, cliente/revisión, operaciones y auditoría. El lote mixto inválido incluye primero un puerto válido y después uno de otro grupo, de modo que la comprobación detecta una aplicación parcial. Se verifican permisos de lector403 y usuario ajeno404 en el servidor, además de reglas inválidas422 y puerto de otro cliente404.

## Pruebas ejecutadas por este revisor

Comando: `C:\Python312\python.exe -X utf8 -B evidence/s1-20261025/c2-room-fields-codex/focos_revision.py`.

**Tres focos puros PASS**, salida en `FOCOS-REVISION.json`:

1. Esperado escrito de forma independiente: coincide con `expected_sql`; la entrada permanece intacta.
2. Seis mutaciones de identidad, grupo, gn, vecino, extremo de cable y sala: todas rechazadas por el comparador.
3. Siete mutaciones de propiedades anidadas, color adicional, nota, null frente a cero/vacío, familia y propiedad de cable: todas rechazadas.

Además contrasté por lectura los recibos del ensayo real: 16 escrituras, 16 revisiones consecutivas, dos `device.update` y catorce `ports.update`; grupos y cables completos iguales al original. No hay tokens ni cabeceras de autenticación en el registro de comandos publicado por este foco.

## Ejecuciones del coordinador contrastadas, no repetidas por el revisor

- Ensayo nuevo `.local/c2-room-fields-20261025-intento1/fixture.json`: **PASS32,719s**, PostgreSQL17.11, navegador exit0, 16 operaciones, auditoría2+14, siete rechazos atómicos, recarga/otra cuenta/reinicio, fuentes y artefactos iguales; laboratorio y servidores detenidos.
- Regresión `.local/c2-room-fields-20261025-regresion1/fixture.json`: **PASS27,562s**, PostgreSQL17.11; cuatro operaciones de edición básica, cuatro auditorías de inventario más una preferencia de idioma, 403/404/422 sin cambios y persistencia tras reiniciar; entradas iguales y procesos detenidos.

## Límites

Este revisor no ejecutó PostgreSQL, Edge, compilación, VM, instalador, servicios Windows ni QA. Sus pruebas fueron sólo funciones puras y comprobaciones de recibos. El foco nuevo usa español y un puerto seleccionado de cada familia por objeto, sin afirmar todas las combinaciones posibles ni un ensayo físico. Los artefactos congelados de laboratorio dependen de `.local/`; no equivalen a una reproducción desde un clon limpio ni a integración en el instalador08.

La evidencia anterior de borrado individual/conjunto con vista previa, cancelación e impacto se reutiliza por su alcance ya revisado, sin declararla una ejecución nueva. El coordinador conserva la responsabilidad de conciliar el peso fijo del subpaso; este dictamen no calcula ni modifica el porcentaje global.
