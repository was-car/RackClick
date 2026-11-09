# F-02.02 · operadores SQL · resultado parcial

02.11.2026. Encargo: paso 6, conservar D y reutilizar F-02.01. Se implementaron adaptadores, se ejecutaron pruebas reales en laboratorio y se mantuvo explícita la integración restante. **No se acredita F-02.02 ni se activa SQL protegido en D.**

## Reutilización y cambios

Investigación antes de implementar en [INVESTIGACION-PREVIA.md](INVESTIGACION-PREVIA.md). Codec/host de F-02.01 conservan sus tres hashes: no se repitieron las 132 pruebas invariantes de esa tanda. Se reutilizan el patrón de carpeta privada exclusiva de Backup y los operadores pg_dump/pg_restore existentes. Ninguna dependencia o migración nueva.

- Nuevo `RackClick.SqlSecrets.ps1`: runtime RCSQL001 compatible con .NET, descriptor y entorno; backup v2 DPAPI CurrentUser; creación de carpetas nuevas y diagnósticos finitos. Importar sólo define funciones. No CLI nueva ni uso interno del codec C#: la compatibilidad de los envoltorios se prueba entre procesos.
- `RackClick.Backup.ps1`: lectura explícita v2 sin fallback, conservando v1 y pgpass temporal privado. No se altera el dump/manifiesto exportado.
- `RackClick.Instance.ps1`: rama runtime v2 con ruta fija/pin, archivo retenido y resultado sólo de metadatos. El contrato restante de cinco secretos owner/cluster y perfil antiguo no se relaja.
- Dos lanzadores: selección centralizada y eliminación de ConnectionStrings/SqlSecret y los once alias de .NET, tanto suministrados como ambientales. No mutan el entorno del padre.
- Ficha: lectura protegida acotada y export sólo de metadatos. El formatter anterior delega al nuevo, para que no quede otro camino de exportar las contraseñas. Se conservan máscara y consulta local, validaciones y aviso de escritura SQL sin ámbitos web.
- Diagnóstico: once códigos adicionales de lista cerrada, sin aprender mensajes de archivos privados ni reflejar datos desconocidos.

Fuentes y pruebas en HASHES-CODIGO.json; cambios contra snapshots en DIFF.diff. No se conservó snapshot previo completo de Start-RackClickLabInstance.ps1 al inicio; su cambio propio es la sustitución acotada de la asignación de conexión por el adaptador y limpieza ambiental. No se presenta un diff Git global como si todos sus cambios fueran de esta tanda.

## Ejecución real del coordinador

Windows anfitrión, **Windows PowerShell 5.1.26100.9711**, SDK **10.0.401**, Debug, PostgreSQL **17.11** nuevo. Fuentes privadas/logs/TRX/binlogs/credenciales sintéticas sólo en `.local/f02-02-operadores` y laboratorios propios. El código .NET de producto, csproj/locks, MFA, esquema y paquetes no cambian.

| Comprobación | Resultado y alcance |
|---|---|
| Operadores PS nuevos | **27 PASS**: DPAPI/contextos/corrupción, destino existente conservado, entorno/11 alias, ficha sin contraseñas, visor protegido con ocho claves, rechazo de los tres flags sensibles activados y compilación del lector nativo. |
| Interoperabilidad .NET/PS | **5 PASS, 0 omitidas**: ambos sentidos RCSQL001 con DPAPI real, proveedor de configuración .NET real en memoria para CUSTOM/POSTGRESQL y validador completo del visor con las once claves normalizadas del codec .NET. |
| Acceso privado | **94 PASS** en WinPS5.1: controles previos conservados y expectativas de ficha ajustadas al cambio confirmado. Sin ventana, consultas de servicios, lectura privada instalada o privilegios reales activados; escritura administrativa positiva no ejecutada. |
| Descriptor de instancia | **4 PASS** reutilizando la instancia sintética recién creada por la regresión: resultado sin conexión en claro, entorno protegido, ciphertext retenido contra escritura y pin alterado rechazado. No arrancó PG/app/servicio; mantiene archivos owner legados. |
| Backup v2 real | `backup_complete`, dump custom y manifiesto como únicas dos salidas; restauradas **20 filas** en DB nueva con otro rol/contraseña/perfil/UUID. Origen conservado; ciphertext copiado falla antes de crear destino; pgpass temporal retirado. Mismo principal Windows de laboratorio, no otro host/SID. |
| Regresiones existentes | **8 backup + 6 preparación Instance + 6 lanzador**, sin fallos/errores. Usan fixtures históricos/schema9 y entradas congeladas existentes; no son una instalación protegida43 ni ejecución en D. |
| Build final | **0 errores y 0 advertencias**, sin restore/publish. Binlogs de cada invocación privados. |

[Resumen](PRUEBAS.json), [backup](BACKUP-V2.json), [descriptor](INSTANCE-DESCRIPTOR.json). No sumar focos, repeticiones o fixtures como nuevas funciones o puntos. El revisor atribuye por separado sus probes; no son estas ejecuciones.

Comandos principales:

```
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File tools/tests/sql_secrets/Test-SqlOperators.ps1 -FixtureRoot <directorio NUEVO privado del lote>
C:/Python312/python.exe -X utf8 -B evidence/s1-20261102/f02-02-operadores/probar-backup-v2.py
C:/Python312/python.exe -X utf8 -B tools/tests/test_database_backup.py --evidence <salida privada nueva>
C:/Python312/python.exe -X utf8 -B tools/tests/test_instance_provisioning.py --evidence <salida privada nueva>
C:/Python312/python.exe -X utf8 -B tools/tests/test_instance_launcher.py --evidence <salida privada nueva>
```

Las pruebas .NET usan `dotnet test --no-build --no-restore --filter FullyQualifiedName~SqlOperatorInteropTests` con `RACKCLICK_SQL_OPERATOR_MODULE` apuntando al módulo fuente y binlog/TRX privados. Test-SqlInstanceDescriptor sólo acepta el directorio de fixtures del test de preparación, nunca una instalación arbitraria.

## Hallazgos corregidos y errores conservados

**P2 entorno:** el revisor reprodujo 11 alias retenidos en memoria bajo PS7; el coordinador confirmó dos en WinPS5.1 antes de corregir. Se contrastó la fuente .NET10 fijada. Tras corregir, PS comprueba los once y dos escenarios pasan además por el proveedor real .NET. No hubo fallback en el host protegido anterior: el alias podía causar rechazo/conflicto.

**P2 visor:** el revisor reprodujo con sustituto de descifrado, en WinPS5.1, aceptación de ocho claves y rechazo de las once normalizadas por .NET. Se admiten ahora sólo los dos conjuntos exactos; las tres opciones sensibles deben ser false y la ampliación sólo vale para v2 protegido. El positivo completo actual usa DPAPI .NET real; los tres flags true se rechazan con DPAPI PS real. Se corrigió el nombre del test antiguo que sólo probaba codec, y la descripción textual «sin DPAPI» para no negar la llamada indirecta al adaptador.

Incidencias propias, sin ocultarlas: import inicial del fixture sin PostgresBinPath; un intento .NET ejecutado antes de finalizar build y sobre binario anterior (excluido), con warning de copia MSB3026 por solapamiento; BOM de stdin del arnés corregido a UTF-8 sin BOM; fixture que usó la variable reservada HOME y otro acceso de diccionario inexistente en StrictMode; error del recolector Python con nombre de codificación `utf8-sig` tras un PASS de PS, recuperado del JSON guardado sin repetir operación. Las salidas y binlogs originales se conservan privados. No se declaran como fases rojas de producto. El build/test final se ejecutó secuencialmente, 0/0 y 5/5.

## Límites que impiden acreditar el paso

New/Restore aún generan los cinco archivos anteriores y la referencia owner-password.txt. El nuevo perfil de backup aislado **no** supera ese contrato completo; no se han convertido sus demás credenciales ni reescrito recibos. La preparación del runtime usa ACL de laboratorio; aún necesita propiedad SYSTEM/servicio readonly y su comprobación bajo el SID efectivo. DPAPI CurrentUser exige crear y usar el perfil bajo la misma cuenta del backup programado, extremo no probado aquí.

Faltan integración de provisionamiento, distribución del módulo nuevo y candidata completa; servicio, tareas programadas, recuperación en otra máquina y aceptación. No reemplazar scripts o claves en D para cubrirlo. La custodia/recuperación MFA no cambia. No hay prueba de borrado físico ni de strings en memoria.

QA-168 añadido **planned**, guía regenerada. Los 167 casos anteriores son idénticos y las respuestas de Wascar no se leen ni cambian. La candidata 11 sigue llevando su visor y operadores anteriores; esta QA no se habilita por existir las fuentes.

## Contabilidad y preservación

Revisión independiente en REVISION-INDEPENDIENTE.md. Sólo F-02.02 pasará pending → in_progress, **crédito0**, índice exacto **1849/168 = 11,01/100**. Pesos/criterios y 268 números estables. F-02.01 permanece parcial; F-02.03/.04 no se acreditan.

No se operó D/VM, SCM, cuentas, DB existente, red, MFA o datos de Wascar. No se leen credenciales reales, transcripciones o resultados QA; sin commits/push/publicación. Clústeres propios detenidos; fixture sintético usado para descriptor queda con su estado preparatorio, no aceptado como instalación. Paquetes11/cargador02 conservados por hash. Actualizados continuidad, changelog y registros; comprobación final y sello después de regenerar las tres vistas del plan.
