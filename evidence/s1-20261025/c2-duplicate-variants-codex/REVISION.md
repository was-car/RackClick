# Revisión independiente — I-04.03 duplicado de rack

25.10.2026. Revisor distinto de los autores del producto y de los tests nuevos. Propiedad limitada a este informe y `review-sql-sensitivity.py`. Git inspeccionado antes; cambios ajenos conservados. No se editó producto ni tests de otros autores; sin builds, instalaciones, DB, navegadores, VM, QA, MFA o ledger ejecutados/modificados por el revisor.

## Dictamen

**Conforme acreditar exclusivamente I-04.03 (`5/14`), sin hallazgos bloqueantes nuevos.** Texto exacto leído en `docs/PLAN-CIERRE-RACKCLICK.json`: «Duplicado sin/con cables y reserved confirmado válido; conservar negativos existentes.» No acredita I-04 completo, Dosen, orden/drag/táctil, candidata final, accesibilidad/paridad completas ni QA/adopción de Wascar.

El verde nativo nuevo y la batería existente cubren el texto acotado. Mis tres pruebas propias verifican sensibilidad del comparador SQL; las ejecuciones Edge/PostgreSQL pertenecen al coordinador y sólo fueron contrastadas por lectura de recibos.

## Fuente y prueba revisadas

- `InventoryDuplicate.cs`, `InventoryStore.DuplicateRack`: cada rack/equipo/grupo/puerto recibe `Guid.NewGuid`; `portMap` usa UUID, no `gn`. Sólo con `includeConnections=true` selecciona cables cuyos dos extremos pertenecen a puertos del rack fuente y remapea ambos. `ConfirmReserved` recibe los puertos originales de esos cables internos; un reservado suelto y el cable externo quedan fuera. Sin cables omite esa confirmación.
- `InventoryConnections.cs`: `Pair` rechaza `disabled/faulty`; `ConfirmReserved` exige igualdad exacta de conjuntos de UUID reservados, no inclusión parcial. Se revisó también `ConnectionRow`/`InsertConnection`.
- `InventoryStore.cs`: `Execute`/`Apply` ligan autorización, revisión, altas, operación, auditoría y commit a una transacción. Las altas previas a una confirmación inválida no pueden aceptarse como éxito por una compilación.
- `InventoryPanel.jsx`: `duplicateRack`; `inventory-model.ts`: `internalCablePortIds`, `reservedPortIds`. El payload GUI confirma sólo los UUID originales reservados de cables internos y devuelve lista vacía al excluir cables.
- `browser-duplicate-variants.mjs`: `assertCopy`, `openDuplicate`, `oneAuditCommit`; dos envíos reales, formulario inválido sin POST/auditoría, mapeo por equipo/grupo/orden, identidades disjuntas aun con `gn` repetido, originales/externo conservados, recarga/otra sesión y render de topología.
- `test_duplicate_variants_gui.py`: `assert_sql_variants`, `fixture`, `checked_paths`, `main`; estado esperado de las nueve tablas construido desde **before + mappings**. De `after` sólo incorpora el `created_at` permitido del cable nuevo, exigiéndolo posterior al original; los demás atributos derivan de `before`. Cuenta exactamente dos revisiones, operaciones y auditorías, y comprueba reinicio con ambas cuentas y `atomic_state` íntegro.
- `test_inventory_duplicate_gui.py`: batería existente leída; `fixture`, `assert_sql_copy`, `atomic_state`, negativos y ámbitos. Sin modificar ni repetir su ejecución.

## Pruebas propias ejecutadas

```powershell
& 'C:/Python312/python.exe' -B evidence/s1-20261025/c2-duplicate-variants-codex/review-sql-sensitivity.py
```

Windows/PowerShell, Python 3.12 existente. **Exit 0, 3/3 PASS, 0,009 s**. Se extrae por AST únicamente `assert_sql_variants`; no se importa el runner ni sus dependencias de laboratorio. Matriz artificial propia de nueve tablas con originales/externo, dos copias, `pa` conectado y `extraPort` suelto reservados, y `gn=1` repetido en grupos distintos.

1. Control positivo acepta sólo adiciones previstas `0/0/0/2/4/6/10/1/2` y conserva todos los argumentos.
2. Rechaza cambios individuales de label, power_role, connector_family y properties de puerto copiado; ubicación del rack original; nota del cable externo y del copiado. Demuestra que no acepta atributos arbitrarios tomados de `after`.
3. Rechaza alias de UUID con el original o la primera copia, incluso actualizando coherentemente mapping/fila; rechaza redirigir un extremo copiado a `extraPort` reservado suelto.

Sin ejecución propia de Edge/PostgreSQL, pruebas de teclado/lector de pantalla, zoom, responsive, reboot Windows ni apertura de capturas.

## Evidencia nativa contrastada, ejecutada por el coordinador

- `EDGE-PG-VARIANTES.json`: **PASS 23,219 s**, PostgreSQL 17.11, browser exit 0. Dos racks/cuatro equipos/seis grupos/diez puertos/un cable/dos extremos añadidos; nueve tablas, originales/externo y ambos remapeos exactos; conjuntos UUID disjuntos; casilla requerida bloquea HTTP/auditoría; sólo confirma UUID antiguos; **2 operaciones y 2 commits**. `serverRestartPersistence`, `atomicReadRestartUnchanged`, `inputsUnchanged`, `labStopped` y `serversStopped` verdaderos; QA real no accedida.
- `NAVEGADOR-VARIANTES.json`: Edge `156.0.4314.42`, tres focos PASS y `jsExceptions=[]`; sin cables pese a `pa` reservado conectado, con cable tras confirmación válida sólo de `pa`, excluyendo `extraPort`/externo/copias; recarga y segunda sesión exactas.
- `REGRESION-EXISTENTE.json`: **PASS 33,469 s**, PostgreSQL 17.11. Mantiene 409 por confirmación vacía/UUID externo incorrecto, `disabled/faulty`, dos ámbitos sin edición 403/lectura externa 404 y duplicado cross-customer 404. Cada rechazo conserva `atomic_state` (inventario + customer/revisión + operation + audit_event). Reinicio y entradas intactas, laboratorio/servidores detenidos.
- `NAVEGADOR-EXISTENTE.json`: recorrido previo con cable interno/exclusión del externo y dos sesiones PASS, sin errores. Declara explícitamente sus anteriores límites sin duplicado sin cables ni positivo reserved; el escenario nuevo cubre esos huecos, sin atribuirlos retrospectivamente a esa batería.

## Huellas y límites finales

| Archivo revisado | SHA256 |
| --- | --- |
| test_duplicate_variants_gui.py | `c7d07806a25c2cc23ab25a8d89d20eb015c9f13cef37183f38400b610de75154` |
| browser-duplicate-variants.mjs | `44a72c8cbd7e0ee0e08d62e06b2d49886bcd31084719e4dd8928d668e13fc463` |
| review-sql-sensitivity.py | `10d53c4b179e59e5b730896fd3ad4bf91a4729161ba0c39a8ba51b9e1b58a548` |
| InventoryDuplicate.cs | `4d4ed9524d2bb637dc9c30009ce05c4059d2d5bae6a38e9a5af0c96d4d039f3a` |
| InventoryConnections.cs | `99889fa10ac5dcb62dbb6441acb0537ac9a530e6704acb962655499c2d7cc751` |

Las nueve tablas se comparan íntegramente, aunque site/building/room están vacías en el laboratorio nativo; mi matriz artificial sí contiene filas de jerarquía. Cobertura de dos variantes de rack y un cable interno, no matriz exhaustiva de topologías. No se afirma porcentaje global ni se altera la métrica: el coordinador puede registrar la fracción fija `5/14` de I-04.03 con estas evidencias; el 78 % histórico continúa retirado.
