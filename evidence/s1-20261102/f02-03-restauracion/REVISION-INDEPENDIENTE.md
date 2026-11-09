# Revisión independiente · F-02.03 · parcial

02.11.2026. Revisor: /root/f01_classification_review, distinto del coordinador implementador. El único archivo escrito por el revisor es este dictamen; no editó producto, pruebas, ledger o documentación ajena.

**Favorable para registrar desarrollo y ensayo de laboratorio parciales. NO aprobado para cierre ni acreditación de F-02.03 o de F-02 completo. Crédito: 0.** F-02.01/.02 mantienen sus pendientes y F-02.04 no se acredita. El índice permanece en 1849/168 = 11,01/100; no es un porcentaje global nuevo del producto.

Contrasté los cinco archivos de producto con las copias previas de sources/: New-RackClickLabInstance.ps1, New-RackClickRecoveredInstance.ps1, RackClick.Instance.ps1, RackClick.Process.ps1 y RackClick.Process.Gate.ps1. Revisé los vínculos, inventario y ramas v1/v2, el opt-in ProtectSqlCredentials, Write-InstanceSqlProfiles, Read-InstanceSqlProfile, Read-RackClickInstance, Invoke-InstanceChild, Invoke-RecoveryOwnedChild, Invoke-InstanceWithTemporarySecret, Start-RackClickOwnedProcess y el recorrido protegido del Gate. Se reutiliza la revisión del codec y del helper SQL de las tandas anteriores; no se repitieron sus suites ni lecturas de blobs.

La versión revisada distingue explícitamente el legado del manifiesto v2 con seis archivos privados. El v2 rechaza runtime en claro y liga perfiles a UUID, puerto, base, rol y referencia exacta; conserva pins y archivos retenidos. El lector runtime comprueba metadatos de owner/cluster, sin descifrarlos. El mantenimiento abre sus perfiles explícitamente antes de iniciar PostgreSQL en la sonda. Esto corrige la dependencia anterior del lector runtime respecto del contexto CurrentUser del provisionador; no demuestra todavía la separación operativa final de actores.

Hallazgos tratados durante la revisión:

- **P2, resuelto: petición persistente en claro.** El trazado inicial mostraba ownerConnection y stdin serializados en request.json. El coordinador reprodujo una coincidencia mediante ROJO-PETICION.json, sin valores públicos. Ahora los hijos bootstrap/migrate/recover-admin del opt-in usan ProtectRequest: DPAPI CurrentUser con propósito y ruta, cifrado antes de escribir, sobre cerrado de tres campos, Gate protegido sin fallback y error constante. Las peticiones legadas no se convierten silenciosamente.
- **P2, resuelto por el coordinador: pgpass de Restore persistente.** El ensayo intermedio conservado dio 7 PASS/1 FAIL por restore-password.pgpass. La rama protegida lo utiliza ahora mediante el mismo helper temporal exclusivo y lo retira al finalizar.
- **P3, resuelto estáticamente: limpieza de initdb.** La escritura inicial quedaba fuera del try; posteriormente Dispose podía impedir alcanzar Delete. El helper actual registra propiedad inmediatamente después de CreateNew y anida Dispose, limpieza de bytes y retirada propia. Si CreateNew rechaza un archivo preexistente, éste no se elimina. No se ejecutó inyección de fallo de Dispose/Flush; la estructura de ese borde se revisó por código. Un corte abrupto o un fallo de almacenamiento no equivale a borrado físico garantizado.

No quedan hallazgos bloqueantes nuevos dentro de esta versión acotada de laboratorio. Lo anterior no constituye aprobación para activar el formato en una instalación o cambiar D.

Mis comprobaciones ejecutadas fueron lecturas de fuentes/diffs y documentación pública, comparación de las 11 huellas de HASHES-CODIGO.json y de las fuentes declaradas por el resultado estable, y contraste estructural de los JSON públicos. Leí también los focos de petición protegida, temporal, privacidad y mantenimiento para comprobar su alcance y el orden anterior al arranque de PostgreSQL. **No ejecuté PostgreSQL, Gate, DPAPI, scripts de provisión/Restore, suites, builds, escaneos, autenticación, instaladores, GUI, servicios o VM en esta tanda. No abrí credenciales, transcripciones ni archivos privados de los fixtures.** Las sondas propias de tandas anteriores no se contabilizan como ejecuciones nuevas.

Leí los informes del coordinador, que son sus ejecuciones:

- Resultado estable: 8/8 PASS, 0 fallos/errores, 126,187 s; PostgreSQL 17.11/esquema43 en dos clústeres nuevos bajo el mismo principal Windows. Incluye datos sintéticos, dos reanudaciones del clúster destino, lectura runtime y rechazo del comando DDL, destino existente preservado y material ausente/alterado/de otro contexto rechazado antes de iniciar PostgreSQL en mantenimiento.
- Petición protegida: 8 controles PASS; temporal exclusivo: 4 controles PASS. Estos últimos cubren uso normal, fallo de la acción y archivo preexistente; no inyección de fallo de Dispose/Flush.
- Regresiones legadas: 6/6 New y 6/6 lanzador. No son un arranque protegido del host nuevo ni aceptación de Windows/servicio.
- Privacidad: cero coincidencias finales de las tres contraseñas SQL propias en UTF-8/UTF-16 dentro de private, logs y sql-security de ambos fixtures. Es una comparación focal de valores generados por el ensayo, no un escáner global, ni una inspección de pgdata, historial, otros privados o memoria. Los intentos rojos anteriores se conservan y no se presentan como verdes finales.

Huellas finales comprobadas:

| Archivo | SHA256 |
|---|---|
| tools/windows/New-RackClickLabInstance.ps1 | e38d51901289966554cd76b0f9ce1748483a2ef0fbfe841312d75df983868a1a |
| tools/windows/New-RackClickRecoveredInstance.ps1 | c51553fec0506f4b12adc46883b734ef0e19a6573554e940063cd2315be2e589 |
| tools/windows/RackClick.Instance.ps1 | 41c258a3b0918347c90c8304eb955eba2166602d4e5d84cb0cce03c511fc4487 |
| tools/windows/RackClick.Process.ps1 | c9442b504a00f5b1a20aa9f37be5f48d6f45c35d44b5bc48feb672bcb4e1b316 |
| tools/windows/RackClick.Process.Gate.ps1 | 44c934cb41d3eec07b9e7394802a736f83bc8f98d462c8f3caa82ac833834e4b |
| HASHES-CODIGO.json, 11 entradas | adc51d84e30bc0be800d48c53e9ad6c800ce38e6cd54efda29ffae7d6abf4744 |
| pruebas-estables/result.json | f45fc2fcba1b33157934fffbbcc703e04c9fedea32dacce236ad2a266c2aed3e |
| PRUEBAS.json | a0e13f8d89784e1d3c8ee84b599e62a69f25107f4131966cfc4ddf8f3ee2daa3 |

También consulté INVESTIGACION-PREVIA.md, RESULTADOS.md, ROJO-PETICION.json, el contrato REANUDACION-RESTORE-SQL-PROTEGIDO.md y PASO-007-REANUDACION-RESTORE-SQL.md. Las fuentes primarias contrastadas fueron [Microsoft DataProtectionScope](https://learn.microsoft.com/en-us/dotnet/api/system.security.cryptography.dataprotectionscope?view=windowsdesktop-9.0) y [PostgreSQL17 initdb](https://www.postgresql.org/docs/17/app-initdb.html): el contexto CurrentUser y la necesidad de un archivo para pwfile se tratan con sus límites, sin introducir dependencias.

La DLL43 histórica se usa únicamente para las CLI de bootstrap/recuperación y no contiene el código SQL del paso5. No se ha probado el host HTTP protegido, un servicio estándar, backup programado, otro Windows/SID, Restore con factores MFA ni migrate13→43 en este lote. La preparación v2 no es una candidata instalable aceptada. Siguen pendientes la cuenta de backup con privilegios mínimos, sus actores efectivos, propietario/ACL productivos, integración de setup/recibos/distribución y candidata completa. El acceso web inicial conserva su archivo privado contractual: no se afirma cifrado de todas las credenciales del producto.

Dictamen limitado a las fuentes y evidencias fijadas: D, otros servicios/cuentas, paquetes, QA de Wascar y privados ajenos no fueron operados por el revisor. El siguiente cambio contable admisible es sólo F-02.03 pending → in_progress, sin crédito; el revisor no lo ha aplicado.
