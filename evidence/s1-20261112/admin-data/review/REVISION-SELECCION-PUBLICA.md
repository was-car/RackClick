# Revisión independiente de la selección de publicación20

12.11.2026. Worktree `feature/admin-data-20261112`, base `98ad43582dcf08b3227f16873175625048dc09bd`. Revisión acotada de69 referencias históricas y cuatro assets. El revisor no implementó estos archivos, no publicó, no modificó producto ni cambió visibilidad. Complementa `REVISION-PAQUETE20.md`; no sustituye New20 nativo ni adopción.

## Dictamen

**Favorable para conservar las69 referencias y para la selección de cuatro assets identificada abajo. Sin secretos ni contenido impropio de publicación detectados en este conjunto. Sin P1/P2 abiertos reproducibles.** Conviene conservar las referencias para la regeneración documental desde un clon: todas están expresamente declaradas en `docs/REGISTRO-MAESTRO-CONFIG.json`, y el generador verifica su presencia e incorpora su SHA256. No se acredita por ello reproducibilidad binaria, una nueva ejecución de las pruebas históricas ni aumento de la métrica de cierre.

El conjunto histórico consta de **31MD,34JSON y4patch**, **1.124.356bytes**. Los69 tamaños y SHA256 coinciden con el inventario privado aportado por el coordinador. Su finalidad es conservar resultados/criterios/revisiones, inventarios de fuentes, incidencias y cambios de código propios. Los archivos de fuentes contienen rutas relativas y hashes; los resultados de seguridad contienen estados, recuentos y booleanos. Las menciones a claves, contraseñas, sesiones o MFA describen comportamiento y pruebas; no son material de una instalación.

## Referencias y contenido

| Carpeta bajo `evidence/s1-20261111/` | Archivos |
|---|---:|
| `f06-04-cierre` | 6 |
| `f07-05-enrolamiento` | 8 |
| `f08-01-generacion` | 6 |
| `f08-02-recuperacion` | 6 |
| `f08-03-consumo` | 6 |
| `f08-04-ultimo-administrador` | 9 |
| `f08-05-cierre` | 8 |
| `f09-01-autorizacion-local` | 7 |
| `f09-02-material-perdida` | 7 |
| `f09-03-revocacion-auditoria` | 6 |

Se leyeron todas las entradas por código, sus estructuras JSON/campos relacionados con credenciales, encabezados y límites de los informes y contenido pertinente de los cuatro parches. Se buscaron adicionalmente asignaciones literales de credenciales, cabeceras de claves privadas, URI de enrolamiento, autorización literal, registros de dumps, rutas de perfiles personales, direcciones privadas y correos personales: sin candidatos. En los parches, las referencias a credenciales son parámetros, variables o generación aleatoria de fixtures; no contienen sesiones, factores ni claves capturados de una instalación. No se incorporan binlogs, dumps, logs crudos ni binarios entre estos69 archivos.

No se recomienda recortar o sustituir silenciosamente estos archivos para ahorrar1,12MB: hacerlo rompe la presencia/hash de fuentes que permite comprobar el registro. Sus fechas, límites y atribución histórica deben mantenerse. Copiarlos a la selección no convierte los resultados anteriores en pruebas nuevas, ni habilita capacidades pendientes.

## Contraste del escaneo del coordinador

El coordinador ejecutó **Gitleaks8.30.1**, reglas sin modificar:162 archivos de fuentes y los cuatro assets, con profundidadZIP3. Este revisor **no ejecutó Gitleaks**: inspeccionó `scan_publication.py`, `classify_asset20.py`, los informes privados y volvió a clasificar cada alerta contra los bytes y datos de catálogo. Se comprobó también `.gitleaks.toml`: sólo extiende las reglas oficiales con `useDefault=true`, sin allowlist; no hay `.gitleaksignore` en el worktree ni en la selección escaneada.

- Fuentes: una alerta de regla genérica en `f07-05-enrolamiento/review/DICTAMEN.md:30`. Se comprobó su contexto: descripción de versiones de material retirado/activo y cifrado del factor. No es una asignación ni una clave o credencial. No se copia el valor del match a este informe.
- Assets: **1468 alertas**, todas comprobadas individualmente. **1444** son identificadores de perfiles presentes en definiciones validadas de catálogo; **22**, identificadores de grupos del mismo catálogo; **1**, SHA256 que coincide con los bytes reales de `046-mfa-key-rotation.sql` y con el manifiesto de aplicación fijado; **1**, captura truncada de un identificador de perfil, verificada contra el JSON exacto, su ubicación y sus dos referencias internas coherentes.
- Se volvió a leer cada miembro anidado afectado, se comprobó su SHA256 contra la clasificación y el digest del valor detectado. La clasificación independiente no necesitó aceptar por sí sola la whitelist anterior de ubicación. **Cero alertas sin resolver.**

Los resultados crudos de Gitleaks y los valores de coincidencia permanecen privados. La clasificación pública sólo contiene recuentos/contexto; no se debilitaron reglas ni se introdujo una excepción de escaneo en el producto.

## Cuatro assets exactos

Directorio privado de entrega: `.local/admin-data-20261112/entrega-20`. El set de nombres coincide exactamente con `release-assets.json`; no hay quinto archivo. Los cuatro tamaños/SHA256 se calcularon de nuevo. El HTML y la guía coinciden con las fuentes actuales; la suma externa corresponde al ZIP. La guía se mantiene fuera de éste para fijar su hash sin circularidad.

| Asset | Bytes | SHA256 |
|---|---:|---|
| `RackClick-Windows-Online-20.zip` | 11.555.659 | `2644dc115ed03086a5a1d60b5e6418989350ebaf08942e8c07d81a5bdda813fb` |
| `RackClick-Windows-Online-20.zip.sha256` | 98 | `7baaf27690a743c8710b01831a5860d3edc45698d43670598376a1f27faaebc1` |
| `00-LEEME.html` | 12.361 | `62b27c34ae3abc18d996f5bdc1f3386ad6b0b1dba67ccc805bd9e58b021f62ce` |
| `INSTALACION20-PASO-A-PASO.md` | 9.811 | `8946a973b978864769bc9f36fd293fd9d3eeb1546d35bcd960c7b931aa9ab0c2` |

La guía externa incluye descarga con `Invoke-WebRequest`, comparación con el SHA fijado antes de extraer y rechazo de carpeta preexistente. La ruta de descarga apunta al tag20 previsto. El ZIP conserva la identidad revisada en `REVISION-PAQUETE20.md`; Native/bundle privados contienen runtimes y siguen excluidos de estos cuatro assets.

## Observación de acceso resuelta

La documentación30-10 describía `was-car/RackClick` como privado, por lo que se señaló al coordinador una posible incompatibilidad con la descarga sin login. El contraste actual la resuelve: **GET anónimo** a [GitHub API, repositorio RackClick](https://api.github.com/repos/was-car/RackClick), sin cabecera Authorization, **HTTP200**, `private=false`, `visibility=public`, **2026-11-12T08:56:14Z**. No se modificó visibilidad. El navegador de búsqueda no pudo abrir el endpoint; se realizó el GET con `urllib.request` estándar sin autenticación y se guardó el resultado sanitizado privado.

Esto verifica la visibilidad actual del repositorio; **no acredita todavía que el tag20 y sus cuatro assets estén publicados o descargables**. Corresponde al coordinador contrastar después de publicar una descarga anónima de cada asset y su tamaño/SHA256. No debe atribuirse ese paso futuro a esta revisión.

## Pruebas propias y límites

- `C:/Python312/python.exe -B tools/build_master_roadmap.py --check`: exit0,53resultados/302correspondencias; `closurePointsUnchanged=26.63095238095238`, `writesLedgerOrProduct=false`.
- Relectura de los69 archivos:69/69 tamaños/SHA exactos,69/69 declarados en `config.sources`.
- `C:/Python312/python.exe -B C:/RackClick_SVR/.local/admin-data-20261112/review-public-selection.py`: PASS,69 referencias, cuatro assets exactos, las1468 alertas de assets y la alerta de fuentes clasificadas por comprobación propia. Resultado privado `review-public-selection-result.json`. La primera versión de la sonda exigía erróneamente que el contexto de una alerta contuviera una palabra no presente en esa línea; se corrigió sólo la aserción del revisor para contrastar el contexto real, sin modificar producto/documentos.
- GET anónimo descrito arriba, con resultado sanitizado `review-public-repository-status.json`.

Archivos/símbolos adicionales consultados: `tools/build_master_roadmap.py` (`build`, comprobación de `config.sources`, cálculo de hashes, `main --check`), `docs/REGISTRO-MAESTRO-CONFIG.json`, `docs/PUBLICACION-GITHUB-30-10-2026.md`, los69 paths del inventario privado `historical-roadmap-references.json`, `release-assets.json`, `final-scans.json`, `asset-scan-classification.json`, `scan_publication.py` (`scan`, selección/extensiones prohibidas), `classify_asset20.py` (`nested_file`, ramas de clasificación), cargadores/definiciones de catálogo reutilizados para comprobar los identificadores y los cuatro assets de la tabla. El informe exacto de paquete20 se conserva separado.

No se ejecutaron builds, pruebas PostgreSQL/GUI, instaladores, VM, servicios, cuentas, commits, push, publicación ni descarga de una Release20 ya publicada. No se escaneó de nuevo todo el historialGit por este revisor. La recomendación se limita al conjunto identificado; la publicación del nuevo informe también corresponde al coordinador y a su comprobación incremental. No se incrementa la métrica de cierre ni se acredita aceptación instalada de Wascar.
