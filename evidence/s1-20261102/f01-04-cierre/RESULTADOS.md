# F-01.04 · evaluación de cierre

02.11.2026. Coordinador: Codex. Encargo: paso 4, conservar D y reutilizar evidencia antes de implementar. No se necesitó implementar producto.

**Resultado: criterio de cierre no satisfecho; no acreditar F-01.04 ni cerrar F-01.** La evaluación es un resultado documental verificable, no una exención de las condiciones que faltan. La revisión independiente se registra por separado en [REVISION-INDEPENDIENTE.md](REVISION-INDEPENDIENTE.md).

## Criterio y contraste

Literal congelado: «Cada candidato/indeterminado tiene clasificación y resolución verificables; credenciales reales expuestas revocadas/rotadas de forma coordinada; comprobación focal de fuentes/paquete sin exposición.»

| Condición | Evidencia reutilizada | Dictamen y límite |
|---|---|---|
| Clasificación | F-01.01: clasificación saneada y revisión independiente | Satisfecha para los 92 hallazgos históricos seleccionados y 90 metadatos relacionados. No se suman como secretos distintos ni se extiende al resto del historial/archivos privados. |
| Tratamiento de exposición | F-01.02: disposición saneada y revisión independiente | **No satisfecho**: OBS-LOCAL-20261025 sin atribución y OBS-LAB-CHAT no corroborada independientemente; pueden solaparse. «No lo sé» permanece desconocido. No se prueba exposición activa ni vinculación a D. |
| Registro sin supresiones | F-01.03: registro, negativos de contexto y focal del escáner | Satisfecho dentro del conjunto revisado. Sin nuevas excepciones. El focal staged=10/working=0 se reutiliza, no es una ejecución de esta tanda. |
| Fuentes/paquetes relevantes | Windows43 y cargador 02: revisiones previas y pins | Contraste focal favorable, limitado a las fuentes congeladas y bytes de esos paquetes; no demuestra ausencia universal de secretos, ni derechos de redistribución. |

Las referencias completas, hashes actuales de entradas y comprobaciones nuevas figuran en [EVALUACION.json](EVALUACION.json). No se leen valores detectados ni registros privados para preparar esta matriz. Las revisiones anteriores siguen siendo ejecuciones de sus autores, no de este lote.

## Comprobación ejecutada en esta tanda

Windows/PowerShell del anfitrión, Python 3.12 local. Comando reproducible:

```
C:/Python312/python.exe -X utf8 -B evidence/s1-20261102/f01-04-cierre/evaluar-cierre.py
```

- Identidad entre los resúmenes públicos de clasificación, disposición y registro; contadores y observaciones abiertas conservados.
- Configuración Gitleaks, hook, escáner y lock idénticos a F-01.03. Catálogo QA con el mismo SHA256. No se repite el escáner, sus negativos ni las 16 fuentes versionadas de la clasificación.
- **Windows 11**: SHA256 `f090b56e13bc3d4670834746cff33a2d01831eae517dbb0343ce760241c567b0`, 123.473.555 bytes, 140 entradas. Verificador existente sin cambios (`verify`, no `build`): `windows_candidate_verified`, edición 11/esquema 43. Se ejecutó en lectura, sin extraer ni instalar.
- **Cargador 02**: SHA256 `7e743873abbde9ca4ce2eba0846f629024425519adf6c0a4af3ff03201fb62c2`, 1.920.706 bytes, seis entradas; idéntico a su revisión de empaquetado. Esta revisión se reutiliza, no se vuelve a ejecutar su verificador ni se carga Demo50.
- En ambos ZIP, comprobación focal de nombres de las entradas exteriores: no aparecen los nombres privados/extensiones de seguridad declarados por el auxiliar. **No inspecciona contenido de todos los binarios/ZIP anidados.** El escaneo previo de 118 fuentes de Windows43 no se presenta como uno nuevo ni universal.

Las referencias `vmTested:false` del manifiesto de creación de Windows11 no reemplazan el ensayo posterior ya registrado en D. No se cambian esos bytes históricos para actualizar su relato.

## Diferencia observada y ejecución detenida

La primera ejecución del auxiliar se detuvo en la comparación conjunta de controles y referencias Git. Los cuatro archivos de control sí coinciden; la huella de `git for-each-ref` es ahora `b93d16873f7a8fe6abacf2c5ca3b93ca3dcf05e93d5566430a7f07075dd9d2c3`, distinta de `6b6ca60c8da2e6d455be6d8b2df1aa5921c471b931bbff61e2acb760fa703711` conservada en F-01.03. No es una diferencia de CRLF/LF. Se corrigió la afirmación del auxiliar para registrar la diferencia, sin modificar Git ni las evidencias anteriores. Se conserva como límite; no se atribuye causa, autor o reescritura. No se declara historial idéntico ni se amplía a un barrido nuevo. La ejecución posterior termina con comprobaciones PASS y evaluación `closure_not_met`.

## Contabilidad y preservación

Sólo se registrará F-01.04 de pending a in_progress tras la revisión. **Crédito nuevo: 0**. F-01.01/.03 done; F-01.02 in_progress. Índice exacto **1849/168**, redondeado **11,01/100**. Pesos, criterio, huella congelada y denominador intactos. 25 acreditados, 255 sin cierre; se conservan los 268 números del plan.

No hay operaciones sobre D/otras VM, autenticaciones, rotaciones, cuentas, DB/SCM/red/MFA, credenciales o transcripciones. No se cambian archivos de aplicación, paquetes, resultados de Wascar o reglas. No hay commits, push o publicación.

Pendiente concreto: disposición verificable del antecedente del paso 2, seguida de revisión final sobre evidencia pertinente. Sin asumirlo resuelto por una búsqueda negativa o por el desconocimiento del operador. Otros pasos independientes pueden continuar.

## Registro posterior a revisión

La revisión independiente confirma el estado parcial sin crédito. `actualizar-estado.py` se ejecutó con el ledger inicial fijado y comprobó el único cambio F-01.04 pending → in_progress, igual índice exacto y huella de alcance. Resultado en [ESTADO.json](ESTADO.json); copias previas de los cuatro documentos de planificación en `sources/`, sin valores privados.

Regeneración documental secuencial y verificación de cada generador mediante `--check`:

```
C:/Python312/python.exe -X utf8 -B tools/progress_report.py --write
C:/Python312/python.exe -X utf8 -B tools/build_master_roadmap.py --write
C:/Python312/python.exe -X utf8 -B tools/build_remaining_work_plan.py --write
```

La comprobación final se registra en `VERIFICACION-CIERRE.json`: 25 done/251 pending/4 in_progress, 268 números idénticos, peso/criterio intactos y sin cambios en QA/controles/paquetes. Las huellas finales se fijan en `SHA256SUMS.txt`; no se modifica ningún sello histórico para hacerlo coincidir con el estado nuevo.
