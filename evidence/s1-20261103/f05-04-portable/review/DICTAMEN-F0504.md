# Dictamen independiente · F-05.04 · paso17

03.11.2026. **Favorable para cerrar exclusivamente F-05.04 (+1/2)** por el recorrido portable offline ejecutado entre Windows LEAO y Windows Server E. No cierra F-05.05, F-05 completo, R-04 ni la integración/aceptación de un Restore de aplicación.

## Resultado contrastado

- Origen y destino tienen UUID de máquina distintos y comprobados. Material completamente nuevo y sintético: anillo con1retirada/7activa y dos factores cifrados con sus Systemhaus/usuario/versión originales. El destino usa otro `installationId`, adaptado expresamente mediante el recorrido aprobado de recuperación y reprotección DPAPI.
- La ronda2 contiene **siete recibos de hijo coherentes y ordenados**. Sin adaptación, contraseña incorrecta, versión retirada requerida ausente y origen incompatible se rechazan antes de crear `instances`. El positivo recupera las dos versiones; la repetición sobre destino existente se rechaza y conserva su snapshot.
- El verificador autentica/descifra **dos factores** mediante el proveedor recuperado bajo token estándar efectivo del servicio destino, ligado a SCM/PID/cuenta/SID/tiempo/imagen. Comprueba restauración de identidad,7activa y lectura de1retirada. **Seis cambios de AAD** —Systemhaus, usuario y versión para cada factor— fallan; versión8ausente se rechaza.
- En los **seis objetivos** del almacén nuevo, FILE_WRITE_DATA y WRITE_DAC están denegados: **6+6denegaciones,0concesiones,0indeterminados**. La huella de contenido/ACL del almacén permanece igual durante la verificación y la colisión. Esos12intentos no se presentan como repetición de toda la matriz F-04.02.
- Hay un **dump PostgreSQL17.11 real** de2076bytes, limitado a una tabla/dos factores sintéticos cifrados y sus IDs/versiones. El recibo de inspección lo liga al fixture verificado; no contiene claves/anillo/sobre/contraseña y no es un backup completo del producto. Se transporta separado de los sobres y del canal de contraseña. No se restaura DB en E.

[Comprobación propia y hashes](COMPROBACION-F0504.json), [auxiliar ejecutado](Verify-Portable-Result.py), [recibos reales](../ejecucion/), [origen y alcance](../ORIGEN-Y-ALCANCE.json).

## Custodia, limpieza y preservación

El job/tarea coinciden con los pins aprobados para ronda2. Su terminación registra servicio previo igual, entrada privada retirada y ausencia de modificación del almacén instalado. El postflight confirma **las dos tareas ausentes** mediante leafHRESULT `0x80070002`, entrada privada ausente y las dos copias de sobre en E retiradas tras comprobar hash/ACL. En LEAO se retiró el archivo transitorio en claro; se conservan sobre fuente y contraseña protegida con DPAPI CurrentUser, en artefactos privados distintos del dump.

La contraseña era sintética y estuvo temporalmente en disco privado para alimentar stdin. **No se acredita borrado físico ni custodia externa productiva de Wascar**. El origen usa confianza/lector de laboratorio explícitos; la confianza destino es fija SYSTEM/Administradores y la cuenta estándar real sólo lee. La herramienta no escribe `management`, DB, configuración o material instalado del servicio. D no recibió comandos; no se abrieron factores existentes de D/E.

Dos precisiones se conservan sin reconstruir evidencia:

- Ronda1 falló antes del primer hijo por precedencia del alias `H`→`Get-History`; no acredita importación. Su residuo privado se retiró, tarea/namespace ausentes se comprobaron y servicios/PID coincidían antes de una ronda2 explícita con salidas/tarea nuevas. Los originales y su límite siguen registrados.
- El primer postflight etiquetó `image` aunque recogía la línea de comando SCM. No se equipara a la ruta del proceso: un suplemento posterior **sólo de lectura** compara `Process.Path`, PID y hora con el estado previo. He contrastado ese suplemento; no se repitió importación ni verificación del factor para corregirlo.

## Hallazgos y límites

**Ningún bloqueante pendiente para F-05.04.** Los controles previos de DACL nulo/ausente y de ausencia de tarea se corrigieron antes del Run. El conflicto de alias fue un defecto del harness observado y corregido, no un fallo del codec ni una recuperación silenciosa del producto.

El resultado es un almacén de ensayo en un namespace nuevo y una lectura bajo token real: **el servicio instalado no fue reconfigurado para usarlo**. Se verificó AEAD/AAD del factor, no un código TOTP ni login/HTTP, sesiones o API. No hay Restore DB adoptado, coordinador operativo D2 de journal/fence/marcador/conciliación, cortes de energía, nuevo instalador o aceptación del entorno recuperado. Los componentes actuales permiten este ensayo; no se anuncia una funcionalidad de Restore completa por sus métodos internal/IVT.

La separación demostrada es entre artefactos del laboratorio. El esquema del dump es sintético y limitado; las versiones requeridas son1y7, no un inventario universal de todos los backups retenidos. La conservación/integridad de instalaciones existentes se fundamenta en el alcance de código y en metadatos de servicios, sin leer ni hashear sus claves instaladas.

## Trabajo del revisor

Consulté criterio F-05.04/.05 y R-04; D2 técnico; `MfaSecretCipher.Seal/Open/Aad`; `Program.Source/Recover/Verify/ValidateFactors/LinkedToken` del harness; csproj/IVT y manifiesto; `Run-PortableTrial`, wrapper de tarea, coordinación/retirada/postflight; controles locales y recibos/metadatos anteriores/posteriores. Fuentes/hashes y símbolos de la revisión previa se conservan en [APTO](APTO-PARA-ENSAYO.md), [hallazgos](PRE-RUN-HALLAZGOS.md) y [APTO ronda2](APTO-PARA-ENSAYO-R2.md).

Ejecuté exclusivamente auxiliares documentales propios de hashes/conciliación y lecturas de fuente/metadatos; el final terminó con salida0 y verificó los siete hijos, terminación/tarea/postflight y suplemento de imagen. **No ejecuté** MSBuild, herramienta criptográfica, comandos de VM, SQL, servicios/cuentas/ACL ni abrí contraseñas, claves, sobres o contenidos del dump. Las mediciones reales corresponden al coordinador y están identificadas como tales.

**Recomendación:** acreditar sólo+1/2 del cierre restante:1565/84 = **18,63/100** si el coordinador lo registra. No es un porcentaje global nuevo del producto. F-05.05, integración operativa y R-04 siguen pendientes; no se modifica ningún criterio, peso o ledger desde esta revisión.
