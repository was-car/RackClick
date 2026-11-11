# Integración16 · dictamen independiente

04.11.2026. Revisor `revision_integracion16`, distinto de los autores de producto y del coordinador que ensambló la entrega. Propiedad de escritura exclusivamente `review/`. Estado Git concurrente inspeccionado antes de trabajar; no se sobrescribió trabajo ajeno.

**Favorable para incorporar el escritor F0401 aprobado a la candidata completa16 y marcar únicamente `F-04.integrated_current_candidate` cumplido.** No se detectan bloqueantes nuevos en este alcance. `target_acceptance` permanece pendiente. No autoriza publicación, instalación, adopción ni actualización de D. Mantiene **0 puntos nuevos** y **19,13/100 del índice de cierre restante**; no estima otro porcentaje global.

## Correspondencia comprobada

- Fuentes: 413 entradas del freeze45 contrastadas por bytes; sólo cambia `WindowsMfaKeyStoreWriter.cs`, de `ebbac2ef…` a la fuente aprobada `76e6dfc3364cb43260ef95e02bb88816702b21dc8f0230946645878d7c894d55`. Las otras412 coinciden. SQL y frontend fuente conservados; no se compiló el árbol concurrente.
- DLL final Release: `c05742f9079705c6cd97a1f97f89133183fc72e554dac0b2d52678c548921c2f`. Se recalcularon sus hashes en publicación, distribución, bundle y copia de pruebas; coinciden. Otras cuatro copias de aplicación/dependencias y la DLL de pruebas Release también coinciden con el recibo. No se afirma reproducibilidad binaria entre directorios distintos de compilación.
- Perfil nuevo `schema45-mfa-store-01`, esquema45: manifiesto `a2ec1c7d3570593297a63b672ee485489e49ed0658ff49f6d2ef585803f6a8af`; 55 archivos de servidor y18 de frontend. Se verificó el inventario exacto y todos sus hashes. Perfiles históricos43SQL/45SQL intactos. SQL45, frontend18, Npgsql/Otp.NET y sus metadatos de dependencias no cambian respecto a la entrega15.
- Bundle `b9336b50e4460166595c63d4e1631eb64e206214906b047e326939d62e9dc521`: 2018 entradas exactas, todas verificadas mediante lectura secuencial; aplicación73 y manifiesto fijados.
- Payload `90a8e17ecdd4ef6da8cf81cbfdfd72c462d29b8fa9c3efbd1b5326549a93f9d8`: 117 archivos exactos, incluidos116 declarados y `payload.json` cuyo SHA es `92079ab27d60635cb484be04ae314d995193731e24bba3af2439e411393e69f6`.
- Envoltorio `a862565da3e8351d734206b87886e4d8653b3cf4526661496012acc37901345a`: cinco archivos exactos; `PAQUETE.json` identifica edición16 y fija el payload, también fijado en `INICIAR.ps1`. Todos los hashes y tamaños coinciden.
- Se autenticó el payload15 anterior por SHA `59edfda54cac5e1951ca21c29926c34b4f5da9440393822ce1284aed176e364f`. Sus35 nombres de instalador se conservan: sólo cambian Install/SetupMfa y tres archivos con cuatro sustituciones de pin. Los26 operadores del bundle conservan sus nombres; sólo cambian NewRecovered, OfflineBundle y Test-ServerDistribution. Los38 archivos del servicio son idénticos. Los cuatro actualizadores43→45 ajenos a esta entrega están excluidos. Se verificaron asimismo las79 entradas seleccionadas del árbol privado de empaquetado.

## Fuentes y símbolos consultados

- `AGENTS.md`, `docs/BRIEFING-MAESTRO.md`, secciones vigentes de `CONTINUIDAD-CODEX.md`, `EQUIPO-Y-SKILLS.md`, `PROGRESO-GLOBAL.md`, `REVISION-PASOS-08-A-18.md`; revisiones F0401/F0404 y evidencias anteriores15. Se reutiliza su investigación primaria documentada, sin otra dependencia o instalación.
- `WindowsMfaKeyStoreWriter.cs`: `CreateCore`, `CreateStoreFromMaterial`, `StageMaterial`, `CreateExclusiveFile`, `TryCreateOwnedDirectory`, `CreationSecurity`, `Publish`, `PreservePublished`, `Discard`, `Failed`; correspondencia con la fuente aprobada y su revisión independiente anterior.
- `RackClick.SetupMfa.ps1`: `Get-SetupMfaApplicationSchema`, `Test-SetupMfaReadiness`, `Initialize-SetupMfaStore`. La versión procede del digest reconocido del bundle ya verificado; el recibo conserva ese entero. `Install-RackClickServer.ps1`: comprobación del recibo antes de crear el servicio, readiness con igualdad exacta del esquema y recibo de instalación.
- `New-RackClickRecoveredInstance.ps1`: `Get-RecoverySchemaTransition`, `Assert-RecoveryMfaMaterial`, llamada posterior a migración. Admite literalmente13/14/15/43→45 y current45; rechaza44, historias incompletas/duplicadas/desconocidas y downgrade. `recovery_mfa_envelope_required` permanece intacta.
- `build_server_distribution.py`: `load_profile`; `package_offline_bundle.py`: perfiles cerrados, `application_schema`, `collect_application`, licencias; `package_server_installer.py`: `checked_edition`, `build`; `package_clean_server_installer.py`: `clean_build`. Lectores nativos `RackClick.OfflineBundle.ps1`, `Test-ServerDistribution.ps1` y los tres archivos que fijan los cuatro pines. Perfiles43SQL/45SQL/45MFA y manual16.
- Pruebas `test_installer45_mfa_integration.py`, `test_distribution45_mfa.py`, `WindowsMfaKeyStoreCreationSecurityTests.cs`, fixture y guardia de ruta de `MfaPortableDatabaseRestoreTests.cs`; `run_new_restore45.py` y aserciones de `Invoke-SqlProtectedInstanceProbe.ps1`. Recibos públicos y manifiestos finales del lote. No se abrieron secretos, dumps, sobres, TRX, binlogs o rawlogs privados.

El índice MCP indicó cobertura parcial de los tres scripts PowerShell; se leyeron directamente las funciones, diferencias y llamadas afectadas, y se usó el parser real PS5.1. La ausencia de avisos del índice no se utilizó como prueba de corrección.

## Pruebas propias y recibos contrastados

| Origen | Ejecución o contraste real | Resultado y límite |
|---|---|---|
| Revisor | `C:/Python312/python.exe -B …/review/verify_integration16.py` | 29/29 focos:15 operadores y14 distribución; PowerShell5.1 real, sin instalador/DB. Además9 controles propios de fuente, artefactos, perfiles y pin nuevo→SetupMfa→readiness, incluyendo campos ausentes/nulos y esquema distinto. |
| Revisor | `…/verify_execution_receipts.py` | 5/5 controles de recibos, hashes reales de copias de DLL y derivación del fixture desde el original más un único cambio de línea. No vuelve a ejecutar DB/HTTP. |
| Revisor | `…/verify_chain16.py` | 11/11 controles: cinco pines de entrega,79 fuentes seleccionadas, inventarios y contenido completo de ZIPs,35/26/38 archivos, cuatro pines, licencias y límites del manual. Sin extracción/instalación ni cambios en ZIPs. |
| Coordinador, revisado | `HTTP-WRITER-RELEASE-R2.json` y `PUBLICACION-EN-PRUEBAS.json` | 16/16 PASS:8 creación segura y8 DB/restauración/TOTP/API con DLL Release exacta y proveedor Windows; TestServer. Primer8/16 conservado: el fixture rechazaba la raíz privada nueva. El diff cambia sólo aquella guardia a igualdad exacta; su hash derivado coincide. Producto y prueba original intactos. |
| Coordinador, revisado | `NEW-RESTORE45.json` y runner/aserciones | 14 llamadas positivas y dos rechazos esperados de destino existente;45→45 y43→45,20 filas, identidades nuevas, dos resumes por transición, permisos de catálogo/DDL, backup y material privado conservados. Cuatro clusters propios parados. Usa instancia protegida formato2 y loopback; no acredita formato3 ni asistente elevado. |
| Autores/coordinador, revisado | `REGRESION-EMPAQUETADO.txt`, `BUNDLE-NATIVO.json`, `PAYLOAD-NATIVO.json` | 43 pruebas de empaquetado previas PASS y verificadores nativos positivos; payload alterado/archivo extra rechazados y final restaurado válido. Son recibos contrastados, no nuevas ejecuciones del revisor. |

Los25 controles propios y29 focos no son puntos de producto ni pruebas únicas adicionales a sus categorías repetidas. La comprobación de integridad se repitió al fijar la cadena final; las29 pruebas sólo se ejecutaron una vez. El primer comprobador propio produjo un falso rechazo por stderr con el JSON esperado ya correcto; se preservó `COMPROBACION-INDEPENDIENTE-R1.json`, se silenció el progreso de PowerShell y se reutilizó la salida29/29. No cambió producto.

## Hallazgos por gravedad y límites

**Bloqueantes nuevos de esta integración: ninguno.** No queda defecto reproducible abierto en las fronteras modificadas que impida el hito de candidata integrada.

- **Alta, condición heredada de aceptación final:** no se ejecutaron instalación elevada, nueva cuenta/servicio SCM, HTTPS de red, reboot ni actualización de D con esta candidata. El hito `target_acceptance` y la QA final de Wascar permanecen abiertos. Los ensayos SQL/TestServer no sustituyen esos recorridos.
- **Alta, alcance operativo pendiente:** recuperaciónMFA por instalador, coordinador/fence/journal/disco–DB, rotación/emergencia y reconciliación conservan sus resultados pendientes. La guardia del operador rechaza factores incluso deshabilitados sin el recorrido de material integrado. Esta entrega no los acredita.
- **Media, redistribución pendiente:** se conservan runtime10.0.12, PG17.11, VC14.51 y avisos/licencias existentes. La nota del bundle mantiene explícitamente abiertas las obligaciones LGPL/redistribución y los derechos VC++; conservar avisos no cierra esas condiciones. No se autoriza redistribuir binarios o adoptar por este dictamen.
- **Media, límite heredado de rutas:** el fallo Win32206 del staging largo observado en18 sigue sin corrección de producto. El fixture usa una ruta corta delimitada; no demuestra soporte general de rutas largas.
- **Media, rollback operativo pendiente:** se conserva la entrega15 y el manual prohíbe arrancar DLL43 contra DB45 como reversión. En este lote no se ensayó reversión tras actividad posterior ni corte de energía; el rename del writer no acredita durabilidad/transacción disco–DB.

Este revisor realizó **0 compilaciones, instalaciones, operaciones DB/servicios/ACL/cuentas/MFA/VM y 0 commits/push**. D/E, sus datos y resultados manuales de Wascar quedan fuera del alcance. La edición16 integra un cambio ya acreditado, por lo que no cambia el índice ni concede aceptación del producto.

Evidencia reproducible propia: `COMPROBACION-INDEPENDIENTE.json`, `CONTRASTE-RECIBOS.json`, `CADENA-INDEPENDIENTE.json`, `FOCOS-INDEPENDIENTES.txt` y los tres auxiliares de lectura conservados en este directorio.
