# C2 · inversa API de reducción pura · cierre de desarrollo

25.10.2026 · Implementación Codex; revisión de un agente distinto `c2_reduction_rules`.

## Resultado

`operations.compensate` admite ahora la reducción pura de grupos/puertos de una edición propia con evidencia v1 completa. Restaura grupos, puertos, cables y ambos extremos con UUID, propiedades, atributos y `created_at` originales, sin snapshot aportado por el navegador. Exige identidad/ámbito/revisión, supervivientes idénticos, ausencia de IDs reutilizados y estado actual exacto después de bloquear. También bloquea los puertos remotos que la captura del dispositivo no contiene como filas completas.

Inserta grupos → puertos → cable → sus dos extremos con SQL literal parametrizado y columnas explícitas. No inserta la columna generada, no hace UPSERT, no genera identidades/fechas sustitutas y no elimina conexiones actuales para restaurar las antiguas. `Pair`/`ConfirmReserved` y la autorización vigente se conservan; cualquier conflicto revierte el conjunto. El flujo existente produce revisión/auditoría/operación y confirma sólo después del commit.

El adaptador valida la variante cerrada `groupReduction` con tres conjuntos de IDs restaurados. La vía anterior de atributos y la nueva de crecimiento conservan sus contratos. No se habilita GUI estructural ni detalle/contexto ficticio del feed. [Contrato, archivos, límites y continuación](../../../docs/C2-INVERSA-REDUCCION-25-10-2026.md).

## Build y comandos reales

Workspace privado `.local/c2-reduction-20261025-3936b00ab633`, snapshot `source`. SDK **10.0.401**, Npgsql **10.0.3**, PostgreSQL **17.11**, Node **24.21.0**, Windows. Snapshot global.json ajusta sólo búsqueda absoluta del SDK local, conservando versión/rollForward. Publicación tras cargar `tools/windows/Use-Toolchain.ps1` y la caché NuGet local:

```powershell
.local/dotnet-10.0.401/dotnet.exe publish <workspace>/source/development/server/src/RackClick.Server/RackClick.Server.csproj -c Release -o <workspace>/app -p:UseAppHost=false -p:RestoreLockedMode=true '-bl:<workspace>/publish-{}.binlog'
```

Exit 0; binlog comprobado, privado. **DLL `5eb1abcf9d2f91d293bae8f1b01e94f0352ca254c0387aaa45de1c35b2a97585`**. Entradas seleccionadas de build, 102, en `BUILD-INPUTS.json`; no es manifiesto de distribución.

Prueba principal:

```powershell
C:/Python312/python.exe -X utf8 -B .local/c2-reduction-20261025-3936b00ab633/run-job.py green
```

Job Object, timeout 300 s, imports/SQL del snapshot, herramientas/laboratorios del repositorio. Clúster nuevo y una base/owner/runtime nuevos por caso; todos detenidos al terminar. No son las cuentas/bases de una instalación. Resultado inicial: **11 ejecutados, 10 conformes, 0 fallos de aserción y 1 error de fixture**, sin omisiones.

## Corrección comprobada del fixture y cobertura final

El caso de puerto remoto ocupado creaba un cable sintético en dos statements sin transacción. El trigger diferido de dos extremos se ejecutaba al terminar el INSERT del cable, antes del INSERT de extremos. Falló preparando datos, sin llegar a probar ese conflicto del producto. Se corrigió con `BEGIN/COMMIT`, manteniendo activos los triggers. Se conserva la ejecución original; no se atribuye su error al producto.

Se reforzó además el foco sin cables para reducir sólo un grupo existente: los arrays de grupos y cables restaurados quedan vacíos. Se ejecutaron **únicamente esos dos focos, 2/2 correctos**, con los helpers copiados a `tests02` y el test corregido; el snapshot original y la DLL no se modificaron:

```powershell
C:/Python312/python.exe -X utf8 -B .local/c2-reduction-20261025-3936b00ab633/run-focused-job.py focused02
```

Último caso nuevo mediante la CLI real del test: eliminación de todos los grupos de un dispositivo de alimentación, cable eléctrico y rol remoto incompatible → 409; con rol compatible se restaura el `before` exacto. **1/1**, clúster nuevo/detenido, misma DLL. Lanzador privado `run-power-cli.py` dentro de Job Object; invoca `test_group_reduction_compensation.py --dll <workspace>/app/RackClick.Server.dll --evidence <workspace>/power-cli-result --cases test_all_groups_removed_power_pair_revalidated_before_exact_restore`, con herramientas y SQL del snapshot.

`RESULTADOS.json` separa estas ejecuciones: **12 casos distintos cubiertos después de la corrección, nueve nuevos y tres regresiones**, sin afirmar una nueva suite conjunta de doce. Incluyen:

- Restitución exacta de filas, UUID, propiedades anidadas, Unicode, NULL/cero/decimal, fechas y ambos extremos, conservando un cable superviviente.
- Restauración sin grupo/cable que reinsertar, replay, cancelación comprometida, reinicio, journal y última revisión.
- Evidencia ausente/incompleta/corrupta, extremo ausente/duplicado, fecha inválida y edición mixta: rechazo sin escrituras.
- Estado modificado, IDs ocupados en otro dispositivo, otra revisión; extremos remotos reservados, disabled/faulty, ocupados o ausentes: sin desplazamiento ni sobrescritura.
- Actor/cliente —mismo actor autorizado en dos ámbitos—, CSRF, permiso revocado y sesión caducada durante espera real.
- Fallo de auditoría revierte todas las inserciones; dos peticiones concurrentes producen un commit y un 412, una sola auditoría de compensación.
- Eliminación de todos los grupos y revalidación eléctrica antes de restaurar.
- Regresiones de evidencia de reducción, inversa de crecimiento y compensación anterior PoE/watts/reinicio.

La expectativa activa de `test_group_edit_evidence.py` se actualiza a restauración positiva, porque ese caso ya está soportado. No se reescriben informes, comandos ni snapshots históricos que acreditaban su rechazo anterior. La fuente final del test nuevo y los cambios posteriores al snapshot quedan identificados por hash.

## Frontend, negativo y revisión distinta

Node `--test --test-reporter=tap` sobre las cuatro familias de pruebas de compensación del snapshot: **16/16**, cuatro nuevas y doce regresiones (`FRONTEND.tap`). Respuestas ambiguas/alteradas mantienen incertidumbre; replay/cancelación comparten controles; expectativas antiguas rechazan la variante estructural. Se mantiene el aviso preexistente de tipo de módulo. No se ejecutó navegador ni build de distribución.

Control negativo `run-job.py red`: el caso positivo nuevo contra la DLL anterior `40bc8098…` recibe 422 `compensation_unsupported`, fallo esperado, clúster detenido (`CONTROL-NEGATIVO.json`). Se ejecutó después de escribir fuentes; no se anuncia fase roja previa/TDD.

[REVISION.md](REVISION.md): favorable acotado, sin hallazgos bloqueantes. **1/1 PostgreSQL independiente**, con espera observada mediante `pg_blocking_pids`: un propietario sintético modifica un extremo remoto a faulty y confirma antes de liberar el lock. La inversa rechaza 409, preserva todas las filas posteriores, revisión y cantidades de auditoría/operaciones. Laboratorio detenido, DLL igual. El revisor inspeccionó los resultados/deltas de tests del implementador, sin atribuirse sus ejecuciones ni repetir la suite.

## Conservación, integridad y límites

`GUARDAS.json`: 195 archivos existentes de otras fuentes/SQL/frontend iguales a la línea base. Candidata `f11a689e…`, manifiesto `2ec91056…` y ZIP interno 14-02 `191acd6f…` mantienen sus hashes. No se cambian dependencias, SQL, MFA, Program/PostgresStore, instaladores, servicios, paquetes, bases existentes o QA/VM. No hay commits/push ni adopción. `FUENTES-EXISTENTES.diff` compara las tres fuentes existentes con el estado previo de C2; archivos nuevos y documentos se identifican en `SHA256SUMS.txt`. Logs, credenciales, clústeres y binlogs quedan privados.

`VERIFICACION.json` registra formato, sintaxis, escaneo acotado y comando de integridad. No se declara limpieza del historial por revisar este bloque. Los resultados anteriores se conservan como historia. No se habilitan casos QA ni se regeneran guías, porque la disponibilidad visible no cambia.

Faltan GUI/confirmación/recuperación de incertidumbre, cambios mixtos/reordenamientos y consentimiento de reservados; la matriz física completa RC9, incluyendo límites de familias/PoE, sigue pendiente. Dosen/finales conservan D5. Integrar en una futura candidata coordinada con Claude y repetir controles sobre ese artefacto; esta DLL privada no sustituye su paquete. Instalación, MFA, recuperación y QA/adopción final siguen en sus frentes.

**Global aproximado: 78 %.** Se amplía la cobertura verificable de C2, sin cerrar todavía el frente completo.
