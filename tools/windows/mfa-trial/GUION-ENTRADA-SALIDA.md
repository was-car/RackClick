# Guion de entrada y salida · ensayo MFA-INIT (L2k, edicion 03)

Escrito para: operador del equipo de ensayo y revision de Codex. Los valores entre `<...>` se sustituyen en cada ejecucion; no se escriben valores reales en este documento.

## 1. Entrada que recibe el equipo

| Dato | Forma | Quien lo entrega |
|---|---|---|
| ZIP `RackClick-MFA-Ensayo-03.zip` | archivo | desarrollo, con su ruta de origen |
| SHA256 del ZIP | 64 caracteres hexadecimales en minusculas | desarrollo, por canal separado del ZIP |
| SHA256 de `SHA256SUMS` | 64 caracteres hexadecimales en minusculas | desarrollo, por canal separado del ZIP |
| Nombre de servicio | solo si hay varios `RackClick*` | operador |
| UUID de ensayo | generado por el propio ensayo al ejecutar `run` | sale en pantalla |

## 2. Verificacion externa (antes de extraer o ejecutar cualquier archivo)

```
Get-FileHash -Algorithm SHA256 -LiteralPath .\RackClick-MFA-Ensayo-03.zip
```

El resultado debe ser igual al SHA256 del ZIP recibido por el canal separado. Si no coincide, no extraiga el ZIP ni ejecute ningun `.cmd`. La verificacion interna del paquete (`SHA256SUMS`) no sustituye a este paso: no autentica su propio origen.

## 3. Comandos

Carpeta de trabajo: una carpeta nueva y vacia donde se extrae el ZIP. Consola elevada.

```
INICIAR-ENSAYO-MFA.cmd <SHA256-de-SHA256SUMS>
```
Modo Check: solo lectura. No crea carpetas ni escribe recibos.

```
INICIAR-ENSAYO-MFA.cmd run <SHA256-de-SHA256SUMS>
```
Modo Run: exige consola, elevacion, LEAO fuera, el SHA256 indicado y la confirmacion escrita.

Con varios servicios `RackClick*` el ensayo se detiene y lista sus nombres: vuelva a lanzar con el nombre como ultimo argumento, por ejemplo `INICIAR-ENSAYO-MFA.cmd run <SHA256> <NOMBRE-DEL-SERVICIO>`.

Equivalente directo en PowerShell (solo si el operador lo necesita):
```
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Invoke-MfaInitTrial.ps1 -Mode Check -ExpectedSumsSha256 <SHA256>
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Invoke-MfaInitTrial.ps1 -Mode Run -ExpectedSumsSha256 <SHA256> -ServiceName <NOMBRE-SI-HAY-VARIOS>
```

## 4. Lo que el ensayo llama internamente

Primera y unica invocacion de servidor en cada paso, con stdin JSON de una linea:

```
runtime\dotnet.exe servidor\RackClick.Server.dll --mfa-keys-init
```

stdin (una linea UTF-8 sin BOM):

```
{"instancesRoot":"<C:\ProgramData\RackClick-MFA-Ensayo-03-UUID>","installationId":"<UUID>","readerSid":"<SID-DE-LA-CUENTA-DEL-SERVICIO>"}
```

El entorno del proceso hijo no hereda profiler, EventPipe, perf maps ni hooks: se fija `DOTNET_EnableDiagnostics=0` y se desactiva el profiling solo en ese proceso.

No se ejecuta el host normal, ni comandos de PostgreSQL, ni `--migrate`, `--bootstrap` o `--recover-admin`.

## 5. Salidas esperadas

| Ejecucion | Estado | Codigo | Residuo | Salida del proceso |
|---|---|---|---|---|
| 1.a (primera, carpeta nueva) | `created` | (ninguno) | `none` | `0` |
| 2.a (misma carpeta) | `rejected` | `mfa_keystore_init_exists` | `none` | `1` |

Ninguna otra combinacion es correcta. Ante cualquier otro resultado el ensayo se detiene, conserva el estado, no reintenta y muestra el resumen de parada.

Antes y despues de la segunda ejecucion el ensayo compara la huella del estado: rutas, tamanos, SHA256 de cada archivo y hash del ACL de cada entrada, incluida la carpeta raiz. Debe ser identica.

## 6. Salidas de texto

- Consola: plan, resultado de cada paso y una linea JSON final `{"status":...,"code":...}`.
- Resumen sanitizado, siempre (tambien en parada): resultado, codigo de parada, paso observado, pasos no ejecutados, paquete, equipo, UUID, servicio, cuenta, SID, ejecuciones y huella. Se muestra en pantalla y se guarda en `%ProgramData%\RackClick-MFA-Ensayo-03-<UUID>.resumen-sanitizado.txt`.
- Recibo privado: `%ProgramData%\RackClick-MFA-Ensayo-03-<UUID>.recibo-privado.json`. No se envia.

## 7. Criterio de exito

- Ambos pasos cumplen la tabla del apartado 5.
- La huella del estado no cambio entre la primera y la segunda ejecucion.
- El resumen indica elevacion observada, UUID, servicio, cuenta y SID.

## 8. Lo que el ensayo no prueba

- No demuestra que el servicio lea la clave ni que su token funcione.
- La consulta del SID por SCM no equivale a ejecucion bajo ese SID.
- No habilita MFA para usuarios ni activa `MfaKeyStore:Enabled`.
