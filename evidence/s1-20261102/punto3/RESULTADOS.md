# Punto 3 · resultados de dos recorridos integrados

02.11.2026. Implementación: coordinador, p3_mfa_codes_backend y p3_json_export, con archivos asignados. Revisión por p3_independent_review (rackclick_security), distinta de los implementadores. Investigación previa en [INVESTIGACION-PREVIA](INVESTIGACION-PREVIA.md). [Manual y pendientes](../../../docs/PUNTO3-FUNCIONES-PENDIENTES.md).

## Resultado final

**Dos recorridos probados en desarrollo43; no cierre íntegro del punto3 ni instalación/adopción.** Códigos MFA propios de entrega única, canje restringido a enrolamiento nuevo y confirmación antes de API; exportación del inventario actual de un cliente con autorización, recibo, integridad y descarga. Se conservan catálogo506, montajes, Click-Click, política45 y administración anteriores. Sin SQL nuevo, versiones o dependencias nuevas.

| Verificación | Ejecución real | Resultado |
|---|---|---|
| Compilación | SDK10.0.401, Release, locked restore previo; binlogs privados | 0 errores, 0 advertencias |
| Pruebas nuevas MFA/OpenAPI | 28 casos C#, incluidos almacén con PostgreSQL17.11, HTTP y un recorrido Edge | 28 PASS |
| Regresión afectada | 76 casos históricos de almacén, enrolamiento, HTTP, cuenta y gracia45 | 76 PASS |
| Conjunto final | Una misma ejecución, binario final; 104 casos, sin omitidas | 104 PASS, 0 FAIL |
| Frontend | mfa-api, mfa-recovery e inventory-json-export, fuentes finales sin cambios posteriores | 26 Node PASS |
| JSON integrado | PostgreSQL17.11 nuevo, API/Edge, snapshot exacto, recibo histórico, segunda sesión/reinicio del proceso, concurrencia/rollback/permisos y límite4MiB | PASS |
| Revisión independiente | Nueve negativos Node propios y revisión de fuentes/contratos; salidas ajenas identificadas como tales | Dictamen y adendas en review/REVISION.md |

Los104 no son104 pruebas PostgreSQL distintas: incluyen pruebas puras y de HTTP/navegador. Los escenarios JSON tampoco se cuentan como una prueba nueva por cada aserción. Las repeticiones no aumentan el recuento de casos.

El navegador MFA demuestra primera generación privada, ausencia de valores en localStorage/sessionStorage, retirada de la sesión anterior, API401 después del canje y API200 sólo tras confirmar un secreto nuevo. El JSON descargado coincide con las ocho colecciones originales y conserva referencias/montajes; un lector sin exportación no obtiene el control ni el recibo. Se rechazaron Origin/CSRF/actor/revisión/capacidad incorrectos, revocación de permiso y recuperación por la ruta genérica. El fallo forzado de auditoría deja la transacción sin cambios. El historial conserva el mismo artefacto tras cambiar la fuente y reiniciar el host.

## Fallos conservados y corrección comprobada

1. `build01`: producto compiló, pero el test HTTP nuevo omitía CancellationToken en seis llamadas; xUnit1051 detuvo la compilación. Se pasaron los tokens del ejecutor sin desactivar el analizador. Build02 pasó.
2. Primera tanda nueva:27/27 y JSON/Edge pasaron con DLLfb83470d…, pero no ejercitaban OpenAPI. No se utilizan para afirmar que OpenAPI estuviera bien.
3. Regresión inicial:75 PASS y1 FAIL, GETopenapi devolvía503. La hipótesis inicial de permisos del fixture no resolvió el fallo: el foco siguió0 PASS/1 FAIL. Se retiró ese cambio de fixture y su fuente final coincide con la original. No se presenta esa hipótesis como causa demostrada ni como arreglo de producto.
4. **P3-R01**, hallado por el revisor: `Operation` omite `parameters` cuando no tiene parámetros comunes, y el recibo nuevo indexaba la clave ausente. Un test directo de `OpenApiDocument.Create` falló por KeyNotFoundException sobre DLLfb83470d…. Se inicializó la lista con el parámetro requestId requerido; el mismo test pasó sobre DLLb756c907…. No se relajó ningún control de seguridad ni el assert HTTP200.
5. Con la DLL corregida se repitió el conjunto104 y el JSON/Edge en PostgreSQL nuevos: todos pasaron. Los intentos previos, TRX/binlogs y diagnósticos completos permanecen privados en el directorio del lote. Las salidas sanitizadas iniciales fallidas también se conservan aquí.

## Identidad del resultado

| Artefacto | SHA256 |
|---|---|
| RackClick.Server.dll final | `b756c907eac9b949d14e70bea63f2f5fbc05b73cc6bc1cb1eccdf64e3d4d8ed3` |
| app.js final | `1ecb9bede2009177715a12ff0275e891f9f89475ca81560555c8f2abe9f85266` |
| Ledger conservado | `f2653b6a3fac5bbae3f2dd613f92c66a4004b8ce8192e6eb1b06f4493783fa3d` |
| ZIP revisión punto2 conservado | `af1c54b288ecbf5dd42ee6db138979254817a31665a2b36e5b642ed19f554808` |

`BUILD-SOURCES.json` identifica la base43 congelada y los overlays asignados; se contrastan con raíz y copia compilada. No se compila desde todo el árbol concurrente. Los artefactos nuevos están en `.local/` y no reemplazan la distribución/ZIP del punto2. No son un instalador ni una candidata para actualizar la VM.

## Comandos y entorno

En Windows, con las herramientas oficiales fijadas en `.local`, el coordinador ejecutó:

```powershell
C:/Python312/python.exe -X utf8 -B .local/build-punto3.py
C:/Python312/python.exe -X utf8 -B .local/resume-punto3.py
C:/Python312/python.exe -X utf8 -B .local/refresh-punto3.py build05-final
C:/Python312/python.exe -X utf8 -B .local/test-p3-final.py
```

Los auxiliares privados preservan la copia congelada y los logs. La última invocación inicia un clúster nuevo con `pg_support.Lab`, inyecta su conexión sólo en el entorno del hijo, usa `dotnet test -c Release --no-build --no-restore`, filtro explícito de las clases indicadas, TRX y binlog único. No reutiliza un clúster o servicio existente. Las pruebas C# están en `MfaRecoveryCodesTests.cs` y `MfaRecoveryHttpTests.cs`, con las clases históricas ya existentes. `RACKCLICK_TEST_PG_ADMIN` exige un laboratorio aislado; no apuntarlo al servidor instalado.

El escenario JSON reproducible usa el script versionable del producto, con los caminos de la copia identificada:

```powershell
C:/Python312/python.exe -X utf8 -B development/server/tests/test_inventory_json_export.py --dll <DLL-identificada> --frontend <frontend-identificado> --output <carpeta-nueva-bajo-.local> --browser
& '.local/node-v24.21.0-win-x64/node.exe' --test development/frontend/tests/mfa-api.test.mjs development/frontend/tests/mfa-recovery.test.mjs development/frontend/tests/inventory-json-export.test.mjs
& '.local/node-v24.21.0-win-x64/node.exe' --test evidence/s1-20261102/punto3/review/p3-independent-negative.test.mjs
```

No se anuncian pruebas desde un clon limpio sin herramientas/artefactos instalados. Para compilación desde fuentes rige el manual de desarrollo; los binlogs y las conexiones permanecen privados. Los dos clústeres finales y sus servidores se detuvieron; no hubo VM, QA, cuentas/servicios/DB existentes, HTTPS Windows o reinicio Windows. MFA usa clave sintética por DI en el host de prueba, no la custodia bajo la identidad efectiva del servicio.

## Límites y siguiente paso

- Códigos generados expresamente por la cuenta propia, no automáticamente al enrolar ni visibles para administradores ajenos. Un canje retira todo el conjunto, y después del factor nuevo hay que generar otro. Recuperación local/portable/rotación y custodia operativa del último administrador siguen pendientes.
- Un host que no puede arrancar con su almacén de claves no se recupera por esta ruta web. No se modifica ese comportamiento seguro.
- JSON incluye notas y propiedades arbitrarias; excluir tablas de seguridad no garantiza que una nota no contenga información sensible. La UI lo advierte.
- Límite4MiB/100.000 filas sin truncar, después del snapshot; no se afirma un límite de memoria/carga de PostgreSQL.
- Intención incierta JSON sólo mientras vive la vista; cambiar cliente o recargar pierde esa referencia local. Importación/merge/originalRC9 y backupPG/dashboard no están implementados por esta tanda.
- QA163/164 siguen planificadas hasta una candidata completa instalada. Se conservan162 casos anteriores, metadata y resultados de Wascar. No se acredita todo F-07, P-03 ni R-04.

Pendientes concretos en el manual y registro maestro. Catálogo506/506 (100% de esa selección); índice acreditado del cierre pendiente9,76/100 sin incremento automático. Sin porcentaje global nuevo, commits/push, publicación o limpieza.

## Revisión acotada de secretos

Gitleaks fijado inspeccionó59 archivos de esta tanda (fuentes/pruebas asignadas, manual y evidencia pública), sin escanear todo el historial ni publicar. Marcó8 coincidencias en BUILD-SOURCES.json: todas son SHA256 de archivos, y se verificaron contra sus bytes actuales. Se conservan las8 alertas y su clasificación; no se cambian reglas ni se anuncia salida limpia del escáner. No quedaron credenciales sin clasificar en este alcance. Ver SECRET-SCAN.json y SECRET-SCAN-CLASIFICACION.json. Los logs, conexiones y binlogs quedan privados.
