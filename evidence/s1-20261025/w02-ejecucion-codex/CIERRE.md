# W-02 · contraste independiente de ejecución · 25.10.2026

**Resultado:** W-02.01 acreditado con 0,50 puntos; W-02.02–05 pendientes. [Dictamen](../../../docs/REVISION-W02-EJECUCION-CODEX.md), [respuesta para Claude](../../../docs/MENSAJE-PARA-CLAUDE-W02-EJECUCION-25-10-2026.md). Esta revisión no constituye aceptación de producto ni instalación nueva de Codex.

## Evidencia ejecutada y leída

Entorno del revisor: LEAO/Windows, PowerShell; Python 3.12, PostgreSQL 17.11 privado. Sin build .NET/frontend ni instalación de herramientas en este bloque.

| Comprobación | Resultado y límite |
|---|---|
| 35 ficheros originales de ejecución de Claude | SHA256/tamaños registrados en [ENTRADAS.json](ENTRADAS.json); conservados, sin reescribir su historia. |
| Cuatro ZIP sanitizados | Lectura y CRC de miembros; sólo `INFORME.json`, no credenciales/dumps. |
| Cuatro ZIP congelados 07 | 4/4 pins coinciden en [ARTEFACTOS.json](ARTEFACTOS.json); sin reconstruirlos. |
| New A y Restore B intento 3 | Recibos de instalación y postboot correlacionados por UUID; ambos postboot verificados. [CONTRASTE.json](CONTRASTE.json). La ejecución original es de Claude. |
| Exportación A y entrada B | Manifiesto de la segunda copia coincide; cliente visible en B según observación de Claude. No se leyó `data.dump` ni se repitió acceso HTTP. |
| Registro de dos VM | [REGISTRO-VM.json](REGISTRO-VM.json): metadatos aportados más configuración pasiva de hardware/red. Imagen declarada, no hash ISO autenticado; cuentas A no enumeradas exhaustivamente. |
| Primer fallo B | El ZIP original contiene diagnóstico de recuperación administrativa. No demuestra un fallo del motor PostgreSQL. |
| Prueba propia CLI con DLL exacta 07 | PASS 16,72 s, PG17.11 nuevo: nombre existente rechazado sin mutación en 14 tablas/marcador; nombre nuevo conservando original y auditando recuperación. [REPRO-COLISION.json](REPRO-COLISION.json). |
| Revisión distinta | [REVISION-HALLAZGOS.md](REVISION-HALLAZGOS.md): fuentes congeladas, clasificación, lectura del test antes de ejecución y resultado/registro después. No declara pruebas propias del revisor delegado. |

## Prueba reproducible

Fuente: [test_recovery_username_collision.py](../../../development/server/tests/test_recovery_username_collision.py). Invocación real:

```powershell
C:/Python312/python.exe -X utf8 -B development/server/tests/test_recovery_username_collision.py --dll C:/RackClick_SVR/.local/w02-ejecucion-review-20261025T142111Z-56a4e28c/frozen-server/RackClick.Server.dll --output C:/RackClick_SVR/.local/w02-ejecucion-review-20261025T142111Z-56a4e28c/recovery-collision
```

Se extrajeron únicamente los 24 archivos de servidor permitidos del bundle fijado, a un directorio nuevo privado; DLL `19c94d4e104ef117f4c7788a0a0d4fbe1f846656c4e00d2dc854c2e80bd7f78c`. El test exige salida privada nueva y genera secretos/base/cuentas locales de laboratorio; llama al CLI de esa DLL y usa una lista interna cerrada de 14 tablas. El marcador simula una identidad restaurada: no sustituye a un ensayo de `pg_restore` ni confirma la causa exacta histórica. Se detuvo el laboratorio y se comprobó input intacto. Logs/credenciales permanecen en `.local/`, no en esta evidencia.

La lectura del hipervisor se limita a `vmrun list`, inventario, configuración y búsqueda de identificadores concretos en logs existentes. RackClickSRV apagada/VMnet2; vínculo con QA y causa desconocidos. Cero autenticaciones invitadas, órdenes de potencia o cambios de servicios/cuentas/red/VM. No se certifica lo realizado por terceros fuera de los recibos revisados.

## Cierre y pendientes

Conforme con la revisión distinta, se acredita sólo W-02.01. Peso/texto/denominador congelados; delta 1/2, total **67/14 = 4,79/100**, **11/280 subpasos** y **1/50 resultados** del inventario restante. [Crédito](CREDITO-W0201.json). No es el porcentaje global del producto.

Pendientes: error CLI original del primer fallo; mejor diagnóstico; reintento con cuenta nueva sin borrar identidades; informe del auxiliar resistente a reinicio; presentación del estado actual frente a recibos históricos; comparación hoja/GUI; resto de matriz Windows y cierre independiente completo. Se preservan los fallos, la intervención manual declarada y todos los ZIP 07. No se integra C2 ni se modifica el catálogo de QA por esta revisión sin cambio visible.

Integridad de cierre: [fuentes](FUENTES.json), [controles](CONTROLES.json), [escaneo](ESCANEO.json), [manifiesto](SHA256SUMS.txt). Sin commits, push, publicación, cambios de producto o acciones sobre QA. La prueba nueva y el ledger/documentación son los cambios propios de este bloque.
