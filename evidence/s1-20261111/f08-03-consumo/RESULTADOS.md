# F-08.03 · consumo y revocaciones en una transacción

11.11.2026. Cierre técnico con revisión independiente favorable. D y E sin operaciones. No se usaron VM, servicios, cuentas o bases instaladas, commits, push o despliegue.

## Reutilización e investigación

El canje del punto 3 ya usa transacción explícita, bloqueo y revalidación de cuenta/factor/desafío/política/códigos. F-08.01/.02 acreditaron generación y transición restringida; no se reimplementan. Se conserva la fuente y se añade únicamente `MfaRecoveryRedemptionTransactionTests.cs`, dos escenarios que demuestran solapamiento real y una transacción ganadora observada en PostgreSQL.

Consulta oficial del 11.11.2026: [transacciones PostgreSQL 17](https://www.postgresql.org/docs/17/tutorial-transactions.html) y [bloqueos explícitos PostgreSQL 17](https://www.postgresql.org/docs/17/explicit-locking.html). Se reutilizan Npgsql directo, SQL y pruebas existentes, sin librerías, migraciones, política o algoritmo nuevos. El testigo no sustituye la prueba de rollback ni prueba durabilidad frente a un apagón.

## Resultado comprobado

La prueba retiene la fila de la cuenta y exige observar dos PID runtime esperando antes de liberar. Ejecuta el canje con un mismo código o dos distintos del conjunto anterior. En ambos casos sólo un canje devuelve el desafío enroll; el otro recibe 401 `mfa_challenge_invalid`. Quedan diez códigos consumidos, dos sesiones previas retiradas, tres desafíos previos consumidos y un desafío nuevo, con factor desactivado y reenrolamiento exigido.

Un testigo creado sólo en el fixture registra relación, operación, rol y txid; no copia valores de filas. Las seis relaciones del ganador —códigos, factor, política individual, sesiones, desafíos y auditoría— aparecen bajo la transacción del audit ganador y el rol runtime. La auditoría final registra sólo pending y contadores (10/2/3). El rol es no propietario y sin DDL del producto; la tabla/función/triggers del testigo los crea el propietario, con permisos de inserción/lectura sólo para ese fixture.

Otra cuenta conserva exactamente sus seis colecciones propias de usuario, política MFA, factor, códigos, sesiones y desafíos. La política global de gracia no cambia. Las comparaciones se hacen sin volcar valores. El snapshot de diez tablas no contiene los códigos conocidos en formato original/normalizado ni los tokens/CSRF originales de los desafíos inspeccionados. Un proveedor que lanza al solicitar claves TOTP demuestra que el canje no las pide; el código puede leer metadatos/ciphertext sin descifrarlos.

## Ejecuciones nuevas

Windows, SDK 10.0.401/runtime 10.0.12, PostgreSQL 17.11, esquema 46. Copia aislada `.local/f0803-83799606/freeze`; conexiones, TRX, logs y binlogs privados. Restore locked y build Release: exit 0, cero errores y advertencias. Foco **9/9 PASS, 0 fallos y omitidas**, en su primera ejecución. Los dos casos nuevos amplían cobertura sobre producto que ya funciona; no se inventa fase roja ni corrección de producto.

| Casos | Cobertura |
|---|---|
| 2 nuevos | Mismo código o dos códigos del conjunto, dos PID esperando, un ganador, testigo de commit, revocaciones por cuenta, otra cuenta intacta y valores originales ausentes |
| 1 existente | Canje sin sesión y sin solicitar clave TOTP |
| 1 existente | Canje concurrente histórico; se conserva su cobertura, sin atribuir a Task.WhenAll una observación de solapamiento |
| 1 existente | Replay, finalidad equivocada y CSRF, sin consumo indebido |
| 1 existente | Caducidad y cambio de revisión de política |
| 1 existente | Caducidad mientras espera el lock de filas de códigos, demostrando espera real |
| 1 existente | Intentos inválidos acotados y bloqueo compartido con uso del factor |
| 1 existente | Fallo forzado al insertar audit; rollback de las diez tablas del snapshot, incluido código, sesión y desafíos |

Los siete existentes pertenecen a `MfaRecoveryCodesTests`. Los nombres completos, pines y resultados individuales se conservan en FOCO.json/TRX privado. Comando: `dotnet test ... -c Release --no-build --no-restore --filter <foco F0803> --logger trx;LogFileName=<privado>/focus.trx -bl:<privado>/focus-{}.binlog`. El driver privado crea y cierra su clúster y comprueba pines antes/después; el test y helper son fuentes del repositorio. No se ejecuta un operador sobre D.

## Identidad y evidencia reutilizada

Los 227 archivos de producto de F-08.02 se conservan en raíz/copia; no cambian generador, canje, UI, SQL, dependencias o política. FUENTES.json contrasta también el núcleo y fuentes asignadas del punto 3 y las pruebas nuevas de F-08.01/.02. La DLL tiene pin propio por reconstrucción en otra ruta; no se anuncia identidad binaria con la candidata instalada.

Los 20 Node y el recorrido HTTP de F-08.02 se reutilizan con su fecha y fuente. Edge y la regresión final del punto 3 son históricos y se atribuyen a sus ejecutores; no se repiten ni suman como pruebas nuevas. No hay cambio visible o caso QA nuevo. Se preservan los 175 casos y resultados de Wascar y se reutiliza QA-163 sin alterar disponibilidad.

## Límites

- Prueba de transacciones/bloqueos sobre PostgreSQL real, no apagón, reinicio Windows o recuperación de proceso durante commit.
- Fixture con roles SQL separados y factores/sesiones sintéticos; no SID efectivo, DPAPI, servicio instalado, TLS, navegador o candidata objetivo nuevos.
- `SnapshotAll` cubre diez tablas de identidad/MFA/Systemhaus/operación/auditoría, no toda la base o el inventario. La comparación de la otra cuenta cubre las seis colecciones indicadas. No es un análisis de memoria, logs, dumps o todo el historial de secretos.
- El canje retira el conjunto completo y sólo concede enrolamiento; no sustituye la emergencia local de un host sin almacén. Custodia, último administrador, F-08.04/.05, hitos operativos y aceptación de Wascar permanecen pendientes.


Pines finales: servidor `d315a00df4cd522b26030369de26fba1410a04c5a2c77667572aa6733e7c59b4`; pruebas `4f3d914452030f13eb877b2fb7680b18b77fbb63ef4531af2272cc73184b5120`. FUENTES.json conserva 227 archivos de producto, 29 fuentes asignadas del punto 3 y dos pruebas previas, además de 13 referencias históricas; ninguna de esas ejecuciones históricas se vuelve actual por el hash.


## Revisión y conciliación

[Dictamen distinto](review/DICTAMEN.md): repetición propia de los dos casos nuevos y del rollback existente, 3/3 PASS sin omisiones, con pines comprobados antes y después y clúster detenido. Se distingue del foco 9/9 del coordinador y las ejecuciones históricas. Sólo F-08.03 suma 1/2: 1943/84 → 1985/84 = 23,630952…/100 del cierre restante. F-08.01/.02 se conservan; F-08.04/.05 e hitos operativos permanecen pendientes.
