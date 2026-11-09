# Demo50 · clientes e inventario sintéticos

02.11.2026 · Punto4. Esta demostración es opcional y está separada de los diez clientes originales y de la instalación actual de Wascar. El estado y los conteos finales se registran en [las evidencias del lote](../evidence/s1-20261102/demo50/RESULTADOS.md).

## Qué se prepara

50 clientes ficticios: diez oficinas/comercios, diez empresas medianas, ocho multisede, seis educativos, seis industriales, seis centros de datos y cuatro laboratorios mixtos. Sus nombres y etiquetas se conservan al cambiar ES/DE/EN.

Cada edificio tiene infraestructura de negocio, y cada cliente tiene además una sala **Muestras de catálogo · QA**. Esta separación permite probar todas las revisiones sin fingir que una tienda necesita todos los modelos de un centro de datos. Los equipos auxiliares genéricos y verificadores de conexión llevan rótulos sintéticos: no son nuevos modelos comerciales.

La cobertura abarca **868 parejas perfil/revisión**, con los 506 modelos elegidos y los demás perfiles disponibles en la base congelada del punto3. No se confunden 868 revisiones con 868 modelos distintos. Hay 24 perfiles sin conectores propios; se prueban montaje/capacidad y ausencia de puertos inventados, con conexión no aplicable y motivo. Las familias con extremos operativos tienen cableado documentado, y se comprueban todas las entradas/salidas de alimentación materializadas.

Los enlaces entre edificios representan un campus de laboratorio. No definen circuitos WAN, módulos/transceptores instalados, distancias ni compatibilidad eléctrica. Consola, IDC, fibra, SAS y alimentación DC conservan sus familias y descriptores: no se convierten en Ethernet para poder conectar.

## Archivos para consultar los datos

La entrega de datos es **RackClick-Demo-50-Clientes-01.zip**, con:

- `VER-50-CLIENTES.html`: índice local para buscar clientes y revisar conteos.
- Cincuenta archivos `cNN.inventory.json`, en formato `RackClickInventory-v1`, uno por cliente.
- `manifest.json`, `plan.json`, `coverage-matrix.json` y `COBERTURA-868.csv`: identidad, integridad y correspondencia entre perfil, instancia, grupos, puertos y conexiones.
- `SHA256SUMS.txt` y `00-LEEME.md`.

El ZIP contiene inventario, notas y metadatos sintéticos. No transporta cuentas, contraseñas, sesiones, factores MFA, conexión PostgreSQL, dump de la base o ejecutables. No es el Full Backup original RC9 ni un instalador. La importación desde el dashboard y la selección de esta demo en el paquete Windows completo siguen siendo trabajos de integración distintos.

Para verlo sin instalar:

1. Guarda el ZIP en una carpeta de tu elección. En el Explorador de archivos haz clic derecho sobre él y selecciona **Extraer todo**. Usa una carpeta nueva.
2. Abre la carpeta `RackClick-Demo50-01` extraída y haz doble clic en **VER-50-CLIENTES.html**. Se abrirá en tu navegador.
3. Arriba, en **Buscar cliente, escenario o idioma**, escribe parte de un nombre. En la fila de ese cliente pulsa **Detalles** para ver conteos, revisión y SHA256, o **JSON** para consultar su archivo.
4. El índice no conecta con el servidor ni modifica una base. Para ver racks interactivos con estos datos se usará la candidata completa que los incorpore; no copies archivos JSON o DLL sobre la VM actual.

## Reproducir el laboratorio desde las fuentes

Esta parte es para desarrollo. Se ejecuta en el equipo de trabajo, sin elevación, usando las herramientas fijadas del repositorio: Python3.12, runtime .NET10.0.12, PostgreSQL17.11 y, para la GUI, Node/Edge existentes. No instala dependencias, servicios ni certificados. Los clientes de RackClick siguen utilizando sólo navegador.

1. Abre **Inicio**, escribe **PowerShell** y pulsa Enter. No elijas «Ejecutar como administrador» para este laboratorio.
2. Sitúate en el repositorio:

```powershell
Set-Location -LiteralPath 'C:\RackClick_SVR'
```

3. Para generar sólo un plan, sin base ni conexión, elige un nombre que no exista:

```powershell
C:/Python312/python.exe -X utf8 -B tools/build_demo50_plan.py --output .local/demo50-plan-revision.json
```

4. Para repetir el ensayo completo, usa el manifiesto de la aplicación revisada y una **salida nueva**. El auxiliar crea las carpetas por sí mismo; no hay que crearlas antes:

```powershell
$baseDemo = (Get-Content -LiteralPath '.local/punto3-current.txt' -Raw).Trim()
$aplicacionDemo = Join-Path $baseDemo 'ARTIFACTS.json'
C:/Python312/python.exe -X utf8 -B tools/prepare_demo50.py --application $aplicacionDemo --output 'C:/RackClick_SVR/.local/demo50-mi-ensayo' --browser
$LASTEXITCODE
```

Se exigen los hashes exactos de la aplicación revisada de esquema43. Si cambian, hay que revisar y fijar otra edición, no desactivar la comprobación. El comando no acepta una base o conexión existente. Una salida previa se rechaza antes de leer la aplicación o crear el clúster: no duplica ni sobrescribe una carga anterior.

5. Espera `result: PASS`, salida0, `labStopped: true` y `serversStopped: true`. Un fallo no es una entrega válida, aunque la fase de población haya creado los cincuenta clientes. Conserva la carpeta y el informe; no borres intentos para repetir con el mismo nombre.
6. `RESULTADOS.json`, `PERFORMANCE.json` y la matriz resumen las comprobaciones. Los archivos `access-private.json`, logs, datos PostgreSQL y `backup-private` permanecen en `.local`, con permisos privados. **No los adjuntes ni los añadas al ZIP público de inventario.**

El ensayo detiene sus servidores y su PostgreSQL al terminar; las URL del archivo privado no quedan como una instalación en servicio. Las cuentas se generan con contraseñas nuevas locales. La semilla reproduce topología, nombres, identidades lógicas e identificadores de solicitudes; los UUID de recursos se obtienen de respuestas confirmadas del servidor y serán nuevos en otra carga. El backup/restore sí debe conservar los UUID persistidos.

## Comprobaciones y QA posterior

- Cobertura por contenido persistido, no sólo por el plan: identidad y revisión, montajes, capacidad, grupos, ordinals, caras, UUID y conexiones. Toda alimentación propia y de auxiliares queda documentada.
- Roles separados: administrador global, administrador de cliente, técnico, lector sin exportación y usuario sin acceso. Diez usuarios distintos leen y escriben simultáneamente, con ámbitos propios y auditoría atribuible.
- Negativos: mezcla de clientes o conectores, doble ocupación, revisión obsoleta, soporte ocupado, acceso sin permiso y fallo de auditoría; deben dejar las tablas y los recibos intactos. Los reintentos confirmados no crean objetos nuevos.
- Edge recorre siete clientes representativos, frontal/trasera, ES/DE/EN, Click-Click, recarga y otra sesión.
- Un dump PostgreSQL custom privado se restaura a otra base nueva y se ejecuta el comando nativo de recuperación. Se comparan inventario/UUID y revocaciones. El otro Systemhaus se ensaya en otra base/host: el producto admite uno por instalación y no se altera esa restricción.

El laboratorio desactiva explícitamente el proveedor MFA, como los ensayos de fuentes anteriores. No desactiva MFA en tu servidor ni prueba aquí la custodia real del servicio. La instalación limpia, HTTPS, reinicio Windows, backup operativo y recuperación integral de MFA corresponden al punto5 y sus pendientes de seguridad.

La guía de Wascar conserva sus resultados y añade QA-165 para esta demo. Permanecerá planificado en la instalación actual hasta vincularlo a una candidata completa. No se exige repetir manualmente las 868 altas: se proponen recorridos por siete escenarios y modelos concretos, con Pass/Not Pass/observaciones propios.
