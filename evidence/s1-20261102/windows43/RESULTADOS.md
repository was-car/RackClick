# Punto5 · paquete completo Windows43 · edición11

02.11.2026. **Preparado y revisado como candidata local de ensayo.** No se instaló sobre LEAO, VM o QA. No equivale a aceptación final ni a recuperación productiva completa. Los instaladores10 y anteriores, ZIP de aplicación43/punto2 y Demo50 original se conservan.

## Entrega

`RackClick-Windows-Completo-11.zip`: **123.473.555 bytes,140 entradas**, SHA256 `f090b56e13bc3d4670834746cff33a2d01831eae517dbb0343ce760241c567b0`. El archivo `.sha256` acompaña la entrega. Dos construcciones desde las mismas entradas congeladas producen el mismo ZIP; no se afirma reproducción universal de DLL/PDB entre máquinas/rutas.

Incluye `01-INSTALAR.cmd`, envoltorio oficial11, payload/bundle de aplicación43, runtime.NET10.0.12, PostgreSQL17.11 privado, VC++14.51.36247.0,38archivos del servicio Windows histórico, operadores, avisos de licencia, manual autónomo, mantenimientoIP y Demo50 opcional. El cargador de datos usa PowerShell5.1/API, no requiere Python/SDK ni importa usuarios, contraseñas, sesiones o factores. No se incluye el backup privado del laboratorio.

| Pieza | SHA256 |
|---|---|
| Aplicación43/punto3 | `d352c04381cd4f1954aa43735e540970b295f231106560c5c9880c7ee1dc78db` |
| DLL servidor, idéntica al punto3 | `b756c907eac9b949d14e70bea63f2f5fbc05b73cc6bc1cb1eccdf64e3d4d8ed3` |
| app.js, idéntico al punto3 | `1ecb9bede2009177715a12ff0275e891f9f89475ca81560555c8f2abe9f85266` |
| Bundle43-11,2.015entradas | `19113a00d7245b8d29fe83c6ff88ff9de2466a000a9dc08a39d078f908883e84` |
| Payload11,117entradas | `7c032764319ee7cd1c05ecb61ff6bac61cba8f4080cc6d7ada4a7bf6ffce5798` |
| payload.json | `112e902e11f8ef3826bc938f8a0c23fcd9bff9dac5ec1a60bc2dc7f0248cca17` |
| Envoltorio11,5entradas | `e0d065416716e3a6c9e38c9a2d3c64175d5f7c83f74843150d576851d95b1f1b` |
| MantenimientoIP11,67entradas | `f30e5d1592d0cc26f879e8912c1b4e31e3ba1d8bfcf2ab7bd85723b6107976ed` |
| Plan opcional50 | `a3b44a37d8ca81f2f13d515d26905a520af8f09ffb2cfe498f97d06367bf423a` |
| ImportadorPS5.1 final | `86ab579763f6110e26cbead7484b258291d3282d0a6454459be027d2ccabfabc` |

## Cambios y procedencia

- Se publica sin recompilar/restaurar desde la fuente congelada del punto3. SDK10.0.401, Release sin apphost, binlog privado único. DLL, frontend, dependencias y43SQL conservan sus bytes revisados. No hay dependencias, SQL ni cambios de aplicación nuevos.
- Perfil de aplicación43/punto3 cerrado adicional; verificador mantiene el perfil43/punto2 y los históricos14/15. Colector/lector de bundle aceptan sólo el pin nuevo y esquema43 explícito, no el rango16–42. Conteo53servidor+18frontend. Metadatos y avisos fijados.
- Diez operadores propagan43 a Stage,New,Restore,readiness yMFA. Dos motoresIP y el instalador elevado usan43/pins11. Las siete tablas del catálogo reciben `REVOKE ALL` y `GRANT SELECT` después de las concesiones generales; runtime no es propietario ni tiene DDL. Los factores restaurados no vacíos siguen rechazados sin sobre.
- Se reutilizan los generadores de producción. Se congela el conjunto de empaquetado separado del árbol concurrente;118fuentes y38archivos del servicio enumerados en `FUENTES-CONGELADAS.json`. Los pins de red se fijan después de crear el payload y quedan fuera de él, evitando autorreferencia. El registro provisional anterior se corrigió al cerrar los pins.
- Generador nuevo `tools/package_windows43.py` cierra el árbol de138archivos de contenido mediante digest literal externo al manifiesto de140entradas. Construcción/verificación exigen el mismo árbol; no basta un manifiesto autoconsistente. Datos opcionales y mantenimiento se incluyen fuera del payload operativo.

## Pruebas ejecutadas

En Windows LEAO, con instancias PostgreSQL17.11 nuevas y procesos propios; sin elevación/SCM/firewall/CA global/VM:

| Prueba | Resultado real |
|---|---|
| Distribución43 y regresión15 + contratoWindows43 |43 pruebas PASS:17distribución43,16perfil15 y10operadores. No cuentan como43funciones nuevas. |
| Catálogo/runtime PostgreSQL real | Bootstrap43/868definiciones; concesión general anterior viola guardia, helper nuevo deja7tablasSELECT-only;7DELETE yDDL denegados. Un UPDATE añadido indebidamente se detecta. AltaAPI deAruba con29puertos. [Detalle](operators/RESULTADOS.md). |
| Bundle nativo | `bundle_verified`,2.015archivos;71archivos de aplicación,53servidor+18frontend;339runtime,1.568PostgreSQL,25operadores ymetadatos/avisos. Conteos exactos en manifiesto. |
| Preparación New desde bundle11 | `installation_prepared`, base/roles nuevos y despliegueTLS preparado; no servicio Windows instalado. |
| Ciclo nativo43 | HTTPS con CA/certificado explícito validado,login, escritura de equipo29puertos, backup online,parada confirmada,rearranque y persistencia exacta. [Resultado](NATIVE-CYCLE.json). |
| Restore43→43 | Entry `Install-RackClickOfflineBundle.ps1`, misma copia confiable en otra instalación/base/roles,HTTPS nuevo,loginrecuperado e inventarioUUID/referencias exactos. Ambos lanzadores/clústeres detenidos. |
| Restore15→43 | Entry nativo con copia15 propia sin factores; conserva inventario10tablas/usuarios/origen/copia,868definiciones/7catSELECT-only, revoca1sesión y deja0desafíos. Login y altaAruba29puertos correctos. [Adenda](operators/ADENDA-MIGRACION15-43.md). No se ejecutaron13/14→43 ni Restore confactores. |
| Cargador50 |50clientes/2.553comandos en195,906s;180racks/1.563equipos-objetos/20.665puertos/2.207conexiones. Contraste completo de ocho colecciones por IDs remapeados ygrupo/tipo/gn, no sólo conteos.16unitPASS ydos negativosHTTP/PG finales: confirmación incorrecta/destino no vacío, cero comandos ylogout con0sesiones. [Detalle](demo/RESULTADOS.md). |
| Empaquetador exterior |9pruebas PASS. Dos construcciones desde entradas idénticas, mismo SHA. Verificación externa yárbolcerrado PASS. |
| Manual |HTML autónomo abierto en Edge headless con perfil nuevo; captura inspeccionada, sin recursos externos. Markdown conpasos00–07 ytablaPASS/NOTPASS. |
| Revisión independiente |40focos propios y24comprobaciones de cadena,59scriptsPS analizados,38archivos servicio idénticos10,118fuentes coincidentes,50JSON/plan contrastados; límites PG/HTTP ajenos declarados. [Dictamen](review/REVISION.md). |

**68pruebas focales del implementador** (43+16+9), más los flujos reales y las comprobaciones propias del revisor, separados. No se suman las pruebas del punto3/4 ni se repite su catálogo completo por mover bytes idénticos. Seguridad: escaneo limitado de118fuentes congeladas sin hallazgos; losJSON originales conservan el escaneo/clasificación de529identificadores del punto4. No es escaneo dehistorial ni de binarios y no se afirma una garantía universal.

## Fallos y correcciones conservados

- Guion nativo intento01: indexaba `customer` en vez de `resource` en una respuesta de creación válida. Intento02: SKU/revisión inventados por el guion; el servidor respondió422 `hardware_profile_unknown`. No se cambió producto para permitirlo. Se conservan ambosFAIL; el ciclo final reutiliza sólo el cliente/rack de su propio intento02 y usa la pareja de catálogo real `aruba-jl682a`/`aruba-20261030-v1`.
- Primera llamada al generador de distribución recibió un baseCommit de longitud incorrecta y se rechazó antes de escribir salida; se repitió con el commit del manifiesto de origen. La publicación no se repitió.
- Primer foco de paths del empaquetador exterior no detectaba barra inversa porque el productor ZIP de Python la normalizaba en Windows. Se fijó el rechazo de nombre original y se cambió el fixture para alterar las cabeceras reales.9focos finales PASS. No se presenta ese fixture como un fallo observado del ZIP entregado.
- **OUTER-R01**: el revisor construyó tres archivos ficticios conmanifiesto/sumas coherentes y el verificador los aceptaba. Se añadió el digestliteral de TODOel árbol final en build/verify; el mismo negativo yla alteración coordinada de script/manifiesto/sumas/hash externo ahora se rechazan. Rojo/verde conservados por el revisor.
- Migración15→43: primer ensayo de Restore demasiado anidado falló al extraer; un miembro alcanzaba261caracteres. Una sonda posterior devolvióDirectoryNotFound, no el tipoPathTooLong supuesto por el arnés. Se conservanambosFAIL; reutilizar la misma copia en una raíz corta pasa sin cambiar paquete. Usar rutas cortas prescritas en el manual.
- El cargador conserva fallos de arnés/charsetUTF8 de sus intentos: ver detalle del implementador. No se ocultan ni se vuelven a etiquetarPASS. Los ajustes finales de prompt/logout204 tuvieron focos acotados; no se repitió la carga2.553comandos por esos cambios.

## Pendientes y límites de entrega

1. Ensayo en VM Windows Server2025 limpia: cuenta/SID efectivo, servicioSCM,CA/firewall,HTTPS/MFA real del host ydel cargador,backup programado yreinicioWindows. Los resultados de la instalación10 de Wascar se conservan, pero no se trasladan a11.
2. El asistente **no recupera backups con factores MFA** sin sobre externo; importación operativa, emergencia yrotación siguen pendientes. No borrar factores para sortearlo. La prueba43→43 actual no equivale a esa recuperación.
3. Otros pendientes del punto3, dashboardbackup/importación yQA final siguen abiertos. La opción50 no es JSONimportador genérico ni una transacción global.
4. Redistribución pública de binarios/licencias sigue abierta. Entrega local privada de desarrollo, sin GitHub/push ni adopción.

Guía: [INSTALADOR11-WINDOWS43.md](../../../docs/INSTALADOR11-WINDOWS43.md). QA-166/167 planificadas;165casos anteriores ymetadata/observaciones preservados. Catálogo elegido506/506 (100% de esa selección). **Índice acreditado de cierre pendiente9,76/100 intacto; no se inventa un porcentaje global nuevo por crearZIP o contarpruebas.** Sin commits, publicación, limpieza, ni cambios de servicios/cuentas/bases instaladas.
