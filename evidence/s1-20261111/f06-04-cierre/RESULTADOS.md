# F-06.04 · cierre de rotación y recuperación coherente

11.11.2026. Cierre técnico con revisión independiente favorable. Sin operaciones en D/E, VM, servicios instalados, cuentas o bases ajenas; sin commits, push o despliegues.

## Reutilización e investigación

Se contrastaron primero F-06.01/.02/.03, D2 y sus evidencias revisadas. El revisor identificó el catálogo vacío de `MfaRotationProcessTests`: las caídas probaban conciliación de DB/material, pero no un conjunto de backups retenidos anterior y posterior. El escenario nuevo cierra esa brecha, conservando el producto.

Se reutilizan los componentes existentes sin bibliotecas, versiones o licencias nuevas. Consulta11.11.2026: [pg_dump17](https://www.postgresql.org/docs/17/app-pgdump.html), [pg_restore17](https://www.postgresql.org/docs/17/app-pgrestore.html). El censo utiliza la instantánea exportada que consume pg_dump custom; Restore usa `--single-transaction --exit-on-error` en base nueva. PostgreSQL transporta la DB, no el almacén DPAPI. El material y AAD se validan con RackClick por separado.

## Ejecución del coordinador

Windows, SDK10.0.401/runtime10.0.12, PostgreSQL17.11. Congelado privado `.local/f0604-af3681af/freeze`, binlogs únicos y logs originales privados.

- Servidor SHA256: `3a39bb95e2fc45b3eccff3376b53535d0273766743204874180f1112e62956fd`.
- Pruebas SHA256: `2e189e549b897e9e5a28318f0277318c67dd93df7a50c044de02f7860003f0ed`.
- Restore locked y build Release: exit0,0 errores/advertencias.
- Cinco invocaciones del trabajador:5PASS,0FAIL,0 omitidas. Dos rotaciones reales1→8→9, tres backups de generaciones `[1,7,7]`, `[8,8,8]`, `[9,9,9]` y tres Restores reales en otros clústeres. Cuatro clústeres propios terminados al concluir.
- Catálogo final con3entradas, no una afirmación de descubrimiento automático de medios.
- Todos los factores se autentican antes/después de cada rotación; cada Restore se autentica con proveedor del anillo final y con un almacén nuevo recuperado desde su sobre. Se preservan secretos TOTP y metadatos, incluidos estado y antirreplay.
- Retirada1/7/8 bloqueada por backups; clave1 ausente y dump alterado rechazan `PrepareAsync` sin mutar DB/anillo ni crear fence. En cada destino, una clave ausente rechaza el descifrado sin escribir DB; su restitución permite autenticar de nuevo.
- Cada Restore conserva la huella de ciphertext y número de testigos de la DB origen. No se sobrescribe ni reconcilia la DB origen con un backup antiguo.

Comando reproducible: `C:/Python312/python.exe -B tools/tests/run_mfa_rotation_closure.py --source-root <freeze> --expected-server-sha256 <pin servidor> --expected-tests-sha256 <pin pruebas>`. El runner comprueba ambos pines antes y después de cada fase. Contextos con credenciales, sobres, DPAPI, dumps y salidas originales quedan sólo en `.local/` privado, nunca en esta evidencia.

## Integridad y atribución

`FUENTES.json` registra227archivos de producto idénticos al congelado F-06.03, las fuentes nuevas de prueba/arnés y los pines. Ningún SQL, contrato de cifrado, dependencia, Program, coordinador o publicador cambia. La diferencia de hashes binarios procede de reconstruir en otra ruta; no se afirma reproducibilidad bit a bit ni se sustituye el pin de F-06.03.

Los360casos de regresión,15cortes/15reaperturas,2Restores de transición y3negativosPG de F-06.03 son **ejecuciones históricas reutilizadas**, con sus fuentes y sellos contrastados. Los297casos,8controles de backup y revisión153 de F-06.02 también se reutilizan. No se presentan como pruebas nuevas ni se suman otra vez para acreditar alcance.

## Intentos y límites

El primer build aislado falló con `batch50_catalog_stale`: faltaban los scripts/inputs que fijan los targets del catálogo. Se contrastaron sus858entradas por hash y se copiaron a la copia privada; el siguiente build pasó. No se regeneró catálogo ni se relajó el target. No hubo cambio de producto ni reproducción de un defecto: estas pruebas nuevas añaden cobertura y pasaron en su primera ejecución funcional. No se inventa una fase roja.

Los metadatos del backup se comparan en este escenario secuencial sin escritores; el censo/dump sí comparten snapshot. No se afirma que la lectura auxiliar de metadatos en otra conexión comparta esa instantánea ante concurrencia. Los sobres de rotación se autentican en memoria; los tres sobres de backup sí se conservan cifrados en el laboratorio. No son custodia física externa.

El token/confianza son de laboratorio; no el SID efectivo de un servicio instalado. No hay CLI pública rotate, instalador46, nueva aceptación de Wascar, reinicio de Windows, apagón o persistencia universal ante pérdida eléctrica. Restore es offline, misma identidad explícita y mismo equipo DPAPI; no portabilidad ni adaptación. No se elimina una clave antigua ni se ensaya retirada criptográfica física.

El `verified` interno sigue significando conciliación offline; `service_resumed` y `verified` operativo D2 siguen pendientes. La matriz delimita el cierre técnico; los hitos de implementación operativa, integración y aceptación no se cierran por este ensayo.


## Dictamen y conciliación

[Revisión distinta](review/DICTAMEN.md): repite cinco fases propias, tres Restores y cuatro clústeres terminados con los mismos pines. No son los resultados del coordinador. F-06.04 acredita únicamente5/8:3529/168→1817/84=21,630952…/100del cierre restante,21,63redondeado. Hitos técnicos de pruebas/revisión conciliados; definición/implementación operativas, integración y aceptación siguen pendientes. No se acredita porcentaje global ni adopción.
