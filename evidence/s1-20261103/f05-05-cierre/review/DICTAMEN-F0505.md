# Dictamen independiente · F-05.05 · paso18

03.11.2026. **Favorable para cerrar F-05.05 técnicamente (+1/2)**: el criterio de F-05 queda probado por el conjunto F-05.01–.04 más la integración real DB/almacén/pipeline de esta tanda. No es aceptación de un operador productivo, instalador o recuperación operativa integral. `implementation_complete`, `integrated_current_candidate` y `target_acceptance` deben permanecer pendientes.

Este alcance corresponde a la [adenda del umbral](UMBRAL-F0505.md): TestServer aislado, sin listener de red o instancia instalada adoptada, permite verificar el flujo del servidor sin fingir un coordinador D2 productivo. Las guardias del operador nativo no se han eliminado ni se presentan como implementadas por la supervisión del fixture.

## Identidad y evidencia

- Fuente final Freeze6: `b6bd93e3a7cf36de94828405210cc0d4f7beef0008221e03fd0458ff9e9cd35a`.
- DLL de pruebas Release: `d29dab229ac0859299bfd23bd52f2059aaa0e64c0b923865e9108cea7abab267`; servidor Debug aprobado F-04.01: `cd3ccf922c7830007d3a82277729c372242f5f67ca1f4d032269d4093b0b7bcd`.
- Comprobación independiente de **9 artefactos núcleo,45 SQL, proyecto/lock y12 fuentes de producto** iguales a la copia aprobada. SDK10.0.401, frameworks10.0.12 con rollForward Disable. No se reconstruyó el producto para esta revisión.
- [Recibo R3 del coordinador](../COORDINACION-PG-R3.json): **8/8 PASS,0fallos,0omitidas**, salida0, binlog privado producido y cluster propio detenido. Las dos corridas anteriores también quedaron detenidas y preservadas. No se suman los intentos fallidos como pruebas nuevas exitosas.

[Comprobación y hashes propios](COMPROBACION-F0505.json), [auxiliar documental ejecutado](Verify-F0505.py), [manifiesto Freeze6](../implementacion/HARNESS-FREEZE6-PREVIO-PG.json).

## Qué demuestra el recorrido

1. **Restore PostgreSQL real.** Se crea el esquema45 de aplicación y datos sintéticos con jerarquía/inventario y dos usuarios/factores. `pg_dump` custom y `pg_restore --single-transaction` se ejecutan sobre DB/roles nuevos. Antes de la recuperación administrativa se comprueba igualdad del fingerprint de todas las filas/tablas públicas origen/destino, no sólo conteos parciales.
2. **Autoridades y datos conservados.** `RecoveryAdministrator.Run` real revoca sesiones/desafíos restaurados y deja auditoría con2desafíos revocados. Las cookies antiguas y el desafío anterior no autorizan API ni generan sesión. Los factores elegidos no se resetean para fabricar el positivo; conservan Systemhaus/userId/key_version/ciphertext y sus usuarios originales. La fuente se contrasta tras los casos y al disponer el fixture mediante filas públicas y bytes/ACL de almacenes/sobres.
3. **Material recuperado en el host de aplicación.** Se recuperan versiones1retirada/7activa mediante APIs Windows aprobadas. `Program` compone realmente `WindowsMfaKeyProvider` sobre la raíz recuperada; la prueba comprueba su tipo. No se inyecta un proveedor que entregue claves ni se simula la aprobación de TOTP. El cambio de Windows/SID real se reutiliza de F-05.04, sin afirmar que se repitió aquí.
4. **Login completo para ambas versiones.** Contraseña válida→desafío sin sesión API→TOTP válido→sesión/CSRF nuevos→`/me` con el usuario original y API autorizada. CSRF incorrecto se rechaza, logout válido revoca la sesión y el mismo TOTP con otro desafío es rechazado sin añadir sesión. TOTP incorrecto también da401 sin cookie ni aumento de sesiones.
5. **Fallos de material.** Contraseña del sobre incorrecta, versión requerida ausente y AAD de usuario incompatible impiden crear el almacén candidato y construir un host para él. La supervisión previa contra los factores DB es **código del fixture**, no un comando/guardia productivo nuevo. Los positivos y negativos de aplicación se prueban con componentes reales; esta distinción limita lo que se anuncia del producto.
6. **Rol de ejecución restringido.** La API usa una cuenta distinta del propietario, sin SUPERUSER/CREATEDB/CREATEROLE/BYPASSRLS ni CREATE/TEMP de DB/esquema; crear una tabla falla por permisos. Las siete tablas globales de catálogo sólo permiten SELECT. Migración/recuperación usan identidad separada. No se afirma que este fixture haya instalado todos los grants de un servidor productivo.

## Hallazgos y precisiones

**No hay bloqueantes pendientes para el cierre técnico indicado.** Autenticación, revocación y CSRF atraviesan las rutas/middleware/almacén reales. Los usuarios probados tienen permisos de lectura definidos; el resultado no depende de ocultar controles de UI ni de una cuenta exenta que entre sólo con contraseña.

- La primera corrida falló durante la preparación del almacén antes de ejecutar los cuerpos de los8casos. Una sonda con la misma DLL confirmó Win32 206 con ruta proyectada266 y éxito258; se acortó la ruta del fixture. **No se corrigió ni se acredita soporte universal de rutas largas del producto**.
- La segunda corrida obtuvo3PASS/5FAIL: cuatro errores de raíz de contenido WAF y una expectativa de excepción demasiado exacta. Freeze6 fija el content root mediante variable oficial acotada al fixture y restaurada en `finally`, copia el deps correcto y espera la familia `CryptographicException`, incluida `AuthenticationTagMismatchException`, manteniendo rechazo y destino ausente. No se relajó a excepción genérica o éxito alternativo.
- El runner limpia DOTNET/COMPlus/COR/CORECLR y configuración heredada relevante antes de introducir sólo ajustes conocidos/credenciales del nuevo cluster. La primera corrida ya declaró0nombres peligrosos heredados; el endurecimiento no convierte sus fallos de preparación en defectos de producto ni exige repetirla por ese motivo.
- Los seams de **identidad de laboratorio y dirección IP TestServer por caso** están declarados. El rate limiter del producto sigue activo; no se reproduce tráfico/TLS real ni identidad Windows de servicio en este archivo. La lectura bajo token estándar real ya está acreditada separadamente por F-05.04.

## Límites que deben seguir abiertos

No se ha construido un operador Restore distribuible, coordinador D2 de journal/fence/marcador DB/conciliación productiva, ni se ha probado aquí adopción, TLS de red, navegador, SCM, reboot, backup posterior/RTO, rotación, pérdida total o custodia externa real. No hay cambios de DB/almacenes instalados o de D/E; los clusters y artefactos de prueba son propios y privados.

Los siete huecos operativos documentados no desaparecen porque este test de integración pase. F-06/F-09/R-03/R-04 y la entrega conservan sus criterios. No se debe presentar como recuperable por el instalador una candidata que mantiene su guardia de rechazo. El nombre amigo del proyecto aislado no convierte las APIs internal en una función publicada.

## Trabajo y recomendación del revisor

Consulté `MfaPortableDatabaseRestoreTests` y sus símbolos `InitializeAsync/PrepareCandidate/Client/RestoreNewDatabase/RunPg/DisposeAsync`, `LabIdentity`, control de IP y casos HTTP/SQL; runner, auxiliares PG de cluster propio, manifiesto/recibos y criterio/hitos F-05. Se reutilizan dictámenes F-05.01–.04 y fuentes invariantes. **Ejecuté sólo lectura y conciliación documental de hashes/contadores**; mi auxiliar terminó0. No abrí contraseñas/claves/dumps/TRX/binlogs privados, no ejecuté MSBuild, PostgreSQL, herramienta criptográfica ni comandos de VM/servicios.

Recomiendo acreditar sólo **F-05.05 +1/2**:1607/84 = **19,13/100 del cierre restante**, sujeto al registro del coordinador, sin nuevo porcentaje global. Pueden marcarse `technical_tests_same_scope` e `independent_review_same_scope` con este alcance técnico explícito y estas evidencias. Mantener implementación operativa, integración en candidata objetivo y aceptación pendientes; no declarar F-05 como entrega/producto adoptados. Este revisor no modifica planes, pesos, contratos o código que aprueba.
