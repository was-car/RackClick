# Instalador descargable equivalente a W02-A

12.11.2026 · Trabajo en curso. Instalación nueva y Release todavía pendientes.

## Solicitud y decisiones confirmadas

Wascar pide descargar e instalar desde GitHub el producto utilizado en W02-A, con los50 clientes sintéticos y sus conexiones, sin compilar. El destino nuevo es RackClick-W02-B; A, D y E se conservan. Wascar no dispone de licencia VisualStudio: VisualC++, PostgreSQL, Python y el archivoMicrosoft del que se toma el runtime se adquieren directamente de los proveedores en el destino, con hashes y tamaños fijados. No se alojan esos binarios en el activoGitHub.

Aplicación48/GUI, DLLdelservicio y Demo50 se reutilizan bytea byte. No se compiló ni se cambió códigoC#, JavaScript, SQL o comportamientoMFA. Se transporta el servicio con37archivos y se omite su apphostEXE sin uso; SCM utiliza dotnet.exe y la DLL. Se incluyen MIT y avisos de terceros del servicio por separado del contrato del runtime. Los textos/digests de licencias se contrastan en la revisión adjunta.

## Montaje y pruebas ejecutadas

- Core01 detectó la ausencia del lock de paquetes del servicio durante un montaje local. El fallo y su salida se conservan; se corrigió el colector antes de generar Core02.
- Montaje real con Pythonembebido3.12.3/zlib1.3.1: bundle48 reconstruido con SHA256 `098392ebfc62f2fe5ec9f79909ea3bdbecbf3c565286747a5a9d9507fccd8d40`, idéntico a la referencia. Dos construcciones del wrapper19 dieron SHA256 `4bb169adf155cb521ace5917afce40ddf3a59ff5a4123c5ce726bcc3f28584dd`. No se instaló producto en el host.
- El primer foco Windows detectó que el padre creaba `work` antes del ensamblador exclusivo. Se reprodujo y corrigió. Coordinador:21/21(8Python+13PowerShell5.1). Revisor:20/20 y8sondas propias; no se suman como41pruebasdistintas.
- Observación del CLI: un rechazo de raíz ajena podía añadir un diagnóstico. Nuevo negativo previo, corrección y9/9Python posteriores (incluye prueba del productor exterior). Core04: SHA256 `572215e3e99b2510f64433ba458beead7de69c761b722ef521b0abb221ca35e5`,197miembros,8799622bytes.
- Primer transporte completo:68miembros,12652565bytes, SHA256 `470e28c2848555b575aeff1ee3b2d98efb9819ef6e4116e7e1839a723247d231`. Revisor comprobó67hashes internos,4pins,62archivosDemo y ausencia de runtimes restringidos; reprodujo exactamente el ZIP. Manual y cargador accesibles desde la raíz extraída. Este transporte no se presenta como instalación verificada.
- Escaneo focal de15archivos de fuente nuevos/modificados:0hallazgos. No sustituye el escaneo/classificación de la publicación65156d4 ni afirma0hallazgos en todo el repositorio.

## B: comprobación real y parada antes de instalar

B medida WindowsServer2025x64 noDC, VMwareTools activo, operador elevado y0servicios/cuentas/carpetas de instalaciónRackClick. Se copió el ZIP exacto y se contrastaron SHA y68miembros. Check real: `online_checked`, exit0.

Prepare se ejecutó una vez. Se creó únicamente su staging privado y se verificó/extrajo el core. Se detuvo antes de adquirir Python por falta de Internet: adaptador `Ethernet0`, red192.168.206.0/24, sin puerta de enlace; una consultaHEAD al proveedor agotó su tiempo.0servicios/cuentas/basesRackClick creados. Se conserva `unexpected_error` del intento, sin convertirlo en éxito ni repetirlo.

Wascar recibió instrucciones para poner sólo B enNAT desdeVMware. No se han cambiado la redWindows, snapshots ni encendido/apagado. Pendiente su confirmación. Se prepara una corrección acotada del diagnóstico de red y del rechazo de un staging previo propio, que se conservará sin adoptar ni borrar. No es una reparación de una instalación parcial.

## Continuación

1. Terminar las pruebas de la entradaWindows corregida y generar un transporte nuevo, conservando el anterior.
2. Con Internet enB, leer su nuevaIP, adquirir archivos oficiales y contrastar el wrapper19 exacto antes de ejecutar el brokerNew una sola vez.
3. Servicio estándar/HTTPS/MFA, carga50clientes una vez, comparación de8colecciones/nombres ybackup posterior.
4. Reinicio porWascar, comprobación automática y manual separadas, datos persistentes.
5. Revisión/escaneo finales y Releaseprivada conZIP/SHA/manualEN/DE/ES. No anunciar la descarga como disponible hasta verificar el activo remoto.

Investigación y dictamen: [condiciones de distribución](review/CONDICIONES-DISTRIBUCION.md), [revisión online19](review/REVISION-ONLINE19.md). Contrato: [equivalencia W02-A](../../../docs/ENTREGA-GITHUB-EQUIVALENTE-W02A.md). Herramientas nuevas en un worktree aislado; diagnóstico y datos privados fuera de Git. Índice de cierre restante **26,63/100**, sin incremento por empaquetado o pruebas; no es un nuevo porcentaje global del producto.

## Transporte revisado02, listo para el ajuste de red de B

Tras el fallo de red se corrigieron dos aspectos de la entrada: `download_unavailable` para errores de red esperables, sin reintentos; y reconocimiento estricto de una carpeta de transporte anterior privada para no bloquear un nuevo intento en un servidor aún vacío. Sólo directorio directo deProgramData con patrón reservado exacto, sin reparse, propietarioSYSTEM/Administradores y DACLprotegida con dosACEcompletasOI/CI para esos dosprincipales. No se lee como instalación ni se reutiliza, modifica o elimina. Servicios/cuentas/instalaciones reales, nombres parecidos y ACLinseguras siguen rechazados.

Trabajador: rojo→verde de ambos controles,16/16pruebasWindowsPowerShell5.1, confixtures que no descargan ni instalan. Se conserva el primer transporte470e y se genera otro: SHA256 `186cecafcfa27009f9476ba5fc58bd6538710eb9d487886f8844008998296806`,68miembros/12653708bytes. MismosCore04/wrapper/app/Demo; sólo entrada ymanual exterior modificados. El manual añade NAT/Internet, recursos recomendados y enlaces a términos de proveedores. Escaneofocalfinal15fuentes0hallazgos; diff--check0.

ZIPnuevo copiado y contrastado enB, en carpetaRevision02 separada. Check realexit0/online_checked,servicios0,staginganteriorconservado. No nuevoPrepare ni instalación. IPsigue192.168.206.129sinpuertadeenlace: pendienteacciónNATdeWascar. QA177planned yguíaverificada;no habilitado por código. `TRANSPORTE19-02.json` registra el estado, sinsecretos. La guía legible también está en `docs/INSTALADOR19-ONLINE.html`.

Revisión independiente final del transporte02: favorable,5focos propiosPASS y67hashes correctos. El revisor no operóB. Dictamen/hash enTRANSPORTE19-02.json yreview/REVISION-ONLINE19.md. El ensayo permanece pendiente deInternet enB;no nuevaRelease.

## Reanudación con Internet confirmada por Wascar

B ahora tiene192.168.178.125/24 ypuertadeenlace192.168.178.1. UUIDyservidorvacío se contrastaron sin cambiar Windows ni su red. HTTPS alPython oficial200/tamaño11055461. Transporte02 Prepare único con Internet descargó yverificóPython, pero el primer proveedor falló enurllib/OpenSSL: `SSLCertVerificationError`, issuerlocal ausente. El nuevo staging yelerrororiginal se conservan;0servicios/cuentas/bases yninguna instalaciónNew.

Diagnóstico separado: HttpWebRequest de.NET/Windows con TLS normalresponde200 ylongitudexacta paraSDK300608304B,PG379726839ByCRT18731856B. No callbacks de confianza ni CAmanual. Se decide usar esa mismaAPIWindows ya utilizada porlaentrada paraadquirirlos3proveedores ypasar`--cache`privado alensambladorexistente, querevalidatamaño/hash. Core04,producto,versionsybundlenocambian. Larecetaoriginalpinadarechazametadatosajenos; ningunafallbackaTLSsinverificar. Modificacióndelaentradaenpruebas antesdeemitirtransporte03. Investigaciónprimaria: docs.python.org/3.12/library/ssl.html (OpenSSL/defaultcerts) yMicrosoftLearnHttpWebRequest.GetResponse (erroresyTLSWindows).

## New19 y50clientes comprobados en B tras reinicio

Prepare03 adquirió los4archivos oficiales y reconstruyó wrapper4bb exacto. New19oficial ejecutado una vez, sin finalizadores: exit3/validtrue/awaiting_reboot. Servicio estándar automático, HTTPS48/frontend21d85 exacto, backup inicial yMFA disponibles.2553comandos únicos cargaron50clientes17EN/17DE/16ES, ocho colecciones contrastadas; backup posterior0 con cuenta estándar. Wascar reinició Windows; misma instalación, servicioAuto/Running, HTTPS y50nombres/8conteos persistentes. Verificador oficialmanualpostboot_verified0; primer automáticoHTTPSfalló1 y se conservó. No convertirlo enéxito, no repetirinstalación yno cambiar factores. Carpeta/credenciales propias de B; A/D/E intactos. La evidencia JSON adjunta contiene sólo resultados sanitizados.

La tarea automática mantieneLastTaskResult1. Procesoactualapp creado después del primercheck; no se afirma historia completa ni causa del fallo deA. Esta observación permanece explícita en Release/guías, sin impedir el ensayo funcional comprobado ni equivaler a aceptación productiva. Revisión independiente y publicación remota de la selección terminándose.

## Escaneo de la entrega

Fuentes nuevas/modificadas:42archivos,0hallazgos. ActivoZIP con profundidad3:1737hallazgosGenericApiKey,1737clasificadoscomoidentificadoresdeperfiles/gruposdelcatálogo osumaSHA256delSQL046,0sinresolver. No se afirma0hallazgosdelZIP ni se excluyenarchivos/reglas:datosDemoidénticosalospublicados yvalorescontrastadosconcatálogovalidado;checksum046contrastadoconarchivo. Clasificación/digests enESCANEO19.json;rawprivados. Base651conservasu clasificación2457/0. Los metadatos finales derivados se vuelven a escanear antesdelíndice. Revisiónindependiente decondiciones y426fuentes/artefactofavorable,conconciliacióndocumental explícita.
