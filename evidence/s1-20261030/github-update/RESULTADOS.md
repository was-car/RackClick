# Publicación privada · resultados de selección y reproducción

30.10.2026. Implementación/ejecución del coordinador; revisión independiente en `docs/REVISION-PUBLICACION-30-10-2026.md`. Windows x64 real, PowerShell 5.1, SDK 10.0.401 y PostgreSQL 17.11. No se usaron VM, QA, bases existentes ni cuentas instaladas.

## Resultado final

| Comprobación | Resultado |
|---|---|
| Restore locked y publish desde el clon seleccionado | Código 0; servidor, cargador y frontend construidos. Binlogs privados. |
| Calidad servidor con PostgreSQL real | 378 Pass, 0 Fail, 3 omitidas: Docker y dos pruebas GUI sin navegador configurado. |
| Dominio | 76 Pass, salida 0. |
| Frontend completo `node --test tests/*.test.mjs` | 801 Pass, 0 Fail, 0 omitidas, tras las correcciones descritas abajo. |
| Cargador original, PostgreSQL real | 11 Pass: rechazo de actor/rol/revisión/destino, preservación de seguridad y atomicidad, entre sus escenarios. |
| Auxiliar demo | 6 Pass: pin/alcance de seed, entorno del hijo, salidas cambiadas/ausentes/extras y seed alterado. |
| `tools/start_demo.py --smoke` | Código 0; login, 10 clientes, 5408 puertos, frontend servido y carga committed. Proveedor MFA desactivado explícitamente. |
| Fuentes congeladas e índice Git | 221 archivos de producto exactos; 6 transformaciones de fixtures y seed contrastados también contra los blobs del índice: 228 comprobaciones. |
| Generador maestro, en workspace y clon | `--check`, código 0, sin cambiar ledger ni puntos. |
| Métrica de cierre, workspace | `tools/progress_report.py --check`, código 0; misma base 9,755952380952381/100. |
| Laboratorios creados por este lote | Detenidos al terminar; archivos conservados privados. No se borran bases. |

El escaneo Gitleaks 8.30.1 del historial y selección dio cero hallazgos tras sustituir las seis contraseñas constantes de fixtures. Se repite sobre la selección final antes del commit. Es un resultado de ese escáner/alcance, no una garantía de ausencia universal de secretos ni una nueva revisión completa de seguridad. Los archivos ZIP no se recorren por ese escaneo; el único ZIP seleccionado es la referencia RC9 conservada, no un nuevo instalador.

## Fallos y correcciones conservados

1. **Lanzador privado de regresión:** heredó `MfaKeyStore__Enabled=false` del auxiliar demo y anuló el JSON de una prueba de arranque. Se interrumpió sólo su árbol de procesos, se cerró su clúster y se conservó la salida. Se retiró esa variable del entorno del ensayo y se repitió la suite. No se modificó la expectativa ni producto.
2. **Dos constantes adicionales:** el primer escaneo staged señaló contraseñas de fixtures en `MfaActiveKeyTests.cs` y `MfaWindowsHostHttpTests.cs`. Se aplicó generación CSPRNG igual a las cuatro transformaciones anteriores; revisión independiente y hashes registrados, sin valores en el informe.
3. **Frontend amplio inicial:** 798 Pass y 3 Fail. El JSON del catálogo había cambiado a CRLF al clonar; se repuso el LF canónico y se fijó la conservación de bytes en `.gitattributes` para fuentes/fixtures/operadores. Otra prueba todavía exigía nueve capacidades: se sustituye por una lista literal cerrada de diez, incluida `templates.publish`, que ya existe en el contrato del dominio. La tercera necesitaba un ejecutable Git y un commit privados: se añadió la referencia histórica propia exacta con SHA256 y se conservó la misma aserción de evolución. Regresión final 801/801.

El revisor comprobó las tres causas y sus cambios: no se relajó una autorización ni se editaron los 221 archivos de producto. El test histórico ahora verifica el hash de su referencia antes de comparar.

## Comandos principales

Desde el clon seleccionado, con herramientas fijadas instaladas por `Initialize-Toolchain.ps1`:

```text
python -B tools/start_demo.py --build-only
python -B tools/start_demo.py --smoke
python -B -m unittest discover -s tools/tests -p test_source_demo.py -v
node --test tests/*.test.mjs                         (desde development/frontend)
python -B development/server/tests/test_rc9_demo_loader.py --publication <publicacion-nueva> --loader <cargador-compilado> --plan development/examples/demo-original.inventory.json -v
python -B tools/build_master_roadmap.py --check
python -B tools/progress_report.py --check           (workspace completo)
python -B tools/security/secret_scan.py scan --repo <clon-seleccionado> --mode all
```

El proyecto de calidad se restauró con `--locked-mode --source https://api.nuget.org/v3/index.json` y se ejecutó con `dotnet test -c Release --no-restore`, cada invocación MSBuild con binlog privado distinto. La conexión del administrador PostgreSQL del ensayo sólo se pasó por el entorno del hijo a un clúster nuevo, sin imprimirse ni incorporarse al repo. Los comandos exactos privados conservan las rutas de esa ejecución; no son prerrequisitos ocultos del manual.

## Límites

No se vuelve a acreditar la QA de Wascar, la instalación del servicio, MFA real bajo servicio ni la recuperación portable por estos ensayos. El instalador 10 no se redistribuye en GitHub, por la revisión de licencias abierta. `npm run test:build` conserva una referencia histórica a un archivo ausente; no se presenta como prueba pasada ni se usa en el recorrido documentado. No se activa CI ni se publica una release final. Índice de cierre sin incremento.
