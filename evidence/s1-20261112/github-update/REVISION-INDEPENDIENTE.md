# Revisión independiente de publicación privada · fuentes48

12.11.2026 · Revisor separado del preparador. Alcance: selección para `was-car/RackClick`, desde `.local/github-update-20261112/repository`, base `fd43fc41a1738baa844aa6d300e0266fc585da36`. Sin cambios de producto, commits, push, instalación ni operaciones VM por este revisor.

## Dictamen final de revisión

**Favorable para el push privado autorizado**, con los controles mecánicos previos al push descritos abajo. No quedan hallazgos de contenido bloqueantes en la selección revisada. No equivale a adopción ni aceptación productiva, cambio de visibilidad o autorización de despliegue. No se incorpora un instalador binario nuevo ni una dependencia nueva.

**Adenda del gate de staging:** el inventario definitivo es de **2438 archivos**, 207 más que el snapshot2231 descrito abajo. Son exactamente 202 referencias históricas de `reference-additions.json` y cinco evidencias públicas de este lote, ignoradas por la política Git efectiva del clon. Contrasté la diferencia de conjuntos: ninguna ruta nueva de producto, tools, datos, binarios o contenido ajeno; ninguna referencia queda fuera. La primera revisión validó los bytes de las 300 referencias, pero fue demasiado amplia al atribuirles a todas cobertura del escaneo2231: estas 202 se incorporan al escaneo completo2438. La nueva sonda comprueba expresamente pertenencia a selección y entrada del escáner, además de hashes.

`stage.py` usa `git --literal-pathspecs add -f` únicamente con la lista NUL de `publication-files.json`, sin carpetas ni `-A`. Antes comprueba los hashes físicos y después exige igualdad exacta entre manifiesto e índice, sólo modos regulares y SHA256 de todos los blobs. Revisé ese mecanismo: el uso acotado de `-f` es apto para estas rutas ya revisadas; no autoriza incorporar otros archivos ignorados.

El snapshot contrastado contiene **2231 archivos / 124.511.190 bytes**, con 426 fuentes de producto. Después se ajustó la conservación de bytes de checkout, según el párrafo siguiente; la cifra de bytes citada identifica el snapshot anterior a ese ajuste. Revisé `/docs/** -text` añadido a `.gitattributes`: conserva los documentos fijados por hash; `git check-attr` devuelve `text: unset` en los tres documentos representativos consultados y `git -c core.whitespace=cr-at-eol diff --check` termina con código 0.

Revisé también `preserve_base_bytes.py`: sólo restaura un archivo previamente publicado cuando la diferencia es exclusivamente expansión CRLF y el blobHEAD coincide con su pin histórico. Ejecuté `review/check_preserved_bytes.py` mediante lectura por lotes de `git cat-file`: **144/144 archivos actuales coinciden byte a byte con HEAD y con el manifiesto publicado previo**, sin duplicados, 135 documentos y 9 archivos de configuración/raíz. Ninguno pertenece a producto, herramientas, catálogo, fixtures, referencia o Demo50. Se evita así introducir cambios artificiales de checkout; `checkoutBytePolicy` registra la operación. No se cambiaron contenidos lógicos ni manual18 por este paso.

Antes del push corresponde incorporar esta versión del informe y los resúmenes finales, regenerar los manifiestos para incluir los ajustes de bytes/atributos, repetir el escaneo de esa selección y conservar el punto de retorno privado. La comprobación final debe dar inventario/hashes exactos y ninguna coincidencia sin resolver. Estos pasos no autorizan ampliar fuentes, producto ni instalaciones; cualquier diferencia adicional exige revisión propia. Después de restaurar los 144 archivos repetí la sonda general: las 2231 rutas vuelven a coincidir con selección y hashes, conservando 426 fuentes, seis transformaciones, 62Demo50 y los digests SQL.

## Hallazgos comunicados

| Gravedad | Hallazgo y efecto | Estado |
|---|---|---|
| Media | Las tres guías de inicio anunciaban esquema45/03.11 como estado actual, frente al README48. Sus límites MFA requerían distinguir componentes técnicos implementados de aceptación final. | Resuelto y comprobado: esquema48/12.11 y límites MFA actuales en EN/DE/ES. |
| Media | `docs/INSTALACION18-ESTADO-Y-ACCESO.md` ofrecía un enlace a ZIP bajo `.local`, excluido del repositorio, junto a rutas de CA particular. | Resuelto y comprobado: enlace ZIP sustituido por texto de entrega local y adenda expresa sobre ZIP/CA/URL de laboratorio; transformación documentada con pins. |
| Media, de cierre | Selección preliminar con 158 hashes discordantes y 15 documentos fuera de selección. | Resuelto en snapshot2231: cero hashes discordantes, faltas, duplicados o archivos fuera del inventario. Último ajuste de atributos ya revisado, pendiente sólo de regeneración mecánica. |
| Media, de evidencia | Lanzadores privados simultáneos sobrescribieron filas del agregado `checks.json`. | Conciliado en `PRUEBAS-CLON.json` y `RESULTADOS.md` desde logs nominales/TRX. Contrasté sus resultados finales; no se utiliza el agregado incompleto para inventar ejecuciones. |
| Baja | Metadatos de transformaciones aún decían15/45 y contador413 sin delimitar. | Resuelto y comprobado: helper48, `historicalFrozenInputsVerified20261103:413` y `currentProductSourceFiles:426`. |

## Comprobaciones propias ejecutadas

- `C:/Python312/python.exe -B .local/github-update-20261112/review/review_probe.py`, repetido sobre la selección final: HEAD base correcto; **2231 rutas de selección = 2231 rutas candidatas**, sin faltas, duplicados, elementos fuera de selección ni diferencias de hash. Las 426 fuentes de frontend/servidor/SQL coinciden con `BASELINE-SOURCES.json`; están los 48 SQL. El snapshot precede al único ajuste de atributos mencionado arriba.
- Las seis transformaciones de fixtures conservan sus pins de origen y exportación, difieren del original únicamente en la asignación de `Password` y mantienen exactamente la línea CSPRNG de la publicación previa, incluido `MfaWindowsHostHttpTests` actualizado.
- Demo50 trilingüe: los 62 archivos bajo `DATOS-DEMO50/` y `CARGAR-50-CLIENTES/` coinciden byte a byte con la entrega03 revisada. No se convierten las 868 revisiones históricas de inventario43 en cobertura de las 884 actuales.
- Inventario de rutas candidatas: cero `.local`, repositorios anidados, bin/obj, dumps, `.binlog`, bases, ejecutables de instalador, claves/certificados o fotos nuevas. El único archivo binario/visual inventariado es el ZIP RC9 adoptado en `reference/`, ya publicado. Esta comprobación por rutas no sustituye el escaneo de secretos de contenido/historial.
- 21 archivos de proyectos, locks y configuración de versiones comparados contra la base, sin cambios. Se conserva la política de licencia privada y el aviso CC0 de NetBox; no se publica una licencia abierta nueva ni se acredita redistribución de instaladores.
- Desde el clon: `C:/Python312/python.exe -B -m unittest tools.tests.test_demo50_trilingual tools.tests.test_source_demo -v`: **18/18 PASS**, 0 fallos / 0 omitidas, Windows/Python3.12/PowerShell5.1, 26,725s. Incluye pins, nombres17EN/17DE/16ES, topología preservada, archivos adicionales/tamper, reproducción del paquete Demo50, escape de nombres, parser PowerShell y rechazo de esquema no entero48. Log privado bajo `.local/github-update-20261112/review/python-units.private.log`.

## Escaneo y referencias añadidas

Ejecuté `C:/Python312/python.exe -B .local/github-update-20261112/review/final_audit.py`. Contrasté `publication-files.json` con `source-selection.json` y todos los bytes del directorio `scan-input`: mismo conjunto de 2231 archivos, sin extras, faltas ni diferencias. El hash del binario Gitleaks coincide con el declarado; las reglas, lock y auxiliar del escáner no cambian respecto a la base. La ejecución del escáner pertenece al coordinador: Gitleaks8.30.1, profundidad de archivo1, código10 por coincidencias, no error de herramienta.

Revisé privadamente las **2456 coincidencias = 2456 clasificadas / 0 sin resolver**, sin incorporar valores al informe. Validé todos sus pins de archivo y reglas/posiciones: 1527 decisiones históricas se reutilizan sólo sobre archivos byte-idénticos; las 929 restantes corresponden al catálogo validado y aparecen en campos `hardwareProfileKey`262, `profileKey`542, `hardwareGroupKey`12 y `key`113. No hay clasificación nueva por mera forma HEX, directorio o extensión. No se afirma un escaneo vacío ni un nuevo barrido del historial remoto.

La ampliación final2438 produce **2457 coincidencias**. La ocurrencia adicional es `evidence/s1-20261017/tres-tandas-53/CIERRE.md`, línea8/columna128, regla `generic-api-key`, blob SHA256 `c3104ba66fa87b5a86f6f5b17e4f8b0558788bc144527878d83d7e06de9b4cad`. Leí el texto exacto y lo contrasté con el reporte privado: es una enumeración narrativa de cuatro tipos de datos SQL comparados por igualdad en un ensayo de preparación/recuperación; no asigna un nombre de cuenta, token, contraseña ni otro valor autenticador. Acredito **FP-03** sólo para esa ocurrencia y esos bytes, categoría `natural_language_sql_object_list_no_authentication_value`, documentada sin el valor en `review/one-new-scan-classification.json`. Debe incorporarse a la clasificación final para cerrar2457/2457; no se añade una exclusión al escáner ni se rebaja una regla.

`reference-additions.json` registra **300 referencias: 98docs + 202evidence**, desglosadas en 242Markdown, 55JSON, 2HTML y 1patch. Todas mantienen bytes de origen y se limitan a esas categorías permitidas; cero extensiones inseguras o directorios omitidos. Los JSON no contienen valores string en los campos autenticadores concretos comprobados por la sonda. Consulté además recibos representativos de token de servicio, postflight y pérdida nativa: contienen resultados/metadatos sanitizados, no tokens, claves ni contraseñas. El escaneo del conjunto también cubre esas referencias; no se adoptan logs privados para completar enlaces.

## Resultados del coordinador contrastados por lectura

No son ejecuciones del revisor. Leí el TRX final: **189 ejecutadas / 189 PASS / 0 fallos / 0 omitidas**, ocho clases afectadas. El log del cargador acredita **13/13 PASS** en PostgreSQL y el smoke confirma 10 clientes, 5408 puertos, frontend servido, rol runtime sólo DML, inventario committed y MFA desactivado.

La última corrida Python amplia conserva **54 casos / 53 PASS / 1 ERROR**, por falta del bundle privado fijado. El log corregido final acredita **16/16 PASS** de los afectados después de aportar el fixture exacto. Las fallas anteriores por variable de DLL ausente y junction rechazada se conservan; no se declara una corrida única54/54 ni se cambian aserciones para pasar. Los logs finales de roadmap/plan/progreso/catálogos y `PRUEBAS-CLON.json` reflejan ese alcance; el ledger conserva su SHA y métrica.

## Adaptación del cargador de diez clientes

Diff revisado de `tools/rc9-demo-load/Program.cs`: sólo comentario y entrada cerrada para secuencia1..48, digest `68d935a07f744b0696ee09ff53710b3c79b2786826993fefdf7dfa9cb77cae61`. Recalculé independientemente los tres digests15/45/48 desde los SQL del clon, siguiendo `SchemaMigrations.Apply` y `Secrets.Digest`: coinciden exactamente con sus perfiles cerrados. Conserva pins de plan/origen, perfiles15/45, rol restringido, loopback y transacción. `development/server/tests/test_rc9_demo_loader.py` sólo amplía su descripción; mantiene negativos de esquema desconocido, hueco de historial y digest alterado. La ejecución PostgreSQL y el smoke nuevos son responsabilidad del coordinador; no se atribuyen al revisor.

## Archivos y símbolos consultados

- Método: `AGENTS.md`, `docs/BRIEFING-MAESTRO.md`, `docs/EQUIPO-Y-SKILLS.md`, `docs/PUBLICACION-GITHUB-30-10-2026.md`, `docs/PUBLICACION-GITHUB-09-11-2026.md`, `docs/PROGRESO-GLOBAL.md`, `docs/CRITERIO-FALSOS-POSITIVOS-SECRETOS.md`, `.codex/agents/release.toml`.
- Preparación: `prepare.py/copy`, `update_docs.py`, `checks.py/run`, `publish_loader.py`, `loader_check.py`, `source-selection.json`, `selection-changes.json`, `context.json`; todos dentro de `.local/github-update-20261112/`.
- Cierre: `refresh_metadata.py`, `complete_references.py`, `finalize_docs.py`, `scan.py`, `publication-files.json`, `reference-additions.json`, `scan-classification.json`, `review_probe.py`, `final_audit.py` y sus resultados privados. `tools/security/secret_scan.py/executable`, reglas/lock; catálogo validado de `load_definitions`, `build_hardware_german_cpe.validated_rows` y `build_hardware_german_repeaters.validated_rows`.
- Checkout: `preserve_base_bytes.py`, `unchanged-base-bytes-preserved.json`, `check_preserved_bytes.py`, `preserved-bytes-results.json`; contraste de los 144 blobs con HEAD y el manifiesto de publicación anterior.
- Gate de staging: `stage.py`, `final_gate.py`, guardas previas de `publish.py`, `ignored-selection-results.json`, `one-new-scan-classification.json`; contraste independiente del conjunto2438 y de los207 ignorados seleccionados. No ejecuté staging, commit ni push.
- Clon: `BASELINE-SOURCES.json`, `PUBLICATION-TRANSFORMS.json`, `.gitattributes`, `global.json`, `THIRD-PARTY-NOTICES.md`, README EN/DE/ES, guías de inicio EN/DE/ES, `docs/INSTALACION18-ESTADO-Y-ACCESO.md`, `docs/DISTRIBUCION48-PERFIL.json`, pasos22/32 y `development/server/README.md`.
- Fixtures: `MfaActiveKeyTests`, `MfaEnrollmentTests`, `MfaHttpTests`, `MfaStoreTests`, `MfaWindowsHostHttpTests`, `RecoveryChallengeTests`.
- Código: `Program.SchemaProfiles/Run` del cargador; `SchemaMigrations.LatestVersion/Files`; SQL046/048; `build_server_distribution.PROFILE_SCHEMAS/load_profile`; empaquetadores `package_server_installer.build`, `package_clean_server_installer.clean_build`, `package_windows48.collect/build/members/manifest`; `Get-SetupMfaApplicationSchema/Test-SetupMfaReadiness`.
- Demo y pruebas: `build_demo50_trilingual.read_base/transform/verify`, `TrilingualData`, `SourceDemoTests`, `Rc9DemoLoaderTests`, `Installer48Tests`, `New48Postgres`, `Complete18Tests`, manifest/inventarios Demo50 y replay histórico fijado.
- Evidencias consultadas: `PRUEBAS-CLON.json`, `RESULTADOS.md`, TRX `quality.trx` y logs nominales de loader/smoke/Python/generadores; `06-service-token.json`, `POSTFLIGHT.json` y `NATIVO.json` de las referencias añadidas.

## Pruebas no ejecutadas y límites

No compilé ni repetí suites .NET/PG, no accedí a A/D/E, no instalé, reinicié, restauré ni comprobé SCM/HTTPS nativo. No ejecuté personalmente Gitleaks, análisis de vulnerabilidades online ni auditoría jurídica nueva de dependencias sin cambios: comprobé el escaneo y resultados reales del coordinador según lo descrito. No acredito coldNew18, Restore48, éxito de la primera tarea automática HTTPS, custodia externa ni QA/adopción. Los textos revisados distinguen New17 más finalización, manual postbootPASS y automáticoHTTPSfallido.

Rollback de publicación: el padre debe conservar la base indicada y copia/bundle privado antes del push, sin reescribir historial. Revertir fuentes en Git no restaura bases ni esquemas instalados; esta tanda no opera instalaciones. El revisor no modifica punteros de publicación.

Avance: esta revisión no añade puntos. Referencia vigente: **26,63/100 del cierre restante**, sin calcular otro porcentaje global. Siguen pendientes F-09.05, Restore48, coldNew18, custodia y aceptación final, entre los límites del plan.
