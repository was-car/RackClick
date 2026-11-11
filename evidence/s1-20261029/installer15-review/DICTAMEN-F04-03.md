# Dictamen independiente — F-04.03 y ensayo10

29.10.2026. Alcance: conciliar recibos sanitizados y código/pruebas existentes, sin operar la VM ni volver a ejecutar suites. No se modificaron producto ni ledger.

**Propongo acreditar únicamente F-04.03:5/8de punto, es decir0,625.** Su criterio es conectar el proveedor real tras D2 y rechazar claves/versiones ausentes sin regeneración ni fallback a contraseña. No se acredita F-04 completo ni sus otros subpasos por este dictamen. El coordinador registra el crédito tras conciliar el ledger; no se deduce un porcentaje global del producto.

## Evidencia suficiente para este subpaso

1. D2 consta confirmada por Wascar el25.10.2026 en la cabecera de `docs/DECISION-D2-CUSTODIA-CLAVE-TOTP.md` y en `docs/DECISIONES-MFA-CONFIRMADAS-25-10-2026.md`. La decisión posterior45días/exención no sustituye esa custodia.
2. La candidata10 y el bundle/distribución15 quedaron ligados por hashes en las adendas previas. El vínculo del ensayo identifica wrapper10, esquema15, cuenta estándar y estado anterior al reinicio. `trial-status.json` registra exit observado3 y `awaiting_reboot`, **no éxito final postboot**. El init registra `setup_mfa_store_created`, sin residuos ni claves divulgadas. El requisito CRT consta instalado/verificado en el recibo del coordinador; este revisor no lo instaló ni midió en el invitado.
3. Inspeccioné las aserciones del harness B: liga el recibo al UUID/esquema, el servicio en marcha a su SID, consulta disponibilidad y política real, enrola una cuenta sintética y comprueba factor activo y sesión MFA. El recibo B conserva el fallo401 posterior: **no se cuenta como flujo completo PASS**. Acredita sus pasos alcanzados, incluido confirm200 y sesión verificada.
4. El harness C conserva la misma aplicación, usa una sesión nueva, exige desafío `verify`, recibe200 en la verificación y comprueba `sessionMfaVerified`, factor activo y proveedor disponible antes de logout204. Su recibo pasa; no desactiva validación TLS. Revisé el ajuste del cliente Framework: copia sólo el desafío emitido por el servidor, validando nombre, Path y atributos Secure/HttpOnly/SameSite=Strict. Sustituir también una cookie previa evita reutilizar la obsoleta del fixture B; no cambia servidor ni autoridad concedida. **Es prueba HTTP, no prueba visual del navegador ni escaneo físico del QR.**
5. Concilié7fuentes actuales con la copia congelada de la que procede la publicación. Composición Windows, proveedor, lector y anillo conservan además sus hashes de L2I-01. `Program.cs` actual coincide con su copia compilada: resuelve la composición/proveedor antes del listener y termina con código1 ante error de composición; no crea almacenes ni usa un proveedor alternativo en esa rama. La activación de política se hace después del preflight y tampoco abre listener si falla.
6. Leí el TRX final de29.10 de la copia congelada: **39resultados `MfaWindowsHost*` Passed**, incluidos proceso con almacén ausente sin creación/listener, versión1y7ausentes sin regeneración, raíz inválida y pérdida de clave activa durante ejecución. En este último, el HTTP devuelve503 sin sesión, factor ni consumo del desafío. Son resultados existentes conciliados, **no39pruebas nuevas ejecutadas por este revisor**. Las pruebas y sus límites de identidad de laboratorio se conservan; el positivo actual del servicio estándar aporta el tramo real que faltaba.

`F04-03-EVIDENCIA-CONCILIADA.json` registra hashes de las7fuentes,7recibos y TRX, nombres/resultados revisados y la propuesta exacta de crédito. No incluye secretos, cookies, códigos ni datos del autenticador. No abrí archivos privados de credenciales/material MFA.

## Texto propuesto para `F-04.current`

> Proveedor Windows DPAPI integrado mediante configuración explícita en la candidata10/esquema15. El servicio estándar de C completó enrolamiento y un nuevo login con segundo factor por HTTPS; se concilian negativos de arranque y claves/versiones ausentes sin regeneración ni sesión alternativa. F-04.03 verificado en este alcance. Siguen pendientes los controles completos de ACL con otros tokens/escritura del servicio y el cierre integral de F-04; reinicio de la instalación y adopción no acreditados todavía.

La frase anterior «Program.cs fija proveedor null; no existe proveedor productivo demostrado» es histórica y ya no describe este estado. Corregirla no obliga a marcar terminada toda la tarea.

## Lo que permanece pendiente

- **F-04.01:** no se emite un dictamen de crédito para este subpaso. El resultado completo de ACL desde creación y publicación del almacén requiere su conciliación particular; un init exitoso por sí solo no sustituye ese análisis.
- **F-04.02:** lectura del servicio demostrada, pero faltan los negativos completos bajo otro token y la comprobación de ausencia de escritura/WRITE_DAC efectivo del servicio, además del alcance de padres/herencia/reparse. El código y los fixtures no sustituyen todo ese criterio real.
- **F-04.04 / cierre F-04:** no se acredita el criterio completo ni su aceptación. La revisión de este subpaso tiene alcance distinto.
- Reinicio manual y `postboot_verified`, QA visual de Wascar, recuperación portable operativa, códigos/emergencia y Restore con factores MFA siguen sus tareas propias. Los recibos de esta prueba no cierran esos requisitos.
- Los permisos de gracia45/exención global son política autorizada; no constituyen fallback ante pérdida de claves. Esta revisión no transforma un login permitido por esa política en una supuesta verificación MFA.

Cero operacionesVM por el revisor. Ninguna alteración de servicios, cuentas, claves, QA, política ni datos del ensayo. Las dos cuentas sintéticas y el MFA del bootstrap se describen como hechos del coordinador; no se verificó su inventario por una consulta nueva al invitado.
