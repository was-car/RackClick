# Punto 4 · Demo50 preparada y verificada

02.11.2026. [Manual](../../../docs/LABORATORIO-50-CLIENTES.md) · [ZIP de inventario](../../../RackClick-Demo-50-Clientes-01.zip) · [Índice local](../../../DEMO-50-CLIENTES-01/VER-50-CLIENTES.html) · [Revisión independiente](review/REVISION.md).

**Resultado: PASS del laboratorio03 y revisión favorable.** Los cincuenta clientes están preparados, poblados y probados. No se han instalado en la VM ni se declara completa la entrega Windows. Los datos y cuentas originales de Wascar se conservan.

## Volumen persistido final

| Elemento | Total |
|---|---:|
| Clientes ficticios | 50 |
| Sitios / edificios poblados | 66 / 88 |
| Salas | 226 |
| Racks | 180 |
| Equipos y objetos de sala, incluidos auxiliares | 1.563 |
| Grupos / puertos | 2.869 / 20.665 |
| Cables / extremos de cable | 2.207 / 4.414 |
| Parejas perfil/revisión primarias | 868 |
| Puertos de esas instancias primarias | 16.928 |
| Perfiles operativos / sin extremos propios | 844 / 24 |
| Extremos eléctricos conectados, incluidos auxiliares | 2.202 |

El número de revisiones no es un número de modelos distintos: 862 revisiones comerciales corresponden a861 claves comerciales; las seis restantes son referencias sintéticas. La selección original sigue siendo506/506. Los24 perfiles sin extremos propios se marcan no aplicables con motivo y comprobación de montaje/capacidad, sin inventar conectores.

Diez oficinas/comercios, diez empresas medianas, ocho multisede, seis educativos, seis industriales, seis centros de datos y cuatro laboratorios mixtos. Cada edificio cuenta con rack y switch de negocio. Las muestras extensas de catálogo están en una sala QA identificada, sin presentarlas como una infraestructura recomendada para una tienda.

Se añadieron38 enlaces explícitos entre edificios,16 de ellos entre sitios. El contraste independiente encuentra32 cables entre sitios en total, porque el resto de cableado válido también puede cruzar ubicaciones del mismo cliente. Son enlaces del campus sintético de laboratorio; no describen circuitos WAN, distancias o transceptores instalados.

## Construcción y comprobación

Se reutilizó la aplicación exacta revisada del punto3, sin compilar ni cambiar producto, SQL, dependencias, MFA o instaladores. Se verificaron los868 hashes de definición contra PostgreSQL antes de cargar. Toda la jerarquía, equipos, soportes y cables se crearon mediante comandos de servidor, con actor, revisión, claves idempotentes y recibos. El SQL administrativo se limita a bootstrap/roles/comprobaciones, fallo de auditoría deliberado y fixtures de recuperación en bases nuevas.

La matriz y los50 JSON se contrastaron contra los datos persistidos. Se verificaron UUID, referencias, revisión de perfil, grupos/ordinales, caras, metadatos físicos, montajes y capacidad. Cada grupo operativo tiene al menos un extremo conectado y toda alimentación materializada está documentada. Los puertos libres, reservados, averiados y deshabilitados se conservan como casos reales de documentación; no se llenan todas las bocas.

| Comprobación | Resultado real |
|---|---|
| Generador y guardas del cargador | 21 pruebas unitarias PASS:17 del plan y4 del cargador |
| Permisos / negativos | 7 rechazos comprobados sin cambios en inventario, auditoría o recibos; replay confirmado sin duplicar |
| Diez usuarios | Diez credenciales/ámbitos distintos y barrera de inicio simultáneo; auditoría confirma10 actores y10 clientes escritos |
| GUI nativa de laboratorio | 50 clientes visibles, siete escenarios,14 vistas frontal/trasera, ES/DE/EN,3 conexiones Click-Click, recarga y segunda sesión |
| Persistencia | Reinicio del proceso ASP.NET y comparación exacta de los50 proyectos |
| Backup / recuperación | Dump custom privado de6.097.061 bytes; restore a base/roles nuevos; comando nativo conserva inventario y revoca18 sesiones |
| Otro Systemhaus | Otra base/host nuevos, cliente propio200, oculto en el primero404 y sesión del primero rechazada401 |
| Paquete / visor | ZIP57 entradas,56 hashes internos, dos construcciones con mismos bytes; visor Edge muestra50 filas |
| Revisión independiente | 13 casos propios PASS y contraste del contenido de los50 JSON, sedes/cables yZIP |

Los13 del revisor son5 guardas de carga,4 direccionales y4 de metadatos de empaquetado. No se suman sus rojos y verdes como casos distintos. El revisor no repitió PostgreSQL/HTTP/Edge: leyó las salidas sanitizadas y ejecutó sus verificadores independientes sobre los archivos exportados reales. No reutilizó `verify_instance` o `compatible` para ese contraste.

## Rendimiento del ensayo, no garantía de producción

Antes del ensayo se fijaron presupuestos de humo: p95<5s en lectura y p95<10s en escritura pequeña. La muestra final incluye diez clientes de los siete escenarios,30 lecturas y10 escrituras, con usuarios distintos. Lectura p50=30,788ms y p95=52,066ms; escritura p50=19,950ms y p95=30,118ms. Listar los50 clientes tardó19,387ms,7.788 bytes.

CPU acumulada del proceso propio antes/después:24,109375/24,296875s; working set135.598.080/136.871.936 bytes. Se conservan muestras, tamaños, memoria privada y contadores PostgreSQL en PERFORMANCE.json. Los contadores PostgreSQL son asíncronos, no una traza de consultas ni una medición completa de picos/recuperación. Se esperaron21s por el limitador de login al crear sesiones; no se desactivó ni se incluyen esos segundos como latencia de lectura/escritura.50 clientes no equivale a50 usuarios concurrentes ni a un SLA. Entorno en ENTORNO.json.

## Fallos y correcciones conservados

1. Ensayo01: población y pruebas de API/carga correctas; el guion de GUI intentó pulsar la cara sin abrir primero un rack. Falló el guion, no se atribuye un fallo al producto. Se corrigió la selección y se conservó el intento.
2. Ensayo02: GUI, exportación y recuperación funcionaron, pero el fixture intentó crear dos Systemhaus en una base. La constraint del producto lo rechazó correctamente. Se corrigió el fixture para usar otra base/host nuevos, sin quitar la constraint ni tocar inventario para eludirla. El intento02 sigue FAIL.
3. **D50-R01:** el helper de planificación era asimétrico y podía aceptar bidi→TX/RX en un caso sintético. Los dos negativos fallaron antes y pasan con la comprobación simétrica. La revisión de todos los cables reales de02 confirmó que ese defecto no se materializó allí; no se inventa un cable malo observado.
4. **D50-R02:** el primer conjunto tenía66 sitios pero sólo50 poblados, y88 edificios pero sólo50 poblados. Se añadieron88 infraestructuras de negocio y enlaces, manteniendo las868 asignaciones primarias y88 racks de catálogo anteriores. El mismo comprobador independiente verifica66/66 y88/88 en03.
5. **D50-R03:** el empaquetador admitía campos ajenos en metadatos. Se reprodujo con tres canarios sintéticos. Ahora exige contratos cerrados, reconstrucción canónica del plan desde fuentes/semilla y correspondencia exacta de matriz/inventario. Se conserva rojo02 y verde03 con su control válido. Una copia llamada «before» por el revisor ya contenía la corrección por una carrera de lectura: su adenda lo reconoce y no la usa como referencia roja original.

El ensayo03 es nuevo, completo y PASS, con todos sus procesos detenidos. No se combinan etapas de varios ensayos para presentarlas como una sola ejecución. No se borraron intentos, bases o evidencias anteriores.

## Artefactos y reproducción

| Artefacto | SHA256 |
|---|---|
| DLL exacta del punto3 | `b756c907eac9b949d14e70bea63f2f5fbc05b73cc6bc1cb1eccdf64e3d4d8ed3` |
| app.js exacto | `1ecb9bede2009177715a12ff0275e891f9f89475ca81560555c8f2abe9f85266` |
| Plan final | `68a5822beeba686e15c979ce8c4cea2e9387c3df51f03f15bbc7072a28a2af66` |
| Digest del catálogo del plan | `a281a36063c66424823d72562c110436c6711409737bf448c538378b464c01ac` |
| ZIP de inventario | `f89d8c7a5d796133cfe6b13812b885a124ee5fd21431a3c5271fd1a23d8a3447` |

Comandos principales ejecutados, con herramientas ya fijadas:

```powershell
C:/Python312/python.exe -X utf8 -B -m unittest tools.tests.test_demo50_loader tools.tests.test_demo50_plan
C:/Python312/python.exe -X utf8 -B tools/prepare_demo50.py --application '<copia revisada punto3>/ARTIFACTS.json' --output 'C:/RackClick_SVR/.local/demo50-03' --browser
C:/Python312/python.exe -X utf8 -B tools/package_demo50.py --portable .local/demo50-03/portable --output .local/demo50-03/RackClick-Demo-50-Clientes-01.zip
```

El manifiesto/JSON y la matriz son portables sin seguridad. La semilla fija plan y requestId; los UUID de recursos se obtienen del servidor. La copia privada conserva credenciales aleatorias, cluster, logs y dump, fuera de la entrega. `.local/demo50-current.txt` identifica03. El CLI no admite conexión o base existente y rechaza una salida existente antes de crear nada. Una réplica requiere el repositorio, la aplicación revisada y las herramientas fijadas; el ZIP de datos no es un instalador autónomo ni una importación implementada.

QA-165 queda planificada para la futura candidata completa; se conservan164 casos, metadata y resultados de Wascar. Puntos pendientes: integración opcional de la demo y Windows43/New/Restore/servicio/HTTPS/reinicio/backup operativo/QA en el punto5, además de los pendientes explícitos del punto3. El proveedor MFA se desactiva sólo en el laboratorio de fuentes; no se cambia MFA del servidor instalado ni se acredita custodia bajo su SID real.

Punto4 preparado en laboratorio; catálogo506/506 (100% de esa selección). Índice acreditado del cierre pendiente9,76/100 conservado: esta demo no equivale al cierre integral E-06 ni a un porcentaje global nuevo. Sin VM, servicios/cuentas/bases existentes, commits, push, publicación o limpieza.

## Escaneo acotado de la entrega

Gitleaks fijado inspeccionó65 archivos de fuentes, datos y manual, sin incluir accesos/backup/logs privados ni ejecutar un escaneo completo del historial. Conservó529 alertas de alta entropía en identificadores de catálogo/grupo:131 hardwareProfileKey,6 hardwareGroupKey y392 profileKey. Se contrastaron todos los valores de cada campo señalado contra las claves y grupos de las definiciones aprobadas, no contra una lista de contraseñas. No se modificaron reglas ni allowlists y no se anuncia que el escáner devolviese cero hallazgos. Clasificación y alcance en SECRET-SCAN.json y SECRET-SCAN-CLASIFICACION.json. La advertencia sobre notas arbitrarias sigue vigente.
