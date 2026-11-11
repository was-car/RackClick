# Ensayo independiente de despliegues privados 14

25.10.2026. Codex coordinador ejecuta; `bundle02_native_review` revisa estáticamente las interfaces y el observador/resultado. No se compila producto ni se modifican fuentes de Claude. Este ensayo usa **la candidata congelada anterior a D14-05**, para avanzar con los orquestadores mientras Claude prepara su corrección.

## Resultado real

**Recorrido final completo: PASS, exit 0, 128,06 segundos.** Son ejecuciones de operadores Windows con PostgreSQL 17.11 real y HTTP sobre HTTPS local; no fixtures que sustituyen esos operadores. Dos instancias nuevas, tres arranques del launcher y tres paradas normales, sin terminación forzada.

| Recorrido | Comprobación ejecutada |
|---|---|
| `New-RackClickPrivateDeployment.ps1` | Stage14 + instancia nueva14 + perfil HTTPS + recibo: `deployment_prepared`. Verificador posterior `deployment_verified`. |
| Destino ya existente | Nuevo intento rechazado `preflight_destination_exists`, exit1; recibo original intacto. |
| Arranque privado inicial | `Invoke-RackClickPrivateDeployment -Operation Start` llega a ready; `/health/ready` informa esquema14. Certificado verificado con el PEM propio como confianza del cliente, sin desactivar verificación TLS ni escribir almacenes de Windows. |
| Login/escritura | Login con credencial generada por New; cambio de Systemhaus sin CSRF rechazado403. Escritura con CSRF/revisión/idempotencia y lectura posterior correctas. No se imprime la credencial ni la cookie. |
| Backup del origen | Operación pública `Backup` devuelve `deployment_backup_complete` mientras PostgreSQL está en marcha. |
| Parada y nuevo arranque | Operación `Stop` confirma parada; segundo arranque/login conserva el nombre guardado. Es reinicio del launcher/procesos, **no reinicio de Windows**. |
| `Restore-RackClickPrivateDeployment.ps1` | Backup14 → otra instancia14: Stage, recuperación, HTTPS y recibo nuevos; `deployment_prepared` y `deployment_verified`. |
| Arranque del restaurado | Sesión del origen rechazada401; login del administrador recuperado correcto, nombre guardado conservado y nuevo backup completo. |
| Cierre | Tres paradas con `postgresCleanStop=true` y `applicationGracefulExit=true`; sin `postmaster.pid`, los cuatro puertos asignados cerrados y entradas congeladas intactas. |

Las cookies no se limitan por puerto: se reenvió la cookie del origen al restaurado en el mismo host, con el contexto TLS propio del restaurado. El401 es una comprobación HTTP de rechazo de esa sesión después de recuperar; no una afirmación de pruebas MFA completas.

Los tres eventos registran **`applicationHttpDrain=false`**. Se acredita salida normal de aplicación y PostgreSQL, pero no drenaje HTTP ni el tratamiento de peticiones activas durante parada. [Eventos saneados](PARADAS.json).

## Artefactos y repetición

- Manifiesto14: `2ec9105661db0f5c9a97d58e2a7f44e69bfd7e1903493b72f0fc57cc94c4b71a`.
- DLL: `f11a689e49dd507b79c4b9a43ce8670cd02fc46aa5325e58caa980fe959a1085`.
- Operadores de la copia congelada de la revisión anterior: New `03262fe4…`, Restore `9dae3e89…`, NewRecovered `0f53cf25…`. Pins completos en [ENTRADAS.json](ENTRADAS.json). No se mezcla la DLL antigua con el operador que Claude modifica para D14-05.
- Observador versionable sin secretos: [replay_deployments.py](replay_deployments.py). Exige salida nueva bajo `.local`, puertos dinámicos, certificados/secretos locales y Job propio que acota descendientes. No instala cuentas Windows, servicios, firewall ni confianza global.
- Resultado final íntegro: [RESULTADOS.json](RESULTADOS.json). Primera ejecución: [PRIMER-INTENTO.json](PRIMER-INTENTO.json). Revisión separada: [REVISION-OBSERVADOR.md](REVISION-OBSERVADOR.md).

El primer intento preparó/verificó New y rechazó el destino existente, pero falló **antes de arrancar runtime** por un error del observador: la función `http` ocultaba el módulo `http.cookiejar`. Se corrigió únicamente el alias de importación y se repitió todo en destinos nuevos. No se cuenta ese intento como un recorrido completo ni como un fallo de producto. Sus archivos/diagnósticos se conservan privados.

Comando de repetición con las mismas entradas congeladas, con el repositorio situado en la ruta indicada:

```powershell
$raiz = 'C:\RackClick_SVR'
$copia = "$raiz\.local\propagation14-review-20261025-55aad15a6b86\tree"
$salida = "$raiz\.local\deployment14-repeticion-$([guid]::NewGuid().ToString('N'))"
& 'C:\Python312\python.exe' -X utf8 -B `
  "$raiz\evidence\s1-20261025\deployment14-privado-codex\replay_deployments.py" `
  --repo $raiz --operators "$copia\tools\windows" `
  --distribution "$copia\.local\distribution14\candidata-01" `
  --dotnet "$copia\.local\dotnet-10.0.401\dotnet.exe" `
  --pg-bin "$copia\.local\labs\mfa-m1-20261023\pgsql\bin" --out $salida
```

Se requieren esos binarios/artefactos y los helpers `pg_support.py`/`windows_job.py` del repositorio. **No es autosuficiente desde un clon limpio**. Perfiles, contraseñas, certificados privados, dumps y logs sólo en `.local/deployment14-review-20261025-4df6ce0776ff/`.

## Límites y siguiente paso

- Se cierran estos recorridos privados New14 y Restore14→14 sobre los artefactos identificados, junto con el arranque real del launcher de laboratorio. La revisión anterior comprobó por separado el operador interno 13→14; hoy no se acredita el wrapper privado completo 13→14.
- **No se valida D14-05.** Este backup de laboratorio no lleva desafíos MFA pendientes. La corrección que Claude comunica se mantiene como declaración del implementador hasta recibir y revisar sus bytes, pins y resultados.
- No se ejecuta `Invoke-RackClickServerRuntime.ps1` como servicio, ni instalación elevada desde cero, confianza desde otro equipo, drenaje HTTP o reinicio del sistema. El rechazo de instalación14 del bundle03 se conserva.
- No cambia la candidata, el paquete, el perfil de distribución ni la disponibilidad visible de QA. Catálogo, guías y resultados de Wascar conservados. Sin commits/push, QA, VM, servicios instalados o bases existentes.
- Próximo trabajo: revisar D14-05 y la candidata nueva; repetir focos de recuperación y compatibilidad de estos orquestadores con sus pins; después candidata interna de instalación y Windows Server limpio/reinicio. Evitar repetir toda la suite por inercia.

**Avance global aproximado: 78 %, sin incremento automático.** Avanzó la evidencia operativa de creación/restauración privada; aún faltan entrega Windows completa, recuperación MFA, integración funcional pendiente y QA/adopción final. Controles del cierre en `VERIFICACION.json`; manifiesto del bloque en `SHA256SUMS.txt`.
