# Paso18 · cierre técnico de la recuperación portable MFA

03.11.2026. **F-05.05 cerrado técnicamente:8/8 PASS, sin omisiones, y [revisión independiente favorable](review/DICTAMEN-F0505.md).** Este resultado no adopta una instalación ni cierra el Restore operativo completo.

Coordinador/root: revisión del estado, investigación, runner PostgreSQL, tres ejecuciones aisladas y conciliación. Implementador `rackclick_backend`: nuevo test/proyecto privado, compilaciones y sonda de rutas sinPG. Revisor distinto `rackclick_security`: criterio, fuente, pins y resultados; sus operaciones están delimitadas en su dictamen. D/E no reciben comandos de invitado, SQL o autenticación ni cambios de potencia/snapshot.

## Qué cambió y por qué

- Nuevo `development/server/tests/RackClick.Quality.Tests/MfaPortableDatabaseRestoreTests.cs`: faltaba unir DB de aplicación restaurada y factor conservado con el pipeline de login. Se reutilizan recuperación/DPAPI/proveedor/crypto/Program revisados, sin stubs de claves ni de TOTP.
- Nuevo `tools/tests/run_mfa_portable_database_restore.py`: sólo crea un cluster privado nuevo en127.0.0.1, proporciona credenciales de laboratorio al runner sin publicarlas y para exclusivamente ese cluster al finalizar. No acepta una DB/VM existente como destino. Guard de ruta externa al proyecto privado comprobado en [CONTROL-RUNNER](CONTROL-RUNNER.json).
- No se modificaron fuentes de producto, migraciones, csproj/locks originales, GUI, instaladores o paquetes de usuario. No hay commits, push o publicación. Las pruebas originales y los codecs no se reescriben ni se repiten para sumar resultados.

## Ejecución y trazabilidad

Windows LEAO, SDK10.0.401, NETCore/ASPNet10.0.12 exactos, PostgreSQL17.11 local nuevo. DLL de producto **Debug F-04.01** SHA256`cd3ccf922c7830007d3a82277729c372242f5f67ca1f4d032269d4093b0b7bcd`, fuente con esquema45. Test Release con apphost privado exigido por xUnit; no se reconstruye el producto. [Manifiesto final](implementacion/HARNESS-FREEZE6-PREVIO-PG.json) liga nueve archivos y45SQL exactos a la copia revisada; no es una candidata Windows completa ni una distribución nueva.

Fuente del test: `b6bd93e3a7cf36de94828405210cc0d4f7beef0008221e03fd0458ff9e9cd35a`. DLL del test: `d29dab229ac0859299bfd23bd52f2059aaa0e64c0b923865e9108cea7abab267`. Build final0errores/advertencias. Cada restore/build/test MSBuild conserva binlog propio privado. Logs/TRX/credenciales/dumps/sobres/DPAPI permanecen privados; no se añaden a Git ni al informe público.

Se ejecutó:

```powershell
C:/Python312/python.exe -B tools/tests/run_mfa_portable_database_restore.py `
  --project <proyecto-privado-fijado> `
  --fixture-root <raiz-privada-exclusiva> `
  --result evidence/s1-20261103/f05-05-cierre/COORDINACION-PG-R3.json
```

El runner usa `dotnet test --no-build --no-restore -c Release`, filtro de la nueva clase, TRX y binlog privado único. Las tres variables de fixture son sólo de laboratorio; no se proporcionan credenciales del usuario. El entorno del hijo elimina hooks/profilers y variables previas de conexión/configuración antes de añadir los valores fijados. [Primera comprobación de nombres](ENV-PRIMER-ENSAYO.json): no había variables peligrosas heredadas; el endurecimiento posterior del runner queda separado del fallo funcional.

[Corrida final](COORDINACION-PG-R3.json):8ejecutados/8PASS/0FAIL/0omisiones; binlog producido y propio cluster parado. [Resumen del fixture](implementacion/RESUMEN-SANITIZADO-CORRIDA3.json), [matriz de cierre](MATRIZ-CIERRE.md) y [detalle de implementación](implementacion/RESULTADOS.md) describen DB restaurada, igualdad de filas, roles, factores1/7, revocación y login/TOTP/CSRF/negativos. El source DB y sus archivos/anillo/sobres se contrastan sin cambios tras cada caso; los datos parciales propios se conservan privados.

## Intentos previos conservados

1. [Primera corrida](COORDINACION-PG.json): un fallo común de inicialización del fixture bloqueó los ocho casos antes de llegar a HTTP. No fueron ocho defectos funcionales. La ruta de staging266caracteres falló con Win32206 y la de258pasó con la misma DLL en [sonda sinPG](implementacion/SONDA-LONGITUD-SIN-PG.json). Se abrevia sólo el candidato del fixture; no se toca Winreg/Win32 del producto ni se afirma soporte universal de rutas largas.
2. [Segunda corrida](COORDINACION-PG-R2.json):3PASS/5FAIL. Cuatro fallos por content root no resuelto en el proyecto privado de referenciasDLL, cuyo manifiesto MVC generado estaba vacío; se fija la variable oficial de content root sólo durante el fixture y se restaura en finally. El otro caso rechazaba correctamente AAD mediante `AuthenticationTagMismatchException`; una aserción excesivamente exacta se ajusta a la familia `CryptographicException`, conservando rechazo, origen invariable y directorio ausente.
3. Tercera corrida sobre otro cluster nuevo y Freeze6:8/8PASS. No se mezclan resultados, se reconstruyen recibos ni se reutiliza una DB de la corrida fallida. Los tres clusters propios quedaron parados. Los controles adicionales previos a PG reforzaron transacción única del restore, permisos y comparación global de filas; los manifiestos anteriores se conservan.

## Qué acredita y qué conserva pendiente

La [investigación](INVESTIGACION-Y-DECISION.md) y el [umbral independiente](review/UMBRAL-F0505.md) distinguen prueba técnica y adopción. TestServer usa endpoints/middleware/almacenes reales pero no una conexión HTTP/TLS de red o servicio Windows; la confianza Windows LAB se declara, sin atribuirle el token real de F-05.04. Los gates de versión/AAD/material del fixture no implementan el operador/fence de producción.

Se acredita sólo F-05.05 con su peso1/2 después del dictamen. `technical_tests_same_scope` e `independent_review_same_scope` se concilian en el alcance técnico. `implementation_complete`, `integrated_current_candidate` y `target_acceptance` mantienen la operación/entrega pendientes. F-06/F-09/R-04, instalador/CLI/coordinadorD2/journal/fence/caídas/aceptación no se cierran por este ensayo. D y la MFA de Wascar se conservan.

## Registro y continuidad

Sólo el checkpoint F-05.05 pasa de pending a done:1565/84→**1607/84=19,13/100** del cierre restante.41done/237pending/2in_progress,53resultados/280checkpoints/268números, sin alterar baselinev3/huella/criterios/pesos u otros52resultados. Los dos hitos técnicos/revisión se actualizan con alcance expreso; los demás permanecen como estaban. [Verificación de cierre](VERIFICACION-CIERRE.json).

Plan, registro maestro, continuidad y changelog actualizados; tres generadores en modo write/check correctos. No es porcentaje global nuevo del producto ni aceptación final. Sigue **19/F-06.01**, conciliación de fases de rotación/coherencia antes de la implementación. Los intentos previos y el sello de130archivos del paso17 se preservan mediante referencias actuales o snapshots previos.
