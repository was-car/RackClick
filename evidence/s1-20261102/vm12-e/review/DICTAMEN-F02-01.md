# Dictamen de alcance · F-02.01

Fecha: 02.11.2026. Revisor independiente `/root/audit_steps_5_7`. Evaluación documental final sin nuevas pruebas, instalaciones o lecturas privadas. Se reutilizan los resultados y comprobaciones ya ejecutados y revisados.

## Decisión

**F-02.01 cumple su criterio literal y puede acreditarse exclusivamente por su peso congelado de `5/8` puntos, es decir0,625 puntos del índice.** No equivale a cerrar F-02, F-02.02, F-02.03 o F-02.04. No modifico su estado en el ledger ni recalculo el global.

Criterio vigente leído en `docs/PLAN-CIERRE-RACKCLICK.json`, tarea F-02, checkpoint F-02.01:

> Diseñar e integrar protección compatible con cuenta/instancia reales y canal mínimo de lectura para el servicio; conservar separación owner/migración/runtime.

La carencia concreta que mantuvo parcial este checkpoint en mi primera revisión —la integración y el positivo bajo la identidad efectiva de servicio en una instancia Windows real— dispone ahora de evidencia suficiente. No hay que exigir para este mismo checkpoint un Restore o un reinicio que pertenecen al ensayo de recuperación y al cierre del resultado completo.

## Contraste de cada parte del criterio

| Parte literal | Evidencia reutilizada | Conclusión |
|---|---|---|
| Diseñar e integrar protección | Contrato RCSQL001/DPAPI, descriptor sin contraseña, rechazo de respaldo en claro al habilitar, publicación y transporte del C# SQL y de los26 operadores. Comprobación independiente de la cadena13,14 y14-r2; mismo bundle `b3f609…` y mismas DLL/operadores de ejecución. | Diseño e integración materializados en la candidata; no sólo en stubs o código suelto. |
| Compatible con cuenta/instancia reales | `service-observed13.json`: instalación13 en E, servicio `Running`/`Auto`, SID ligado al recibo, propietario del proceso coincidente y cuenta no administradora; HTTPS con validación TLS Windows normal, salud `ready`, esquema43. `source-next-actual.json`: instancia3, runtimeRoleMatches, cuatro privados y ausencia de perfiles owner/cluster. | Positivo operativo bajo la cuenta Windows real, junto al consumo de la configuración protegida del circuito ya revisado. No se confunde con el token de laboratorio de las primeras pruebas. |
| Canal mínimo de lectura para el servicio | Lector C# fijo con SID del proceso y confianza productiva, ACL privada, integridad/ruta/identidad y límites, sin propietario/escritura para el lector ni secretos owner/cluster disponibles. El montaje mínimo sólo conserva runtime y backup de alcance limitado; las peticiones privilegiadas se consumen antes del hijo. Revisión de esos controles, pruebas propias aisladas y positivo nativo descrito arriba. | Canal runtime limitado implementado e integrado. No se afirma protección frente a SYSTEM/administradores, compromiso del host o acceso efectivo universal de Windows. |
| Conservar separación owner/migración/runtime | Provisionamiento crea owner/cluster para inicializar/migrar la base nueva y no persiste sus contraseñas en instancia3. Runtime no es owner/superusuario y carece de DDL; sus modos CLI privilegiados se rechazan. Pruebas reales PG17.11 de roles/permisos y manifiesto3; getter real confirma runtime ligado y ausencia de perfiles owner/cluster. Backup usa un rol SQL distinto, de lectura, no owner/runtime. | Se conserva la separación SQL requerida. La cuenta Windows del backup puede coincidir con la del servicio sin contradecir este criterio; no se exige aquí una segunda cuenta Windows que el texto no pide. |

## Qué evidencia cambia el dictamen anterior

- `evidence/s1-20261102/revision-pasos-01-07/REVISION-SQL-INDEPENDIENTE.md` sigue conservado: allí no había positivo con el SID real ni candidata completa de SQL. Su parcial para F-02.01 era correcto con aquella evidencia.
- `cierre-bloqueantes-01-07/sql-revision/REVISION.md` documenta componentes, peticiones efímeras, mínimo de cuatro privados y pruebas propias; dejaba expresamente pendiente la VM. No se reescribe como si ya contuviera ese ensayo.
- El ensayo nativo13 aporta el servicio estándar real y la salud de aplicación. Los fallos posteriores del **visor administrativo** —ACL raíz y perfil MFA2— no eran fallos del canal SQL del servicio en marcha. Ambos tienen corrección, pruebas y revisiones separadas.
- `source-next-actual.json` aporta el getter administrativo completo con las fuentes corregidas, sin cambiar programas/ACL instalados ni imprimir credenciales. Su código es `next_source_private_access_verified`. Es una ejecución del coordinador contra E13, **no un ensayo mío ni una instalación14-r2**.
- `REVISION-PAQUETE14-R2.md` liga las fuentes corregidas y los componentes invariantes al nuevo paquete, sin atribuirle la ejecución completa de13. De14 a14-r2 sólo cambian el visor y su manifiesto; aplicación, bundle y servicehost permanecen idénticos. Eso permite reutilizar la prueba del servicio13 para este componente invariante.

La prueba de preparación directa desde el bundle, `instancia3/BUNDLE-PREPARATION.json`, ya confirmaba formato3, cuatro archivos, cero peticiones protegidas pendientes y26 operadores, pero por sí sola declaraba `actualServiceIdentityTested=false`. **No se usa sola como sustituto del ensayo nativo posterior.**

Los resultados estables de laboratorio `instancia3/pruebas-estables/result.json` registran4/4 PASS, PG real, backup/Restore, dos reanudaciones y rechazos explícitos. Continúan declarando `sameWindowsPrincipal=true` y no sustituyen el Restore Windows que falta. Se reutilizan aquí para la separación de roles y el mecanismo, no para cerrar F-02.03.

## Atribución y pruebas

En esta última evaluación **no ejecuté ninguna prueba nueva**. Leí el criterio congelado, los recibos públicos sanitizados, los contratos y mis dictámenes anteriores. Las pruebas propias de componentes y de integridad/delta ya constan con comandos y hashes en esos informes. El servicio/backup/getter en E son ejecuciones del coordinador, claramente separadas de las mías.

No he operado VM, servicios, cuentas, tareas, DB, red o certificados. No he leído secretos, factores, contraseñas, transcripciones o credenciales reales. No he cambiado código, programas instalados, ACL, informes anteriores, ledger, QA o pesos.

## Qué no se acredita

- F-02.02: operación final de fichas/diagnóstico/backup y su criterio propio; sus evidencias existentes se conservan sin cerrar ese checkpoint por arrastre.
- F-02.03: Restore nativo14-r2 a destino/identidades nuevos y reanudación/postboot pendientes. `bootChanged=false` en el recibo observado; la pregunta de reinicio a Wascar sigue abierta.
- F-02.04 y cierre global F-02: la condición completa incluye la recuperación y la revisión/aceptación que corresponda. No se cumplen automáticamente al acreditar F-02.01.
- D no se migra ni se adopta esta candidata en su lugar. El antecedente F01 y sus decisiones se mantienen separados.

**Recomendación contable al coordinador:** registrar F-02.01 como cumplido, enlazar este dictamen y las evidencias nativas/invariantes, y añadir únicamente `5/8` puntos una sola vez. Mantener los otros checkpoints con su estado real y explicar el cambio de evidencia respecto al parcial previo; no alterar los pesos ni dar por finalizado el resultado F-02.
