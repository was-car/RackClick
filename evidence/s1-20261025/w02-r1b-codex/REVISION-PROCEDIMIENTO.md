# W-02 · Ronda R1b · procedimiento y batería

25.10.2026. Revisión independiente de lectura por Codex, distinta de la implementación de Claude. Alcance exclusivo: procedimiento §5.5, generador/batería de focos y precisión de sus límites. **No ejecuté pruebas, generador, batería, VerifyOnly oficial, INICIAR, instalador, SQL, servicios, QA ni VM.** Sólo se escribe este informe; las fuentes y evidencias de Claude se conservan. El coordinador revisa el bloqueo del ejecutor y reproduce sus focos por separado.

**Dictamen: sin defecto material nuevo en este alcance.** La instrucción de reapertura y los defectos de agregación identificados en la ronda anterior están corregidos por lectura. La aprobación de esta preparación no acredita el recorrido real: **W-02 mantiene 0,00/2,50 puntos** hasta su evidencia en VM.

## Procedimiento de reinicio

`docs/PROCEDIMIENTO-W02-NEW-RESTORE-07.md:153–160` indica abrir el acceso `RackClick-VERIFICAR-05-<8 caracteres>.cmd` creado por **esta ejecución 07**, que abre `Show-RackClickInstalledServer.ps1 -VerifyInstallation` con elevación. Prohíbe volver a Execute/INICIAR/limpieza y ordena parar si falta el acceso o no aparece una instalación. Corrige el riesgo operativo que señalaba la revisión anterior, sin modificar el envoltorio congelado.

El `05` se identifica correctamente como etiqueta histórica H3; no remite a un paquete antiguo. El panel puede iniciar la comprobación al abrir con `-VerifyInstallation`; pulsar el botón permite verificarla desde ese mismo panel. El estado `awaiting_reboot`/exit 3 continúa siendo una preparación pendiente de comprobar el nuevo arranque, no prueba de instalación terminada ni necesariamente de un fallo de prerrequisito.

## Batería y generador

- `ejecutar-focos.sh:22–29` acumula discrepancias de códigos en `fallos`. Las estáticas conservan el exit de Python antes de resumir su texto (`:49–51`). También se acumulan el informe R2 no sustituido por fail, la creación de junction fallida y los controles del simulador. `:130–135` devuelve 1 si hay fallos, en vez de heredar el éxito del último cat.
- La comprobación de no lanzamiento se hace al final de los casos: cuenta los directorios W inspeccionados y sus marcadores, falla si detecta lanzamientos o no hay casos y escribe NO_LANZADO sólo en la rama sin hallazgos. Los casos simulados se distinguen de ese barrido de los seis envoltorios oficiales.
- `W02_FOCOS_NEGATIVO=1` prepara intencionadamente un código esperado incorrecto y un marcador de lanzamiento. Por lectura ambas condiciones suman fallo y llevan a exit 1. No lo he ejecutado; el ensayo negativo comunicado es de Claude.
- Cada corrida usa nombre nuevo por fecha/pid; `generar-focos.py:20–25` rechaza una salida existente. Las variantes copian INICIAR/PAQUETE y comparten sólo el payload inalterado mediante hardlink. No se sobrescriben los paquetes congelados.
- `generar-focos.py:33–49` exige anclas únicas y crea copias instrumentadas explícitas: quita exclusión/compuerta necesarias, introduce la parada previa al lanzamiento o sustituye únicamente la entrada por `sim/sim.ps1`. No modifica el ejecutor del repositorio para alcanzar esos caminos.

## Qué acredita la simulación, y qué queda fuera

El simulador generado (`generar-focos.py:53–71`) ejecuta un proceso PowerShell de prueba que obtiene el digest de INICIAR en ambas llamadas. Con ataque intenta escribir, renombrar, borrar el archivo y mover su carpeta. La batería exige los cuatro rechazos y los dos hashes autorizados, con un control separado sin ataque. No ejecuta el contenido del INICIAR que está leyendo.

Los catch del simulador etiquetan cualquier excepción como «bloqueado»: prueban que las operaciones fallan, **no identifican por HResult su causa concreta**. La revisión del código de bloqueo y los focos independientes del coordinador completan esa atribución; no se presenta aquí como cuatro pruebas propias de una causa específica.

Leí el resultado publicado que termina BATERIA_OK y registra hashes coincidentes. La atribución sigue siendo a Claude. Su informe distingue expresamente el lanzador simulado y reconoce que **no ha probado que el INICIAR real pueda leer los archivos retenidos**, ni el VerifyOnly oficial ni la instalación. Es un límite correcto y relevante para el siguiente ensayo, sin confundirlo con un fallo demostrado. Las 21 estáticas y 24 comprobaciones comunicadas no se reclasifican como instalación ni como ejecuciones de este revisor.

## Huellas recibidas

| Archivo | SHA256 |
|---|---|
| `tools/windows/w02/Invoke-W02TrialPlan.ps1` | `28c0b0c0309aab59b54e36aa0cbc14a0ab1667f0a3ebaeeb6da1246cb3749999` |
| `tools/tests/test_w02_trial_plan.py` | `c89fe7265ed47924558ed1c5f0422347cafd963cbf7619474e1fe0d70f6d0f33` |
| `docs/PROCEDIMIENTO-W02-NEW-RESTORE-07.md` | `c7eaaa156aaef2831edc01015535524e6bd9ac81de92cd9883637f30a0305c6d` |
| `focos/generar-focos.py` | `5a94825de08d5f0e8cbc2c7df9b61357256762b085626378bf222817c4bac547` |
| `focos/ejecutar-focos.sh` | `bcc672d99d96561541dc4a9bd9435790714efa38e62046922beae3feca72a918` |

La revisión no cierra W-02 ni acredita SCM/reboot Windows/Restore. No altera el plan de cierre ni estima un porcentaje global del producto.
