# F06.02 · revisión independiente de la integración nativa

09.11.2026. Revisor de seguridad distinto de los implementadores. **Dictamen favorable acotado para esta integración de metadatos; F06.02 permanece `in_progress`, +0 puntos.** No se aprueba la retirada de claves ni el cierre completo del paso20. No modifiqué producto, contratos, permisos, ledger o trabajo ajeno; sólo sondas/evidencia privadas y este dictamen.

## Alcance y fuentes consultadas

Leídos AGENTS, BRIEFING-MAESTRO, PLAN-F0602-INTEGRACION-BACKUP, PASO-020 y CONTRATO-INVENTARIO-RETENCION-MFA-v1; contexto de continuidad, S1, contrato servidor, mapa/aceptación, README, equipo y PROGRESO-GLOBAL. Los tramos históricos del paso20 describen la tanda de componentes anterior y deben distinguirse de esta integración.

Archivos y símbolos contrastados:

- `development/server/src/RackClick.Server/MfaBackupInventoryCommand.cs`: `RunAsync`, `ValidateIdentity`, `ValidateSchemaVersion`, `ConnectionString`, `ReadLine`, `Parse`, `Exact`, `String`, `Id`, `Hash`, `Base64`, `Reply`, `Reject`.
- `Program.cs`: rama `--mfa-backup-inventory`, exclusión de modos y retorno previo a `WebApplication.CreateBuilder`; diff contra `.local/f0602-native-b59d6b15/before/Program.cs`.
- `MfaFactorKeyInventoryReader.ReadAsync`; `MfaKeyRetention.InspectEnvelope`, `CreateBackupInventory`, `SerializeBackupInventory`, `ParseBackupInventory`, `EvaluateCandidate` y derivación de versiones requeridas.
- `tools/windows/RackClick.MfaBackupInventory.ps1`: `Open/Close-MfaBackupTool`, `Set-MfaBackupChildEnvironment`, `Start/Read/Complete/Close-MfaBackupProtocol`, `Read-MfaBackupBytes`, `Read-MfaBackupReceipt` y hashes.
- `New-RackClickMfaDatabaseBackup.ps1` y `Test-RackClickMfaDatabaseBackup.ps1`: conservación de ruta .NET previa a imports, protocolo, snapshot, publicación exclusiva, recibo externo y consumidor.
- Reutilizados de `RackClick.Backup.ps1`: `Assert-BackupPath`, `Assert-BackupNoReparse`, `New-BackupPrivateDirectory`, `Assert-BackupPrivateAcl`, `Read-BackupProfile`, `Assert-BackupPostgresTools`, `Write-BackupNewText`, `Invoke-BackupPg`, `Read-BackupManifest`; declaración de parámetros de `Test-RuntimePrerequisites.ps1`.
- `MfaBackupInventoryCommandTests.cs`, `tools/tests/test_mfa_backup_inventory_operator.py`, `test_mfa_backup_inventory_cli_host.py`, `run_mfa_backup_inventory_native.py`, CLI-RESULTADOS, POSTGRES-NATIVO y FUENTES.

Se verificaron de nuevo los **9 SHA256 de FUENTES.json** contra el árbol y la DLL aislada `a222a6dbf2010d0f8155a636549b6b6d20ceb6a01dccb8b2dbf5b78dd1915706`. Coinciden. El sello incluye CLI `f9af6d5a…dd22c3c`, helper `120302b9…6263185`, New `366fb09f…20d104` y Test `40d90d1d…5d5f5e`; las huellas completas y los nueve paths están en [FUENTES.json](FUENTES.json).

## Hallazgos corregidos durante la revisión

| Gravedad | Observación y comprobación | Estado final |
|---|---|---|
| P1 | El coordinador reprodujo que `obj_description` omitía el comentario compartido de DB, incluido marcador de recuperación. | `shobj_description`; negativo PG final rechaza el marcador. Contraste propio de código y resultado, ejecución PG del coordinador. |
| P2 | Hallazgo propio: sólo comprobar DML en `app_mfa_factor` admitía `UPDATE(username)` en `app_user` y membresía owner `SET TRUE/INHERIT FALSE`. El coordinador reprodujo aceptación antes del arreglo. | Se comprueban DML/columnas en relaciones de schemas no sistema, CREATE de schemas/DB y cualquier membresía directa. Ambos negativos PG finales rechazan. No se alteran privilegios desde el CLI. |
| P2 | El coordinador reprodujo aceptación de una junction vacía ajena al layout del tool. | Se inspecciona cada entrada antes de descender, se rechaza reparse/directorio no respaldado por SUMS y se acota a1024 directorios. Test propio final pasa. |
| P2 | Integración PowerShell: el import del prerrequisito histórico vaciaba `DotnetPath` por compartir scope/nombre. | New/Test conservan `$mfaRuntimeHostPath` antes de importar y lo usan al iniciar; contrastado directamente. Recorrido PG final pasa. |
| P2 | Compatibilidad PS5.1: `ProcessStartInfo.StandardInputEncoding` no existe en .NET Framework. | `StreamWriter` UTF-8 explícito sobre stdin; ambos operadores usan `InputWriter`, que se cierra/dispone. Test propio de arranque de proceso pasa en PS5.1. |
| P2 | El backend reprodujo un lector que ignoraba el token y no terminaba. | Espera enlazada a cancelación y salida acotada; prueba roja/verde documentada por backend. No me atribuyo esa ejecución. |

No quedan bloqueantes nuevos identificados en el conjunto sellado dentro de este alcance. Esto no prueba ausencia de defectos fuera del alcance o de las entradas ensayadas.

## Pruebas ejecutadas por este revisor

Entorno Windows/PowerShell5.1 y Python3.12 existentes; sin instalaciones. Comandos ejecutados y salidas leídas:

- `C:/Python312/python.exe -B -m unittest tools.tests.test_mfa_backup_inventory_operator -v`: **10/10 PASS**, 0 fallos, ejecución final3,962s. Pines/tool alterado/extra, archivos retenidos contra escritura, entorno sólo del hijo, junction vacía, recibos, parser PS5.1 y arranque de proceso/pipe .NET Framework. Las ejecuciones8/8 y9/9 anteriores se sustituyen por esta final; no se suman.
- `powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File .local/f0602-native-b59d6b15/review/review-probes.ps1`: **4 comprobaciones PASS** sobre helper final. Recibo canónico con pin; duplicado rechazado aun con hash coincidente; creación exclusiva de archivo/directorio conserva sentinel; reparse tanto hoja como ancestro rechazados. Sonda y fixtures sintéticos conservados bajo `.local/.../review/`.
- `C:/Python312/python.exe -B -m unittest tools.tests.test_mfa_backup_inventory_cli_host -v`, seleccionando DLL aislada final de `freeze` mediante `RACKCLICK_F0602_NATIVE_DLL`: **3/3 PASS**. Configuración host inválida no se compone; conflicto con cinco modos anteriores; argumentos adicionales rechazados. DLL cotejada contra el pin indicado arriba.
- Verificación PowerShell de los nueve archivos de FUENTES.json y de la DLL: **9+1 coincidencias**.

Incidencia propia de selección: un primer intento de los tests host apuntó a `cli-freeze`, que conservaba Program anterior al wiring, y falló3tests/7subcasos. Se comprobaron huellas de Program y se corrigió la selección a `freeze`; no se oculta ni se clasifica como defecto del producto final.

## Evidencia ejecutada por otros y contrastada

Leídos `CLI-RESULTADOS.md` y log privado `cli-final.log`: backend24/24 pruebas puras, 0 fallos/omitidas,189ms; no son pruebas ejecutadas por este revisor.

Leídos [POSTGRES-NATIVO.json](POSTGRES-NATIVO.json), harness final y log privado `native-final.private.log`: coordinador **8/8 comprobaciones PG17.11/esquema45**, con DLL exacta. Tres negativos de identidad/rol rechazan; exportador mantiene RepeatableRead/read-only hasta terminar dump; pg_dump importa `--snapshot`; escritor posterior añade8/disabled; dump restaurado en otra DB contiene exactamente1/disabled,1/pending y7/active, sin la escritura posterior. Origen conserva cuatro factores; el harness final compara además un hash de JSONB ordenado de todas las columnas/filas de factores antes/después de los operadores, no sólo su número. Operador New y consumidor Test pasan; inventario alterado, destino existente y tercer archivo histórico se rechazan. Cluster propio consta parado. Son pruebas del coordinador, no una nueva ejecución PostgreSQL propia. Se repitió el cotejo de los nueve hashes después de actualizar el harness final; todos coinciden.

Los fallos previos de autoload de módulo de seguridad PS7/PS5.1, colisión de parámetro y API de stdin se conservan como intentos anteriores; el verde final no los transforma en pruebas pasadas. Se contrastaron después [REGRESION.json](REGRESION.json) y los logs privados `regression-final.private.log` y `python-final.private.log`: coordinador138/138 pruebas .NET, 0 fallos/omitidas, y13/13 Python (3host+10PS). Es una regresión acotada del coordinador sobre el conjunto final, no pruebas propias ni adicionales a sumar a la misma cobertura.

## Conclusiones y límites

El CLI local retorna antes del host, no abre listener ni usa identidad API; el acceso de este operador depende de la cuenta Windows y del rol de backup explícito. La validación actual liga DB, sesión/usuario, owner y UUID nativos, versiónPG y secuenciaSQL45. La secuencia1..45 **no valida los digests de migración** ni vuelve confiable un servidor administrado por un tercero.

El inventario y su consumidor ligan instalación/backup y hashes de manifiesto/dump/sobre mediante un recibo cuyo pin viene de fuera del archivo. Los recibos canónicos y los contenidos conservan comprobaciones cerradas. Esa integridad requiere custodia independiente fiable del pin; el laboratorio no acredita custodia externa real. `catalogComplete=false` y `retirementAuthorized=false` permanecen explícitos. Los backups históricos sin inventario siguen siendo dependencias desconocidas.

Contraseñas/sobre se transportan por stdin; se limpian configuraciones PG/.NET, hooks/profilers y configuración de secretos del hijo; los diagnósticos externos son constantes. No se observó inclusión de secretos reales en estas fuentes/evidencias; los ensayos usan material sintético privado. No se certificó memoria del proceso ni borrado físico.

No ejecuté PostgreSQL, servicios, VM, instalación, restauración operativa MFA, login/CSRF/revocación de sesiones, tests API por cliente, retirada, publicación de anillo, fence, crash/reboot o suite global. El lote no cambia autorización HTTP ni revocación; no procede presentarlo como una auditoría completa de esos subsistemas. No se repitieron las115 pruebas de componentes por inercia.

La coherencia probada cubre censo/dump de una instantánea SQL. No es lease sobre futuras escrituras ni snapshot coordinado de DB/anillo/disco. **Siguen pendientes coordinador/fence/recenso, catálogo global autoritativo y retirada/publicación recuperable real de F06.03 para completar el criterio literal de F06.02.** Sin adopción de Wascar, operaciones sobre D/E, commits o publicación. Índice conservado **19,76/100 del cierre restante**, no porcentaje global nuevo.
