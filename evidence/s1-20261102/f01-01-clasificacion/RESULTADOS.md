# Paso 1 · F-01.01 terminado

02.11.2026, Windows del anfitrión, Python 3.12 y Gitleaks 8.30.1 fijado existente. Wascar pidió clasificar candidatos/indeterminados reutilizando evidencia y conservar D. **No se operaron D, ninguna VM, servicios, DB, cuentas o factores MFA.**

## Resultado de clasificación

| Conjunto | Hashes de archivos verificados | Identificadores sin uso de autenticación | Narración técnica | Sin resolver |
|---|---:|---:|---:|---:|
| Históricos: 23 candidatos y 69 indeterminados | 80 | 3 | 9 | 0 |
| Metadatos working del mismo barrido, corroborados en Git | 80 | 3 | 7 | 0 |

**No se identificaron credenciales reales dentro de estos hallazgos.** Las 92 y 90 entradas se solapan: no son 182 secretos ni 182 casos distintos. La corroboración working tiene referencias versionadas a las líneas correspondientes, pero no reconstruye el snapshot completo original, que el barrido antiguo no conservó.

Se revisaron 15 rutas del conjunto histórico. Los 80 digest se contrastaron con los bytes de 16 fuentes versionadas y su uso como comprobaciones de integridad. Los tres identificadores se vincularon a nombres de diario/carpeta y a su uso; no se descartaron sólo por tener forma UUID/HEX. Las nueve narraciones son tres frases, incluidas sus copias en parches.

[Resumen público sin valores](CLASIFICACION-SANEADA.json) · [Investigación previa](INVESTIGACION-PREVIA.md) · [Revisión independiente favorable](REVISION-INDEPENDIENTE.md).

## Trazabilidad privada

El informe final anterior se seleccionó por coincidencia de recuentos/categorías y SHA256; no se mezcló con dos intentos previos de clasificación distinta. Las trazas nuevas recuperan commit de detección, versión de fuente, ruta, línea, columna y SHA256 del blob. Cada entrada tiene clasificación y razón de resolución. Los valores detectados no se guardan ni siquiera en el informe de clasificación privado.

Los informes de detalle se conservan en el directorio privado propio señalado por `.local/security/f01-01-current.json`, ignorado y sin seguimiento Git. El JSON público sólo contiene recuentos, razones generales y huellas de informes, no rutas/commits de hallazgos ni valores. Los informes históricos originales se conservaron.

## Ejecución y controles

Se verificó y reutilizó el Gitleaks fijado; no se instaló ni actualizó ninguna herramienta. Se repitió **sólo el historial de las 15 rutas seleccionadas**, no un barrido completo del repositorio. El auxiliar captura toda salida del hijo y usa redacción completa. No se ejecutó contenido de Git.

```powershell
C:/Python312/python.exe -X utf8 -B evidence/s1-20261102/f01-01-clasificacion/recuperar-trazas.py
C:/Python312/python.exe -X utf8 -B evidence/s1-20261102/f01-01-clasificacion/clasificar.py --write
C:/Python312/python.exe -X utf8 -B evidence/s1-20261102/f01-01-clasificacion/verificar-negativos.py
```

[Cuatro negativos en memoria](NEGATIVOS.json), todos PASS: digest alterado, identificador no vinculado al diario, uso adicional del símbolo de carpeta y frase no revisada se rechazan. Se comprueba primero un caso válido; no hay valores en stdout ni cambios de archivos fuente. No son pruebas de producto o autenticación.

El revisor independiente contrastó directamente el conjunto, los blobs, su uso y la ausencia de valores en los informes. No ejecutó Gitleaks ni los negativos del coordinador; sus límites están en el dictamen.

Los tres generadores (`progress_report.py`, `build_master_roadmap.py` y `build_remaining_work_plan.py`) se regeneraron y comprobaron con `--check`. [Control focal del cierre real](VERIFICACION-CIERRE.json): 268 pares número/ID conservados, sólo el botón F-01.01 desactivado, índice 10,38 y conteos 24/256 correctos en HTML/JSON. Es una lectura estructural del documento, no otra prueba de navegador o del producto. La revisión independiente también comprobó el delta del ledger y el peso fijo.

## Incidencias del auxiliar conservadas

- La primera inspección eligió un informe previo con 3.162 hints candidatos/indeterminados, no el final de 92. Se corrigió la selección mediante recuentos y huella; no se clasificaron esos 3.162 ni se sumaron al alcance. La salida contenía sólo metadatos, no secretos.
- Una lectura de metadatos previa carecía de `classificationHint`; el intento incompleto no cuenta como clasificación.
- El auxiliar inicial podía señalar una línea equivocada por `splitlines()` en logs CRCRLF. La resolución estricta se detuvo en la entrada 38. Se cambió a conteo por LF y se verificó la coincidencia redactada en la versión Git exacta. Los intentos privados incompletos se conservan; sólo las trazas finales se usan.
- Un comando de inspección fue rechazado por sintaxis de PowerShell antes de ejecutarse. La inspección se trasladó a un archivo Python propio.
- La primera lectura del mapa inline trató como JSON toda la línea JavaScript; había código después del objeto. Se acotó con `JSONDecoder.raw_decode`. No se ejecutó el JavaScript ni se cambió código de producto.

## Crédito y límites

Se acredita **F-01.01 = 5/8 = 0,625 puntos**: índice del cierre pendiente **9,755952 → 10,380952/100**, redondeado **9,76 → 10,38/100**. El denominador, los pesos, los IDs y la huella de alcance congelada no cambian. Se conserva el ledger anterior en `sources/` y el contraste en `ACREDITACION.json`.

Los 268 números del plan se mantienen: el paso 1 aparece cerrado; quedan 256 subpasos del ledger sin cierre y 24 acreditados. Los 7 cierres de catálogo, 3 iniciativas posteriores y 1 proceso de repositorio no reciben peso adicional.

**F-01 completo sigue abierto.** F-01.02 (tratamiento de credenciales reales), F-01.03 (criterio/registro de falsos positivos) y F-01.04 (comprobación final de higiene) no se acreditan por esta tanda. Tampoco se verificaron las otras categorías de hallazgos, todos los archivos actuales/untracked, privados ajenos, archivos comprimidos o historial inaccesible. No se declara el repositorio limpio.

Sin rotación, revocación, supresiones, cambios de reglas/hook, reescritura de historial, commits, push, publicación, paquete o QA manual. Próximo paso numerado disponible: **2 (F-01.02)**; cualquier operación que afecte una instalación seguirá necesitando atribución y coordinación, no se hace por este informe.
