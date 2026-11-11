# F-04.04 · dictamen independiente del cierre técnico de F-04

03.11.2026. Revisor `rackclick_security`, distinto de quienes implementaron el proveedor, el escritor y la sonda de permisos. **Favorable al cierre técnico de F-04.04 y del criterio técnico de F-04. Recomiendo acreditar exclusivamente el 5/8 de F-04.04.** No se identificó un hueco bloqueante literal que justifique otro proveedor o repetir ensayos existentes.

Se revisaron el criterio congelado, los tres subpasos anteriores y sus límites antes de decidir. No se editaron producto, ledger, documentos compartidos o evidencias anteriores. No hubo VM/SCM/servicios/DB, lectura de claves o credenciales, binlogs privados, compilaciones o nuevas pruebas de producto por este revisor.

## Criterio y cobertura

> Servicio real lee/descifra y verifica factores; otra cuenta no lee, servicio no escribe ni modifica ACL, management no se amplía; negativos y revisión independiente registrados.

| Obligación | Evidencia suficiente conciliada |
|---|---|
| Custodia antes de componer el proveedor | Decisión confirmada del 25.10 y F-03.02/.03; se conservan claves fuera de PostgreSQL/management, LocalMachine y autoridad SYSTEM/Administradores. Rige gracia45/exención global del 29.10, sin pedir otra confirmación ni volver a MFA inmediato universal. |
| Creación y publicación inicial seguras | F-04.01: escritor actual `76e6dfc3…` pasa descriptor protegido en creación nativa exclusiva, valida antes de publicar y conserva el conjunto completo ante fallo posterior. Rojo 5 fallos/3 controles, verde 8/8, regresión 195/195 y revisión independiente propia. |
| Servicio real lee y descifra | Instalación nativa C10 con init elevado, proveedor Windows DPAPI y cuenta estándar, reforzada por D11. No se sustituye el descifrado por una apertura de archivo o una prueba SQL. |
| Verifica un factor real | C10 confirma enrolamiento y un login nuevo con desafío `verify` por HTTPS; se repite tras reinicio. El intento B con 401 posterior sigue parcial; ensayo C y verificación posterior son los positivos. QA-MFA11 de D también verifica con Windows/DPAPI real y TLS normal, separada del factor personal de Wascar. |
| Otra cuenta no lee; servicio no escribe ni cambia ACL | F-04.02: dos tokens reales y distintos de servicios de E, 30 objetivos por actor; 16 lecturas propias/comunes concedidas, 44 lecturas ajenas/administrativas y 444 solicitudes de modificación denegadas con error 5. Ningún error indeterminado o concesión inesperada. Incluye WRITE_DAC/WRITE_OWNER, DELETE y DELETE_CHILD en padres. |
| Management, padres, herencia y reparse | Misma matriz incluye ambos management y sus 14 nodos, las raíces privadas y los padres comunes. Política/DACL contrastadas; 32 metadatos nativos y 30 hashes PowerShell permanecen iguales antes/después. Los cuatro descriptores distintos entre API se conservan documentados, sin fingir igualdad serializada. |
| Fallos cerrados, sin regeneración ni sesión alternativa | F-04.03 concilia 39 resultados históricos Passed del host, incluidos almacén/versión ausentes sin creación ni listener, y pérdida de activa durante ejecución con 503, sin sesión, factor nuevo o consumo de desafío. Los negativos del lector L2b se reutilizan en su alcance. |
| Revisión independiente registrada | Dictámenes específicos F-04.01/.02/.03, revisión previa y final de la ejecución real de E, y esta revisión del conjunto. Sus autores, ejecuciones y límites están separados. |

La lectura permitida durante gracia o por exención global no se convierte en una supuesta verificación MFA. La política autorizada no es fallback ante pérdida de material cuando el proveedor está habilitado.

## Correspondencia de fuentes y evidencia

Se contrastaron [MATRIZ-CIERRE.md](../MATRIZ-CIERRE.md), [CONCILIACION-EVIDENCIA.json](../CONCILIACION-EVIDENCIA.json), [CONTRASTE-NUCLEO.json](../CONTRASTE-NUCLEO.json) y el diff de Program. El [verificador independiente](Verify-F0404-References.py) terminó con salida 0, antes de modificar el ledger. [COMPROBACION-F0404.json](COMPROBACION-F0404.json) registra 99 referencias verificadas por hash, las fuentes, comandos, crédito recomendado y límites.

- Reader `4cc4203cf338f484eb9ddca253a77b491e7f37f75de97efe1cfbdad328f0f884`, proveedor `c634dd5e8e0272e8abe68842a60ae723bc87c532538fae9a775a10df7a83b3c9`, composición `9990c379ca2704ce7350f58a81f3f9a07c9cea840b3b7b0a9539e417e03de30f` y anillo conservan los hashes de la referencia C10 revisada.
- El núcleo de verificación, enrolamiento, cifrado y autenticación mantiene las cuatro identidades de fuente recogidas en CONTRASTE-NUCLEO. Se comprobó cada hash actual; no se atribuye identidad binaria a una compilación distinta.
- Program completo cambió: la composición/resolución MFA se conserva; el diff añade SQL protegido, recorrido de recuperación por código y mapping de exportación JSON. Su hash actual corresponde al manifiesto publicado45. **No se afirma que toda la DLL actual sea la ensayada en C10**, ni se acreditan por ello los resultados completos de recuperación/exportación.
- El escritor actual coincide con la fuente ya revisada de F-04.01. Sus cambios no se presentan como instalados en D.

Los 39 resultados, 195 pruebas y 504 aperturas son evidencia anterior reutilizada, no nuevas ejecuciones de esta tanda ni nuevos puntos. La revisión no abrió TRX/binlogs privados ni material de seguridad; leyó las conciliaciones públicas y los recibos sanitizados.

## Cierre técnico y entrega, separados

La propuesta de hitos de la matriz es coherente: definición, implementación en fuentes, pruebas técnicas del alcance y revisión independiente quedan cumplidas para F-04. **`integrated_current_candidate` permanece pendiente** para incorporar y ensayar el escritor corregido en una candidata completa. **`target_acceptance` permanece pendiente** como aceptación final de la entrega; custodia ya confirmada y satisfacción de Wascar con MFA administrativo no son PASS de toda la QA.

Por tanto, el cierre técnico usa evidencia compuesta con correspondencia de componentes y contratos. No promete un único instalador nuevo ensayado con todas las correcciones ni obliga a tocar D para producirlo. No cierra recuperación portable, rotación/disco-DB, códigos/emergencia, New/Restore final, backups con MFA o aceptación de producción: mantienen sus resultados F/W/R/E correspondientes.

Persisten los límites de confianza de D2 frente a administrador/SYSTEM o servicio comprometido, durabilidad ante corte y comparación de metadatos frente a igualdad de contenido. No se rebaja el criterio de F-04 para acreditar esas otras propiedades.

## Crédito exclusivo recomendado

Sólo **F-04.04: +5/8 = 0,625**; los tres subpasos anteriores conservan su crédito. Índice propuesto: `2689/168 → 1397/84`, **16,63/100 del cierre restante**. Pesos, IDs, criterio y huella congelada permanecen. No es un porcentaje global nuevo del producto ni adopción de Wascar. El coordinador aplica y concilia ese único cambio tras este dictamen.
