# F-06.02 · catálogo y retirada bajo mantenimiento

09.11.2026 · Continuación expresamente solicitada por Wascar. D/E sin operaciones; no instaladores, cuentas/servicios instalados, commits o push. Este bloque añade una **retirada lógica operativa**, no una rotación/recifrado ni borrado criptográfico.

## Resultado implementado

- Catálogo privado por instalación/generación, cobertura explícita y SID/UTC del operador autorizado. Raíces y entradas exactas, recibos externos pineados, manifiesto/dump/inventario contrastados y handles de archivos/directorios retenidos. Unknown/legacy/parcial/missing/alterado bloquean. Refresh es monótono y conserva generaciones; no expira backups.
- CLI `--mfa-key-maintenance`, elevada antes de leer stdin, confianza productiva fija SYSTEM/Administradores, comprobación SCM sólo lectura y binding de cuenta/rutas de instalación. El wrapper PowerShell no detiene servicios automáticamente; transmite el secreto SQL por stdin y no lo refleja.
- Coordinador con identidad SQL owner/UUID/PG17.11/SQL45, exclusión local y PostgreSQL, ACCESS EXCLUSIVE sobre factores, censo ReadCommitted después de obtener locks, nueva comprobación de catálogo/dependencias y autenticación de todos los factores con AAD. No escribe filas SQL ni añade DDL, roles o migraciones.
- Fence/journal previos a publicación, anillo inicial/final privados, reemplazo del objeto comprobado y verificación posterior. GetKey de la versión retirada falla; todos los archivos DPAPI siguen idénticos. Resume observa material original/final esperado y reconoce una operación ya verificada.
- Host antes del listener: fence, lease PG compartida y retención local del anillo hasta terminar su vida. Monitor/gate ante pérdida de admisión. Backup con inventario también obtiene lease compartida. La exclusión física sigue protegiendo al perderse PG; la transacción de mantenimiento conserva el lock de factores durante el cierre del fence.

[Manual](../../../docs/MANTENIMIENTO-CATALOGO-Y-RETIRADA-MFA.md), [plan/investigación](../../../docs/PLAN-F0602-CATALOGO-Y-RETIRADA.md), [fuentes/pines](FUENTES.json), [catálogo](CATALOGO.md), [almacén/SCM](ALMACEN.md), [dictamen independiente](REVISION.md).

## Ejecuciones y entorno

Windows anfitrión, SDK10.0.401/runtime10.0.12, Npgsql10.0.3, PostgreSQL17.11, esquema45. Build aislado y restore locked con binlogs privados únicos; sin dependencias nuevas. Los resultados finales se fijan en POSTGRES-REGRESION.json y BACKUP-NATIVO.json, y las salidas originales/TRX están sólo en `.local/f0602-retire-2cfc68a4/` y laboratorios UUID propios.

- Catálogo:52 casos Windows del implementador y52 repetidos por revisor distinto, mismos casos; no sumarlos como104 funciones.
- Almacén:37 Windows del implementador y37 repetidos de forma independiente; DPAPI real en carpetas sintéticas. SCM:28 casos, con observación de un nombre GUID inexistente; el positivo real SCM no fue ejecutado.
- Coordinador:16 casos PG/Windows propios y16 repetidos por revisor en otro clúster nuevo: retirada sin referencias, pending/active/disabled, activa rechazada, backup real pg_dump que conserva versión, catálogo monótono, RootACL ajena, ciphertext/AAD inválidos, cuatro cortes por excepción y resume, sesión PG terminada con retención física, lector de backup rechazado y escritor SQL bloqueado, censo sin lock rechazado. Todas las seis tablas de seguridad contrastadas y los archivos de claves permanecen iguales en la retirada; no se afirma haber fingerprintado todas las tablas de DB45.
- Regresión pertinente final: **297/297,0fallos/0omitidas**, con contadores y pines en [POSTGRES-REGRESION.json](POSTGRES-REGRESION.json). Incluye casos previos de retención/inicialización/composición y HTTP del proveedor Windows, más fence y vida efectiva del handle del host. Los HTTP usan TestServer/identidad de laboratorio; no navegador/TLS real ni token del servicio.
- Backup nativo:8 controles reales repetidos con la nueva admisión sobre la DLL final; snapshot censo/dump/restore con escritor posterior, operador New/Test, alteraciones/destino existente/tercer archivo. No se atribuye esa ejecución de metadatos a retirada o custodia externa real.
- PowerShell/Python:18 casos de operadores/procesos, incluidas exclusión de modos, rechazo no elevado antes de preguntar/consultar servicio, ASCII/PS5.1 y argumentos adicionales. No se ejecutó el wrapper elevado contra un servicio real.

## Hallazgos, rojos e intentos conservados

- La lectura de directorios sólo con FILE_READ_ATTRIBUTES permitía renombrar una raíz vacía. Reproducción independiente y del implementador; GENERIC_READ + FileShare.Read lo bloquea. Nuevo foco previo1FAIL/1PASS y52PASS después. No se atribuye fallo al ancestro ya protegido por un descendiente.
- `candidate` de tipo string/null/objeto/array/bool lanzaba InvalidOperationException. Cinco negativos fallaron; ahora se exige Number antes de TryGetInt32. Se mantienen códigos constantes y errores de programación fuera de capturas globales.
- Se detectó por revisión el riesgo de perder la lease PG mientras el host seguía abierto. Se añadieron handle local de vida del host, preflight sin escritura, monitor y gate. PG real termina la sesión y comprueba que el mantenimiento sigue excluido.
- Request con connectionString tiene ToString explícitamente redactado; prueba sin datos claros. La composición válida con fence se rechaza y no modifica material.
- Primer PG16:3PASS/13FAIL por cleanup de fixture que suponía cascade al borrar app_user. Se corrigió **sólo el fixture propio** para borrar su factor antes de su usuario, con parámetros/transacción, y una nueva instancia PG16 dio16PASS. No se modificó el producto o FK para hacer pasar la prueba.
- Una regresión inicial294PASS precedió los dos nuevos focos de host y ToString. El primer297 dio296PASS/1FAIL: la prueba de vida del host creaba el Harness pero el cliente era lazy y todavía no había arrancado el host. Se añadió GET real `/health/live` antes de la aserción y espera acotada de la liberación al cerrar. Se conserva el intento fallido; no se cuenta como comportamiento correcto del producto.
- Compilaciones intermedias por anotación Windows, nullability y cancelación xUnit se conservan con binlog; no cuentan como pruebas válidas. No se normalizaron ni sustituyeron suites históricas para conseguir un verde.

## Autoridad, límites y cierre

Completitud es sobre **todas las raíces retenidas declaradas** y verificadas por la autoridad local; no se infiere que no haya USB/raíces externas omitidas. ACL limita terceros y los productores deben respetar admisión; copiar/importar retenidos desde otros medios durante mantenimiento está fuera del protocolo. Un administrador local malicioso puede alterar la autoridad; los pines no prueban inexistencia de copias externas. Unknown no se convierte en lista vacía.

Se conservan DPAPI, anillos/journal y backups previos. Una escritura inicial de fence/journal interrumpida antes de quedar preparada puede quedar parcial: falla cerrado y exige diagnóstico; no se repara por nombre. File.Replace+flush/relectura no acredita corte eléctrico universal. Los cuatro cortes de esta tanda son excepciones de ensayo, no todos los cortes de proceso de F-06.03.

La CLI productiva comprueba elevación/SYSTEM/Administradores y SCM fijo; su positivo elevado contra la cuenta real del servicio **no fue ejecutado**. El positivo del coordinador usa token y confianza de laboratorio explícitos, con DPAPI/ACL/locks reales. F-06.03 (rotación/recifrado/testigo DB y su matriz de caídas), F-06.04 y QA/adopción siguen separados. Ningún hito completo de F06 o adopción instalada se acredita por esta entrega de fuentes.

Tras el dictamen final favorable del criterio literal, sólo **F-06.02** pasa a `done`, con **+5/8**. Índice428/21=**20,38/100 del cierre restante** (antes3319/168=19,76), no porcentaje global del producto. No se suman variantes, casos repetidos, repositorios o controles como puntos nuevos. Se preservan texto/peso5/8, estructura congelada y todos los hitos operativos pendientes de F06.
