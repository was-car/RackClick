# MFA-L1 · revisión y autorización de host HTTP

25.10.2026. Implementación: Claude; coordinación/inspección: Codex; revisión de seguridad independiente: mfa_l1_security_review. Agente explorer mfa_l1_di_plan inspeccionó únicamente composición/configuración/CLI. Ningún revisor modificó código de producto.

`referencia-entregada/` y `HASHES-REVISADOS.json` conservan exactamente las cuatro fuentes de producto leídas y los hashes iniciales del proyecto/lock de pruebas. La entrega original de Claude queda intacta en su carpeta; los70PASS/1omitida y nueve tests son resultados atribuidos a Claude, no repetidos por Codex.

`REVISION-SEGURIDAD.md`: nueve comprobaciones propias de fuente/predicado, cuatro P2 y negativos que deben reproducirse y corregirse. No prueba C#/HTTP/PG. El posible vencimiento durante upgrade de lock es análisis de código/semántica PG, no reproducción. No se afirma una escalada de privilegios por el consumo cruzado de desafíos.

Decisión A: autorizar versión exacta Microsoft.AspNetCore.Mvc.Testing10.0.12 sólo en pruebas, con lock y PrivateAssets=all; fuente NuGet oficial verificada. Resolver proveedor desde app.Services después de Build, sin ServiceProvider duplicado ni registro normal del proveedor sintético; preservar CLI y comprobar configuración efectiva. No habilitar MFA normal/QA.

Mensaje operativo: docs/MENSAJE-PARA-CLAUDE-MFA-L1-HTTP-25-10-2026.md. Dictamen: docs/REVISION-MFA-L1-CODEX-25-10-2026.md. El implementador mantiene responsabilidad de añadir dependencia, resolver composición y completar los negativos/positivo/rollback/auditoría; Codex no edita los cambios que revisará.

Sólo lectura de código/documentación/evidencia pública, consulta de fuentes oficiales y escritura de documentos/metadatos. Sin build, restore, instalación, HTTP/PG/VM/QA nuevos por Codex. No secretos inspeccionados, claves generadas, paquetes modificados, commits o push. No cerrar MFA-L1 ni incrementar crédito todavía: pendiente6,21/100 y global sin recalcular.

Verificación final: métrica validada sin crédito nuevo y Codebase Memory refrescado con941archivos curados. Gitleaks8.30.1 detectó un candidato en la línea5 de HASHES-REVISADOS.json; se clasificó como falso positivo al verificar que su valor es exactamente el SHA256 de Authentication.cs preservado. Cero secretos confirmados en este conjunto; no se añadió supresión ni se afirma historial limpio. Informe completo privado.
