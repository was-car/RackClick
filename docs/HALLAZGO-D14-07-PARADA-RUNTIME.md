# D14-07 · publicación de la solicitud de parada

25.10.2026. Codex, trabajo paralelo al instalador de Claude. **Hallazgo P2 abierto en el producto; corrección propuesta y probada sólo en una copia privada.** No se editó el runtime compartido ni se instaló un servicio. No hay commits ni cambios en QA o en la VM.

## Para Claude

Antes de promover el próximo instalador, corregir la publicación de `stop-request.json` en `tools/windows/server-install/Invoke-RackClickServerRuntime.ps1`. El archivo compartido medido al cierre conserva SHA256 **`29c55fd16eef55aab2e8d1640257fc5990656f195fcec0915faf7e6645ce94b9`**, igual al snapshot ensayado. Comparar primero tu versión actual; no sobrescribir trabajo posterior.

1. Aplicar o adaptar la [propuesta atómica](../evidence/s1-20261025/runtime14-perfil-codex/PROPUESTA-ATOMICA.patch): temporal único en el mismo directorio privado, escritura/flush/cierre, comprobación ACL y `File.Move` sin sobrescribir. Si otro Stop publicó primero, validar esquema/UUID/instancia. Limpiar sólo el temporal propio. Mantener las comprobaciones actuales de ACL, identidad y estado.
2. Ejecutar el [foco determinista](../evidence/s1-20261025/runtime14-perfil-codex/reproduce_stop_publish_writer.ps1), y Start/HTTP/Backup/Stop/reinicio del runtime. La [revisión independiente](../evidence/s1-20261025/runtime14-perfil-codex/REVISION.md) indica exactamente lo ejecutado por el revisor.
3. Integrarlo en tu candidata nueva y actualizar sus pins/recibos. **No reemplazar bundle06 ni las candidatas congeladas.** La aplicación03/e9 y su DLL19c no cambian por esta corrección de operador.
4. Entregar hashes y evidencia para revisión. Este foco no acredita instalación limpia, host C#/SCM, cuenta de servicio ni reinicio de Windows Server. No desplegarlo en QA como parte de esta tanda.

La propuesta privada ensayada tiene SHA256 **`0752db6a67493491933914922d33641dc9c0b1fbd2ce0276908a9cd62341a94b`**. El parche está contra el snapshot anterior, no contra posibles cambios concurrentes de Claude. Su éxito aislado no cierra la integración del producto.

## Problema y prueba

Stop llama `Write-BackupNewText` sobre el nombre final. El helper crea ese archivo con `FileShare.None`; antes de cerrarlo, Start puede verlo con `File.Exists`. Su `ReadAllText` falla por compartición y el catch lo convierte en `stop_request_invalid`. Un JSON válido al terminar la escritura no evita esa ventana.

En el primer ensayo completo, la candidata03 arrancó por HTTPS, permitió login/escritura y generó backup. Stop devolvió `server_stop_failed`; el runtime terminó con `stop_request_invalid`, aunque confirmó cierre de aplicación y PostgreSQL. No se observó pérdida de datos. El informe conserva el intento de terminación de respaldo del observador y los puertos cerrados; no lo contamos como parada normal.

La reproducción determinista extrae los bloques AST reales de escritor y lector, importa los helpers reales y usa un breakpoint WinPS justo después del `CreateNew` real. Con el original, el nombre final ya es visible y el lector falla. Con la propuesta, sólo existe el temporal: el lector no ve todavía una orden; tras publicar, acepta el mismo contenido. Ambos rechazan un esquema/UUID inválidos. No se reemplazaron funciones por mocks. Es un foco de archivos y planificación, separado del ensayo completo con PostgreSQL.

## Resultado con la propuesta privada

Windows 11 local, WinPS5.1, PostgreSQL17.11 y runtime .NET10.0.12. Nueva base, puertos y claves; interfaz local de laboratorio. Recibos de instalación **sintéticos y explícitos** enlazan un despliegue privado real con el productor real de perfil TLS. No se ejecutó ni eludió el instalador bloqueado.

- Perfil válido; digest incorrecto rechazado.
- Readiness14, TLS verificado con CA exclusiva del cliente; login de contraseña sin acreditar MFA.
- Escritura con commit, negativo CSRF y lectura.
- Stop con UUID ajeno rechazado y runtime aún listo; backup online completo.
- Dos paradas normales, repetición del Stop exacto y datos conservados tras reinicio del runtime foreground.
- Entradas intactas, PostgreSQL propio detenido y puertos cerrados. `applicationHttpDrain=false` conservado.

El primer observador esperaba por error `server_backup_complete`; el operador devolvía correctamente `backup_complete`. Se corrigió sólo esa expectativa. Ese error no explica el fallo independiente de parada. Los intentos y límites están en el [cierre reproducible](../evidence/s1-20261025/runtime14-perfil-codex/CIERRE.md).

**Estado global aproximado:78 %, sin incremento automático.** Pendientes: integración/revisión de D14-07, instalador completo, ensayo limpio y reinicio de Windows Server, proveedor de laboratorio/HTTP MFA y custodia D2/QA/adopción final.
