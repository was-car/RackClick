# Construcción local del paquete Windows S1

**Integración1450–1509.** Doce perfiles cerrados:337/397/532 de9,592 de10,712/832/849 de11,969 de12 y1089/1209/1329/1449 de13. Candidata1449 exacta, cero compilaciones.25operadores/cuatro manuales/productor congelados antes de dosZIP idénticos; versiones y pines anteriores intactos.

Este productor es una herramienta de desarrollo Python 3.12; no forma parte del
software requerido para operar el servidor instalado. Crea un ZIP interno para
validación. No compila, descarga, ejecuta PostgreSQL ni instala dependencias.
La entrega completa, servicio Windows, PKI productiva, Windows limpio, obligaciones
de licencias y QA/adopción final de Wascar siguen pendientes.

## Entradas fijadas

El productor y el lector Windows admiten exclusivamente estos doce perfiles.
El manifiesto identifica la carpeta de candidata y cada archivo se comprueba de nuevo.

| Perfil | Esquema / archivos | Bytes de aplicación | SHA256 del manifiesto |
|---|---|---:|---|
| [337/GUI185](../evidence/s1-20261017/treinta-tandas-308-337/CANDIDATA337.json) |9 /18 servidor+18 interfaz|6.578.061|`b7b26834ac5186792a01014b7221f4ba94940da19efafb84546ca635f868fa00`|
| [397/XLSX](../evidence/s1-20261017/treinta-tandas-368-397/CANDIDATA397.json) |9 /18+18|6.653.702|`cf51b03c80ddec460944295daf09705f3dbdec0cd83e054f5bfc6592fb081685`|
| [532/editor privado](../evidence/s1-20261018/sesenta-tandas-473-532/CANDIDATA532-FINAL03.json) |9 /18+18|6.794.984|`c818294e27a40c94fe2ebf603709c94263820af1facca9a7d5c288cb70e8158e`|
| [592/compartidas](../evidence/s1-20261018/sesenta-tandas-533-592/CANDIDATA592-FINAL02.json) |10 /19+18|6.939.574|`66426b3c4fdf8c75b8c1faae4572066754934000eb2567881d93407f4ae5e9f9`|
| [712/preferencias](../evidence/s1-20261018/sesenta-tandas-653-712/CANDIDATA712-FINAL02.json) |11 /20+18|7.028.507|`f256c0fc5c99c4ff24c05e36a7eddc0ed2da9d66979db3502e0c4d606ac881cd`|
| [832/XLSHTML RC9](../evidence/s1-20261018/sesenta-tandas-773-832/CANDIDATA832-02.json) |11 /20+18|7.108.267|`511c097bafd5baf7590da15287a0dbd53bb5eb8e2fde33931c940b2885e7dfc5`|
| [849/aviso accesible](../evidence/s1-20261018/tanda-849/CANDIDATA849.json) |11 /20+18|7.108.622|`1b40f9ceffde0503c024f0dce1fb79de02c05a21bc9cb93ad3b0d6a3d359dc09`|
| [969/paleta personal](../evidence/s1-20261018/sesenta-tandas-970-1029/CANDIDATA969-FIX02.json) |12 /21+18|7.037.914|`b589609154fed1567106ef0865972155258f0f5474128c73076f4697d43b8bda`|
| [1089/parejas de categorías](../evidence/s1-20261018/sesenta-tandas-1030-1089/CANDIDATA1089-02.json) |13 /22+18|7.133.395|`c8b3df5b8e0fb6c5db148b7ddca2a8064ade6b90557713fb0835cbf69bb9710c`|
| [1209/alta guiada](../evidence/s1-20261018/sesenta-tandas-1150-1209/CANDIDATA1209-01.json) |13 /22+18|7.146.303|`dc79c53fe188187637972c2cad479edd1868d1942414c602de17bb4454bd153b`|
| [1329/relaciones UUID](../evidence/s1-20261018/sesenta-tandas-1270-1329/CANDIDATA1329-01.json) |13 /22+18|7.148.383|`38bbae727ffd545436506ab65d1c66525a64bf316e0a9354079cace0aa60c6b6`|
| [1449/alta de grupos](../evidence/s1-20261018/sesenta-tandas-1390-1449/CANDIDATA1449-01.json) |13 /22+18|7.159.235|`55bdd496ec654494fd8e3400140e3e84241488986e24481939bad67cde7a91c6`|

El productor exige el hash externo correspondiente y los36,37,38,39 o40 hashes del perfil.
Rechaza cualquier hash no registrado y los manifiestos cruzados entre perfiles.
No hay opción para confiar otra versión. El tamaño de aplicación de REPORT.json,
las cantidades y SQL001..N proceden del perfil, sin arrastrar constantes de otro.
El lector Windows verifica los mismos límites y la secuencia SQL completa.
Construir un paquete no selecciona QA ni cambia datos/cuentas de ningún laboratorio.

`development/toolchain.lock.json` fija los archivos oficiales completos:
SDK10.0.401 y PostgreSQL17.11-4. Antes de abrir sus ZIP se verifican sus hashes
SHA512/SHA256 íntegros. Del SDK sólo se selecciona runtime10.0.12, host y avisos:
339 archivos/110.497.993B. De PostgreSQL se conservan `bin`, `lib`, `share` y los
cinco avisos raíz:1.568 archivos/141.177.651B. No se incluyen SDK, Node, Python,
Git, pgAdmin ni StackBuilder. Conservar sus avisos presentes en el ZIP original
no implica incluir sus ejecutables.

`development/offline-bundle.sources.json` fija rutas relativas al workspace y
hashes de VC++14.51.36247.0 y la licencia completa de Npgsql:903B, fuente upstream
fijada por commit. Las rutas no se buscan recursivamente. Los25 operadores y los
cuatro manuales se seleccionan por listas cerradas en el productor. Toda licencia
y aviso oficial seleccionado se conserva sin modificaciones. El aviso
`licenses/README.txt` declara pendiente la revisión de derechos de redistribución
y obligaciones LGPL. No se copian DLL del sistema ni se ejecuta el redistribuible.

## Ejecución

Desde la raíz del repositorio, reservar nombres nuevos de ZIP y evidencia, cuyos
directorios padre ya deben existir. Sustituir `NOMBRE-NUEVO` por un nombre único;
no reutilizar salidas ni dirigirlas dentro de una fuente de entrada:

```powershell
C:/Python312/python.exe -B tools/package_offline_bundle.py `
  --manifest evidence/s1-20261018/sesenta-tandas-1390-1449/CANDIDATA1449-01.json `
  --expected-manifest-sha 55bdd496ec654494fd8e3400140e3e84241488986e24481939bad67cde7a91c6 `
  --sdk-archive .local/downloads/dotnet-sdk-10.0.401-win-x64.zip `
  --postgres-archive .local/downloads/postgresql-17.11-4-windows-x64-binaries.zip `
  --sources-lock development/offline-bundle.sources.json `
  --destination .local/NOMBRE-NUEVO.zip `
  --evidence evidence/s1-20261018/sesenta-tandas-1450-1509/packaging/NOMBRE-NUEVO
```

Para reconstruir un perfil9 se cambian únicamente `--manifest` y su hash por la pareja correspondiente
de la tabla, conservando un destino y una evidencia nuevos. Un ZIP337 histórico
no cambia; una reconstrucción con operadores o manuales nuevos obtiene sus propios
hashes, aunque conserve los36 archivos de aplicación337.

La carpeta de evidencia se crea exclusivamente después de validar las fuentes.
Una escritura fallida conserva el archivo parcial y `FAILED.json`; no constituye
un paquete válido. No se borra, mueve ni reemplaza un destino existente.

## Verificación y operación

`REPORT.json` registra hashSHA256 externo del ZIP, hash de `bundle.json`, hash
del manifiesto de aplicación, tamaños, cantidades, versiones y hashes oficiales.
No contiene rutas privadas. `SHA256SUMS.txt` identifica ese ZIP por su nombre.
Cada nueva construcción obtiene sus propios hashes: no reutilizar un informe
antiguo ni editar el paquete después de verificarlo.

`bundle.json` tiene inventario exacto de rutas→bytes/SHA256, esquema/versiones
cerrados y UUID5 derivado del contenido. No contiene fechas de construcción.
El ZIP contiene sólo archivos ordenados, con timestamp1980, atributos y flags
fijos. Mismas entradas y mismo productor/Python/zlib producen los mismos bytes;
se debe comprobar con dos ejecuciones nuevas tras congelar fuentes. No se promete
igualdad entre distintas implementaciones o versiones de zlib.

Para instalar y operar, consultar `MANUAL-PAQUETE-WINDOWS-S1.md`,
`OPERAR-DESPLIEGUE-PRIVADO-WINDOWS-S1.md` y
`RECUPERACION-DESPLIEGUE-WINDOWS-S1.md` incluidos. El lector Windows exige el hash
externo confiable antes de extraer. Transferir ZIP e informe por un medio con
integridad controlada; calcular un hash propio de un archivo recibido no acredita
su procedencia.

El paquete interno no se publica ni adopta. Ante fallo de instalación se conservan
los parciales para diagnóstico. El rollback operativo consiste en conservar la
instalación anterior y usar un destino nuevo verificado; la recuperación de datos
sigue su manual y nunca sobrescribe bases o servicios ajenos.


FIX02, bloque970–1029: Restore12 rechazaba la candidata inicial por un literal de recuperación administrativa todavía11. Se conserva el ZIP01 fallido y se usa exclusivamente CANDIDATA969-FIX02 y el nuevo ZIP02. El cambio funcional es ese literal12; frontend, SQL001–012 y dependencias son iguales. Las DLL/PDB de dominio/servidor reflejan también la revisiónGit de compilación. No equivale a una adopción ni a otra versión de SDK/runtime. Resultados de New/Restore y revisión se atribuyen al cierre1029.


Integración1090–1149: perfil1089 cerrado por el manifiesto CANDIDATA1089-02 (SHA256 c8b3df5b8e0fb6c5db148b7ddca2a8064ade6b90557713fb0835cbf69bb9710c), SQL001–013 y22+18 artefactos. Un backup13 requiere ese perfil13: no ejecutar binarios12 sobre13. La copia de laboratorio es distinta de Restore administrativo: protege por separado principal969/12 (37 tablas) y recuperación849/11 (35), conserva preparado/sello1029 y copia sólo principal a nuevas1089/13 (39) y recuperación969/12 (37). SQL013 corre sólo en la nueva principal; sus dos tablas nuevas empiezan vacías. Cinco secretosPG nuevos y datos/cuentas/sesiones/privados/grants conservados; sin bootstrap/recover-admin. Retorno condicionado por ausencia de actividad en las cuatro ramas, incluso actividad compensada; ante incertidumbre conservarlas y resolver recovery_required, sin reescribir baselines. Pruebas Windows/QA nuevas1090–1149 se separan de1030–1089 y anteriores. No se compila ni se cambian dependencias al empaquetar.



## Alta de grupos1449 y operación1450–1509

Candidata1449-01: SHA25655bdd496ec654494fd8e3400140e3e84241488986e24481939bad67cde7a91c6,40archivos/22+18/7.159.235bytes/esquema13.195fuentes; sólo app.js difiere de1329, servidor1089/SQL001–013/CSS/dependencias exactos. Las secciones de integraciones anteriores son antecedentes.

Interfaz: INICIAR-QA-RESTAURADO.cmd→guía y credenciales privadas. Desde Todos los clientes elige Español arriba a la derecha y espera guardado; dentro de Administración no hay selector de idioma. Barra izquierda→Usuarios→debajo de Lista de cuentas, Grupos y permisos→Crear grupo. Elige Grupo de usuarios o Grupo de clientes, escribe nombre y pulsa Crear grupo. Tras commit, Grupo creado muestra nombre literal/tipo/UUID; Abrir relaciones abre sólo la ficha exacta y enfoca Grupo seleccionado. No añade miembros ni concede permisos. Navegar conserva los tres editores; salir de Administración/recargar retira el recibo temporal, sin borrar el grupo persistido.

Si queda pendiente: Consultar resultado del grupo, Reintentar alta original o Cancelar alta de grupo pendiente conservan la intención original. No registrado no acredita cancelación ni crea recibo; un commit ya confirmado se conserva ante fallo de limpieza, bloqueando continuación hasta resolver pendiente y leer snapshot válido. Los casos QA91–93 sólo se habilitan después de selección revisada de1449. Conserva observaciones y resultados anteriores; voz requiere lector habitual, no una prueba visual.

Actualización QA1509: mismo clúster/principal13(39tablas)/recuperación96912(37), cuentas/contraseñas/sesiones/permisos/datos/puntero. Sólo artifactDirectory+bundleSha256; nueva versión1449 y registro/sello propios. Cadena1149→1209→1329 intacta, inventario exacto, nada de migrar/copiar bases/bootstrap/recover-admin/login/DML de aplicación en QA real. Baseline actual capturado una vez. Sólo la misma operación explícita puede reentrar tras rolled_back confirmado, con registro/sello/baseline/parent1329/puntero intactos y sin actividad intermedia. Interferencia o incertidumbre bloquean retorno; sin rollback tardío.

New/Restore nativos usan laboratorio nuevo, secretos/TLS propios y runtime sinSDK; no acreditan otra máquina, Windows limpio, SCM/PKI productiva o voz. Instalación definitiva, licencias/redistribución, recuperación integral y adopción de Wascar siguen pendientes.

## Antecedente histórico · alta guiada1209 y operación1210–1269

Candidata1209-01: SHA256 dc79c53fe188187637972c2cad479edd1868d1942414c602de17bb4454bd153b,40 archivos/22+18/7.146.303 bytes/esquema13. Sólo app.js difiere de1089;22 archivos de servidor, SQL001–013, CSS y dependencias exactos. No ejecutar un perfil12 contra una base13. Los apartados de integración1090–1149 describen la copia histórica12→13, no la actualización actual.

En la barra lateral izquierda pulsa **Usuarios**, cerca de la parte inferior. En **Secciones de administración**, a la izquierda del contenido, pulsa **Crear cuenta**. En el centro completa **Nombre de usuario** y **Contraseña**, pulsa **Crear usuario** y espera la confirmación del servidor. La tarjeta **Cuenta creada** muestra nombre literal y UUID completo. Pulsa **Continuar a membresías**: abre **Grupos y permisos** y enfoca **Membresías de usuarios**. Si faltan cuentas nuevas, pulsa **Actualizar grupos**; contrasta UUID, elige un grupo explícito y pulsa **Guardar asignación**. La navegación no asigna grupos ni concede permisos. Vuelve a la tarjeta y pulsa **Revisar permisos efectivos**; en el panel pulsa **Actualizar cuentas** y **Consultar permisos**. Una cuenta sin grupos no obtiene acceso por su nombre ni por aparecer en una lista. Compruébalo iniciando esa cuenta en otro perfil de navegador.

Ante un guardado incierto usa Consultar original/Reintentar original/Cancelar original con la misma cuenta e intención. Una coincidencia en una lista o notRecorded no demuestra alta. El recibo confirmado permanece sólo en memoria, sin contraseña; un borrador/petición/recuperación pendiente bloquea la continuación. Después de401/403 se retiran sus datos. En390px usa desplazamiento; conserva EN/DE/ES y nombres propios. Los pasos detallados son QA85–87 en la guía, disponibles sólo tras verificar selección real1209, cuentas/roles y configuración. No se sobrescriben resultados de Wascar.

Actualización QA1269 de artefactos: misma raíz/clúster/principal13(39 tablas)/recuperación969/12(37), mismos OIDs/cuentas/sesiones/grants/secretos y puntero. Nueva versión con40 archivos; previous/preview/selected privados sellados. Sólo artifactDirectory y bundleSha256 cambian en manual-qa.json. El preparado1149, su sello, configuración fuente y artefactos1089/969 quedan como evidencia exacta. No hay migrate/bootstrap/recover-admin ni login/DML de aplicación sobre el QA actual. Se comparan datos actuales, no la foto histórica de creación.

Preview/readiness13→parada confirmada→selección atómica→GET/readiness13→parada/verificación. Retorno sólo dentro de la operación fallida si inputs, quietud y watermark único del clúster, comprobado antes/después de ambasDB, coinciden con el baseline original. Actividad incluso compensada o incertidumbre exige recovery_required y conservar selección/versiones; no renovar baseline ni ofrecer rollback posterior. El watermark es conservador por clúster. Siete runtime/logs anteriores se archivan privadamente; no se promete igualdad de archivos físicos PG tras arrancar. Si hay procesos ajenos o sesiones activas, no forzar parada.

Las pruebas New/Restore de Windows1269 usan fixtures nuevos y API/transporte exactoapp.js; no son una nueva pruebaDOM/voz/Office ni instalación limpia en otro Windows/SCM/PKI productiva/CRT elevado/licencias aprobadas. Cero builds/descargas/cambios de versiones al empaquetar. Producto final y QA/adopción de Wascar siguen pendientes.


## Antecedente histórico · relaciones por UUID1329 y operación1330–1389

Candidata1329-01: SHA25638bbae727ffd545436506ab65d1c66525a64bf316e0a9354079cace0aa60c6b6,40archivos/22+18/7.148.383bytes/esquema13. Sólo app.js difiere de1209; servidor1089/SQL001–013/CSS/dependencias exactos. Las integraciones anteriores se conservan como antecedentes, no describen la selección nueva.

Para comprobar la interfaz: ejecuta INICIAR-QA-RESTAURADO.cmd y usa la guía y credenciales privadas que abre. Elige Español arriba a la derecha y espera el guardado del idioma. En la barra izquierda pulsa Usuarios, cerca de la parte inferior. Debajo de Lista de cuentas abre Grupos y permisos. Dentro busca Relaciones de grupos · solo lectura, encima de Crear grupo; no hay un botón Relaciones de grupos en Secciones de administración.

En Tipo de grupo elige Grupos de usuarios y en Grupo seleccionado contrasta el UUID completo. Dentro de Permisos asignados, una concesión explícita sobre un grupo de clientes ofrece Ver grupo de clientes. Ese botón abre exactamente su UUID y lleva el foco al selector persistente. Desde la ficha de clientes, Ver grupo de usuarios vuelve a su origen exacto. Nombres iguales no implican identidad; pertenencias múltiples se conservan. Las concesiones globales y directas a un cliente no se convierten en grupos. Navegar no guarda, asigna miembros o permisos ni cambia el usuario común o los borradores.

La ayuda de Crear grupo dirige a editores de membresías y Permisos de grupos de usuarios, que sí requieren acciones explícitas y confirmación del servidor. Actualizar grupos retira datos obsoletos o denegados. EN/DE/ES mantienen nombres literales; usa desplazamiento en ventana estrecha. La prueba de voz requiere tu lector habitual: si no está disponible, registra Bloqueado para esa parte. Los casos QA88–90 sólo están habilitados cuando la guía confirma la distribución1329 seleccionada y sus cuentas/configuración revisadas. No cambies resultados anteriores por disponer de código nuevo.

QA1389 conserva principal13(39tablas), recuperación969/12(37), OIDs/cuentas/sesiones/grants/secretos y puntero. Se añade una versión1329, con configuración previous/preview/selected y registro/sello privados; sólo artifactDirectory y bundleSha256 cambian en manual-qa.json. El preparado1149 y overlay1209/1269 permanecen byteexactos, sin reescribir historia. La validación de la cadena excluye únicamente el descendiente identificado; una versión ajena o un sello alterado impide continuar. No copiar/migrar bases ni ejecutar bootstrap/recover-admin/login/DML de aplicación en el QA real.

Capturar baseline actual una sola vez, no la foto histórica de creación. Preview/readiness13, parada confirmada, selección atómica, GET/readiness13, parada y comparación de ambas bases/historias/permisos/actividad. Un cambio incluso compensado o una duda bloquea retorno y mantiene recovery_required; no renovar baseline ni ofrecer rollback tardío. Si existen sesiones o procesos ajenos, conservarlos y no forzar parada. Archivos runtime originales archivados privadamente; no se promete igualdad de archivos físicos PostgreSQL tras arrancar.

New/Restore de Windows se comprueban en fixtures nuevas con runtime sinSDK y secretos propios. El transporte app.js y las pruebasAPI no son una nueva ejecuciónDOM/voz/Office ni instalación limpia en otroWindows/SCM/PKI productiva. Licencias/redistribución, recuperación integral e instalación final y QA/adopción de Wascar siguen pendientes. Sin descargas ni cambios de versiones durante esta integración.

Si una operación1389 termina en rolled_back confirmado y con sus procesos detenidos, sólo se admite reintentar el mismo --operation explícito: registro, sello, baseline, puntero y parent1209 exactos y sin actividad intermedia. No descubrir otra operación ni recapturar el baseline; cualquier interferencia bloquea la reentrada. No es un rollback tardío.
