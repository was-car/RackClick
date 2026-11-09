# Ensayo offline de recuperación portable MFA · F-05.04

Herramienta de laboratorio para demostrar LEAO → otra máquina Windows y otro SID, conservando dos factores sintéticos cifrados. No es un instalador ni un operador de recuperación del producto. No abre listener, consulta PostgreSQL, modifica servicios o configura MFA. No debe copiarse sobre una instalación ni sobre la suite de calidad.

## Identidad y componentes

El nombre del ensamblado es **`RackClick.Quality.Tests.dll`**, por decisión explícita del coordinador: utiliza el acceso amigo ya existente para invocar componentes internos aprobados. Este ejecutable aislado **no es** el proyecto `development/server/tests/RackClick.Quality.Tests`. La identidad amiga no es una frontera de autorización ni una modificación del producto.

Se referencia la DLL **Debug** de F-04.01, con el escritor corregido, sin reconstruir el servidor. El ejecutable de ensayo es **Release**. La cadena exacta está en `evidence/s1-20261103/f05-04-portable/implementacion/MANIFIESTO-TOOL.json`. No se afirma identidad con la DLL instalada en D. Se enlazan, sin editarlos, `Native.cs` y `Measure.cs` de `tools/mfa-service-read-probe`.

Se reutilizan `WindowsMfaKeyStoreWriter`, `WindowsMfaKeyRecoveryFiles`, `WindowsMfaKeyProvider`, `WindowsMfaKeyFileReader`, `MfaKeyRing`, `MfaKeyRecoveryEnvelope`, `MfaKeyRecoveryPayload` y `MfaSecretCipher`. No hay paquetes NuGet nuevos, nuevo formato criptográfico, KDF, rotación o recifrado de factores.

## Compilación

SDK fijado por `global.json`: 10.0.401. El `runtimeconfig` generado debe exigir **Microsoft.NETCore.App y Microsoft.AspNetCore.App 10.0.12**, con `rollForward: Disable`. No usar un runtimeconfig de otra herramienta.

Propiedades obligatorias: `RackClickServerDir` (directorio con las cuatro DLL referenciadas) y `RackClickServerSha256` (SHA256 completo de la DLL del servidor). Conservar `BaseIntermediateOutputPath` y `BaseOutputPath` en una carpeta privada nueva. Ejecutar `restore` y `build --no-restore -c Release` con estas mismas propiedades y un binlog privado único por llamada, por ejemplo `'-bl:<privado>/build-{}.binlog'`. Los binlogs no se versionan.

Transportar sólo los siete archivos no PDB enumerados en el manifiesto. El coordinador verifica y retiene esos bytes y el runtime antes de ejecutar. El ejecutable vuelve a comprobar el digest de la DLL del servidor antes de leer stdin. No se ejecuta una reconstrucción posterior como si conservara el digest anterior.

## Interfaz exacta

Hay tres verbos, cada uno recibe **un objeto JSON por stdin redirigido**, hasta 16.384 caracteres. No hay secretos en argumentos, stdout o stderr. Los campos extra y duplicados se rechazan. Los GUID son no vacíos, minúsculos y en formato `D`; las huellas son SHA256 hexadecimal minúsculo de 64 caracteres. La contraseña se proporciona sólo a `source` y `recover`, con UTF-8 válido y 12–256 puntos Unicode. El tool no la escribe en disco.

Campos de `source`, exactamente:

```text
schemaVersion: 1
operationId: GUID
expectedHost: "LEAO"
baseDirectory: "C:\\RackClick_SVR\\.local\\f0504-<nombre nuevo>"
installationId: GUID de origen
password: texto privado
```

El destino debe ser hijo directo de `.local`, empezar por `f0504-` y no existir. Crea carpetas privadas con descriptor desde creación exclusiva. La confianza **de laboratorio** incluye al usuario de LEAO, SYSTEM y Administradores. El lector/custodio de los fixtures es el SID Usuarios; no es la configuración productiva. Genera claves nuevas de 32 bytes, versiones 1 retirada y 7 activa, y dos secretos TOTP sintéticos nuevos de 20 bytes. Sólo persiste factores cifrados y sus compromisos SHA256, nunca sus secretos en claro.

Archivos privados de origen:

```text
<base>/source-store/<origen>/mfa-keys/{ring.json,key-v1.dpapi.json,key-v7.dpapi.json}
<base>/source-incomplete-store/<origen>/mfa-keys/{ring.json,key-v7.dpapi.json}
<base>/envelopes/export.rckey
<base>/envelopes/missing-retired.rckey
<base>/datos/factors.json
```

El segundo sobre es un negativo real: sólo contiene la clave activa 7. El fixture de factores sigue requiriendo 1 y 7. Contraseña y sobres se transportan por separado, bajo responsabilidad del coordinador.

Campos de `recover`, exactamente:

```text
schemaVersion: 1
operationId: GUID de la operación de origen
expectedHost: nombre observado y fijado de E
baseDirectory: "C:\\ProgramData\\RackClick-F0504-<operationId>"
originInstallationId: GUID de origen
installationId: GUID nuevo de destino
serviceName: servicio estándar medido
expectedServiceSid: SID observado y fijado del servicio
custodianSid: SID del custodio del sobre, distinto del servicio
password: texto privado
envelopeSha256: digest del sobre de entrada
factorsSha256: digest del fixture transportado
adaptDestinationInstallation: booleano explícito
```

El coordinador prepara antes la base protegida, `envelope-in/export.rckey` y `datos/factors.json`. `instances` debe estar ausente. La base no puede atravesar puntos de reparse. `envelope-in` y el sobre deben satisfacer el lector aprobado: propietario SYSTEM/Administradores; confianza fija SYSTEM/Administradores; lectura del custodio indicado. El archivo de factores permanece privado. Los directorios de código son legibles por el servicio, pero nunca modificables por él. No adaptar ACL de datos o claves preexistentes para hacer pasar el ensayo.

`recover` requiere Windows elevado o SYSTEM y excluye LEAO. Se liga al servicio en ejecución mediante SCM, PID, imagen y SID, y comprueba que su token corresponde a una cuenta estándar. Si origen y destino difieren, `adaptDestinationInstallation` debe ser `true`; no se deduce. Antes de publicar, autentica el sobre, exige las versiones retirada 1/activa 7 y descifra ambos factores con sus AAD y compromisos. Sólo después llama al recuperador aprobado y comprueba ambos factores de nuevo. Cambia la identidad del anillo/entropía DPAPI, no los `systemhausId`, `userId`, `key_version` ni ciphertext de los factores. Este éxito todavía no prueba lectura efectiva bajo el servicio.

Campos de `verify`, exactamente:

```text
schemaVersion: 1
operationId: GUID de la operación
expectedHost: nombre observado y fijado de E
baseDirectory: la misma base aislada
originInstallationId: GUID de origen
installationId: GUID de destino
serviceName: el mismo servicio estándar
expectedServiceSid: SID observado del servicio
expectedProcessId: PID observado inmediatamente antes
expectedProcessStartUtc: fecha UTC observada, con precisión conservada
factorsSha256: digest del fixture transportado
```

No recibe contraseña. Retiene el proceso y comprueba fecha de creación, PID, imagen, SID y vínculo SCM antes y después. Duplica el token y comprueba suplantación/restauración de identidad. Bajo ese token lee la versión activa 7 y retirada 1, descifra ambos factores y verifica sus compromisos; rechaza seis combinaciones de AAD incorrecta (Systemhaus, usuario y versión para cada factor) y la versión inexistente 8. Comprueba denegación de escritura y `WRITE_DAC` sobre tres carpetas, anillo y dos claves: seis objetivos. Compara bytes y DACL/propietario del almacén antes/después. Esto es una medición acotada, no un cálculo universal del acceso efectivo o de todas las facultades de Windows.

## Salida y paradas

Una línea JSON, código de proceso 0 sólo para éxito. La envoltura informa `offlineOnly`, `notMfaActivation` y `productAdopted:false`. No imprime rutas, SIDs, contraseña, claves, factores, compromisos ni mensajes de excepciones. Los errores usan códigos/categorías constantes y, en recuperación, indican si `instances` está ausente o se preservó como laboratorio fallido. No hay retirada recursiva, sobrescritura ni reintento automático. Un resultado incierto se conserva y se revisa antes de seguir.

El UUID de la instalación D está rechazado en los campos de identidad. Esto **no distingue por sí solo dos clones Windows con el mismo nombre**: el coordinador debe fijar VMX/UUID físico de E, comprobar que es distinto de D y usar el host y raíz esperados. Las peticiones, fixtures, sobres, runtime y DLL transportadas se verifican por huella y se retienen durante la ejecución en el directorio protegido. No se pretende resistir a un administrador o SYSTEM que controle el proceso o las entradas.

## Alcance de aceptación

Los controles de LEAO sólo verifican creación sintética y rechazos locales. El coordinador ejecuta después las negativas de contraseña/origen/adaptación/material incompleto en E sin `instances`, la recuperación válida, la denegación del segundo intento y `verify` bajo el token real. Una DB/dump PostgreSQL de fixture, si procede, se prepara y valida por separado; esta herramienta no lo consume ni afirma haberlo restaurado.

Quedan fuera: uso del almacén MFA instalado, servicios/cuentas nuevos, UI/login TOTP, DB de producción, restauración nativa completa, activación, rotación, rewrap, códigos de emergencia, durabilidad ante corte y adopción. El borrado de arrays de claves/secretos no borra el `string` administrado de contraseña ni garantiza limpieza física de toda la memoria. Los restos privados se conservan deliberadamente.
