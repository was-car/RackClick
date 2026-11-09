# Sonda de acceso efectivo MFA · F-04.02

Herramienta de comprobación, sin referencia al producto ni paquetes NuGet. No instala, habilita MFA, genera claves, modifica ACL o arranca/detiene servicios. Se ejecuta como SYSTEM en la VM de ensayo **E**, coordinada por Codex. No ejecutar sobre D. El ejecutable rechaza LEAO y el UUID de D; el coordinador liga además el objetivo al VMX exacto de E, pues los clones pueden compartir nombre Windows.

`--measure` lee una petición JSON por stdin, limitada a 65.536 caracteres. Exige Windows, SYSTEM, nombre esperado y dos identidades de servicio estándar distintas. Consulta SCM/PID/binario/cuenta y liga el proceso por hora de creación antes/después. Duplica sólo el token de suplantación, comprueba SID efectivo dentro del bloque y restaura la identidad. Nunca ajusta privilegios.

## Entrada

```json
{
  "schemaVersion": 1,
  "expectedHost": "NOMBRE-DE-E",
  "installationIds": ["aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "11111111-2222-3333-4444-555555555555"],
  "actors": [
    {
      "label": "service13",
      "serviceName": "RackClick",
      "expectedSid": "S-1-5-21-1-2-3-1001",
      "targets": [
        {"label": "common-root", "path": "C:\\ProgramData\\RackClick", "isDirectory": true, "readExpected": true},
        {"label": "common-instances", "path": "C:\\ProgramData\\RackClick\\Instances", "isDirectory": true, "readExpected": true},
        {"label": "own-keys", "path": "C:\\ProgramData\\RackClick\\Instances\\aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee\\security\\aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee\\mfa-keys", "isDirectory": true, "readExpected": true}
      ]
    },
    {
      "label": "service14",
      "serviceName": "RackClickRestore",
      "expectedSid": "S-1-5-21-1-2-3-1002",
      "targets": [
        {"label": "common-root", "path": "C:\\ProgramData\\RackClick", "isDirectory": true, "readExpected": true},
        {"label": "common-instances", "path": "C:\\ProgramData\\RackClick\\Instances", "isDirectory": true, "readExpected": true},
        {"label": "other-keys", "path": "C:\\ProgramData\\RackClick\\Instances\\aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee\\security\\aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee\\mfa-keys", "isDirectory": true, "readExpected": false}
      ]
    }
  ]
}
```

Es sólo un ejemplo de **forma**, no el plan completo ni datos para ejecutar. El coordinador debe incluir ambos almacenes, sus padres protegidos, anillo/archivos DPAPI y management, con acceso propio/cross y las expectativas revisadas. Dos entradas de directorio común no acreditan todo F-04.02. Los identificadores, SID y servicio se miden en E; no se adivinan ni se copian de D.

Rutas permitidas: los dos padres comunes exactos mostrados y descendientes de los dos UUID de instalación declarados, dentro de `C:\ProgramData\RackClick\Instances`. No UNC/ADS/traversal ni el UUID de D. Los ancestros hasta C: sólo se observan para anclaje/reparse/metadatos; no se les impone el DACL privado de MFA.

## Derechos y resultado

Cada apertura usa `OPEN_EXISTING`, compartición de lectura/escritura/borrado y derechos individuales: `READ_DATA/LIST_DIRECTORY`, `WRITE_DATA/ADD_FILE`, `APPEND_DATA/ADD_SUBDIRECTORY`, `WRITE_EA`, `WRITE_ATTRIBUTES`, `DELETE`, `WRITE_DAC`, `WRITE_OWNER` y, en carpetas, `DELETE_CHILD`. Sólo se abre/cierra el identificador; no se llama a ReadFile, WriteFile, SetAcl, truncate o delete.

La lectura tiene la expectativa explícita por actor/objetivo. Los derechos de mutación siempre deben denegarse. **Sólo Win32 5 significa denegación correcta**; ruta ausente, sharing violation y otros errores fallan. Una concesión inesperada falla aunque no se utilice. La medición de un derecho no concede ese derecho ni cambia la ACL.

La huella antes/después incluye tipo, atributos, volumen/identidad, enlaces, tamaño, mtime y descriptor propietario/DACL de objetivos y ancestros. Rechaza redirección, reparse, tipo incoherente y hardlinks en archivos. No incluye atime. **No lee ni calcula hashes del contenido de los archivos MFA o de management**; no prueba igualdad byte a byte. Las ACL se publican con máscaras y principales clasificados (`system`, `administrators`, actor o `other`), sin rutas/SID en la salida. `protectedDacl` y `ownerFixedTrust` son observaciones: la política de cada nodo, y especialmente los ancestros de lectura pública, se concilia en la revisión de la matriz; no hay una regla privada universal aplicada a C: o ProgramData.

Salida: una línea JSON, exit0 sólo para `verified/effective_acl_verified`, y exit1 para rechazo/fallo. `verified` se refiere a **la matriz solicitada**, no por sí solo a todo el checkpoint ni a una activación de MFA. El resultado liga el SHA256 del texto JSON recibido y el host esperado. `keysRead=false` indica que no se leen claves ni blobs; la apertura de lectura se comprueba sin leer datos. Se preservan los fallos y no se reintenta automáticamente.

## Invocación del auxiliar PowerShell

`Invoke-MfaAclProbe.ps1` exige SYSTEM y verifica/retiene en lectura la DLL, deps, runtimeconfig y petición mediante hashes recibidos aparte. Arranca sólo el proceso propio con entorno de .NET/profiler/hooks aislado, diagnósticos apagados y roll-forward desactivado. No crea ficheros de informe; el coordinador recoge stdout en su carpeta de ensayo. No debe ejecutarse hasta la revisión de esa entrega.

Parámetros: `-RuntimePath`, `-ProbeDirectory`, `-RequestPath`, `-ExpectedAssemblySha256`, `-ExpectedDepsSha256`, `-ExpectedRuntimeConfigSha256`, `-ExpectedRequestSha256`. El runtime y la sonda deben estar en una ubicación de código accesible a ambos SID. No se copian binarios a las instalaciones ni se alteran sus permisos para facilitar la prueba.

## Compilación y selftest

Desde una copia nueva de esta carpeta, SDK 10.0.401 fijado, sin apphost. El runtime es **10.0.12 exacto**, el ya usado en los instaladores, con roll-forward desactivado; no usar el runtimeconfig inicial que solicitaba 10.0.0. Cada invocación MSBuild conserva binlog único **privado**:

```powershell
dotnet restore .\RackClick.MfaAclProbe.csproj --locked-mode '-bl:C:\carpeta-privada\restore-{}.binlog'
dotnet build .\RackClick.MfaAclProbe.csproj --no-restore -c Release '-bl:C:\carpeta-privada\build-{}.binlog'
dotnet .\bin\Release\net10.0-windows\RackClick.MfaAclProbe.dll --selftest
```

El selftest usa únicamente el token propio y archivos TEMP sintéticos; valida parser, Win32, denegación WRITE_DATA, error distinto de 5 y restauración del token. El propietario del fixture conserva WRITE_DAC implícito: **no** se presenta este selftest como prueba de denegación WRITE_DAC o segundo token de servicio real. No llama a SCM. La matriz de servicios sólo se ejecuta con `--measure` y el guion validado de E.
