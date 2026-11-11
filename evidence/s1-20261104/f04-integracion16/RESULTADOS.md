# F-04 · integración de la corrección en la candidata completa16

04.11.2026. Continuación autorizada de los pendientes de la revisión8–18. [Investigación previa y reparto](INVESTIGACION-Y-ALCANCE.md). No hay instalación, actualización, cuentas/servicios nuevos de Windows u operación sobre D/E.

## Resultado técnico

Se construye una candidata completa de **aplicación45 / edición16** con único delta C# del escritor aprobado `76e6dfc3364cb43260ef95e02bb88816702b21dc8f0230946645878d7c894d55`. Las413entradas base se contrastan con el freeze de15; no se compila el árbol concurrente. `package/DIFERENCIA-FUENTES.json` y `PUBLICACION-FUENTES.json` fijan las fuentes; buildRelease/publish y sus tres binlogs privados tienen resultado0, sin errores/advertencias. SDK10.0.401, runtime10.0.12, locks de dependencias sin cambios.

DLL Release: **`c05742f9079705c6cd97a1f97f89133183fc72e554dac0b2d52678c548921c2f`**. Frontend18, SQL45 y servicio38 se reutilizan y contrastan byte a byte. Perfil nuevo `schema45-mfa-store-01`, manifiesto **`a2ec1c7d3570593297a63b672ee485489e49ed0658ff49f6d2ef585803f6a8af`**, sin modificar los perfiles históricos43/45SQL.

## Código de operadores y empaquetado

- `RackClick.SetupMfa.ps1`: esquema15/43/45 desde el perfil cerrado del bundle ya verificado; el recibo de inicialización transporta ese esquema. No se altera la salida estricta del CLI de creación ni su elevación/confianza.
- `Install-RackClickServer.ps1`: valida el tipo/rango cerrado de ese recibo antes de crear el servicio; exige readiness del mismo esquema y lo conserva en la ficha. Una respuesta ready43 no acredita instalar45.
- `New-RackClickRecoveredInstance.ps1`: matriz cerrada de migración13/14/15/43→45 y actual45. La guardia MFA queda idéntica. No se admite44, secuencia rota o downgrade ni se regeneran factores.
- Perfil generador, colector y lectores nativos: registro paralelo del par digest/profileId nuevo con ruta y metadatos fijados. Conserva la familia interna `45-sql`, su protecciónSQL y26operadores. No admite hashes arbitrarios del llamador ni amplía esquemas por rango.
- Los cuatro pins nativos se ligan al bundle nuevo. Para payload/envoltorio se congela una selección de35scripts cuyo inventario procede del payload15 autenticado. Se excluyen explícitamente los cuatro actualizadores43→45 presentes en el árbol actual: no se necesitan para New16 y no se incorporan por una enumeración concurrente. Las copias congeladas incluyen los cambios aprobados de esta tanda.

Diffs, referencias anteriores y huellas de los tres operadores están en `operadores/`; los registros de perfil/pines y selección congelada en `package/`. No se cambia el C# compartido, SQL, frontend, servicio ni dependencias.

## Entrega privada fijada

| Artefacto | SHA256 |
|---|---|
| Bundle45-16,2018entradas | `b9336b50e4460166595c63d4e1631eb64e206214906b047e326939d62e9dc521` |
| Payload16,117archivos incluyendo su manifiesto | `90a8e17ecdd4ef6da8cf81cbfdfd72c462d29b8fa9c3efbd1b5326549a93f9d8` |
| Envoltorio16 completo | `a862565da3e8351d734206b87886e4d8653b3cf4526661496012acc37901345a` |
| `payload.json`,116archivos declarados | `92079ab27d60635cb484be04ae314d995193731e24bba3af2439e411393e69f6` |

Rutas/tamaños en [ENTREGA.json](package/ENTREGA.json). No se publica ni adopta; derechos generales de redistribución siguen abiertos.

## Pruebas ejecutadas realmente

1. **Empaquetado43/45/45MFA:43/43PASS**, sin omitir. Negativos de perfil/ruta/pin/SQL/DLL/metadata y compatibilidad histórica; `package/REGRESION-EMPAQUETADO.txt`.
2. **Operadores:15/15PASS** en Windows PowerShell5.1, con rojo anterior conservado. Prueban versión derivada, readiness exacta/tipos/estado, matriz de Restore, guardia MFA intacta y parser; sin ejecutar asistente elevado. `operadores/ROJO-01.txt`, `VERDE-01.txt`, `HASHES-FINALES.json`.
3. **DLL Release real del paquete:16/16PASS** en WindowsPG17.11: ocho pruebas existentes de creación segura y ocho de DB restaurada/login MFA. Nuevo proyecto de pruebas privado referencia la publicación, no recompila producto. Las cinco copias de DLL/deps en el test coinciden con la publicación; `PUBLICACION-EN-PRUEBAS.json`. Program/WindowsProvider reales y TestServer, confianza/identidad LAB explícitas; no TLS, SCM o instalación. Los gates previos de recuperación siguen en el fixture.
4. **Stage/New/RestoreSQL reales:** Stage43 y45; New45 protegido, Restore45→45 y43→45 con identidades distintas y veinte filas sintéticas conservadas por recorrido; dos reanudaciones por destino, runtime sin DDL y permisos de catálogo comprobados, backups invariantes. Dos destinos existentes rechazados sin variar su material privado. **16llamadas:14positivas y2rechazos previstos**, cuatro clústeres parados. `NEW-RESTORE45.json`. El seeding usa formato2 protegido con propietario para mantenimiento, no formato3 de la instalación nativa ni servicioWindows.
5. **Integridad final nativa:** `BUNDLE-NATIVO.json` devuelve bundle_verified2018; `PAYLOAD-NATIVO.json` valida117, rechaza extra/alteración y vuelve a validar después de restaurar únicamente el archivo propio de prueba. `verify_package16.py` contrasta73miembros de aplicación contra la distribución,26operadores del bundle y seis scripts/pins del payload contra fuentes finales, además de los hashes de cada miembro y la cadena PAQUETE→payload→bundle.

Los resultados repetidos por revisión no se añaden como casos únicos. No se repiten los195casos de F0401 por inercia: el delta es el mismo writer revisado y se prueba ahora en la DLL final con los ocho controles afectados y su nueva integración.

## Incidencias conservadas y límites

- Primer ensayo de la DLL: ocho pruebas de creación pasan y ocho de integración fallan durante la inicialización compartida `private_fixture`. El test histórico sólo acepta su antiguo prefijo `.local/f0505-integration-`; la nueva raíz exclusiva se rechazaba antes del esquema/HTTP. Se cambia **una línea de la copia privada**, a igualdad exacta con la nueva raíz, sin editar el test original o relajar seguridad productiva. Recibo inicial conservado en `HTTP-WRITER-RELEASE.json`; diff/identidad en `DIFF-FIXTURE-RAIZ.diff` y `ADAPTACION-FIXTURE-RELEASE.json`; corrida final R2 conserva16/16. Ambos clústeres propios de estas corridas se detuvieron.
- Los comprobadores del coordinador corrigieron supuestos propios: `edition` pertenece a PAQUETE y no al manifiesto interno cerrado;117incluye `payload.json`; el verificador nativo exige ruta absoluta. Fueron errores de invocación/inspección, no cambios de producto o recompilaciones de la candidata.
- No se acredita New/Restore elevado, formatoSQL mínimo3, SID/SCM/HTTPS/reinicio de16, actualización45→45 de D, durabilidad frente a corte o adopción. La guardia `recovery_mfa_envelope_required` permanece vigente.
- RecuperaciónMFA operativa, coordinador D2/fence/journal/marcadorDB, exportación concurrente, retención/rotación/emergencia, aceptación/custodia externa y recorrido R04 siguen pendientes. La excepción de laboratorio no autoriza a servir una DB/material adoptados sin esas garantías.
- No hay operaciones VM, cambios de D/E, nuevos usuarios/servicios locales, commits/push o publicación. Datos de prueba, dumps, sobres, secretos, rawlogs, TRX y binlogs permanecen en `.local/`; las evidencias públicas no contienen sus valores.

## Revisión y contabilidad

[Dictamen independiente](review/DICTAMEN.md), con focos propios y límites de lo que el revisor ejecutó. Tras dictamen favorable, se puede acreditar únicamente el hito de **integración F04 en candidata completa**, manteniendo `target_acceptance` pendiente. No se vuelve a acreditar un checkpoint cerrado ni se cierra F05/F06/R04.

El índice permanece **1607/84=19,13/100 del cierre restante**,41done/237pending/2in_progress;53resultados/280checkpoints/268números y huella/pesos/criterios intactos. **0puntos añadidos**, sin porcentaje global nuevo. El próximo trabajo operativo sigue necesitando coordinador/RestoreMFA y ensayo nativo de una candidata fijada, sin tocar D por conveniencia.


## Cierre documental retomado · 09.11.2026

Verificación actual de conservación de fuentes/artefactos/pins/sello independiente y tres verificadores nativos de integridad, sin ejecutar suites de producto/builds/DB/VM. Se preservan la fecha y resultados04.11. Registro, escaneo y sello final del bloque completados en [cierre-20261109/](cierre-20261109/RESULTADOS.md). La misma combinación revisada permanece válida para su alcance técnico; no se declara instalación nativa ni RestoreMFAoperativo. Ledger/hito y crédito se mantienen sin cambios.
