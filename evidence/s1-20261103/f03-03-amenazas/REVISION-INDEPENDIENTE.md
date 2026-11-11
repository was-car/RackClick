# Revisión independiente F-03.03 · Límites de amenaza

03.11.2026 · Revisor: `f0303_review`, distinto del autor. **Dictamen favorable dentro del alcance documental de F-03.03.** No se ha encontrado un hallazgo material bloqueante. No es aprobación de un proveedor, prueba de aislamiento ni aceptación de producción.

Documento revisado: `docs/D2-LIMITES-AMENAZA-F03-03.md`, SHA256 **`b19f3fc02ae7262bb1eee8a2823fd33068e3211dc8723229ebb890b32e420968`**. El dictamen sólo cubre esos bytes; cambios posteriores necesitan contraste de la parte afectada.

## Criterio y comprobaciones de lectura

El texto congelado de F-03.03 pide registrar que DPAPI LocalMachine no aísla del administrador local ni del servicio comprometido. El documento lo declara expresamente y separa:

- Ámbito criptográfico de equipo frente a autorización de lectura por ACL/token Windows; no atribuye aislamiento exclusivo al SID del servicio a LocalMachine.
- Entropía `installationId`/versión como contexto determinista, no contraseña secreta. `MfaKeyRing.EntropyFor` confirma esa derivación.
- Escritor con `CryptProtectLocalMachine=0x4` combinado con `UI_FORBIDDEN`; proveedor que lee claves autorizadas y llama a `CryptUnprotectData` con el contexto correspondiente. La composición productiva conserva confianza SYSTEM/Administradores y lector estándar separado.
- Capacidad de un proceso legítimo de usar material descifrado frente a compromiso de ese proceso. Lectura sola sobre el almacén no elimina la exposición que implica esa capacidad.
- Blob aislado trasladado a otro host frente a imagen/snapshot/volcado completo con potencial estado de plataforma o memoria. No se afirma que copiar la VM sea una custodia externa portable segura por sí misma.
- Cifrado de secretos TOTP frente a todo el contenido SQL; resistencia del sobre a autenticación/corrupción frente a intentos offline con contraseña débil; reenvolver la misma semilla frente a revocar una semilla ya sustraída.
- Borrado de buffers concretos frente a ausencia universal de copias en memoria. No se afirma un ensayo de memoria que no existe.

La gracia45/exención global y la custodia confirmada permanecen; la recuperación restringida y los límites de publicación de F-03.02 se referencian, sin anunciar operadores o ensayos nuevos. Tampoco se afirma un incidente en D ni se reabre F-01 por conjetura.

## Evidencia reutilizada

Se contrastaron por hash lectorL2b, anilloL2d y escritorL2f contra sus manifiestos históricos: **3/3 idénticos**. El detalle está en [CONTRASTE-REVISION.json](CONTRASTE-REVISION.json). Esto permite reutilizar las afirmaciones ya revisadas dentro de su alcance; no representa pruebas ejecutadas hoy ni suma sus cifras.

Fuentes/símbolos consultados: AGENTS/briefing; D2v2 §1/§2, decisión confirmada25.10, política45, F-03.02, criterio/owners/closure del ledger; `WindowsMfaKeyStoreWriter` (flags, llamada Protect), `WindowsMfaKeyProvider` (constructor/GetKey/GetActiveKey/ReadKey/Unprotect), `MfaKeyRing.EntropyFor` y `MfaWindowsHostComposition` (identidad/confianza productiva); revisiónL2b y manifiestos indicados. Se reutiliza la consulta oficial actual de DPAPI/DACL registrada por el coordinador y sus enlaces primarios; este revisor no ejecutó otra navegación o ensayo de Windows.

## Conciliación permitida del cierre

Puede marcarse **sólo F-03.03 pending→done, peso0**, tras registrar el contrato y este dictamen. Con F-03.01/F-03.02 ya documentados, F-03 puede quedar completo como **decisión registrada**. Hitos `definition_confirmed`/`implementation_complete` se refieren aquí a su salida documental, no al código de recuperación.

`target_acceptance` sólo puede conciliarse con la confirmación de custodia de Wascar25.10 ya trazada en F-03.01, dejando explícito que no acredita aceptación operativa del proveedor, producción ni una nueva aprobación general de riesgos. No solicitar de nuevo la custodia ni interpretar que este revisor la decide. No cerrar F-04..F-09/R-04 ni sus pruebas/QA por arrastre.

## Ejecutado y no ejecutado

**Ejecutado:** Git status de lectura, contraste documental y fuente, cálculo SHA256 y comparación de tres componentes. **No ejecutado:** build, pruebas unitarias/PG/HTTP, ataques, DPAPI con claves reales, dumps, lectura de credenciales, autenticación, SCM/tareas, operaciones o borrado de VM, cambios de ACL, instalación, generadores o edición de ledger. No se modificó producto ni el documento del autor, ni hubo commits/push. Las únicas escrituras propias son este dictamen y sus metadatos de revisión.

El paso registra el límite del diseño; no elimina los riesgos descritos. D/E quedan sin operaciones. El índice ponderado permanece2479/168=14,76/100 y no crea un porcentaje global del producto.
