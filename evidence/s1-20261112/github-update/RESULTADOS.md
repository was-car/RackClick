# Publicación privada48 y Demo50 trilingüe · 12.11.2026

Solicitud de Wascar: actualizar el GitHub existente. Destino privado `was-car/RackClick`, `main`; clon separado desde `fd43fc41a1738baa844aa6d300e0266fc585da36`. No se opera A/D/E, servicios ni snapshots. Los binarios de instalación siguen fuera de GitHub.

## Qué cambia

Fuentes revisadas hasta48, SQL046–048, mantenimiento y recuperación MFA, operadores18, pasos19–32 y planificación. Catálogo884revisiones/877modelos conservado.62archivos de Demo50trilingüe03 idénticos a la entrega revisada:17EN/17DE/16ES,180racks,1563equipos,20665puertos,2207conexiones,2553comandos. Fuente43 y868revisioneshistóricas, sin usuarios/sesiones/factores o contraseñas. README y guías EN/DE/ES actualizados. Se conservan las seis transformaciones CSPRNG de fixtures; no se publican sus valores históricos.

El cargador de los diez originales rechazó48 en prueba real antes del cambio. Se añadió sólo el perfil48 con digest exacto;15/45, permisos y negativos conservados.13/13 pruebas PG17.11 y smoke real con10clientes/5408puertos/HTTPloopback/MFAdesactivado. No se usa el cargador10 paraDemo50 ni se carga una instalación existente.

## Verificación y errores de preparación

- Build Release de la demo y proyecto de calidad con locks/versiones intactos; todos los comandos MSBuild con binlog privado.189/189 casos afectados de calidad, sin omisiones. No es la regresión íntegra del servidor ni un ensayo bajo SID de servicio.
- Python: la última corrida amplia dio53PASS de54, con1error por el bundle privado aún ausente. Se aportó la copia exacta fijada y las16pruebas afectadas repitieron16PASS. En preparación anterior faltó la variable de DLL y se usó una junction que el verificador rechaza por diseño: se corrigieron fixtures, no el producto. No se suma cada repetición como caso nuevo ni se presenta una corrida única54/54 que no se hizo.
- Los generadores de roadmap/plan requirieron incorporar sus referencias públicas faltantes y regenerar derivados tras actualizar documentación; checks finales coherentes, pesos y ledger sin cambios. No se copian logs privados para satisfacer referencias.
- Dos lanzadores privados solaparon una reescritura de `checks.json`; se concilian resultados desde los logs conservados/TRX. No se repiten pruebas para inventar un registro perdido.
- Escaneo completo de la selección con Gitleaks8.30.1 autenticado y reglas intactas. Los identificadores públicos/hash detectados se clasifican por catálogo validado o coincidencia exacta con archivos previamente revisados sin cambios. Consultar `ESCANEO-CLASIFICADO.json`; no se afirma un escaneo vacío. Los resultados crudos permanecen privados. La historia remota anterior se conserva sin reescritura.

La revisión independiente especifica comprobaciones propias separadas de los ensayos del coordinador. Commit y contraste remoto se registran después de publicar, sin auto-deploy ni cambio de visibilidad.

## Límites

A real es New17 más finalización acotada, no New18 completo. Servicio y datos se verificaron tras reinicio; primer chequeo automáticoHTTPS falló, el oficialmanual posterior pasó. No se reutilizan esas ejecuciones como pruebas nuevas de esta publicación. ColdNew18/Restore48/cambiodeRed48 y aceptación productiva continúan pendientes. Las rutas de entregas locales de los manuales no son descargas GitHub. Se mantiene26,63/100 del cierre restante, sin incremento por esta publicación.
