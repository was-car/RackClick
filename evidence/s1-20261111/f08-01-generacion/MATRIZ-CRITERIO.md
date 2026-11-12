# F-08.01 · matriz de comprobación

11.11.2026. Literal congelado: «Generar y mostrar una sola vez códigos por usuario; almacenar sólo hashes con sal conforme D2, sin dependencia de clave TOTP».

| Parte | Fuente y evidencia | Alcance/límite |
|---|---|---|
| Diez códigos propios impredecibles | MfaRecoveryCodeCodec.NewCode,16bytesCSPRNG; generación propia entrega10; [FOCO.json](FOCO.json) |128bits por construcción; no auditoría del generador del sistema operativo |
| Sal y hash ligados al usuario | Hash/Matches, formato rck1 y dominio+Systemhaus+usuario;9casos codec | Sal128bits, SHA256, comparación constante de hashes; no derivación de contraseña humana |
| Sin dependencia criptográfica de clave TOTP | Codec sin referencia a IMfaKeyProvider/semilla; generación no descifra factor; pruebas existentes y foco nuevo | Requiere autoridad MFA previa; no asegura arranque de host con almacén perdido |
| Valores sólo en primera respuesta | GenerateOwnRecoveryCodes devuelve valores después del commit; status/receipt/replay nunca los devuelven |«Una vez» es entrega por operación, no número de lecturas/descargas de memoria del usuario |
| Entrega única incluso solicitudes solapadas | Nuevo TheSameConcurrentGenerationDisclosesTenCodesInOnlyOneResponse:2PIDbloqueados, una entrega;10hashes/1operation/1audit | Generación en almacén; el HTTP propio se prueba aparte con replay secuencial |
| DB/auditoría/recibos sin claro | SnapshotAll y búsquedas de valor en operation; transacción guarda hash/metadatos y rollback de auditoría | Datos sintéticos; no análisis físico de todo proceso/memoria/archivo del usuario |
| Sólo usuario autorizado | Focos PG y OwnGenerationKeepsOriginCsrfActorPasswordAndCodeFreeReplayGuards; otro actor/intención/MFA/password/revisión | No generación ni visualización de códigos ajenos por administrador |
| Panel/journal/EN-DE-ES | [punto3/Edge](../../s1-20261102/punto3/MFA-EDGE.json), [revisión](../../s1-20261102/punto3/review/REVISION.md), identidad de fuente y10Node nuevos | Edge histórico reutilizado, no otra sesión de navegador |
| Revisión independiente actual | review/DICTAMEN.md, con ejecuciones propias y pines | SóloF0801, no canje/reenrolamiento/último administrador |
| Timing D2 y custodia | D2 histórico vs [procedimiento público](../../../docs/PUNTO3-FUNCIONES-PENDIENTES.md) | Generación explícita posterior; no automática al confirmar, sin custodia instalada/aceptación nuevas |

El plan numerado ya registra la implementación revisada y ordena conciliarla. Esta matriz no cambia el texto/peso, no convierte el cierre parcial en aceptación integral D2 y no acredita los pasos25–28 o F08completo.
