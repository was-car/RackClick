# F-06 · contraste del criterio literal

11.11.2026. Criterio congelado: «Cada punto de interrupción tiene estado recuperable demostrado; todos los factores/backups retenidos siguen descifrables con versiones conservadas y faltantes se rechazan explícitamente».

| Parte del criterio | Evidencia ejecutada y vínculo | Alcance/límite |
|---|---|---|
| Fases y clave anterior al uso | [F0601](../../s1-20261109/f06-01-fases/RESULTADOS.md), protocolo y revisión; [F0603](../../s1-20261110/f06-03-rotacion/RESULTADOS.md) prepara clave, anillo aditivo y sobre antes del commit | Especificación y proceso interno; custodia productiva pendiente |
| Antes/después de cada publicación y commit | [MatrizF0603](../../s1-20261110/f06-03-rotacion/MATRIZ-CAIDAS.json):15cortes reales/15reaperturas y2Restores de transición; [revisión](../../s1-20261110/f06-03-rotacion/REVISION.md) | Reutilizado, no repetido. Proceso Windows, no apagón ni rebootWindows |
| Commit incierto/continuación hacia delante | Mismo trabajador/testigoF0603; pérdida de admisión, colisión y DB anterior rechazadas | No asumir rollback por exit ni activar DB antigua con journal ya completado |
| Todos los estados de factor | [F0603 regresión](../../s1-20261110/f06-03-rotacion/POSTGRES-REGRESION.json), y ensayo nuevo `MfaRotationClosureTests` con pending/active/disabled |3factores sintéticos, identidad/AAD y huellas TOTP privadas; no datos reales |
| Backups retenidos anteriores/posteriores a rotar | [RETENIDOS.json](RETENIDOS.json): catálogo3copias, dos rotaciones y tres Restores reales separados | Todo el conjunto declarado de este escenario, no USB omitidos o futuros |
| Claves conservadas siguen descifrando | En cada Restore se autentican sus3filas con anillo final9 y sobre de su generación recuperado en tienda nueva | Igualdad del secreto, versiones, metadatos y origen conservado; no servicio arrancado |
| Versiones sólo referidas por backup no se retiran | Ensayo nuevo tras rotación9: retiradas1/7/8 devuelven `mfa_retirement_backup_referenced`; claves idénticas conservadas | Retirada lógica bajo coordinador; no destrucción de DPAPI |
| Faltante en material retenido bloquea | Prepare con clave1 ausente, aunque los factores vivos usen9: rechazo sin fence ni cambio DB/anillo; tres destinos rechazan su clave ausente | Objeto propio del fixture se conserva/restituye; no reparación ni degradaciónMFA |
| Catálogo/dump no fiable bloquea | Nuevo dump alterado rechaza Prepare; [F0602](../../s1-20261109/f06-02-retirada/RESULTADOS.md) cubre unknown/legacy/parcial y permisos | No descubre raíces que el operador omita; se mantiene declaración/censo completos |
| Autorización/roles e invariancia | Runtime sóloSELECTtestigo y locks/guard en F0603; producto227archivos idéntico. NuevosRestores no cambian fuente | Nuevoensayo usa owner separado de laboratorio; no pretende ensayo de tokenservicio |
| Revisión distinta del resultado conjunto | Dictamen en `review/DICTAMEN.md`, con ejecuciones propias separadas de las históricas | Sólo tras dictamen favorable procede crédito5/8 |
| Integración/aceptación instaladas | Pendiente: candidata46/CLI, servicioSID, custodia externa, HTTPS/login y QA/adopción | No se cierra por conciliar checkpoints técnicos; D/E conservados |

La cobertura es compuesta y trazada, no un único instalador ensayado ni una nueva repetición de todos los codecs. F-06.04 añade revisión y prueba de la brecha retenida; no vuelve a puntuar F-06.01/.02/.03.
