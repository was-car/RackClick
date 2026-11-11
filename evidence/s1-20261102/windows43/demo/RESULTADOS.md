# Demo50 opcional para Windows43 · componente del punto5

02.11.2026. Implementación separada del instalador y pendiente de su revisión independiente. No se modificó aplicación, SQL, dependencias, VM, QA, servicios/cuentas o bases existentes. No hay commits ni publicación. La instalación del paquete completo y su HTTPS/SCM/reinicio se acreditan por separado.

## Entrega

Archivos asignados nuevos:

- `tools/build_demo50_replay.py`: generador de desarrollo. Lee recibos del ensayo03 del punto4 y los50JSON públicos aceptados, extrae exclusivamente tipos/payload/UUID de inventario y resultados de creación. No transporta actor, sesión, recibos de seguridad ni cuentas. Incorpora los diez nombres de terminal modificados por la medición concurrente y los tres cables creados mediante Edge después de los recibos originales.
- `tools/windows/demo50/Import-RackClickDemo50.ps1`: cargador PowerShell5.1 mediante API; sin Python, SDK, Node ni acceso SQL en el servidor destino. Requiere esquema43, HTTPS confiable, administrador global, destino sin clientes y confirmación explícita. Conserva contraseña/MFA actuales. Completa un desafío TOTP de verificación; si falta enrolamiento, exige completarlo en la web. No cambia la política ni evita MFA.
- `tools/windows/demo50/CARGAR-50-CLIENTES.cmd`: lanzador con argumentos estáticos, CRLF y ASCII. URL/usuario/contraseña/TOTP se piden en PowerShell; contraseña y TOTP usan `Read-Host -AsSecureString`.
- `tools/windows/demo50/LEEME-DEMO50.txt`: pasos del operador, resultados y parada ante fallo. La carga es opcional, nunca predeterminada.
- `tools/tests/test_demo50_windows_import.py`:16 focos de generación y ejecución de auxiliares nativos. Los de generación usan explícitamente los datos locales aceptados; su omisión en un clon que carezca de ellos no equivale a aceptación.

Plan privado de entrega, sin seguridad: `.local/demo50-replay-01.json`; dentro del paquete se llamará `demo50/demo50-replay.json`. Tiene11.900.151bytes,50clientes y2.553comandos. SHA256:

`a3b44a37d8ca81f2f13d515d26905a520af8f09ffb2cfe498f97d06367bf423a`

El script fija ese digest literal además de exigir la referencia externa. Un plan diferente rehecho localmente con otro SHA no se admite. Se mantiene en memoria después de leerlo bajo bloqueo. Las rutas con reparse se rechazan. `FUENTES.json` fija los cinco archivos y `PLAN.json` la entrada de datos.

## Persistencia y correspondencia

Cada comando usa identidad efectiva del servidor, CSRF, If-Match e Idempotency-Key nuevo. Sólo se llaman las rutas de clientes/comandos conocidas. Los UUID de origen del plan no son autoridad: se remapean con los recibos del servidor nuevo; un UUID sin mapa se rechaza antes de enviarlo. Los resultados de creación se contrastan al final del cliente contra todos los campos de las ocho colecciones. Grupos/puertos incluyen dispositivo, grupo, tipo, gn y metadatos físicos; el índice gn por sí solo no permite superar el contraste. Para conexiones se conserva dirección/color/nota/patch/propiedades; `createdAt` pertenece al commit nuevo y se excluye de igualdad.

No hay transacción global de los50clientes ni reintento automático. Si un comando falla o su respuesta queda incierta, la carga se detiene y conserva los datos parciales. No se intenta borrar por nombre, reparar ACL, reemplazar clientes ni reanudar a ciegas. La sesión nueva se cierra en `finally`, también al rechazar el destino o la confirmación. Se reconoce el contrato real de logout204sin cuerpo.

## Ensayos realmente ejecutados

Windows anfitrión LEAO, Windows PowerShell5.1, Python3.12.3 sólo en desarrollo, PostgreSQL17.11 y servidor/frontend exactos del punto3 sin compilar:

- DLL `b756c907eac9b949d14e70bea63f2f5fbc05b73cc6bc1cb1eccdf64e3d4d8ed3`.
- Frontend `1ecb9bede2009177715a12ff0275e891f9f89475ca81560555c8f2abe9f85266`.
- Laboratorios nuevos mediante `DemoLab`, roles propietario/ejecución separados; catálogo SELECT-only. El proveedor MFA se desactiva exclusivamente en el entorno del hijo de laboratorio, como ya hace el arnés de fuentes. No cambia una instalación nativa.

| Prueba | Resultado |
|---|---|
| Carga completa mediante el script PowerShell real | Intento05PASS,195,906s:50clientes,2.553comandos confirmados;66sitios,88edificios,226salas,180racks,1.563equipos/objetos,2.869grupos,20.665puertos y2.207conexiones. |
| Contraste final | Las ocho colecciones de cada uno de los50clientes coinciden por identidad remapeada y contenido completo. No sólo conteos ni respuesta200. |
| Negativos HTTP/PG con fuentes definitivas | Confirmación incorrecta y destino con un cliente existente: ambos rechazos correctos, cero comandos/inventario sin cambios y cero sesiones activas después de logout. Intento03PASS,19,578s. |
| Suite focal |16/16PASS finales. Incluye parser/ASCII, URL, remapeo desconocido/conflicto, gn ambiguo, hash alterado/pin desconocido, plan reproducible/conteos/metadatos, JSON UTF8 sin charset, MFA por lanzador simulado y cierre de sesión en rechazos por auxiliares simulados. |
| Limpieza de procesos | Todos los PostgreSQL/ASP.NET propios de cada intento están detenidos. Se conservan sus datos y logs privados, sin borrado. |

El ensayo completo comenzó antes de tres ajustes de entrada/finalización: ampliar `finally` a los rechazos previos, pedir URL para el CMD y ocultar TOTP, más reconocer explícitamente logout204. No se repitieron los2.553comandos por esos ajustes: los16focos y los dos negativos HTTP finales ejercitan las ramas cambiadas. El ciclo de carga/contraste de inventario conserva su código. La prueba MFA del script usa un lanzador simulado, no token/custodia real.

## Fallos e incidencias conservados

- Carga01: fallo del arnés antes de API, al heredar `PSModulePath` de PowerShell7 y no poder importar Microsoft.PowerShell.Security en5.1. Cero clientes. El arnés fija sólo en ese hijo la ruta nativa de módulos.
- Carga02: el arnés buscó la clave `SystemRoot` en un diccionario cuyas claves eran mayúsculas; falla antes de cargar. Cero clientes.
- Cargas03/04: un cliente y49comandos aceptados; el contraste detectó `Ubicación` frente a `UbicaciÃ³n`. Causa real del cargador: `Invoke-WebRequest`5.1 decodificaba `.Content` de endpoints JSON sin charset como Latin1. Se corrigió leyendo `RawContentStream` como UTF8 estricto y se añadió un servidor HTTP de fixture sin charset a los focos. `UTF8-ROJO.json` conserva los dos textos medidos;05 pasa. No se alteraron datos para ocultar el fallo ni se reanudaron los destinos parciales.
- Primera suite focal:7FAIL de12; seis por el estado `$?` que PowerShell deja después de capturas correctas en el arnés y uno por contar todos los lotes de un cable como si fueran sólo los tres GUI. Se corrigieron los focos, no se cambiaron controles del producto por ellos. Ese resultado se conserva como anotación, no como una ejecución verde.
- Negativos01: el rechazo de confirmación pasó, pero el cotejo SQL del arnés consultó `revoked_at`, columna que no existe. El producto elimina la fila de sesión al cerrar. Negativos02 confirmó cero sesiones, pero después el arnés esperó200del logout manual al preparar el destino existente; el contrato es204. Se corrigió la expectativa, conservando losFAIL. Negativos03 pasa ambos casos; el cargador también reconoce204 explícitamente.

Los intentos `INTENTO-01`a05 y `NEGATIVOS-INTENTO-01`a03 se preservan con sus estados originales. Las contraseñas, rutas de acceso privadas y drivers de desarrollo no se incorporan a esta evidencia.

## Reproducción

Generación de la entrada determinista de desarrollo:

```powershell
C:/Python312/python.exe -X utf8 -B tools/build_demo50_replay.py --receipts .local/demo50-03/loaded-private.json --portable DEMO-50-CLIENTES-01 --output .local/demo50-replay-01.json
C:/Python312/python.exe -X utf8 -B -m unittest tools.tests.test_demo50_windows_import
```

El generador rechaza salida existente; la segunda construcción para comparar bytes se prepara en otra ruta. Para reconstruir desde cero sus entradas se requiere la evidencia/artefactos aceptados del punto4, que siguen siendo dependencias locales explícitas. El paquete de usuario lleva el plan ya fijado y no necesita los recibos privados ni ese generador.

Los arneses propios están en `.local/run-demo50-windows.py` y `.local/run-demo50-windows-negative.py`; sus salidas identificadas se conservan bajo `.local/demo50-windows-05` y `.local/demo50-windows-negative-03`. No son instrucciones para ejecutar contra un servidor instalado ni acreditación desde un clon limpio.

## Límites

No se ha ensayado este cargador con HTTPS/certificado real, token de la cuenta del servicio, TOTP real o la VM; la integración del paquete decide su prueba nativa posterior. No es importación/merge de cualquier JSON, backup PostgreSQL ni restauración del original RC9. Los manejos de contraseña y TOTP ponen a cero sus BSTR; no prometen borrar las cadenas administradas/copias internas del runtime. No hay garantía de durabilidad eléctrica ni atomicidad de todos los clientes. La clausura E06/Windows/MFA y el ledger no cambian por este componente.

No se modificó ledger, continuidad ni CHANGELOG compartidos; los coordina root al cerrar. Índice acreditado conservado9,76/100, sin porcentaje global nuevo. Revisión independiente: corresponde al revisor designado por el coordinador, no al autor de este informe.
