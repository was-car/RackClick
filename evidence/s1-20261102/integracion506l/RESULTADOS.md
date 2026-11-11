# Punto1 · migración y persistencia del catálogo L ·02.11.2026

**PASS en laboratorio Windows con PostgreSQL17.11 y Edge real.** No es instalación, QA de Wascar ni adopción. Laboratorio y hosts de esta prueba detenidos al terminar; sin VM, servicio instalado, commits o push.

## Resultado y procedencia

- Actualización41→43 ejecutada en el intento03:805 definiciones y799 instancias comerciales anteriores conservadas con inventario, auditoría, operaciones/recibos e historial. Se repite migración sin cambios y se contrastan replay y segunda sesión. El intento03 global fue FAIL posterior en fresh; se conserva íntegro en INTENTO03.json.
- Nueva base43 ejecutada en el intento06:62 modelos/1673 extremos,51 pares adicionales de modelos con puertos, receptor USP28 extremos, cuatro armarios vacíos y sus cuatro duplicados.868 definiciones/revisiones;862 revisiones comerciales/861 claves comerciales distintas. UUID, grupo/ordinal, cara, conector, cotas/BOM y montaje contrastados.
- Conexiones:17 por API y17 más por Click-Click, una de cada tipo presente en L. SmartPower usa el receptor real de revisión explícita. No se afirma haber conectado todas las bocas o cada modelo individualmente.
-45 rechazos de comandos registrados más negativos de permisos de lector/ámbito, alteración de metadata de catálogo, UPDATE/DELETE/TRUNCATE del propietario y ausencia de DDL del runtime. Rollback de auditoría forzado, replay/conflicto, recarga, otra cuenta y reinicio del proceso comprobados.
- Edge inspecciona62 modelos×2caras,1673 UUID y objetivos de al menos24px, sin imágenes de terceros; selector868 acotado, alta GUI de armario, recarga/segunda cuenta/lector. Capturas de viewport: no equivalen a inspección visual exhaustiva de toda la altura de los armarios.

RESULTADOS.json conserva la atribución explícita `upgradeExecutedThisAttempt=false` y el SHA del intento03. Se verificaron los172 inputs/copias de build idénticos, incluidos SQL042/043, y los binarios/frontend; por eso no se repitió el upgrade al corregir sólo el auxiliar de pruebas. Las tres fuentes runtime se fijan aparte: no forman todas parte de esas172 fuentes de compilación. La prueba completa reproducible sigue en `development/server/tests/test_hardware_selected506l.py` con `--dll`, `--baseline-dll`, `--frontend`, `--output` NUEVO bajo.local y `--browser`.

## Correcciones y fallos conservados

1. SQL042 sustituía inventory_port_check(PoE) en lugar de inventory_port_check1(power_role). El intento02 lo detectó creando DC. Rojo focal: DC válido rechazado y PoE sobre SFP aceptado. Verde: DC válido aceptado, rol de energía sobre RJ45 rechazado, PoE sobre SFP rechazado y RJ45-PoE admitido. Sólo se sustituye check1, conservando el control PoE original. Diff y cuatro casos antes/después adjuntos; no se modifica SQL001–041.
2. Intento03 y diagnóstico04: el auxiliar histórico sólo enviaba mountSlotKey si existía padre. La PDU vertical tiene slot propio sin padre. Se corrigió el fixture, conservando la validación de producto; después se crea y se rechaza ocupar dos veces el lateral.
3. Intento05: el fixture esperaba403 al leer otro cliente. `RequireRead` ya establece404/not_found para ocultar existencia. Se alineó la aserción al contrato existente, incluyendo cuerpo y checkpoint inalterado. El lector autorizado sigue recibiendo403 al escribir.
4. Los paréntesis CASE y el despacho nativo L corregidos antes de esta tanda mantienen su evidencia propia.35C# y995Node son resultados previos; no se anuncian repetidos. Se conservan los12 focos Node posteriores del despacho. Build03 sin errores ni advertencias, binlogs privados. No se ejecutó otra regresión completa por cambios sólo de SQL/fixture.

Los intentos fallidos01–05, bases sintéticas detenidas, logs y recibos privados se conservan en.local. No se han eliminado ni convertido sus FAIL en PASS. La revisión independiente está en `evidence/s1-20261101/integracion506l/review/FINAL-20261102.md` y su adenda `ADENDA-FRESH06-20261102.md`: los ensayos PG/API/Edge anteriores son del coordinador; el revisor identifica sus propios focos y límites.

## Límites y siguiente trabajo

Los dibujos son vectores propios basados en referencias, con límites por SKU. Vacíos, BOM fijas, dimensiones desconocidas, Smartoptics1RU nominal, Telco3U conservadoras y variantes parciales siguen declarados. No hay trazado interno óptico/pasivo, matriz Calient, radio, certificación de pinout/carga/fit real ni configurador modular dinámico. Permanecen observaciones menores de legibilidad Core/Atlas.

Selección506/506 definida y con integración de desarrollo contrastada por etapas A–L; no equivale a506 modelos adoptados por Wascar. Siguiente: conciliar una candidata completa con MFA/administración existentes, paquete integral Windows/New/Restore/backup y QA. El laboratorio50 clientes viene tras fijar esa candidata. Índice de cierre restante9,76/100 intacto; no es porcentaje global y no sube por contar pruebas/modelos.
