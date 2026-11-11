# Paso 30 · material nuevo y reenrolamiento por pérdida de claves MFA

11.11.2026 · F-09.02. Cerrado técnicamente con revisión independiente favorable, limitado al protocolo interno publicado con fence. **D y E se conservan.**

El protocolo interno permite preparar un anillo nuevo cuando se declaran expresamente versiones de clave perdidas. Conserva las claves que todavía se pueden leer, los archivos originales opacos y las filas cifradas completas de los factores afectados. Retira esos factores de la tabla viva y obliga a sus cuentas a configurar un factor nuevo. Conserva cuentas, permisos, gracia45 e inventario.

## Recorrido y protección

1. **Prepare:** censo de versiones del anillo, archivos, factores de todos los estados, historial y backups declarados. La versión nueva supera todo ese censo. Una clave aún legible no se puede declarar perdida; una dependencia no declarada bloquea. Se conservan originales privados, candidato y bloqueo persistente de mantenimiento.
2. **Export:** devuelve un sobre RCKEY cifrado en memoria. No lo guarda dentro de la instancia ni de sus backups. Antes de Apply hay que entregar ese mismo sobre, su contraseña y su hash; se autentica contra el candidato y su pin queda fijado en metadatos privados.
3. **Apply:** una transacción archiva las filas completas de los factores afectados en `rackclick_private`, las retira del uso, fuerza required/pending y aumenta su revisión. Incluye las revocaciones mínimas inseparables y un testigo de autoridad Windows. No inventa un actor RackClick ni modifica fechas de gracia o permisos. Un fallo deshace toda la transacción.
4. **Publish:** comprueba plan, candidato, sobre, testigo, base y objetos del disco; publica la clave nueva y el anillo y comprueba el material restante. **Mantiene el bloqueo de mantenimiento.** Las reentradas por el mismo UUID no repiten la transición.

Los entrypoints productivos recapturan la autoridad Windows y consultan el servicio vinculado parado antes de acceder a la base. Los ensayos usan un seam interno explícito con identidad de laboratorio; no equivale a un positivo elevado o bajo el SID del servicio instalado.

## Qué no hay que ejecutar aún

`--mfa-emergency-recovery` continúa rechazando la transición con cero operaciones y sin sesión. No se ha actualizado ningún instalador ni se ha desplegado el esquema47 en D/E. Esta tanda no ofrece una recuperación operativa del servidor.

El caso sin anillo o con historial desconocido se detiene: no adivina la versión ni reconstruye un namespace. El positivo de pérdida total probado conserva metadatos fiables y usa blobs corruptos/uno vacío. Hay un negativo con un archivo de clave físicamente retirado y candidato alterado; no es una recuperación de una carpeta completa desaparecida.

Las interrupciones son excepciones inyectadas en checkpoints, no apagones ni procesos terminados por fuerza. La atomicidad DB/disco y la durabilidad universal del directorio no se afirman. Las rutas demasiado largas para el escritor Win32 aprobado se rechazan antes de crear archivos/fence.

## Evidencia y continuación

[Plan e investigación](PLAN-F0902-MATERIAL-PERDIDA-MFA.md) · [resultados](../evidence/s1-20261111/f09-02-material-perdida/RESULTADOS.md) · [matriz](../evidence/s1-20261111/f09-02-material-perdida/MATRIZ-CRITERIO.md) · [revisión independiente](../evidence/s1-20261111/f09-02-material-perdida/review/DICTAMEN.md).

Los pasos31–33 siguen pendientes: contrato completo de revocación/auditoría, composición de la CLI, guarda de arranque específica de pérdida, servicio real/HTTPS y ensayo operativo de pérdida total. La observación de automatización Edge del paso28 permanece abierta. No se habilitan casos GUI nuevos ni se alteran resultados personales de QA.


Sólo F-09.02 acredita **1/2 punto**: índice del cierre restante **25,13→25,63/100**. No es porcentaje global nuevo ni habilitación de emergencia en D/E. Siguiente paso31/F-09.03.
