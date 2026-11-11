# Actualización privada · fuentes48 y Demo50 trilingüe · 12.11.2026

Wascar autoriza actualizar el repositorio privado `was-car/RackClick`. Se utiliza un clon separado de `main`, conservando el árbol concurrente y todas las instalaciones. No se cambia la visibilidad ni se despliega una VM.

## Selección

- Fuentes revisadas hasta el esquema48: mantenimiento, inventario/retención de backups MFA, códigos de recuperación, emergencia/pérdida, rotación y comprobaciones de arranque. Se conservan sus límites de aceptación del plan numerado, sin declarar todos los recorridos productivos cerrados.
- SQL046–048, pruebas, operadores y código de empaquetado del instalador18. **No se publican ZIP de instalación ni binarios**; las condiciones de redistribución siguen abiertas.
- Catálogo existente completo:884 revisiones para877 modelos comerciales, incluida la selección506 y routers/repetidores alemanes. Ilustraciones interactivas propias, sin fotografías comerciales descargadas ni repositorios de referencia ajenos.
- Datos opcionales en `development/examples/demo50-trilingual03/`:50 empresas ficticias con17 nombres ingleses,17 alemanes y16 españoles, visor, cargador, hashes y2553 comandos.180 racks,1563 equipos,20665 puertos y2207 conexiones. Sólo inventario: no contiene usuarios, contraseñas, sesiones, factores MFA ni cadenas PostgreSQL. La fuente sigue en43; el cargador03 exige destino48 nuevo y vacío. Conserva868 revisiones históricas, sin afirmar cobertura de las884 actuales.
- README y guías base EN/DE/ES, pasos19–32, planificación, continuidad y changelog. Las evidencias históricas no se convierten en ejecuciones nuevas.

## Investigación y adaptación mínima

Se reutiliza el método autorizado del30.10 y la selección revisada del09.11, las seis transformaciones de contraseñas de fixtures a generación aleatoria, los locks y el perfil48 existente. No se añaden bibliotecas ni se cambian versiones. El replay histórico de inventario ya publicado se utiliza con idénticos bytes y pin para que el generador trilingüe no necesite el archivo de trabajo de `.local`.

La demo original de diez clientes sigue separada. Su cargador local rechazaba48 con `schema_profile_unsupported`; se conserva ese rojo real PostgreSQL y se añade únicamente el perfil completo1..48 con SHA256 `68d935a07f744b0696ee09ff53710b3c79b2786826993fefdf7dfa9cb77cae61`. Se mantienen15/45, rechazo de esquemas desconocidos, huecos y digests alterados, permisos restringidos, transacción y seguridad existente. No se amplía un rango a versiones futuras.

`BASELINE-SOURCES.json` identifica las fuentes seleccionadas, no reproducción binaria. `PUBLICATION-TRANSFORMS.json` explica las adaptaciones del clon y no presenta el árbol concurrente completo como un commit exacto de producto. Pruebas/escaneo/revisión y verificación remota se registran en `evidence/s1-20261112/github-update/`; logs completos y binlogs quedan privados.

## Estado nativo y límites

A tiene aplicación48 y50 clientes comprobados después de reiniciar Windows, HTTPS normal, servicio automático y backup posterior. Es **New17 más finalización acotada revisada**, sin recrear base/cuentas/claves. La primera tarea automática de verificación HTTPS falló; el comprobador oficial manual posterior pasó. No se atribuye una causa puntual no medida ni se declara éxito de esa tarea automática.

La edición18 corrige el defecto de ámbito del asistente y está empaquetada/revisada. **Su instalación completa desde cero no se ha ensayado. Restore48 y cambio automático de red48 permanecen deshabilitados.** D y E se conservan. No hay adopción productiva por publicar las fuentes.

Se excluyen `.local`, bases/dumps, credenciales, claves/sobres MFA, certificados privados y la CA particular de A, transcripciones, binlogs y resultados privados QA. Los enlaces a entregas locales no son descargas de GitHub. Se conserva la referencia offline adoptada ya publicada como entrada de compilación, byte a byte, y sus avisos de terceros.

Índice de cierre **2237/84 =26,63/100 del cierre restante**, sin incremento por publicar, sin nuevos pesos ni porcentaje global del producto.
