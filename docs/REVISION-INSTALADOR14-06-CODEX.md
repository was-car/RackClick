# Revisión de la candidata interna 06 del instalador

25.10.2026. Implementación de Claude; revisión de Codex y revisión focal distinta por `bundle02_native_review`. Sin cambios de producto, commits, QA ni VM. **Cadena de archivos conforme; candidata interna de ensayo, pendiente de dos correcciones antes de promoverla.**

## Dictamen

La retirada de la guardia de esquema14 del **bundle14-07 identificado** es válida para permitir ensayos internos de preparación New/Restore. Codex ejecutó ambos mediante el operador real, en destinos privados nuevos, con resultado `installation_prepared`. Esa retirada no acredita el instalador elevado ni autoriza a presentar06 como entrega apta para la VM QA. Los bundles01–06 permanecen históricos. El perfil registra07 como interno con hallazgos abiertos, conservando los objetos anteriores y `installationApproved=false`/`productAdopted=false`.

Persisten dos asuntos concretos:

1. **D14-07, P2, runtime de parada:** el payload contiene `Invoke-RackClickServerRuntime.ps1` con SHA256 `29c55fd16eef55aab2e8d1640257fc5990656f195fcec0915faf7e6645ce94b9`. Es exactamente el original defectuoso de la [revisión de parada](HALLAZGO-D14-07-PARADA-RUNTIME.md). La propuesta atómica0752db sigue sólo en copia privada. Integrar y repetir sus focos y ciclo de vida antes de promover el instalador. No se repitió aquí ese fallo ya demostrado con los mismos bytes.
2. **P2 del generador, parámetro `edition`:** `clean_build` concatena el valor sin validarlo en los nombres ZIP. El revisor generó cinco entradas con `../` usando `edition='06/../../escape'`. El foco ejecuta el empaquetador exterior real con un payload interno de fixture; no es una instalación ni una reproducción completa del empaquetador interior. **La06 literal revisada no contiene rutas inseguras.** Validar edición antes de invocar `build` o crear salidas, tanto en `build` como en `clean_build`; conservar las comprobaciones actuales de rutas, hashes y destinos nuevos.

Además, «valores por defecto05» no equivale a «bytes históricos05»: los generadores leen Setup/documentos vivos con pins06. Corregir esa afirmación y rechazar temprano combinaciones incoherentes, o seleccionar fuentes congeladas coherentes. Conservar los ZIP05 originales; no es necesario reconstruirlos desde fuentes06 para terminar esta tanda.

## Comprobaciones ejecutadas aquí

Windows11 local, WinPS5.1, PostgreSQL17.11 y .NET10.0.12 incluidos en el bundle. Sin builds, descargas ni instalación de prerrequisitos.

| Verificación propia | Resultado |
|---|---|
| Sumas de entrega y snapshots | 7/7 digests coinciden;703 archivos declarados de cada S1/S2/S3 comprobados. |
| ZIPs y manifiestos | Bundle1986 entradas/1985 registros; payload114, envoltorio5 e IP65. Inventarios completos, hashes/tamaños verificados, sin duplicados por mayúsculas, symlinks o rutas inseguras en estos archivos. |
| Aplicación y operadores | 45 archivos de `application/` idénticos a candidata03:42 de producto y3 de metadatos.25 operadores idénticos entre bundle, payload yS2. Aplicación e9c58c0c…/DLL19c94d4e… conservada; no incorporación de C2. |
| Cadena | Bundle6d5a… dentro del payload6994…; `payload.json`31a4… y sus113 miembros; envoltoriod6b6… contiene ese payload; CMDIPb1a9… verifica el mismo31a4…. |
| Seis pruebas específicas de Claude repetidas | **6/6 PASS, sin omisiones.** No se repitió la suite81 completa. |
| Lector nativo del bundle | `bundle_verified`, exit0; digest falso rechazado `archive_hash_mismatch`, exit2. |
| `Install-RackClickOfflineBundle`, New | **`installation_prepared`, exit0**, recibo/hash/estado preparados y esquema14 verificados. Destino nuevo privado. |
| Mismo operador, Restore14→14 | **`installation_prepared`, exit0**, recibo/hash/estado preparados y esquema14 verificados. Backup sintético propio de laboratorio anterior; destino nuevo. |

El recorrido independiente de archivo y preparación finalizó exit0 en152,12s, entradas intactas, sin pidfiles y puertos cerrados. `crtDecision=reuse`: no se solicitó `-InstallPrerequisites`. Los recibos de este operador son reales, **no los fixtures sintéticos del ensayo de runtime anterior**.

El operador offline puede ensayarse así sin instalar servicios: crea sólo su instalación privada y el PostgreSQL propio que después detiene. No se ejecutaron `Install-RackClickServer`, `INICIAR`, SCM, nuevas cuentas Windows, firewall, almacenes de confianza ni reinicio. Por ello, «ninguna instalación» sigue siendo cierto para el instalador de servicios, pero **ya no es cierto para la ejecución del operador privado New/Restore**: esta revisión aporta esa prueba nueva.

[Resultados estructurados y comandos](../evidence/s1-20261025/instalador14-06-codex/CIERRE.md), [revisión focal de fuentes/generador](../evidence/s1-20261025/instalador14-06-codex/REVISION-FUENTES.md).

## Siguiente tanda para Claude

Integrar D14-07 y validar `edition`; ejecutar sólo los focos afectados y los negativos de edición antes de generar salidas. Registrar correctamente los límites de05. Generar **nueva edición** de payload/envoltorio/CMD y sus pins sin sobrescribir06. El bundle14-07 puede reutilizarse si sus25 operadores y su contenido no cambian: el runtime de parada está fuera de ese bundle, en el payload. Si cambia contenido del bundle, generar otro con nombre y digest nuevos.

Después, revisión de esos artefactos y ensayo en **otra VM Windows Server limpia**: New/Restore, cuenta/servicio, HTTPS, backup y reinicio real. No cambiar ahora la VM QA. La reparación de red y `prepare_server_step2.py` históricos deben quedar identificados como05; no exigir su modernización para probar esta corrección, ni ofrecerlos como herramientas06.

La candidata depende aún de artefactos `.local`; aprovisionamiento reproducible, derechos de redistribución, HTTP MFA/proveedor de laboratorio, decisión D2 y aceptación final permanecen pendientes. **Avance global aproximado:78 %, sin incremento automático.**
