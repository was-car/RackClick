# Revisión independiente · F-06.04

11.11.2026. Revisor distinto del implementador del ensayo y de los componentes previos. Encargo acotado de seguridad y cierre técnico. Inspeccioné las fuentes y ejecuté el recorrido integrado en un laboratorio PostgreSQL nuevo; no modifiqué producto, pruebas, fuentes del arnés, instalaciones, ledger, cuentas o servicios. D y E quedaron fuera de mis operaciones. Sin commits ni publicación.

**Dictamen favorable para F-06.04 técnico, peso congelado5/8.** El criterio literal queda sustentado por evidencia compuesta y trazable: las caídas/conciliación ya revisadas de F-06.03 y el nuevo recorrido con un catálogo no vacío, dos rotaciones y restauración/autenticación de cada generación retenida. No afirma cierre operativo D2, candidata instalada, custodia externa ni aceptación de Wascar.

## Criterio y brecha contrastados

El criterio congelado dice: «Cada punto de interrupción tiene estado recuperable demostrado; todos los factores/backups retenidos siguen descifrables con versiones conservadas y faltantes se rechazan explícitamente».

Consulté `AGENTS.md`, `docs/BRIEFING-MAESTRO.md`, continuidad/progreso, D2, `D2-CONDICIONES-TECNICAS-F03-02.md`, el protocolo F-06.01, los cierres F-04.04/F-05.05 y el registro F06. Se mantienen gracia45/exención global y la separación de checkpoints técnicos frente a integración/aceptación operativa.

La lectura previa detectó que `MfaRotationProcessTests` declara un catálogo con `entries=Array.Empty<object>()`. Sus quince cortes prueban recuperación de DB/material en transición; no prueban por sí solos el conjunto de backups retenidos antes y después de rotar. Lo comuniqué al coordinador antes de añadir el escenario de cierre. No se trató como defecto de producto ni se alteraron las pruebas históricas.

## Archivos y símbolos revisados

- `MfaRotationCoordinator`: `PrepareAsync`, `ExportAsync`, `ResumeAsync`, `VerifyEnvelope`, `RequireWitness`, `Catalog` y exclusión. `MfaMaintenanceCoordinator`: `ValidateMaterial`, `AuthenticateFactors`, catálogo monótono y rechazo de retirada referida. `MfaKeyRetention`/`MfaBackupCatalog`: dependencia por versiones, recibos/pines y apertura del conjunto exacto declarado.
- `MfaRotationDatabase`, SQL046, publicadores/recibo de `WindowsMfaMaintenanceStore.Rotation*` y `MfaRotationStartupGuard`, como fuentes históricas conservadas, contrastadas con su evidencia revisada. No repetí una auditoría completa de cada primitiva ya aprobada.
- Nueva prueba `MfaRotationClosureTests.RetainedGenerationsWorker`: `Backup`, `Rotate`, `Authenticate`, ramas seed/rotate/restore, captura del secreto por huella privada, comparación de metadatos y negativos de material/dump.
- Nuevo `tools/tests/run_mfa_rotation_closure.py`: pines antes/después de cada fase, DB/clústeres nuevos con identidad nativa explícita, pg_dump custom y pg_restore en transacción; ausencia de fallback a una instancia instalada.
- `PLAN-F0604-CIERRE-ROTACION.md`, ficha22, `RESULTADOS.md`, `MATRIZ-CIERRE.md`, `RETENIDOS.json`, `FUENTES.json`, `PIN-NEGATIVO.json` y diff local. El primer build fallido por inputs de catálogo ausentes queda declarado como fallo de preparación, sin alterar producto ni rebajar el target.

## Ejecución propia

Fuente aislada: `.local/f0604-af3681af/freeze`. Windows nativo, SDK10.0.401/runtime10.0.12, PostgreSQL17.11 y esquema46.

| Binario | SHA256 |
|---|---|
| RackClick.Server.dll | `3a39bb95e2fc45b3eccff3376b53535d0273766743204874180f1112e62956fd` |
| RackClick.Quality.Tests.dll | `2e189e549b897e9e5a28318f0277318c67dd93df7a50c044de02f7860003f0ed` |

Ejecuté, desde la raíz del repositorio:

```powershell
C:/Python312/python.exe -B tools/tests/run_mfa_rotation_closure.py --source-root C:/RackClick_SVR/.local/f0604-af3681af/freeze --expected-server-sha256 3a39bb95e2fc45b3eccff3376b53535d0273766743204874180f1112e62956fd --expected-tests-sha256 2e189e549b897e9e5a28318f0277318c67dd93df7a50c044de02f7860003f0ed
```

Resultado propio: **exit0; cinco fases xUnit correctas, cero fallos y cero omitidas**. Preparación1/1, dos rotaciones encadenadas1/1 y tres Restores/autenticaciones3/3. Son cinco invocaciones del mismo trabajador, no cinco funciones de producto ni una nueva suite completa.

- Tres factores sintéticos active/pending/disabled, versiones iniciales1/7; rotaciones a8 y9. Los metadatos, estados, antirreplay y huellas de los mismos secretos se conservan. El proveedor y guard finales aceptan el conjunto coherente.
- Catálogo con tres generaciones reales: `[1,7,7]`, `[8,8,8]` y `[9,9,9]`. El dump y censo comparten snapshot exportado. Las retiradas1/7/8 devuelven `mfa_retirement_backup_referenced` aunque los factores vivos ya usan9.
- Falta de clave1 —dependencia sólo de backups— y alteración del primer dump rechazan preparar otra rotación sin crear fence ni cambiar la huella DB/anillo. El fixture restituye exclusivamente su propio objeto y compara material conservado.
- Tres pg_restore reales, cada uno en otro clúster/DB nuevos. Cada generación autentica sus tres factores con el anillo final9 y con su propio sobre recuperado en un almacén nuevo. La falta de una clave requerida en cada destino se rechaza; después de restituirla vuelven a autenticarse. Las filas destino no cambian por estas comprobaciones.
- La huella de ciphertext y el número de testigos de la DB origen permanecen iguales durante cada Restore. No se carga una DB antigua sobre la fuente viva ni se fabrica un recibo de arranque.
- El arnés informa cuatro clústeres propios parados. Contrasté además ausencia de `postmaster.pid` en el origen de mi ejecución, sus cinco TRX y los tres backups: cabecera custom `PGDMP`, tamaño y SHA256 de cada dump coinciden con su manifiesto. Los dos pines de DLL se mantienen al terminar.

Salidas/binlogs y comprobaciones propias: `.local/f0604-review/independent.private.log`, `pins-and-sources.json`, `final-proof.json`; laboratorio nuevo `.local/labs/f0604-closure-9e7862ee05e94a1290ecb523eef4c6f9`. Ninguna credencial, sobre, dump, clave o ciphertext se incorpora a este dictamen.

## Integridad y atribución

Verifiqué227archivos de producto: coinciden con `FUENTES.json` y con el congelado F-06.03. Las20fuentes/herramientas históricas registradas por F-06.03 conservan sus hashes actuales; las45SQL históricas y el sello de esa evidencia también coinciden. Las dos herramientas Python históricas se ejecutan desde la raíz, no se presume que formen parte del congelado de producto. La clase de prueba nueva coincide exactamente con la compilada en el congelado final.

La DLL nueva tiene pin propio por reconstrucción en otra ruta; no afirmo igualdad binaria con la DLL anterior ni reproducibilidad bit a bit. Ningún cambio de producto, SQL, dependencia, política o permisos se acredita como implementación nueva en este lote.

Los360casos, quince cortes reales y quince reaperturas, dos Restores de transición y tres negativos PG de F-06.03 son **resultados históricos reutilizados**, con dictamen separado y hashes contrastados. No los ejecuté de nuevo aquí. Los resultados de F-06.02 —incluido el rechazo de catálogos desconocidos/parciales y la retirada segura— también se reutilizan con sus límites. El negativo del pin equivocado se leyó en el recibo del coordinador; no lo presento como ejecución mía.

## Observaciones y límites

No quedan hallazgos bloqueantes para el criterio técnico delimitado. «Todos» significa todo el conjunto retenido declarado y verificado en el contrato/escenario, no medios omitidos o desconectados ni una garantía de backups futuros.

La comparación auxiliar de metadatos de backup usa otra conexión; este ensayo es secuencial sin escritores. No demuestra que esa lectura auxiliar comparta snapshot ante concurrencia, aunque censo y dump sí lo comparten. Los sobres de rotación se autentican en memoria; los tres sobres de backup se conservan cifrados en el mismo equipo privado. Eso no demuestra custodia externa física de Wascar.

Restore usa la misma identidad explícita y DPAPI de este equipo, con cuenta/confianza de laboratorio. No prueba adaptación de identidad, portabilidad entre máquinas o token real de servicio. No ejecuté CLI pública rotate, instalación46, servicio/HTTPS/login instalado, reboot de Windows, apagón ni durabilidad universal ante pérdida eléctrica. El resultado interno `verified` sigue siendo conciliación offline, no `service_resumed`/`verified` operativo D2.

## Recomendación de cierre

Conciliar **sólo F-06.04,5/8**, sin sumar pruebas o variantes como puntos nuevos. La evidencia conjunta admite los hitos `technical_tests_same_scope` y `independent_review_same_scope` técnicos. Mantener pendientes definición/implementación del recorrido operativo público, `integrated_current_candidate` y `target_acceptance`. La totalidad operativa F06/R04 y la adopción de Wascar no se cierran.

No he modificado ni recalculado el ledger o el porcentaje. El coordinador registra el crédito conforme al criterio congelado y conserva la distinción entre índice de cierre restante y porcentaje global de producto.
