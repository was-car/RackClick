# Catálogo de backups y retirada de versiones MFA

09.11.2026 · Herramientas nuevas de fuentes, **sin desplegar en D/E ni incorporar a un instalador**. El binario instalado anterior no contiene estos comandos. Ensayar primero con la candidata completa correspondiente y un laboratorio independiente. No copiar una DLL aislada a D.

## Qué significa retirar

Retira una versión no activa del anillo que usa `WindowsMfaKeyProvider`. Después `GetKey(versión)` la rechaza. **Conserva el archivo DPAPI original y el anillo anterior**: no borra material cifrado ni afirma destrucción criptográfica. No cambia TOTP, factores, sesiones, desafíos, usuarios, permisos o gracia45. La rotación/recifrado y su testigo DB son F-06.03, otra operación.

El catálogo cubre todas las raíces de backups retenidos **declaradas por el operador autorizado**. El software comprueba sus objetos y conjuntos exactos, pero no puede descubrir una copia en un USB desconectado o una raíz omitida. Confirmar cobertura significa incluir también esas copias: si no están disponibles o clasificadas, detenerse; no declararlas inexistentes para continuar.

## Requisitos y preparación

1. Windows PowerShell5.1 **como administrador**: Inicio → escribir `Windows PowerShell` → botón derecho → **Ejecutar como administrador**.
2. Servicio identificado y detenido. El operador no lo detiene automáticamente. La CLI verifica en SCM su cuenta/SID, estado y las rutas exactas de runtime, host y configuración de esa instalación. No basta un nombre parecido o un PID.
3. Runtime .NET10 oficial, PostgreSQL17.11 y herramienta publicada desde estas fuentes. `ToolDirectory` incluye `SHA256SUMS`; su pin se recibe por referencia independiente. Se verifican y retienen los bytes de herramienta/dependencias durante el hijo.
4. UUID de instalación, servicio, puerto PostgreSQL y la raíz MFA exacta. En el perfil nativo: raíz de instancias Windows `…\RackClick\Instances`, raíz MFA `…\Instances\<uuid>\security`, claves `…\security\<uuid>\mfa-keys`. No cambiar esos niveles.
5. Credencial **SQL de mantenimiento** del propietario `rc_owner_<uuid sin guiones>`, separada de ejecución. Se solicita oculta y viaja por stdin. La herramienta no habilita cuentas, cambia contraseñas ni usa la cuenta runtime para DDL. Si esa credencial no está disponible, usar el procedimiento de mantenimiento SQL; no adivinarla ni pegarla en el chat.
6. Raíces de copias privadas y con autoridad de escritura delimitada: operador/SYSTEM/Administradores y cuenta identificada del servicio. Lectura/escritura concedida a otros principales provoca rechazo. No copiar/mover/importar backups desde otros medios durante mantenimiento; la producción de copias debe respetar el protocolo de admisión.

## Preparar la declaración de catálogo

Una entrada corresponde a un backup con `database/manifest.json`, `database/data.dump` y `mfa-inventory.json`, más el recibo externo y su SHA256 independiente producido por el operador de inventario. El catálogo conserva el recibo, no el sobre ni su contraseña. Reutilizar [el operador de backup con inventario](BACKUP-MFA-CON-INVENTARIO-DESARROLLO.md).

Formato de la declaración JSON UTF8 sin BOM:

```text
format: RackClick.MfaBackupCatalog
formatVersion: 1
installationId: UUID exacto
catalogId: UUID nuevo de esta generación
operatorSid: SID de la sesión elevada que la confirma
confirmedUtc: DateTime.UtcNow.ToString('O')
coverage: all-retained-roots-declared
roots: [todas las carpetas que contienen las copias retenidas]
entries: [{backupDirectory, receiptBase64, receiptSha256}, ...]
```

Cada `backupDirectory` es hijo directo de una raíz. `receiptBase64` contiene los bytes exactos del recibo privado; `receiptSha256` es su pin externo, **no** uno recalculado y aceptado sin referencia. Se deben contrastar antes de preparar la entrada:

```powershell
$bytes = [IO.File]::ReadAllBytes($rutaRecibo)
$medido = (Get-FileHash -LiteralPath $rutaRecibo -Algorithm SHA256).Hash.ToLowerInvariant()
if ($medido -cne $pinExternoDelRecibo) { throw 'Recibo distinto. Detenerse.' }
$entrada = @{ backupDirectory=$rutaBackup; receiptBase64=[Convert]::ToBase64String($bytes); receiptSha256=$pinExternoDelRecibo }
```

La lista vacía sólo es válida con al menos una raíz explícita y realmente vacía, cubierta por la confirmación del operador. Un backup desconocido, legacy sin inventario, parcial `INCOMPLETE`, desaparecido, alterado, de otra instalación o con campos extra **bloquea**. No se expira ni elimina. Para clasificar una copia histórica hay que contrastar su dump/sobre/censo en laboratorio nuevo; no asignarle las versiones de la DB actual por conjetura.

## Inicializar, verificar y retirar

Usar `tools/windows/Invoke-RackClickMfaKeyMaintenance.ps1`; no hay endpoint HTTP. Parámetros comunes:

```powershell
$comun = @{
    DotnetPath = '<ruta del dotnet.exe oficial>'
    ToolDirectory = '<herramienta verificada>'
    ExpectedToolSumsSha256 = '<SHA256 externo de SHA256SUMS>'
    InstancesRoot = '<raiz MFA terminada en uuid\security>'
    InstallationId = '<uuid>'
    ServiceName = '<servicio exacto>'
    PostgresPort = 55441
}
```

- Primera generación: `& .\tools\windows\Invoke-RackClickMfaKeyMaintenance.ps1 @comun -Action catalog-initialize -CatalogPath '<declaracion.json>'`.
- Guardar el `catalogSha256` devuelto fuera del catálogo. La confirmación `CONFIRMO CATALOGO <uuid>` acredita que se declararon todas las raíces retenidas, incluidas las externas.
- Verificar: mismo script con `-Action check -ExpectedCatalogSha256 '<pin>'`. Es mantenimiento exclusivo: requiere servicio detenido, adquiere lock y puede crear el archivo privado de exclusión; no es una consulta online del dashboard.
- Preparar `$operacion = [guid]::NewGuid().ToString('D')` y guardarla junto al UUID/pin. Retirar: `-Action retire -ExpectedCatalogSha256 '<pin>' -Candidate 2 -OperationId $operacion`. Exige `CONFIRMO RETIRADA <uuid> v2`.

Activa, versión desconocida, cualquier factor pending/active/disabled y cualquier backup que la requiera impiden la retirada. Se autentican también los factores conservados con su clave/AAD reales. El catálogo se vuelve a escanear y censar bajo exclusión antes de publicar.

El host y las copias nuevas participan en la lease PostgreSQL compartida. El host conserva además lectura del anillo durante toda su vida; mantenimiento exige acceso de escritura sin escribir como preflight. ACCESS EXCLUSIVE sobre factores impide cambios/snapshots durante el censo/publicación. Una sesión de PG perdida no basta para que un host vivo deje de excluir mantenimiento.

## Interrupción y generaciones nuevas

Ante un fallo, **no repetir `retire` ni generar otro UUID**. Conservar el resultado y los archivos. `mfa-maintenance-fence.json` bloquea arranque antes del listener; el journal privado conserva autoridad, versiones, identidades y hashes de anillos, sin claves claras o connectionStrings.

Reanudar con `-Action resume -ExpectedCatalogSha256 '<mismo pin>' -OperationId '<misma operacion>'`. Confirma `CONFIRMO REANUDAR <uuid> <operacion>`. Sólo se acepta el anillo original o final previsto; un tercer estado no se adopta. Si ya terminó, se reconoce el journal verificado de forma idempotente. No reconstruye recibos ni cambia datos para lograr éxito.

Un journal/fence parcial durante su creación o una alteración externa puede requerir diagnóstico: queda bloqueado, sin reparación/adopción automática. No borrar fence/journal ni modificar las claves a mano. Los cortes por excepción ensayados no acreditan durabilidad universal frente a pérdida eléctrica o todos los cortes de proceso de F-06.03.

`catalog-refresh`, con nueva declaración/UUID de catálogo y el pin actual, permite **añadir** raíces/entradas. Conserva las generaciones anteriores y no permite retirar raíces, entradas o pines existentes. La expiración de backups necesita la política de retención correspondiente; no se introduce aquí.

Tras éxito y retirada del fence, iniciar sólo el servicio identificado desde su procedimiento. El guard revalida admisión antes de servir peticiones. Esta entrega de fuentes no cambia el servicio, el MFA o los datos de D/E ni constituye adopción de producción.

[Plan y decisiones](PLAN-F0602-CATALOGO-Y-RETIRADA.md) · [Resultado/revisión](../evidence/s1-20261109/f06-02-retirada/RESULTADOS.md).
