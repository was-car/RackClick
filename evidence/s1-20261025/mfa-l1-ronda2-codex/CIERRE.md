# MFA-L1 ronda 2 · revisión y ejecución independiente

25.10.2026. Implementación de Claude, ejecución de revisión por coordinador; revisión de seguridad distinta por `mfa_l1_security_review`. Probe adicional escrito por `mfa_l1_runtime_http_probe`; receta de laboratorio/CLI inspeccionada por `mfa_l1_pg_cli_explore`. No cambios de producto por estos revisores.

## Recibos

- `FUENTES-ENTREGADAS.json`:110 archivos congelados; ocho hashes coinciden con `referencia-entregada/HASHES.txt`. Restore locked y Release con SDK10.0.401 fijado, sin advertencias ni errores. Fuentes originales de entrega y salidas de Claude preservadas, sin convertirlas en ejecuciones de Codex.
- `INTENTO1-AUXILIAR.json`: build correcto, pero el driver esperaba el código inexistente recovery_request_invalid; el comando correctamente rechazó username_invalid y el driver paró antes de ejecutar C#. Corrección sólo del driver; referencia original conservada.
- `INTENTO2-REGRESION-Y-OBSERVADOR.json`:88 pruebas originales PASS, Docker omitida. El Fact adicional pasó el flujo, privilegios, cookies y consumo, pero falló su último observador pg_stat_activity. No se determina una causa específica de ese conteo0 ni se declara fallo del producto. Referencia del probe y resultado conservados.
- `RESULTADO-RUNTIME-Y-CLI.json`: repetición sólo del Fact adicional, **1PASS/0omitidas en19,031s**, PostgreSQL17.11. Identidades capturadas por triggers SECURITY INVOKER en la DB de laboratorio: session_user/current_user/base/application_name reales de las cinco escrituras confirmadas, no valores suministrados como testigo.3transiciones de factor y2sesiones. DDL rechazado42501. Cabeceras, hashes/TTL, sesión/CSRF nuevos y no acceso previo al API aprobados.
- CLI en el último recibo: bootstrap real,14 digests registrados, migrate inmutable, rechazos de segundo bootstrap/modos incompatibles/base vacía, recover sin usuario y origen inválido sin host. No acredita migración13→14 ni emergencia completa.
- DLL de revisión SHA256 `2d067c424f0e120b6b7671871cf704a013f9e4ff1591bff16f9ff36528d653a4`, idéntica antes y después de corregir sólo el probe. Segundo build incremental1,42s; no repetición de las88 pruebas originales. Procesos/laboratorios propios detenidos. Logs/TRX/binlogs completos privados,5binlogs.
- `REVISION-SEGURIDAD.md`: cuatro P2 corregidos, no P1/P2 nuevo;3focos de fuente/16aserciones propios, no runtime del revisor. Adenda contrasta recibos y el testigo de identidad. CompleteVerify no realiza upgrade de política tras el reloj. P3 de cleanup de entorno asignado a Claude, atributos de cookies complementados por probe.

## Reproducción

`run_review.py --work <copia-privada-con-source>` exige los110 hashes de `FUENTES-ENTREGADAS.json`, el probe y la toolchain local. Añade sólo ese test a la copia; crea PostgreSQL/base/roles nuevos y detiene su laboratorio. Con fuente exacta se ejecutan restore locked y el driver; `--probe-only` limita la repetición al test adicional. La copia privada debe reproducir el árbol `development/server`, con su Directory.Build.props/global.json y NuGet.Config oficial. No usar QA o bases existentes.

Para esta revisión, restore se hizo previamente y los builds del driver llevan --no-restore. `--reuse-build` está limitado al binario/probe originales del intento1; no es una aceptación de un binario cualquiera. Las referencias .cs conservadas junto al probe no se copian a la compilación, porque declaran la misma clase.

No es una distribución ni una reproducción del instalador08; la copia contiene fuentes de trabajo identificadas, incluidas otras piezas C2. No empaquetar esa DLL como candidata sin reconciliar su alcance. HTTP usa TestServer: no prueba TCP/TLS/cookies de navegador. Proveedor sintético exclusivo de DI de pruebas. Ninguna clave real/contraseña/token/URI secreta se publica.

## Cierre

Backend L1 conforme técnicamente; proveedor real, versión activa/anillo operativo, sobre portable, recuperación, UI y candidata final pendientes. Se acreditan sólo F-07.01/.03,1punto total, de557/84 a641/84: cierre del inventario pendiente7,63/100,19subpasos. No porcentaje global, sin pesos/alcance cambiados. F-07/F-12 no se cierran completos.

Actualizados continuidad/progreso/CHANGELOG y mensaje de siguiente lote. Catálogo/guías QA permanecen intactos: no MFA habilitado ni cambio visible disponible. C cerrado y apagado según Wascar. Sin consultas/operaciones VM, QA, instalaciones, paquetes, commits o push. Hashes vigentes de este cierre en su manifiesto; verificación y escaneo seleccionados se registran al finalizar.

Validación final de la métrica: `progress_report.py --write` y `--check` correctos, huella de alcance/pesos conservada. Codebase Memory refrescado:944archivos, huella en ENTORNO.json; no es una candidata compilada ni análisis exhaustivo. Gitleaks8.30.1 sobre el conjunto nuevo seleccionado devolvió17hallazgos brutos:15son SHA256 de fuentes recalculados y2constantes públicas de contraseñas ficticias de los tests temporales. Clasificación reproducible en clasificar_escaneo.py/CLASIFICACION-ESCANEO.json:0sin clasificar, sin reglas de supresión añadidas. No se declara escaneo limpio de todo el historial/repositorio; informe bruto redactado y binlogs permanecen privados.
