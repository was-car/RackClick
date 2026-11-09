# Actualización privada de RackClick · 09.11.2026

Wascar solicita actualizar `was-car/RackClick` con los cambios revisados, la documentación y los dispositivos, incluyendo los ejemplos sintéticos. Se prepara desde un clon separado de `main`; no se incorpora el árbol concurrente completo ni se modifica una instalación.

## Selección

- Fuentes de esquema 45, incluida la corrección revisada del escritor del almacén MFA integrada en la candidata interna 16. Se conservan la GUI y el catálogo: 884 revisiones de perfiles para 877 modelos comerciales distintos, con los 506 elegidos originalmente y las familias alemanas de routers y repetidores.
- Operadores de empaquetado e instalación actualizados, su perfil cerrado de distribución y pruebas correspondientes. Publicar sus fuentes no equivale a publicar o aceptar un instalador binario.
- Decisiones D2, pasos 1–18, revisión 8–18, contrato de SQL protegido, recuperación pendiente, plan numerado, continuidad y changelog.
- Colección `DEMO-50-CLIENTES-01/`: 50 clientes ficticios, 66 sitios, 88 edificios, 226 salas, 180 racks, 1563 equipos, 2869 grupos de puertos, 20665 puertos y 2207 conexiones. Incluye visor HTML, inventarios por cliente, plan, matriz de cobertura y hashes. No contiene usuarios, sesiones, contraseñas, factores MFA ni conexión PostgreSQL.
- README en EN/DE/ES y guías de alcance Demo50 en los tres idiomas. La demo original de diez clientes desde fuentes sigue siendo independiente y predeterminada.

El conjunto Demo50 conserva sus bytes revisados y la cobertura histórica de 868 parejas perfil/revisión del esquema 43. No se presenta como prueba de las 884 revisiones actuales. Se comprobaron sus 56 archivos fijados por hash, identidades únicas y vínculos internos; no se restauró ninguna base para publicarlo.

## Investigación y reutilización

Se reutiliza la selección publicada el 03.11 y el método de [publicación autorizado](PUBLICACION-GITHUB-30-10-2026.md), los locks del catálogo, el lector de autoría y el validador del plan Demo50 existentes. Las seis transformaciones de fixtures que generan contraseñas aleatorias se conservan; no se reintroducen sus constantes de laboratorio. No se añaden dependencias ni se cambian versiones. La documentación y las referencias oficiales de implementación siguen en [FUENTES-OFICIALES-DESARROLLO.md](FUENTES-OFICIALES-DESARROLLO.md).

`BASELINE-SOURCES.json` fija identidad de fuentes, no reproducción binaria. `PUBLICATION-TRANSFORMS.json` registra las adaptaciones de publicación; no se presenta el árbol local concurrente como un commit exacto de producto. El commit publicado y sus verificaciones se registran en la evidencia local sanitizada del lote.

## Comprobación y exclusiones

Antes del push se exige validación del inventario y catálogo, pruebas pertinentes en el clon, escaneo de la selección, clasificación de coincidencias y revisión independiente. Los resultados reales del lote se conservan en `evidence/s1-20261109/github-update/`; los logs completos y binlogs permanecen privados, fuera del repositorio publicado. No se atribuyen a esta publicación ensayos antiguos de PostgreSQL o VM.

Quedan fuera `.local/`, bases y dumps, credenciales, factores y claves MFA, sobres de recuperación, certificados privados, binlogs, transcripciones, resultados privados de QA, fotos comerciales descargadas, repositorios de referencia ajenos e instaladores binarios. La configuración existente del repositorio se mantiene privada, sin despliegue ni nueva licencia abierta.

## Límites vigentes

La candidata 16 tiene pruebas internas y fuentes revisadas, pero aún requiere instalación nativa limpia New/Restore, cuenta/SID efectivo, SCM, HTTPS, backup y comprobación tras reinicio. La recuperación MFA mediante instalador/operador, emergencia y rotación siguen pendientes. La guardia `recovery_mfa_envelope_required` no se relaja. No se modifica D ni E, ni se habilita MFA o un caso QA por publicar fuentes.

El índice sigue en **1607/84 = 19,13/100 del cierre restante**. Publicar no aumenta la aceptación ni crea puntos nuevos o un porcentaje global.
