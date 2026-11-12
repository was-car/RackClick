# F-08.05 · cierre técnico conjunto, paso 28

11.11.2026. Estado: cerrado técnicamente con revisión independiente favorable y observación de automatización conservada. D/E preservadas, sin operaciones sobre VM, servicios instalados, cuentas o datos de Wascar. Sin commits, push o publicación.

## Investigación y reutilización

Se reutilizan la fuente, decisiones, cuatro matrices y revisiones de F-08.01–.04, y la investigación previa válida del mismo día: [codec/generación](../f08-01-generacion/RESULTADOS.md), [transacciones y bloqueos PG17](../f08-03-consumo/RESULTADOS.md). Referencias oficiales allí consultadas: .NET10 `RandomNumberGenerator.GetBytes`/`CryptographicOperations.FixedTimeEquals` y PostgreSQL17 transacciones/bloqueos. No se introduce algoritmo, biblioteca, dependencia, migración, instalador ni política nuevos. Reutilizar la implementación revisada permite comprobar el cierre sin repetir el trabajo de los cuatro pasos.

Se conservan 227 archivos de producto y cuatro archivos de prueba añadidos en esos pasos. El único cambio de producto entre F0803 y F0804 fue el guard D2 de `MfaAccountManagement.cs`; ya tiene reproducción roja y revisión distinta. **No hay cambios de producto en F0805.** Las DLL finales son las mismas de F0804, comprobadas antes y después de cada ejecución; no hubo build .NET nuevo.

## Ejecución nueva

- **Foco conjunto: 12/12 PASS, exit0, cero omitidas**, PostgreSQL17.11/esquema46. Windows, SDK10.0.401 fijado, `dotnet test -c Release --no-build --no-restore`, filtro de las cuatro clases nuevas más replay/finalidad/CSRF y rollback existentes. Un clúster nuevo; cierre en `finally`; salida/TRX/binlog únicos y privados. [FOCO.json](FOCO.json) conserva nombres y resultados sin valores secretos.
- Fuente/bases/hashes y reutilización: [FUENTES.json](FUENTES.json). Investigación, preparación y salida privada quedan bajo `.local/`; no se incorporan credenciales, semillas, códigos, cookies, DOM, TRX o binlogs a la evidencia pública.
- **Edge/Kestrel/PG actuales:** dashboard PASS (8 comprobaciones) y recuperación PASS (4) en ejecuciones distintas sobre la misma aplicación. El primer lanzamiento conjunto fue **1 PASS/1 FAIL, exit1**; la recuperación fue intermitente. [Los siete intentos](NAVEGADOR-INTENTOS.json) y la [observación detallada](OBSERVACION-NAVEGADOR.md) conservan todos los resultados. No hay cambio de producto ni causa/fix atribuidos; no se declara2/2 en una misma corrida ni batería íntegramente verde. [FRONTEND.json](FRONTEND.json) fija los18 artefactos generados y las fuentes originales.
- Los 68 Node y la regresión afectada del paso27 se reutilizan con su atribución y límites. Allí hubo 49 seleccionadas: 48 PASS y un navegador opcional omitido; el driver devolvió1 y la conciliación posterior fue sólo discovery, no otra ejecución. Este documento no lo transforma en49/49.

## Criterio y límites

[Matriz conjunta](MATRIZ-CIERRE.md) · [ficha28](../../../docs/PASO-028-CIERRE-CODIGOS-MFA.md) · [plan](../../../docs/PLAN-F0805-CIERRE-CODIGOS.md).

El canje consume el conjunto antiguo, revoca sesiones/desafíos y sólo abre un desafío nuevo de enrolamiento. Confirmar el autenticador nuevo precede a la sesión API, también para el global exento. La generación actual es expresa; no se afirma generación automática histórica ni custodia efectiva. Los códigos almacenados como hash no necesitan la clave TOTP para compararse, pero esta vía presupone host disponible, cuenta utilizable, contraseña y códigos válidos.

Integración de candidata Windows, SID efectivo, DPAPI/TLS instalados, custodia/aceptación de Wascar y emergencia de pérdida total F-09 siguen pendientes. Se conserva QA-163 y los otros174 casos, sin habilitarlos por el build de desarrollo ni sobrescribir resultados del navegador.

## Comandos y entorno

El driver privado `.local/f0805-53a7f4b2/run_focus.py` utiliza `pg_support.Lab` con clúster nuevo, propietario/migrador separados del rol de ejecución sin DDL, entorno hijo aislado y pines antes/después. Invocaciones: sin opciones para los12 casos; `--review` para los6 del revisor; `--browser` para ambos guiones y `--recovery-only` para diagnósticos posteriores de uno. `dotnet test` usa `-c Release --no-build --no-restore --filter <selección> --logger trx` y `-bl:<ruta privada única>-{}.binlog`. No se hace restore/build .NET en este paso.

El frontend usa el `node.exe`24.21.0 ya fijado y `node build.mjs` en copia privada con la referencia RC9 y los catálogos validados; buildexit0. Las dos pruebas C# lanzan Edge headless por CDP, perfil nuevo privado y Kestrel HTTP loopback explícito. El proveedor de clave se inyecta sólo en el host de pruebas; no hay HTTPS, servicio Windows o token efectivo acreditados por estos recorridos. Las herramientas/dependencias existentes no se actualizan.


## Revisión y conciliación

[Dictamen independiente](review/DICTAMEN.md): inspección del criterio completo y seis casos críticos propios PASS en otro clúster. La observación Edge queda explícita y no acredita aceptación nativa. Sólo F-08.05 suma1/2: 2027/84→2069/84=24,630952…/100 del cierre restante. Cuatro hitos técnicos se concilian con su evidencia; los dos operativos se preservan pending. No cambia ningún otro checkpoint, criterio, peso o resultado.
