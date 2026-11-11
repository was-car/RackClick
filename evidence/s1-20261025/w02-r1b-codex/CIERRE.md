# W-02 · revisión R1b · Codex

25.10.2026, Windows/LEAO. Implementación recibida de Claude; revisión de Codex y lectura distinta acotada del procedimiento. [Dictamen](../../../docs/REVISION-W02-R1B-CODEX.md), [mensaje listo para Claude](../../../docs/MENSAJE-PARA-CLAUDE-W02-R1B-25-10-2026.md), [segunda lectura](REVISION-PROCEDIMIENTO.md).

**Las tres correcciones pedidas quedan conformes para el alcance ensayado. W-02 no está ejecutado en VM y conserva crédito0/2,50.** Sin instalación, INICIAR/VerifyOnly reales, servicios, cuentas, SQL, red, QA/VM, commits o publicación. No se editó código ni evidencia de Claude; no se reconstruyeron paquetes.

## Ejecuciones propias nuevas

| Comprobación | Resultado |
|---|---|
| Pruebas estáticas del helper | 21/21 OK, exit0; repetidas dentro de la batería, no contadas como otras21. |
| Primera batería Bash | FAIL/exit1, 23 discrepancias: Windows PowerShell hijo no encontraba Get-FileHash por PSModulePath heredado del host. No pasó el entrypoint ni llegó a los focos de bloqueo. [Salida preservada](BATERIA-ENTORNO.txt). |
| Batería con entorno hijo estándar | **24 comprobaciones OK, BATERIA_OK, exit0**; seis directorios W comprobados sin lanzamiento real. [Salida propia](BATERIA-FINAL.txt). |
| Negativo deliberado | **BATERIA_FALLIDA/exit1**, código esperado erróneo y marcador sintético de lanzamiento. [Salida](BATERIA-NEGATIVO.txt). No se lanzó un envoltorio para producir el marcador. |
| Foco independiente de handles | **5/5 PASS**, funciones exactas por AST, sin entrypoint ni procesos. [Resultado](BLOQUEOS.json), [script](check_file_locks.ps1). |

La batería nueva ejecuta los casos de Claude en salidas nuevas; no se renombra su log anterior como ejecución propia. Sólo en sus copias instrumentadas se sortean las compuertas necesarias para alcanzar el foco; el entrypoint del repositorio mantiene las exclusiones. Los dos lanzamientos de sus casos SIM son un hijo PowerShell de prueba, que calcula hashes e intenta cuatro alteraciones. Nunca ejecuta el contenido de INICIAR. Original válido, alteración coordinada, extra, cambios individuales, junction, tres informes fabricados y diagnósticos H1 concuerdan con los códigos previstos.

El foco propio confirma hashes sobre streams retenidos, apertura de segundo lector con bytes exactos, escritura rechazada con IOException/código nativo32, escritura tras Dispose y liberación de ambos handles cuando falla el hash. Datos sintéticos nuevos; sin borrados ni movimientos recursivos. Las etiquetas genéricas «bloqueado» de la batería prueban fallo de operaciones; el foco adicional sí comprueba la causa nativa de la escritura. No generaliza esa causa a los otros tres intentos.

## Repetición

Requiere los cuatro ZIP07 privados fijados en `.local/instalador-07/entrega`, Git Bash, Windows PowerShell5.1 y Python3.12 existentes. No es una receta de clon limpio ni instala herramientas. Para la batería, desde PowerShell:

```powershell
& C:/Python312/python.exe -X utf8 -B -m unittest tools.tests.test_w02_trial_plan
& 'C:\Program Files\Git\bin\bash.exe' -c 'unset PSModulePath; exec bash C:/RackClick_SVR/evidence/s1-20261025/w02-vm-limpia-07-claude/focos/ejecutar-focos.sh C:/RackClick_SVR'
```

Negativo: añadir `export W02_FOCOS_NEGATIVO=1;` antes de exec en esa invocación. Se espera exit1; el script crea su propia salida nueva y no elimina la anterior. Retirar PSModulePath sólo afecta al proceso hijo y permite a Windows PowerShell inicializar sus módulos estándar; no cambia el registro, perfil ni configuración persistente.

```powershell
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File .\evidence\s1-20261025\w02-r1b-codex\check_file_locks.ps1 -RunnerPath .\tools\windows\w02\Invoke-W02TrialPlan.ps1 -OutputDirectory C:\RackClick_SVR\.local\W02-R1B-BLOQUEOS-REPETICION-NUEVA
```

Ese script exige el hash exacto recibido y una salida nueva dentro de `.local` sin reparse. Extrae sólo tres funciones por AST. No carga ni ejecuta el entrypoint. [Huellas recibidas](RECIBIDO.json), [ZIP07 sin cambio](ARTEFACTOS-07.json). Los logs privados conservan el diagnóstico Get-FileHash original y las fuentes recibidas; no se publican datos privados del equipo.

## Conciliación

Reapertura §5.5, agregación de fallos y R1b conformes. H1 oficial posterior, H2 manual y H3 sin regeneración cosmética. El técnico aún debe probar que INICIAR real puede leer con los archivos retenidos y completar New/Restore/servicio/HTTPS/backup/reinicio/acceso posterior/exportación/informe en las VM. Si falla, se para sin quitar la protección. No se acepta por simulación ni se declara producto adoptado.

W-02.01–05 pendientes, delta0: **3,57/100 puntos del trabajo restante, 8/280 subpasos y 1/50 resultados completos**; porcentaje global sin afirmar. [Crédito](CREDITO-W02.json), [plan previo](PLAN-ANTES-W02.json), [controles finales](CONTROLES-CIERRE.json). No cambian pesos, alcance o C2. Catálogo y guías QA intactos: esta revisión no cambia funciones visibles ni disponibilidad.

[SHA256SUMS.txt](SHA256SUMS.txt) fija los bytes finales del cierre, comprobados con `tools/verify_hashes.py`. Escaneo limitado al contenido público nuevo y entradas nuevas de continuidad; no presenta el historial completo como limpio.
