# Demo50 trilingüe · edición03 · 11.11.2026

Componente para la nueva candidata de instalación17/esquema48. Su revisión independiente, instalación y carga real corresponden al coordinador. Este documento no afirma que se haya cargado una VM.

## Contenido

- 50 empresas enteramente ficticias: **17 nombres en inglés,17 en alemán,16 en español**. Cada nombre lleva una etiqueta de dato sintético en su idioma. Los nombres son fijos: cambiar EN/DE/ES en la interfaz no traduce la empresa.
- Se conservan byte a byte los50 JSON de inventario, `coverage-matrix.json` y `COBERTURA-868.csv` de la edición01. Identidades de fuente, dispositivos, montaje, puertos y cables no se reconstruyen.
- Sólo cambian `name`/`language` en los clientes de `manifest.json`/`plan.json`, y `name` en el replay. El visor y los manuales se regeneran para mostrar esos nombres.
- Fuente de inventario **esquema43**, destino autorizado **esquema48**. No se finge que la fuente se exportó de48. El cargador anterior02 permanece intacto.
- El inventario representa868 revisiones de perfil y506 modelos originales. La instalación actual contiene884 revisiones/877 modelos; esta demo no demuestra que los16 perfiles posteriores estén colocados en racks.
- No hay usuarios, sesiones, contraseñas, factores MFA ni configuración PostgreSQL. Los nombres y etiquetas interiores de sitios/salas/equipos se conservan; no se traducen en este lote.

| Elemento | Total |
|---|---:|
| Clientes |50|
| Comandos del replay |2.553|
| Sitios |66|
| Edificios |88|
| Salas |226|
| Racks |180|
| Equipos |1.563|
| Grupos de puertos |2.869|
| Puertos |20.665|
| Conexiones |2.207|

## Entrega privada

Archivo: `C:\RackClick_SVR\.local\demo50-trilingual03\entrega-01\RackClick-Demo50-Trilingual-03.zip`.

- ZIP: `d7ab9469d4929af703285b0cc7eddcf13e9f245f43828cfcaee95c0e2d2e9215`,3.926.984 bytes,64 entradas.
- Replay: `44f7fca5dd78b10de1a5efbb51f34cff488974ed264bfcf9ea72059b1194216d`,11.900.217 bytes.
- Carpeta superior: `RackClick-Demo50-Trilingual-03/`.
- `DATOS-DEMO50/`:57 archivos públicos de inventario/visor/documentación.
- `CARGAR-50-CLIENTES/`: script,CMD,LEEME,replay ySHA256SUMS propios.
- `00-LEEME.md` y `SHA256SUMS.txt` superiores describen y fijan la entrega completa.

Los hashes son de esta entrega: si se modifica un miembro hay que construir otra entrega y medirla, no reutilizar estas huellas.

## Uso en el servidor nuevo

1. Termina la instalación48 y la verificación de HTTPS/servicio/backup del procedimiento de la candidata completa. Conserva D y las instalaciones anteriores.
2. Comprueba el ZIP contra el hash entregado por el coordinador. Extrae en una carpeta nueva; no mezcles ediciones.
3. Opcionalmente abre `DATOS-DEMO50\VER-50-CLIENTES.html` para explorar los clientes. Ese visor no se conecta a RackClick ni importa nada.
4. En la VM abre `CARGAR-50-CLIENTES\CARGAR-50-CLIENTES.cmd`. Introduce la URL HTTPS de la instalación **nueva y vacía**, la cuenta administradora global y su contraseña privada.
5. Si esa cuenta tiene MFA, introduce el TOTP en la consola. Si necesita enrolamiento, termínalo en el navegador antes de comenzar. No desactives MFA ni cambies la política para cargar datos.
6. Confirma exactamente `CARGAR 50 CLIENTES SINTETICOS`. La carga conserva TLS,cookies acotadas,CSRF,ámbitos,revisionado e idempotencia existentes.
7. Resultado esperado: `demo50_loaded_verified`,50 clientes,2.553 comandos y los conteos de la tabla.
8. Si falla o la respuesta queda incierta, conserva la salida y los datos parciales. **No repitas ni borres**: no existe una transacción global ni un reintento automático.
9. El cargador relee las ocho colecciones completas por cliente. En el servidor se crean UUID nuevos y se verifica su correspondencia con los UUID de fuente; no se exige igualdad con los UUID del laboratorio original.

## Construcción y comprobación

Desde `C:\RackClick_SVR`, con Python3.12 y las fuentes históricas aceptadas disponibles:

```powershell
C:/Python312/python.exe -B tools/build_demo50_trilingual.py build --output .local/demo50-trilingual03/otra-entrega-nueva
C:/Python312/python.exe -B tools/build_demo50_trilingual.py verify --zip .local/demo50-trilingual03/entrega-01/RackClick-Demo50-Trilingual-03.zip --sha256 d7ab9469d4929af703285b0cc7eddcf13e9f245f43828cfcaee95c0e2d2e9215
C:/Python312/python.exe -B -m unittest tools.tests.test_demo50_trilingual
```

El constructor rechaza salida existente, cambios de fuente, miembros extra, duplicados o alteraciones. Exige el replay43 histórico aceptado en `.local/demo50-replay-01.json`; es inventario sin seguridad, pero no forma parte de un clon limpio. Un clon sin ese artefacto no puede acreditar estas pruebas. No necesita recibos privados del laboratorio, claves ni dumps.

## Verificación de este lote

-12/12 pruebas nuevas: nombres/distribución/Unicode, igualdad estructural y de bytes, mutaciones de inventario/comandos/identidad, mapa incompleto/extra/duplicado, ZIP alterado/autorrehasheado, reproducibilidad, parser PowerShell5.1 y rechazo de destinos incompatibles.
-26/26 focos de regresión heredados, sobre el cargador03: cookie MFA y finalidad/ruta/flags, CSRF, TLS, UTF8, no reintento, servidor ocupado y correspondencia de puertos/UUID. Se adaptaron sólo los fixtures a plan03/health48, sin modificar el archivo de pruebas histórico.
- La guarda de esquema48 falló sobre la copia sin adaptar del cargador02 y pasó tras la corrección. El componente de generación es nuevo: su primera ejecución falló por ausencia del módulo y no se presenta como reproducción de un defecto preexistente.
- No hay ejecución de2.553 comandos, prueba PostgreSQL, navegador ni VM en este lote. Esa aceptación corresponde al ensayo de instalación17.

Evidencia: [datos/RESULTADOS.md](../evidence/s1-20261111/instalacion17-demo50/datos/RESULTADOS.md). Sin commits, cambios de seguridad, instalación, ledger ni crédito nuevo.
