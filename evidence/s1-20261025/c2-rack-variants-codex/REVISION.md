# Revisión independiente acotada — opciones de inventario C2

25.10.2026. Revisor distinto del implementador; encargo exclusivo del coordinador. Sólo se crean este informe y `review-fields.test.mjs`. No se modifica producto, pruebas de otros autores, ledger, QA, VM, MFA ni paquetes. Estado Git inspeccionado antes: árbol con numerosos cambios ajenos, conservados.

## Dictamen y gravedad

**Sin hallazgos bloqueantes nuevos en el delta revisado.** La corrección es adecuada para nombres literales y destinos homónimos. La comparación completa de los dos consumidores con sus copias originales confirma que el delta se limita a importar el helper, sustituir cuatro productores de opciones y renderizar opciones/títulos en `Fields`; los cuerpos de permisos, comandos, DTO, clases y estilos de esos archivos permanecen iguales.

**P2 anterior, corregido en fuente:** el selector Mover traducía un rack llamado literalmente `room` a `Sala` en ES; dos destinos homónimos resultaban indistinguibles y carecían de títulos. El fixture propio reproduce esos tres defectos con los consumidores originales. También reproduce dos rutas de sala idénticas sin UUID. La reproducción carga el `Fields` original aislado y sus productores originales: no depende de que exista el módulo nuevo en el árbol anterior, ni falla por un import ausente.

**Límites de cobertura, sin asignar gravedad de defecto:** la prueba de renderizado usa un sustituto de `React.createElement`, no DOM ni píxeles. Comprueba estructura de etiqueta implícita, valor/required/disabled y callbacks, pero no navegación con teclado, lector de pantalla, contraste, zoom, recorte en pantallas estrechas ni presentación nativa de tooltips. No acredita accesibilidad ni paridad visual completas.

## Archivos y símbolos consultados

- `development/frontend/src/inventory-choice-labels.ts`: `inventoryEntityOption`, `inventoryOptionLabel`.
- `development/frontend/src/OperationDialog.jsx`: `Fields`; cuerpo restante de `OperationDialog` por comparación completa.
- `development/frontend/src/InventoryPanel.jsx`: `hierarchy`, `rackEditor`, `sharedDeviceEditor`, `moveDevice`, `open`, `option`, `select`, `number`, `named`; `deviceEditor` como contexto.
- Copias originales autorizadas de ambos JSX bajo `.local/c2-rack-variants-20261025T193105Z-3bbe929b/original/`; exclusivamente código de comparación.
- `development/frontend/src/inventory-model.ts`: `roomPath`; `inventory-words.ts`: `inventoryWords` EN/DE/ES.
- `development/frontend/tests/browser-rack-variants.mjs`: lectura del escenario, sin ejecutarlo; tests existentes `inventory-choice-labels.test.mjs` y `operation-dialog-context.test.mjs` como contexto, sin atribuir su ejecución al revisor.
- `docs/PLAN-CIERRE-RACKCLICK.json`: I-04/I-04.02; `docs/PROGRESO-GLOBAL.md` y `docs/CIERRE-METRICA.json`: métrica vigente; AGENTS, briefing, continuidad, equipo/perfil UX y documentación inicial de contrato/aceptación consultados para límites.

Huellas SHA256 del producto revisado:

| Archivo | SHA256 |
| --- | --- |
| inventory-choice-labels.ts | `707139849eb000913dc9e6da32d0b20f89dfc929445be0ffedc5eb9a0c728938` |
| OperationDialog.jsx | `d69baabd0fbc17288884777e7aabb2ec575dba6e4e8471417a8ba23a550dd2cd` |
| InventoryPanel.jsx | `03cc6de0ee9b1e9881b2761801c8cb0025817804b4b382c3bbf96cac03579ebd` |

## Prueba ejecutada por este revisor

Entorno: Windows/PowerShell, Node existente v24.21.0, esbuild existente 0.25.10. Sin instalación ni build completo; esbuild sólo transforma en memoria JSX extraído de fuentes reales.

```powershell
& 'C:/RackClick_SVR/.local/node-v24.21.0-win-x64/node.exe' --test evidence/s1-20261025/c2-rack-variants-codex/review-fields.test.mjs
```

Resultado real: **exit 0; 7 tests, 7 PASS, 0 FAIL, 0 skipped; 371,1125 ms**. Node emitió aviso `MODULE_TYPELESS_PACKAGE_JSON` al detectar módulos ES en los TS existentes; no error, sin cambiar `package.json`.

1. Productores reales de padres site/building, sala de rack, destinos compartidos rack/dose/endDevice y movimiento de equipo de rack: homónimos distinguibles por UUID completo, nombre literal y título en EN/DE/ES.
2. Título del select y opción correspondiente al UUID seleccionado, cambio de selección, ausencia de selección y coincidencia numérica/string.
3. Placeholder `unassigned`, yes/no y cinco estados patch traducidos en los tres idiomas.
4. `__proto__`, `constructor`, `toString`, Unicode/combining y apariencia HTML preservados como hijos string y títulos string; sin `dangerouslySetInnerHTML`. Traducción rechaza propiedades heredadas del diccionario. Nombre literal exacto `room` sin sufijo también se conserva.
5. Etiqueta envolvente, `name`, `required`, disabled global/local, filtro show, opciones dinámicas y callback normal/personalizado conservados; formulario original intacto.
6. Comparación completa y normalizada de ambos JSX con los originales, descontando exclusivamente el delta autorizado: igualdad exacta; no cambio de lectura/escritura ni comandos.
7. Reproducción de defectos de etiquetas/títulos con fuentes anteriores, sin error artificial por módulo nuevo ausente.

Fixture SHA256: `400c7214fc68ec91fcc8fa5c4cbdb36934c44d58026f722a9237ef643dc4b5a0`.

## I-04.02 y atribución

Texto exacto: «Focos de editar/reasignar rack, reducciónU con ocupación, equipo/metadatos/presets y tooltips por UUID/homónimos.» Peso existente `5/14`, sin modificarlo.

La prueba nativa comprueba un rack reasignado a roomB por UUID y reducido a 2U ocupadas; rechazo 409 de 1U con borrador y proyecto íntegros; homónimos site/building/room/rack; creación real del preset servidor `sw8p` con IDs nuevos y propiedades/grupos/puertos exactos; edición de nombre/2U/budget cero/cinco metadatos literales conservando el resto; tooltips, recarga y segunda sesión. El texto no exige agotar los 33 presets; no extender el crédito a Dosen, duplicado, drag/táctil, candidata final o QA de Wascar. I-04.03–07 conservan sus propios criterios.

**Condición nativa cerrada mediante lectura de recibos aportados por el coordinador:** `EDGE-PG.json` registra PASS 22,0 s, Edge exit 0, PostgreSQL 17.11, filas originales/cambios previstos y filas del preset exactos, metadatos no-notas y grupos/puertos/cables conservados, `serverRestartPersistence=true` y `inputsUnchanged/labStopped/serversStopped=true`. `NAVEGADOR.json` registra cuatro focos PASS, recarga y segunda sesión autorizada, una única respuesta de comando 409 esperada y `jsExceptions=[]`. `ORIGINAL.json` conserva FAIL 26,61 s con inputs intactos y laboratorio detenido; `ORIGINAL-DIAGNOSTICO.json` lo vincula al assert real de nombre literal `siteA`, no a un módulo ausente. Estos cuatro recibos fueron leídos por el revisor; las ejecuciones pertenecen al coordinador.

**Dictamen final: conforme acreditar I-04.02 (`5/14`) en el alcance descrito**, sumando mis siete pruebas independientes y el contraste de recibos nativos, sin editar aquí el ledger. **No he ejecutado Edge/PostgreSQL ni el runner nativo**, ni inspeccionado personalmente sus capturas; la inspección de `rack-move-literal-options.png` y `rack-edit-repeated-paths.png` es del coordinador. La regresión adicional de permisos/recuperación sigue en ejecución según su comunicación; no se declara pasada en este informe. Sin ensayo Windows reboot, VM o QA/adopción.

Avance: este informe no cambia puntos ni inventa porcentaje global. Métrica vigente consultada al inicio: `4,785714/100` del cierre del trabajo restante, porcentaje global del producto nulo; el 78 % histórico está retirado. El coordinador puede actualizar exclusivamente la fracción `5/14` de I-04.02, conforme a los pesos existentes.
