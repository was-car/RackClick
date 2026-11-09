# Catálogo SQL17 — resultado de la tanda

30.10.2026. Las cuatro referencias de hardware ya tienen definiciones, grupos,
alojamientos y correspondencias en PostgreSQL, con revisiones selladas y lectura
limitada para la cuenta de ejecución. El comando consulta y contrasta ese catálogo
antes de crear o montar un equipo. [Contrato](CONTRATO-CATALOGO-SQL17.md).

Se añade explícitamente una migración017; SQL001–016 y hw-reference-v1 conservan
sus bytes. La instalación10, cuentas/MFA, VM y datos de Wascar quedan intactos.
No hay fabricantes nuevos ni cambio visible del selector.

| Verificación ejecutada | Resultado |
|---|---|
| Build aislado | SDK10.0.401, restore locked/Release:0errores/0advertencias; binlogs privados por invocación. |
| Autoría/registro | 27 pruebas del compilador y4del registro C# PASS; fuente y dibujo congelados. |
| Frontend | Build con37adaptadores y814pruebas Node PASS; dibujo/acciones conservados. |
| PostgreSQL17.11 | 8comprobacionescompuestas PASS: actualización16→17 real con81puertos/3cables, replay previo, digests, runtime real sin DML/DDL de catálogo, sellado/revisiones, deriva/permisos incorrectos, fallo de migración atómico, bootstrap1→17 y persistencia tras reinicio. |
| Regresión de montaje | 20comprobacionescompuestas/14negativosHTTP PASS; constraints, concurrencia por slot, rollback de auditoría, cableado y otra cuenta/reinicio. |
| Revisión distinta | 15focospropiosPASS, incluida carrera real sellar→insertar y prohibición de asociar una instancia a un borrador. |

Dos P2 se corrigieron durante la revisión: se podían añadir componentes a una
revisión ya existente, y SQL permitía asociar una instancia a un borrador aunque
la API lo rechazaba. Ambos quedaron reproducidos y cerrados antes del resultado
final. [Dictamen](REVISION-CATALOGO-SQL17-30-10-2026.md).

Se conservan intentos fallidos de fixtures: TRUNCATE y duplicados eran rechazados
por una guarda anterior al mensaje esperado; la regresión antigua esperaba
diagnósticos exclusivos de SQL16 en cuatro casos. Se ajustaron esas expectativas
a las guardas más fuertes, manteniendo rechazo y comparación exacta sin cambios.
No se relajaron las negativas ni se modificó producto para satisfacerlas.

Evidencia, hashes, comandos y límites:
`evidence/s1-20261030/hardware-sql17/RESULTADOS.md`.
Todos los laboratorios de esta tanda están detenidos. No se repite Edge ni se
presentan sus capturas históricas como ejecuciones de17: no hay interacción nueva
y el frontend construido conserva el mismo hash de aplicación de la tanda previa.

**Siguiente:** preparar la publicación controlada de modelos que use este contrato,
con un primer modelo comercial verificado; completar consumidores de montaje y
después distribución/operadores17 y candidata completa para QA136/137.
También falta el recorrido de backup/Restore17 y su integración con permisos.

Sin commits, push, cambios en VM/QA o paquetes nativos.
**Índice de cierre restante:9,76/100**, sin crédito automático. No acredita todo
C-HW-02/C-HW-06 ni representa un nuevo porcentaje global del producto.
