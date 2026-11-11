# Restore C · evidencia de Codex

25.10.2026. Instalación realizada por Claude/Wascar; comprobación posterior del coordinador, sin repetir instalación, reinicio o Restore. Revisión distinta en `REVISION-INDEPENDIENTE.md` (12 aserciones de consistencia sobre los cuatro archivos públicos de Claude).

## Mediciones nuevas

- `COMPROBACION-C-API.json` y su `.ps1`: lectura del recibo, comparación de hoja/preparación/red, CRT, salud HTTPS, login y cliente restaurado, logout. El script no contiene claves: lee la credencial administrativa preexistente sólo en memoria del invitado. La respuesta publicada no incluye contraseña, cookie, CSRF ni cuerpo de login. Login/logout sí escriben autenticación; `productDataWrites=0` se refiere a datos de clientes/inventario.
- `EXPORT-ADICIONAL-C.json` y su `.ps1`: hash del postboot y de la exportación adicional, tamaño/metadatos; sin abrir el dump. Decisión: conservarla privada sin borrar ni mover.
- `LECTURA-INICIAL-PARCIAL-C.json`: intento anterior detenido en acceso a runtime privado, antes de login. Conservado; no acredita medición de versiones ni ausencia de dependencias.
- `CONTRASTE-COORDINADOR.json`: 14 aserciones PASS sobre las dos mediciones nuevas, incluidas identidad, arranque, datos, sesión cerrada, entrada A07, red y límites registrados. No ejecuta otras llamadas al invitado.

`tools/progress_report.py --write` y `--check`: PASS, 5,50/100 del pendiente, alcance/pesos congelados. Gitleaks8.30.1 sobre los archivos públicos nuevos del bloque: exit0, cero hallazgos; informe del escáner privado bajo `.local/w02/manual`. No es un escaneo de todo el proyecto o de su historial.

Sondas ejecutadas en Windows PowerShell del invitado con `vmrun runProgramInGuest`, salida a archivo propio en `C:\W02\informes`, luego `copyFileFromGuestToHost`. Scripts largos se copiaron como archivos antes de ejecutarlos. Dos intentos de pasar la sonda completa por EncodedCommand fueron rechazados por VMware (`Buffer too small`, exit4294967295), antes de esta vía con archivo; no son fallos del producto ni ejecuciones del instalador. Credencial Windows leída del archivo privado local; nunca literal en los scripts ni publicada. No se cambiaron ACL ni servicios; se dejaron los informes y sondas de este bloque en la carpeta de informes del invitado.

## Resultado y límites

PASS: servicio Running, postboot mismo UUID/boot, TLS con confianza Windows normal, ready/esquema14, login200, coincidencia exacta «Cliente prueba W02», logout204, hashes de entrada A07 y firewall concordantes. Visual del navegador no ejecutada. No se midió el total de clientes; el campo null del informe no representa un recuento.

No cerrado: fase04/exit del auxiliar ausente; Reconcile unknown; igualdad literal de Systemhaus no lograda; versiones reales .NET/PG no medidas por la sonda al denegarse acceso. Backup adicional declara PG17.11 tras el control SQL de versión del operador: evidencia indirecta, sin nueva consulta SQL del coordinador. El fallo postboot inicial sigue conservado, sin causa ni duración de petición inferidas.

W-02.02 en curso, crédito nuevo0. W-02=0,50/2,50; cierre pendiente5,50/100,13/280subpasos,1/50resultados. No es porcentaje de producto. Sin cambios de código de producto, build, paquetes, A/B/QA ni commits.

[Dictamen](../../../docs/REVISION-W02-RESTORE-C-CODEX.md), [coordinación Claude](../../../docs/MENSAJE-PARA-CLAUDE-C-RESTORE-REVISION-25-10-2026.md). `SHA256SUMS.txt` cubre los archivos del bloque; los hashes históricos de Claude se contrastan, no se presentan como actualizados después de una edición.
