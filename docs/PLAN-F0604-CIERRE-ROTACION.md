# F-06.04 · plan de cierre técnico de rotación

11.11.2026. Ejecución autorizada por Wascar del paso22. Se conserva D y también E. Método: implementación del arnés por el coordinador y revisión independiente acotada; sin commits, push o despliegues.

**Objetivo:** contrastar el criterio literal F06: cada interrupción recuperable, factores y backups retenidos descifrables con versiones conservadas y rechazo explícito de faltantes.

**Arquitectura:** reutilizar íntegramente F0601–03. Añadir sólo ensayo encadenado en laboratorio Windows/PG17.11, con catálogo no vacío, dos rotaciones y restauración de cada generación retenida en otro clúster nuevo. Sin ampliar API de producto, CLI, dependencias o esquema46.

**Especificación:** `PROTOCOLO-ROTACION-MFA-v1.md`, `D2-CONDICIONES-TECNICAS-F03-02.md`, criterio/hitos congelados de F06 y evidencia revisada de F0602/F0603.

## Decisiones y límites

Se consideraron: conciliar sólo documentos (no demuestra recuperabilidad de backups no vacíos después de rotar), repetir todas las suites/cortes (duplica pruebas invariantes) y añadir el escenario encadenado faltante. Se elige el tercero. Las quince caídas, dos Restores de transición y negativos existentes se reutilizan con sus pines y atribución histórica; no se presentan como ejecuciones nuevas.

El cierre técnico no implica CLI pública, candidata instalada46, SID de servicio efectivo, servicio/HTTPS/login instalados, custodia física externa, apagón o aceptación de Wascar. Esos hitos permanecen pendientes. «Todos» cubre el conjunto retenido declarado y comprobado, no medios omitidos/desconectados. Restore de este lote es offline con identidad explícita; no habilita una DB antigua junto al journal vivo ya completado.

## Investigación previa

Se reutilizan catálogo/retirada, proveedores y codecs aprobados. Consulta oficial11.11: [pg_dump17](https://www.postgresql.org/docs/17/app-pgdump.html), [pg_restore17](https://www.postgresql.org/docs/17/app-pgrestore.html). Se usa custom, snapshot exportado compartido con el censo y restore en transacción en DB nueva; sin instalar ni copiar código externo. PostgreSQL no transporta archivos DPAPI: la conservación/autenticación del material se prueba aparte con componentes RackClick.

## Tareas

- [x] **1. Contraste y trazabilidad.** Matriz literal→evidencia/hash/límite; conservar45SQL históricos, fuentes F0603, ledger y172+1casos QA. No modificar producto para fabricar un cierre.
- [x] **2. Recorrido integrado.** Crear tres factores pending/active/disabled en versiones1/7; dump/censo/sobre anteriores; rotar a8; segundo backup; catálogo completo; rotar a9. Autenticar factores y sobres, bloquear retirada1/7/8 dependientes sólo de backup, rechazar material ausente y catálogo alterado sin cambiar DB/disco. Restaurar cada dump en clúster nuevo y autenticar cada factor con las claves conservadas y con su sobre de generación. Fuente invariable por cada Restore.
- [x] **3. Verificación y revisión.** Build aislado/pines, casos nuevos y sensibilidad por defecto temporal sólo en copia privada si pertinente, revisión distinta con ejecución acotada. No repetir360casos ni15cortes de código idéntico.
- [x] **4. Continuidad y contabilidad.** Registrar resultados reales, fallos/límites, ficha22 y dictamen. Sólo si favorable conciliar F0604 y los hitos técnicos que cumplan su criterio, conservar integración/aceptación pendientes; regenerar índices/guía y verificar privacidad/huellas.

## Foco de revisión

- No tomar un catálogo vacío como prueba de backups anteriores.
- El censo y el dump deben describir la misma instantánea; no construir un inventario ficticio.
- Verificar secretos/metadatos de todos los estados, no sólo conteos/versiones.
- La versión que sólo necesita un backup sigue siendo imprescindible y su ausencia bloquea.
- Restaurar cada generación con todo su material, sin escribir sobre DB/tienda origen ni confundir guard offline con servicio arrancado.

Archivos previstos: `MfaRotationClosureTests.cs`, `tools/tests/run_mfa_rotation_closure.py`, ficha/evidenciaF0604 y registros de continuidad. Producto y guiones existentes conservados salvo fallo reproducido, que exigiría prueba roja/corrección/revisión separadas.

Cierre técnico11.11: [resultado](../evidence/s1-20261111/f06-04-cierre/RESULTADOS.md) y [dictamen](../evidence/s1-20261111/f06-04-cierre/review/DICTAMEN.md). Sin cambios de producto; hitos operativos separados y pendientes.
