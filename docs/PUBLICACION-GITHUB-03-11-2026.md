# Fuentes45 y documentaciÃ³n base EN/DE/ES Â· 03.11.2026

Repositorio de destino: [was-car/RackClick](https://github.com/was-car/RackClick), **privado**, rama `main`. ActualizaciÃ³n autorizada por Wascar; continÃºa la publicaciÃ³n seleccionada del30.10. No cambia la visibilidad ni instala automÃ¡ticamente el servidor.

## Contenido

- [English](../README.md), [Deutsch](../README.de.md) y [EspaÃ±ol](../README.es.md): presentaciÃ³n equivalente, funciones, tecnologÃ­a, estructura y estado real.
- GuÃ­as completas de demo desde fuentes: [EN](GETTING-STARTED.en.md), [DE](GETTING-STARTED.de.md), [ES](INSTALACION-DESDE-GITHUB.md). Los documentos tÃ©cnicos histÃ³ricos conservan su idioma; no se afirma traducciÃ³n integral del repositorio.
- Fuentes actuales de frontend, dominio, servidor y SQL001â€“045, catÃ¡logo y generadores, pruebas, herramientas Windows, contratos y documentaciÃ³n seleccionada.884 revisiones/877 modelos comerciales, incluida la selecciÃ³n original506, seis routers y diez repetidores alemanes. Las ilustraciones propias conservan puertos interactivos; no se incorporan fotografÃ­as comerciales descargadas.
- Ejemplo original **sÃ³lo inventario**:10clientes,68racks,311equipos,5408puertos,623conexiones. No es el dump ni la seguridad de una instalaciÃ³n existente. El helper crea otro laboratorio PostgreSQL nuevo en cada ejecuciÃ³n y desactiva expresamente MFA en esa demo HTTPloopback.

## SelecciÃ³n y comprobaciones

Se construye en clon separado del Ã¡rbol concurrente. `BASELINE-SOURCES.json` identifica las fuentes de producto seleccionadas; `PUBLICATION-TRANSFORMS.json` conserva las seis sustituciones anteriores de contraseÃ±as constantes de fixtures por CSPRNG. No se cambian contraseÃ±as de usuarios ni cÃ³digo del servidor para publicar.413inputs congelados del catÃ¡logo/actualizaciÃ³n45 se contrastan por SHA256; la identidad de fuente no afirma reproducciÃ³n binaria.

La compilaciÃ³n, el ejemplo PostgreSQL17.11 real y la regresiÃ³n del frontend se ejecutan sobre ese clon. Se corrige el cargador local del ejemplo: conserva el perfil15 y admite explÃ­citamente el45, con sus digests completos; rechaza versiones desconocidas e historias incompletas. PreservaciÃ³n de seguridad, permisos restringidos, transacciÃ³n, auditorÃ­a e idempotencia permanecen comprobadas. La regresiÃ³n aÃ±ade el contratoK propio requerido y concilia el vocabularioL con las dos extensiones alemanas exactas, sin modificar el contrato histÃ³rico ni el producto.

Escaneo Gitleaks8.30.1 con reglas oficiales intactas: historial previo sin coincidencias; las coincidencias de la selecciÃ³n se contrastan una por una con identificadores pÃºblicos del catÃ¡logo, digests y dos literales de fuente. Se conserva la salida original con hallazgos y su clasificaciÃ³n por archivo/lÃ­nea/hash; no se presenta como un escaneo de cero coincidencias. La revisiÃ³n independiente y las salidas completas quedan en la evidencia local del lote, excluyendo credenciales y binlogs.

## LÃ­mites

No hay nueva licencia abierta de RackClick, Release binaria, workflow de despliegue ni cambio de dependencias. Se conservan los avisos de terceros y la referencia offline ya publicada; se añade el [aviso de procedencia NetBox y su licencia CC0 íntegra](../THIRD-PARTY-NOTICES.md). Instaladores, herramientas binarias, bases/dumps, credenciales, certificados privados, claves/sobres MFA, sesiones, transcripciones y registros privados quedan fuera. Las condiciones de redistribuciÃ³n nativa siguen pendientes de la revisiÃ³n anterior.

La actualizaciÃ³n45 de la instalaciÃ³n existente ya se ensayÃ³ por separado. **New/Restore45, postboot45, recuperaciÃ³n portable/emergencia/rotaciÃ³n MFA y QA final siguen pendientes.** Esta publicaciÃ³n no los acredita, no opera las VM y no modifica el ledger: Ã­ndice de cierre14,76/100 sin incremento; no es un nuevo porcentaje global.

GitHub identifica la portada raÃ­z y permite enlaces relativos entre idiomas: [documentaciÃ³n oficial de README](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes). El commit vigente se consulta en [historial de main](https://github.com/was-car/RackClick/commits/main/); los hashes y el contraste remoto de esta entrega se registran localmente despuÃ©s del push.

## Regresión de pruebas históricas

El dominio ejecutó76/76 y el frontend1031/1031. La ejecución inicial del proyecto de calidad con PG17.11 produjo488total:468PASS,10FAIL y10omitidas. Los diez fallos procedían de expectativas de catálogo/esquema anteriores; se conciliaron en cinco archivos de pruebas preservando los históricos y sus negativos. Las cinco clases completas repitieron42/42 sin omitidas. No se presenta ese foco como una segunda ejecución íntegra de488casos; las diez omisiones del entorno y la salida inicial se conservan explícitamente. No se cambió código de producto por esos fallos.

## Regresión de pruebas históricas

El dominio ejecutó76/76 y el frontend1031/1031. La ejecución inicial del proyecto de calidad con PG17.11 produjo488total:468PASS,10FAIL y10omitidas. Los diez fallos procedían de expectativas de catálogo/esquema anteriores; se conciliaron en cinco archivos de pruebas preservando los históricos y sus negativos. Las cinco clases completas repitieron42/42 sin omitidas. No se presenta ese foco como una segunda ejecución íntegra de488casos; las diez omisiones del entorno y la salida inicial se conservan explícitamente. No se cambió código de producto por esos fallos.
