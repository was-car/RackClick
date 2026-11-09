# F-02.03 · reanudación/Restore SQL protegido · 02.11.2026

**Resultado: implementación y ensayo de laboratorio completados; checkpoint parcial, sin crédito. D intacta.** [Contrato](../../../docs/REANUDACION-RESTORE-SQL-PROTEGIDO.md) · [Ficha](../../../docs/PASO-007-REANUDACION-RESTORE-SQL.md) · [Revisión independiente](REVISION-INDEPENDIENTE.md).

## Qué se reutiliza y qué cambia

Se reutilizan el codec/lector C# del paso5, los perfiles/codec PS y operadores de backup del paso6 y sus pruebas ya registradas. No se repiten sus39/132 pruebas C#,27PS,5interop,94visor ni el backup v2 anterior como trabajo nuevo. Se conserva la DLL43 histórica del ZIP de revisión fijado: sólo se usan sus CLI bootstrap y recover-admin. **Esa DLL no contiene el código C# SQL del paso5 y aquí no se ha arrancado el host HTTP protegido.** No hay build, publish, restore NuGet, nuevas dependencias, migraciones o paquetes.

Cinco archivos de producto cambian respecto a su copia previa de este lote, conservada en `sources/` y `ANTES.json`; el diff no se atribuye a todo el árbol concurrente:

- New y Restore: opt-in `ProtectSqlCredentials`, manifiesto2/inventario cerrado, owner/cluster CurrentUser y runtime RCSQL001 nuevos por destino. Legado sin opt-in conservado. Archivos SQL antiguos en claro no se crean en el circuito final protegido.
- Instance: validación v1/v2 por ramas, perfiles ligados a ID/base/rol/puerto/ruta, runtime ausente con código constante, lector runtime sólo de metadatos para owner/cluster. Mantenimiento descifra explícitamente; no concede al runtime una clave privilegiada.
- Process y Gate: petición protegida opt-in CurrentUser ligada a propósito/ruta, sobre cerrado sin fallback y diagnóstico constante. Se limita a los hijos SQL de la rama protegida; no cambia las peticiones históricas ni D.
- Helper temporal compartido: CreateNew/propiedad inmediatamente después de crear; Dispose, limpieza de bytes y retirada propia en finally anidados. Initdb y el pgpass de Restore protegidos lo usan. No borra un archivo preexistente. Un corte abrupto puede conservar un temporal privado; no se afirma eliminación física o durabilidad universal.

`RackClick.SqlSecrets.ps1`, C#, MFA, dependencias, SQL, paquetes y catálogo no cambian. El esquema de datos sigue43. La aplicación inicial web continúa en su archivo privado según el contrato existente: no se afirma cifrado de toda credencial del producto.

## Ensayos reales del coordinador

Windows11 del anfitrión, Windows PowerShell5.1, PostgreSQL17.11, herramientas .NET del SDK10.0.401 ya fijado. Instancias/clústeres nuevos no registrados como servicios, bajo el mismo SID Windows del laboratorio. Datos y logs propios bajo `.local/sql-recovery-labs/`; no se accede a D, SCM, claves reales, sesiones o resultados de Wascar.

| Comprobación | Resultado final y alcance |
|---|---|
| `test_sql_protected_recovery.py` | **8/8 PASS**,126,187s. New+backup+Restore nativos con aplicación43,20filas sintéticas. Otro UUID/base/clusterAdmin/owner/runtime, contraseñas/ciphertext locales nuevos. Dos arranques y paradas del clúster recuperado, lectura con runtime y DDL rechazado; fuente y export conservados. |
| Negativos dentro de los8 | Destino existente preservado. Runtime ausente, runtime alterado incluso rehaciendo ambos digests, owner ciphertext copiado del origen y archivo owner ausente rechazados antes de iniciar PostgreSQL. Metadata runtime acepta el inventario/pins con owner de otro contexto sin intentar descifrarlo; mantenimiento lo rechaza. No son ocho ensayos de servicio. |
| Privacidad dentro de los8 | Compara en memoria las tres contraseñas SQL propias contra UTF8/UTF16 de configuración, ciphertext y logs/request finales de ambos fixtures: **0 coincidencias**. No es un escáner global de secretos ni de `.local`. |
| `Test-ProtectedProcessRequest.ps1` | **8 controles PASS** reales: hijo recibe entorno/stdin y termina, request sólo sobre, mensaje constante, rechazo del legado bajo modo protegido, copia de ciphertext a otra ruta y alteración. No prueba otro usuario Windows. |
| `Test-TemporarySqlSecret.ps1` | **4 controles PASS**: contenido/ACL durante uso, limpieza normal, limpieza si la acción falla, destino previo intacto sin ejecutar acción. Sin inyección de fallo de Dispose/Flush. |
| Regresión `test_instance_provisioning.py` | **6/6 PASS**,74,875s, entradas vigiladas idénticas; aplicación histórica9, clústeres nuevos. |
| Regresión `test_instance_launcher.py` | **6/6 PASS**,13,422s, entradas vigiladas idénticas; procesos/fixtures simulados del lanzador. No es un arranque HTTP del host SQL nuevo. |

No sumar controles como puntos ni convertir esquemas históricos en pruebas del43. Las guardas comprueban fuentes inalteradas durante cada ejecución y los clústeres propios detenidos; no se borran laboratorios antiguos.

Comandos nuevos: `C:/Python312/python.exe -X utf8 -B tools/tests/test_sql_protected_recovery.py --evidence evidence/s1-20261102/f02-03-restauracion/pruebas-estables`; ambos focos PS5.1 se ejecutan con `-NoProfile -NonInteractive -ExecutionPolicy Bypass -File` y una carpeta nueva exclusiva bajo `.local/sql-request-labs/`. Las regresiones usan `--evidence .local/f02-03-regression-instance-final` y `...launcher-final`. No se ejecutan instaladores.

## Fallos previos conservados

1. Primer ensayo7/7 correcto en lo que medía, **insuficiente para privacidad**: revisión detectó owner en `request.json`. El nuevo foco sobre ese fixture reproduce `sql_plaintext_retained`, una coincidencia; `ROJO-PETICION.json` no contiene valores. Se añade petición cifrada antes de escribir, no retirada tardía por nombre.
2. El siguiente ensayo8 arroja7PASS/1FAIL: privacidad del origen0, destino1 por el `restore-password.pgpass` legado persistente. Se conserva `pruebas-finales/result.json` como fallo, sin llamarlo verde final. Se corrige con el temporal exclusivo y se repite sobre dos clústeres nuevos: `pruebas-estables/result.json`,8PASS.
3. Revisión detectó que el lector runtime intentaba descifrar owner/cluster: se separó metadata de mantenimiento. El positivo con owner extranjero y el negativo del mantenimiento ejercitan la separación, **no un token Windows diferente**. Se anidó la limpieza para no saltarla si Dispose falla; ese borde se revisó estáticamente, no con fallo de disco.

Los intentos previos quedan privados y detenidos; sus contraseñas son exclusivamente sintéticas. No se modifican sus logs para fingir privacidad final ni se exportan a Git.

## Qué no se cierra

- Falta una candidata completa compatible con el código C# SQL actual y el inventario de operadores; no se transporta el módulo nuevo en paquetes11 históricos.
- Falta propietario/ACL productivo del runtime y la identidad efectiva del servicio estándar. Los helpers preparan material privado; no habilitan el host saltándose su lector.
- Falta diseño/provisionamiento operativo de la cuenta de backup con privilegios mínimos. CurrentUser del provisionador no se convierte en CurrentUser del servicio: copiar ciphertext no funciona y sellar owner para el runtime no cumpliría separación de privilegios.
- Falta otro Windows/SID, backup programado y Restore operativo con esos actores. Dos clústeres nuevos bajo un mismo SID no acreditan portabilidad ni adopción. No hay migración de DPAPI origen.
- No se ejercitó la rama migrate13→43 en este lote, ni Restore con factores MFA, ni GUI/login/reinicio Windows. Reutilizar sólo las evidencias anteriores válidas para sus propios alcances.

Por ello F-02.03 pasa sólo a **in_progress**,0puntos; F-02.01/.02 conservan su estado parcial y F-02.04 no se cierra. Índice exacto1849/168 = **11,01/100**, sin porcentaje global nuevo. Alcance/criterios/pesos/53resultados/280checkpoints/268números conservados. QA168 sigue planificado y todo el catálogo QA conserva sus bytes. Sin commits/push, publicación, instalación, servicio/cuenta/red o VM. La revisión distingue lo inspeccionado por el revisor de las ejecuciones anteriores del coordinador.
