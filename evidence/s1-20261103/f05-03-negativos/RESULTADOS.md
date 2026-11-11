# Paso 16 · F-05.03 · negativos del sobre MFA

03.11.2026. **Cerrado con revisión independiente favorable.** Se reutilizó la evidencia antes de decidir que no existía un hueco material que exigiera implementar o repetir pruebas. D/E se conservan sin operaciones. Cero compilaciones, pruebas criptográficas nuevas, sobres nuevos, cambios de producto/dependencias o accesosVM/DB/servicios/cuentas/claves.

## Evidencia y cobertura

[Investigación](INVESTIGACION-Y-DECISION.md), [matriz](MATRIZ-NEGATIVOS.md) y [casos conciliados](NEGATIVOS-CONCILIADOS.json) relacionan el criterio con contraseña incorrecta, alteración de sal/nonce/tag/ciphertext, truncados, datos extra/concatenación, versión/KDF/AEAD desconocidos y coste/tamaños fuera de perfil. Codificación/longitudes y AAD tienen además sus controles pertinentes.

`CONCILIAR-NEGATIVOS.py`, Python3.12, salida0:21referencias, seis fuentes idénticas a sus manifiestos y selloL2d7/7. El log público conserva26PASS nominales del autor; el recibo de la revisión26.10 conserva26+8PASS y salidas0, sin fallos/omisiones. Incluyen controles positivos; no se presentan como34negativos únicos o ejecuciones nuevas. `SALIDA-VERIFICACION.json` registra la segunda comprobación.

Los errores de autenticación de los casos instrumentados acreditan1KDF; forma/perfil/tamaños ilegales acreditan0donde la aserción lo comprueba. Los contadores son de la llamada bajo prueba, sin la preparaciónLazy del sobre válido. Datos extra y concatenación rechazan autenticación, **sin contadorKDF instrumentado en esos dos controles**. No se inventa su número ni una duración0ms para rechazos.

El coste fuera de perfil probado fue600001. La fuente invariable compara desigualdad exacta con600000 antes de derivar, por lo que cualquier valor distinto recorre la misma rama; no se afirma que se ejecutaran0/599999/todoslosuint. Truncados/tamaños concretos están cubiertos, sin prometer todos los prefijos/fuzzing exhaustivo. La batería existente y revisión de fuente bastan para las categorías del criterio.

## Correspondencia de integración

Codec/tests conservan sus identidadesL2d. `WindowsMfaKeyRecovery`/tests son idénticos aL2f y RecoveryFiles/tests aL2gcorrección. `Recover` abre/autentica, analiza el contenido y después llama al writer. La prueba existente de contraseña incorrecta/ciphertext alterado exige `AuthenticationFailed` y destino ausente. El cambio posterior del writerF04 no se alcanza en esos fallos y no obliga a repetir ese recorrido.

El comentario histórico `altered[^1]` dice «tag», pero modifica ciphertext; su precisiónL2f ya lo documenta. Esta revisión acredita tag mediante el cambio real en offset43 del codec. Formato ilegal y autenticación fallida conservan categorías distintas; no hay promesa de indistinguibilidad universal, tiempos iguales, memoria físicamente limpia o recuperación operativa de factores/sesiones.

## Revisión y cierre

[Dictamen independiente favorable](review/DICTAMEN-F0503.md), revisor distinto del implementador: sin bloqueantes en este subpaso. Su [verificador](review/Verify-Negative-Evidence.py) terminó en0, contrastando referencias/fuentes,26PASS y8controles históricos; [comprobación](review/COMPROBACION-F0503.json). Sin builds/testnuevos, operacionesVM/DB o credenciales/binlogs privados.

Sólo **F-05.03 +1/2**:1481/84→1523/84 =**18,13/100 del cierre restante**.39checkpoints cerrados/241sin cierre (239pending,2in_progress),53resultados/280checkpoints/268números, criterios/pesos/huella congelada intactos. **F-05.04/.05 y todoF05 siguen abiertos.** No es porcentaje global nuevo ni adopción productiva.

Ledger, contexto maestro, plan numerado, progreso y changelog actualizados. Tres generadores write/check y conciliación del único estado, escaneo de selección y sello conservados; planes/documentos previos y sello del paso15 preservados. Sin cambio visible/disponibilidadQA ni resultados de Wascar modificados; sin commits/push. Siguiente **17/F-05.04**, recuperar el anillo en otra instanciaWindows preservando identidad/AAD/custodia; no se declara ese resultado por la prueba del codec o de un almacénTEMP en el mismo equipo.
