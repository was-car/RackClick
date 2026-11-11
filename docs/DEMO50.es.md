# Inventario opcional de 50 clientes sintéticos

El repositorio incluye [DEMO-50-CLIENTES-01](../DEMO-50-CLIENTES-01/), con50 clientes ficticios, sitios, salas, racks, equipos, puertos y conexiones físicas. Descarga o clona el repositorio y abre `DEMO-50-CLIENTES-01/VER-50-CLIENTES.html` en el navegador. La búsqueda y los detalles permiten revisar cada cliente y descargar su JSON. El visor funciona localmente, sin acceso a una base de datos.

`manifest.json` identifica el archivo, tamaño y SHA256 de cada cliente. `SHA256SUMS.txt` fija todos los archivos de la colección salvo él mismo. `coverage-matrix.json` relaciona las868 parejas perfil/revisión históricas con las instancias y conexiones. El catálogo actual tiene884 revisiones para877 modelos comerciales: esta muestra no demuestra todos los perfiles actuales. La selección original de 506 modelos sigue incluida en el catálogo.

Sólo contiene inventario: sin usuarios, contraseñas, sesiones, factores MFA ni cadenas de conexión. No es un dump PostgreSQL ni un backup completo con seguridad. No copies los JSON a carpetas de base de datos ni los cargues sobre una instalación existente. La [demo desde fuentes con diez clientes](INSTALACION-DESDE-GITHUB.md) sigue siendo la predeterminada: genera credenciales nuevas y desactiva explícitamente MFA. La reproducción/importación Demo50 es otro recorrido de laboratorio aislado, descrito en [LABORATORIO-50-CLIENTES.md](LABORATORIO-50-CLIENTES.md) y [CARGADOR-DEMO50-02.md](CARGADOR-DEMO50-02.md). La publicación de fuentes no implica disponibilidad en un instalador desplegado.

Se excluyen fotos comerciales y repositorios de referencia de terceros. Las carcasas interactivas forman parte del código de la aplicación. Los nombres de recursos se conservan como fueron escritos, sin traducirlos automáticamente.

`development/examples/demo50-replay43.json` contiene la reproducción API de inventario (2553 comandos), fijada por SHA256 `a3b44a37d8ca81f2f13d515d26905a520af8f09ffb2cfe498f97d06367bf423a`. El importador Windows histórico exige un servidor vacío de **esquema43** y rechaza el45. Esta publicación no adapta ese importador ni autoriza cargar un servidor existente.

## Edición03 trilingüe · 12.11.2026

El conjunto opcional actual está en [development/examples/demo50-trilingual03](../development/examples/demo50-trilingual03/): 17 empresas ficticias con nombres ingleses, 17 alemanes y 16 españoles. Abre localmente `DATOS-DEMO50/VER-50-CLIENTES.html`. `CARGAR-50-CLIENTES` contiene el cargador HTTPS revisado, el replay fijado por hash y las instrucciones. Sólo carga un **servidor48 nuevo y vacío**, con confirmación expresa; la demo de diez clientes desde fuentes sigue separada. Ante rechazo o respuesta incierta conserva los datos parciales y no repitas automáticamente. No importa usuarios, sesiones, contraseñas ni factores MFA.

La estructura43 de origen, los 50 inventarios y las conexiones se conservan: 180 racks, 1.563 equipos, 20.665 puertos y 2.207 conexiones. La cobertura sigue en 868 revisiones históricas, no todas las actuales. El conjunto se cargó en la VM A y se releyó después de reiniciar Windows. Las secciones anteriores describen la edición01 conservada. Los instaladores nativos permanecen fuera de GitHub.
