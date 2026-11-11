# Resolución de bloqueantes de los pasos1–7

02.11.2026 · Windows/PowerShell5.1, SDK10.0.401 fijado, PostgreSQL17.11 en clústeres nuevos. Se reutilizaron los contratos, codec, lector, pruebas y antecedentes de los pasos1–7. No hubo operaciones sobre D, SCM, cuentas Windows, VM, CA raíz o red del equipo; no hay commits/push/publicación. Los roles nuevos son sólo SQL de los clústeres propios.

**Resultado:** bloqueantes de código, compatibilidad y empaquetado SQL corregidos; candidata12 integrada preparada. El cierre completo sigue condicionado al ensayo nativo en otra VM/identidad y a la disposición del antecedente F-01. No se acreditan los cinco pasos abiertos sólo por este resultado.

## Decisión técnica y cambios

Investigación antes de implementar en [INVESTIGACION-Y-DECISION.md](INVESTIGACION-Y-DECISION.md), con fuentes oficiales y reutilización de componentes existentes. No se añadieron dependencias ni se cambiaron SDK/runtime/PostgreSQL/Npgsql u Otp.NET.

1. **Formato mínimo3:** la cabecera añade `backupRole` y el privado contiene exactamente cuatro archivos. Cluster/owner se usan durante preparación y no conservan contraseñas/perfiles. Runtime protegido y backup CurrentUser conservan sus codecs aprobados; el rol SQL backup tiene sólo CONNECT/USAGE/SELECT. No se amplía la confianza productiva para aceptar al operador del laboratorio.
2. **Operadores:** New/Restore privados transmiten los dos flags SQL. InstallOfflineBundle los selecciona únicamente para el nuevo perfil43-sql cerrado. Los demás formatos tienen ramas explícitas. El Gate consume la petición protegida antes del hijo; no se declaran completas preparaciones con peticiones pendientes.
3. **Acceso privado:** lector1/2/3 con inventarios exactos, rol backup ligado al UUID y descriptor protegido obligatorio en2/3; ficha exportada sin contraseñas. Véase [visor/RESULTADOS.md](visor/RESULTADOS.md).
4. **Publicación/distribución:** C# actual congelado en copia privada; entradas externas de catálogo pinadas también copiadas. Restore locked, build Release sin apphost y publish sin restore/build: exit0, build0errores/0advertencias. Binlogs privados por invocación fuera del paquete. Frontend reutilizado byte a byte del punto3 vigente; SQL43 y catálogo conservados. Nueva candidata71archivos,53servidor+18frontend.
5. **Bundle/instalador:** nuevo perfil transporta26operadores. Guardas/inventarios conservan la lista histórica25 para sus artefactos; construir un bundle viejo desde fuentes nuevas sin SqlSecrets se rechaza. Setup, payload y wrapper12 tienen pins coherentes. Manual autónomo00–07 y QA168 planned, sin habilitarlo en D/11 ni tocar las167casos anteriores o respuestas de Wascar.
6. **Lanzador:** regresión detectó lectura del log retenido tras timeout. Wait ahora toma un snapshot con compartición de lectura/escritura y conserva exit124. No transforma una salida parcial en éxito. Esta corrección obliga a una revisión r2 del bundle; r1 se conserva.

El mantenimiento con DDL se hace por Restore a instancia nueva, no con una contraseña owner persistida. Contrato: [SQL-PROTEGIDO-INSTANCIA3.md](../../../docs/SQL-PROTEGIDO-INSTANCIA3.md).

## Artefactos finales r2

Todos siguen locales y no adoptados. Los r1 anteriores y la primera distribución con frontend01 se conservan como superados, sin sobrescribirlos.

| Pieza | SHA256 completo |
|---|---|
| Wrapper RackClick-Servidor-12-r2.zip,119269057bytes | `d75892e5938e9522e3b9d640a6f7b203146dc07babe02180b2dab899a65f697c` |
| Payload Servidor-12-r2.zip,117archivos | `769558894ad920a92e2758d5bcc6705d4a0cbd6c5367e285bd30b90592c6475b` |
| Bundle RackClick-Bundle-SQL-12-r2.zip,119013196bytes/2016entradas | `b3f60963b59edddab4ceb51414ced6df8d42afa28210b1ff67701baa4c024f73` |
| Manifiesto bundle | `295fac9e2b4bb23a8b4368559c40ff5d8f140eb5b4ac494fb5396dac1b1c6879` |
| Manifiesto aplicación43-sql | `29685419d0746df89777a5da72d25f5b7ac0e571e30decec1888787fe5f0f950` |
| Inventario aplicación | `86ad16f9295fbd71c6aae78a403a2c336e15d284897ae4216d341b8d040ef40c` |
| SHA256SUMS aplicación | `e2cb5728431bfa51bf66d2d4b17760a8d70a3d66a30595ead24bc39cf5e8baac` |

Construcción final:

```
C:/Python312/python.exe -X utf8 -B tools/package_clean_server_installer.py --archive .local/sql-integracion-12/RackClick-Bundle-SQL-12-r2.zip --service-publish .local/sql-integracion-12/service-publish --payload-output .local/sql-integracion-12/Servidor-12-r2.zip --output .local/sql-integracion-12/RackClick-Servidor-12-r2.zip --bundle-sha256 b3f60963b59edddab4ceb51414ced6df8d42afa28210b1ff67701baa4c024f73 --edition 12
```

ServiceHost reutilizado del11 pinado,38archivos sin recompilar. Su DLL conserva SHA256 `130e9cc3959d414a0e00759a2e3323a0fc004d76113df56c250f319d38065c61`. La publicación de la aplicación nueva no es la DLL histórica43 ni una reconstrucción prometida de su commit histórico. Sus fuentes congeladas y binlogs constan en el privado `.local/sql-integracion-12/`.

La copia entregable en la raíz es **RackClick-Servidor-12.zip**, idéntica al wrapper-r2 revisado; su archivo `.sha256` y [ENTREGA.json](ENTREGA.json) fijan tamaño y hash. Se copió exclusivamente a un destino nuevo, sin sustituir una entrega anterior. Es candidata para el ensayo coordinado, no una instalación ya aceptada.

## Pruebas realmente ejecutadas

| Ensayo final | Resultado y límite |
|---|---|
| New/Restore mínimo PG17.11 | **4/4 PASS**,77,109s.20clientes,roles/material nuevos,dos reanudaciones,backup posterior,rechazo de DELETE por backup y CREATE por runtime,ciphertext ajeno/material ausente/destino existente. Mismo principal Windows; no servicio. [Resultado](instancia3/pruebas-estables/result.json). |
| New nativo y Restore nativo | Ambos `deployment_prepared`,manifiesto3/cuatro privados. [New](instancia3/NATIVE-FACTORY.json) / [Restore](instancia3/NATIVE-RESTORE-FACTORY.json). Sin SCM ni confianza CA global. |
| Preparación desde bundle r2 | `installation_prepared`; selección automática de manifiesto3,sin flags manuales,26operadores extraídos del ZIP final,0peticiones protegidas pendientes y PG detenido. [Resultado](instancia3/BUNDLE-PREPARATION.json). No instala servicio. |
| Host publicado SQL negativo | Exit1,`sql_secret_missing`,diagnóstico sanitizado antes del listener. [Resultado](instancia3/HOST-NEGATIVO.json). No acredita el positivo con cuenta efectiva. |
| Visor | **122PASS** y **12focos de orquestación**. Los12simulan fronteras de archivo/SCM/descifrado; no abren secretos reales ni GUI. [Detalle](visor/RESULTADOS.md). |
| Distribución/collector | **15nuevas+16bundle+17distribución43+16distribución15 PASS**. Tres casos ZIP reales, incluidos dos negativos nuevos. [Alcance, fuentes y salidas](distribucion/RESULTADOS.md). No se suman como funciones terminadas. |
| Bundle r2 | Verificación nativa `bundle_verified`,26operadores actuales. Comparación integral con r1: sólo Process.ps1 y bundle.json cambian;2014miembros idénticos. [Resultado](distribucion-r2/RESULTADOS.md). No se repitieron las suites invariantes por esa sustitución acotada. |
| Regresión New histórica | **6/6 PASS**,47,563s,fuentes finales,privado regression-instance-final. |
| Regresión lanzador | **6/6 PASS**,8,937s,después del foco de timeout1/1. Privados regression-launcher-final y regression-launcher-timeout. |
| Guardia edición/pin | **7/7 PASS**,0,020s. Edición malformada,pin cruzado e intento05 con fuentes actuales rechazados antes de salidas. |

Las repeticiones iniciales no se añaden a esos totales. [INCIDENCIAS.json](INCIDENCIAS.json) conserva las causas de los intentos fallidos; no se cambió producto para hacer pasar los errores de fixtures. La evidencia independiente está en [sql-revision/REVISION.md](sql-revision/REVISION.md), con sus focos propios y sin atribuirse las ejecucionesPG del coordinador.

**Dictamen independiente final:** favorable para componentes e integridad12-r2, sin P1/P2 nuevos en su alcance. Verificó5/117/2016entradas, hashes/CRC,60PS1 y26operadores actuales,frontendP3/SQL43,metadata SQL compilada y sustitución r1→r2. Ejecutó8controles Gate sintéticos reales,6visor en memoria y4Wait con escritor Windows real/proceso simulado. No ejecutó sus propios ensayosPG/host/VM ni aprobó el servicio/backup bajo cuenta real. Huella del dictamen: `dced68b950ec3847525149d916bb8fce669f6bdd54c8a725787df1ebff049645`.

## Antecedente de exposición F-01

[Investigación](f01/RESULTADOS.md) y [revisión independiente](f01/REVISION-RESOLUCION.md): se distinguen búsqueda de autenticación, contexto de autorización y listado de nombres. Los informes retenidos no permiten saber qué material se mostró en la salida original, ya ausente. El escaneo limitado y redactado de esos informes tiene0hallazgos; no demuestra ausencia de exposición del contenido perdido. Las referencias exactas se buscaron sólo en eventos técnicos del proyecto, no en conversaciones ajenas ni almacenes de credenciales.

No se ha demostrado una credencial concreta activa de D expuesta, ni se ha rotado nada por conjetura. El desconocimiento tampoco se convierte en un falso positivo. Se pidió disposición expresa a Wascar; sigue pendiente. Una eventual aceptación administrativa debe distinguirse de un cierre técnico y conciliar el criterio explícitamente antes de dar crédito.

## Cierre y siguiente operación

- 1 y3 conservan sus cierres históricos.2/4 dependen de la disposición anterior.5/6/7 tienen una candidata integrada y pruebas nuevas; resta el extremo operativo real.
- No hay VM de ensayo independiente disponible confirmada en esta tanda. Wascar controla encendido/snapshots. Se pidió VM Windows Server2025 limpia,noDC,distinta de D; no se sustituyó por LEAO ni se tocó D.
- Pendiente en esa VM: instalación New12,propietario/ACL y lectura bajo SID del servicio,HTTP protegido,backup programado bajo su cuenta,Acceso privado,reboot real y Restore a otro destino Windows/SID con nuevos roles/claves. Reutilizar las pruebasSQL y negativos existentes.
- Los derechos de redistribución siguen su revisión previa; esta candidata es local de desarrollo. No se publica ni se declara adopción/producción.
- Ledger intacto:53resultados/280checkpoints/268números,25done/248pending/7in_progress. **1849/168 =11,01/100**,sin crédito nuevo ni porcentaje global nuevo. Plan contextualv1.8 documenta el avance sin cambiar pesos/criterios/estados.

## Comprobaciones de cierre documental

Los tres generadores pasan `--check`; [salidas](GENERADORES-CHECK.json). El ledger conserva su SHA256 inicial y los ZIP11/cargador02 sus hashes fijados. QA conserva exactamente los167casos anteriores; sólo cambia el caso168planificado y la revisión del catálogo, con guía regenerada. [Contraste](PRESERVACION.json). No se leyeron/escribieron resultados personales de Wascar.

Escaneo redactado acotado a147fuentes y archivos de esta evidencia: Gitleaks8.30.1 fijado devuelve8coincidencias,exit1. Las ocho son digests de archivos nombrados en inventarios/before/after, contrastados uno a uno contra sus bytes exactos actuales o snapshots conservados; no se decidió por su forma hexadecimal. [Medición sin valores](SCAN-SELECCION-SANEADO.json) · [Disposición contextual](SCAN-DISPOSICIONES.json). No se alteran escáner/reglas ni se añade una supresión; tampoco se convierte esa clasificación en higiene global o disposición del antecedente perdido F-01. El primer intento de copiar la selección superó el límite de ruta Windows antes de invocar al escáner; la copia aplanada conserva un mapa privado de procedencia.

[Revisión separada del escaneo](sql-revision/REVISION-SCAN.md): las8disposiciones corroboradas mediante48comprobaciones propias de archivos públicos,campos,líneas y referencias actuales/snapshots; cuatro controles del escáner conservan sus huellas. Sin nueva ejecución del escáner ni lectura de la captura/mapa privados por el revisor. Su SHA256 es `248e8a6ebacddac67d99e72a2fed7a0b16e1314b3db08289d2a9b9bc6a5a3fd1`. Los72entradas de los cuatro sellos hijos se verificaron sin reescribirlos: [resultado](SELLOS-HIJOS.json).
