# Distribución 14: decisiones y regresión independiente

23.10.2026 · Codex. Desarrollo local Windows; sin commits, staging, despliegue, cambios en QA ni acceso a la VM.

## Resultado

Las cinco decisiones solicitadas por Claude quedan resueltas en [DECISION-DISTRIBUCION14-CODEX.md](../../../docs/DECISION-DISTRIBUCION14-CODEX.md), en su mismo orden. Se fija una lista explícita; el perfil 14 tendrá su propio digest; se encarga un generador de producción; se construirá un bundle nuevo conservando los históricos; se actualizarán las pruebas activas sin reetiquetar fixtures históricos. Son decisiones técnicas del desarrollo autorizado, no adopción del producto.

[DISTRIBUCION14-PERFIL.json](../../../docs/DISTRIBUCION14-PERFIL.json) es una **definición**, sin digest de release ni paquete construido. Enumera 10 archivos de aplicación, 14 SQL y 18 frontend. `RackClick.Server.exe` queda fuera: el runtime existente lanza `dotnet` con `RackClick.Server.dll`. El EXE del host del servicio Windows es un componente diferente y sigue requerido. La futura publicación usará `UseAppHost=false` en un destino vacío; los archivos extra provocarán rechazo. No se ha borrado el apphost de la publicación aportada por Claude.

Los operadores y los empaquetadores requieren conciliación de todo el recorrido, incluida recuperación 13→14 con migración y grants reales. Un cambio aislado de esquema o digest no la acredita. La lista de rutas afectadas está en la decisión; Claude conserva la propiedad de su implementación. Codex no ha modificado esos archivos ni las fuentes MFA.

## Ensayo nuevo ejecutado

Se contrastaron los cuatro hashes comunicados con sus archivos locales. La candidata copiada desde `.local/m3-publish-2` tiene DLL SHA256 `f11a689e49dd507b79c4b9a43ce8670cd02fc46aa5325e58caa980fe959a1085`. Las identidades de las fuentes y de Otp.NET constan en [BASELINE.json](BASELINE.json). No se reconstruyó el producto ni se sustituyó su DLL.

Se compiló sólo el programa de comprobación con SDK 10.0.401, referencias directas a los binarios copiados y sin ProjectReference. El binlog y la salida de compilación permanecen privados en `.local`. Se ejecutó [run_expiry.py](run_expiry.py) con `--work` apuntando al snapshot privado `distribution14-decision-20261023-dba5f66fb6`, mediante `windows_job.run_isolated`; exit 0. Utiliza [M3ExpiryProbe.cs](M3ExpiryProbe.cs), un proveedor de claves sintético exclusivo del ensayo y una base nueva en un clúster PostgreSQL 17.11 independiente.

**11/11 casos pasan**, según [RESULTADOS.json](RESULTADOS.json): código válido; desafío consumido; CSRF ausente, incorrecto y correcto tras rechazos; reset administrativo real con auditoría; enrolamiento pendiente; revisión de política cambiada; y caducidad tras esperar los bloqueos de usuario, política y desafío. Los tres últimos registran que realmente hubo espera y que el desafío ya estaba caducado al liberar el bloqueo. Todos rechazan con `mfa_challenge_invalid`.

El bootstrap normal creó esquema 14 con historial `14|14`, sin aplicar 014 por un hook manual. Migración/bootstrap y ejecución usan identidades distintas; los grants de este ensayo proceden del helper del laboratorio, no del instalador. El clúster quedó detenido; la DLL y las dos fuentes seleccionadas conservan sus hashes. No se incorporan claves, contraseñas, configuraciones privadas, logs o binlogs a esta evidencia.

Revisión secuencial por `method_git_readonly23`: [REVISION.md](REVISION.md), dictamen favorable sin incoherencias materiales. Fue una revisión estática de documentos, inventarios, harness y resultados; no repitió las suites. `SHA256SUMS` identifica exclusivamente los documentos y archivos públicos de este cierre, sin sustituir el futuro manifiesto de distribución.

## Alcance y siguiente paso

La regresión independiente confirma la corrección de caducidad M3-04 en **esta DLL**. Son 11 casos propios; las 49 pruebas comunicadas por Claude no se presentan como ejecutadas por Codex. El ensayo invoca el almacén: no acredita HTTP, custodia definitiva, MFA completo, instalación limpia ni la GUI. La regresión C1 anterior corresponde a otra DLL y no se transfiere a ésta.

Siguiente: Claude construye el conjunto 14 coherente y entrega hashes, diff y resultados; Codex revisa esa candidata y ejecuta la regresión pertinente. Los ZIP M3 anteriores siguen sin ser aptos para instalar. Sin cambios visibles no se habilitan casos QA ni se regeneran guías. Los archivos compartidos de continuidad y CHANGELOG se mantienen bajo coordinación del bloque paralelo.

**Avance global aproximado: 78 %.** Se elimina una incertidumbre de caducidad y se concreta la construcción; siguen pendientes el paquete completo, su verificación, custodia MFA y QA/adopción final de Wascar.
