# C2: evidencia de edición de grupos

25.10.2026 · Codex, mientras Claude propaga instalación 14.

## Propiedad del lote

Codex toma únicamente `InventoryImpact.cs` (captura before/after de `EditPortGroups`), el nuevo `InventoryGroupEditEvidence.cs`, la nueva prueba `test_group_edit_evidence.py`, este documento y `evidence/s1-20261025/c2-grupos-evidencia-codex/`. Claude conserva MFA, instalación, Stage/runtime/migración/Restore, locks y paquetes. Sin cambios de rutas compartidas, esquema, GUI o QA/VM; sin commits.

## Objetivo acotado

Preparar evidencia versionada, generada por el servidor y acotada al dispositivo, con filas completas de grupos, puertos y conexiones antes/después de editar grupos. La captura participa en la misma transacción y auditoría que la operación. Es fundamento de la inversa estructural pendiente: este lote **no ofrece ni anuncia deshacer grupos**. Los registros históricos y el rechazo actual de compensación estructural se conservan.

La conciliación C2 del 23 ya confirmó S-14/S-30 parciales. Dosen/dispositivos finales y pasos físicos mantienen D5 del plan: no se amplía su alcance en este lote. Evidencia anterior: `docs/C2-CONCILIACION-INVENTARIO.md`.

## Resultado implementado

`groupEditEvidence` versión 1 se añade a los dos lados de la auditoría de `device.editPortGroups`. Conserva las filas SQL completas de grupos y puertos del dispositivo, conexiones afectadas y **ambos extremos** en `inventory_connection_endpoint`, con sus UUID, atributos, propiedades y fechas. Las arrays tienen orden estable. La captura anterior precede al borrado y la posterior lee las filas persistidas después de validar alimentación, en la transacción existente. Se conservan los campos de auditoría previos y la respuesta del comando.

La evidencia se genera desde PostgreSQL y no procede del objeto del navegador. Si un lado supera 8 MiB, ambos se guardan con `complete:false` y motivo `size_limit`; la edición puede seguir confirmándose. El límite corresponde al subobjeto nuevo transferido a .NET, no a todo el audit ni a memoria de PostgreSQL. La futura inversa deberá rechazar evidencia incompleta y comprobar estado/identidad, autorización y revisión; capturar no equivale a poder restaurar.

## Pruebas y versión

- SDK **10.0.401**, PostgreSQL **17.11**, Windows real. Publicación de un snapshot privado con versiones fijadas, sin apphost y con binlogs privados. DLL de desarrollo nueva: **`e3a217cc5dc55b1cb10241a628a989b7974d6060f1f748887b85c916e541eaa1`**.
- **6/6 pruebas del implementador**: cuatro nuevas (filas completas/scope/datos aportados por cliente, reducción con cable eliminado/replay/reinicio/rechazo de inversa, rollback por fallo de auditoría y evidencia sobredimensionada), más las dos regresiones existentes de ampliación y reducción.
- **1/1 adicional del revisor independiente**, crecimiento en otro clúster nuevo sobre la misma DLL. Dictamen favorable, sin habilitar inversa ni GUI. Clústeres detenidos.
- Control negativo sobre la DLL anterior `f11a689e…`: falla por ausencia de `groupEditEvidence`, resultado esperado. Se conserva separado el primer intento que falló por un fixture que confundía la proyección de conexiones con sus tablas normalizadas; la corrección usa `inventory_connection_endpoint` tanto en captura como en contraste.

No se modificaron los otros 78 archivos de producto seleccionados, autenticación/MFA, esquema, UI, locks, herramientas de instalación o paquetes. **La candidata de Claude sigue siendo `f11a689e…`/manifiesto `2ec91056…`; esta DLL no la sustituye.** Integrar después requiere nueva identidad de build/candidata y revisión de esa combinación. No se cambia QA/VM, no se publican secretos, no hay commits.

Evidencia, diff, entradas de compilación/hashes y revisión: [CIERRE.md](../evidence/s1-20261025/c2-grupos-evidencia-codex/CIERRE.md). Sin cambio visible no se habilitan casos ni se regenera la guía QA.

## Próximo paso

Implementar primero una inversa de crecimiento propio que use únicamente esta evidencia versionada y compruebe revisión/estado/identidades/permisos, con replay/conflictos/rollback. Después reducción/restauración de cables y ampliación explícita de los DTO/detalles y GUI existente. Los registros anteriores sin evidencia suficiente siguen fuera del contrato de inversa. **S-14/S-30 y C2 continúan parciales. Global aproximado: 78 %, sin incremento por este fundamento.**
