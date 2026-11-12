# F-09.03 · revocación, auditoría y último administrador

11.11.2026. Cerrado técnicamente con dictamen independiente favorable sólo a F-09.03. **D/E preservadas**, sin VM, cuentas/servicios Windows, instalación, commits o push. Sólo bases/roles/cuentas app sintéticos nuevos.

## Reutilización antes de implementar

[Plan previo](../../../docs/PLAN-F0903-REVOCACION-AUDITORIA-MFA.md). Contrastados fuente/sello232archivos y dictamen del [paso30](../f09-02-material-perdida/RESULTADOS.md), D2§2.2/§4.1, F08 y las guardas actuales. Se reutilizan loss-reset, revocación y witness de SQL047. La auditoría local dedicada satisface el contrato; no hace falta otra migración ni un appactor inventado para audit_event. El resultado del witness es el commit de la transición DB, no recuperación de servicio/usuario.

Fuentes oficiales consultadas: [transacciones PG17](https://www.postgresql.org/docs/17/tutorial-transactions.html), [bloqueos](https://www.postgresql.org/docs/17/explicit-locking.html) y [triggers/retornoNULL](https://www.postgresql.org/docs/17/plpgsql-trigger.html). Se adapta el código existente; sin dependencias, versiones o algoritmos nuevos.

## Hallazgo y corrección acotada

Un resultado SQL exitoso puede haber suprimido una fila. La referencia validaba plenamente el witness en reentrada/Publish, pero no la primera aplicación antes del commit. Nueve negativos con triggers sintéticos demostraron commit indebido ante archivo, pending, retirada de factor/sesión, consumo de desafío/código o escritura del witness suprimidos, incluido cero factores y una autoridad alterada.

**Sólo cambia `MfaLossResetDatabase.cs`:** recuentos de archivo/pending iguales al plan, UPDATE final del witness de exactamente una fila y relectura/validación completa del witness fresh y sus hashes antes de retornar al coordinador que hará COMMIT. Cualquier discrepancia provoca rollback. No se diagnostican esos triggers como presentes en el producto instalado ni se pretende resistencia a un propietario PostgreSQL hostil arbitrario.

231 de232fuentes anteriores conservadas; ningún archivo de producto nuevo. SQL001–047, Program, coordinador Windows, CLI, lectores/escritores, política/gracia45, frontend, dependencias y pruebas históricas intactos. Un archivo nuevo de pruebas reutiliza el fixture F0902 sin modificarlo.

## Verificación

Windows, SDK10.0.401 Release, PG17.11 nativo nuevo, owner/runtime separados, DPAPI/ACL reales con SID/trust de fixture. Logs, binlogs, TRX y credenciales técnicas del laboratorio privados e ignorados por Git; cada invocación MSBuild conserva binlog único. No se guardan sobres ni contraseñas de custodia MFA.

| Ejecución | Resultado |
|---|---|
| Primer rojo |14casos:4PASS/10FAIL. Nueve fallos pertinentes por ausencia del rechazo; uno era preparación incompleta del fixture |
| Rojo limpio antes de producto |14casos:5PASS/9FAIL, todos los9 con `No exception was thrown` en las supresiones/corrupción previstas |
| Verde |14/14 PASS,0omitidas, tras corrección mínima |
| Build definitivo |0errores/0advertencias, restorelocked; sin nuevas dependencias |
| Regresión definitiva |52/52 PASS,0FAIL/0omitidas, mismos binarios del verde:14nuevos +30F0902 +5último administrador F08 +3HTTP |

El error inicial del fixture era un factor marcado active pero sin confirmed_at. La generación de códigos lo rechazó correctamente con mfa_active_factor_required. Se completó sólo el fixture y se repitió el rojo antes de tocar producto. No se relajó el control real. La identidad del build de referencia es de fuentes; no se afirma igualdad binaria entre rutas de compilación diferentes.

Los nueve rojos limpios usan el mismo archivo final de pruebas y la fuente de producto anterior exacta. Constituyen la sensibilidad pertinente; no se hizo otra mutación redundante. Los fallos inducidos son en DB nuevas y no cambios sobre D/E.

## Qué se contrastó realmente

- Auditoría de19campos cerrados con UUID, autoridad/SID Windows, instalación/DB/Systemhaus, versiones, hashes, conteos y fecha. Sin claves, semilla, contraseña, sesión, valores de códigos, ciphertext o actor app inventado. El archivo cifrado permanece separado. Reentrada por el mismo UUID no duplica el registro ni repite revisiones.
- Retirada de4sesiones, consumo de8desafíos pendientes (ambas finalidades e incluidos expirados) y4códigos en el escenario mixto; desafíos ya consumidos conservan su timestamp. La cuenta no afectada conserva exactamente sus objetos de seguridad. Usuarios, permisos, gracia e inventario sintético permanecen iguales.
- Uso real de sesión antigua y llamadas con desafíos verify/enroll anteriores rechazados; código real previamente generado no canjeable con su desafío anterior. Contraseña incorrecta no da acceso; contraseña correcta sólo entrega enroll sin sesión.
- Un único global activo conserva capacidades y cuenta tras pérdida. Login, start e intento de código inválido no devuelven sesión administrativa. Sólo TOTP nuevo sobre clave activa8 emite sesión/CSRF nuevos, permite leer usuarios y conserva la exención global ordinaria al terminar. La guarda last_admin_required sigue rechazando su desactivación.
- Fallos inducidos de INSERT/UPDATE de auditoría, las nueve supresiones/corrupciones y caso cero factores: todo el cambio DB revierte, sin witness/archivo parcial, conservando candidato/fence para conciliación.

No hay listener ni servicio reanudado en ese recorrido; las llamadas son a componentes con rol runtime PG restringido. Los3HTTP son fronteras históricas de API restringida y ausencia de emergencia remota, repetidas sobre el build nuevo; no recuperación del host perdido por HTTP.

## Reproducción y límites

Driver privado `.local/f0903-79ddc76e/run.py`: `red --restore --build`, `red-clean --build`, `green --build`, `final --filter <frontera afectada>`. Build con `--no-incremental`; final usa `--no-build --no-restore`. Lab nuevo explícito por corrida, variables de fixture y cierre en finally. `FOCOS.json` fija nombres, counters, hashes de TRX privado y DLL; `FUENTES.json` y `CAMBIOS.patch` fijan fuentes/diff y evidencia previa conservada.

[Matriz](MATRIZ-CRITERIO.md) · [ficha31](../../../docs/PASO-031-REVOCACION-Y-AUDITORIA-MFA.md). Positivos elevados/SYSTEM, SID real del servicio, custodia externa física, arranque/guarda/CLI de pérdida, liberación del fence, HTTPS e instalación quedan para F0904/.05. El fence sigue presente y la CLI sigue sin transición operativa. No hay nuevos resultados personales ni casos GUI habilitados;175casos QA se conservan. La observación Edge del paso28 sigue abierta. No aceptación de Wascar ni porcentaje global nuevo.


## Revisión y conciliación

[Dictamen independiente](review/DICTAMEN.md):15/15 propias (14nuevas +1rollback previo), sin omitidas y sin recompilar, sobre pines finales. El primer intento15FAIL fue un error de longitud de ruta del harness; ambos clusters se detuvieron y la repetición sólo acortó la raíz privada, sin cambiar producto/bins. Sólo F-09.03 suma1/2:2153/84→2195/84=26,130952…/100 del cierre restante. F0904/.05 y seis hitos completos siguen pendientes, sin atribuir servicio recuperado ni aceptación.
